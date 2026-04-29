"""pytest-cloudreport: uploads pytest results to Cloud Report for analytics.

Configuration (in order of precedence):
  env PYTEST_CLOUD_API_KEY     — your project API key (required)
  pytest.ini cloudreport_api_key

  env PYTEST_CLOUD_API_URL     — override backend URL (optional, for self-hosted)
  pytest.ini cloudreport_api_url

  env PYTEST_CLOUD_ENV         — environment label, default "ci"
  pytest.ini cloudreport_environment

  env CLOUDREPORT_DISABLE=1   — disable the plugin entirely (killswitch)

Flags:
  --cloudreport         enable upload (also auto-enabled when API key is set)
  --cloudreport-verbose print upload result / error to stdout
  --cloudreport-local   generate a local HTML report (works with or without cloud upload)
  --accumulate          append run to local history DB (requires --cloudreport-local)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import warnings
from typing import Optional

import pytest

_PLUGIN_NAME = "cloudreport-collector"
_DEFAULT_API_URL = "https://www.cloudreport.dev"
_MAX_ERROR_LEN = 2_000  # chars — keep payloads sane
_CONNECT_TIMEOUT = 2    # seconds for TCP connect
_TOTAL_TIMEOUT = 5      # seconds for connect + read combined


# ── CI environment detection ──────────────────────────────────────────────────


def _detect_ci_provider() -> str:
    if os.environ.get("GITHUB_ACTIONS"):
        return "github_actions"
    if os.environ.get("GITLAB_CI"):
        return "gitlab_ci"
    if os.environ.get("JENKINS_URL"):
        return "jenkins"
    if os.environ.get("CIRCLECI"):
        return "circleci"
    return "local"


def _detect_ci_run_id() -> Optional[str]:
    return (
        os.environ.get("GITHUB_RUN_ID")
        or os.environ.get("CI_PIPELINE_ID")  # GitLab CI
        or os.environ.get("BUILD_NUMBER")  # Jenkins
        or os.environ.get("CIRCLE_WORKFLOW_ID")  # CircleCI
        or None
    )


def _detect_branch() -> Optional[str]:
    for var in ("GITHUB_REF_NAME", "CI_COMMIT_REF_NAME", "GIT_BRANCH", "CIRCLE_BRANCH"):
        val = os.environ.get(var)
        if val:
            return val
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            # detached HEAD → not useful
            return branch if branch and branch != "HEAD" else None
    except Exception:
        pass
    return None


def _detect_commit_sha() -> Optional[str]:
    for var in ("GITHUB_SHA", "CI_COMMIT_SHA", "GIT_COMMIT", "CIRCLE_SHA1"):
        val = os.environ.get(var)
        if val:
            return val
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except Exception:
        pass
    return None


# ── Plugin class ──────────────────────────────────────────────────────────────


class _CloudReportPlugin:
    """Collects per-test results and uploads them after the session ends."""

    def __init__(
        self,
        api_key: str,
        api_url: str,
        environment: str,
        verbose: bool,
        cloud_active: bool = True,
    ) -> None:
        self._api_key = api_key
        self._api_url = api_url.rstrip("/")
        self._environment = environment
        self._verbose = verbose
        self._cloud_active = cloud_active
        # nodeid → result dict (last write wins so teardown errors can update)
        self._results: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._session_start: Optional[float] = None

    # ── pytest hooks ──────────────────────────────────────────────────────────

    def pytest_sessionstart(self, session: pytest.Session) -> None:
        try:
            self._session_start = time.monotonic()
        except BaseException:
            pass

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        try:
            self._handle_logreport(report)
        except BaseException:
            pass

    def _handle_logreport(self, report: pytest.TestReport) -> None:
        nodeid = report.nodeid

        if report.when == "call":
            # Skip intermediate retry reports from pytest-rerunfailures.
            # Intermediate retries have report.rerun > 0; the final outcome
            # (pass or last failure) has no rerun attribute or rerun == 0.
            if getattr(report, "rerun", 0):
                return

            if report.passed:
                status = "passed"
            elif report.failed:
                # xfail (expected failure) is reported as failed but is not a real failure
                status = "passed" if hasattr(report, "wasxfail") else "failed"
            else:
                status = "skipped"

            error_msg: Optional[str] = None
            if report.failed and not hasattr(report, "wasxfail") and report.longrepr:
                error_msg = str(report.longrepr)[:_MAX_ERROR_LEN]

            with self._lock:
                self._results[nodeid] = {
                    "test_name": _test_name_from_nodeid(nodeid),
                    "nodeid": nodeid,
                    "file_path": _file_path_from_nodeid(nodeid),
                    "status": status,
                    "duration_ms": _ms(report.duration),
                    "error_message": error_msg,
                }

        elif report.when == "setup":
            if report.skipped:
                with self._lock:
                    self._results[nodeid] = {
                        "test_name": _test_name_from_nodeid(nodeid),
                        "nodeid": nodeid,
                        "file_path": _file_path_from_nodeid(nodeid),
                        "status": "skipped",
                        "duration_ms": None,
                        "error_message": None,
                    }
            elif report.failed:
                with self._lock:
                    self._results[nodeid] = {
                        "test_name": _test_name_from_nodeid(nodeid),
                        "nodeid": nodeid,
                        "file_path": _file_path_from_nodeid(nodeid),
                        "status": "error",
                        "duration_ms": None,
                        "error_message": str(report.longrepr)[:_MAX_ERROR_LEN]
                        if report.longrepr
                        else None,
                    }

        elif report.when == "teardown" and report.failed:
            with self._lock:
                existing = self._results.get(nodeid)
                if existing:
                    existing["status"] = "error"
                    existing["error_message"] = (
                        str(report.longrepr)[:_MAX_ERROR_LEN]
                        if report.longrepr
                        else None
                    )

    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: object) -> None:
        try:
            self._handle_sessionfinish(session, exitstatus)
        except BaseException:
            pass

    def _handle_sessionfinish(self, session: pytest.Session, exitstatus: object) -> None:
        with self._lock:
            if not self._results:
                if self._verbose:
                    print(
                        "\n[cloudreport] No test results collected — skipping upload."
                    )
                return
            tests = list(self._results.values())

        duration_ms: Optional[int] = None
        if self._session_start is not None:
            duration_ms = int((time.monotonic() - self._session_start) * 1000)
        passed = sum(1 for t in tests if t["status"] == "passed")
        failed = sum(1 for t in tests if t["status"] in ("failed", "error"))
        skipped = sum(1 for t in tests if t["status"] == "skipped")

        payload = {
            "branch": _detect_branch(),
            "commit_sha": _detect_commit_sha(),
            "ci_provider": _detect_ci_provider(),
            "ci_run_id": _detect_ci_run_id(),
            "environment": self._environment,
            "duration_ms": duration_ms,
            "total_tests": len(tests),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "tests": tests,
        }

        local_mode = session.config.getoption("--cloudreport-local", default=False)
        accumulate = session.config.getoption("--accumulate", default=False)

        if accumulate and not local_mode:
            print(
                "\npytest-cloudreport: --accumulate requires --cloudreport-local. Ignoring."
            )
            return

        if local_mode and self._cloud_active:
            print(
                "\npytest-cloudreport: Local report enabled; cloud upload also active because an API key is configured."
            )

        if self._cloud_active:
            # Upload in a background thread, then join with a generous timeout
            # so the process waits for the result but never hangs CI indefinitely.
            # _TOTAL_TIMEOUT (5 s) bounds the actual network call; 30 s is the
            # outer safety net for any unexpected delay before the thread starts.
            thread = threading.Thread(
                target=self._upload, args=(payload,), daemon=True
            )
            thread.start()
            thread.join(timeout=30)

        if local_mode:
            try:
                from .local_report import (
                    collect_run_data,
                    save_to_sqlite,
                    get_history,
                    generate_html,
                    open_report,
                )

                run_data = collect_run_data(self)  # pass the plugin instance

                if accumulate:
                    save_to_sqlite(run_data)
                    history = get_history(run_data["project_path"], limit=10)
                else:
                    history = []

                html = generate_html(run_data, history)
                open_report(html)

                if accumulate:
                    print(
                        f"\npytest-cloudreport: Report saved. "
                        f"History: {len(history)} runs. Open: cloudreport.html"
                    )
                else:
                    print(
                        "\npytest-cloudreport: Report generated. Open: cloudreport.html"
                    )
            except Exception as exc:
                # Never break CI
                print(f"\npytest-cloudreport: Local report failed — {exc}")

    # ── Upload ────────────────────────────────────────────────────────────────

    def _upload(self, payload: dict) -> None:
        """HTTP POST to the backend.  Runs in a daemon thread; never raises."""
        try:
            data = json.dumps(payload, default=str).encode("utf-8")
            req = urllib.request.Request(
                f"{self._api_url}/api/runs",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self._api_key,
                    "User-Agent": "pytest-cloudreport/0.1.2",
                },
                method="POST",
            )
            # _TOTAL_TIMEOUT covers both TCP connect and read phases.
            # A Railway/infra hiccup that hangs the socket will be aborted
            # after this many seconds so CI never blocks indefinitely.
            with urllib.request.urlopen(req, timeout=_TOTAL_TIMEOUT) as resp:
                body: dict = json.loads(resp.read())
            if self._verbose:
                status = body.get("status", "ok")
                run_id = body.get("run_id", "")
                if status == "duplicate":
                    print(
                        f"\n[cloudreport] Duplicate run — already uploaded. run_id={run_id}"
                    )
                else:
                    print(f"\n[cloudreport] Upload successful. run_id={run_id}")

        except urllib.error.HTTPError as exc:
            if self._verbose:
                try:
                    detail = exc.read().decode("utf-8", errors="replace")[:500]
                except Exception:
                    detail = "(no body)"
                print(f"\n[cloudreport] Upload failed: HTTP {exc.code} — {detail}")

        except Exception as exc:  # network error, timeout, etc.
            if self._verbose:
                print(f"\n[cloudreport] Upload failed: {exc}")
            else:
                print(
                    "[cloudreport] Upload failed (use --cloudreport-verbose for details)",
                    file=sys.stderr,
                )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _ms(duration: Optional[float]) -> Optional[int]:
    """Convert float seconds → integer milliseconds."""
    return int(duration * 1000) if duration is not None else None


def _file_path_from_nodeid(nodeid: str) -> Optional[str]:
    """'path/to/test_foo.py::Class::test_bar' → 'path/to/test_foo.py'"""
    return nodeid.split("::")[0] if "::" in nodeid else nodeid or None


def _test_name_from_nodeid(nodeid: str) -> str:
    """'path/to/test_foo.py::Class::test_bar[param]' → 'Class::test_bar[param]'
    Falls back to the full nodeid if there is no '::' separator.
    """
    parts = nodeid.split("::")
    return "::".join(parts[1:]) if len(parts) > 1 else nodeid


# ── pytest integration ────────────────────────────────────────────────────────


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("cloudreport", "pytest-cloudreport test reporting")
    group.addoption(
        "--cloudreport",
        action="store_true",
        default=False,
        help="Enable pytest-cloudreport upload (auto-enabled when PYTEST_CLOUD_API_KEY is set).",
    )
    group.addoption(
        "--cloudreport-verbose",
        action="store_true",
        default=False,
        help="Print upload result or error message after the session.",
    )
    group.addoption(
        "--cloudreport-local",
        action="store_true",
        default=False,
        help="Generate a self-contained HTML report after the run. If an API key is configured, cloud upload still runs too.",
    )
    group.addoption(
        "--accumulate",
        action="store_true",
        default=False,
        help="Save results to local SQLite history (~/.pytest-cloudreport/history.db). "
        "Requires --cloudreport-local.",
    )
    parser.addini(
        "cloudreport_api_key",
        default="",
        help="pytest-cloudreport project API key.",
    )
    parser.addini(
        "cloudreport_api_url",
        default="",
        help="Override backend URL (default: https://api.cloudreport.dev).",
    )
    parser.addini(
        "cloudreport_environment",
        default="",
        help="Environment label attached to every run (default: ci).",
    )


def pytest_configure(config: pytest.Config) -> None:
    try:
        _configure(config)
    except BaseException:
        pass


def _configure(config: pytest.Config) -> None:
    # Hard killswitch — security-conscious teams can disable the plugin entirely
    # without removing it from their dependencies.
    if os.environ.get("CLOUDREPORT_DISABLE", "").strip() in ("1", "true", "yes"):
        return

    # pytest-xdist: only upload from the controller process, not from workers.
    # Workers set PYTEST_XDIST_WORKER to their worker ID (e.g. "gw0").
    if os.environ.get("PYTEST_XDIST_WORKER"):
        return

    # Resolve API key (env > ini)
    api_key: str = (
        os.environ.get("PYTEST_CLOUD_API_KEY", "").strip()
        or config.getini("cloudreport_api_key").strip()
    )

    # Plugin is active when --cloudreport flag is passed OR an API key is present
    flag_enabled: bool = bool(config.getoption("--cloudreport", default=False))
    key_present: bool = bool(api_key)
    local_mode: bool = bool(config.getoption("--cloudreport-local", default=False))

    cloud_active = flag_enabled or key_present

    if cloud_active and not api_key:
        warnings.warn(
            "[cloudreport] --cloudreport flag set but no API key found. "
            "Set PYTEST_CLOUD_API_KEY or add cloudreport_api_key to pytest.ini.",
            stacklevel=2,
        )
        cloud_active = False

    if cloud_active:
        api_url: str = (
            os.environ.get("PYTEST_CLOUD_API_URL", "").strip()
            or config.getini("cloudreport_api_url").strip()
            or _DEFAULT_API_URL
        )

        environment: str = (
            os.environ.get("PYTEST_CLOUD_ENV", "").strip()
            or config.getini("cloudreport_environment").strip()
            or "ci"
        )

        verbose: bool = bool(config.getoption("--cloudreport-verbose", default=False))

        plugin = _CloudReportPlugin(
            api_key=api_key,
            api_url=api_url,
            environment=environment,
            verbose=verbose,
        )
        config.pluginmanager.register(plugin, _PLUGIN_NAME)
        return

    # Register local-only plugin if --cloudreport-local is set without cloud upload.
    # Reuses the full collection machinery; upload is skipped via cloud_active=False.
    if local_mode and config.pluginmanager.get_plugin(_PLUGIN_NAME) is None:
        local_plugin = _CloudReportPlugin(
            api_key="",
            api_url="",
            environment="local",
            verbose=False,
            cloud_active=False,
        )
        config.pluginmanager.register(local_plugin, _PLUGIN_NAME)


def pytest_sessionfinish(session: pytest.Session, exitstatus: object) -> None:
    """
    Module-level hook: emits the --accumulate-without-local warning when
    no plugin instance handled it. If the plugin is registered, its own
    sessionfinish method handles everything.
    """
    try:
        if session.config.pluginmanager.get_plugin(_PLUGIN_NAME) is not None:
            return

        local_mode = bool(session.config.getoption("--cloudreport-local", default=False))
        accumulate = bool(session.config.getoption("--accumulate", default=False))

        if accumulate and not local_mode:
            print(
                "\npytest-cloudreport: --accumulate requires --cloudreport-local. Ignoring."
            )
    except BaseException:
        pass
