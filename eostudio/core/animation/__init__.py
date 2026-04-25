"""Animation engine — keyframes, timelines, spring physics, and presets."""

from eostudio.core.animation.keyframe import (
    Keyframe,
    KeyframeTrack,
    EasingFunction,
    EASING_FUNCTIONS,
    interpolate,
)
from eostudio.core.animation.timeline import AnimationTimeline, AnimationClip
from eostudio.core.animation.spring import SpringSimulator, SpringConfig
from eostudio.core.animation.presets import AnimationPreset, PRESETS, get_preset

__all__ = [
    "Keyframe",
    "KeyframeTrack",
    "EasingFunction",
    "EASING_FUNCTIONS",
    "interpolate",
    "AnimationTimeline",
    "AnimationClip",
    "SpringSimulator",
    "SpringConfig",
    "AnimationPreset",
    "PRESETS",
    "get_preset",
]
