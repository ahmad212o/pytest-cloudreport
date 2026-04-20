"""
local_report.py — offline HTML reporting for pytest-cloudreport.

Used by --cloudreport-local and --accumulate flags.
No network, no API key, no external dependencies beyond stdlib + jinja2.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Jinja2 is available as a pytest dependency — no new dep needed.
from jinja2 import Environment, FileSystemLoader, select_autoescape

_DB_DIR = Path.home() / ".pytest-cloudreport"
_DB_PATH = _DB_DIR / "history.db"
_TEMPLATE_DIR = Path(__file__).parent / "templates"


# ── Git helpers ────────────────────────────────────────────────────────────────

def _get_git_branch() -> Optional[str]:
    """Reuse the same detection logic as the main plugin."""
    for var in ("GITHUB_REF_NAME", "CI_COMMIT_REF_NAME", "GIT_BRANCH", "CIRCLE_BRANCH"):
        val = os.environ.get(var)
        if val:
            return val
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL, text=True, timeout=5,
        ).strip()
        return branch if branch and branch != "HEAD" else None
    except Exception:
        return None


def _get_git_sha() -> Optional[str]:
    for var in ("GITHUB_SHA", "CI_COMMIT_SHA", "GIT_COMMIT", "CIRCLE_SHA1"):
        val = os.environ.get(var)
        if val:
            return val[:7]
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL, text=True, timeout=5,
        ).strip() or None
    except Exception:
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

def collect_run_data(plugin) -> dict:
    """
    Build a run data dict from the _CloudReportPlugin instance.

    Accepts the plugin instance directly so we can access self._results
    and self._session_start without re-implementing collection logic.
    """
    import time

    tests = list(plugin._results.values())

    passed  = sum(1 for t in tests if t["status"] == "passed")
    failed  = sum(1 for t in tests if t["status"] in ("failed", "error"))
    skipped = sum(1 for t in tests if t["status"] == "skipped")

    duration_s = 0.0
    if plugin._session_start is not None:
        duration_s = round(time.monotonic() - plugin._session_start, 2)

    failed_tests = [
        {
            "name": t["test_name"],
            "duration_ms": t["duration_ms"] or 0,
            "error_message": (t["error_message"] or "")[:500],
        }
        for t in tests
        if t["status"] in ("failed", "error")
    ]

    return {
        "project_path": str(Path.cwd()),
        "branch": _get_git_branch(),
        "commit_sha": _get_git_sha(),
        "total": len(tests),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "duration_s": duration_s,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "failed_tests": failed_tests,
    }


def save_to_sqlite(run_data: dict) -> None:
    """
    Save run_data to ~/.pytest-cloudreport/history.db.
    Creates the DB and tables if they do not exist.
    Never raises — all errors are caught and printed silently.
    """
    try:
        _DB_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(_DB_PATH))
        cursor = conn.cursor()

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                project_path TEXT    NOT NULL,
                branch       TEXT,
                commit_sha   TEXT,
                total        INTEGER NOT NULL,
                passed       INTEGER NOT NULL,
                failed       INTEGER NOT NULL,
                skipped      INTEGER NOT NULL,
                duration_s   REAL    NOT NULL,
                created_at   TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS test_results (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id        INTEGER NOT NULL REFERENCES runs(id),
                test_name     TEXT    NOT NULL,
                status        TEXT    NOT NULL,
                duration_ms   INTEGER NOT NULL,
                error_message TEXT
            );
        """)

        cursor.execute(
            """
            INSERT INTO runs
              (project_path, branch, commit_sha, total, passed, failed,
               skipped, duration_s, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_data["project_path"],
                run_data["branch"],
                run_data["commit_sha"],
                run_data["total"],
                run_data["passed"],
                run_data["failed"],
                run_data["skipped"],
                run_data["duration_s"],
                run_data["created_at"],
            ),
        )
        run_id = cursor.lastrowid

        for ft in run_data.get("failed_tests", []):
            cursor.execute(
                """
                INSERT INTO test_results (run_id, test_name, status, duration_ms, error_message)
                VALUES (?, ?, 'failed', ?, ?)
                """,
                (run_id, ft["name"], ft["duration_ms"], ft["error_message"]),
            )

        conn.commit()
        conn.close()
    except Exception as exc:
        print(f"[cloudreport] Warning: could not save to SQLite — {exc}")


def get_history(project_path: str, limit: int = 10) -> list[dict]:
    """
    Read the last `limit` runs for this project from SQLite.
    Returns newest-first. Returns [] on any error or if DB doesn't exist.
    """
    if not _DB_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(str(_DB_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM runs
            WHERE project_path = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (project_path, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as exc:
        print(f"[cloudreport] Warning: could not read history — {exc}")
        return []


def generate_html(run_data: dict, history: list[dict]) -> str:
    """
    Render the Jinja2 HTML template with run data and history.
    Returns the complete HTML string.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("local_report.html")

    pass_rate = 0.0
    if run_data["total"] > 0:
        pass_rate = round(run_data["passed"] / run_data["total"] * 100, 1)

    generated_at = datetime.now().strftime("%b %d %Y %H:%M:%S")

    return template.render(
        run={**run_data, "pass_rate": pass_rate},
        history=history,
        has_history=bool(history),
        generated_at=generated_at,
    )


def open_report(html_content: str, output_path: str = "cloudreport.html") -> None:
    """
    Write html_content to output_path and open in the default browser.
    Never raises.
    """
    try:
        out = Path(output_path).resolve()
        out.write_text(html_content, encoding="utf-8")
        webbrowser.open(out.as_uri())
    except Exception as exc:
        print(f"[cloudreport] Warning: could not open report — {exc}")
