"""Animation timeline — sequencing, staggering, and parallel animations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from eostudio.core.animation.keyframe import (
    EasingFunction,
    KeyframeTrack,
    NumericValue,
    interpolate,
)


class PlayState(Enum):
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    FINISHED = "finished"


class FillMode(Enum):
    NONE = "none"
    FORWARDS = "forwards"
    BACKWARDS = "backwards"
    BOTH = "both"


class Direction(Enum):
    NORMAL = "normal"
    REVERSE = "reverse"
    ALTERNATE = "alternate"
    ALTERNATE_REVERSE = "alternate_reverse"


@dataclass
class AnimationClip:
    """A single animation clip that animates one or more properties on a target."""
    target_id: str
    tracks: List[KeyframeTrack] = field(default_factory=list)
    delay: float = 0.0
    duration: float = 1.0
    iterations: int = 1  # -1 for infinite
    direction: Direction = Direction.NORMAL
    fill_mode: FillMode = FillMode.FORWARDS
    speed: float = 1.0
    label: str = ""

    _state: PlayState = field(default=PlayState.IDLE, init=False)
    _elapsed: float = field(default=0.0, init=False)
    _iteration: int = field(default=0, init=False)

    def add_track(self, property_name: str) -> KeyframeTrack:
        track = KeyframeTrack(property_name=property_name)
        self.tracks.append(track)
        return track

    def get_track(self, property_name: str) -> Optional[KeyframeTrack]:
        for track in self.tracks:
            if track.property_name == property_name:
                return track
        return None

    @property
    def total_duration(self) -> float:
        return self.delay + self.duration * max(1, self.iterations)

    @property
    def state(self) -> PlayState:
        return self._state

    def reset(self) -> None:
        self._elapsed = 0.0
        self._iteration = 0
        self._state = PlayState.IDLE

    def evaluate(self, time: float) -> Dict[str, NumericValue]:
        """Evaluate all tracks at the given time, returning property -> value map."""
        values: Dict[str, NumericValue] = {}
        effective_time = time - self.delay

        if effective_time < 0:
            if self.fill_mode in (FillMode.BACKWARDS, FillMode.BOTH):
                for track in self.tracks:
                    values[track.property_name] = track.evaluate(0)
            return values

        if self.duration <= 0:
            for track in self.tracks:
                values[track.property_name] = track.evaluate(track.keyframes[-1].time if track.keyframes else 0)
            return values

        iteration = int(effective_time / self.duration)
        if self.iterations > 0 and iteration >= self.iterations:
            if self.fill_mode in (FillMode.FORWARDS, FillMode.BOTH):
                for track in self.tracks:
                    final_time = track.keyframes[-1].time if track.keyframes else self.duration
                    values[track.property_name] = track.evaluate(final_time)
            return values

        local_time = effective_time % self.duration
        progress = local_time / self.duration

        # Handle direction
        is_reverse = False
        if self.direction == Direction.REVERSE:
            is_reverse = True
        elif self.direction == Direction.ALTERNATE:
            is_reverse = (iteration % 2) == 1
        elif self.direction == Direction.ALTERNATE_REVERSE:
            is_reverse = (iteration % 2) == 0

        if is_reverse:
            progress = 1.0 - progress

        for track in self.tracks:
            track_duration = track.duration if track.duration > 0 else self.duration
            values[track.property_name] = track.evaluate(progress * track_duration)

        return values

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_id": self.target_id,
            "tracks": [t.to_dict() for t in self.tracks],
            "delay": self.delay,
            "duration": self.duration,
            "iterations": self.iterations,
            "direction": self.direction.value,
            "fill_mode": self.fill_mode.value,
            "speed": self.speed,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnimationClip":
        clip = cls(
            target_id=data["target_id"],
            delay=data.get("delay", 0),
            duration=data.get("duration", 1.0),
            iterations=data.get("iterations", 1),
            direction=Direction(data.get("direction", "normal")),
            fill_mode=FillMode(data.get("fill_mode", "forwards")),
            speed=data.get("speed", 1.0),
            label=data.get("label", ""),
        )
        for t_data in data.get("tracks", []):
            clip.tracks.append(KeyframeTrack.from_dict(t_data))
        return clip


class AnimationTimeline:
    """Master timeline that orchestrates multiple animation clips with sequencing and staggering."""

    def __init__(self, name: str = "Timeline") -> None:
        self.name = name
        self.clips: List[AnimationClip] = []
        self._state = PlayState.IDLE
        self._elapsed = 0.0
        self._speed = 1.0
        self._on_update: Optional[Callable[[float, Dict[str, Dict[str, NumericValue]]], None]] = None
        self._on_complete: Optional[Callable[[], None]] = None

    @property
    def state(self) -> PlayState:
        return self._state

    @property
    def duration(self) -> float:
        if not self.clips:
            return 0.0
        return max(clip.total_duration for clip in self.clips)

    @property
    def elapsed(self) -> float:
        return self._elapsed

    def add_clip(self, clip: AnimationClip) -> AnimationClip:
        self.clips.append(clip)
        return clip

    def create_clip(self, target_id: str, duration: float = 1.0,
                    delay: float = 0.0, **kwargs: Any) -> AnimationClip:
        clip = AnimationClip(target_id=target_id, duration=duration, delay=delay, **kwargs)
        self.clips.append(clip)
        return clip

    def stagger(self, target_ids: List[str], tracks_config: List[Dict[str, Any]],
                stagger_delay: float = 0.1, duration: float = 0.5,
                base_delay: float = 0.0) -> List[AnimationClip]:
        """Create staggered animations across multiple targets."""
        clips = []
        for i, target_id in enumerate(target_ids):
            clip = AnimationClip(
                target_id=target_id,
                duration=duration,
                delay=base_delay + i * stagger_delay,
            )
            for tc in tracks_config:
                track = clip.add_track(tc["property"])
                track.add_keyframe(0, tc["from"], tc.get("easing", EasingFunction.EASE_OUT))
                track.add_keyframe(duration, tc["to"], tc.get("easing", EasingFunction.EASE_OUT))
            clips.append(clip)
            self.clips.append(clip)
        return clips

    def sequence(self, clips: List[AnimationClip], gap: float = 0.0) -> None:
        """Arrange clips to play one after another."""
        current_time = 0.0
        for clip in clips:
            clip.delay = current_time
            current_time += clip.duration + gap
            if clip not in self.clips:
                self.clips.append(clip)

    def play(self) -> None:
        self._state = PlayState.PLAYING
        self._elapsed = 0.0

    def pause(self) -> None:
        if self._state == PlayState.PLAYING:
            self._state = PlayState.PAUSED

    def resume(self) -> None:
        if self._state == PlayState.PAUSED:
            self._state = PlayState.PLAYING

    def stop(self) -> None:
        self._state = PlayState.IDLE
        self._elapsed = 0.0
        for clip in self.clips:
            clip.reset()

    def seek(self, time: float) -> Dict[str, Dict[str, NumericValue]]:
        """Seek to a specific time and return all animated values."""
        self._elapsed = max(0.0, min(time, self.duration))
        return self.evaluate(self._elapsed)

    def tick(self, dt: float) -> Dict[str, Dict[str, NumericValue]]:
        """Advance by dt seconds. Returns target_id -> {property -> value}."""
        if self._state != PlayState.PLAYING:
            return {}

        self._elapsed += dt * self._speed
        values = self.evaluate(self._elapsed)

        if self._elapsed >= self.duration:
            self._state = PlayState.FINISHED
            if self._on_complete:
                self._on_complete()

        if self._on_update:
            self._on_update(self._elapsed, values)

        return values

    def evaluate(self, time: float) -> Dict[str, Dict[str, NumericValue]]:
        """Evaluate all clips at a given time."""
        result: Dict[str, Dict[str, NumericValue]] = {}
        for clip in self.clips:
            values = clip.evaluate(time)
            if values:
                if clip.target_id not in result:
                    result[clip.target_id] = {}
                result[clip.target_id].update(values)
        return result

    def on_update(self, callback: Callable[[float, Dict[str, Dict[str, NumericValue]]], None]) -> None:
        self._on_update = callback

    def on_complete(self, callback: Callable[[], None]) -> None:
        self._on_complete = callback

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "clips": [c.to_dict() for c in self.clips],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnimationTimeline":
        tl = cls(name=data.get("name", "Timeline"))
        for c_data in data.get("clips", []):
            tl.clips.append(AnimationClip.from_dict(c_data))
        return tl
