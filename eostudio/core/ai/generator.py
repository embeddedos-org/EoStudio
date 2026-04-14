"""AI design generator — text-to-UI, text-to-3D, text-to-CAD."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from eostudio.core.ai.llm_client import LLMClient, LLMConfig


class AIDesignGenerator:
    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self._client = llm_client or LLMClient(LLMConfig())

    def text_to_ui(self, prompt: str) -> Dict[str, Any]:
        messages = [{"role": "user", "content": (
            f"Generate a UI design as JSON with keys: name, components (list of dicts with type/label), layout.\n"
            f"Prompt: {prompt}"
        )}]
        raw = self._client.chat(messages)
        try:
            result = json.loads(raw)
            if "components" in result:
                return result
        except (json.JSONDecodeError, TypeError):
            pass
        return {
            "name": "Untitled",
            "components": [],
            "layout": "vertical",
            "metadata": {"source": "fallback"},
        }

    def text_to_3d(self, prompt: str) -> Dict[str, Any]:
        messages = [{"role": "user", "content": (
            f"Generate a 3D scene as JSON with keys: name, objects.\n"
            f"Prompt: {prompt}"
        )}]
        raw = self._client.chat(messages)
        try:
            result = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            result = {"name": "Scene", "objects": []}
        result.setdefault("lights", [{"type": "ambient", "intensity": 0.5}])
        result.setdefault("camera", {"position": [0, 5, 10], "target": [0, 0, 0]})
        return result

    def text_to_cad(self, prompt: str) -> Dict[str, Any]:
        messages = [{"role": "user", "content": (
            f"Generate a CAD design as JSON with keys: name, features, parameters.\n"
            f"Prompt: {prompt}"
        )}]
        raw = self._client.chat(messages)
        try:
            result = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            result = {"name": "Part", "features": [], "parameters": {}}
        result.setdefault("units", "mm")
        return result

    def refine_design(self, original: Dict[str, Any], instruction: str) -> Dict[str, Any]:
        messages = [{"role": "user", "content": (
            f"Refine this design:\n{json.dumps(original, indent=2)}\n\n"
            f"Instruction: {instruction}\n"
            f"Return the updated design as JSON."
        )}]
        raw = self._client.chat(messages)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return original
