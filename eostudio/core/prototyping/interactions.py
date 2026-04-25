"""Interaction system — click, hover, scroll, drag triggers and actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class InteractionTrigger(Enum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    HOVER_IN = "hover_in"
    HOVER_OUT = "hover_out"
    MOUSE_DOWN = "mouse_down"
    MOUSE_UP = "mouse_up"
    SCROLL_INTO_VIEW = "scroll_into_view"
    SCROLL_OUT_VIEW = "scroll_out_view"
    DRAG_START = "drag_start"
    DRAG_END = "drag_end"
    LONG_PRESS = "long_press"
    KEY_PRESS = "key_press"
    FOCUS = "focus"
    BLUR = "blur"
    VALUE_CHANGE = "value_change"
    TIMER = "timer"
    ON_MOUNT = "on_mount"


class InteractionAction(Enum):
    NAVIGATE = "navigate"
    OPEN_OVERLAY = "open_overlay"
    CLOSE_OVERLAY = "close_overlay"
    TOGGLE_OVERLAY = "toggle_overlay"
    PLAY_ANIMATION = "play_animation"
    STOP_ANIMATION = "stop_animation"
    SET_VARIABLE = "set_variable"
    TOGGLE_VARIABLE = "toggle_variable"
    INCREMENT_VARIABLE = "increment_variable"
    SHOW_COMPONENT = "show_component"
    HIDE_COMPONENT = "hide_component"
    TOGGLE_VISIBILITY = "toggle_visibility"
    SCROLL_TO = "scroll_to"
    OPEN_URL = "open_url"
    PLAY_SOUND = "play_sound"
    VIBRATE = "vibrate"
    COPY_TEXT = "copy_text"
    CUSTOM = "custom"


@dataclass
class Interaction:
    """A single interaction binding a trigger to an action on a target component."""
    id: str
    source_id: str  # Component that triggers the interaction
    trigger: InteractionTrigger
    action: InteractionAction
    target_id: str = ""  # Target component or screen
    parameters: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None  # Variable-based condition
    delay: float = 0.0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "trigger": self.trigger.value,
            "action": self.action.value,
            "target_id": self.target_id,
            "parameters": self.parameters,
            "condition": self.condition,
            "delay": self.delay,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Interaction":
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            trigger=InteractionTrigger(data["trigger"]),
            action=InteractionAction(data["action"]),
            target_id=data.get("target_id", ""),
            parameters=data.get("parameters", {}),
            condition=data.get("condition"),
            delay=data.get("delay", 0),
            enabled=data.get("enabled", True),
        )


class InteractionManager:
    """Manages all interactions in a prototype and dispatches events."""

    def __init__(self) -> None:
        self._interactions: List[Interaction] = []
        self._listeners: Dict[str, List[Callable[[Interaction, Dict[str, Any]], None]]] = {}
        self._variables: Dict[str, Any] = {}

    def add_interaction(self, interaction: Interaction) -> None:
        self._interactions.append(interaction)

    def remove_interaction(self, interaction_id: str) -> None:
        self._interactions = [i for i in self._interactions if i.id != interaction_id]

    def get_interactions_for(self, source_id: str,
                             trigger: Optional[InteractionTrigger] = None) -> List[Interaction]:
        results = [i for i in self._interactions if i.source_id == source_id and i.enabled]
        if trigger:
            results = [i for i in results if i.trigger == trigger]
        return results

    def set_variable(self, name: str, value: Any) -> None:
        self._variables[name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        return self._variables.get(name, default)

    def on_action(self, action: InteractionAction,
                  callback: Callable[[Interaction, Dict[str, Any]], None]) -> None:
        key = action.value
        if key not in self._listeners:
            self._listeners[key] = []
        self._listeners[key].append(callback)

    def dispatch(self, source_id: str, trigger: InteractionTrigger,
                 event_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Dispatch a trigger event and execute matching interactions."""
        results = []
        interactions = self.get_interactions_for(source_id, trigger)

        for interaction in interactions:
            # Check condition
            if interaction.condition and not self._evaluate_condition(interaction.condition):
                continue

            result = self._execute_action(interaction, event_data or {})
            results.append(result)

            # Notify listeners
            listeners = self._listeners.get(interaction.action.value, [])
            for listener in listeners:
                listener(interaction, result)

        return results

    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a simple condition like 'isLoggedIn == true'."""
        try:
            parts = condition.split()
            if len(parts) == 3:
                var_name, op, expected = parts
                actual = self._variables.get(var_name)
                if op == "==":
                    return str(actual) == expected
                if op == "!=":
                    return str(actual) != expected
                if op == ">":
                    return float(actual or 0) > float(expected)
                if op == "<":
                    return float(actual or 0) < float(expected)
            elif len(parts) == 1:
                return bool(self._variables.get(parts[0]))
        except (ValueError, TypeError):
            pass
        return True

    def _execute_action(self, interaction: Interaction,
                        event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an interaction action and return result."""
        action = interaction.action
        params = interaction.parameters
        result: Dict[str, Any] = {
            "action": action.value,
            "target_id": interaction.target_id,
            "success": True,
        }

        if action == InteractionAction.SET_VARIABLE:
            var_name = params.get("variable", "")
            var_value = params.get("value")
            self._variables[var_name] = var_value
            result["variable"] = var_name
            result["value"] = var_value

        elif action == InteractionAction.TOGGLE_VARIABLE:
            var_name = params.get("variable", "")
            current = self._variables.get(var_name, False)
            self._variables[var_name] = not current
            result["variable"] = var_name
            result["value"] = not current

        elif action == InteractionAction.INCREMENT_VARIABLE:
            var_name = params.get("variable", "")
            increment = params.get("increment", 1)
            current = self._variables.get(var_name, 0)
            self._variables[var_name] = current + increment
            result["variable"] = var_name
            result["value"] = current + increment

        elif action == InteractionAction.NAVIGATE:
            result["screen"] = params.get("screen", interaction.target_id)
            result["transition"] = params.get("transition", "push")

        elif action in (InteractionAction.SHOW_COMPONENT, InteractionAction.HIDE_COMPONENT,
                        InteractionAction.TOGGLE_VISIBILITY):
            result["visibility_action"] = action.value

        elif action == InteractionAction.PLAY_ANIMATION:
            result["animation"] = params.get("animation", "")
            result["preset"] = params.get("preset", "fadeIn")

        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interactions": [i.to_dict() for i in self._interactions],
            "variables": dict(self._variables),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InteractionManager":
        manager = cls()
        for i_data in data.get("interactions", []):
            manager.add_interaction(Interaction.from_dict(i_data))
        manager._variables = data.get("variables", {})
        return manager
