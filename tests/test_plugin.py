from unittest.mock import MagicMock

from pytest_cloudreport import _CloudReportPlugin


def _make_report(
    *,
    when: str,
    failed: bool = False,
    passed: bool = False,
    skipped: bool = False,
    longrepr=None,
):
    report = MagicMock()
    report.when = when
    report.failed = failed
    report.passed = passed
    report.skipped = skipped
    report.longrepr = longrepr
    report.nodeid = "tests/test_sample.py::test_case"
    report.duration = 0.01
    report.rerun = 0  # prevent MagicMock truthiness from tripping the retry-skip guard
    return report


def test_teardown_failure_overrides_previous_pass_result():
    plugin = _CloudReportPlugin("key", "https://api.example.com", "ci", False)

    plugin.pytest_runtest_logreport(_make_report(when="call", passed=True))
    plugin.pytest_runtest_logreport(
        _make_report(when="teardown", failed=True, longrepr="teardown exploded")
    )

    result = plugin._results["tests/test_sample.py::test_case"]
    assert result["status"] == "error"
    assert result["error_message"] == "teardown exploded"


def test_teardown_failure_overrides_previous_skipped_result():
    plugin = _CloudReportPlugin("key", "https://api.example.com", "ci", False)

    plugin.pytest_runtest_logreport(_make_report(when="setup", skipped=True))
    plugin.pytest_runtest_logreport(
        _make_report(when="teardown", failed=True, longrepr="fixture cleanup failed")
    )

    result = plugin._results["tests/test_sample.py::test_case"]
    assert result["status"] == "error"
    assert result["error_message"] == "fixture cleanup failed"


def test_session_finish_waits_for_upload_thread(mocker):
    plugin = _CloudReportPlugin("key", "https://api.example.com", "ci", False)
    plugin._results = {
        "tests/test_sample.py::test_case": {
            "test_name": "test_case",
            "nodeid": "tests/test_sample.py::test_case",
            "file_path": "tests/test_sample.py",
            "status": "passed",
            "duration_ms": 10,
            "error_message": None,
        }
    }
    start_mock = mocker.patch("pytest_cloudreport.threading.Thread.start")
    join_mock = mocker.patch("pytest_cloudreport.threading.Thread.join")

    plugin.pytest_sessionfinish(MagicMock(), 0)

    start_mock.assert_called_once()
    join_mock.assert_called_once_with(timeout=30)


def test_session_finish_announces_local_and_cloud_mode(capsys, mocker):
    plugin = _CloudReportPlugin("key", "https://api.example.com", "ci", False)
    plugin._results = {
        "tests/test_sample.py::test_case": {
            "test_name": "test_case",
            "nodeid": "tests/test_sample.py::test_case",
            "file_path": "tests/test_sample.py",
            "status": "passed",
            "duration_ms": 10,
            "error_message": None,
        }
    }

    session = MagicMock()
    session.config.getoption.side_effect = lambda name, default=False: {
        "--cloudreport-local": True,
        "--accumulate": False,
    }.get(name, default)

    mocker.patch("pytest_cloudreport.threading.Thread.start")
    mocker.patch("pytest_cloudreport.threading.Thread.join")
    mocker.patch("pytest_cloudreport.local_report.collect_run_data", return_value={"project_path": "/tmp/project"})
    mocker.patch("pytest_cloudreport.local_report.generate_html", return_value="<html></html>")
    mocker.patch("pytest_cloudreport.local_report.open_report")

    plugin.pytest_sessionfinish(session, 0)

    out = capsys.readouterr().out
    assert "Local report enabled; cloud upload also active because an API key is configured." in out
