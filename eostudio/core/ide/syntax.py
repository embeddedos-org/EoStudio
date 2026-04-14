"""Syntax highlighting (stub)."""

from __future__ import annotations

from typing import Dict, List, Optional


class SyntaxHighlighter:
    def __init__(self, language: str = "python") -> None:
        self.language = language
        self._keywords: Dict[str, List[str]] = {}

    def highlight(self, source: str) -> str:
        return source

    def set_language(self, language: str) -> None:
        self.language = language
