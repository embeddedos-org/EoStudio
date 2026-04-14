"""Design agent — conversational AI assistant for design tasks."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from eostudio.core.ai.llm_client import LLMClient, LLMConfig

_DOMAIN_PROMPTS = {
    "general": "You are a helpful design assistant for EoStudio.",
    "cad": "You are a CAD design expert. Help users with 3D modeling and engineering design.",
    "ui": "You are a UI/UX design expert. Help users build great interfaces.",
    "3d": "You are a 3D modeling expert. Help users create 3D scenes and objects.",
    "simulation": "You are a simulation expert. Help users build and tune simulation models.",
}


class DesignAgent:
    def __init__(self, domain: str = "general", endpoint: Optional[str] = None,
                 model: Optional[str] = None, provider: Optional[str] = None,
                 api_key: Optional[str] = None) -> None:
        self.domain = domain
        system_prompt = _DOMAIN_PROMPTS.get(domain, _DOMAIN_PROMPTS["general"])
        config = LLMConfig(
            provider=provider or "ollama",
            endpoint=endpoint,
            model=model or "llama3",
            api_key=api_key,
            system_prompt=system_prompt,
        )
        self._client = LLMClient(config)
        self._history: List[Dict[str, str]] = []

    @property
    def client(self) -> LLMClient:
        return self._client

    def ask(self, prompt: str) -> str:
        self._history.append({"role": "user", "content": prompt})
        messages = self._client._prepend_system(self._history)
        response = self._client.chat(messages)
        self._history.append({"role": "assistant", "content": response})
        return response

    def suggest_improvements(self, design_dict: Dict[str, Any]) -> List[str]:
        prompt = (
            f"Analyze this design and suggest improvements as a JSON array of strings:\n"
            f"{json.dumps(design_dict, indent=2)}"
        )
        messages = [{"role": "user", "content": prompt}]
        messages = self._client._prepend_system(messages)
        raw = self._client.chat(messages)
        try:
            result = json.loads(raw)
            if isinstance(result, list):
                return result
        except (json.JSONDecodeError, TypeError):
            pass
        return [raw] if raw else ["No suggestions available"]

    def set_domain(self, domain: str) -> None:
        self.domain = domain
        system_prompt = _DOMAIN_PROMPTS.get(domain, _DOMAIN_PROMPTS["general"])
        self._client.config.system_prompt = system_prompt

    def clear_history(self) -> None:
        self._history.clear()

    def generate_design_brief(self, prompt: str) -> Dict[str, Any]:
        messages = [{"role": "user", "content": (
            f"Generate a design brief as JSON with keys: name, type, components, layout.\n"
            f"Prompt: {prompt}"
        )}]
        messages = self._client._prepend_system(messages)
        raw = self._client.chat(messages)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {"name": "Untitled", "type": "unknown", "components": [], "layout": "vertical"}
