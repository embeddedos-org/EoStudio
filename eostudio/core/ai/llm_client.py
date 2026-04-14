"""LLM client and configuration."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

_DEFAULT_ENDPOINTS = {
    "ollama": "http://localhost:11434",
    "openai": "https://api.openai.com",
}


@dataclass
class LLMConfig:
    provider: str = "ollama"
    endpoint: Optional[str] = None
    model: str = "llama3"
    temperature: float = 0.7
    max_tokens: int = 2048
    api_key: Optional[str] = None
    system_prompt: Optional[str] = None

    def __post_init__(self) -> None:
        if self.endpoint is None:
            self.endpoint = _DEFAULT_ENDPOINTS.get(self.provider, "http://localhost:11434")

    def effective_endpoint(self) -> str:
        ep = self.endpoint or ""
        return ep.rstrip("/")


class LLMClient:
    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        self.config = config or LLMConfig()

    @classmethod
    def from_env(cls) -> LLMClient:
        provider = os.environ.get("EOSTUDIO_LLM_PROVIDER", "ollama")
        model = os.environ.get("EOSTUDIO_LLM_MODEL", "llama3")
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("EOSTUDIO_API_KEY")
        endpoint = os.environ.get("EOSTUDIO_LLM_ENDPOINT")
        config = LLMConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            endpoint=endpoint,
        )
        return cls(config)

    def _prepend_system(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if not self.config.system_prompt:
            return list(messages)
        if messages and messages[0].get("role") == "system":
            return list(messages)
        return [{"role": "system", "content": self.config.system_prompt}] + list(messages)

    def chat(self, messages: List[Dict[str, str]]) -> str:
        raise NotImplementedError("Subclass or mock this method")

    def chat_json(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        raw = self.chat(messages)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": "parse error", "raw": raw}

    def is_available(self) -> bool:
        return False

    @staticmethod
    def _unavailable_message(reason: str = "") -> str:
        msg = "LLM backend is not available"
        if reason:
            msg += f": {reason}"
        return msg
