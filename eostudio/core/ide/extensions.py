"""Extension manager (stub)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ExtensionManager:
    def __init__(self) -> None:
        self._extensions: Dict[str, Any] = {}

    def install(self, name: str) -> bool:
        self._extensions[name] = {"installed": True}
        return True

    def uninstall(self, name: str) -> bool:
        return self._extensions.pop(name, None) is not None

    def list_installed(self) -> List[str]:
        return list(self._extensions.keys())
