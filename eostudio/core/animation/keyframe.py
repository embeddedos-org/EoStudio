"""Keyframe and interpolation engine for EoStudio animations."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

NumericValue = Union[float, Tuple[float, ...], List[float]]


class EasingFunction(Enum):
    """Built-in easing functions."""
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    EASE_IN_QUAD = "ease_in_quad"
    EASE_OUT_QUAD = "ease_out_quad"
    EASE_IN_OUT_QUAD = "ease_in_out_quad"
    EASE_IN_CUBIC = "ease_in_cubic"
    EASE_OUT_CUBIC = "ease_out_cubic"
    EASE_IN_OUT_CUBIC = "ease_in_out_cubic"
    EASE_IN_QUART = "ease_in_quart"
    EASE_OUT_QUART = "ease_out_quart"
    EASE_IN_OUT_QUART = "ease_in_out_quart"
    EASE_IN_EXPO = "ease_in_expo"
    EASE_OUT_EXPO = "ease_out_expo"
    EASE_IN_OUT_EXPO = "ease_in_out_expo"
    EASE_IN_BACK = "ease_in_back"
    EASE_OUT_BACK = "ease_out_back"
    EASE_IN_OUT_BACK = "ease_in_out_back"
    EASE_IN_ELASTIC = "ease_in_elastic"
    EASE_OUT_ELASTIC = "ease_out_elastic"
    EASE_IN_OUT_ELASTIC = "ease_in_out_elastic"
    EASE_OUT_BOUNCE = "ease_out_bounce"
    CUBIC_BEZIER = "cubic_bezier"


def _bounce_out(t: float) -> float:
    if t < 1 / 2.75:
        return 7.5625 * t * t
    elif t < 2 / 2.75:
        t -= 1.5 / 2.75
        return 7.5625 * t * t + 0.75
    elif t < 2.5 / 2.75:
        t -= 2.25 / 2.75
        return 7.5625 * t * t + 0.9375
    else:
        t -= 2.625 / 2.75
        return 7.5625 * t * t + 0.984375


EASING_FUNCTIONS: Dict[EasingFunction, Callable[[float], float]] = {
    EasingFunction.LINEAR: lambda t: t,
    EasingFunction.EASE_IN: lambda t: t * t * t,
    EasingFunction.EASE_OUT: lambda t: 1 - (1 - t) ** 3,
    EasingFunction.EASE_IN_OUT: lambda t: 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2,
    EasingFunction.EASE_IN_QUAD: lambda t: t * t,
    EasingFunction.EASE_OUT_QUAD: lambda t: 1 - (1 - t) ** 2,
    EasingFunction.EASE_IN_OUT_QUAD: lambda t: 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2,
    EasingFunction.EASE_IN_CUBIC: lambda t: t ** 3,
    EasingFunction.EASE_OUT_CUBIC: lambda t: 1 - (1 - t) ** 3,
    EasingFunction.EASE_IN_OUT_CUBIC: lambda t: 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2,
    EasingFunction.EASE_IN_QUART: lambda t: t ** 4,
    EasingFunction.EASE_OUT_QUART: lambda t: 1 - (1 - t) ** 4,
    EasingFunction.EASE_IN_OUT_QUART: lambda t: 8 * t ** 4 if t < 0.5 else 1 - (-2 * t + 2) ** 4 / 2,
    EasingFunction.EASE_IN_EXPO: lambda t: 0.0 if t == 0 else 2 ** (10 * t - 10),
    EasingFunction.EASE_OUT_EXPO: lambda t: 1.0 if t == 1 else 1 - 2 ** (-10 * t),
    EasingFunction.EASE_IN_OUT_EXPO: lambda t: (
        0.0 if t == 0 else 1.0 if t == 1
        else 2 ** (20 * t - 10) / 2 if t < 0.5
        else (2 - 2 ** (-20 * t + 10)) / 2
    ),
    EasingFunction.EASE_IN_BACK: lambda t: 2.70158 * t ** 3 - 1.70158 * t ** 2,
    EasingFunction.EASE_OUT_BACK: lambda t: 1 + 2.70158 * (t - 1) ** 3 + 1.70158 * (t - 1) ** 2,
    EasingFunction.EASE_IN_OUT_BACK: lambda t: (
        ((2 * t) ** 2 * (3.5949095 * 2 * t - 2.5949095)) / 2 if t < 0.5
        else ((2 * t - 2) ** 2 * (3.5949095 * (2 * t - 2) + 2.5949095) + 2) / 2
    ),
    EasingFunction.EASE_IN_ELASTIC: lambda t: (
        0.0 if t == 0 else 1.0 if t == 1
        else -(2 ** (10 * t - 10)) * math.sin((t * 10 - 10.75) * (2 * math.pi) / 3)
    ),
    EasingFunction.EASE_OUT_ELASTIC: lambda t: (
        0.0 if t == 0 else 1.0 if t == 1
        else 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1
    ),
    EasingFunction.EASE_IN_OUT_ELASTIC: lambda t: (
        0.0 if t == 0 else 1.0 if t == 1
        else -(2 ** (20 * t - 10) * math.sin((20 * t - 11.125) * (2 * math.pi) / 4.5)) / 2 if t < 0.5
        else (2 ** (-20 * t + 10) * math.sin((20 * t - 11.125) * (2 * math.pi) / 4.5)) / 2 + 1
    ),
    EasingFunction.EASE_OUT_BOUNCE: _bounce_out,
}


def cubic_bezier(p1x: float, p1y: float, p2x: float, p2y: float) -> Callable[[float], float]:
    """Create a cubic-bezier easing function with control points (p1x, p1y) and (p2x, p2y)."""
    def _eval(t: float) -> float:
        # Newton-Raphson to solve for parameter from x, then evaluate y
        u = t
        for _ in range(8):
            x_est = 3 * p1x * u * (1 - u) ** 2 + 3 * p2x * (1 - u) * u ** 2 + u ** 3
            if abs(x_est - t) < 1e-6:
                break
            dx = 3 * p1x * (1 - u) ** 2 - 6 * p1x * u * (1 - u) + 3 * p2x * 2 * u * (1 - u) - 3 * p2x * u ** 2 + 3 * u ** 2
            if abs(dx) < 1e-6:
                break
            u -= (x_est - t) / dx
            u = max(0.0, min(1.0, u))
        return 3 * p1y * u * (1 - u) ** 2 + 3 * p2y * (1 - u) * u ** 2 + u ** 3
    return _eval


@dataclass
class Keyframe:
    """A single keyframe at a specific time with a value and easing."""
    time: float  # seconds
    value: NumericValue
    easing: EasingFunction = EasingFunction.EASE_IN_OUT
    bezier_points: Optional[Tuple[float, float, float, float]] = None

    def get_easing_fn(self) -> Callable[[float], float]:
        if self.easing == EasingFunction.CUBIC_BEZIER and self.bezier_points:
            return cubic_bezier(*self.bezier_points)
        return EASING_FUNCTIONS.get(self.easing, EASING_FUNCTIONS[EasingFunction.LINEAR])


@dataclass
class KeyframeTrack:
    """A track of keyframes for a single property (e.g., 'opacity', 'x', 'scale')."""
    property_name: str
    keyframes: List[Keyframe] = field(default_factory=list)

    def add_keyframe(self, time: float, value: NumericValue,
                     easing: EasingFunction = EasingFunction.EASE_IN_OUT,
                     bezier_points: Optional[Tuple[float, float, float, float]] = None) -> Keyframe:
        kf = Keyframe(time=time, value=value, easing=easing, bezier_points=bezier_points)
        self.keyframes.append(kf)
        self.keyframes.sort(key=lambda k: k.time)
        return kf

    def remove_keyframe(self, index: int) -> None:
        if 0 <= index < len(self.keyframes):
            self.keyframes.pop(index)

    def evaluate(self, time: float) -> NumericValue:
        if not self.keyframes:
            return 0.0
        if time <= self.keyframes[0].time:
            return self.keyframes[0].value
        if time >= self.keyframes[-1].time:
            return self.keyframes[-1].value

        for i in range(len(self.keyframes) - 1):
            k0, k1 = self.keyframes[i], self.keyframes[i + 1]
            if k0.time <= time <= k1.time:
                duration = k1.time - k0.time
                if duration == 0:
                    return k1.value
                t = (time - k0.time) / duration
                eased_t = k1.get_easing_fn()(t)
                return interpolate(k0.value, k1.value, eased_t)
        return self.keyframes[-1].value

    @property
    def duration(self) -> float:
        if not self.keyframes:
            return 0.0
        return self.keyframes[-1].time - self.keyframes[0].time

    def to_dict(self) -> Dict[str, Any]:
        return {
            "property": self.property_name,
            "keyframes": [
                {
                    "time": kf.time,
                    "value": kf.value if isinstance(kf.value, (int, float)) else list(kf.value),
                    "easing": kf.easing.value,
                    "bezier": kf.bezier_points,
                }
                for kf in self.keyframes
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KeyframeTrack":
        track = cls(property_name=data["property"])
        for kf_data in data.get("keyframes", []):
            val = kf_data["value"]
            if isinstance(val, list):
                val = tuple(val)
            easing = EasingFunction(kf_data.get("easing", "ease_in_out"))
            bezier = kf_data.get("bezier")
            if bezier:
                bezier = tuple(bezier)
            track.add_keyframe(kf_data["time"], val, easing, bezier)
        return track


def interpolate(a: NumericValue, b: NumericValue, t: float) -> NumericValue:
    """Linearly interpolate between two numeric values using factor t (0..1)."""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + (b - a) * t
    a_seq = a if isinstance(a, (list, tuple)) else [a]
    b_seq = b if isinstance(b, (list, tuple)) else [b]
    length = max(len(a_seq), len(b_seq))
    result = []
    for i in range(length):
        va = a_seq[i] if i < len(a_seq) else 0.0
        vb = b_seq[i] if i < len(b_seq) else 0.0
        result.append(va + (vb - va) * t)
    return tuple(result) if isinstance(a, tuple) else result
