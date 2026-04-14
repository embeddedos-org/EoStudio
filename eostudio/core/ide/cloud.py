"""Cloud sync (stub)."""

from __future__ import annotations

from typing import Optional


class CloudSync:
    def __init__(self, endpoint: str = "") -> None:
        self.endpoint = endpoint
        self._connected = False

    def connect(self) -> bool:
        self._connected = False
        return self._connected

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def sync(self) -> bool:
        return False
