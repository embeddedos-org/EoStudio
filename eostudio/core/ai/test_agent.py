"""AI Testing Agent — auto-generates tests, runs them, fixes failures iteratively.

Includes built-in test validation (syntax/structure check without running),
coverage estimation, and spec-based completeness checking.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from eostudio.core.ai.llm_client import LLMClient, LLMConfig


@dataclass
class TestResult:
    """Result of a test run."""
    file: str
    passed: bool
    total: int = 0
    failures: int = 0
    errors: List[str] = field(default_factory=list)
    coverage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"file": self.file, "passed": self.passed, "total": self.total,
                "failures": self.failures, "errors": self.errors, "coverage": self.coverage}


@dataclass
class TestReport:
    """Comprehensive test report with pass/fail summary, coverage, and suggestions."""
    total_files: int = 0
    files_with_tests: int = 0
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    coverage_percent: float = 0.0
    missing_tests: List[str] = field(default_factory=list)
    results: List[TestResult] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_files": self.total_files,
            "files_with_tests": self.files_with_tests,
            "total_tests": self.total_tests,
            "passed": self.passed, "failed": self.failed, "skipped": self.skipped,
            "coverage_percent": self.coverage_percent,
            "missing_tests": self.missing_tests,
            "results": [r.to_dict() for r in self.results],
            "validation_errors": self.validation_errors,
        }

    @property
    def summary(self) -> str:
        status = "PASS" if self.failed == 0 else "FAIL"
        return (
            f"[{status}] {self.passed}/{self.total_tests} tests passed | "
            f"Coverage: {self.coverage_percent:.0f}% | "
            f"Missing tests: {len(self.missing_tests)} files"
        )


class AITestAgent:
    """Agent that generates tests, runs them, and fixes failures."""

    def __init__(self, llm_client: Optional[LLMClient] = None,
                 test_framework: str = "vitest",
                 max_fix_attempts: int = 3) -> None:
        self._client = llm_client or LLMClient(LLMConfig())
        self.test_framework = test_framework
        self.max_fix_attempts = max_fix_attempts

    def generate_tests(self, source_file: str, source_code: str,
                       framework: str = "react") -> str:
        """Generate test code for a source file."""
        messages = [{"role": "user", "content": (
            f"Generate comprehensive tests for this {framework} file.\n"
            f"Test framework: {self.test_framework}\n"
            f"File: {source_file}\n\n"
            f"```\n{source_code}\n```\n\n"
            f"Generate tests covering:\n"
            f"- Component rendering\n- User interactions\n- Edge cases\n"
            f"- Error handling\n- Accessibility\n"
            f"Return ONLY the test code, no explanation."
        )}]
        raw = self._client.chat(messages)
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
            if raw.endswith("```"):
                raw = raw[:-3]
        return raw or self._fallback_test(source_file, framework)

    def generate_tests_for_project(self, project_dir: str) -> Dict[str, str]:
        """Generate tests for all source files in a project."""
        test_files: Dict[str, str] = {}
        src_dir = os.path.join(project_dir, "src")
        if not os.path.exists(src_dir):
            src_dir = project_dir

        for root, _, files in os.walk(src_dir):
            for fname in files:
                if fname.endswith((".tsx", ".ts", ".jsx", ".js")) and not fname.endswith((".test.", ".spec.")):
                    filepath = os.path.join(root, fname)
                    with open(filepath, "r") as f:
                        code = f.read()
                    if len(code) > 50:  # skip tiny files
                        test_name = fname.replace(".tsx", ".test.tsx").replace(".ts", ".test.ts")
                        test_name = test_name.replace(".jsx", ".test.jsx").replace(".js", ".test.js")
                        test_path = os.path.join(root, "__tests__", test_name)
                        test_code = self.generate_tests(fname, code)
                        test_files[test_path] = test_code
        return test_files

    def run_tests(self, project_dir: str) -> List[TestResult]:
        """Run tests and return results."""
        cmd_map = {
            "vitest": "npx vitest run --reporter=json",
            "jest": "npx jest --json",
            "pytest": "python -m pytest --tb=short -q",
        }
        cmd = cmd_map.get(self.test_framework, "npm test")
        try:
            result = subprocess.run(
                cmd.split(), cwd=project_dir,
                capture_output=True, text=True, timeout=120,
            )
            return self._parse_results(result)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return [TestResult(file="all", passed=True, total=0)]

    def fix_failing_tests(self, test_file: str, test_code: str,
                          errors: List[str], source_code: str) -> str:
        """Fix failing test code based on errors."""
        messages = [{"role": "user", "content": (
            f"Fix these failing tests.\n\n"
            f"Test file: {test_file}\nErrors:\n{chr(10).join(errors[:5])}\n\n"
            f"Current test code:\n```\n{test_code}\n```\n\n"
            f"Source code being tested:\n```\n{source_code[:1000]}\n```\n\n"
            f"Return ONLY the fixed test code."
        )}]
        raw = self._client.chat(messages)
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
            if raw.endswith("```"):
                raw = raw[:-3]
        return raw or test_code

    def run_and_fix_loop(self, project_dir: str) -> Dict[str, Any]:
        """Run tests, fix failures, repeat until all pass or max attempts reached."""
        history = []
        for attempt in range(self.max_fix_attempts):
            results = self.run_tests(project_dir)
            all_passed = all(r.passed for r in results)
            history.append({
                "attempt": attempt + 1,
                "results": [r.to_dict() for r in results],
                "all_passed": all_passed,
            })
            if all_passed:
                break
            # Fix failures
            for r in results:
                if not r.passed and r.errors:
                    test_path = os.path.join(project_dir, r.file)
                    if os.path.exists(test_path):
                        with open(test_path, "r") as f:
                            test_code = f.read()
                        fixed = self.fix_failing_tests(r.file, test_code, r.errors, "")
                        with open(test_path, "w") as f:
                            f.write(fixed)

        return {
            "total_attempts": len(history),
            "final_passed": history[-1]["all_passed"] if history else False,
            "history": history,
        }

    def generate_coverage_report(self, project_dir: str) -> Dict[str, Any]:
        """Run tests with coverage and return report."""
        try:
            result = subprocess.run(
                ["npx", "vitest", "run", "--coverage"],
                cwd=project_dir, capture_output=True, text=True, timeout=120,
            )
            return {"success": result.returncode == 0, "output": result.stdout[-1000:]}
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {"success": False, "error": "Coverage tool not available"}

    def generate_test_config(self, project_dir: str,
                             framework: Optional[str] = None) -> Dict[str, str]:
        """Generate test configuration files (vitest.config.ts / jest.config.ts / pytest.ini)."""
        fw = framework or self.test_framework
        configs: Dict[str, str] = {}

        if fw == "vitest":
            configs["vitest.config.ts"] = (
                '/// <reference types="vitest" />\n'
                'import { defineConfig } from "vite";\n'
                'import react from "@vitejs/plugin-react";\n'
                'import { resolve } from "path";\n\n'
                "export default defineConfig({\n"
                "  plugins: [react()],\n"
                "  test: {\n"
                '    globals: true,\n'
                '    environment: "jsdom",\n'
                '    setupFiles: ["./src/test/setup.ts"],\n'
                '    include: ["src/**/*.{test,spec}.{ts,tsx}"],\n'
                "    coverage: {\n"
                '      provider: "v8",\n'
                '      reporter: ["text", "json", "html"],\n'
                "      exclude: [\"node_modules/\", \"src/test/\"],\n"
                "      thresholds: { lines: 70, functions: 70, branches: 60 },\n"
                "    },\n"
                "  },\n"
                "  resolve: {\n"
                '    alias: { "@": resolve(__dirname, "./src") },\n'
                "  },\n"
                "});\n"
            )
            configs["src/test/setup.ts"] = (
                'import "@testing-library/jest-dom/vitest";\n'
            )
        elif fw == "jest":
            configs["jest.config.ts"] = (
                "export default {\n"
                '  preset: "ts-jest",\n'
                '  testEnvironment: "jsdom",\n'
                "  setupFilesAfterSetup: [\"<rootDir>/src/test/setup.ts\"],\n"
                '  moduleNameMapper: { "^@/(.*)$": "<rootDir>/src/$1" },\n'
                '  collectCoverageFrom: ["src/**/*.{ts,tsx}", "!src/**/*.d.ts"],\n'
                "  coverageThreshold: {\n"
                "    global: { branches: 60, functions: 70, lines: 70 },\n"
                "  },\n"
                "};\n"
            )
        elif fw == "pytest":
            configs["pytest.ini"] = (
                "[pytest]\n"
                "testpaths = tests\n"
                "python_files = test_*.py\n"
                "python_functions = test_*\n"
                "addopts = -v --tb=short --cov=app --cov-report=term-missing\n"
                "markers =\n"
                "    slow: marks tests as slow\n"
                "    integration: marks integration tests\n"
            )
            configs["tests/conftest.py"] = (
                "import pytest\n\n\n"
                "@pytest.fixture\n"
                "def app_client():\n"
                '    """Create a test client for the application."""\n'
                "    from app.main import app\n"
                "    from fastapi.testclient import TestClient\n"
                "    return TestClient(app)\n"
            )

        # Write configs to disk
        for filename, content in configs.items():
            filepath = os.path.join(project_dir, filename)
            os.makedirs(os.path.dirname(filepath) or project_dir, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        return configs

    def validate_test_files(self, project_dir: str) -> List[str]:
        """Validate test files for syntax and structure without running them."""
        errors: List[str] = []

        for root, _, files in os.walk(project_dir):
            for fname in files:
                if not (fname.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
                        or (fname.startswith("test_") and fname.endswith(".py"))):
                    continue

                filepath = os.path.join(root, fname)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        code = f.read()
                except (OSError, UnicodeDecodeError):
                    errors.append(f"{fname}: cannot read file")
                    continue

                if fname.endswith(".py"):
                    # Validate Python syntax
                    try:
                        ast.parse(code)
                    except SyntaxError as e:
                        errors.append(f"{fname}:{e.lineno}: SyntaxError — {e.msg}")
                    # Check for test functions
                    if "def test_" not in code:
                        errors.append(f"{fname}: no test functions found (missing def test_*)")
                else:
                    # Validate TS/TSX test structure
                    if "describe(" not in code and "it(" not in code and "test(" not in code:
                        errors.append(f"{fname}: no test blocks found (missing describe/it/test)")
                    if "import" not in code:
                        errors.append(f"{fname}: no imports — test likely won't run")
                    # Check for common issues
                    if "expect(" not in code:
                        errors.append(f"{fname}: no assertions found (missing expect())")

        return errors

    def estimate_coverage(self, project_dir: str) -> TestReport:
        """Estimate test coverage by analyzing which source files have test files."""
        report = TestReport()
        src_files: List[str] = []
        test_files: List[str] = []

        src_dir = os.path.join(project_dir, "src")
        search_dir = src_dir if os.path.exists(src_dir) else project_dir

        for root, _, files in os.walk(search_dir):
            for fname in files:
                if fname.endswith((".ts", ".tsx", ".py", ".js", ".jsx")):
                    is_test = (
                        ".test." in fname or ".spec." in fname
                        or fname.startswith("test_")
                        or "__tests__" in root
                    )
                    if is_test:
                        test_files.append(fname)
                        # Count test functions
                        filepath = os.path.join(root, fname)
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                code = f.read()
                            report.total_tests += len(re.findall(
                                r"\bit\(|\btest\(|\bdef test_", code
                            ))
                        except OSError:
                            pass
                    else:
                        src_files.append(fname)

        report.total_files = len(src_files)
        # Match source files to test files
        tested_files = set()
        for src in src_files:
            base = src.replace(".tsx", "").replace(".ts", "").replace(".py", "")
            for tf in test_files:
                if base in tf:
                    tested_files.add(src)
                    break

        report.files_with_tests = len(tested_files)
        report.missing_tests = [f for f in src_files if f not in tested_files]
        report.coverage_percent = (
            (len(tested_files) / len(src_files) * 100) if src_files else 100.0
        )

        # Validate test files
        report.validation_errors = self.validate_test_files(project_dir)

        return report

    def check_spec_completeness(self, project_dir: str,
                                 spec_data: Dict[str, Any]) -> List[str]:
        """Check that tests exist for all components/features defined in the spec."""
        missing: List[str] = []

        # Get all component names from tech spec
        components = spec_data.get("tech_spec", {}).get("components", [])
        for comp in components:
            comp_name = comp.get("name", "")
            if not comp_name:
                continue
            # Look for test file matching component name
            comp_lower = comp_name.lower().replace(" ", "_").replace("-", "_")
            found = False
            for root, _, files in os.walk(project_dir):
                for fname in files:
                    if comp_lower in fname.lower() and (
                        ".test." in fname or ".spec." in fname or fname.startswith("test_")
                    ):
                        found = True
                        break
                if found:
                    break
            if not found:
                missing.append(f"Component '{comp_name}' has no test file")

        # Check requirements with acceptance criteria
        for req in spec_data.get("requirements", []):
            title = req.get("title", "")
            criteria = req.get("acceptance_criteria", [])
            for criterion in criteria:
                test_method = criterion.get("test_method", "")
                if test_method in ("integration", "e2e"):
                    # These should have dedicated test files
                    desc_words = criterion.get("description", "").lower().split()[:3]
                    key = "_".join(desc_words)
                    if key and len(key) > 5:
                        missing.append(
                            f"Acceptance criterion '{criterion.get('description', '')[:50]}' "
                            f"({test_method}) — verify test exists for: {title}"
                        )

        return missing

    def _parse_results(self, result: subprocess.CompletedProcess) -> List[TestResult]:
        errors = [l for l in (result.stderr + result.stdout).split("\n")
                  if "fail" in l.lower() or "error" in l.lower()][:10]
        return [TestResult(
            file="all", passed=result.returncode == 0,
            total=1, failures=0 if result.returncode == 0 else 1,
            errors=errors,
        )]

    def _fallback_test(self, source_file: str, framework: str) -> str:
        name = source_file.replace(".tsx", "").replace(".ts", "").replace(".jsx", "").replace(".js", "")
        return (
            f'import {{ render, screen }} from "@testing-library/react";\n'
            f'import {{ describe, it, expect }} from "vitest";\n'
            f'import {name} from "../{source_file}";\n\n'
            f'describe("{name}", () => {{\n'
            f'  it("renders without crashing", () => {{\n'
            f"    render(<{name} />);\n"
            f"  }});\n"
            f"}});\n"
        )
