"""State machine for prototype logic — variables, conditions, and state transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class VariableType(Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    COLOR = "color"
    LIST = "list"
    OBJECT = "object"


@dataclass
class PrototypeVariable:
    """A variable in the prototype state machine."""
    name: str
    value: Any
    var_type: VariableType = VariableType.STRING
    description: str = ""
    persistent: bool = False  # survives screen navigation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "type": self.var_type.value,
            "description": self.description,
            "persistent": self.persistent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PrototypeVariable":
        return cls(
            name=data["name"],
            value=data["value"],
            var_type=VariableType(data.get("type", "string")),
            description=data.get("description", ""),
            persistent=data.get("persistent", False),
        )


@dataclass
class PrototypeState:
    """A state in the prototype state machine."""
    name: str
    screen_id: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)
    on_enter_actions: List[Dict[str, Any]] = field(default_factory=list)
    on_exit_actions: List[Dict[str, Any]] = field(default_factory=list)
    is_initial: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "screen_id": self.screen_id,
            "variables": self.variables,
            "on_enter_actions": self.on_enter_actions,
            "on_exit_actions": self.on_exit_actions,
            "is_initial": self.is_initial,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PrototypeState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class StateTransition:
    """A transition between prototype states."""
    from_state: str
    to_state: str
    trigger: str = ""  # event name or interaction ID
    condition: Optional[str] = None
    actions: List[Dict[str, Any]] = field(default_factory=list)
    guard: Optional[str] = None  # condition that must be true

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_state,
            "to": self.to_state,
            "trigger": self.trigger,
            "condition": self.condition,
            "actions": self.actions,
            "guard": self.guard,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateTransition":
        return cls(
            from_state=data["from"],
            to_state=data["to"],
            trigger=data.get("trigger", ""),
            condition=data.get("condition"),
            actions=data.get("actions", []),
            guard=data.get("guard"),
        )


class StateMachine:
    """Finite state machine for prototype logic and navigation flow."""

    def __init__(self, name: str = "Prototype") -> None:
        self.name = name
        self._states: Dict[str, PrototypeState] = {}
        self._transitions: List[StateTransition] = []
        self._variables: Dict[str, PrototypeVariable] = {}
        self._current_state: Optional[str] = None
        self._history: List[str] = []
        self._listeners: Dict[str, List[Callable[[str, str, Dict[str, Any]], None]]] = {
            "state_change": [],
            "variable_change": [],
        }

    @property
    def current_state(self) -> Optional[PrototypeState]:
        if self._current_state:
            return self._states.get(self._current_state)
        return None

    @property
    def state_name(self) -> str:
        return self._current_state or ""

    def add_state(self, state: PrototypeState) -> None:
        self._states[state.name] = state
        if state.is_initial and self._current_state is None:
            self._current_state = state.name

    def add_transition(self, transition: StateTransition) -> None:
        self._transitions.append(transition)

    def add_variable(self, variable: PrototypeVariable) -> None:
        self._variables[variable.name] = variable

    def set_variable(self, name: str, value: Any) -> None:
        if name in self._variables:
            old_value = self._variables[name].value
            self._variables[name].value = value
            for listener in self._listeners["variable_change"]:
                listener(name, old_value, {"new_value": value})
        else:
            self._variables[name] = PrototypeVariable(name=name, value=value)

    def get_variable(self, name: str, default: Any = None) -> Any:
        var = self._variables.get(name)
        return var.value if var else default

    def get_all_variables(self) -> Dict[str, Any]:
        return {name: var.value for name, var in self._variables.items()}

    def send_event(self, trigger: str, data: Optional[Dict[str, Any]] = None) -> bool:
        """Send an event/trigger to the state machine. Returns True if a transition occurred."""
        if not self._current_state:
            return False

        for transition in self._transitions:
            if transition.from_state != self._current_state:
                continue
            if transition.trigger != trigger:
                continue
            if transition.guard and not self._evaluate_guard(transition.guard):
                continue
            if transition.condition and not self._evaluate_guard(transition.condition):
                continue

            old_state = self._current_state
            # Execute exit actions
            current = self._states.get(old_state)
            if current:
                for action in current.on_exit_actions:
                    self._execute_action(action)

            # Execute transition actions
            for action in transition.actions:
                self._execute_action(action)

            # Enter new state
            self._current_state = transition.to_state
            self._history.append(old_state)

            new = self._states.get(transition.to_state)
            if new:
                for action in new.on_enter_actions:
                    self._execute_action(action)

            # Notify listeners
            for listener in self._listeners["state_change"]:
                listener(old_state, transition.to_state, data or {})

            return True
        return False

    def go_back(self) -> bool:
        """Navigate back to previous state."""
        if self._history:
            old = self._current_state
            self._current_state = self._history.pop()
            for listener in self._listeners["state_change"]:
                listener(old or "", self._current_state, {"back": True})
            return True
        return False

    def reset(self) -> None:
        """Reset to initial state."""
        self._history.clear()
        for state in self._states.values():
            if state.is_initial:
                self._current_state = state.name
                return
        if self._states:
            self._current_state = next(iter(self._states))

    def on_state_change(self, callback: Callable[[str, str, Dict[str, Any]], None]) -> None:
        self._listeners["state_change"].append(callback)

    def on_variable_change(self, callback: Callable[[str, Any, Dict[str, Any]], None]) -> None:
        self._listeners["variable_change"].append(callback)

    def _evaluate_guard(self, condition: str) -> bool:
        try:
            parts = condition.split()
            if len(parts) == 3:
                var_name, op, expected = parts
                actual = self.get_variable(var_name)
                if op == "==":
                    return str(actual) == expected
                if op == "!=":
                    return str(actual) != expected
                if op == ">":
                    return float(actual or 0) > float(expected)
                if op == "<":
                    return float(actual or 0) < float(expected)
                if op == ">=":
                    return float(actual or 0) >= float(expected)
                if op == "<=":
                    return float(actual or 0) <= float(expected)
            elif len(parts) == 1:
                return bool(self.get_variable(parts[0]))
        except (ValueError, TypeError):
            pass
        return True

    def _execute_action(self, action: Dict[str, Any]) -> None:
        action_type = action.get("type", "")
        if action_type == "set_variable":
            self.set_variable(action["variable"], action["value"])
        elif action_type == "increment":
            current = self.get_variable(action["variable"], 0)
            self.set_variable(action["variable"], current + action.get("amount", 1))
        elif action_type == "toggle":
            current = self.get_variable(action["variable"], False)
            self.set_variable(action["variable"], not current)

    def get_available_transitions(self) -> List[StateTransition]:
        """Get transitions available from the current state."""
        if not self._current_state:
            return []
        return [t for t in self._transitions if t.from_state == self._current_state]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "states": {n: s.to_dict() for n, s in self._states.items()},
            "transitions": [t.to_dict() for t in self._transitions],
            "variables": {n: v.to_dict() for n, v in self._variables.items()},
            "current_state": self._current_state,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateMachine":
        sm = cls(name=data.get("name", "Prototype"))
        for s_data in data.get("states", {}).values():
            sm.add_state(PrototypeState.from_dict(s_data))
        for t_data in data.get("transitions", []):
            sm.add_transition(StateTransition.from_dict(t_data))
        for v_data in data.get("variables", {}).values():
            sm.add_variable(PrototypeVariable.from_dict(v_data))
        sm._current_state = data.get("current_state")
        return sm
