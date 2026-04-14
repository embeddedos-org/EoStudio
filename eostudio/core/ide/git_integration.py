"""Git integration (stub)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class GitIntegration:
    def __init__(self, workspace_path: str = ".") -> None:
        self.workspace_path = workspace_path

    def status(self) -> List[Dict[str, str]]:
        return []

    def diff(self) -> str:
        return ""

    def commit(self, message: str) -> bool:
        return False

    def push(self) -> bool:
        return False

    def pull(self) -> bool:
        return False

    def branch(self) -> str:
        return "main"

    def branches(self) -> List[str]:
        return ["main"]
