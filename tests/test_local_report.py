"""
Tests for local_report.py — offline HTML reporting mode.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pytest_cloudreport.local_report import (
    collect_run_data,
    generate_html,
    get_history,
    open_report,
    save_to_sqlite,
)

pytest_plugins = ["pytester"]


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _make_plugin(passed=5, failed=2, skipped=1):
    """Return a minimal _CloudReportPlugin-like mock."""
    plugin = MagicMock()
    plugin._session_start = None  # duration will be 0

    results = {}
    for i in range(passed):
        nid = f"tests/test_foo.py::test_pass_{i}"
        results[nid] = {
            "test_name": f"test_pass_{i}",
            "nodeid": nid,
            "file_path": "tests/test_foo.py",
            "status": "passed",
            "duration_ms": 100,
            "error_message": None,
        }
    for i in range(failed):
        nid = f"tests/test_foo.py::test_fail_{i}"
        results[nid] = {
            "test_name": f"test_fail_{i}",
            "nodeid": nid,
            "file_path": "tests/test_foo.py",
            "status": "failed",
            "duration_ms": 500,
            "error_message": f"AssertionError: expected True got False (test {i})",
        }
    for i in range(skipped):
        nid = f"tests/test_foo.py::test_skip_{i}"
        results[nid] = {
            "test_name": f"test_skip_{i}",
            "nodeid": nid,
            "file_path": "tests/test_foo.py",
            "status": "skipped",
            "duration_ms": None,
            "error_message": None,
        }

    plugin._results = results
    return plugin


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_collect_run_data_keys_and_types():
    plugin = _make_plugin(passed=5, failed=2, skipped=1)
    data = collect_run_data(plugin)

    assert isinstance(data["project_path"], str)
    assert data["total"] == 8
    assert data["passed"] == 5
    assert data["failed"] == 2
    assert data["skipped"] == 1
    assert isinstance(data["duration_s"], float)
    assert isinstance(data["created_at"], str)
    assert len(data["failed_tests"]) == 2
    assert all(
        k in data["failed_tests"][0]
        for k in ("name", "duration_ms", "error_message")
    )


def test_save_and_load_sqlite(tmp_path, monkeypatch):
    db_path = tmp_path / "history.db"
    monkeypatch.setattr(
        "pytest_cloudreport.local_report._DB_DIR", tmp_path
    )
    monkeypatch.setattr(
        "pytest_cloudreport.local_report._DB_PATH", db_path
    )

    plugin = _make_plugin(passed=10, failed=1, skipped=0)
    run_data = collect_run_data(plugin)
    run_data["project_path"] = "/test/project"

    save_to_sqlite(run_data)

    history = get_history("/test/project", limit=10)
    assert len(history) == 1
    assert history[0]["total"] == 11
    assert history[0]["passed"] == 10
    assert history[0]["failed"] == 1
    assert history[0]["project_path"] == "/test/project"


def test_sqlite_filters_by_project(tmp_path, monkeypatch):
    db_path = tmp_path / "history.db"
    monkeypatch.setattr("pytest_cloudreport.local_report._DB_DIR", tmp_path)
    monkeypatch.setattr("pytest_cloudreport.local_report._DB_PATH", db_path)

    plugin = _make_plugin()
    run_data = collect_run_data(plugin)

    run_data["project_path"] = "/projects/alpha"
    save_to_sqlite(run_data)

    run_data["project_path"] = "/projects/beta"
    save_to_sqlite(run_data)

    alpha_history = get_history("/projects/alpha")
    beta_history  = get_history("/projects/beta")
    other_history = get_history("/projects/gamma")

    assert len(alpha_history) == 1
    assert len(beta_history) == 1
    assert len(other_history) == 0


def test_generate_html_no_history():
    plugin = _make_plugin(passed=10, failed=2, skipped=1)
    run_data = collect_run_data(plugin)
    html = generate_html(run_data, history=[])

    assert "pytest-cloudreport" in html
    assert str(run_data["total"]) in html
    assert "%" in html
    assert "Chart.js" in html or "chart.js" in html
    # No history table
    assert "Run history" not in html
    assert "Want history across machines?" in html


def test_generate_html_with_history(tmp_path, monkeypatch):
    db_path = tmp_path / "history.db"
    monkeypatch.setattr("pytest_cloudreport.local_report._DB_DIR", tmp_path)
    monkeypatch.setattr("pytest_cloudreport.local_report._DB_PATH", db_path)

    plugin = _make_plugin(passed=9, failed=1, skipped=0)
    run_data = collect_run_data(plugin)
    run_data["project_path"] = "/test/project"

    # Save 3 runs to build history
    for _ in range(3):
        save_to_sqlite(run_data)

    history = get_history("/test/project", limit=10)
    html = generate_html(run_data, history=history)

    assert len(history) == 3
    assert "chart" in html.lower()
    # History section should mention run dates or pass rates
    assert "%" in html


def test_generate_html_no_failures():
    plugin = _make_plugin(passed=10, failed=0, skipped=0)
    run_data = collect_run_data(plugin)
    html = generate_html(run_data, history=[])

    assert "All tests passed" in html


def test_generate_html_hides_cloud_cta_when_api_key_present(monkeypatch):
    plugin = _make_plugin(passed=4, failed=0, skipped=0)
    run_data = collect_run_data(plugin)
    monkeypatch.setenv("PYTEST_CLOUD_API_KEY", "pcr_test_key")

    html = generate_html(run_data, history=[])

    assert "Want history across machines?" not in html


def test_accumulate_without_local_flag_prints_warning(pytester):
    """
    When --accumulate is passed without --cloudreport-local, the plugin
    prints a warning and exits cleanly (does not crash, does not write files).
    """
    pytester.makepyfile("""
        def test_dummy():
            assert True
    """)
    result = pytester.runpytest("--accumulate")
    result.stdout.fnmatch_lines([
        "*--accumulate requires --cloudreport-local*"
    ])
    assert result.ret == 0


def test_open_report_writes_file(tmp_path):
    output = tmp_path / "cloudreport.html"
    with patch("webbrowser.open"):
        open_report("<html>test</html>", output_path=str(output))

    assert output.exists()
    assert "<html>test</html>" in output.read_text(encoding="utf-8")
