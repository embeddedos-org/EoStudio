"""Automated release video generator — changelog-driven Manim videos with TTS narration."""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set


# ── Color palette (matches promo/eostudio_promo.py) ──────────────────────────

BG = "#0a0a1a"
PRIMARY = "#3b82f6"
SECONDARY = "#8b5cf6"
ACCENT = "#ec4899"
CYAN = "#22d3ee"
GREEN = "#22c55e"
AMBER = "#f59e0b"
SLATE = "#94a3b8"
DARK_SLATE = "#64748b"
CARD_BG = "#1e1e2e"


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class ChangelogEntry:
    """A single parsed commit entry."""
    hash: str
    subject: str
    body: str = ""
    author: str = ""
    date: str = ""
    type: str = "chore"  # feat / fix / refactor / docs / chore
    breaking: bool = False


@dataclass
class ReleaseChangelog:
    """Parsed changelog between two version tags."""
    version: str
    previous_version: str
    date: str
    features: List[ChangelogEntry] = field(default_factory=list)
    fixes: List[ChangelogEntry] = field(default_factory=list)
    breaking_changes: List[ChangelogEntry] = field(default_factory=list)
    other: List[ChangelogEntry] = field(default_factory=list)
    contributors: Set[str] = field(default_factory=set)
    stats: Dict[str, int] = field(default_factory=lambda: {
        "files_changed": 0, "insertions": 0, "deletions": 0,
    })


@dataclass
class ReleaseVideoConfig:
    """Configuration for release video generation."""
    version: str = "0.0.0"
    product_name: str = "EoStudio"
    tagline: str = ""
    changelog: Optional[ReleaseChangelog] = None
    output_dir: str = "./release-video"
    resolution: tuple = (1920, 1080)
    fps: int = 30
    voice: str = "en-US-GuyNeural"
    voice_rate: str = "-5%"
    voice_pitch: str = "-4Hz"
    include_narration: bool = True
    background_music_path: Optional[str] = None
    theme: str = "dark"
    color_scheme: Dict[str, str] = field(default_factory=lambda: {
        "bg": BG, "primary": PRIMARY, "secondary": SECONDARY,
        "accent": ACCENT, "text": "#ffffff", "muted": SLATE,
    })
    max_features_shown: int = 6
    max_duration: float = 60.0


# ── Changelog Parser ─────────────────────────────────────────────────────────

_CONVENTIONAL_RE = re.compile(
    r"^(?P<type>feat|fix|refactor|docs|chore|perf|test|ci|build|style)"
    r"(?:\((?P<scope>[^)]*)\))?!?:\s*(?P<desc>.+)$",
    re.IGNORECASE,
)


class ChangelogParser:
    """Parse git history between version tags into a structured changelog."""

    def __init__(self, workspace_path: str = ".") -> None:
        self.workspace_path = workspace_path

    def _run_git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.workspace_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def get_version_tags(self) -> List[str]:
        """Return version tags sorted by semver (ascending)."""
        raw = self._run_git("tag", "-l", "v*")
        if not raw:
            return []
        tags = raw.splitlines()
        tags.sort(key=self._semver_key)
        return tags

    @staticmethod
    def _semver_key(tag: str) -> tuple:
        nums = re.findall(r"\d+", tag)
        return tuple(int(n) for n in nums) if nums else (0,)

    def parse_between_tags(self, from_tag: str, to_tag: str) -> ReleaseChangelog:
        """Parse commits between two tags into a ReleaseChangelog."""
        fmt = "%H%n%s%n%b%n%an%n%aI%n---END---"
        raw = self._run_git("log", f"{from_tag}..{to_tag}", f"--format={fmt}")

        changelog = ReleaseChangelog(
            version=to_tag.lstrip("v"),
            previous_version=from_tag.lstrip("v"),
            date=datetime.now().strftime("%Y-%m-%d"),
        )

        if not raw:
            return changelog

        blocks = raw.split("---END---")
        for block in blocks:
            lines = block.strip().splitlines()
            if len(lines) < 4:
                continue

            commit_hash = lines[0].strip()
            subject = lines[1].strip()
            author = lines[-2].strip()
            date = lines[-1].strip()
            body = "\n".join(lines[2:-2]).strip()

            entry = ChangelogEntry(
                hash=commit_hash,
                subject=subject,
                body=body,
                author=author,
                date=date,
            )

            # Parse conventional commit type
            match = _CONVENTIONAL_RE.match(subject)
            if match:
                entry.type = match.group("type").lower()
                entry.subject = match.group("desc")

            # Detect breaking changes
            if "BREAKING CHANGE" in body or "!" in subject.split(":")[0]:
                entry.breaking = True
                changelog.breaking_changes.append(entry)

            if entry.type == "feat":
                changelog.features.append(entry)
            elif entry.type == "fix":
                changelog.fixes.append(entry)
            else:
                changelog.other.append(entry)

            changelog.contributors.add(author)

        # Get diff stats
        changelog.stats = self.get_stats(from_tag, to_tag)
        return changelog

    def parse_latest_release(self) -> ReleaseChangelog:
        """Auto-detect the last two version tags and parse between them."""
        tags = self.get_version_tags()
        if len(tags) < 2:
            raise RuntimeError(
                f"Need at least 2 version tags, found {len(tags)}: {tags}"
            )
        return self.parse_between_tags(tags[-2], tags[-1])

    def get_stats(self, from_tag: str, to_tag: str) -> Dict[str, int]:
        """Get file change stats between tags."""
        try:
            raw = self._run_git("diff", "--shortstat", from_tag, to_tag)
        except RuntimeError:
            return {"files_changed": 0, "insertions": 0, "deletions": 0}

        stats: Dict[str, int] = {"files_changed": 0, "insertions": 0, "deletions": 0}
        m = re.search(r"(\d+) files? changed", raw)
        if m:
            stats["files_changed"] = int(m.group(1))
        m = re.search(r"(\d+) insertions?", raw)
        if m:
            stats["insertions"] = int(m.group(1))
        m = re.search(r"(\d+) deletions?", raw)
        if m:
            stats["deletions"] = int(m.group(1))
        return stats


# ── Release Video Generator ─────────────────────────────────────────────────

class ReleaseVideoGenerator:
    """Generate a professional release video from a changelog."""

    def __init__(self, config: ReleaseVideoConfig) -> None:
        self.config = config
        self._ffmpeg = self._find_ffmpeg()

    @staticmethod
    def _find_ffmpeg() -> str:
        for path in ["ffmpeg", "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg",
                      "/home/spatchava/.local/bin/ffmpeg",
                      "C:\\ffmpeg\\bin\\ffmpeg.exe"]:
            try:
                subprocess.run([path, "-version"], capture_output=True, timeout=5)
                return path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return "ffmpeg"

    # ── Manim Script Generation ──────────────────────────────────────────

    def generate_manim_script(self) -> str:
        """Generate a complete Manim Python script for the release video."""
        cfg = self.config
        cl = cfg.changelog
        colors = cfg.color_scheme

        version = cfg.version
        product = cfg.product_name
        tagline = cfg.tagline or f"Release {version}"
        date_str = cl.date if cl else datetime.now().strftime("%Y-%m-%d")
        has_breaking = bool(cl and cl.breaking_changes)

        num_features = len(cl.features) if cl else 0
        num_fixes = len(cl.fixes) if cl else 0
        num_contributors = len(cl.contributors) if cl else 0
        files_changed = cl.stats.get("files_changed", 0) if cl else 0

        def _quote_items(entries: list, limit: int) -> str:
            items = []
            for e in entries[:limit]:
                safe = e.subject.replace('"', '\\"')
                items.append(f'            "{safe}",')
            return "\n".join(items) if items else '            "No items in this release",'

        features_block = _quote_items(cl.features, cfg.max_features_shown) if cl else '            "No new features in this release",'
        fixes_block = _quote_items(cl.fixes, 5) if cl else '            "Stability and performance improvements",'

        lines = [
            f'"""Auto-generated release video for {product} {version}."""',
            "",
            "from manim import *",
            "",
            f'BG = "{colors.get("bg", BG)}"',
            f'PRIMARY = "{colors.get("primary", PRIMARY)}"',
            f'SECONDARY = "{colors.get("secondary", SECONDARY)}"',
            f'ACCENT = "{colors.get("accent", ACCENT)}"',
            'SLATE = "#94a3b8"',
            'DARK_SLATE = "#64748b"',
            'CARD_BG = "#1e1e2e"',
            'GREEN = "#22c55e"',
            'AMBER = "#f59e0b"',
            'CYAN = "#22d3ee"',
            "",
            "",
            "class ReleaseVideo(Scene):",
            "    def construct(self):",
            "        self.camera.background_color = BG",
            "        self.slide_hero()",
            "        self.slide_features()",
            "        self.slide_fixes()",
            "        self.slide_stats()",
            f"        self.slide_breaking()" if has_breaking else "        pass",
            "        self.slide_cta()",
            "",
            "    def slide_hero(self):",
            '        glow = Circle(radius=3, fill_opacity=0.15, fill_color=SECONDARY, stroke_width=0)',
            "        glow.set_opacity(0)",
            f'        title = Text("{product}", font_size=96, font="Inter", weight=BOLD)',
            "        title.set_color_by_gradient(PRIMARY, SECONDARY, ACCENT)",
            f'        version_label = Text("v{version}", font_size=48, color=PRIMARY, font="Inter", weight=BOLD)',
            "        version_label.next_to(title, DOWN, buff=0.3)",
            f'        tagline = Text("{tagline}", font_size=32, color=SLATE, font="Inter")',
            "        tagline.next_to(version_label, DOWN, buff=0.3)",
            f'        date = Text("{date_str}", font_size=20, color=DARK_SLATE, font="Inter")',
            "        date.next_to(tagline, DOWN, buff=0.4)",
            "",
            "        self.play(FadeIn(glow, scale=0.5), run_time=0.5)",
            "        self.play(glow.animate.set_opacity(0.12), run_time=0.3)",
            "        self.play(Write(title), run_time=0.8)",
            "        self.play(FadeIn(version_label, shift=UP * 0.3), run_time=0.5)",
            "        self.play(FadeIn(tagline, shift=UP * 0.2), run_time=0.4)",
            "        self.play(FadeIn(date, shift=UP * 0.2), run_time=0.3)",
            "        self.wait(1.5)",
            "        self.play(FadeOut(Group(*self.mobjects)), run_time=0.5)",
            "",
            "    def slide_features(self):",
            '        title = Text("What\'s New", font_size=56, font="Inter", weight=BOLD)',
            "        title.set_color_by_gradient(PRIMARY, CYAN)",
            "        title.to_edge(UP, buff=0.8)",
            "        features = [",
            features_block,
            "        ]",
            "        items = VGroup()",
            "        for feat in features:",
            '            icon = Text("\\u2728", font_size=24)',
            '            label = Text(feat[:60], font_size=22, color=WHITE, font="Inter")',
            "            row = VGroup(icon, label).arrange(RIGHT, buff=0.3)",
            "            items.add(row)",
            "        items.arrange(DOWN, buff=0.3, aligned_edge=LEFT)",
            "        items.next_to(title, DOWN, buff=0.6)",
            "",
            "        self.play(Write(title), run_time=0.5)",
            "        for item in items:",
            "            self.play(FadeIn(item, shift=RIGHT * 0.3), run_time=0.25)",
            "        self.wait(1.5)",
            "        self.play(FadeOut(Group(*self.mobjects)), run_time=0.5)",
            "",
            "    def slide_fixes(self):",
            '        title = Text("Fixes & Improvements", font_size=56, font="Inter", weight=BOLD)',
            "        title.set_color_by_gradient(GREEN, CYAN)",
            "        title.to_edge(UP, buff=0.8)",
            "        fixes = [",
            fixes_block,
            "        ]",
            "        items = VGroup()",
            "        for fix in fixes:",
            '            icon = Text("\\u2705", font_size=24)',
            '            label = Text(fix[:60], font_size=22, color=WHITE, font="Inter")',
            "            row = VGroup(icon, label).arrange(RIGHT, buff=0.3)",
            "            items.add(row)",
            "        items.arrange(DOWN, buff=0.3, aligned_edge=LEFT)",
            "        items.next_to(title, DOWN, buff=0.6)",
            "",
            "        self.play(Write(title), run_time=0.5)",
            "        for item in items:",
            "            self.play(FadeIn(item, shift=RIGHT * 0.3), run_time=0.25)",
            "        self.wait(1.5)",
            "        self.play(FadeOut(Group(*self.mobjects)), run_time=0.5)",
            "",
            "    def slide_stats(self):",
            '        title = Text("By The Numbers", font_size=56, font="Inter", weight=BOLD)',
            "        title.set_color_by_gradient(AMBER, ACCENT)",
            "        title.to_edge(UP, buff=0.8)",
            "        stats_data = [",
            f'            ("{num_features}", "New Features"),',
            f'            ("{num_fixes}", "Bugs Fixed"),',
            f'            ("{files_changed}", "Files Changed"),',
            f'            ("{num_contributors}", "Contributors"),',
            "        ]",
            "        cards = VGroup()",
            "        for num, label in stats_data:",
            '            n = Text(num, font_size=64, color=PRIMARY, font="Inter", weight=BOLD)',
            '            l = Text(label, font_size=18, color=SLATE, font="Inter")',
            "            l.next_to(n, DOWN, buff=0.15)",
            "            cards.add(VGroup(n, l))",
            "        cards.arrange(RIGHT, buff=1.2)",
            "        cards.next_to(title, DOWN, buff=0.8)",
            "",
            "        self.play(Write(title), run_time=0.5)",
            "        self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.3) for c in cards], lag_ratio=0.15), run_time=0.8)",
            "        self.wait(1.5)",
            "        self.play(FadeOut(Group(*self.mobjects)), run_time=0.5)",
        ]

        if has_breaking:
            breaking_block = _quote_items(cl.breaking_changes, 3) if cl else ""
            lines.extend([
                "",
                "    def slide_breaking(self):",
                '        title = Text("\\u26a0\\ufe0f Breaking Changes", font_size=56, font="Inter", weight=BOLD)',
                "        title.set_color_by_gradient(AMBER, ACCENT)",
                "        title.to_edge(UP, buff=0.8)",
                "        changes = [",
                breaking_block,
                "        ]",
                "        items = VGroup()",
                "        for change in changes:",
                '            icon = Text("\\u26a0\\ufe0f", font_size=24)',
                '            label = Text(change[:60], font_size=22, color=AMBER, font="Inter")',
                "            row = VGroup(icon, label).arrange(RIGHT, buff=0.3)",
                "            items.add(row)",
                "        items.arrange(DOWN, buff=0.3, aligned_edge=LEFT)",
                "        items.next_to(title, DOWN, buff=0.6)",
                "",
                "        self.play(Write(title), run_time=0.5)",
                "        for item in items:",
                "            self.play(FadeIn(item, shift=RIGHT * 0.3), run_time=0.25)",
                "        self.wait(1.5)",
                "        self.play(FadeOut(Group(*self.mobjects)), run_time=0.5)",
            ])

        lines.extend([
            "",
            "    def slide_cta(self):",
            f'        title = Text("Upgrade to {product} v{version}", font_size=56, font="Inter", weight=BOLD)',
            "        title.set_color_by_gradient(PRIMARY, SECONDARY, ACCENT)",
            '        sub = Text("Available now", font_size=28, color=SLATE, font="Inter")',
            "        sub.next_to(title, DOWN, buff=0.3)",
            "        url_bg = RoundedRectangle(",
            "            width=8, height=0.8, corner_radius=0.15,",
            "            fill_opacity=0.9, stroke_width=0,",
            "        )",
            "        url_bg.set_color_by_gradient(PRIMARY, SECONDARY)",
            f'        url_text = Text("Try {product} v{version} today", font_size=22, color=WHITE, font="Inter", weight=BOLD)',
            "        url_text.move_to(url_bg)",
            "        url_group = VGroup(url_bg, url_text).next_to(sub, DOWN, buff=0.5)",
            "",
            "        self.play(Write(title), run_time=0.8)",
            "        self.play(FadeIn(sub, shift=UP * 0.2), run_time=0.4)",
            "        self.play(FadeIn(url_group, scale=0.9), run_time=0.5)",
            "        self.wait(2)",
            "        self.play(FadeOut(Group(*self.mobjects)), run_time=0.8)",
            "",
        ])

        return "\n".join(lines)

    # ── Narration Script Generation ──────────────────────────────────────

    def generate_narration_script(self) -> List[Dict[str, Any]]:
        """Generate narration segments from the changelog."""
        cfg = self.config
        cl = cfg.changelog
        version = cfg.version
        product = cfg.product_name

        segments: List[Dict[str, Any]] = []

        # Intro
        segments.append({
            "text": f"Introducing {product} version {version}. "
                    f"Here's what's new in this release.",
            "pause_after": 1.0,
        })

        # Features
        if cl and cl.features:
            top_features = [e.subject for e in cl.features[:3]]
            features_text = ", ".join(top_features[:-1])
            if len(top_features) > 1:
                features_text += f", and {top_features[-1]}"
            else:
                features_text = top_features[0]
            segments.append({
                "text": f"This release brings {len(cl.features)} new features, "
                        f"including {features_text}.",
                "pause_after": 1.0,
            })

        # Fixes
        if cl and cl.fixes:
            segments.append({
                "text": f"{len(cl.fixes)} bugs have been fixed, "
                        f"improving stability and performance.",
                "pause_after": 0.8,
            })

        # Stats
        if cl and cl.contributors:
            segments.append({
                "text": f"With contributions from {len(cl.contributors)} developers, "
                        f"this release touches {cl.stats.get('files_changed', 0)} files "
                        f"with {cl.stats.get('insertions', 0)} additions.",
                "pause_after": 0.8,
            })

        # Breaking changes
        if cl and cl.breaking_changes:
            segments.append({
                "text": f"Please note, there are {len(cl.breaking_changes)} breaking changes "
                        f"in this release. Check the changelog for migration details.",
                "pause_after": 1.0,
            })

        # Outro
        segments.append({
            "text": f"Upgrade to {product} version {version} today. "
                    f"Thank you for your support.",
            "pause_after": 1.5,
        })

        return segments

    # ── Video Rendering ──────────────────────────────────────────────────

    def render_video(self) -> str:
        """Write the Manim script to a temp file, render it, and return the video path."""
        cfg = self.config
        os.makedirs(cfg.output_dir, exist_ok=True)

        script_content = self.generate_manim_script()
        script_path = os.path.join(cfg.output_dir, "release_scene.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        # Determine quality flag
        w, h = cfg.resolution
        quality = "-qh" if h >= 1080 else "-qm"

        cmd = [
            "manim", "render", quality,
            "--fps", str(cfg.fps),
            "--media_dir", cfg.output_dir,
            script_path, "ReleaseVideo",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"Manim render failed:\n{result.stderr}")

        # Find the output video
        for root, _dirs, files in os.walk(cfg.output_dir):
            for fname in files:
                if fname.endswith(".mp4") and "ReleaseVideo" in fname:
                    return os.path.join(root, fname)

        raise FileNotFoundError("Manim did not produce a video file")

    # ── TTS Narration ────────────────────────────────────────────────────

    def generate_narration(self, segments: List[Dict[str, Any]]) -> str:
        """Generate TTS narration using edge_tts and concatenate with ffmpeg."""
        cfg = self.config
        narration_dir = os.path.join(cfg.output_dir, "narration_segments")
        os.makedirs(narration_dir, exist_ok=True)

        loop = asyncio.new_event_loop()
        try:
            audio_path = loop.run_until_complete(
                self._generate_narration_async(segments, narration_dir)
            )
        finally:
            loop.close()

        return audio_path

    async def _generate_narration_async(
        self, segments: List[Dict[str, Any]], narration_dir: str,
    ) -> str:
        import edge_tts

        cfg = self.config
        part_paths: List[str] = []

        for i, seg in enumerate(segments):
            seg_path = os.path.join(narration_dir, f"seg_{i:02d}.mp3")
            comm = edge_tts.Communicate(
                seg["text"], cfg.voice, rate=cfg.voice_rate, pitch=cfg.voice_pitch,
            )
            await comm.save(seg_path)
            part_paths.append(seg_path)

            # Generate silence gap
            pause = seg.get("pause_after", 0)
            if pause > 0:
                sil_path = os.path.join(narration_dir, f"sil_{i:02d}.mp3")
                subprocess.run(
                    [self._ffmpeg, "-y", "-f", "lavfi",
                     "-i", "anullsrc=r=24000:cl=mono",
                     "-t", str(pause),
                     "-c:a", "libmp3lame", "-q:a", "9", sil_path],
                    capture_output=True,
                )
                part_paths.append(sil_path)

        # Concatenate all parts
        list_path = os.path.join(narration_dir, "concat_list.txt")
        with open(list_path, "w") as f:
            for p in part_paths:
                f.write(f"file '{p}'\n")

        output_path = os.path.join(self.config.output_dir, "narration.mp3")
        subprocess.run(
            [self._ffmpeg, "-y", "-f", "concat", "-safe", "0",
             "-i", list_path, "-c:a", "libmp3lame", "-q:a", "2", output_path],
            capture_output=True,
        )
        return output_path

    # ── Combine Video + Audio ────────────────────────────────────────────

    def combine_video_audio(self, video_path: str, audio_path: str) -> str:
        """Combine rendered video with narration audio using ffmpeg."""
        cfg = self.config
        output_path = os.path.join(
            cfg.output_dir,
            f"{cfg.product_name}_v{cfg.version}_release.mp4",
        )

        # Get audio duration to set output length
        dur = self._get_duration(audio_path)
        if dur <= 0:
            dur = cfg.max_duration

        cmd = [
            self._ffmpeg, "-y",
            "-stream_loop", "-1", "-i", video_path,
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(min(dur, cfg.max_duration)),
            "-pix_fmt", "yuv420p",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg combine failed:\n{result.stderr}")

        return output_path

    def _get_duration(self, path: str) -> float:
        result = subprocess.run(
            [self._ffmpeg, "-i", path, "-f", "null", "-"],
            capture_output=True, text=True,
        )
        for line in result.stderr.splitlines():
            if "Duration:" in line:
                t = line.split("Duration:")[1].split(",")[0].strip().split(":")
                return float(t[0]) * 3600 + float(t[1]) * 60 + float(t[2])
        return 0.0

    # ── Manifest ─────────────────────────────────────────────────────────

    def generate_manifest(self, video_path: str) -> Dict[str, Any]:
        """Generate metadata manifest for the release video."""
        cfg = self.config
        cl = cfg.changelog
        duration = self._get_duration(video_path) if os.path.exists(video_path) else 0

        manifest = {
            "version": cfg.version,
            "product_name": cfg.product_name,
            "date": cl.date if cl else datetime.now().strftime("%Y-%m-%d"),
            "duration_seconds": round(duration, 1),
            "resolution": f"{cfg.resolution[0]}x{cfg.resolution[1]}",
            "fps": cfg.fps,
            "video_path": video_path,
            "changelog_summary": {
                "features": len(cl.features) if cl else 0,
                "fixes": len(cl.fixes) if cl else 0,
                "breaking_changes": len(cl.breaking_changes) if cl else 0,
                "contributors": len(cl.contributors) if cl else 0,
                "files_changed": cl.stats.get("files_changed", 0) if cl else 0,
            },
        }

        manifest_path = os.path.join(cfg.output_dir, "release_video_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        return manifest

    # ── Full Pipeline ────────────────────────────────────────────────────

    def generate(self) -> Dict[str, Any]:
        """Run the full release video pipeline."""
        cfg = self.config
        os.makedirs(cfg.output_dir, exist_ok=True)

        result: Dict[str, Any] = {
            "version": cfg.version,
            "narration_script": None,
            "video_path": None,
            "audio_path": None,
            "final_video_path": None,
            "manifest": None,
        }

        # 1. Render Manim video
        video_path = self.render_video()
        result["video_path"] = video_path

        # 2. Generate narration (optional)
        if cfg.include_narration:
            segments = self.generate_narration_script()
            result["narration_script"] = segments

            audio_path = self.generate_narration(segments)
            result["audio_path"] = audio_path

            # 3. Combine video + audio
            final_path = self.combine_video_audio(video_path, audio_path)
            result["final_video_path"] = final_path
        else:
            result["final_video_path"] = video_path

        # 4. Generate manifest
        manifest = self.generate_manifest(result["final_video_path"])
        result["manifest"] = manifest
        result["changelog"] = {
            "version": cfg.changelog.version if cfg.changelog else cfg.version,
            "features": len(cfg.changelog.features) if cfg.changelog else 0,
            "fixes": len(cfg.changelog.fixes) if cfg.changelog else 0,
        }

        return result
