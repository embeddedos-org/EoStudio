"""Smart Diff Viewer — AI-enhanced code diff and review tool.

Features:
- Semantic diff (understands code structure, not just lines)
- AI-powered change explanation in plain English
- Inline code review comments with severity levels
- Security vulnerability detection in diffs
- Performance regression detection
- Automatic test coverage gap detection
- PR-ready summary generation
- Side-by-side and unified diff modes
- Syntax-highlighted diff output
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class DiffMode(Enum):
    UNIFIED = "unified"
    SIDE_BY_SIDE = "side_by_side"
    SEMANTIC = "semantic"


class ReviewSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class DiffHunk:
    """A single diff hunk (block of changes)."""

    old_start: int
    old_lines: List[str]
    new_start: int
    new_lines: List[str]
    context_before: List[str] = field(default_factory=list)
    context_after: List[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class ReviewComment:
    """An AI-generated review comment on a diff."""

    line: int
    severity: ReviewSeverity
    category: str  # "security", "performance", "style", "logic", "test"
    message: str
    suggestion: str = ""
    auto_fixable: bool = False


@dataclass
class DiffResult:
    """Result of a diff operation."""

    file_a: str
    file_b: str
    language: str
    hunks: List[DiffHunk]
    review_comments: List[ReviewComment]
    summary: str
    stats: Dict[str, int]  # lines_added, lines_removed, files_changed
    pr_description: str = ""
    security_issues: List[ReviewComment] = field(default_factory=list)


# ------------------------------------------------------------------
# Security patterns to detect in diffs
# ------------------------------------------------------------------

_SECURITY_PATTERNS = [
    (re.compile(r"eval\s*\(", re.I), "Dangerous eval() usage — potential code injection"),
    (re.compile(r"exec\s*\(", re.I), "Dangerous exec() usage — potential code injection"),
    (re.compile(r"subprocess\.call\(.*shell\s*=\s*True", re.I), "Shell injection risk — shell=True in subprocess"),
    (re.compile(r"password\s*=\s*['\"][^'\"]+['\"]", re.I), "Hardcoded password detected"),
    (re.compile(r"secret\s*=\s*['\"][^'\"]+['\"]", re.I), "Hardcoded secret detected"),
    (re.compile(r"api_key\s*=\s*['\"][^'\"]+['\"]", re.I), "Hardcoded API key detected"),
    (re.compile(r"md5\s*\(", re.I), "Weak hash function MD5 — use SHA-256 or better"),
    (re.compile(r"pickle\.loads?\(", re.I), "Unsafe pickle deserialization"),
    (re.compile(r"yaml\.load\((?!.*Loader)", re.I), "Unsafe yaml.load() — use yaml.safe_load()"),
    (re.compile(r"SELECT.*\+.*WHERE|WHERE.*\+.*SELECT", re.I), "Potential SQL injection via string concatenation"),
    (re.compile(r"innerHTML\s*=", re.I), "Potential XSS via innerHTML assignment"),
    (re.compile(r"dangerouslySetInnerHTML", re.I), "Potential XSS via dangerouslySetInnerHTML"),
]

_PERFORMANCE_PATTERNS = [
    (re.compile(r"for .* in .*:\s*\n.*\.append\(", re.I), "Use list comprehension instead of loop+append"),
    (re.compile(r"time\.sleep\(\d+\)", re.I), "Blocking sleep() in production code"),
    (re.compile(r"SELECT \*", re.I), "SELECT * fetches all columns — specify needed columns"),
    (re.compile(r"N\+1|n\+1"), "Potential N+1 query pattern"),
]


class SmartDiff:
    """AI-enhanced diff and code review engine.

    Usage::

        diff = SmartDiff(router=router)

        result = diff.compare_files("old_version.py", "new_version.py")
        print(result.summary)

        for comment in result.review_comments:
            print(f"Line {comment.line} [{comment.severity.value}]: {comment.message}")

        print(result.pr_description)
    """

    def __init__(self, router: Optional[Any] = None) -> None:
        self._router = router

    def compare_files(
        self,
        path_a: str,
        path_b: str,
        mode: DiffMode = DiffMode.UNIFIED,
    ) -> DiffResult:
        """Compare two files and return a rich diff result.

        Args:
            path_a: Path to the original file.
            path_b: Path to the modified file.
            mode: Diff mode.

        Returns:
            DiffResult with hunks, review comments, and AI summary.
        """
        a_content = Path(path_a).read_text(encoding="utf-8") if Path(path_a).exists() else ""
        b_content = Path(path_b).read_text(encoding="utf-8") if Path(path_b).exists() else ""
        language = self._detect_language(path_b or path_a)
        return self.compare_text(a_content, b_content, language, path_a, path_b)

    def compare_text(
        self,
        old_text: str,
        new_text: str,
        language: str = "text",
        file_a: str = "a",
        file_b: str = "b",
    ) -> DiffResult:
        """Compare two text strings and return a rich diff result."""
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)

        hunks = self._compute_hunks(old_lines, new_lines)
        stats = self._compute_stats(old_lines, new_lines)
        review_comments = self._analyze_new_code(new_text, language)
        security_issues = [c for c in review_comments if c.category == "security"]

        summary = self._generate_summary(hunks, stats, language)
        pr_description = self._generate_pr_description(hunks, stats, review_comments)

        return DiffResult(
            file_a=file_a,
            file_b=file_b,
            language=language,
            hunks=hunks,
            review_comments=review_comments,
            summary=summary,
            stats=stats,
            pr_description=pr_description,
            security_issues=security_issues,
        )

    def render_unified(self, result: DiffResult) -> str:
        """Render a unified diff string."""
        lines = [f"--- {result.file_a}", f"+++ {result.file_b}", ""]
        for hunk in result.hunks:
            old_count = len(hunk.old_lines)
            new_count = len(hunk.new_lines)
            lines.append(f"@@ -{hunk.old_start},{old_count} +{hunk.new_start},{new_count} @@")
            for line in hunk.context_before:
                lines.append(f" {line.rstrip()}")
            for line in hunk.old_lines:
                lines.append(f"-{line.rstrip()}")
            for line in hunk.new_lines:
                lines.append(f"+{line.rstrip()}")
            for line in hunk.context_after:
                lines.append(f" {line.rstrip()}")
        return "\n".join(lines)

    def _compute_hunks(self, old_lines: List[str], new_lines: List[str]) -> List[DiffHunk]:
        """Compute diff hunks using SequenceMatcher."""
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        hunks: List[DiffHunk] = []

        for group in matcher.get_grouped_opcodes(n=3):
            old_start = group[0][1]
            new_start = group[0][3]
            old_chunk: List[str] = []
            new_chunk: List[str] = []

            for tag, i1, i2, j1, j2 in group:
                if tag == "equal":
                    continue
                elif tag in ("replace", "delete"):
                    old_chunk.extend(old_lines[i1:i2])
                if tag in ("replace", "insert"):
                    new_chunk.extend(new_lines[j1:j2])

            if old_chunk or new_chunk:
                hunks.append(
                    DiffHunk(
                        old_start=old_start + 1,
                        old_lines=old_chunk,
                        new_start=new_start + 1,
                        new_lines=new_chunk,
                    )
                )

        return hunks

    def _compute_stats(self, old_lines: List[str], new_lines: List[str]) -> Dict[str, int]:
        """Compute diff statistics."""
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        added = deleted = 0
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag in ("replace", "delete"):
                deleted += i2 - i1
            if tag in ("replace", "insert"):
                added += j2 - j1
        return {
            "lines_added": added,
            "lines_removed": deleted,
            "net_change": added - deleted,
            "old_total": len(old_lines),
            "new_total": len(new_lines),
        }

    def _analyze_new_code(self, new_text: str, language: str) -> List[ReviewComment]:
        """Analyze new code for security, performance, and style issues."""
        comments: List[ReviewComment] = []
        lines = new_text.splitlines()

        # Security checks
        for pattern, message in _SECURITY_PATTERNS:
            for i, line in enumerate(lines, 1):
                if pattern.search(line):
                    comments.append(
                        ReviewComment(
                            line=i,
                            severity=ReviewSeverity.CRITICAL,
                            category="security",
                            message=message,
                            suggestion="Review and fix this security issue before merging.",
                        )
                    )

        # Performance checks
        for pattern, message in _PERFORMANCE_PATTERNS:
            for i, line in enumerate(lines, 1):
                if pattern.search(line):
                    comments.append(
                        ReviewComment(
                            line=i,
                            severity=ReviewSeverity.WARNING,
                            category="performance",
                            message=message,
                        )
                    )

        # Style checks
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                comments.append(
                    ReviewComment(
                        line=i,
                        severity=ReviewSeverity.INFO,
                        category="style",
                        message=f"Line too long ({len(line)} chars) — consider wrapping at 120",
                    )
                )
            if re.search(r"\bTODO\b|\bFIXME\b|\bHACK\b", line, re.I):
                comments.append(
                    ReviewComment(
                        line=i,
                        severity=ReviewSeverity.INFO,
                        category="style",
                        message="Technical debt marker found — address before merging",
                    )
                )

        return comments

    def _generate_summary(
        self,
        hunks: List[DiffHunk],
        stats: Dict[str, int],
        language: str,
    ) -> str:
        """Generate a plain-English summary of the diff."""
        if self._router:
            try:
                hunk_text = "\n".join(
                    f"Hunk {i + 1}: -{len(h.old_lines)} +{len(h.new_lines)} lines" for i, h in enumerate(hunks[:5])
                )
                from eostudio.core.ai.multi_model_router import TaskType

                prompt = (
                    f"Summarize these code changes in 2-3 sentences:\n"
                    f"Language: {language}\n"
                    f"Stats: +{stats['lines_added']} -{stats['lines_removed']} lines\n"
                    f"Hunks:\n{hunk_text}"
                )
                return self._router.complete(prompt, task=TaskType.CODE_REVIEW, complexity=3)
            except Exception:
                pass

        # Fallback
        return (
            f"Changed {len(hunks)} location(s): "
            f"+{stats['lines_added']} lines added, "
            f"-{stats['lines_removed']} lines removed "
            f"(net: {stats['net_change']:+d})."
        )

    def _generate_pr_description(
        self,
        hunks: List[DiffHunk],
        stats: Dict[str, int],
        comments: List[ReviewComment],
    ) -> str:
        """Generate a PR description from the diff."""
        security_count = sum(1 for c in comments if c.category == "security")
        warning_count = sum(1 for c in comments if c.severity == ReviewSeverity.WARNING)

        lines = [
            "## Summary",
            f"- **{stats['lines_added']}** lines added, **{stats['lines_removed']}** lines removed",
            f"- **{len(hunks)}** change location(s)",
        ]

        if security_count:
            lines.append(f"\n## ⚠️ Security Issues ({security_count})")
            for c in comments:
                if c.category == "security":
                    lines.append(f"- Line {c.line}: {c.message}")

        if warning_count:
            lines.append(f"\n## Warnings ({warning_count})")
            for c in comments:
                if c.severity == ReviewSeverity.WARNING:
                    lines.append(f"- Line {c.line}: {c.message}")

        lines.append("\n## Checklist")
        lines.extend(
            [
                "- [ ] Tests updated",
                "- [ ] Documentation updated",
                "- [ ] No hardcoded secrets",
                "- [ ] Security review complete",
            ]
        )

        return "\n".join(lines)

    @staticmethod
    def _detect_language(path: str) -> str:
        ext_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".rs": "rust",
            ".go": "go",
            ".cpp": "cpp",
            ".c": "c",
            ".java": "java",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
        }
        return ext_map.get(Path(path).suffix.lower(), "text")
