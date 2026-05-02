"""LLM client and configuration for EoStudio.

Provides a unified interface for multiple LLM backends (Ollama, OpenAI,
Anthropic, local llama-cpp-python) with streaming, retry, rate limiting,
token counting, and cost estimation.

All HTTP dependencies (httpx) are lazily imported so the module is
importable without any optional packages installed.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Optional,
    Type,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default endpoints per provider
# ---------------------------------------------------------------------------

_DEFAULT_ENDPOINTS = {
    "ollama": "http://localhost:11434",
    "openai": "https://api.openai.com",
    "anthropic": "https://api.anthropic.com",
}

# ---------------------------------------------------------------------------
# Approximate per-token pricing (USD) for popular models.
# Keys are lowercased model name prefixes.
# ---------------------------------------------------------------------------

_MODEL_PRICING: Dict[str, tuple[float, float]] = {
    # (input $/token, output $/token)
    "gpt-4o": (2.5e-6, 10e-6),
    "gpt-4-turbo": (10e-6, 30e-6),
    "gpt-4": (30e-6, 60e-6),
    "gpt-3.5-turbo": (0.5e-6, 1.5e-6),
    "claude-3-opus": (15e-6, 75e-6),
    "claude-3-sonnet": (3e-6, 15e-6),
    "claude-3-haiku": (0.25e-6, 1.25e-6),
    "claude-3.5-sonnet": (3e-6, 15e-6),
    "claude-3.5-haiku": (0.8e-6, 4e-6),
}

# ---------------------------------------------------------------------------
# LLMConfig
# ---------------------------------------------------------------------------


@dataclass
class LLMConfig:
    """Configuration for an LLM backend."""

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
        """Return the endpoint with trailing slashes stripped."""
        ep = self.endpoint or ""
        return ep.rstrip("/")


# ---------------------------------------------------------------------------
# Token-bucket rate limiter
# ---------------------------------------------------------------------------


class _TokenBucket:
    """Simple token-bucket rate limiter.

    Parameters
    ----------
    rate:
        Tokens added per second.
    capacity:
        Maximum burst size.
    """

    def __init__(self, rate: float = 10.0, capacity: float = 30.0) -> None:
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._last = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last = now

    def acquire(self, tokens: float = 1.0) -> None:
        """Block (sleep) until *tokens* are available, then consume them."""
        while True:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return
            deficit = tokens - self._tokens
            time.sleep(deficit / self._rate)

    async def acquire_async(self, tokens: float = 1.0) -> None:
        """Async version of :meth:`acquire`."""
        while True:
            self._refill()
            if self._tokens >= tokens:
                self._tokens -= tokens
                return
            deficit = tokens - self._tokens
            await asyncio.sleep(deficit / self._rate)


# ---------------------------------------------------------------------------
# LLMClient base class (backward-compatible)
# ---------------------------------------------------------------------------


class LLMClient:
    """Base LLM client.

    The public API (:meth:`chat`, :meth:`chat_json`, :meth:`is_available`)
    is preserved for backward compatibility.  Concrete subclasses override
    :meth:`chat` (and optionally :meth:`chat_stream`) with real
    implementations.
    """

    # Shared rate limiter -- subclasses can override with their own instance.
    _rate_limiter: _TokenBucket = _TokenBucket(rate=10.0, capacity=30.0)

    # Default HTTP timeout in seconds.
    DEFAULT_TIMEOUT: float = 30.0

    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        self.config = config or LLMConfig()

    # -- Factory methods ----------------------------------------------------

    @classmethod
    def from_env(cls) -> LLMClient:
        """Create a client from environment variables."""
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

    @classmethod
    def create(cls, config: Optional[LLMConfig] = None) -> LLMClient:
        """Factory that returns a concrete subclass based on *config.provider*.

        Supported providers: ``ollama``, ``openai``, ``anthropic``, ``local``.
        Falls back to the base :class:`LLMClient` for unknown providers.
        """
        cfg = config or LLMConfig()
        provider = cfg.provider.lower().strip()
        registry: Dict[str, Type[LLMClient]] = {
            "ollama": OllamaClient,
            "openai": OpenAIClient,
            "anthropic": AnthropicClient,
            "local": LocalLLMClient,
        }
        backend_cls = registry.get(provider, cls)
        return backend_cls(cfg)

    # -- Message helpers ----------------------------------------------------

    def _prepend_system(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Prepend the system prompt if configured and not already present."""
        if not self.config.system_prompt:
            return list(messages)
        if messages and messages[0].get("role") == "system":
            return list(messages)
        return [{"role": "system", "content": self.config.system_prompt}] + list(messages)

    # -- Core chat API ------------------------------------------------------

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """Send *messages* and return the assistant reply as a string."""
        raise NotImplementedError("Subclass or mock this method")

    def chat_json(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Like :meth:`chat` but parse the response as JSON."""
        raw = self.chat(messages)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": "parse error", "raw": raw}

    async def chat_stream(
        self, messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Yield chunks of the assistant reply as they arrive.

        The default implementation simply yields the full :meth:`chat`
        response in one chunk.  Concrete subclasses should override this
        with true streaming when the backend supports it.
        """
        yield self.chat(messages)

    # -- Availability -------------------------------------------------------

    def is_available(self) -> bool:
        """Return *True* if the backend can be reached."""
        return False

    @staticmethod
    def _unavailable_message(reason: str = "") -> str:
        msg = "LLM backend is not available"
        if reason:
            msg += f": {reason}"
        return msg

    # -- Token counting & cost estimation -----------------------------------

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token estimate using the ~0.75 words/token heuristic.

        This is intentionally simple -- accurate counts require a real
        tokenizer.  Good enough for budgeting and cost estimation.
        """
        # Split on whitespace; each word is roughly 1.33 tokens on average.
        words = text.split()
        return max(1, int(len(words) * 1.33))

    @staticmethod
    def estimate_cost(
        input_tokens: int,
        output_tokens: int,
        model: str = "",
    ) -> float:
        """Estimate cost in USD for a given model.

        Looks up per-token pricing from :data:`_MODEL_PRICING`.  Returns
        ``0.0`` for unknown / local models.
        """
        model_lower = model.lower()
        for prefix, (inp_price, out_price) in _MODEL_PRICING.items():
            if model_lower.startswith(prefix):
                return input_tokens * inp_price + output_tokens * out_price
        return 0.0

    # -- Retry helper -------------------------------------------------------

    def _request_with_retry(
        self,
        fn: Any,
        *args: Any,
        max_retries: int = 3,
        base_delay: float = 1.0,
        **kwargs: Any,
    ) -> Any:
        """Call *fn* with exponential back-off on failure.

        Retries on :class:`Exception` up to *max_retries* times.  The
        delay doubles after each attempt (jitter-free for simplicity).
        """
        last_exc: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "LLM request failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        max_retries + 1,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
        raise last_exc  # type: ignore[misc]

    async def _request_with_retry_async(
        self,
        fn: Any,
        *args: Any,
        max_retries: int = 3,
        base_delay: float = 1.0,
        **kwargs: Any,
    ) -> Any:
        """Async version of :meth:`_request_with_retry`."""
        last_exc: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                return await fn(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        "LLM request failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        max_retries + 1,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)
        raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Ollama client
# ---------------------------------------------------------------------------


class OllamaClient(LLMClient):
    """Chat with a model served by Ollama on localhost (or a custom endpoint)."""

    def chat(self, messages: List[Dict[str, str]]) -> str:
        import httpx

        self._rate_limiter.acquire()
        msgs = self._prepend_system(messages)
        url = f"{self.config.effective_endpoint()}/api/chat"
        payload = {
            "model": self.config.model,
            "messages": msgs,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        def _do_request() -> str:
            with httpx.Client(timeout=self.DEFAULT_TIMEOUT) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("message", {}).get("content", "")

        return self._request_with_retry(_do_request)

    async def chat_stream(
        self, messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Stream tokens from Ollama using its native streaming API."""
        import httpx

        await self._rate_limiter.acquire_async()
        msgs = self._prepend_system(messages)
        url = f"{self.config.effective_endpoint()}/api/chat"
        payload = {
            "model": self.config.model,
            "messages": msgs,
            "stream": True,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }
        async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if chunk.get("done"):
                        return

    def is_available(self) -> bool:
        """Ping the Ollama tag list endpoint."""
        try:
            import httpx

            url = f"{self.config.effective_endpoint()}/api/tags"
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url)
                return resp.status_code == 200
        except Exception:
            return False


# ---------------------------------------------------------------------------
# OpenAI client
# ---------------------------------------------------------------------------


class OpenAIClient(LLMClient):
    """Chat via the OpenAI-compatible ``/v1/chat/completions`` endpoint."""

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def chat(self, messages: List[Dict[str, str]]) -> str:
        import httpx

        self._rate_limiter.acquire()
        msgs = self._prepend_system(messages)
        url = f"{self.config.effective_endpoint()}/v1/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": msgs,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        def _do_request() -> str:
            with httpx.Client(timeout=self.DEFAULT_TIMEOUT) as client:
                resp = client.post(url, json=payload, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    return ""
                return choices[0].get("message", {}).get("content", "")

        return self._request_with_retry(_do_request)

    async def chat_stream(
        self, messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Stream tokens using OpenAI SSE streaming."""
        import httpx

        await self._rate_limiter.acquire_async()
        msgs = self._prepend_system(messages)
        url = f"{self.config.effective_endpoint()}/v1/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": msgs,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
            async with client.stream(
                "POST", url, json=payload, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[len("data: "):]
                    if data_str.strip() == "[DONE]":
                        return
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = (
                        chunk.get("choices", [{}])[0]
                        .get("delta", {})
                        .get("content", "")
                    )
                    if delta:
                        yield delta

    def is_available(self) -> bool:
        """Check availability by listing models."""
        try:
            import httpx

            url = f"{self.config.effective_endpoint()}/v1/models"
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url, headers=self._headers())
                return resp.status_code == 200
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Anthropic client
# ---------------------------------------------------------------------------


class AnthropicClient(LLMClient):
    """Chat via the Anthropic Messages API (``/v1/messages``)."""

    ANTHROPIC_VERSION = "2023-06-01"

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "anthropic-version": self.ANTHROPIC_VERSION,
        }
        if self.config.api_key:
            headers["x-api-key"] = self.config.api_key
        return headers

    def _build_payload(
        self, messages: List[Dict[str, str]], *, stream: bool = False
    ) -> Dict[str, Any]:
        """Build the Anthropic request body.

        Anthropic's API takes ``system`` as a top-level string, not as a
        message with role ``system``.  This method extracts it accordingly.
        """
        system_text: Optional[str] = self.config.system_prompt
        user_messages: List[Dict[str, str]] = []

        for msg in messages:
            if msg.get("role") == "system":
                system_text = msg.get("content", system_text)
            else:
                user_messages.append(msg)

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": user_messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": stream,
        }
        if system_text:
            payload["system"] = system_text

        return payload

    def chat(self, messages: List[Dict[str, str]]) -> str:
        import httpx

        self._rate_limiter.acquire()
        msgs = self._prepend_system(messages)
        payload = self._build_payload(msgs, stream=False)
        url = f"{self.config.effective_endpoint()}/v1/messages"

        def _do_request() -> str:
            with httpx.Client(timeout=self.DEFAULT_TIMEOUT) as client:
                resp = client.post(url, json=payload, headers=self._headers())
                resp.raise_for_status()
                data = resp.json()
                content_blocks = data.get("content", [])
                parts = [
                    blk.get("text", "")
                    for blk in content_blocks
                    if blk.get("type") == "text"
                ]
                return "".join(parts)

        return self._request_with_retry(_do_request)

    async def chat_stream(
        self, messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Stream tokens using the Anthropic SSE streaming protocol."""
        import httpx

        await self._rate_limiter.acquire_async()
        msgs = self._prepend_system(messages)
        payload = self._build_payload(msgs, stream=True)
        url = f"{self.config.effective_endpoint()}/v1/messages"

        async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
            async with client.stream(
                "POST", url, json=payload, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[len("data: "):]
                    try:
                        chunk = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    event_type = chunk.get("type", "")
                    if event_type == "content_block_delta":
                        text = chunk.get("delta", {}).get("text", "")
                        if text:
                            yield text
                    elif event_type == "message_stop":
                        return

    def is_available(self) -> bool:
        """Anthropic has no lightweight health endpoint; check for API key."""
        return bool(self.config.api_key)


# ---------------------------------------------------------------------------
# Local LLM client (llama-cpp-python)
# ---------------------------------------------------------------------------


class LocalLLMClient(LLMClient):
    """Run inference via llama-cpp-python if installed, else fall back gracefully."""

    def __init__(self, config: Optional[LLMConfig] = None) -> None:
        super().__init__(config)
        self._llm: Any = None
        self._load_error: Optional[str] = None
        self._tried_load = False

    def _ensure_loaded(self) -> bool:
        """Attempt to load the model once.  Returns *True* on success."""
        if self._tried_load:
            return self._llm is not None
        self._tried_load = True
        try:
            from llama_cpp import Llama  # type: ignore[import-untyped]

            model_path = self.config.model
            if not os.path.isfile(model_path):
                self._load_error = f"Model file not found: {model_path}"
                logger.warning("LocalLLMClient: %s", self._load_error)
                return False
            self._llm = Llama(model_path=model_path, n_ctx=self.config.max_tokens)
            return True
        except ImportError:
            self._load_error = (
                "llama-cpp-python is not installed. "
                "Install it with: pip install llama-cpp-python"
            )
            logger.info("LocalLLMClient: %s", self._load_error)
            return False
        except Exception as exc:
            self._load_error = str(exc)
            logger.warning("LocalLLMClient failed to load model: %s", exc)
            return False

    def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self._ensure_loaded():
            return self._unavailable_message(self._load_error or "unknown error")

        msgs = self._prepend_system(messages)
        prompt_parts: List[str] = []
        for msg in msgs:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            prompt_parts.append(f"<|{role}|>\n{content}")
        prompt_parts.append("<|assistant|>")
        prompt = "\n".join(prompt_parts)

        result = self._llm(
            prompt,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        choices = result.get("choices", [])
        if not choices:
            return ""
        return choices[0].get("text", "").strip()

    async def chat_stream(
        self, messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """llama-cpp-python is synchronous; yield the full result."""
        yield self.chat(messages)

    def is_available(self) -> bool:
        return self._ensure_loaded()
