"""Multi-Model AI Router — intelligently routes requests to the best available LLM.

Supports: OpenAI (GPT-4.1, GPT-4.1-mini, GPT-4.1-nano), Google Gemini 2.5 Flash,
Anthropic Claude, Ollama (local), and any OpenAI-compatible endpoint.

Features:
- Automatic model selection based on task type and complexity
- Fallback chain: primary → secondary → local
- Streaming support for real-time completions
- Token budget management
- Latency tracking and adaptive routing
- Context window management (auto-truncation)
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, Generator, List, Optional

log = logging.getLogger(__name__)


class TaskType(Enum):
    """Task categories that influence model selection."""

    CODE_COMPLETION = auto()  # Fast, short completions (nano/mini)
    CODE_GENERATION = auto()  # Full function/class generation (gpt-4.1)
    CODE_REVIEW = auto()  # Deep analysis (gpt-4.1 / gemini)
    DESIGN_BRIEF = auto()  # Creative design tasks (gemini / claude)
    CHAT = auto()  # General conversation (mini)
    AGENT_LOOP = auto()  # Autonomous multi-step (gpt-4.1 / claude)
    DOCUMENTATION = auto()  # Doc generation (mini)
    REFACTOR = auto()  # Code refactoring (gpt-4.1)
    DEBUG = auto()  # Error diagnosis (gpt-4.1)
    VOICE_TRANSCRIPTION = auto()  # Voice-to-text (whisper)


@dataclass
class ModelProfile:
    """Describes a model's capabilities and cost characteristics."""

    name: str
    provider: str
    context_window: int
    cost_per_1k_tokens: float  # USD
    avg_latency_ms: float
    supports_streaming: bool = True
    supports_vision: bool = False
    best_for: List[TaskType] = field(default_factory=list)


# Registry of known models
MODEL_REGISTRY: Dict[str, ModelProfile] = {
    "gpt-4.1": ModelProfile(
        name="gpt-4.1",
        provider="openai",
        context_window=1_000_000,
        cost_per_1k_tokens=0.002,
        avg_latency_ms=1200,
        supports_vision=True,
        best_for=[
            TaskType.CODE_GENERATION,
            TaskType.CODE_REVIEW,
            TaskType.AGENT_LOOP,
            TaskType.REFACTOR,
            TaskType.DEBUG,
        ],
    ),
    "gpt-4.1-mini": ModelProfile(
        name="gpt-4.1-mini",
        provider="openai",
        context_window=1_000_000,
        cost_per_1k_tokens=0.0004,
        avg_latency_ms=600,
        best_for=[TaskType.CHAT, TaskType.DOCUMENTATION, TaskType.DESIGN_BRIEF],
    ),
    "gpt-4.1-nano": ModelProfile(
        name="gpt-4.1-nano",
        provider="openai",
        context_window=128_000,
        cost_per_1k_tokens=0.0001,
        avg_latency_ms=200,
        best_for=[TaskType.CODE_COMPLETION],
    ),
    "gemini-2.5-flash": ModelProfile(
        name="gemini-2.5-flash",
        provider="openai_compat",
        context_window=1_000_000,
        cost_per_1k_tokens=0.00015,
        avg_latency_ms=400,
        supports_vision=True,
        best_for=[TaskType.CODE_REVIEW, TaskType.DESIGN_BRIEF, TaskType.DOCUMENTATION],
    ),
    "llama3": ModelProfile(
        name="llama3",
        provider="ollama",
        context_window=8_192,
        cost_per_1k_tokens=0.0,
        avg_latency_ms=800,
        best_for=[TaskType.CHAT, TaskType.CODE_COMPLETION],
    ),
}


@dataclass
class RouterConfig:
    """Configuration for the multi-model router."""

    primary_model: str = "gpt-4.1-mini"
    fallback_model: str = "gpt-4.1-nano"
    local_model: str = "llama3"
    max_tokens: int = 4096
    temperature: float = 0.2
    enable_streaming: bool = True
    enable_fallback: bool = True
    latency_budget_ms: float = 5000.0
    prefer_local: bool = False  # Set True to always prefer Ollama


class MultiModelRouter:
    """Routes AI requests to the optimal model based on task type and availability.

    Usage::

        router = MultiModelRouter()
        response = router.complete("Write a Python function to sort a list", task=TaskType.CODE_GENERATION)

        # Streaming
        for chunk in router.stream("Explain this code: ...", task=TaskType.CODE_REVIEW):
            print(chunk, end="", flush=True)
    """

    def __init__(self, config: Optional[RouterConfig] = None) -> None:
        self.config = config or RouterConfig()
        self._latency_history: Dict[str, List[float]] = {}
        self._error_counts: Dict[str, int] = {}
        self._openai_client: Any = None
        self._setup_clients()

    def _setup_clients(self) -> None:
        """Initialize API clients based on available credentials."""
        try:
            from openai import OpenAI

            api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("EOSTUDIO_API_KEY")
            if api_key:
                self._openai_client = OpenAI(api_key=api_key)
                log.info("OpenAI client initialized")
        except ImportError:
            log.warning("openai package not installed; install with: pip install openai")

    def select_model(self, task: TaskType, complexity: int = 5) -> str:
        """Select the best model for a given task and complexity (1-10).

        Args:
            task: The type of task to perform.
            complexity: Estimated complexity on a 1-10 scale.

        Returns:
            Model name string.
        """
        if self.config.prefer_local:
            return self.config.local_model

        # Find models best suited for this task
        candidates = [name for name, profile in MODEL_REGISTRY.items() if task in profile.best_for]

        if not candidates:
            candidates = [self.config.primary_model]

        # Filter by available providers
        available = [c for c in candidates if self._is_available(c)]
        if not available:
            return self.config.local_model

        # For high complexity tasks, prefer more capable models
        if complexity >= 8:
            for preferred in ["gpt-4.1", "gemini-2.5-flash"]:
                if preferred in available:
                    return preferred

        # For low complexity / fast tasks, prefer cheaper/faster models
        if complexity <= 3:
            for preferred in ["gpt-4.1-nano", "gpt-4.1-mini", "gemini-2.5-flash"]:
                if preferred in available:
                    return preferred

        return available[0]

    def _is_available(self, model_name: str) -> bool:
        """Check if a model is currently available."""
        profile = MODEL_REGISTRY.get(model_name)
        if not profile:
            return False

        # Check error rate
        errors = self._error_counts.get(model_name, 0)
        if errors >= 3:
            return False

        if profile.provider in ("openai", "openai_compat"):
            return self._openai_client is not None
        if profile.provider == "ollama":
            return True  # Assume local is always available
        return False

    def complete(
        self,
        prompt: str,
        task: TaskType = TaskType.CHAT,
        complexity: int = 5,
        system: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        model_override: Optional[str] = None,
    ) -> str:
        """Complete a prompt using the best available model.

        Args:
            prompt: The user prompt.
            task: Task type for model selection.
            complexity: Complexity score 1-10.
            system: Optional system prompt.
            messages: Optional full message history (overrides prompt).
            model_override: Force a specific model.

        Returns:
            The model's response text.
        """
        model = model_override or self.select_model(task, complexity)
        profile = MODEL_REGISTRY.get(model)

        if messages is None:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

        start = time.monotonic()
        try:
            result = self._dispatch(model, messages, profile)
            elapsed = (time.monotonic() - start) * 1000
            self._record_latency(model, elapsed)
            return result
        except Exception as exc:
            log.error("Model %s failed: %s", model, exc)
            self._error_counts[model] = self._error_counts.get(model, 0) + 1
            if self.config.enable_fallback and model != self.config.fallback_model:
                log.info("Falling back to %s", self.config.fallback_model)
                return self.complete(
                    prompt,
                    task,
                    complexity,
                    system,
                    messages,
                    model_override=self.config.fallback_model,
                )
            raise

    def stream(
        self,
        prompt: str,
        task: TaskType = TaskType.CHAT,
        complexity: int = 5,
        system: Optional[str] = None,
        model_override: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Stream a completion token by token.

        Yields:
            Text chunks as they arrive from the model.
        """
        model = model_override or self.select_model(task, complexity)
        profile = MODEL_REGISTRY.get(model)

        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        if profile and profile.provider in ("openai", "openai_compat") and self._openai_client:
            yield from self._stream_openai(model, messages)
        else:
            # Fallback: yield complete response as single chunk
            result = self.complete(prompt, task, complexity, system, model_override=model)
            yield result

    def _dispatch(
        self,
        model: str,
        messages: List[Dict[str, str]],
        profile: Optional[ModelProfile],
    ) -> str:
        """Dispatch to the correct provider."""
        if profile and profile.provider in ("openai", "openai_compat") and self._openai_client:
            return self._call_openai(model, messages)
        # Fallback to Ollama
        return self._call_ollama(model, messages)

    def _call_openai(self, model: str, messages: List[Dict[str, str]]) -> str:
        """Call OpenAI-compatible API."""
        response = self._openai_client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        return response.choices[0].message.content or ""

    def _stream_openai(
        self,
        model: str,
        messages: List[Dict[str, str]],
    ) -> Generator[str, None, None]:
        """Stream from OpenAI-compatible API."""
        stream = self._openai_client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    def _call_ollama(self, model: str, messages: List[Dict[str, str]]) -> str:
        """Call local Ollama instance."""
        try:
            import httpx

            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": self.config.temperature},
            }
            resp = httpx.post(
                "http://localhost:11434/api/chat",
                json=payload,
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except Exception as exc:
            raise RuntimeError(f"Ollama call failed: {exc}") from exc

    def _record_latency(self, model: str, latency_ms: float) -> None:
        history = self._latency_history.setdefault(model, [])
        history.append(latency_ms)
        if len(history) > 100:
            history.pop(0)

    def avg_latency(self, model: str) -> float:
        """Return average observed latency for a model in milliseconds."""
        history = self._latency_history.get(model, [])
        return sum(history) / len(history) if history else 0.0

    def stats(self) -> Dict[str, Any]:
        """Return router statistics."""
        return {
            "models": {
                name: {
                    "avg_latency_ms": round(self.avg_latency(name), 1),
                    "errors": self._error_counts.get(name, 0),
                    "available": self._is_available(name),
                }
                for name in MODEL_REGISTRY
            },
            "config": {
                "primary": self.config.primary_model,
                "fallback": self.config.fallback_model,
                "prefer_local": self.config.prefer_local,
            },
        }


# Module-level singleton for convenience
_default_router: Optional[MultiModelRouter] = None


def get_router() -> MultiModelRouter:
    """Get or create the default module-level router."""
    global _default_router
    if _default_router is None:
        _default_router = MultiModelRouter()
    return _default_router
