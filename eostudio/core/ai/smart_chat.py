"""Smart chat — context-aware conversational AI for editors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from eostudio.core.ai.llm_client import LLMClient, LLMConfig

_EDITOR_PROMPTS = {
    "cad": "You are a CAD design assistant integrated into EoStudio.",
    "ui": "You are a UI design assistant integrated into EoStudio.",
    "3d": "You are a 3D modeling assistant integrated into EoStudio.",
    "simulation": "You are a simulation assistant integrated into EoStudio.",
    "game": "You are a game design assistant integrated into EoStudio.",
}

_SAMPLE_PROMPTS: Dict[str, List[str]] = {
    "cad": [
        "Design a bracket for mounting a sensor",
        "Create a gear with 20 teeth",
        "Suggest tolerances for a snap-fit joint",
    ],
    "ui": [
        "Design a login form",
        "Create a dashboard layout",
        "Suggest color palette for a health app",
    ],
    "3d": [
        "Create a low-poly tree",
        "Design a sci-fi corridor",
        "Suggest lighting for an interior scene",
    ],
    "simulation": [
        "Design a PID controller for a DC motor",
        "Create a temperature control loop",
        "Simulate a mass-spring-damper system",
    ],
}

_DEFAULT_PROMPTS = [
    "Help me get started with my design",
    "What can you help me with?",
    "Show me an example project",
]


@dataclass
class EditorContext:
    editor_type: str = ""
    current_design: Optional[Dict[str, Any]] = None
    project_name: Optional[str] = None
    selected_components: Optional[List[Dict[str, Any]]] = None

    def summarize(self) -> str:
        parts = [f"Editor: {self.editor_type}"]
        if self.project_name:
            parts.append(f"Project: {self.project_name}")
        if self.current_design:
            parts.append(f"Design keys: {list(self.current_design.keys())}")
        if self.selected_components:
            types = [str(c.get("type", "unknown")) for c in self.selected_components]
            parts.append(f"Selected: {', '.join(types)}")
        return " | ".join(parts)


@dataclass
class ChatResponse:
    content: str = ""
    context_used: bool = False


class SmartChat:
    def __init__(self, editor_type: str = "", llm_client: Optional[LLMClient] = None) -> None:
        self.editor_type = editor_type
        system_prompt = _EDITOR_PROMPTS.get(editor_type, f"You are a design assistant for {editor_type} in EoStudio.")
        if llm_client is not None:
            self._client = llm_client
            self._client.config.system_prompt = system_prompt
        else:
            self._client = LLMClient(LLMConfig(system_prompt=system_prompt))
        self._history: List[Dict[str, str]] = []

    @property
    def client(self) -> LLMClient:
        return self._client

    @property
    def message_count(self) -> int:
        return len(self._history)

    def send_message(self, text: str, context: Optional[EditorContext] = None) -> ChatResponse:
        user_content = text
        context_used = False
        if context is not None:
            user_content = f"[Context: {context.summarize()}]\n{text}"
            context_used = True
        self._history.append({"role": "user", "content": user_content})
        messages = self._client._prepend_system(self._history)
        response_text = self._client.chat(messages)
        self._history.append({"role": "assistant", "content": response_text})
        return ChatResponse(content=response_text, context_used=context_used)

    def get_sample_prompts(self) -> List[str]:
        return _SAMPLE_PROMPTS.get(self.editor_type, _DEFAULT_PROMPTS)

    def clear_history(self) -> None:
        self._history.clear()
