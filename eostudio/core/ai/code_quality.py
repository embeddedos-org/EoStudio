"""Code Quality Checker — scans generated code for common issues and auto-fixes them."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class QualityIssue:
    """A code quality issue found during scanning."""
    file: str
    line: int
    severity: str  # "error", "warning", "info"
    category: str  # "error_handling", "types", "accessibility", "hardcoded", "unused"
    message: str
    auto_fixable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file, "line": self.line, "severity": self.severity,
            "category": self.category, "message": self.message,
            "auto_fixable": self.auto_fixable,
        }


class CodeQualityChecker:
    """Scans generated TypeScript/React code for production quality issues."""

    def check_file(self, filename: str, code: str) -> List[QualityIssue]:
        """Run all quality checks on a single file."""
        if not filename.endswith((".ts", ".tsx", ".js", ".jsx")):
            return []

        issues: List[QualityIssue] = []
        issues.extend(self._check_error_handling(filename, code))
        issues.extend(self._check_typescript_types(filename, code))
        issues.extend(self._check_accessibility(filename, code))
        issues.extend(self._check_hardcoded_strings(filename, code))
        issues.extend(self._check_unused_imports(filename, code))
        return issues

    def check_project(self, files: Dict[str, str]) -> Dict[str, List[QualityIssue]]:
        """Check all files in a project."""
        results: Dict[str, List[QualityIssue]] = {}
        for filename, code in files.items():
            issues = self.check_file(filename, code)
            if issues:
                results[filename] = issues
        return results

    def auto_fix(self, filename: str, code: str) -> str:
        """Apply auto-fixes to common issues without AI."""
        if not filename.endswith((".ts", ".tsx", ".js", ".jsx")):
            return code

        code = self._fix_missing_use_client(filename, code)
        code = self._fix_console_logs(code)
        code = self._fix_missing_key_prop(code)
        code = self._fix_implicit_any_returns(code)
        return code

    def summary(self, all_issues: Dict[str, List[QualityIssue]]) -> Dict[str, Any]:
        """Generate a quality summary from all issues."""
        total = sum(len(issues) for issues in all_issues.values())
        by_severity = {"error": 0, "warning": 0, "info": 0}
        by_category: Dict[str, int] = {}
        auto_fixable = 0

        for issues in all_issues.values():
            for issue in issues:
                by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
                by_category[issue.category] = by_category.get(issue.category, 0) + 1
                if issue.auto_fixable:
                    auto_fixable += 1

        score = max(0, 100 - (by_severity["error"] * 10) - (by_severity["warning"] * 3))
        return {
            "total_issues": total,
            "by_severity": by_severity,
            "by_category": by_category,
            "auto_fixable": auto_fixable,
            "quality_score": score,
            "files_with_issues": len(all_issues),
        }

    # -----------------------------------------------------------------------
    # Check methods
    # -----------------------------------------------------------------------

    def _check_error_handling(self, filename: str, code: str) -> List[QualityIssue]:
        issues = []
        lines = code.split("\n")

        # Check for fetch/axios calls without try-catch or .catch
        for i, line in enumerate(lines, 1):
            if re.search(r"\bfetch\(|axios\.", line) and "catch" not in code[max(0, code.find(line)-200):code.find(line)+len(line)+200]:
                issues.append(QualityIssue(
                    file=filename, line=i, severity="warning",
                    category="error_handling",
                    message="API call without error handling (missing try-catch or .catch)",
                ))

            # Check for empty catch blocks
            if re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", line):
                issues.append(QualityIssue(
                    file=filename, line=i, severity="error",
                    category="error_handling",
                    message="Empty catch block — errors are silently swallowed",
                    auto_fixable=True,
                ))

        # Check that async functions have error handling
        for m in re.finditer(r"async\s+function\s+(\w+)|async\s+\(", code):
            block_start = m.start()
            # Look ahead ~500 chars for try/catch
            block_end = min(len(code), block_start + 500)
            if "try" not in code[block_start:block_end] and "catch" not in code[block_start:block_end]:
                line_num = code[:block_start].count("\n") + 1
                issues.append(QualityIssue(
                    file=filename, line=line_num, severity="warning",
                    category="error_handling",
                    message="Async function without try-catch error handling",
                ))

        return issues

    def _check_typescript_types(self, filename: str, code: str) -> List[QualityIssue]:
        issues = []
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for explicit `any` type
            if re.search(r":\s*any\b", line) and "eslint-disable" not in line:
                issues.append(QualityIssue(
                    file=filename, line=i, severity="warning",
                    category="types",
                    message="Explicit `any` type — use a specific type instead",
                ))

            # Check for type assertion with `as any`
            if "as any" in line:
                issues.append(QualityIssue(
                    file=filename, line=i, severity="warning",
                    category="types",
                    message="`as any` type assertion — weakens type safety",
                ))

        return issues

    def _check_accessibility(self, filename: str, code: str) -> List[QualityIssue]:
        if not filename.endswith(".tsx"):
            return []

        issues = []
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            # img without alt
            if "<img" in line and "alt=" not in line and "alt =" not in line:
                issues.append(QualityIssue(
                    file=filename, line=i, severity="error",
                    category="accessibility",
                    message="<img> missing alt attribute",
                    auto_fixable=True,
                ))

            # onClick on non-interactive element without role/tabIndex
            if re.search(r"<(div|span|p)\s[^>]*onClick", line):
                if "role=" not in line and "tabIndex" not in line:
                    issues.append(QualityIssue(
                        file=filename, line=i, severity="warning",
                        category="accessibility",
                        message="onClick on non-interactive element without role/tabIndex",
                    ))

            # Form input without label
            if re.search(r"<input\s", line) and "aria-label" not in line and "id=" not in line:
                issues.append(QualityIssue(
                    file=filename, line=i, severity="warning",
                    category="accessibility",
                    message="<input> without aria-label or associated label",
                ))

        return issues

    def _check_hardcoded_strings(self, filename: str, code: str) -> List[QualityIssue]:
        issues = []
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            # Hardcoded URLs (not in comments or imports)
            if re.search(r'https?://(?!localhost|127\.0\.0\.1)', line) and not line.strip().startswith("//") and "import" not in line:
                issues.append(QualityIssue(
                    file=filename, line=i, severity="info",
                    category="hardcoded",
                    message="Hardcoded URL — consider using environment variable",
                ))

            # Hardcoded API keys or secrets
            if re.search(r'(api[_-]?key|secret|password|token)\s*[=:]\s*["\'][^"\']{8,}', line, re.IGNORECASE):
                issues.append(QualityIssue(
                    file=filename, line=i, severity="error",
                    category="hardcoded",
                    message="Possible hardcoded secret — use environment variable",
                ))

        return issues

    def _check_unused_imports(self, filename: str, code: str) -> List[QualityIssue]:
        issues = []
        # Find all imports
        import_pattern = re.compile(r"import\s+(?:\{([^}]+)\}|(\w+))\s+from")
        for m in import_pattern.finditer(code):
            names = m.group(1) or m.group(2)
            if not names:
                continue
            for name in names.split(","):
                name = name.strip().split(" as ")[-1].strip()
                if not name or name == "React":
                    continue
                # Count usages (excluding the import line itself)
                rest_of_code = code[m.end():]
                if re.search(r"\b" + re.escape(name) + r"\b", rest_of_code) is None:
                    line_num = code[:m.start()].count("\n") + 1
                    issues.append(QualityIssue(
                        file=filename, line=line_num, severity="warning",
                        category="unused",
                        message=f"Unused import: {name}",
                        auto_fixable=True,
                    ))

        return issues

    # -----------------------------------------------------------------------
    # Auto-fix methods
    # -----------------------------------------------------------------------

    def _fix_missing_use_client(self, filename: str, code: str) -> str:
        """Add 'use client' directive for Next.js client components."""
        if not filename.endswith(".tsx"):
            return code
        client_hooks = ["useState", "useEffect", "useRef", "useCallback", "useMemo", "useContext"]
        if any(hook in code for hook in client_hooks) and '"use client"' not in code and "'use client'" not in code:
            code = '"use client";\n\n' + code
        return code

    def _fix_console_logs(self, code: str) -> str:
        """Remove console.log statements (keep console.error/warn)."""
        return re.sub(r"^\s*console\.log\([^)]*\);?\s*\n", "", code, flags=re.MULTILINE)

    def _fix_missing_key_prop(self, code: str) -> str:
        """Add key prop to .map() JSX patterns that are missing it."""
        # Pattern: .map((item) => (<tag ...> without key=
        # This is a best-effort fix for simple cases
        pattern = r"\.map\(\((\w+)(?:,\s*(\w+))?\)\s*=>\s*\(\s*<(\w+)\s(?![^>]*\bkey=)"
        def add_key(m: re.Match) -> str:
            item = m.group(1)
            index = m.group(2)
            tag = m.group(3)
            key_expr = f"{item}.id" if not index else index
            return f'.map(({item}{"," + index if index else ""}) => (<{tag} key={{{key_expr}}} '
        return re.sub(pattern, add_key, code)

    def _fix_implicit_any_returns(self, code: str) -> str:
        """Add explicit return type annotations to exported functions missing them."""
        # Fix: export function foo(args) { -> export function foo(args): JSX.Element {
        # Only for simple React component cases
        pattern = r"(export\s+(?:default\s+)?function\s+\w+\([^)]*\))\s*\{"
        def add_return_type(m: re.Match) -> str:
            sig = m.group(1)
            if ":" in sig.split(")")[-1]:  # already has return type
                return m.group(0)
            return f"{sig}: JSX.Element {{"
        return re.sub(pattern, add_return_type, code)
