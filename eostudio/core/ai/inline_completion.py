"""Inline Code Completion Engine — Cursor/Copilot-style AI completions.

Provides:
- Single-line ghost text completions (Tab to accept)
- Multi-line block completions
- Fill-in-the-middle (FIM) for mid-code completions
- Language-aware context extraction
- Debounced completion requests
- Completion cache to avoid redundant API calls
- Telemetry (acceptance rate, latency)
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from eostudio.core.ai.multi_model_router import MultiModelRouter, RouterConfig, TaskType

log = logging.getLogger(__name__)


@dataclass
class CompletionContext:
    """Context extracted from the editor for completion."""

    prefix: str  # Code before cursor
    suffix: str  # Code after cursor (for FIM)
    language: str  # e.g. "python", "typescript", "rust"
    filename: str  # e.g. "app.py"
    line_number: int  # 0-indexed
    column: int  # 0-indexed
    imports: List[str] = field(default_factory=list)
    function_signatures: List[str] = field(default_factory=list)
    project_context: str = ""  # Brief project description


@dataclass
class CompletionResult:
    """A single completion suggestion."""

    text: str  # The completion text to insert
    display_text: str  # Truncated for ghost text display
    confidence: float  # 0.0 – 1.0
    model: str  # Which model generated this
    latency_ms: float  # How long it took
    is_multiline: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def first_line(self) -> str:
        return self.text.split("\n")[0]


class CompletionCache:
    """LRU cache for completion results keyed by context hash."""

    def __init__(self, max_size: int = 256) -> None:
        self._cache: Dict[str, Tuple[CompletionResult, float]] = {}
        self._max_size = max_size
        self._lock = threading.Lock()

    def _key(self, ctx: CompletionContext) -> str:
        raw = f"{ctx.language}|{ctx.filename}|{ctx.prefix[-200:]}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, ctx: CompletionContext, ttl: float = 30.0) -> Optional[CompletionResult]:
        key = self._key(ctx)
        with self._lock:
            entry = self._cache.get(key)
            if entry and (time.monotonic() - entry[1]) < ttl:
                return entry[0]
        return None

    def put(self, ctx: CompletionContext, result: CompletionResult) -> None:
        key = self._key(ctx)
        with self._lock:
            if len(self._cache) >= self._max_size:
                # Evict oldest entry
                oldest = min(self._cache.items(), key=lambda x: x[1][1])
                del self._cache[oldest[0]]
            self._cache[key] = (result, time.monotonic())

    def invalidate(self) -> None:
        with self._lock:
            self._cache.clear()


class InlineCompletionEngine:
    """Provides real-time inline code completions.

    Usage::

        engine = InlineCompletionEngine()

        ctx = CompletionContext(
            prefix="def fibonacci(n):\\n    if n <= 1:\\n        return n\\n    ",
            suffix="",
            language="python",
            filename="math_utils.py",
            line_number=3,
            column=4,
        )

        result = engine.complete(ctx)
        if result:
            print(result.text)  # "return fibonacci(n-1) + fibonacci(n-2)"
    """

    # Minimum prefix length before triggering completion
    MIN_PREFIX_LENGTH = 10
    # Debounce delay in seconds
    DEBOUNCE_DELAY = 0.3

    def __init__(
        self,
        router: Optional[MultiModelRouter] = None,
        debounce_ms: int = 300,
    ) -> None:
        self._router = router or MultiModelRouter(
            RouterConfig(primary_model="gpt-4.1-nano", fallback_model="gpt-4.1-mini")
        )
        self._cache = CompletionCache()
        self._debounce_ms = debounce_ms
        self._pending_timer: Optional[threading.Timer] = None
        self._pending_lock = threading.Lock()

        # Telemetry
        self._total_requests = 0
        self._accepted = 0
        self._rejected = 0

    def complete(
        self,
        ctx: CompletionContext,
        multiline: bool = False,
    ) -> Optional[CompletionResult]:
        """Synchronously generate a completion for the given context.

        Args:
            ctx: The editor context at the cursor position.
            multiline: Whether to request a multi-line completion.

        Returns:
            A CompletionResult or None if no meaningful completion is available.
        """
        if len(ctx.prefix.strip()) < self.MIN_PREFIX_LENGTH:
            return None

        # Check cache first
        cached = self._cache.get(ctx)
        if cached:
            return cached

        self._total_requests += 1
        start = time.monotonic()

        prompt = self._build_prompt(ctx, multiline)
        system = self._build_system(ctx)

        try:
            text = self._router.complete(
                prompt,
                task=TaskType.CODE_COMPLETION,
                complexity=2,
                system=system,
            )
            text = self._post_process(text, ctx)
            if not text:
                return None

            result = CompletionResult(
                text=text,
                display_text=text[:80] + ("…" if len(text) > 80 else ""),
                confidence=0.85,
                model=self._router.config.primary_model,
                latency_ms=(time.monotonic() - start) * 1000,
                is_multiline="\n" in text,
            )
            self._cache.put(ctx, result)
            return result

        except Exception as exc:
            log.debug("Completion failed: %s", exc)
            return None

    def complete_async(
        self,
        ctx: CompletionContext,
        callback: Callable[[Optional[CompletionResult]], None],
        multiline: bool = False,
    ) -> None:
        """Debounced async completion — calls callback when result is ready.

        Args:
            ctx: Editor context.
            callback: Called with the CompletionResult (or None).
            multiline: Whether to request multi-line completion.
        """
        with self._pending_lock:
            if self._pending_timer:
                self._pending_timer.cancel()

            delay = self._debounce_ms / 1000.0

            def _run() -> None:
                result = self.complete(ctx, multiline)
                callback(result)

            self._pending_timer = threading.Timer(delay, _run)
            self._pending_timer.daemon = True
            self._pending_timer.start()

    def accept(self) -> None:
        """Record that the user accepted a completion."""
        self._accepted += 1

    def reject(self) -> None:
        """Record that the user rejected a completion."""
        self._rejected += 1

    @property
    def acceptance_rate(self) -> float:
        """Fraction of completions accepted by the user."""
        total = self._accepted + self._rejected
        return self._accepted / total if total > 0 else 0.0

    def telemetry(self) -> Dict[str, Any]:
        return {
            "total_requests": self._total_requests,
            "accepted": self._accepted,
            "rejected": self._rejected,
            "acceptance_rate": round(self.acceptance_rate, 3),
        }

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    def _build_system(self, ctx: CompletionContext) -> str:
        return (
            f"You are an expert {ctx.language} programmer providing inline code completions. "
            "Complete the code at the cursor position. "
            "Return ONLY the completion text — no explanations, no markdown fences, "
            "no repeating of the existing code. "
            "The completion should be syntactically correct and follow the existing style."
        )

    def _build_prompt(self, ctx: CompletionContext, multiline: bool) -> str:
        lines = [
            f"File: {ctx.filename}",
            f"Language: {ctx.language}",
        ]

        if ctx.imports:
            lines.append(f"Imports: {', '.join(ctx.imports[:5])}")

        if ctx.project_context:
            lines.append(f"Project: {ctx.project_context}")

        # Use FIM (fill-in-the-middle) format when suffix is available
        if ctx.suffix.strip():
            lines.extend(
                [
                    "",
                    "### Code before cursor:",
                    ctx.prefix[-600:],  # Last 600 chars of prefix
                    "",
                    "### Code after cursor:",
                    ctx.suffix[:200],
                    "",
                    f"### Complete the code at the cursor position ({'multi-line' if multiline else 'single line'}):",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "### Code:",
                    ctx.prefix[-800:],
                    "",
                    f"### Continue ({'multi-line block' if multiline else 'next line only'}):",
                ]
            )

        return "\n".join(lines)

    def _post_process(self, text: str, ctx: CompletionContext) -> str:
        """Clean up the raw model output."""
        # Strip markdown code fences
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
        text = re.sub(r"\n?```$", "", text.strip())

        # Remove any repetition of the prefix
        prefix_tail = ctx.prefix[-50:].strip()
        if text.startswith(prefix_tail):
            text = text[len(prefix_tail) :]

        # Trim to reasonable length
        lines = text.split("\n")
        if len(lines) > 20:
            lines = lines[:20]
        text = "\n".join(lines)

        return text.strip()


# ------------------------------------------------------------------
# Language-aware context extractor
# ------------------------------------------------------------------


class ContextExtractor:
    """Extracts structured context from raw editor state."""

    _IMPORT_PATTERNS = {
        "python": re.compile(r"^(?:import|from)\s+(\S+)", re.MULTILINE),
        "typescript": re.compile(r"^import\s+.+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
        "javascript": re.compile(
            r"^(?:import\s+.+from\s+['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\))", re.MULTILINE
        ),
        "rust": re.compile(r"^use\s+(\S+)", re.MULTILINE),
        "go": re.compile(r"^import\s+[\"](\S+)[\"]", re.MULTILINE),
    }

    _FUNCTION_PATTERNS = {
        "python": re.compile(r"^def\s+(\w+)\s*\([^)]*\)", re.MULTILINE),
        "typescript": re.compile(r"(?:function|async function|const\s+\w+\s*=\s*(?:async\s*)?\()", re.MULTILINE),
        "rust": re.compile(r"^(?:pub\s+)?fn\s+(\w+)", re.MULTILINE),
    }

    @classmethod
    def extract(
        cls,
        full_code: str,
        cursor_offset: int,
        language: str,
        filename: str,
        project_context: str = "",
    ) -> CompletionContext:
        """Extract a CompletionContext from raw editor state.

        Args:
            full_code: The complete file content.
            cursor_offset: Character offset of the cursor.
            language: Programming language identifier.
            filename: The file's name/path.
            project_context: Brief project description.

        Returns:
            A populated CompletionContext.
        """
        prefix = full_code[:cursor_offset]
        suffix = full_code[cursor_offset:]

        lines_before = prefix.split("\n")
        line_number = len(lines_before) - 1
        column = len(lines_before[-1])

        # Extract imports
        import_pat = cls._IMPORT_PATTERNS.get(language)
        if import_pat:
            raw_imports = import_pat.findall(prefix)
            # findall returns strings or tuples depending on group count
            imports = [
                (m[0] if isinstance(m, tuple) else m).rstrip(";")
                for m in raw_imports
                if (m[0] if isinstance(m, tuple) else m)
            ]
        else:
            imports = []

        # Extract function signatures
        fn_pat = cls._FUNCTION_PATTERNS.get(language)
        fn_sigs = fn_pat.findall(prefix) if fn_pat else []

        return CompletionContext(
            prefix=prefix,
            suffix=suffix,
            language=language,
            filename=filename,
            line_number=line_number,
            column=column,
            imports=imports[:10],
            function_signatures=fn_sigs[:5],
            project_context=project_context,
        )
