"""Language server protocol client (stub)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class LanguageServer:
    def __init__(self, language: str = "python") -> None:
        self.language = language
        self._running = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def complete(self, source: str, line: int, column: int) -> List[Dict[str, Any]]:
        return []

    def diagnostics(self, source: str) -> List[Dict[str, Any]]:
        return []
