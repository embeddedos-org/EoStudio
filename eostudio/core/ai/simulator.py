"""AI simulator — instability detection, controller recommendation, parameter suggestion."""

from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Optional

from eostudio.core.ai.llm_client import LLMClient, LLMConfig


class AISimulator:
    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self._client = llm_client or LLMClient(LLMConfig())

    def detect_instability(self, signals_dict: Dict[str, List[float]]) -> List[str]:
        warnings: List[str] = []
        for name, values in signals_dict.items():
            for i, v in enumerate(values):
                if math.isnan(v):
                    warnings.append(f"NaN detected in '{name}' at sample {i}")
                elif math.isinf(v):
                    warnings.append(f"Inf detected in '{name}' at sample {i}")
            finite = [v for v in values if math.isfinite(v)]
            if finite:
                if any(abs(v) > 1e6 for v in finite):
                    warnings.append(f"Signal '{name}' contains extreme values (>1e6)")
                if len(finite) >= 5:
                    diffs = [finite[i + 1] - finite[i] for i in range(len(finite) - 1)]
                    if all(d > 0 for d in diffs) and (finite[-1] - finite[0]) > 10 * max(abs(finite[0]), 1):
                        warnings.append(f"Signal '{name}' shows monotonically growing trend")
        return warnings

    def recommend_controller(self, description: str) -> Dict[str, Any]:
        messages = [{"role": "user", "content": (
            f"Recommend a controller for this system as JSON with keys: "
            f"controller_type, gains (dict with Kp, Ki, Kd), reasoning.\n"
            f"System: {description}"
        )}]
        try:
            raw = self._client.chat(messages)
            result = json.loads(raw)
            if "controller_type" in result and "gains" in result:
                return result
        except Exception:
            pass
        return {
            "controller_type": "PID",
            "gains": {"Kp": 1.0, "Ki": 0.1, "Kd": 0.05},
            "reasoning": "Default PID parameters — tune based on system response.",
        }

    def suggest_parameters(self, model_dict: Dict[str, Any]) -> Dict[str, Any]:
        messages = [{"role": "user", "content": (
            f"Suggest simulation parameters as JSON with keys: dt, duration, block_parameters, reasoning.\n"
            f"Model: {json.dumps(model_dict, indent=2)}"
        )}]
        try:
            raw = self._client.chat(messages)
            result = json.loads(raw)
            if "dt" in result:
                return result
        except Exception:
            pass
        return self._default_parameters(model_dict)

    @staticmethod
    def _default_parameters(model_dict: Dict[str, Any]) -> Dict[str, Any]:
        n_blocks = len(model_dict.get("blocks", []))
        return {
            "dt": 0.01,
            "duration": 10.0,
            "block_parameters": {},
            "reasoning": f"Default parameters for model with {n_blocks} blocks.",
        }
