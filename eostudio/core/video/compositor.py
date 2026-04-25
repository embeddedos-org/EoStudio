"""Video compositor — layer-based compositing for promo videos."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class LayerType(Enum):
    SCREEN_RECORDING = "screen_recording"
    IMAGE = "image"
    TEXT = "text"
    SHAPE = "shape"
    DEVICE_FRAME = "device_frame"
    BACKGROUND = "background"
    GRADIENT = "gradient"
    VIDEO = "video"
    ANIMATION = "animation"
    PARTICLE = "particle"


class BlendMode(Enum):
    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    SOFT_LIGHT = "soft_light"
    HARD_LIGHT = "hard_light"
    COLOR_DODGE = "color_dodge"
    COLOR_BURN = "color_burn"


@dataclass
class LayerTransform:
    """Transform properties for a compositor layer."""
    x: float = 0.0
    y: float = 0.0
    width: float = 100.0
    height: float = 100.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    anchor_x: float = 0.5
    anchor_y: float = 0.5
    opacity: float = 1.0

    def to_css_transform(self) -> str:
        parts = []
        if self.x != 0 or self.y != 0:
            parts.append(f"translate({self.x}px, {self.y}px)")
        if self.rotation != 0:
            parts.append(f"rotate({self.rotation}deg)")
        if self.scale_x != 1.0 or self.scale_y != 1.0:
            parts.append(f"scale({self.scale_x}, {self.scale_y})")
        return " ".join(parts) if parts else "none"

    def to_dict(self) -> Dict[str, float]:
        return {
            "x": self.x, "y": self.y, "width": self.width, "height": self.height,
            "rotation": self.rotation, "scale_x": self.scale_x, "scale_y": self.scale_y,
            "opacity": self.opacity,
        }


@dataclass
class LayerKeyframe:
    """A keyframe for animating layer properties over time."""
    time: float  # seconds
    transform: LayerTransform = field(default_factory=LayerTransform)
    easing: str = "ease_in_out"


@dataclass
class Layer:
    """A single layer in the video compositor."""
    id: str
    name: str
    layer_type: LayerType
    transform: LayerTransform = field(default_factory=LayerTransform)
    content: Dict[str, Any] = field(default_factory=dict)
    start_time: float = 0.0
    end_time: float = 10.0
    blend_mode: BlendMode = BlendMode.NORMAL
    visible: bool = True
    locked: bool = False
    keyframes: List[LayerKeyframe] = field(default_factory=list)
    effects: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    def add_keyframe(self, time: float, **transform_props: Any) -> LayerKeyframe:
        transform = LayerTransform(**transform_props)
        kf = LayerKeyframe(time=time, transform=transform)
        self.keyframes.append(kf)
        self.keyframes.sort(key=lambda k: k.time)
        return kf

    def add_effect(self, effect_type: str, **params: Any) -> None:
        self.effects.append({"type": effect_type, **params})

    def evaluate_transform(self, time: float) -> LayerTransform:
        """Evaluate interpolated transform at a given time."""
        if not self.keyframes:
            return self.transform

        if time <= self.keyframes[0].time:
            return self.keyframes[0].transform
        if time >= self.keyframes[-1].time:
            return self.keyframes[-1].transform

        for i in range(len(self.keyframes) - 1):
            k0, k1 = self.keyframes[i], self.keyframes[i + 1]
            if k0.time <= time <= k1.time:
                dt = k1.time - k0.time
                if dt == 0:
                    return k1.transform
                t = (time - k0.time) / dt
                return self._interpolate_transform(k0.transform, k1.transform, t)
        return self.transform

    def _interpolate_transform(self, a: LayerTransform, b: LayerTransform,
                                t: float) -> LayerTransform:
        def lerp(v0: float, v1: float) -> float:
            return v0 + (v1 - v0) * t

        return LayerTransform(
            x=lerp(a.x, b.x), y=lerp(a.y, b.y),
            width=lerp(a.width, b.width), height=lerp(a.height, b.height),
            rotation=lerp(a.rotation, b.rotation),
            scale_x=lerp(a.scale_x, b.scale_x), scale_y=lerp(a.scale_y, b.scale_y),
            opacity=lerp(a.opacity, b.opacity),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "type": self.layer_type.value,
            "transform": self.transform.to_dict(), "content": self.content,
            "start_time": self.start_time, "end_time": self.end_time,
            "blend_mode": self.blend_mode.value, "visible": self.visible,
            "effects": self.effects,
            "keyframes": [{"time": kf.time, "transform": kf.transform.to_dict()} for kf in self.keyframes],
        }


class VideoCompositor:
    """Layer-based video compositor for creating promotional content."""

    def __init__(self, width: int = 1920, height: int = 1080, fps: int = 30,
                 duration: float = 10.0) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self.duration = duration
        self.layers: List[Layer] = []
        self.background_color: str = "#000000"
        self.audio_tracks: List[Dict[str, Any]] = []

    def add_layer(self, layer: Layer) -> Layer:
        self.layers.append(layer)
        return layer

    def create_layer(self, name: str, layer_type: LayerType, **kwargs: Any) -> Layer:
        layer_id = f"layer_{len(self.layers)}"
        layer = Layer(id=layer_id, name=name, layer_type=layer_type, **kwargs)
        self.layers.append(layer)
        return layer

    def remove_layer(self, layer_id: str) -> None:
        self.layers = [l for l in self.layers if l.id != layer_id]

    def move_layer(self, layer_id: str, new_index: int) -> None:
        layer = next((l for l in self.layers if l.id == layer_id), None)
        if layer:
            self.layers.remove(layer)
            self.layers.insert(min(new_index, len(self.layers)), layer)

    def add_text_layer(self, text: str, x: float = 0, y: float = 0,
                       font_size: int = 48, color: str = "#ffffff",
                       font_family: str = "Inter", font_weight: int = 700,
                       start: float = 0, end: float = 10) -> Layer:
        return self.create_layer(
            name=f"Text: {text[:20]}", layer_type=LayerType.TEXT,
            transform=LayerTransform(x=x, y=y),
            content={"text": text, "font_size": font_size, "color": color,
                     "font_family": font_family, "font_weight": font_weight},
            start_time=start, end_time=end,
        )

    def add_device_mockup(self, device: str = "iphone_14",
                          x: float = 0, y: float = 0,
                          scale: float = 1.0) -> Layer:
        return self.create_layer(
            name=f"Device: {device}", layer_type=LayerType.DEVICE_FRAME,
            transform=LayerTransform(x=x, y=y, scale_x=scale, scale_y=scale),
            content={"device": device},
        )

    def add_background_gradient(self, colors: List[str],
                                 direction: str = "to bottom") -> Layer:
        return self.create_layer(
            name="Gradient BG", layer_type=LayerType.GRADIENT,
            transform=LayerTransform(width=self.width, height=self.height),
            content={"colors": colors, "direction": direction},
        )

    def add_audio(self, audio_path: str, start: float = 0,
                  volume: float = 1.0) -> None:
        self.audio_tracks.append({
            "path": audio_path, "start": start, "volume": volume,
        })

    def render_frame(self, time: float) -> Dict[str, Any]:
        """Render a single frame at the given time. Returns layer data for rendering."""
        frame_layers = []
        for layer in self.layers:
            if not layer.visible:
                continue
            if time < layer.start_time or time > layer.end_time:
                continue
            transform = layer.evaluate_transform(time - layer.start_time)
            frame_layers.append({
                "id": layer.id,
                "type": layer.layer_type.value,
                "transform": transform.to_dict(),
                "content": layer.content,
                "blend_mode": layer.blend_mode.value,
                "effects": layer.effects,
            })
        return {
            "time": time,
            "width": self.width,
            "height": self.height,
            "background": self.background_color,
            "layers": frame_layers,
        }

    def render_all_frames(self) -> List[Dict[str, Any]]:
        """Render all frames for the composition."""
        frames = []
        dt = 1.0 / self.fps
        t = 0.0
        while t <= self.duration:
            frames.append(self.render_frame(t))
            t += dt
        return frames

    def generate_ffmpeg_command(self, output_path: str,
                                frame_dir: str = "./frames") -> str:
        """Generate ffmpeg command for rendering frames to video."""
        audio_input = ""
        audio_map = ""
        if self.audio_tracks:
            audio_input = f' -i "{self.audio_tracks[0]["path"]}"'
            audio_map = " -map 0:v -map 1:a -shortest"

        return (
            f'ffmpeg -y -framerate {self.fps} -i "{frame_dir}/frame_%06d.png"'
            f'{audio_input}'
            f' -c:v libx264 -pix_fmt yuv420p -crf 18'
            f'{audio_map}'
            f' -s {self.width}x{self.height}'
            f' "{output_path}"'
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width, "height": self.height,
            "fps": self.fps, "duration": self.duration,
            "background": self.background_color,
            "layers": [l.to_dict() for l in self.layers],
            "audio": self.audio_tracks,
        }
