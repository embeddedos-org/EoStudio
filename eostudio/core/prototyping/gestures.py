"""Gesture recognition — swipe, pinch, long-press, and custom gestures."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class GestureType(Enum):
    TAP = "tap"
    DOUBLE_TAP = "double_tap"
    LONG_PRESS = "long_press"
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    PINCH_IN = "pinch_in"
    PINCH_OUT = "pinch_out"
    ROTATE = "rotate"
    PAN = "pan"
    DRAG = "drag"


@dataclass
class GestureEvent:
    """A detected gesture event with positional and timing data."""
    gesture_type: GestureType
    position: Tuple[float, float] = (0.0, 0.0)
    delta: Tuple[float, float] = (0.0, 0.0)
    velocity: Tuple[float, float] = (0.0, 0.0)
    scale: float = 1.0
    rotation: float = 0.0
    timestamp: float = 0.0
    target_id: str = ""
    phase: str = "end"  # start, move, end

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.gesture_type.value,
            "position": list(self.position),
            "delta": list(self.delta),
            "velocity": list(self.velocity),
            "scale": self.scale,
            "rotation": self.rotation,
            "target_id": self.target_id,
            "phase": self.phase,
        }


@dataclass
class GestureConfig:
    """Configuration for gesture detection thresholds."""
    swipe_threshold: float = 50.0       # minimum distance for swipe (px)
    swipe_velocity: float = 0.3         # minimum velocity for swipe (px/ms)
    long_press_duration: float = 500.0  # long press threshold (ms)
    double_tap_interval: float = 300.0  # max interval between taps (ms)
    pinch_threshold: float = 0.1        # minimum scale change for pinch
    rotation_threshold: float = 5.0     # minimum rotation for rotate gesture (degrees)


class GestureRecognizer:
    """Detects and dispatches gesture events from raw touch/mouse input."""

    def __init__(self, config: Optional[GestureConfig] = None) -> None:
        self.config = config or GestureConfig()
        self._listeners: Dict[GestureType, List[Callable[[GestureEvent], None]]] = {}
        self._touch_start: Optional[Tuple[float, float]] = None
        self._touch_start_time: float = 0.0
        self._last_tap_time: float = 0.0
        self._is_pressing: bool = False
        self._long_press_timer: Optional[Any] = None
        self._active_gestures: List[GestureEvent] = []

    def on_gesture(self, gesture_type: GestureType,
                   callback: Callable[[GestureEvent], None]) -> None:
        if gesture_type not in self._listeners:
            self._listeners[gesture_type] = []
        self._listeners[gesture_type].append(callback)

    def _emit(self, event: GestureEvent) -> None:
        self._active_gestures.append(event)
        for callback in self._listeners.get(event.gesture_type, []):
            callback(event)

    def on_touch_start(self, x: float, y: float, target_id: str = "") -> None:
        self._touch_start = (x, y)
        self._touch_start_time = time.time() * 1000
        self._is_pressing = True

    def on_touch_move(self, x: float, y: float, target_id: str = "") -> None:
        if not self._touch_start:
            return
        dx = x - self._touch_start[0]
        dy = y - self._touch_start[1]
        self._emit(GestureEvent(
            gesture_type=GestureType.PAN,
            position=(x, y),
            delta=(dx, dy),
            target_id=target_id,
            phase="move",
        ))

    def on_touch_end(self, x: float, y: float, target_id: str = "") -> None:
        if not self._touch_start:
            return

        now = time.time() * 1000
        duration = now - self._touch_start_time
        dx = x - self._touch_start[0]
        dy = y - self._touch_start[1]
        distance = (dx ** 2 + dy ** 2) ** 0.5

        if duration > 0:
            vx = dx / duration
            vy = dy / duration
        else:
            vx, vy = 0.0, 0.0

        velocity = (vx ** 2 + vy ** 2) ** 0.5

        # Long press
        if duration >= self.config.long_press_duration and distance < self.config.swipe_threshold:
            self._emit(GestureEvent(
                gesture_type=GestureType.LONG_PRESS,
                position=(x, y), target_id=target_id,
            ))
        # Swipe
        elif distance >= self.config.swipe_threshold and velocity >= self.config.swipe_velocity:
            if abs(dx) > abs(dy):
                gesture = GestureType.SWIPE_RIGHT if dx > 0 else GestureType.SWIPE_LEFT
            else:
                gesture = GestureType.SWIPE_DOWN if dy > 0 else GestureType.SWIPE_UP
            self._emit(GestureEvent(
                gesture_type=gesture,
                position=(x, y), delta=(dx, dy), velocity=(vx, vy),
                target_id=target_id,
            ))
        # Double tap
        elif now - self._last_tap_time < self.config.double_tap_interval:
            self._emit(GestureEvent(
                gesture_type=GestureType.DOUBLE_TAP,
                position=(x, y), target_id=target_id,
            ))
            self._last_tap_time = 0
        # Tap
        else:
            self._emit(GestureEvent(
                gesture_type=GestureType.TAP,
                position=(x, y), target_id=target_id,
            ))
            self._last_tap_time = now

        self._touch_start = None
        self._is_pressing = False

    def on_pinch(self, scale: float, target_id: str = "") -> None:
        if abs(scale - 1.0) >= self.config.pinch_threshold:
            gesture = GestureType.PINCH_OUT if scale > 1.0 else GestureType.PINCH_IN
            self._emit(GestureEvent(
                gesture_type=gesture,
                scale=scale, target_id=target_id,
            ))

    def on_rotate(self, angle: float, target_id: str = "") -> None:
        if abs(angle) >= self.config.rotation_threshold:
            self._emit(GestureEvent(
                gesture_type=GestureType.ROTATE,
                rotation=angle, target_id=target_id,
            ))

    def get_recent_gestures(self, count: int = 10) -> List[GestureEvent]:
        return self._active_gestures[-count:]

    def clear_history(self) -> None:
        self._active_gestures.clear()

    def generate_js_handler(self, gesture_type: GestureType,
                            action_code: str) -> str:
        """Generate JavaScript code for gesture detection."""
        handlers: Dict[GestureType, str] = {
            GestureType.TAP: f"element.addEventListener('click', (e) => {{ {action_code} }});",
            GestureType.DOUBLE_TAP: f"element.addEventListener('dblclick', (e) => {{ {action_code} }});",
            GestureType.LONG_PRESS: (
                f"let pressTimer;\n"
                f"element.addEventListener('pointerdown', () => {{\n"
                f"  pressTimer = setTimeout(() => {{ {action_code} }}, {self.config.long_press_duration});\n"
                f"}});\n"
                f"element.addEventListener('pointerup', () => clearTimeout(pressTimer));"
            ),
            GestureType.SWIPE_LEFT: self._swipe_handler("left", action_code),
            GestureType.SWIPE_RIGHT: self._swipe_handler("right", action_code),
            GestureType.SWIPE_UP: self._swipe_handler("up", action_code),
            GestureType.SWIPE_DOWN: self._swipe_handler("down", action_code),
        }
        return handlers.get(gesture_type, f"// Gesture: {gesture_type.value}\n{action_code}")

    def _swipe_handler(self, direction: str, action_code: str) -> str:
        return (
            f"let startX, startY;\n"
            f"element.addEventListener('touchstart', (e) => {{\n"
            f"  startX = e.touches[0].clientX;\n"
            f"  startY = e.touches[0].clientY;\n"
            f"}});\n"
            f"element.addEventListener('touchend', (e) => {{\n"
            f"  const dx = e.changedTouches[0].clientX - startX;\n"
            f"  const dy = e.changedTouches[0].clientY - startY;\n"
            f"  const threshold = {self.config.swipe_threshold};\n"
            f"  if ('{direction}' === 'left' && dx < -threshold && Math.abs(dy) < Math.abs(dx)) {{ {action_code} }}\n"
            f"  if ('{direction}' === 'right' && dx > threshold && Math.abs(dy) < Math.abs(dx)) {{ {action_code} }}\n"
            f"  if ('{direction}' === 'up' && dy < -threshold && Math.abs(dx) < Math.abs(dy)) {{ {action_code} }}\n"
            f"  if ('{direction}' === 'down' && dy > threshold && Math.abs(dx) < Math.abs(dy)) {{ {action_code} }}\n"
            f"}});"
        )
