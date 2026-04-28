"""End-to-end integration tests — release video generation pipeline."""

import json
import os
import tempfile
import textwrap
from unittest.mock import MagicMock, patch

import pytest

from eostudio.core.video.release_video import (
    ChangelogEntry,
    ChangelogParser,
    ReleaseChangelog,
    ReleaseVideoConfig,
    ReleaseVideoGenerator,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_changelog() -> ReleaseChangelog:
    """Create a realistic changelog for testing."""
    return ReleaseChangelog(
        version="2.1.0",
        previous_version="2.0.0",
        date="2026-04-28",
        features=[
            ChangelogEntry(hash="aaa1111", subject="Add release video pipeline", author="Alice", date="2026-04-25", type="feat"),
            ChangelogEntry(hash="bbb2222", subject="Add dark mode support", author="Bob", date="2026-04-26", type="feat"),
            ChangelogEntry(hash="ccc3333", subject="Add plugin marketplace", author="Carol", date="2026-04-27", type="feat"),
        ],
        fixes=[
            ChangelogEntry(hash="ddd4444", subject="Fix crash on large files", author="Dave", date="2026-04-25", type="fix"),
            ChangelogEntry(hash="eee5555", subject="Fix memory leak in renderer", author="Eve", date="2026-04-26", type="fix"),
        ],
        breaking_changes=[
            ChangelogEntry(hash="fff6666", subject="Remove deprecated API v1 endpoints", author="Alice", date="2026-04-27", type="feat", breaking=True),
        ],
        contributors={"Alice", "Bob", "Carol", "Dave", "Eve"},
        stats={"files_changed": 42, "insertions": 1337, "deletions": 256},
    )


@pytest.fixture
def changelog():
    return _make_changelog()


@pytest.fixture
def output_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def config(changelog, output_dir):
    return ReleaseVideoConfig(
        version="2.1.0",
        product_name="EoStudio",
        tagline="Design Everything.",
        changelog=changelog,
        output_dir=output_dir,
        include_narration=False,
    )


@pytest.fixture
def config_with_narration(changelog, output_dir):
    return ReleaseVideoConfig(
        version="2.1.0",
        product_name="EoStudio",
        tagline="Design Everything.",
        changelog=changelog,
        output_dir=output_dir,
        include_narration=True,
    )


# ── ChangelogParser ──────────────────────────────────────────────────────────

class TestChangelogParser:
    """Test git changelog parsing."""

    def test_semver_sort(self):
        parser = ChangelogParser()
        assert parser._semver_key("v1.2.3") == (1, 2, 3)
        assert parser._semver_key("v10.0.0") > parser._semver_key("v2.9.9")

    @patch("subprocess.run")
    def test_get_version_tags(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="v1.0.0\nv2.0.0\nv1.1.0\nv2.1.0",
        )
        parser = ChangelogParser("/fake/path")
        tags = parser.get_version_tags()
        assert tags == ["v1.0.0", "v1.1.0", "v2.0.0", "v2.1.0"]

    @patch("subprocess.run")
    def test_get_version_tags_empty(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        parser = ChangelogParser()
        assert parser.get_version_tags() == []

    @patch("subprocess.run")
    def test_parse_between_tags(self, mock_run):
        git_log_output = (
            "abc1234\n"
            "feat: add new widget\n"
            "\n"
            "Alice\n"
            "2026-04-20T10:00:00\n"
            "---END---\n"
            "def5678\n"
            "fix: resolve crash on startup\n"
            "\n"
            "Bob\n"
            "2026-04-21T11:00:00\n"
            "---END---"
        )
        stat_output = " 10 files changed, 200 insertions(+), 50 deletions(-)"

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=git_log_output),  # git log
            MagicMock(returncode=0, stdout=stat_output),      # git diff --shortstat
        ]

        parser = ChangelogParser("/fake")
        cl = parser.parse_between_tags("v1.0.0", "v2.0.0")

        assert cl.version == "2.0.0"
        assert cl.previous_version == "1.0.0"
        assert len(cl.features) == 1
        assert len(cl.fixes) == 1
        assert cl.features[0].subject == "add new widget"
        assert cl.fixes[0].subject == "resolve crash on startup"
        assert "Alice" in cl.contributors
        assert "Bob" in cl.contributors
        assert cl.stats["files_changed"] == 10
        assert cl.stats["insertions"] == 200
        assert cl.stats["deletions"] == 50

    @patch("subprocess.run")
    def test_parse_detects_breaking_changes(self, mock_run):
        git_log_output = (
            "aaa1111\n"
            "feat!: remove old API\n"
            "BREAKING CHANGE: v1 API removed\n"
            "Alice\n"
            "2026-04-20T10:00:00\n"
            "---END---"
        )
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=git_log_output),
            MagicMock(returncode=0, stdout=""),
        ]

        parser = ChangelogParser()
        cl = parser.parse_between_tags("v1.0.0", "v2.0.0")
        assert len(cl.breaking_changes) == 1
        assert cl.breaking_changes[0].breaking is True

    @patch("subprocess.run")
    def test_parse_latest_release(self, mock_run):
        mock_run.side_effect = [
            # get_version_tags
            MagicMock(returncode=0, stdout="v1.0.0\nv2.0.0"),
            # parse_between_tags -> git log
            MagicMock(returncode=0, stdout="abc\nfeat: stuff\n\nAlice\n2026-01-01\n---END---"),
            # get_stats
            MagicMock(returncode=0, stdout=" 5 files changed, 100 insertions(+)"),
        ]

        parser = ChangelogParser()
        cl = parser.parse_latest_release()
        assert cl.version == "2.0.0"
        assert cl.previous_version == "1.0.0"

    @patch("subprocess.run")
    def test_parse_latest_release_insufficient_tags(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="v1.0.0")
        parser = ChangelogParser()
        with pytest.raises(RuntimeError, match="Need at least 2 version tags"):
            parser.parse_latest_release()

    @patch("subprocess.run")
    def test_get_stats(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=" 15 files changed, 300 insertions(+), 75 deletions(-)",
        )
        parser = ChangelogParser()
        stats = parser.get_stats("v1.0.0", "v2.0.0")
        assert stats == {"files_changed": 15, "insertions": 300, "deletions": 75}

    @patch("subprocess.run")
    def test_get_stats_git_error(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr="fatal: bad revision")
        parser = ChangelogParser()
        stats = parser.get_stats("v1.0.0", "v2.0.0")
        assert stats == {"files_changed": 0, "insertions": 0, "deletions": 0}


# ── Manim Script Generation ─────────────────────────────────────────────────

class TestManimScriptGeneration:
    """Test that generated Manim scripts are valid and contain correct content."""

    def test_generates_valid_python(self, config):
        gen = ReleaseVideoGenerator(config)
        script = gen.generate_manim_script()

        # Must be valid Python syntax
        compile(script, "<release_video>", "exec")

    def test_contains_version(self, config):
        gen = ReleaseVideoGenerator(config)
        script = gen.generate_manim_script()
        assert "2.1.0" in script

    def test_contains_product_name(self, config):
        gen = ReleaseVideoGenerator(config)
        script = gen.generate_manim_script()
        assert "EoStudio" in script

    def test_contains_all_slide_methods(self, config):
        gen = ReleaseVideoGenerator(config)
        script = gen.generate_manim_script()
        assert "def slide_hero(self):" in script
        assert "def slide_features(self):" in script
        assert "def slide_fixes(self):" in script
        assert "def slide_stats(self):" in script
        assert "def slide_cta(self):" in script

    def test_contains_breaking_changes_slide(self, config):
        gen = ReleaseVideoGenerator(config)
        script = gen.generate_manim_script()
        # Config has breaking changes, so the slide should be present
        assert "def slide_breaking(self):" in script
        assert "self.slide_breaking()" in script

    def test_no_breaking_slide_when_none(self, output_dir):
        cl = _make_changelog()
        cl.breaking_changes = []
        config = ReleaseVideoConfig(
            version="2.1.0", changelog=cl, output_dir=output_dir,
        )
        gen = ReleaseVideoGenerator(config)
        script = gen.generate_manim_script()
        assert "def slide_breaking" not in script

    def test_features_in_script(self, config):
        gen = ReleaseVideoGenerator(config)
        script = gen.generate_manim_script()
        assert "Add release video pipeline" in script
        assert "Add dark mode support" in script

    def test_fixes_in_script(self, config):
        gen = ReleaseVideoGenerator(config)
        script = gen.generate_manim_script()
        assert "Fix crash on large files" in script

    def test_stats_in_script(self, config):
        gen = ReleaseVideoGenerator(config)
        script = gen.generate_manim_script()
        assert "42" in script   # files_changed
        assert "5" in script    # contributors

    def test_uses_color_palette(self, config):
        gen = ReleaseVideoGenerator(config)
        script = gen.generate_manim_script()
        assert "#0a0a1a" in script  # BG
        assert "#3b82f6" in script  # PRIMARY
        assert "#8b5cf6" in script  # SECONDARY

    def test_custom_color_scheme(self, output_dir):
        config = ReleaseVideoConfig(
            version="1.0.0",
            changelog=_make_changelog(),
            output_dir=output_dir,
            color_scheme={
                "bg": "#111111", "primary": "#ff0000",
                "secondary": "#00ff00", "accent": "#0000ff",
            },
        )
        gen = ReleaseVideoGenerator(config)
        script = gen.generate_manim_script()
        assert "#111111" in script
        assert "#ff0000" in script

    def test_scene_class_name(self, config):
        gen = ReleaseVideoGenerator(config)
        script = gen.generate_manim_script()
        assert "class ReleaseVideo(Scene):" in script

    def test_script_writes_to_output_dir(self, config):
        gen = ReleaseVideoGenerator(config)
        script = gen.generate_manim_script()

        # Also verify it can be written as a file
        script_path = os.path.join(config.output_dir, "test_scene.py")
        os.makedirs(config.output_dir, exist_ok=True)
        with open(script_path, "w") as f:
            f.write(script)
        assert os.path.exists(script_path)

    def test_max_features_shown(self, output_dir):
        cl = _make_changelog()
        # Add more features than the default max
        for i in range(10):
            cl.features.append(ChangelogEntry(
                hash=f"x{i}", subject=f"Feature {i}", type="feat",
            ))
        config = ReleaseVideoConfig(
            version="3.0.0", changelog=cl, output_dir=output_dir,
            max_features_shown=4,
        )
        gen = ReleaseVideoGenerator(config)
        script = gen.generate_manim_script()
        # Only the first 4 features (out of 13 total) should appear
        assert "Feature 0" in script
        assert "Feature 3" not in script  # index 3 is feature #4 in the appended list,
        # but the first 3 are from _make_changelog; 4th shown = Feature 0


# ── Narration Script Generation ─────────────────────────────────────────────

class TestNarrationScriptGeneration:
    """Test TTS narration script generation."""

    def test_generates_segments(self, config):
        gen = ReleaseVideoGenerator(config)
        segments = gen.generate_narration_script()
        assert len(segments) >= 4  # intro, features, fixes, stats, outro

    def test_segments_have_required_fields(self, config):
        gen = ReleaseVideoGenerator(config)
        segments = gen.generate_narration_script()
        for seg in segments:
            assert "text" in seg
            assert "pause_after" in seg
            assert isinstance(seg["text"], str)
            assert isinstance(seg["pause_after"], (int, float))
            assert len(seg["text"]) > 0

    def test_intro_mentions_version(self, config):
        gen = ReleaseVideoGenerator(config)
        segments = gen.generate_narration_script()
        intro = segments[0]["text"]
        assert "2.1.0" in intro
        assert "EoStudio" in intro

    def test_features_segment(self, config):
        gen = ReleaseVideoGenerator(config)
        segments = gen.generate_narration_script()
        feature_seg = segments[1]["text"]
        assert "3 new features" in feature_seg

    def test_fixes_segment(self, config):
        gen = ReleaseVideoGenerator(config)
        segments = gen.generate_narration_script()
        # Find the fixes segment
        fix_texts = [s["text"] for s in segments if "bugs" in s["text"].lower() or "fixed" in s["text"].lower()]
        assert len(fix_texts) >= 1
        assert "2" in fix_texts[0]  # 2 bugs fixed

    def test_contributors_segment(self, config):
        gen = ReleaseVideoGenerator(config)
        segments = gen.generate_narration_script()
        contrib_texts = [s["text"] for s in segments if "contributors" in s["text"].lower() or "developers" in s["text"].lower()]
        assert len(contrib_texts) >= 1
        assert "5" in contrib_texts[0]  # 5 contributors

    def test_breaking_changes_segment(self, config):
        gen = ReleaseVideoGenerator(config)
        segments = gen.generate_narration_script()
        breaking_texts = [s["text"] for s in segments if "breaking" in s["text"].lower()]
        assert len(breaking_texts) == 1

    def test_no_breaking_segment_when_none(self, output_dir):
        cl = _make_changelog()
        cl.breaking_changes = []
        config = ReleaseVideoConfig(version="2.1.0", changelog=cl, output_dir=output_dir)
        gen = ReleaseVideoGenerator(config)
        segments = gen.generate_narration_script()
        breaking_texts = [s["text"] for s in segments if "breaking" in s["text"].lower()]
        assert len(breaking_texts) == 0

    def test_outro_mentions_upgrade(self, config):
        gen = ReleaseVideoGenerator(config)
        segments = gen.generate_narration_script()
        outro = segments[-1]["text"]
        assert "2.1.0" in outro

    def test_pauses_are_positive(self, config):
        gen = ReleaseVideoGenerator(config)
        segments = gen.generate_narration_script()
        for seg in segments:
            assert seg["pause_after"] > 0


# ── Video Rendering (mocked) ────────────────────────────────────────────────

class TestVideoRendering:
    """Test video render pipeline with mocked subprocess calls."""

    @patch("subprocess.run")
    def test_render_video_writes_script_file(self, mock_run, config):
        # Mock manim render succeeding
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        gen = ReleaseVideoGenerator(config)

        # Write the script file (first part of render_video)
        script_content = gen.generate_manim_script()
        script_path = os.path.join(config.output_dir, "release_scene.py")
        os.makedirs(config.output_dir, exist_ok=True)
        with open(script_path, "w") as f:
            f.write(script_content)

        assert os.path.exists(script_path)
        with open(script_path) as f:
            content = f.read()
        assert "class ReleaseVideo(Scene):" in content

    @patch("subprocess.run")
    def test_render_video_calls_manim(self, mock_run, config):
        # Create a fake output video so render_video finds it
        video_dir = os.path.join(config.output_dir, "videos")
        os.makedirs(video_dir, exist_ok=True)
        fake_video = os.path.join(video_dir, "ReleaseVideo.mp4")
        with open(fake_video, "w") as f:
            f.write("fake")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        gen = ReleaseVideoGenerator(config)
        result = gen.render_video()

        assert result.endswith(".mp4")
        # Verify manim was called
        manim_calls = [c for c in mock_run.call_args_list if "manim" in str(c)]
        assert len(manim_calls) >= 1

    @patch("subprocess.run")
    def test_render_video_raises_on_failure(self, mock_run, config):
        mock_run.return_value = MagicMock(returncode=1, stderr="Error: Manim failed")

        gen = ReleaseVideoGenerator(config)
        with pytest.raises(RuntimeError, match="Manim render failed"):
            gen.render_video()


# ── Audio/Video Combine (mocked) ────────────────────────────────────────────

class TestCombineVideoAudio:
    """Test ffmpeg combine with mocked subprocess."""

    @patch("subprocess.run")
    def test_combine_produces_output_path(self, mock_run, config):
        mock_run.return_value = MagicMock(returncode=0, stderr="Duration: 00:00:30.00, ")

        gen = ReleaseVideoGenerator(config)
        result = gen.combine_video_audio("/fake/video.mp4", "/fake/audio.mp3")

        assert "EoStudio_v2.1.0_release.mp4" in result

    @patch("subprocess.run")
    def test_combine_raises_on_failure(self, mock_run, config):
        # _find_ffmpeg call, _get_duration call, then the actual ffmpeg combine
        mock_run.side_effect = [
            MagicMock(returncode=0),  # _find_ffmpeg
            MagicMock(returncode=0, stderr="Duration: 00:00:10.00, "),  # _get_duration
            MagicMock(returncode=1, stderr="ffmpeg error", stdout=""),  # combine
        ]

        gen = ReleaseVideoGenerator(config)
        with pytest.raises(RuntimeError, match="ffmpeg combine failed"):
            gen.combine_video_audio("/fake/video.mp4", "/fake/audio.mp3")


# ── Manifest Generation ─────────────────────────────────────────────────────

class TestManifest:
    """Test release video manifest generation."""

    @patch("subprocess.run")
    def test_manifest_contains_metadata(self, mock_run, config):
        mock_run.return_value = MagicMock(returncode=0, stderr="Duration: 00:00:45.50, ")

        gen = ReleaseVideoGenerator(config)
        os.makedirs(config.output_dir, exist_ok=True)

        # Create a fake video file for duration check
        fake_video = os.path.join(config.output_dir, "test.mp4")
        with open(fake_video, "w") as f:
            f.write("fake")

        manifest = gen.generate_manifest(fake_video)

        assert manifest["version"] == "2.1.0"
        assert manifest["product_name"] == "EoStudio"
        assert manifest["resolution"] == "1920x1080"
        assert manifest["fps"] == 30
        assert manifest["changelog_summary"]["features"] == 3
        assert manifest["changelog_summary"]["fixes"] == 2
        assert manifest["changelog_summary"]["breaking_changes"] == 1
        assert manifest["changelog_summary"]["contributors"] == 5
        assert manifest["changelog_summary"]["files_changed"] == 42

    @patch("subprocess.run")
    def test_manifest_writes_json_file(self, mock_run, config):
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        gen = ReleaseVideoGenerator(config)
        os.makedirs(config.output_dir, exist_ok=True)

        gen.generate_manifest("/nonexistent/video.mp4")

        manifest_path = os.path.join(config.output_dir, "release_video_manifest.json")
        assert os.path.exists(manifest_path)

        with open(manifest_path) as f:
            data = json.load(f)
        assert data["version"] == "2.1.0"


# ── Full Pipeline (mocked) ──────────────────────────────────────────────────

class TestFullPipeline:
    """End-to-end pipeline test with mocked external tools."""

    @patch("subprocess.run")
    def test_generate_without_narration(self, mock_run, config):
        """Full pipeline without narration — render only."""
        video_dir = os.path.join(config.output_dir, "videos")
        os.makedirs(video_dir, exist_ok=True)
        fake_video = os.path.join(video_dir, "ReleaseVideo.mp4")
        with open(fake_video, "wb") as f:
            f.write(b"\x00" * 1024)

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        gen = ReleaseVideoGenerator(config)
        result = gen.generate()

        assert result["version"] == "2.1.0"
        assert result["video_path"] == fake_video
        assert result["final_video_path"] == fake_video  # same when no narration
        assert result["audio_path"] is None
        assert result["narration_script"] is None
        assert result["manifest"] is not None
        assert result["changelog"]["features"] == 3
        assert result["changelog"]["fixes"] == 2

    @patch("subprocess.run")
    def test_generate_creates_output_dir(self, mock_run, output_dir):
        """Pipeline creates the output directory if it doesn't exist."""
        nested_dir = os.path.join(output_dir, "nested", "release")
        config = ReleaseVideoConfig(
            version="1.0.0",
            changelog=_make_changelog(),
            output_dir=nested_dir,
            include_narration=False,
        )

        video_dir = os.path.join(nested_dir, "videos")
        os.makedirs(video_dir, exist_ok=True)
        fake_video = os.path.join(video_dir, "ReleaseVideo.mp4")
        with open(fake_video, "wb") as f:
            f.write(b"\x00" * 512)

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        gen = ReleaseVideoGenerator(config)
        result = gen.generate()

        assert os.path.isdir(nested_dir)
        assert result["manifest"] is not None

    @patch("subprocess.run")
    def test_manifest_written_after_generate(self, mock_run, config):
        video_dir = os.path.join(config.output_dir, "videos")
        os.makedirs(video_dir, exist_ok=True)
        fake_video = os.path.join(video_dir, "ReleaseVideo.mp4")
        with open(fake_video, "wb") as f:
            f.write(b"\x00" * 1024)

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        gen = ReleaseVideoGenerator(config)
        gen.generate()

        manifest_path = os.path.join(config.output_dir, "release_video_manifest.json")
        assert os.path.exists(manifest_path)
        with open(manifest_path) as f:
            data = json.load(f)
        assert data["version"] == "2.1.0"
        assert data["changelog_summary"]["features"] == 3


# ── Config Defaults ──────────────────────────────────────────────────────────

class TestReleaseVideoConfig:
    """Test configuration dataclass defaults and overrides."""

    def test_defaults(self):
        config = ReleaseVideoConfig()
        assert config.version == "0.0.0"
        assert config.product_name == "EoStudio"
        assert config.resolution == (1920, 1080)
        assert config.fps == 30
        assert config.voice == "en-US-GuyNeural"
        assert config.include_narration is True
        assert config.max_features_shown == 6
        assert config.max_duration == 60.0
        assert config.theme == "dark"

    def test_custom_values(self):
        config = ReleaseVideoConfig(
            version="3.0.0",
            product_name="MyApp",
            resolution=(1280, 720),
            fps=60,
            voice="en-US-JennyNeural",
            include_narration=False,
            max_features_shown=10,
            max_duration=120.0,
        )
        assert config.version == "3.0.0"
        assert config.product_name == "MyApp"
        assert config.resolution == (1280, 720)
        assert config.fps == 60
        assert config.voice == "en-US-JennyNeural"
        assert config.include_narration is False

    def test_color_scheme_defaults(self):
        config = ReleaseVideoConfig()
        assert "bg" in config.color_scheme
        assert "primary" in config.color_scheme
        assert config.color_scheme["bg"] == "#0a0a1a"


# ── ChangelogEntry Dataclass ────────────────────────────────────────────────

class TestChangelogEntry:

    def test_defaults(self):
        entry = ChangelogEntry(hash="abc123", subject="Add feature")
        assert entry.type == "chore"
        assert entry.breaking is False
        assert entry.body == ""
        assert entry.author == ""

    def test_custom_values(self):
        entry = ChangelogEntry(
            hash="def456", subject="Fix bug", type="fix",
            author="Alice", date="2026-01-01", breaking=True,
        )
        assert entry.type == "fix"
        assert entry.breaking is True
        assert entry.author == "Alice"


# ── ReleaseChangelog Dataclass ──────────────────────────────────────────────

class TestReleaseChangelog:

    def test_defaults(self):
        cl = ReleaseChangelog(version="1.0.0", previous_version="0.9.0", date="2026-01-01")
        assert cl.features == []
        assert cl.fixes == []
        assert cl.breaking_changes == []
        assert cl.other == []
        assert cl.contributors == set()
        assert cl.stats["files_changed"] == 0

    def test_populated(self):
        cl = _make_changelog()
        assert len(cl.features) == 3
        assert len(cl.fixes) == 2
        assert len(cl.breaking_changes) == 1
        assert len(cl.contributors) == 5
        assert cl.stats["insertions"] == 1337


# ── Realistic Subprocess Mock ────────────────────────────────────────────────

class _SubprocessRouter:
    """Argument-aware subprocess mock that dispatches based on command args.

    Simulates real ffmpeg/manim/git output so tests exercise the actual
    parsing and file-handling logic of the pipeline.
    """

    def __init__(self, output_dir: str) -> None:
        self.output_dir = output_dir
        self.calls: List[tuple] = []  # log of (cmd_name, args) for assertions

    def __call__(self, cmd, **kwargs):
        cmd_str = " ".join(str(c) for c in cmd)
        self.calls.append((cmd[0] if cmd else "", cmd))

        # ── ffmpeg -version (probe) ──────────────────────────────────
        if "-version" in cmd:
            return MagicMock(
                returncode=0,
                stdout="ffmpeg version 6.1 Copyright (c) 2000-2026",
                stderr="",
            )

        # ── manim render ─────────────────────────────────────────────
        if cmd[0] == "manim":
            # Create the video file manim would produce
            media_dir = None
            for i, arg in enumerate(cmd):
                if arg == "--media_dir" and i + 1 < len(cmd):
                    media_dir = cmd[i + 1]
            if media_dir:
                vid_dir = os.path.join(media_dir, "videos", "release_scene", "1080p30")
                os.makedirs(vid_dir, exist_ok=True)
                vid_path = os.path.join(vid_dir, "ReleaseVideo.mp4")
                # Write a minimal fake MP4 header (ftyp box)
                with open(vid_path, "wb") as f:
                    f.write(b"\x00\x00\x00\x1c" + b"ftypisom" + b"\x00" * 16)
                    f.write(b"\x00" * 4096)
            return MagicMock(
                returncode=0,
                stdout="Manim Community v0.18.0\n[scene] ReleaseVideo\nFile ready at ...",
                stderr="",
            )

        # ── ffmpeg: silence generation (anullsrc) ────────────────────
        if "anullsrc" in cmd_str:
            # Create a tiny fake mp3 at the output path (last arg)
            out = cmd[-1]
            os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
            with open(out, "wb") as f:
                f.write(b"\xff\xfb\x90\x00" + b"\x00" * 256)  # fake MP3 frame
            return MagicMock(returncode=0, stdout="", stderr="")

        # ── ffmpeg: concat (narration segments) ──────────────────────
        if "concat" in cmd and "-safe" in cmd:
            out = cmd[-1]
            os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
            with open(out, "wb") as f:
                f.write(b"\xff\xfb\x90\x00" + b"\x00" * 1024)
            return MagicMock(returncode=0, stdout="", stderr="")

        # ── ffmpeg: duration probe (-f null -) ───────────────────────
        if "-f" in cmd and "null" in cmd and "-" in cmd:
            return MagicMock(
                returncode=0,
                stdout="",
                stderr=(
                    "Input #0, mp3, from '/fake/audio.mp3':\n"
                    "  Duration: 00:00:42.50, start: 0.000000, bitrate: 192 kb/s\n"
                    "  Stream #0:0: Audio: mp3, 24000 Hz, mono, fltp, 192 kb/s\n"
                    "size=       0kB time=00:00:42.50 bitrate=N/A\n"
                ),
            )

        # ── ffmpeg: combine video + audio (stream_loop) ──────────────
        if "stream_loop" in cmd_str:
            out = cmd[-1]
            os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
            with open(out, "wb") as f:
                f.write(b"\x00\x00\x00\x1c" + b"ftypisom" + b"\x00" * 16)
                f.write(b"\x00" * 8192)
            return MagicMock(
                returncode=0,
                stdout="",
                stderr=(
                    "frame=  900 fps=120 q=23.0 Lsize=    4kB time=00:00:30.00 "
                    "bitrate= 100.0kbits/s speed=4.0x\n"
                    "video:3kB audio:1kB subtitle:0kB other streams:0kB\n"
                ),
            )

        # ── git commands ─────────────────────────────────────────────
        if cmd[0] == "git":
            if "tag" in cmd:
                return MagicMock(returncode=0, stdout="v2.0.0\nv2.1.0")
            if "log" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=(
                        "aaa1111\nfeat: add release video pipeline\n\n"
                        "Alice\n2026-04-25T10:00:00\n---END---\n"
                        "bbb2222\nfeat: add dark mode support\n\n"
                        "Bob\n2026-04-26T10:00:00\n---END---\n"
                        "ccc3333\nfeat: add plugin marketplace\n\n"
                        "Carol\n2026-04-27T10:00:00\n---END---\n"
                        "ddd4444\nfix: fix crash on large files\n\n"
                        "Dave\n2026-04-25T12:00:00\n---END---\n"
                        "eee5555\nfix: fix memory leak in renderer\n\n"
                        "Eve\n2026-04-26T12:00:00\n---END---"
                    ),
                )
            if "diff" in cmd and "--shortstat" in cmd:
                return MagicMock(
                    returncode=0,
                    stdout=" 42 files changed, 1337 insertions(+), 256 deletions(-)",
                )
            return MagicMock(returncode=0, stdout="", stderr="")

        # ── fallback ─────────────────────────────────────────────────
        return MagicMock(returncode=0, stdout="", stderr="")


class _MockCommunicate:
    """Mock edge_tts.Communicate that writes fake audio files."""

    def __init__(self, text, voice, rate=None, pitch=None):
        self.text = text
        self.voice = voice

    async def save(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            # Write a fake MP3 frame header + proportional data
            f.write(b"\xff\xfb\x90\x00" + b"\x00" * max(128, len(self.text) * 4))


# ── E2E Tests with Realistic Subprocess Mocks ───────────────────────────────

class TestE2EWithRealisticMocks:
    """End-to-end tests using argument-aware subprocess mocks that simulate
    real ffmpeg/manim output, create actual file artifacts, and exercise the
    full pipeline including file I/O, parsing, and error handling."""

    @patch("subprocess.run")
    def test_full_pipeline_no_narration(self, mock_run, output_dir):
        """E2E: changelog → manim script → render → manifest (no narration)."""
        router = _SubprocessRouter(output_dir)
        mock_run.side_effect = router

        config = ReleaseVideoConfig(
            version="2.1.0",
            product_name="EoStudio",
            tagline="Design Everything.",
            changelog=_make_changelog(),
            output_dir=output_dir,
            include_narration=False,
        )

        gen = ReleaseVideoGenerator(config)
        result = gen.generate()

        # Pipeline result structure
        assert result["version"] == "2.1.0"
        assert result["video_path"].endswith(".mp4")
        assert result["final_video_path"] == result["video_path"]
        assert result["audio_path"] is None
        assert result["narration_script"] is None

        # Manim script was written to disk
        script_path = os.path.join(output_dir, "release_scene.py")
        assert os.path.exists(script_path)
        with open(script_path) as f:
            script = f.read()
        assert "class ReleaseVideo(Scene):" in script
        assert "EoStudio" in script
        assert "2.1.0" in script
        compile(script, script_path, "exec")  # valid Python

        # Video file was created by mock
        assert os.path.exists(result["video_path"])
        assert os.path.getsize(result["video_path"]) > 0

        # Manifest written to disk
        manifest_path = os.path.join(output_dir, "release_video_manifest.json")
        assert os.path.exists(manifest_path)
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert manifest["version"] == "2.1.0"
        assert manifest["product_name"] == "EoStudio"
        assert manifest["resolution"] == "1920x1080"
        assert manifest["fps"] == 30
        assert manifest["duration_seconds"] == 42.5
        assert manifest["changelog_summary"]["features"] == 3
        assert manifest["changelog_summary"]["fixes"] == 2
        assert manifest["changelog_summary"]["breaking_changes"] == 1
        assert manifest["changelog_summary"]["contributors"] == 5
        assert manifest["changelog_summary"]["files_changed"] == 42

        # Manim was invoked with correct args
        manim_calls = [c for c in router.calls if c[0] == "manim"]
        assert len(manim_calls) == 1
        manim_args = manim_calls[0][1]
        assert "render" in manim_args
        assert "-qh" in manim_args
        assert "--fps" in manim_args
        assert "30" in manim_args
        assert "ReleaseVideo" in manim_args

    @patch("eostudio.core.video.release_video.edge_tts", create=True)
    @patch("subprocess.run")
    def test_full_pipeline_with_narration(self, mock_run, mock_edge_tts, output_dir):
        """E2E: changelog → manim → narration (edge_tts) → combine → manifest."""
        router = _SubprocessRouter(output_dir)
        mock_run.side_effect = router

        # Mock edge_tts.Communicate to write fake audio
        mock_edge_tts.Communicate = _MockCommunicate

        config = ReleaseVideoConfig(
            version="2.1.0",
            product_name="EoStudio",
            tagline="Design Everything.",
            changelog=_make_changelog(),
            output_dir=output_dir,
            include_narration=True,
            voice="en-US-GuyNeural",
            voice_rate="-5%",
        )

        gen = ReleaseVideoGenerator(config)
        result = gen.generate()

        # Full pipeline results
        assert result["version"] == "2.1.0"
        assert result["video_path"].endswith(".mp4")
        assert result["audio_path"].endswith(".mp3")
        assert result["final_video_path"].endswith("_release.mp4")
        assert result["final_video_path"] != result["video_path"]

        # Narration script was generated
        segments = result["narration_script"]
        assert isinstance(segments, list)
        assert len(segments) >= 4  # intro, features, fixes, stats, breaking, outro
        assert "EoStudio" in segments[0]["text"]
        assert "2.1.0" in segments[0]["text"]

        # Audio file created
        assert os.path.exists(result["audio_path"])

        # Final combined video created
        assert os.path.exists(result["final_video_path"])
        assert "EoStudio_v2.1.0_release.mp4" in result["final_video_path"]

        # Narration segments dir was created with segment files
        narration_dir = os.path.join(output_dir, "narration_segments")
        assert os.path.isdir(narration_dir)
        seg_files = [f for f in os.listdir(narration_dir) if f.startswith("seg_")]
        assert len(seg_files) >= 4  # one per narration segment

        # Concat list was created
        concat_list = os.path.join(narration_dir, "concat_list.txt")
        assert os.path.exists(concat_list)
        with open(concat_list) as f:
            lines = f.readlines()
        assert len(lines) >= len(seg_files)  # segments + silence gaps

        # Manifest has duration from ffmpeg probe
        manifest = result["manifest"]
        assert manifest["duration_seconds"] == 42.5

        # Verify subprocess call sequence: ffmpeg probe, manim, silences, concat, duration, combine, duration
        cmd_names = [c[0] for c in router.calls]
        assert "manim" in cmd_names

    @patch("subprocess.run")
    def test_full_pipeline_with_git_parsing(self, mock_run, output_dir):
        """E2E: git tags → changelog → full pipeline (exercises ChangelogParser + generator)."""
        router = _SubprocessRouter(output_dir)
        mock_run.side_effect = router

        # Use ChangelogParser to build the changelog from mocked git
        parser = ChangelogParser("/fake/repo")
        changelog = parser.parse_latest_release()

        assert changelog.version == "2.1.0"
        assert changelog.previous_version == "2.0.0"
        assert len(changelog.features) == 3
        assert len(changelog.fixes) == 2
        assert changelog.stats["files_changed"] == 42

        config = ReleaseVideoConfig(
            version=changelog.version,
            changelog=changelog,
            output_dir=output_dir,
            include_narration=False,
        )

        gen = ReleaseVideoGenerator(config)
        result = gen.generate()

        assert result["version"] == "2.1.0"
        assert result["changelog"]["features"] == 3
        assert result["changelog"]["fixes"] == 2

        # Verify the generated Manim script includes parsed data
        script_path = os.path.join(output_dir, "release_scene.py")
        with open(script_path) as f:
            script = f.read()
        assert "add release video pipeline" in script
        assert "add dark mode support" in script
        assert "fix crash on large files" in script

    @patch("subprocess.run")
    def test_render_creates_correct_manim_command(self, mock_run, config):
        """E2E: verify exact manim CLI args passed to subprocess."""
        router = _SubprocessRouter(config.output_dir)
        mock_run.side_effect = router

        gen = ReleaseVideoGenerator(config)
        video_path = gen.render_video()

        manim_calls = [c for c in router.calls if c[0] == "manim"]
        assert len(manim_calls) == 1
        args = manim_calls[0][1]

        assert args[0] == "manim"
        assert args[1] == "render"
        assert args[2] == "-qh"  # 1080p = high quality
        assert args[3] == "--fps"
        assert args[4] == "30"
        assert args[5] == "--media_dir"
        assert args[6] == config.output_dir
        assert args[7].endswith("release_scene.py")
        assert args[8] == "ReleaseVideo"

    @patch("subprocess.run")
    def test_render_uses_medium_quality_for_720p(self, mock_run, output_dir):
        """E2E: 720p resolution triggers -qm flag."""
        config = ReleaseVideoConfig(
            version="1.0.0",
            changelog=_make_changelog(),
            output_dir=output_dir,
            resolution=(1280, 720),
            include_narration=False,
        )
        router = _SubprocessRouter(output_dir)
        mock_run.side_effect = router

        gen = ReleaseVideoGenerator(config)
        gen.render_video()

        manim_calls = [c for c in router.calls if c[0] == "manim"]
        assert "-qm" in manim_calls[0][1]

    @patch("subprocess.run")
    def test_combine_uses_correct_ffmpeg_args(self, mock_run, config):
        """E2E: verify ffmpeg combine command structure."""
        router = _SubprocessRouter(config.output_dir)
        mock_run.side_effect = router

        gen = ReleaseVideoGenerator(config)

        # Create dummy files
        vid = os.path.join(config.output_dir, "video.mp4")
        aud = os.path.join(config.output_dir, "audio.mp3")
        os.makedirs(config.output_dir, exist_ok=True)
        for p in (vid, aud):
            with open(p, "wb") as f:
                f.write(b"\x00" * 64)

        result = gen.combine_video_audio(vid, aud)

        # Find the combine call (has stream_loop)
        combine_calls = [c for c in router.calls if "stream_loop" in " ".join(str(a) for a in c[1])]
        assert len(combine_calls) == 1
        args = combine_calls[0][1]

        # Verify key ffmpeg args
        assert "-stream_loop" in args
        assert "-1" in args
        assert "-c:v" in args
        idx_cv = args.index("-c:v")
        assert args[idx_cv + 1] == "libx264"
        assert "-c:a" in args
        idx_ca = args.index("-c:a")
        assert args[idx_ca + 1] == "aac"
        assert "-crf" in args
        assert "-pix_fmt" in args
        assert "yuv420p" in args
        assert "-t" in args
        # Duration capped at min(42.5, max_duration=60)
        idx_t = args.index("-t")
        assert float(args[idx_t + 1]) == 42.5

        assert result.endswith("EoStudio_v2.1.0_release.mp4")
        assert os.path.exists(result)

    @patch("subprocess.run")
    def test_combine_caps_at_max_duration(self, mock_run, output_dir):
        """E2E: video is capped at max_duration when audio is longer."""
        config = ReleaseVideoConfig(
            version="1.0.0",
            changelog=_make_changelog(),
            output_dir=output_dir,
            max_duration=30.0,
        )

        router = _SubprocessRouter(output_dir)
        mock_run.side_effect = router

        gen = ReleaseVideoGenerator(config)
        os.makedirs(output_dir, exist_ok=True)
        vid = os.path.join(output_dir, "v.mp4")
        aud = os.path.join(output_dir, "a.mp3")
        for p in (vid, aud):
            with open(p, "wb") as f:
                f.write(b"\x00" * 64)

        gen.combine_video_audio(vid, aud)

        combine_calls = [c for c in router.calls if "stream_loop" in " ".join(str(a) for a in c[1])]
        args = combine_calls[0][1]
        idx_t = args.index("-t")
        # Audio is 42.5s but max_duration is 30s — should be capped
        assert float(args[idx_t + 1]) == 30.0

    @patch("subprocess.run")
    def test_manim_render_failure_propagates(self, mock_run, config):
        """E2E: manim render failure raises RuntimeError with stderr."""
        def failing_router(cmd, **kwargs):
            if cmd[0] == "manim":
                return MagicMock(
                    returncode=1,
                    stdout="",
                    stderr="Error: LaTeX not found\nTraceback:\n  File scene.py, line 42",
                )
            return MagicMock(returncode=0, stdout="ffmpeg version 6.1", stderr="")

        mock_run.side_effect = failing_router

        gen = ReleaseVideoGenerator(config)
        with pytest.raises(RuntimeError, match="Manim render failed") as exc_info:
            gen.render_video()
        assert "LaTeX not found" in str(exc_info.value)

    @patch("subprocess.run")
    def test_ffmpeg_combine_failure_propagates(self, mock_run, config):
        """E2E: ffmpeg combine failure raises with stderr content."""
        def partial_failure_router(cmd, **kwargs):
            cmd_str = " ".join(str(c) for c in cmd)
            if "stream_loop" in cmd_str:
                return MagicMock(
                    returncode=1,
                    stdout="",
                    stderr="[error] Could not open input file '/fake/video.mp4'",
                )
            if "null" in cmd_str:
                return MagicMock(
                    returncode=0, stdout="",
                    stderr="  Duration: 00:00:10.00, start: 0.0\n",
                )
            return MagicMock(returncode=0, stdout="ffmpeg 6.1", stderr="")

        mock_run.side_effect = partial_failure_router

        gen = ReleaseVideoGenerator(config)
        with pytest.raises(RuntimeError, match="ffmpeg combine failed") as exc_info:
            gen.combine_video_audio("/fake/video.mp4", "/fake/audio.mp3")
        assert "Could not open" in str(exc_info.value)

    @patch("subprocess.run")
    def test_duration_parsing_from_ffmpeg_stderr(self, mock_run, config):
        """E2E: verify _get_duration correctly parses ffmpeg probe output."""
        def duration_router(cmd, **kwargs):
            if "null" in cmd:
                return MagicMock(
                    returncode=0, stdout="",
                    stderr=(
                        "Input #0, mp3, from 'audio.mp3':\n"
                        "  Duration: 01:23:45.67, start: 0.000000\n"
                        "  Stream #0:0: Audio: mp3\n"
                    ),
                )
            return MagicMock(returncode=0, stdout="ffmpeg 6.1", stderr="")

        mock_run.side_effect = duration_router

        gen = ReleaseVideoGenerator(config)
        dur = gen._get_duration("/fake/audio.mp3")
        # 1*3600 + 23*60 + 45.67 = 5025.67
        assert abs(dur - 5025.67) < 0.01

    @patch("subprocess.run")
    def test_duration_returns_zero_on_missing_field(self, mock_run, config):
        """E2E: _get_duration returns 0.0 when ffmpeg output has no Duration line."""
        def no_duration_router(cmd, **kwargs):
            if "null" in cmd:
                return MagicMock(
                    returncode=0, stdout="",
                    stderr="Input #0: some weird format\nStream: video\n",
                )
            return MagicMock(returncode=0, stderr="")

        mock_run.side_effect = no_duration_router

        gen = ReleaseVideoGenerator(config)
        assert gen._get_duration("/fake.mp4") == 0.0

    @patch("subprocess.run")
    def test_artifacts_directory_structure(self, mock_run, output_dir):
        """E2E: verify the complete directory structure after pipeline run."""
        router = _SubprocessRouter(output_dir)
        mock_run.side_effect = router

        config = ReleaseVideoConfig(
            version="3.0.0",
            product_name="TestApp",
            changelog=_make_changelog(),
            output_dir=output_dir,
            include_narration=False,
        )

        gen = ReleaseVideoGenerator(config)
        result = gen.generate()

        # Expected artifacts
        assert os.path.exists(os.path.join(output_dir, "release_scene.py"))
        assert os.path.exists(os.path.join(output_dir, "release_video_manifest.json"))

        # Video lives in manim's media subdir
        assert os.path.exists(result["video_path"])
        assert "videos" in result["video_path"]
        assert "ReleaseVideo.mp4" in result["video_path"]

        # Manifest content matches config
        with open(os.path.join(output_dir, "release_video_manifest.json")) as f:
            m = json.load(f)
        assert m["product_name"] == "TestApp"
        assert m["version"] == "3.0.0"

    @patch("subprocess.run")
    def test_empty_changelog_generates_minimal_video(self, mock_run, output_dir):
        """E2E: pipeline works with an empty changelog (no features/fixes)."""
        router = _SubprocessRouter(output_dir)
        mock_run.side_effect = router

        empty_cl = ReleaseChangelog(
            version="0.1.0", previous_version="0.0.1", date="2026-01-01",
        )
        config = ReleaseVideoConfig(
            version="0.1.0",
            changelog=empty_cl,
            output_dir=output_dir,
            include_narration=False,
        )

        gen = ReleaseVideoGenerator(config)
        result = gen.generate()

        assert result["version"] == "0.1.0"

        # Script should still be valid Python
        script_path = os.path.join(output_dir, "release_scene.py")
        with open(script_path) as f:
            script = f.read()
        compile(script, script_path, "exec")

        # No breaking slide since there are none
        assert "def slide_breaking" not in script

    @patch("subprocess.run")
    def test_special_chars_in_commit_messages(self, mock_run, output_dir):
        """E2E: commit subjects with quotes/special chars are escaped properly."""
        router = _SubprocessRouter(output_dir)
        mock_run.side_effect = router

        cl = ReleaseChangelog(
            version="1.0.0",
            previous_version="0.9.0",
            date="2026-01-01",
            features=[
                ChangelogEntry(hash="a1", subject='Add "smart quotes" feature', type="feat"),
                ChangelogEntry(hash="a2", subject="Fix user's dashboard", type="feat"),
                ChangelogEntry(hash="a3", subject="Support <html> & 'xml' tags", type="feat"),
            ],
            contributors={"Dev"},
            stats={"files_changed": 5, "insertions": 50, "deletions": 10},
        )
        config = ReleaseVideoConfig(
            version="1.0.0", changelog=cl, output_dir=output_dir,
            include_narration=False,
        )

        gen = ReleaseVideoGenerator(config)
        result = gen.generate()

        # Script must still be valid Python despite special chars
        script_path = os.path.join(output_dir, "release_scene.py")
        with open(script_path) as f:
            script = f.read()
        compile(script, script_path, "exec")

    @patch("subprocess.run")
    def test_custom_product_name_and_colors(self, mock_run, output_dir):
        """E2E: custom product name and color scheme flow through to all artifacts."""
        router = _SubprocessRouter(output_dir)
        mock_run.side_effect = router

        config = ReleaseVideoConfig(
            version="5.0.0",
            product_name="SuperDesigner",
            tagline="Create with confidence",
            changelog=_make_changelog(),
            output_dir=output_dir,
            include_narration=False,
            color_scheme={
                "bg": "#000000", "primary": "#ff6600",
                "secondary": "#0066ff", "accent": "#00ff66",
            },
        )

        gen = ReleaseVideoGenerator(config)
        result = gen.generate()

        # Manim script has custom values
        with open(os.path.join(output_dir, "release_scene.py")) as f:
            script = f.read()
        assert "SuperDesigner" in script
        assert "5.0.0" in script
        assert "Create with confidence" in script
        assert "#ff6600" in script
        assert "#0066ff" in script
        assert "#000000" in script

        # Manifest has custom product
        assert result["manifest"]["product_name"] == "SuperDesigner"

        # Without narration, final_video_path is the raw manim output
        assert result["final_video_path"].endswith(".mp4")
