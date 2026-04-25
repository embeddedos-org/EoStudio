"""Video exporter — MP4, GIF, WebM export with ffmpeg integration."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class ExportFormat(Enum):
    MP4 = "mp4"
    WEBM = "webm"
    GIF = "gif"
    PNG_SEQUENCE = "png_sequence"
    MOV = "mov"


class ExportPreset(Enum):
    SOCIAL_SQUARE = "social_square"       # 1080x1080
    SOCIAL_PORTRAIT = "social_portrait"   # 1080x1920
    SOCIAL_LANDSCAPE = "social_landscape" # 1920x1080
    APP_STORE = "app_store"               # 1290x2796
    PLAY_STORE = "play_store"             # 1080x1920
    TWITTER = "twitter"                   # 1200x675
    LINKEDIN = "linkedin"                 # 1200x627
    YOUTUBE_THUMB = "youtube_thumb"       # 1280x720
    PRODUCT_HUNT = "product_hunt"         # 1270x760


PRESET_SIZES: Dict[ExportPreset, Dict[str, int]] = {
    ExportPreset.SOCIAL_SQUARE: {"width": 1080, "height": 1080},
    ExportPreset.SOCIAL_PORTRAIT: {"width": 1080, "height": 1920},
    ExportPreset.SOCIAL_LANDSCAPE: {"width": 1920, "height": 1080},
    ExportPreset.APP_STORE: {"width": 1290, "height": 2796},
    ExportPreset.PLAY_STORE: {"width": 1080, "height": 1920},
    ExportPreset.TWITTER: {"width": 1200, "height": 675},
    ExportPreset.LINKEDIN: {"width": 1200, "height": 627},
    ExportPreset.YOUTUBE_THUMB: {"width": 1280, "height": 720},
    ExportPreset.PRODUCT_HUNT: {"width": 1270, "height": 760},
}


@dataclass
class ExportConfig:
    """Configuration for video export."""
    format: ExportFormat = ExportFormat.MP4
    preset: Optional[ExportPreset] = None
    width: int = 1920
    height: int = 1080
    fps: int = 30
    quality: float = 0.9  # 0.0 - 1.0
    bitrate: str = "8M"
    codec: str = "libx264"
    loop: bool = False  # for GIF
    optimize_gif: bool = True
    max_colors_gif: int = 256
    max_file_size_mb: Optional[float] = None
    include_audio: bool = True

    def __post_init__(self) -> None:
        if self.preset:
            size = PRESET_SIZES.get(self.preset, {})
            self.width = size.get("width", self.width)
            self.height = size.get("height", self.height)


class VideoExporter:
    """Export compositions as video files using ffmpeg."""

    def __init__(self, config: Optional[ExportConfig] = None) -> None:
        self.config = config or ExportConfig()
        self._ffmpeg_path = self._find_ffmpeg()

    def _find_ffmpeg(self) -> str:
        """Locate ffmpeg binary."""
        for path in ["ffmpeg", "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg",
                      "C:\\ffmpeg\\bin\\ffmpeg.exe"]:
            try:
                subprocess.run([path, "-version"], capture_output=True, timeout=5)
                return path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return "ffmpeg"

    @property
    def ffmpeg_available(self) -> bool:
        try:
            subprocess.run([self._ffmpeg_path, "-version"], capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def export_mp4(self, frame_dir: str, output_path: str,
                   audio_path: Optional[str] = None) -> Dict[str, Any]:
        """Export frames as MP4 video."""
        cfg = self.config
        crf = int(51 - cfg.quality * 46)  # quality 0.0->CRF51, 1.0->CRF5

        cmd = [
            self._ffmpeg_path, "-y",
            "-framerate", str(cfg.fps),
            "-i", os.path.join(frame_dir, "frame_%06d.png"),
        ]

        if audio_path and cfg.include_audio:
            cmd.extend(["-i", audio_path, "-map", "0:v", "-map", "1:a", "-shortest"])

        cmd.extend([
            "-c:v", cfg.codec,
            "-pix_fmt", "yuv420p",
            "-crf", str(crf),
            "-s", f"{cfg.width}x{cfg.height}",
            output_path,
        ])

        return self._run_command(cmd, output_path)

    def export_gif(self, frame_dir: str, output_path: str) -> Dict[str, Any]:
        """Export frames as animated GIF."""
        cfg = self.config
        palette_path = os.path.join(frame_dir, "_palette.png")

        # Generate palette
        palette_cmd = [
            self._ffmpeg_path, "-y",
            "-framerate", str(cfg.fps),
            "-i", os.path.join(frame_dir, "frame_%06d.png"),
            "-vf", f"fps={min(cfg.fps, 15)},scale={cfg.width}:-1:flags=lanczos,"
                   f"palettegen=max_colors={cfg.max_colors_gif}",
            palette_path,
        ]

        # Generate GIF
        gif_cmd = [
            self._ffmpeg_path, "-y",
            "-framerate", str(cfg.fps),
            "-i", os.path.join(frame_dir, "frame_%06d.png"),
            "-i", palette_path,
            "-filter_complex",
            f"fps={min(cfg.fps, 15)},scale={cfg.width}:-1:flags=lanczos[x];[x][1:v]paletteuse",
        ]

        if cfg.loop:
            gif_cmd.extend(["-loop", "0"])

        gif_cmd.append(output_path)

        self._run_command(palette_cmd, palette_path)
        return self._run_command(gif_cmd, output_path)

    def export_webm(self, frame_dir: str, output_path: str) -> Dict[str, Any]:
        """Export frames as WebM video."""
        cfg = self.config
        crf = int(63 - cfg.quality * 53)

        cmd = [
            self._ffmpeg_path, "-y",
            "-framerate", str(cfg.fps),
            "-i", os.path.join(frame_dir, "frame_%06d.png"),
            "-c:v", "libvpx-vp9",
            "-crf", str(crf),
            "-b:v", "0",
            "-s", f"{cfg.width}x{cfg.height}",
            output_path,
        ]

        return self._run_command(cmd, output_path)

    def export(self, frame_dir: str, output_path: str,
               audio_path: Optional[str] = None) -> Dict[str, Any]:
        """Export using the configured format."""
        fmt = self.config.format
        if fmt == ExportFormat.MP4:
            return self.export_mp4(frame_dir, output_path, audio_path)
        elif fmt == ExportFormat.GIF:
            return self.export_gif(frame_dir, output_path)
        elif fmt == ExportFormat.WEBM:
            return self.export_webm(frame_dir, output_path)
        elif fmt == ExportFormat.MOV:
            self.config.codec = "prores_ks"
            return self.export_mp4(frame_dir, output_path, audio_path)
        else:
            return {"success": True, "format": "png_sequence", "path": frame_dir}

    def generate_command(self, frame_dir: str, output_path: str) -> str:
        """Generate the ffmpeg command string without executing."""
        cfg = self.config
        crf = int(51 - cfg.quality * 46)
        return (
            f'{self._ffmpeg_path} -y '
            f'-framerate {cfg.fps} '
            f'-i "{os.path.join(frame_dir, "frame_%06d.png")}" '
            f'-c:v {cfg.codec} -pix_fmt yuv420p -crf {crf} '
            f'-s {cfg.width}x{cfg.height} '
            f'"{output_path}"'
        )

    def _run_command(self, cmd: List[str], output_path: str) -> Dict[str, Any]:
        """Execute ffmpeg command and return result."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            success = result.returncode == 0
            file_size = os.path.getsize(output_path) if success and os.path.exists(output_path) else 0
            return {
                "success": success,
                "path": output_path,
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "stderr": result.stderr[-500:] if not success else "",
            }
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return {
                "success": False,
                "path": output_path,
                "error": str(e),
                "command": " ".join(cmd),
            }
