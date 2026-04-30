from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from eostudio.core.ai.llm_client import LLMClient, LLMConfig


class ReviewSeverity(Enum):
    CRITICAL = auto()
    WARNING = auto()
    INFO = auto()
    SUGGESTION = auto()


@dataclass
class ReviewComment:
    file: str
    line: int
    severity: ReviewSeverity
    message: str
    suggestion: str = ""
    category: str = ""


@dataclass
class ReviewResult:
    comments: list[ReviewComment] = field(default_factory=list)
    summary: str = ""
    score: int = 100


class CodeReviewer:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient(LLMConfig())

    def _ask(self, prompt: str) -> str:
        return self.llm_client.complete(prompt)

    def review_file(self, code: str, filename: str) -> ReviewResult:
        prompt = (
            f"Review the following code from {filename}. "
            f"Identify bugs, style issues, and improvements:\n\n{code}"
        )
        result = self._ask(prompt)
        return ReviewResult(summary=result, score=80)

    def review_diff(self, diff_text: str) -> ReviewResult:
        prompt = (
            f"Review the following code diff. "
            f"Identify issues and suggest improvements:\n\n{diff_text}"
        )
        result = self._ask(prompt)
        return ReviewResult(summary=result, score=80)

    def review_commit(self, commit_message: str, diff_text: str) -> ReviewResult:
        prompt = (
            f"Review the following commit.\n"
            f"Commit message: {commit_message}\n\n"
            f"Diff:\n{diff_text}"
        )
        result = self._ask(prompt)
        return ReviewResult(summary=result, score=80)