"""Universal test runner supporting multiple frameworks."""
from __future__ import annotations

import enum
import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


class TestStatus(enum.Enum):
    """Status of an individual test."""
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    RUNNING = "running"
    PENDING = "pending"


class TestFramework(enum.Enum):
    """Supported test frameworks."""
    PYTEST = "pytest"
    JEST = "jest"
    CARGO_TEST = "cargo_test"
    GO_TEST = "go_test"
    JUNIT = "junit"
    DOTNET_TEST = "dotnet_test"
    SWIFT_TEST = "swift_test"


@dataclass
class TestResult:
    """Result of a single test execution."""
    name: str
    status: TestStatus
    duration: float = 0.0
    message: str = ""
    file: str = ""
    line: int = 0
    stdout: str = ""
    stderr: str = ""


@dataclass
class TestSuite:
    """Collection of test results."""
    name: str
    tests: list[TestResult] = field(default_factory=list)
    duration: float = 0.0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0

    def add_result(self, result: TestResult) -> None:
        self.tests.append(result)
        if result.status == TestStatus.PASSED:
            self.passed += 1
        elif result.status == TestStatus.FAILED:
            self.failed += 1
        elif result.status == TestStatus.ERROR:
            self.errors += 1
        elif result.status == TestStatus.SKIPPED:
            self.skipped += 1

    @property
    def total(self) -> int:
        return len(self.tests)

    @property
    def success_rate(self) -> float:
        return (self.passed / self.total * 100.0) if self.total else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "tests": [
                {
                    "name": t.name,
                    "status": t.status.value,
                    "duration": t.duration,
                    "message": t.message,
                    "file": t.file,
                    "line": t.line,
                }
                for t in self.tests
            ],
            "duration": self.duration,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "skipped": self.skipped,
            "total": self.total,
            "success_rate": self.success_rate,
        }


@dataclass
class CoverageResult:
    """Code coverage information."""
    total_lines: int = 0
    covered_lines: int = 0
    percentage: float = 0.0
    uncovered_ranges: list[tuple[int, int]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_lines": self.total_lines,
            "covered_lines": self.covered_lines,
            "percentage": self.percentage,
            "uncovered_ranges": self.uncovered_ranges,
        }


# ---------------------------------------------------------------------------
# Framework-specific command builders and parsers
# ---------------------------------------------------------------------------

_FRAMEWORK_COMMANDS: dict[TestFramework, dict[str, Any]] = {
    TestFramework.PYTEST: {
        "run_all": ["python", "-m", "pytest", "-v", "--tb=short"],
        "run_file": ["python", "-m", "pytest", "-v", "--tb=short"],
        "run_test": ["python", "-m", "pytest", "-v", "--tb=short", "-k"],
        "coverage": ["python", "-m", "pytest", "--cov", "--cov-report=json", "-v"],
        "discover": ["python", "-m", "pytest", "--collect-only", "-q"],
        "indicator_files": ["pytest.ini", "pyproject.toml", "setup.cfg", "conftest.py"],
    },
    TestFramework.JEST: {
        "run_all": ["npx", "jest", "--verbose"],
        "run_file": ["npx", "jest", "--verbose"],
        "run_test": ["npx", "jest", "--verbose", "-t"],
        "coverage": ["npx", "jest", "--coverage", "--verbose"],
        "discover": ["npx", "jest", "--listTests"],
        "indicator_files": ["jest.config.js", "jest.config.ts", "jest.config.mjs"],
    },
    TestFramework.CARGO_TEST: {
        "run_all": ["cargo", "test"],
        "run_file": ["cargo", "test"],
        "run_test": ["cargo", "test"],
        "coverage": ["cargo", "tarpaulin", "--out", "Json"],
        "discover": ["cargo", "test", "--", "--list"],
        "indicator_files": ["Cargo.toml"],
    },
    TestFramework.GO_TEST: {
        "run_all": ["go", "test", "-v", "./..."],
        "run_file": ["go", "test", "-v"],
        "run_test": ["go", "test", "-v", "-run"],
        "coverage": ["go", "test", "-v", "-coverprofile=coverage.out", "./..."],
        "discover": ["go", "test", "-list", ".", "./..."],
        "indicator_files": ["go.mod"],
    },
    TestFramework.JUNIT: {
        "run_all": ["mvn", "test"],
        "run_file": ["mvn", "test", "-Dtest="],
        "run_test": ["mvn", "test", "-Dtest="],
        "coverage": ["mvn", "test", "-Djacoco"],
        "discover": ["mvn", "test", "-Dsurefire.useFile=false", "-DdryRun=true"],
        "indicator_files": ["pom.xml", "build.gradle", "build.gradle.kts"],
    },
    TestFramework.DOTNET_TEST: {
        "run_all": ["dotnet", "test", "--verbosity", "normal"],
        "run_file": ["dotnet", "test", "--filter"],
        "run_test": ["dotnet", "test", "--filter"],
        "coverage": ["dotnet", "test", '--collect:"XPlat Code Coverage"'],
        "discover": ["dotnet", "test", "--list-tests"],
        "indicator_files": ["*.csproj", "*.sln"],
    },
    TestFramework.SWIFT_TEST: {
        "run_all": ["swift", "test"],
        "run_file": ["swift", "test", "--filter"],
        "run_test": ["swift", "test", "--filter"],
        "coverage": ["swift", "test", "--enable-code-coverage"],
        "discover": ["swift", "test", "--list-tests"],
        "indicator_files": ["Package.swift"],
    },
}


class TestRunner:
    """Universal test runner that auto-detects and delegates to the right framework."""

    def __init__(self, workspace_path: str = ".") -> None:
        self.workspace = Path(workspace_path).resolve()
        self._framework: TestFramework | None = None
        self._history: list[TestSuite] = []
        self._watchers: list[Callable[[TestSuite], None]] = []

    # ------------------------------------------------------------------
    # Framework detection
    # ------------------------------------------------------------------

    def detect_framework(self) -> TestFramework | None:
        """Auto-detect the test framework based on project files."""
        if self._framework is not None:
            return self._framework

        for fw, meta in _FRAMEWORK_COMMANDS.items():
            for indicator in meta["indicator_files"]:
                if "*" in indicator:
                    if list(self.workspace.glob(indicator)):
                        self._framework = fw
                        return fw
                elif (self.workspace / indicator).exists():
                    if indicator == "pyproject.toml" and fw == TestFramework.PYTEST:
                        content = (self.workspace / indicator).read_text(errors="replace")
                        if "pytest" in content or "tool.pytest" in content:
                            self._framework = fw
                            return fw
                        continue
                    self._framework = fw
                    return fw
        return None

    # ------------------------------------------------------------------
    # Test discovery
    # ------------------------------------------------------------------

    def discover_tests(self) -> list[str]:
        """List all available tests without running them."""
        fw = self._ensure_framework()
        cmd = list(_FRAMEWORK_COMMANDS[fw]["discover"])
        result = self._exec(cmd)
        return [line for line in result.stdout.splitlines() if line.strip()]

    # ------------------------------------------------------------------
    # Running tests
    # ------------------------------------------------------------------

    def run_all(self) -> TestSuite:
        """Run the full test suite."""
        fw = self._ensure_framework()
        cmd = list(_FRAMEWORK_COMMANDS[fw]["run_all"])
        return self._run_and_parse(cmd, suite_name="all")

    def run_file(self, file_path: str) -> TestSuite:
        """Run tests in a specific file."""
        fw = self._ensure_framework()
        cmd = list(_FRAMEWORK_COMMANDS[fw]["run_file"])
        if fw in (TestFramework.PYTEST, TestFramework.JEST):
            cmd.append(file_path)
        elif fw == TestFramework.CARGO_TEST:
            module = Path(file_path).stem
            cmd.append(module)
        elif fw == TestFramework.GO_TEST:
            cmd[-1] = f"./{Path(file_path).parent}"
        elif fw == TestFramework.JUNIT:
            cls = Path(file_path).stem
            cmd[-1] = cmd[-1] + cls
        elif fw == TestFramework.DOTNET_TEST:
            cmd.append(f"FullyQualifiedName~{Path(file_path).stem}")
        elif fw == TestFramework.SWIFT_TEST:
            cmd.append(Path(file_path).stem)
        return self._run_and_parse(cmd, suite_name=file_path)

    def run_test(self, test_name: str) -> TestSuite:
        """Run a single test by name or pattern."""
        fw = self._ensure_framework()
        cmd = list(_FRAMEWORK_COMMANDS[fw]["run_test"])
        cmd.append(test_name)
        return self._run_and_parse(cmd, suite_name=test_name)

    def run_with_coverage(self) -> tuple[TestSuite, CoverageResult]:
        """Run tests and collect coverage data."""
        fw = self._ensure_framework()
        cmd = list(_FRAMEWORK_COMMANDS[fw]["coverage"])
        suite = self._run_and_parse(cmd, suite_name="coverage")
        coverage = self._parse_coverage(fw)
        return suite, coverage

    # ------------------------------------------------------------------
    # Watch mode
    # ------------------------------------------------------------------

    def watch(self, callback: Callable[[TestSuite], None] | None = None, interval: float = 2.0) -> None:
        """Watch for file changes and re-run tests. Blocks until interrupted."""
        import hashlib

        if callback:
            self._watchers.append(callback)

        snapshots: dict[str, str] = {}

        def _snapshot() -> dict[str, str]:
            snap: dict[str, str] = {}
            for p in self.workspace.rglob("*"):
                if p.is_file() and not any(
                    part.startswith(".") or part in ("node_modules", "__pycache__", "target", "bin", "obj")
                    for part in p.parts
                ):
                    try:
                        snap[str(p)] = hashlib.md5(p.read_bytes()).hexdigest()
                    except OSError:
                        pass
            return snap

        snapshots = _snapshot()
        try:
            while True:
                time.sleep(interval)
                new_snap = _snapshot()
                if new_snap != snapshots:
                    snapshots = new_snap
                    suite = self.run_all()
                    for cb in self._watchers:
                        cb(suite)
        except KeyboardInterrupt:
            pass

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_history(self) -> list[dict[str, Any]]:
        """Return past test suite results."""
        return [s.to_dict() for s in self._history]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_framework(self) -> TestFramework:
        fw = self.detect_framework()
        if fw is None:
            raise RuntimeError("No supported test framework detected in workspace.")
        return fw

    def _exec(self, cmd: list[str], timeout: int = 300) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            cmd,
            cwd=self.workspace,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def _run_and_parse(self, cmd: list[str], suite_name: str) -> TestSuite:
        start = time.monotonic()
        proc = self._exec(cmd)
        elapsed = time.monotonic() - start
        fw = self._framework or TestFramework.PYTEST
        suite = self._parse_output(fw, proc.stdout, proc.stderr, suite_name)
        suite.duration = elapsed
        self._history.append(suite)
        return suite

    def _parse_output(self, fw: TestFramework, stdout: str, stderr: str, suite_name: str) -> TestSuite:
        """Dispatch to framework-specific parser."""
        parser = {
            TestFramework.PYTEST: self._parse_pytest,
            TestFramework.JEST: self._parse_jest,
            TestFramework.CARGO_TEST: self._parse_cargo,
            TestFramework.GO_TEST: self._parse_go,
            TestFramework.JUNIT: self._parse_junit_mvn,
            TestFramework.DOTNET_TEST: self._parse_dotnet,
            TestFramework.SWIFT_TEST: self._parse_swift,
        }.get(fw, self._parse_generic)
        return parser(stdout, stderr, suite_name)

    # -- pytest ----------------------------------------------------------

    def _parse_pytest(self, stdout: str, stderr: str, suite_name: str) -> TestSuite:
        suite = TestSuite(name=suite_name)
        pattern = re.compile(
            r"^(?P<file>[^\s:]+)::(?P<name>\S+)\s+(?P<status>PASSED|FAILED|ERROR|SKIPPED)",
            re.MULTILINE,
        )
        for m in pattern.finditer(stdout):
            status_map = {
                "PASSED": TestStatus.PASSED,
                "FAILED": TestStatus.FAILED,
                "ERROR": TestStatus.ERROR,
                "SKIPPED": TestStatus.SKIPPED,
            }
            suite.add_result(
                TestResult(
                    name=m.group("name"),
                    status=status_map.get(m.group("status"), TestStatus.ERROR),
                    file=m.group("file"),
                    stdout=stdout,
                    stderr=stderr,
                )
            )
        if not suite.tests:
            self._fallback_summary(suite, stdout, stderr)
        return suite

    # -- jest -------------------------------------------------------------

    def _parse_jest(self, stdout: str, stderr: str, suite_name: str) -> TestSuite:
        suite = TestSuite(name=suite_name)
        combined = stdout + "\n" + stderr
        pattern = re.compile(
            r"^\s*(?P<icon>[✓✕✗●])\s+(?P<name>.+?)(?:\s+\((?P<dur>\d+)\s*m?s\))?\s*$",
            re.MULTILINE,
        )
        for m in pattern.finditer(combined):
            icon = m.group("icon")
            status = TestStatus.PASSED if icon == "\u2713" else TestStatus.FAILED
            dur = float(m.group("dur") or 0) / 1000.0
            suite.add_result(TestResult(name=m.group("name").strip(), status=status, duration=dur))
        if not suite.tests:
            self._fallback_summary(suite, stdout, stderr)
        return suite

    # -- cargo test -------------------------------------------------------

    def _parse_cargo(self, stdout: str, stderr: str, suite_name: str) -> TestSuite:
        suite = TestSuite(name=suite_name)
        pattern = re.compile(r"^test\s+(?P<name>\S+)\s+\.\.\.\s+(?P<status>ok|FAILED|ignored)", re.MULTILINE)
        for m in pattern.finditer(stdout):
            status_map = {"ok": TestStatus.PASSED, "FAILED": TestStatus.FAILED, "ignored": TestStatus.SKIPPED}
            suite.add_result(
                TestResult(name=m.group("name"), status=status_map.get(m.group("status"), TestStatus.ERROR))
            )
        if not suite.tests:
            self._fallback_summary(suite, stdout, stderr)
        return suite

    # -- go test ----------------------------------------------------------

    def _parse_go(self, stdout: str, stderr: str, suite_name: str) -> TestSuite:
        suite = TestSuite(name=suite_name)
        pattern = re.compile(
            r"^---\s+(?P<status>PASS|FAIL|SKIP):\s+(?P<name>\S+)\s+\((?P<dur>[\d.]+)s\)",
            re.MULTILINE,
        )
        for m in pattern.finditer(stdout):
            status_map = {"PASS": TestStatus.PASSED, "FAIL": TestStatus.FAILED, "SKIP": TestStatus.SKIPPED}
            suite.add_result(
                TestResult(
                    name=m.group("name"),
                    status=status_map.get(m.group("status"), TestStatus.ERROR),
                    duration=float(m.group("dur")),
                )
            )
        if not suite.tests:
            self._fallback_summary(suite, stdout, stderr)
        return suite

    # -- junit (mvn) ------------------------------------------------------

    def _parse_junit_mvn(self, stdout: str, stderr: str, suite_name: str) -> TestSuite:
        suite = TestSuite(name=suite_name)
        summary = re.search(
            r"Tests run:\s*(?P<total>\d+),\s*Failures:\s*(?P<fail>\d+),\s*Errors:\s*(?P<err>\d+),\s*Skipped:\s*(?P<skip>\d+)",
            stdout,
        )
        if summary:
            total = int(summary.group("total"))
            failed = int(summary.group("fail"))
            errors = int(summary.group("err"))
            skipped = int(summary.group("skip"))
            passed = total - failed - errors - skipped
            for i in range(passed):
                suite.add_result(TestResult(name=f"test_{i + 1}", status=TestStatus.PASSED))
            for i in range(failed):
                suite.add_result(TestResult(name=f"failed_{i + 1}", status=TestStatus.FAILED))
            for i in range(errors):
                suite.add_result(TestResult(name=f"error_{i + 1}", status=TestStatus.ERROR))
            for i in range(skipped):
                suite.add_result(TestResult(name=f"skipped_{i + 1}", status=TestStatus.SKIPPED))
        return suite

    # -- dotnet test -------------------------------------------------------

    def _parse_dotnet(self, stdout: str, stderr: str, suite_name: str) -> TestSuite:
        suite = TestSuite(name=suite_name)
        pattern = re.compile(r"^\s*(?P<status>Passed|Failed|Skipped)\s+(?P<name>\S+)", re.MULTILINE)
        for m in pattern.finditer(stdout):
            status_map = {"Passed": TestStatus.PASSED, "Failed": TestStatus.FAILED, "Skipped": TestStatus.SKIPPED}
            suite.add_result(
                TestResult(name=m.group("name"), status=status_map.get(m.group("status"), TestStatus.ERROR))
            )
        if not suite.tests:
            self._fallback_summary(suite, stdout, stderr)
        return suite

    # -- swift test -------------------------------------------------------

    def _parse_swift(self, stdout: str, stderr: str, suite_name: str) -> TestSuite:
        suite = TestSuite(name=suite_name)
        pattern = re.compile(
            r"^Test Case\s+'-\[(?P<name>[^\]]+)\]'\s+(?P<status>passed|failed)\s+\((?P<dur>[\d.]+)\s+seconds\)",
            re.MULTILINE,
        )
        for m in pattern.finditer(stdout + "\n" + stderr):
            status = TestStatus.PASSED if m.group("status") == "passed" else TestStatus.FAILED
            suite.add_result(
                TestResult(name=m.group("name"), status=status, duration=float(m.group("dur")))
            )
        if not suite.tests:
            self._fallback_summary(suite, stdout, stderr)
        return suite

    # -- generic / fallback ------------------------------------------------

    def _parse_generic(self, stdout: str, stderr: str, suite_name: str) -> TestSuite:
        suite = TestSuite(name=suite_name)
        self._fallback_summary(suite, stdout, stderr)
        return suite

    @staticmethod
    def _fallback_summary(suite: TestSuite, stdout: str, stderr: str) -> None:
        """Create a single synthetic result when individual parsing fails."""
        combined = stdout + stderr
        if any(kw in combined.lower() for kw in ("passed", "ok", "success")):
            suite.add_result(TestResult(name="(summary)", status=TestStatus.PASSED, stdout=stdout, stderr=stderr))
        elif any(kw in combined.lower() for kw in ("failed", "failure", "error")):
            suite.add_result(TestResult(name="(summary)", status=TestStatus.FAILED, stdout=stdout, stderr=stderr))

    # -- coverage ----------------------------------------------------------

    def _parse_coverage(self, fw: TestFramework) -> CoverageResult:
        """Attempt to read coverage output generated by the framework."""
        cov = CoverageResult()
        if fw == TestFramework.PYTEST:
            cov_file = self.workspace / "coverage.json"
            if cov_file.exists():
                try:
                    data = json.loads(cov_file.read_text())
                    totals = data.get("totals", {})
                    cov.total_lines = totals.get("num_statements", 0)
                    cov.covered_lines = totals.get("covered_lines", 0)
                    cov.percentage = totals.get("percent_covered", 0.0)
                except (json.JSONDecodeError, KeyError):
                    pass
        elif fw == TestFramework.GO_TEST:
            cov_file = self.workspace / "coverage.out"
            if cov_file.exists():
                lines = cov_file.read_text().splitlines()
                total = covered = 0
                for line in lines[1:]:
                    parts = line.rsplit(" ", 2)
                    if len(parts) >= 3:
                        stmts = int(parts[-2])
                        count = int(parts[-1])
                        total += stmts
                        if count > 0:
                            covered += stmts
                cov.total_lines = total
                cov.covered_lines = covered
                cov.percentage = (covered / total * 100.0) if total else 0.0
        return cov
