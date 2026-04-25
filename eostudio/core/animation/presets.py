"""Built-in animation presets — fadeIn, slideUp, scaleIn, bounce, etc."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from eostudio.core.animation.keyframe import EasingFunction, KeyframeTrack
from eostudio.core.animation.timeline import AnimationClip, Direction, FillMode


@dataclass
class AnimationPreset:
    """A reusable animation preset that can be applied to any target."""
    name: str
    category: str
    duration: float
    tracks_config: List[Dict[str, Any]]
    description: str = ""

    def apply(self, target_id: str, delay: float = 0.0,
              duration: Optional[float] = None) -> AnimationClip:
        d = duration or self.duration
        clip = AnimationClip(target_id=target_id, duration=d, delay=delay,
                             fill_mode=FillMode.FORWARDS, label=self.name)
        for tc in self.tracks_config:
            track = clip.add_track(tc["property"])
            easing = tc.get("easing", EasingFunction.EASE_OUT)
            keyframes = tc.get("keyframes", [])
            if keyframes:
                for kf in keyframes:
                    track.add_keyframe(kf["time"] * d, kf["value"], kf.get("easing", easing))
            else:
                track.add_keyframe(0, tc["from"], easing)
                track.add_keyframe(d, tc["to"], easing)
        return clip

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "duration": self.duration,
            "description": self.description,
            "tracks": self.tracks_config,
        }


# ---------------------------------------------------------------------------
# Preset definitions
# ---------------------------------------------------------------------------

PRESETS: Dict[str, AnimationPreset] = {}


def _register(preset: AnimationPreset) -> AnimationPreset:
    PRESETS[preset.name] = preset
    return preset


# ---- Fade ----
_register(AnimationPreset("fadeIn", "entrance", 0.5, [
    {"property": "opacity", "from": 0.0, "to": 1.0, "easing": EasingFunction.EASE_OUT},
], description="Fade in from transparent"))

_register(AnimationPreset("fadeOut", "exit", 0.5, [
    {"property": "opacity", "from": 1.0, "to": 0.0, "easing": EasingFunction.EASE_IN},
], description="Fade out to transparent"))

_register(AnimationPreset("fadeInUp", "entrance", 0.6, [
    {"property": "opacity", "from": 0.0, "to": 1.0, "easing": EasingFunction.EASE_OUT},
    {"property": "y", "from": 30.0, "to": 0.0, "easing": EasingFunction.EASE_OUT},
], description="Fade in while sliding up"))

_register(AnimationPreset("fadeInDown", "entrance", 0.6, [
    {"property": "opacity", "from": 0.0, "to": 1.0, "easing": EasingFunction.EASE_OUT},
    {"property": "y", "from": -30.0, "to": 0.0, "easing": EasingFunction.EASE_OUT},
], description="Fade in while sliding down"))

_register(AnimationPreset("fadeInLeft", "entrance", 0.6, [
    {"property": "opacity", "from": 0.0, "to": 1.0, "easing": EasingFunction.EASE_OUT},
    {"property": "x", "from": -30.0, "to": 0.0, "easing": EasingFunction.EASE_OUT},
], description="Fade in while sliding from left"))

_register(AnimationPreset("fadeInRight", "entrance", 0.6, [
    {"property": "opacity", "from": 0.0, "to": 1.0, "easing": EasingFunction.EASE_OUT},
    {"property": "x", "from": 30.0, "to": 0.0, "easing": EasingFunction.EASE_OUT},
], description="Fade in while sliding from right"))

# ---- Slide ----
_register(AnimationPreset("slideUp", "entrance", 0.5, [
    {"property": "y", "from": 100.0, "to": 0.0, "easing": EasingFunction.EASE_OUT_CUBIC},
], description="Slide up from below"))

_register(AnimationPreset("slideDown", "entrance", 0.5, [
    {"property": "y", "from": -100.0, "to": 0.0, "easing": EasingFunction.EASE_OUT_CUBIC},
], description="Slide down from above"))

_register(AnimationPreset("slideLeft", "entrance", 0.5, [
    {"property": "x", "from": 100.0, "to": 0.0, "easing": EasingFunction.EASE_OUT_CUBIC},
], description="Slide in from right"))

_register(AnimationPreset("slideRight", "entrance", 0.5, [
    {"property": "x", "from": -100.0, "to": 0.0, "easing": EasingFunction.EASE_OUT_CUBIC},
], description="Slide in from left"))

# ---- Scale ----
_register(AnimationPreset("scaleIn", "entrance", 0.4, [
    {"property": "scale", "from": 0.0, "to": 1.0, "easing": EasingFunction.EASE_OUT_BACK},
    {"property": "opacity", "from": 0.0, "to": 1.0, "easing": EasingFunction.EASE_OUT},
], description="Scale up from zero with slight overshoot"))

_register(AnimationPreset("scaleOut", "exit", 0.3, [
    {"property": "scale", "from": 1.0, "to": 0.0, "easing": EasingFunction.EASE_IN_BACK},
    {"property": "opacity", "from": 1.0, "to": 0.0, "easing": EasingFunction.EASE_IN},
], description="Scale down to zero"))

_register(AnimationPreset("popIn", "entrance", 0.4, [
    {"property": "scale", "from": 0.5, "to": 1.0, "easing": EasingFunction.EASE_OUT_BACK},
    {"property": "opacity", "from": 0.0, "to": 1.0, "easing": EasingFunction.EASE_OUT},
], description="Pop in with bounce-back"))

# ---- Rotate ----
_register(AnimationPreset("rotateIn", "entrance", 0.6, [
    {"property": "rotation", "from": -180.0, "to": 0.0, "easing": EasingFunction.EASE_OUT_CUBIC},
    {"property": "opacity", "from": 0.0, "to": 1.0, "easing": EasingFunction.EASE_OUT},
], description="Rotate in from -180 degrees"))

_register(AnimationPreset("spin", "attention", 1.0, [
    {"property": "rotation", "from": 0.0, "to": 360.0, "easing": EasingFunction.LINEAR},
], description="Full 360 spin"))

# ---- Bounce ----
_register(AnimationPreset("bounce", "attention", 0.8, [
    {"property": "y", "keyframes": [
        {"time": 0.0, "value": 0.0, "easing": EasingFunction.EASE_OUT},
        {"time": 0.25, "value": -20.0, "easing": EasingFunction.EASE_IN_OUT},
        {"time": 0.5, "value": 0.0, "easing": EasingFunction.EASE_OUT_BOUNCE},
        {"time": 0.75, "value": -8.0, "easing": EasingFunction.EASE_IN_OUT},
        {"time": 1.0, "value": 0.0, "easing": EasingFunction.EASE_OUT},
    ]},
], description="Bouncing effect"))

_register(AnimationPreset("bounceIn", "entrance", 0.75, [
    {"property": "scale", "keyframes": [
        {"time": 0.0, "value": 0.3, "easing": EasingFunction.EASE_OUT},
        {"time": 0.5, "value": 1.05, "easing": EasingFunction.EASE_OUT},
        {"time": 0.7, "value": 0.95, "easing": EasingFunction.EASE_IN_OUT},
        {"time": 1.0, "value": 1.0, "easing": EasingFunction.EASE_OUT},
    ]},
    {"property": "opacity", "from": 0.0, "to": 1.0, "easing": EasingFunction.EASE_OUT},
], description="Bounce in with elastic scale"))

# ---- Attention ----
_register(AnimationPreset("pulse", "attention", 1.0, [
    {"property": "scale", "keyframes": [
        {"time": 0.0, "value": 1.0, "easing": EasingFunction.EASE_IN_OUT},
        {"time": 0.5, "value": 1.05, "easing": EasingFunction.EASE_IN_OUT},
        {"time": 1.0, "value": 1.0, "easing": EasingFunction.EASE_IN_OUT},
    ]},
], description="Subtle pulsing scale"))

_register(AnimationPreset("shake", "attention", 0.6, [
    {"property": "x", "keyframes": [
        {"time": 0.0, "value": 0.0, "easing": EasingFunction.LINEAR},
        {"time": 0.1, "value": -10.0, "easing": EasingFunction.LINEAR},
        {"time": 0.2, "value": 10.0, "easing": EasingFunction.LINEAR},
        {"time": 0.3, "value": -10.0, "easing": EasingFunction.LINEAR},
        {"time": 0.4, "value": 10.0, "easing": EasingFunction.LINEAR},
        {"time": 0.5, "value": -5.0, "easing": EasingFunction.LINEAR},
        {"time": 1.0, "value": 0.0, "easing": EasingFunction.EASE_OUT},
    ]},
], description="Horizontal shake"))

_register(AnimationPreset("wobble", "attention", 1.0, [
    {"property": "rotation", "keyframes": [
        {"time": 0.0, "value": 0.0, "easing": EasingFunction.EASE_IN_OUT},
        {"time": 0.15, "value": -5.0, "easing": EasingFunction.EASE_IN_OUT},
        {"time": 0.3, "value": 3.0, "easing": EasingFunction.EASE_IN_OUT},
        {"time": 0.45, "value": -3.0, "easing": EasingFunction.EASE_IN_OUT},
        {"time": 0.6, "value": 2.0, "easing": EasingFunction.EASE_IN_OUT},
        {"time": 0.75, "value": -1.0, "easing": EasingFunction.EASE_IN_OUT},
        {"time": 1.0, "value": 0.0, "easing": EasingFunction.EASE_OUT},
    ]},
], description="Wobble rotation"))

_register(AnimationPreset("flash", "attention", 1.0, [
    {"property": "opacity", "keyframes": [
        {"time": 0.0, "value": 1.0, "easing": EasingFunction.LINEAR},
        {"time": 0.25, "value": 0.0, "easing": EasingFunction.LINEAR},
        {"time": 0.5, "value": 1.0, "easing": EasingFunction.LINEAR},
        {"time": 0.75, "value": 0.0, "easing": EasingFunction.LINEAR},
        {"time": 1.0, "value": 1.0, "easing": EasingFunction.LINEAR},
    ]},
], description="Flashing visibility"))

# ---- Scroll-triggered ----
_register(AnimationPreset("revealUp", "scroll", 0.8, [
    {"property": "opacity", "from": 0.0, "to": 1.0, "easing": EasingFunction.EASE_OUT},
    {"property": "y", "from": 60.0, "to": 0.0, "easing": EasingFunction.EASE_OUT_CUBIC},
], description="Reveal on scroll — slide up and fade in"))

_register(AnimationPreset("revealScale", "scroll", 0.6, [
    {"property": "opacity", "from": 0.0, "to": 1.0, "easing": EasingFunction.EASE_OUT},
    {"property": "scale", "from": 0.8, "to": 1.0, "easing": EasingFunction.EASE_OUT},
], description="Reveal on scroll — scale up and fade in"))

# ---- Transition ----
_register(AnimationPreset("crossFade", "transition", 0.3, [
    {"property": "opacity", "from": 0.0, "to": 1.0, "easing": EasingFunction.EASE_IN_OUT},
], description="Cross-fade transition"))

_register(AnimationPreset("slideTransition", "transition", 0.4, [
    {"property": "x", "from": 100.0, "to": 0.0, "easing": EasingFunction.EASE_OUT_CUBIC},
    {"property": "opacity", "from": 0.0, "to": 1.0, "easing": EasingFunction.EASE_OUT},
], description="Slide-in page transition"))

# ---- Layout ----
_register(AnimationPreset("layoutShift", "layout", 0.3, [
    {"property": "x", "from": 0.0, "to": 0.0, "easing": EasingFunction.EASE_IN_OUT},
    {"property": "y", "from": 0.0, "to": 0.0, "easing": EasingFunction.EASE_IN_OUT},
    {"property": "width", "from": 0.0, "to": 0.0, "easing": EasingFunction.EASE_IN_OUT},
    {"property": "height", "from": 0.0, "to": 0.0, "easing": EasingFunction.EASE_IN_OUT},
], description="Smooth layout position/size change"))


def get_preset(name: str) -> Optional[AnimationPreset]:
    """Get a preset by name, or None if not found."""
    return PRESETS.get(name)


def list_presets(category: Optional[str] = None) -> List[AnimationPreset]:
    """List all presets, optionally filtered by category."""
    presets = list(PRESETS.values())
    if category:
        presets = [p for p in presets if p.category == category]
    return presets


def preset_categories() -> List[str]:
    """Return all unique preset categories."""
    return sorted(set(p.category for p in PRESETS.values()))
