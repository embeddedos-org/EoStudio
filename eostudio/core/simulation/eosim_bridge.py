"""Bridge to EoSim native simulation backend (stub)."""

from __future__ import annotations


class EoSimBridge:
    """Stub for interfacing with the native EoSim C/Rust engine."""

    def __init__(self, endpoint: str = "localhost:5050") -> None:
        self.endpoint = endpoint
        self._connected = False

    def connect(self) -> bool:
        self._connected = False
        return self._connected

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def run_simulation(self, model_dict: dict) -> dict:
        raise NotImplementedError("EoSim native backend not yet available")
