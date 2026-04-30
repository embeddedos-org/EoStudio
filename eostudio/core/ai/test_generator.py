from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from eostudio.core.ai.llm_client import LLMClient, LLMConfig


class TestType(Enum):
    UNIT = auto()
    INTEGRATION = auto()
    E2E = auto()


@dataclass
class TestCase:
    name: str
    code: str
    description: str
    type: TestType


class TestGenerator:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient(LLMConfig())

    def _ask(self, prompt: str) -> str:
        return self.llm_client.complete(prompt)

    def generate_unit_tests(self, code: str, filename: str) -> list[TestCase]:
        prompt = (
            f"Generate unit tests for the following code from {filename}:\n\n{code}"
        )
        result = self._ask(prompt)
        return [
            TestCase(
                name=f"test_{filename}",
                code=result,
                description="Generated unit tests",
                type=TestType.UNIT,
            )
        ]

    def generate_integration_tests(self, code: str, filename: str) -> list[TestCase]:
        prompt = (
            f"Generate integration tests for the following code "
            f"from {filename}:\n\n{code}"
        )
        result = self._ask(prompt)
        return [
            TestCase(
                name=f"integration_test_{filename}",
                code=result,
                description="Generated integration tests",
                type=TestType.INTEGRATION,
            )
        ]

    def generate_edge_cases(self, code: str, filename: str) -> list[TestCase]:
        prompt = (
            f"Generate edge case tests for the following code "
            f"from {filename}:\n\n{code}"
        )
        result = self._ask(prompt)
        return [
            TestCase(
                name=f"edge_case_test_{filename}",
                code=result,
                description="Generated edge case tests",
                type=TestType.UNIT,
            )
        ]

    def generate_from_coverage(
        self, code: str, uncovered_lines: list[int], filename: str
    ) -> list[TestCase]:
        lines_str = ", ".join(str(ln) for ln in uncovered_lines)
        prompt = (
            f"Generate tests to cover lines {lines_str} in the following "
            f"code from {filename}:\n\n{code}"
        )
        result = self._ask(prompt)
        return [
            TestCase(
                name=f"coverage_test_{filename}",
                code=result,
                description=f"Tests for uncovered lines: {lines_str}",
                type=TestType.UNIT,
            )
        ]