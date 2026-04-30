from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from eostudio.core.ai.llm_client import LLMClient, LLMConfig


class CompletionType(Enum):
    INLINE = auto()
    MULTI_LINE = auto()
    BLOCK = auto()


@dataclass
class CodeSuggestion:
    text: str
    type: CompletionType
    confidence: float
    start_line: int
    end_line: int


class CodeAssistant:
    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient(LLMConfig())

    def _ask(self, prompt: str) -> str:
        return self.llm_client.complete(prompt)

    def complete(
        self,
        code: str,
        cursor_line: int,
        cursor_col: int,
        language: str,
        context_files: list[str] | None = None,
    ) -> list[CodeSuggestion]:
        context = ""
        if context_files:
            context = "\n".join(f"// File: {f}" for f in context_files)
        prompt = (
            f"Complete the following {language} code at line {cursor_line}, "
            f"column {cursor_col}.\n\n{context}\n\n{code}"
        )
        result = self._ask(prompt)
        return [
            CodeSuggestion(
                text=result,
                type=CompletionType.INLINE,
                confidence=0.8,
                start_line=cursor_line,
                end_line=cursor_line,
            )
        ]

    def explain(self, code: str, language: str) -> str:
        prompt = f"Explain the following {language} code:\n\n{code}"
        return self._ask(prompt)

    def refactor(self, code: str, instruction: str, language: str) -> str:
        prompt = (
            f"Refactor the following {language} code according to this "
            f"instruction: {instruction}\n\n{code}"
        )
        return self._ask(prompt)

    def translate(self, code: str, from_lang: str, to_lang: str) -> str:
        prompt = f"Translate the following {from_lang} code to {to_lang}:\n\n{code}"
        return self._ask(prompt)

    def generate_docstring(self, code: str, language: str) -> str:
        prompt = (
            f"Generate a docstring for the following {language} code:\n\n{code}"
        )
        return self._ask(prompt)

    def fix_error(self, code: str, error_message: str, language: str) -> str:
        prompt = (
            f"Fix the following error in this {language} code.\n"
            f"Error: {error_message}\n\nCode:\n{code}"
        )
        return self._ask(prompt)

    def suggest_improvements(self, code: str, language: str) -> list[dict]:
        prompt = (
            f"Suggest improvements for the following {language} code. "
            f"Return each suggestion as a separate item:\n\n{code}"
        )
        result = self._ask(prompt)
        return [{"suggestion": result}]