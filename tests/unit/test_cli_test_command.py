"""Tests for the ``EoStudio test`` command.

The command drives the real ``TestRunner``; only ``TestRunner._exec`` (the
subprocess call) is replaced, so a mismatch between the CLI and the runner's
API still fails here.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from eostudio.cli.main import cli
from eostudio.core.devtools import testing as devtools_testing

PYTEST_OUTPUT = (
    "tests/test_x.py::test_ok PASSED\ntests/test_x.py::test_skip SKIPPED\ntests/test_x.py::test_bad FAILED\n"
)


def _workspace(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text('[tool.pytest.ini_options]\ntestpaths = ["tests"]\n')
    return tmp_path


def _fake_exec(stdout: str, calls: list):
    def _exec(self, cmd, timeout=300):
        calls.append((self.workspace, cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    return _exec


def test_run_all_reports_counts_and_fails_on_failures(tmp_path):
    ws = _workspace(tmp_path)
    calls: list = []
    with mock.patch.object(devtools_testing.TestRunner, "_exec", _fake_exec(PYTEST_OUTPUT, calls)):
        result = CliRunner().invoke(cli, ["test", str(ws)])

    assert result.exception is None or isinstance(result.exception, SystemExit), result.exception
    assert result.exit_code == 1, result.output
    assert "Test framework: pytest" in result.output
    assert "Passed : 1" in result.output
    assert "Failed : 1" in result.output
    assert "Skipped: 1" in result.output
    # The runner is bound to the given path, not the current directory.
    assert calls and calls[0][0] == ws.resolve()


def test_run_all_exits_zero_when_everything_passes(tmp_path):
    ws = _workspace(tmp_path)
    calls: list = []
    with mock.patch.object(
        devtools_testing.TestRunner, "_exec", _fake_exec("tests/test_x.py::test_ok PASSED\n", calls)
    ):
        result = CliRunner().invoke(cli, ["test", str(ws)])

    assert result.exit_code == 0, result.output
    assert "Passed : 1" in result.output


def test_single_file_is_passed_to_the_runner(tmp_path):
    ws = _workspace(tmp_path)
    calls: list = []
    with mock.patch.object(
        devtools_testing.TestRunner, "_exec", _fake_exec("tests/test_x.py::test_ok PASSED\n", calls)
    ):
        result = CliRunner().invoke(cli, ["test", str(ws), "--file", "tests/test_x.py"])

    assert result.exit_code == 0, result.output
    assert calls[0][1][-1] == "tests/test_x.py"


def test_coverage_prints_percentage(tmp_path):
    ws = _workspace(tmp_path)
    (ws / "coverage.json").write_text(
        json.dumps({"totals": {"num_statements": 200, "covered_lines": 150, "percent_covered": 75.0}})
    )
    calls: list = []
    with mock.patch.object(
        devtools_testing.TestRunner, "_exec", _fake_exec("tests/test_x.py::test_ok PASSED\n", calls)
    ):
        result = CliRunner().invoke(cli, ["test", str(ws), "--coverage"])

    assert result.exit_code == 0, result.output
    assert "Coverage: 75.0%" in result.output
    assert "--cov" in calls[0][1]


def test_coverage_not_read_is_reported_as_unavailable(tmp_path):
    # The runner reads no coverage data for jest, so it must not print 0.0%.
    (tmp_path / "jest.config.js").write_text("module.exports = {};\n")
    calls: list = []
    with mock.patch.object(devtools_testing.TestRunner, "_exec", _fake_exec("Tests: 1 passed, 1 total\n", calls)):
        result = CliRunner().invoke(cli, ["test", str(tmp_path), "--coverage"])

    assert result.exit_code == 0, result.output
    assert "Test framework: jest" in result.output
    assert "Coverage: not available for jest" in result.output
    assert "0.0%" not in result.output


def test_missing_test_tool_is_a_clear_error(tmp_path):
    ws = _workspace(tmp_path)

    def _exec(self, cmd, timeout=300):
        raise FileNotFoundError(2, "No such file or directory", cmd[0])

    with mock.patch.object(devtools_testing.TestRunner, "_exec", _exec):
        result = CliRunner().invoke(cli, ["test", str(ws)])

    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, SystemExit)
    assert "Error: could not run pytest tests:" in result.output
    assert "No such file or directory" in result.output


def test_test_tool_timeout_is_a_clear_error(tmp_path):
    ws = _workspace(tmp_path)

    def _exec(self, cmd, timeout=300):
        raise subprocess.TimeoutExpired(cmd, timeout)

    with mock.patch.object(devtools_testing.TestRunner, "_exec", _exec):
        result = CliRunner().invoke(cli, ["test", str(ws)])

    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, SystemExit)
    assert "Error: could not run pytest tests:" in result.output
    assert "timed out" in result.output


def test_watch_passes_a_summary_callback(tmp_path, capsys):
    ws = _workspace(tmp_path)
    with mock.patch.object(devtools_testing.TestRunner, "watch", autospec=True) as watch:
        result = CliRunner().invoke(cli, ["test", str(ws), "--watch"])

    assert result.exit_code == 0, result.output
    assert "Watching for changes" in result.output
    watch.assert_called_once()
    callback = watch.call_args.kwargs["callback"]

    suite = devtools_testing.TestSuite(name="all", passed=3, failed=1)
    callback(suite)
    printed = capsys.readouterr().out
    assert "Passed : 3" in printed
    assert "Failed : 1" in printed


def test_no_framework_is_a_clear_error(tmp_path):
    result = CliRunner().invoke(cli, ["test", str(tmp_path)])

    assert result.exit_code == 1, result.output
    assert isinstance(result.exception, SystemExit)
    assert "no supported test framework detected" in result.output


def test_missing_directory_is_reported_as_missing(tmp_path):
    result = CliRunner().invoke(cli, ["test", str(tmp_path / "does-not-exist")])

    assert result.exit_code == 2, result.output
    assert "does not exist" in result.output
    assert "no supported test framework" not in result.output
