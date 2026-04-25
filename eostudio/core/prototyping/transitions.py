"""Screen transitions — push, fade, slide, dissolve, and custom transitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TransitionType(Enum):
    NONE = "none"
    FADE = "fade"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    PUSH = "push"
    POP = "pop"
    DISSOLVE = "dissolve"
    SCALE = "scale"
    FLIP_HORIZONTAL = "flip_horizontal"
    FLIP_VERTICAL = "flip_vertical"
    COVER_UP = "cover_up"
    REVEAL_DOWN = "reveal_down"
    SHARED_ELEMENT = "shared_element"
    CUSTOM = "custom"


class TransitionDirection(Enum):
    FORWARD = "forward"
    BACKWARD = "backward"


@dataclass
class ScreenTransition:
    """A transition between two screens in a prototype."""
    from_screen: str
    to_screen: str
    transition_type: TransitionType = TransitionType.PUSH
    direction: TransitionDirection = TransitionDirection.FORWARD
    duration: float = 0.3
    easing: str = "ease_in_out"
    shared_elements: List[str] = field(default_factory=list)
    custom_keyframes: Optional[Dict[str, Any]] = None

    def get_css_animation(self) -> Dict[str, str]:
        """Generate CSS animation properties for this transition."""
        animations: Dict[TransitionType, Dict[str, str]] = {
            TransitionType.FADE: {
                "enter": "opacity: 0 -> 1",
                "exit": "opacity: 1 -> 0",
                "css_enter": "animation: fadeIn {d}s {e}",
                "css_exit": "animation: fadeOut {d}s {e}",
            },
            TransitionType.SLIDE_LEFT: {
                "enter": "transform: translateX(100%) -> translateX(0)",
                "exit": "transform: translateX(0) -> translateX(-100%)",
                "css_enter": "animation: slideInRight {d}s {e}",
                "css_exit": "animation: slideOutLeft {d}s {e}",
            },
            TransitionType.SLIDE_RIGHT: {
                "enter": "transform: translateX(-100%) -> translateX(0)",
                "exit": "transform: translateX(0) -> translateX(100%)",
                "css_enter": "animation: slideInLeft {d}s {e}",
                "css_exit": "animation: slideOutRight {d}s {e}",
            },
            TransitionType.SLIDE_UP: {
                "enter": "transform: translateY(100%) -> translateY(0)",
                "exit": "transform: translateY(0) -> translateY(-100%)",
                "css_enter": "animation: slideInUp {d}s {e}",
                "css_exit": "animation: slideOutUp {d}s {e}",
            },
            TransitionType.SLIDE_DOWN: {
                "enter": "transform: translateY(-100%) -> translateY(0)",
                "exit": "transform: translateY(0) -> translateY(100%)",
                "css_enter": "animation: slideInDown {d}s {e}",
                "css_exit": "animation: slideOutDown {d}s {e}",
            },
            TransitionType.SCALE: {
                "enter": "transform: scale(0.8); opacity: 0 -> transform: scale(1); opacity: 1",
                "exit": "transform: scale(1); opacity: 1 -> transform: scale(0.8); opacity: 0",
                "css_enter": "animation: scaleIn {d}s {e}",
                "css_exit": "animation: scaleOut {d}s {e}",
            },
            TransitionType.DISSOLVE: {
                "enter": "opacity: 0; filter: blur(4px) -> opacity: 1; filter: blur(0)",
                "exit": "opacity: 1; filter: blur(0) -> opacity: 0; filter: blur(4px)",
                "css_enter": "animation: dissolveIn {d}s {e}",
                "css_exit": "animation: dissolveOut {d}s {e}",
            },
        }

        anim_data = animations.get(self.transition_type, animations[TransitionType.FADE])
        result = {}
        for key, val in anim_data.items():
            if key.startswith("css_"):
                result[key] = val.format(d=self.duration, e=self.easing.replace("_", "-"))
            else:
                result[key] = val
        return result

    def generate_framer_motion_props(self) -> Dict[str, Any]:
        """Generate Framer Motion transition props."""
        variants: Dict[TransitionType, Dict[str, Any]] = {
            TransitionType.FADE: {
                "initial": {"opacity": 0},
                "animate": {"opacity": 1},
                "exit": {"opacity": 0},
            },
            TransitionType.SLIDE_LEFT: {
                "initial": {"x": "100%"},
                "animate": {"x": 0},
                "exit": {"x": "-100%"},
            },
            TransitionType.SLIDE_RIGHT: {
                "initial": {"x": "-100%"},
                "animate": {"x": 0},
                "exit": {"x": "100%"},
            },
            TransitionType.SLIDE_UP: {
                "initial": {"y": "100%"},
                "animate": {"y": 0},
                "exit": {"y": "-100%"},
            },
            TransitionType.SLIDE_DOWN: {
                "initial": {"y": "-100%"},
                "animate": {"y": 0},
                "exit": {"y": "100%"},
            },
            TransitionType.SCALE: {
                "initial": {"scale": 0.8, "opacity": 0},
                "animate": {"scale": 1, "opacity": 1},
                "exit": {"scale": 0.8, "opacity": 0},
            },
            TransitionType.DISSOLVE: {
                "initial": {"opacity": 0, "filter": "blur(4px)"},
                "animate": {"opacity": 1, "filter": "blur(0px)"},
                "exit": {"opacity": 0, "filter": "blur(4px)"},
            },
        }

        props = variants.get(self.transition_type, variants[TransitionType.FADE])
        props["transition"] = {"duration": self.duration, "ease": self.easing.replace("_", "")}
        return props

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_screen": self.from_screen,
            "to_screen": self.to_screen,
            "type": self.transition_type.value,
            "direction": self.direction.value,
            "duration": self.duration,
            "easing": self.easing,
            "shared_elements": self.shared_elements,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScreenTransition":
        return cls(
            from_screen=data["from_screen"],
            to_screen=data["to_screen"],
            transition_type=TransitionType(data.get("type", "push")),
            direction=TransitionDirection(data.get("direction", "forward")),
            duration=data.get("duration", 0.3),
            easing=data.get("easing", "ease_in_out"),
            shared_elements=data.get("shared_elements", []),
        )
