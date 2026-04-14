"""Debugger (stub)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class Debugger:
    def __init__(self) -> None:
        self._running = False
        self._breakpoints: List[Dict[str, Any]] = []

    def start(self, path: str) -> bool:
        self._running = True
        return True

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def add_breakpoint(self, file: str, line: int) -> None:
        self._breakpoints.append({"file": file, "line": line})

    def remove_breakpoint(self, file: str, line: int) -> None:
        self._breakpoints = [
            bp for bp in self._breakpoints
            if not (bp["file"] == file and bp["line"] == line)
        ]
