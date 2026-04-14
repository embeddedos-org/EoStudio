"""Terminal emulator (stub)."""

from __future__ import annotations

from typing import Optional


class TerminalEmulator:
    def __init__(self) -> None:
        self._output: str = ""

    def execute(self, command: str) -> str:
        self._output = f"$ {command}\n(stub — not executed)"
        return self._output

    def clear(self) -> None:
        self._output = ""

    def get_output(self) -> str:
        return self._output
