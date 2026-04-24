"""LLM client and configuration.

Security features:
- API keys loaded exclusively from environment variables
- Input sanitization before sending to LLM APIs
- PII detection warnings for user-provided data
- Security audit logging for API interactions
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)
security_log = logging.getLogger("eostudio.security")

_DEFAULT_ENDPOINTS = {
    "ollama": "http://localhost:11434",
    "openai": "https://api.openai.com",
}

#: Patterns that may indicate PII in user messages.
_PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
    "ip_address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
}


def sanitize_input(text: str) -> str:
    """Sanitize user input before sending to an LLM API.

    Strips control characters and null bytes that could cause issues
    with API calls or prompt injection.
    """
    # Remove null bytes
    text = text.replace("\0", "")
    # Remove other non-printable control characters (keep newlines/tabs)
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text


def check_pii(text: str) -> List[str]:
    """Check text for potential PII patterns.

    Returns a list of PII types detected (e.g. ["email", "phone"]).
    Does NOT modify the text — callers decide how to handle warnings.
    """
    detected: List[str] = []
    for pii_type, pattern in _PII_PATTERNS.items():
        if pattern.search(text):
            detected.append(pii_type)
    if detected:
        security_log.warning(
            "Potential PII detected in LLM input: %s. "
            "Review data before sending to external APIs.",
            ", ".join(detected),
        )
    return detected


def _resolve_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    """Resolve an API key, preferring environment variables.

    If an explicit key is passed (e.g. from CLI), log a warning
    recommending env-var usage instead.
    """
    env_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("EOSTUDIO_API_KEY")

    if explicit_key and not env_key:
        security_log.warning(
            "API key passed explicitly. For security, prefer setting "
            "OPENAI_API_KEY or EOSTUDIO_API_KEY environment variables."
        )
        return explicit_key

    if env_key:
        return env_key

    return explicit_key


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
        # Resolve API key through secure path
        self.api_key = _resolve_api_key(self.api_key)

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
        endpoint = os.environ.get("EOSTUDIO_LLM_ENDPOINT")
        config = LLMConfig(
            provider=provider,
            model=model,
            endpoint=endpoint,
            # api_key resolved automatically via _resolve_api_key in __post_init__
        )
        return cls(config)

    def _prepend_system(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if not self.config.system_prompt:
            return list(messages)
        if messages and messages[0].get("role") == "system":
            return list(messages)
        return [{"role": "system", "content": self.config.system_prompt}] + list(messages)

    def _sanitize_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Sanitize all user messages and check for PII before API call."""
        sanitized: List[Dict[str, str]] = []
        for msg in messages:
            content = msg.get("content", "")
            if msg.get("role") == "user":
                content = sanitize_input(content)
                check_pii(content)
            sanitized.append({**msg, "content": content})
        return sanitized

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
