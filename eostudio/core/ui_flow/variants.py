"""Component variants and states — hover, active, disabled, focus states."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ComponentState(Enum):
    DEFAULT = "default"
    HOVER = "hover"
    ACTIVE = "active"
    FOCUS = "focus"
    DISABLED = "disabled"
    PRESSED = "pressed"
    SELECTED = "selected"
    ERROR = "error"
    LOADING = "loading"


@dataclass
class StateOverride:
    """Property overrides for a specific component state."""
    state: ComponentState
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_css_selector(self, base_selector: str) -> str:
        state_map = {
            ComponentState.HOVER: ":hover",
            ComponentState.ACTIVE: ":active",
            ComponentState.FOCUS: ":focus",
            ComponentState.DISABLED: ":disabled",
            ComponentState.FOCUS: ":focus-visible",
        }
        pseudo = state_map.get(self.state, "")
        if pseudo:
            return f"{base_selector}{pseudo}"
        return f"{base_selector}[data-state=\"{self.state.value}\"]"

    def to_dict(self) -> Dict[str, Any]:
        return {"state": self.state.value, "properties": self.properties}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateOverride":
        return cls(state=ComponentState(data["state"]), properties=data.get("properties", {}))


@dataclass
class ComponentVariant:
    """A variant of a component with different properties (e.g. size, color scheme)."""
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    states: List[StateOverride] = field(default_factory=list)
    description: str = ""

    def get_state(self, state: ComponentState) -> Optional[StateOverride]:
        for s in self.states:
            if s.state == state:
                return s
        return None

    def add_state(self, state: ComponentState, **props: Any) -> StateOverride:
        override = StateOverride(state=state, properties=props)
        # Replace existing state if present
        self.states = [s for s in self.states if s.state != state]
        self.states.append(override)
        return override

    def resolve_properties(self, state: ComponentState = ComponentState.DEFAULT) -> Dict[str, Any]:
        """Get merged properties for a given state."""
        result = dict(self.properties)
        if state != ComponentState.DEFAULT:
            override = self.get_state(state)
            if override:
                result.update(override.properties)
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "properties": self.properties,
            "states": [s.to_dict() for s in self.states],
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComponentVariant":
        variant = cls(
            name=data["name"],
            properties=data.get("properties", {}),
            description=data.get("description", ""),
        )
        for s_data in data.get("states", []):
            variant.states.append(StateOverride.from_dict(s_data))
        return variant


@dataclass
class VariantSet:
    """A set of variants for a component type (e.g. Button has primary, secondary, ghost)."""
    component_type: str
    variants: List[ComponentVariant] = field(default_factory=list)
    default_variant: str = ""

    def add_variant(self, name: str, **props: Any) -> ComponentVariant:
        variant = ComponentVariant(name=name, properties=props)
        self.variants.append(variant)
        if not self.default_variant:
            self.default_variant = name
        return variant

    def get_variant(self, name: str) -> Optional[ComponentVariant]:
        for v in self.variants:
            if v.name == name:
                return v
        return None

    def variant_names(self) -> List[str]:
        return [v.name for v in self.variants]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_type": self.component_type,
            "default": self.default_variant,
            "variants": [v.to_dict() for v in self.variants],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VariantSet":
        vs = cls(component_type=data["component_type"],
                 default_variant=data.get("default", ""))
        for v_data in data.get("variants", []):
            vs.variants.append(ComponentVariant.from_dict(v_data))
        return vs

    @classmethod
    def create_button_variants(cls) -> "VariantSet":
        vs = cls(component_type="Button", default_variant="primary")
        primary = vs.add_variant("primary", bg="#2563eb", color="#ffffff",
                                 border_radius=8, padding="10px 20px", font_weight=600)
        primary.add_state(ComponentState.HOVER, bg="#1d4ed8")
        primary.add_state(ComponentState.ACTIVE, bg="#1e40af", transform="scale(0.98)")
        primary.add_state(ComponentState.DISABLED, bg="#93c5fd", opacity=0.6, cursor="not-allowed")
        primary.add_state(ComponentState.FOCUS, outline="2px solid #60a5fa", outline_offset="2px")

        secondary = vs.add_variant("secondary", bg="#f1f5f9", color="#1e293b",
                                   border="1px solid #cbd5e1", border_radius=8, padding="10px 20px")
        secondary.add_state(ComponentState.HOVER, bg="#e2e8f0")
        secondary.add_state(ComponentState.ACTIVE, bg="#cbd5e1")
        secondary.add_state(ComponentState.DISABLED, opacity=0.6, cursor="not-allowed")

        ghost = vs.add_variant("ghost", bg="transparent", color="#2563eb",
                               border_radius=8, padding="10px 20px")
        ghost.add_state(ComponentState.HOVER, bg="#eff6ff")
        ghost.add_state(ComponentState.ACTIVE, bg="#dbeafe")

        danger = vs.add_variant("danger", bg="#dc2626", color="#ffffff",
                                border_radius=8, padding="10px 20px", font_weight=600)
        danger.add_state(ComponentState.HOVER, bg="#b91c1c")
        danger.add_state(ComponentState.ACTIVE, bg="#991b1b")

        return vs

    @classmethod
    def create_input_variants(cls) -> "VariantSet":
        vs = cls(component_type="Input", default_variant="outlined")
        outlined = vs.add_variant("outlined", bg="#ffffff", border="1px solid #d1d5db",
                                  border_radius=6, padding="10px 12px", font_size=14)
        outlined.add_state(ComponentState.FOCUS, border_color="#2563eb",
                           box_shadow="0 0 0 3px rgba(37,99,235,0.1)")
        outlined.add_state(ComponentState.ERROR, border_color="#dc2626",
                           box_shadow="0 0 0 3px rgba(220,38,38,0.1)")
        outlined.add_state(ComponentState.DISABLED, bg="#f9fafb", opacity=0.6)

        filled = vs.add_variant("filled", bg="#f1f5f9", border="none",
                                border_radius=6, padding="10px 12px")
        filled.add_state(ComponentState.FOCUS, bg="#e2e8f0",
                         box_shadow="0 0 0 2px rgba(37,99,235,0.2)")

        return vs
