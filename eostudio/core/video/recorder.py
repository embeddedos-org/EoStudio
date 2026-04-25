"""Screen recorder — captures prototype sessions and canvas animations as frames."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class RecordingState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class RecordingConfig:
    """Configuration for screen recording."""
    fps: int = 30
    width: int = 1920
    height: int = 1080
    quality: float = 0.9
    capture_cursor: bool = True
    capture_clicks: bool = True
    max_duration: float = 300.0  # seconds
    device_frame: str = "iphone_14"
    background_color: str = "#1a1a2e"

    DEVICE_SIZES: Dict[str, Tuple[int, int]] = field(default_factory=lambda: {
        "iphone_14": (390, 844),
        "iphone_15_pro": (393, 852),
        "pixel_8": (412, 915),
        "ipad_pro": (1024, 1366),
        "desktop": (1440, 900),
        "custom": (0, 0),
    })


@dataclass
class RecordedFrame:
    """A single recorded frame with metadata."""
    index: int
    timestamp: float
    screen_data: Dict[str, Any] = field(default_factory=dict)
    cursor_position: Optional[Tuple[int, int]] = None
    click_position: Optional[Tuple[int, int]] = None
    annotations: List[Dict[str, Any]] = field(default_factory=list)


class ScreenRecorder:
    """Records prototype interactions and canvas animations as frame sequences."""

    def __init__(self, config: Optional[RecordingConfig] = None) -> None:
        self.config = config or RecordingConfig()
        self._state = RecordingState.IDLE
        self._frames: List[RecordedFrame] = []
        self._start_time: float = 0.0
        self._frame_count = 0
        self._on_frame: Optional[Callable[[RecordedFrame], None]] = None

    @property
    def state(self) -> RecordingState:
        return self._state

    @property
    def duration(self) -> float:
        if not self._frames:
            return 0.0
        return self._frames[-1].timestamp - self._frames[0].timestamp

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    def start(self) -> None:
        self._state = RecordingState.RECORDING
        self._start_time = time.time()
        self._frames.clear()
        self._frame_count = 0

    def pause(self) -> None:
        if self._state == RecordingState.RECORDING:
            self._state = RecordingState.PAUSED

    def resume(self) -> None:
        if self._state == RecordingState.PAUSED:
            self._state = RecordingState.RECORDING

    def stop(self) -> List[RecordedFrame]:
        self._state = RecordingState.STOPPED
        return list(self._frames)

    def capture_frame(self, screen_data: Dict[str, Any],
                      cursor: Optional[Tuple[int, int]] = None,
                      click: Optional[Tuple[int, int]] = None) -> Optional[RecordedFrame]:
        """Capture a single frame during recording."""
        if self._state != RecordingState.RECORDING:
            return None

        elapsed = time.time() - self._start_time
        if elapsed > self.config.max_duration:
            self.stop()
            return None

        frame = RecordedFrame(
            index=self._frame_count,
            timestamp=elapsed,
            screen_data=screen_data,
            cursor_position=cursor,
            click_position=click,
        )
        self._frames.append(frame)
        self._frame_count += 1

        if self._on_frame:
            self._on_frame(frame)

        return frame

    def add_annotation(self, text: str, position: Tuple[int, int],
                       duration: float = 2.0) -> None:
        """Add a text annotation at the current frame."""
        if self._frames:
            self._frames[-1].annotations.append({
                "text": text,
                "position": list(position),
                "duration": duration,
                "style": {"color": "#ffffff", "font_size": 16, "bg": "rgba(0,0,0,0.7)"},
            })

    def on_frame(self, callback: Callable[[RecordedFrame], None]) -> None:
        self._on_frame = callback

    def get_frames(self, start: float = 0.0,
                   end: Optional[float] = None) -> List[RecordedFrame]:
        """Get frames within a time range."""
        frames = self._frames
        if start > 0:
            frames = [f for f in frames if f.timestamp >= start]
        if end is not None:
            frames = [f for f in frames if f.timestamp <= end]
        return frames

    def trim(self, start: float, end: float) -> None:
        """Trim recording to a time range."""
        self._frames = [f for f in self._frames if start <= f.timestamp <= end]
        if self._frames:
            offset = self._frames[0].timestamp
            for f in self._frames:
                f.timestamp -= offset
                f.index = self._frames.index(f)

    def generate_thumbnail(self, frame_index: int = 0) -> Dict[str, Any]:
        """Generate thumbnail data from a specific frame."""
        if 0 <= frame_index < len(self._frames):
            frame = self._frames[frame_index]
            return {
                "width": self.config.width // 4,
                "height": self.config.height // 4,
                "screen_data": frame.screen_data,
                "timestamp": frame.timestamp,
            }
        return {"width": 0, "height": 0}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": {
                "fps": self.config.fps,
                "width": self.config.width,
                "height": self.config.height,
                "device_frame": self.config.device_frame,
            },
            "duration": self.duration,
            "frame_count": self.frame_count,
            "frames": [
                {
                    "index": f.index,
                    "timestamp": f.timestamp,
                    "screen_data": f.screen_data,
                    "cursor": f.cursor_position,
                    "click": f.click_position,
                    "annotations": f.annotations,
                }
                for f in self._frames
            ],
        }
