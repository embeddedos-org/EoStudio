"""Tests for video engine — recorder, compositor, export, promo templates."""

import pytest

from eostudio.core.video.recorder import ScreenRecorder, RecordingConfig, RecordingState
from eostudio.core.video.compositor import (
    VideoCompositor, Layer, LayerType, LayerTransform, BlendMode,
)
from eostudio.core.video.export import (
    VideoExporter, ExportConfig, ExportFormat, ExportPreset, PRESET_SIZES,
)
from eostudio.core.video.promo_templates import (
    PROMO_TEMPLATES, get_template, list_templates, template_categories,
)


# -----------------------------------------------------------------------
# Screen Recorder
# -----------------------------------------------------------------------

class TestScreenRecorder:
    def test_create(self):
        rec = ScreenRecorder()
        assert rec.state == RecordingState.IDLE

    def test_start_stop(self):
        rec = ScreenRecorder()
        rec.start()
        assert rec.state == RecordingState.RECORDING
        frames = rec.stop()
        assert rec.state == RecordingState.STOPPED
        assert isinstance(frames, list)

    def test_capture_frame(self):
        rec = ScreenRecorder()
        rec.start()
        frame = rec.capture_frame({"screen": "home"}, cursor=(100, 200))
        assert frame is not None
        assert frame.index == 0
        assert frame.cursor_position == (100, 200)

    def test_pause_resume(self):
        rec = ScreenRecorder()
        rec.start()
        rec.pause()
        assert rec.state == RecordingState.PAUSED
        frame = rec.capture_frame({})
        assert frame is None  # can't capture while paused
        rec.resume()
        assert rec.state == RecordingState.RECORDING

    def test_frame_count(self):
        rec = ScreenRecorder()
        rec.start()
        rec.capture_frame({"a": 1})
        rec.capture_frame({"b": 2})
        rec.capture_frame({"c": 3})
        assert rec.frame_count == 3

    def test_annotation(self):
        rec = ScreenRecorder()
        rec.start()
        rec.capture_frame({})
        rec.add_annotation("Hello", (100, 100), duration=2.0)
        frames = rec.stop()
        assert len(frames[0].annotations) == 1
        assert frames[0].annotations[0]["text"] == "Hello"

    def test_to_dict(self):
        rec = ScreenRecorder()
        rec.start()
        rec.capture_frame({"test": True})
        data = rec.to_dict()
        assert data["frame_count"] == 1


# -----------------------------------------------------------------------
# Video Compositor
# -----------------------------------------------------------------------

class TestVideoCompositor:
    def test_create(self):
        comp = VideoCompositor(1920, 1080, fps=30, duration=10.0)
        assert comp.width == 1920
        assert comp.height == 1080

    def test_add_text_layer(self):
        comp = VideoCompositor()
        layer = comp.add_text_layer("Hello World", x=100, y=200)
        assert layer.layer_type == LayerType.TEXT
        assert layer.content["text"] == "Hello World"

    def test_add_device_mockup(self):
        comp = VideoCompositor()
        layer = comp.add_device_mockup("iphone_14", x=960, y=540)
        assert layer.layer_type == LayerType.DEVICE_FRAME
        assert layer.content["device"] == "iphone_14"

    def test_add_gradient(self):
        comp = VideoCompositor()
        layer = comp.add_background_gradient(["#000", "#333"])
        assert layer.layer_type == LayerType.GRADIENT

    def test_render_frame(self):
        comp = VideoCompositor(duration=5.0)
        comp.add_text_layer("Title", start=0, end=3)
        frame = comp.render_frame(1.0)
        assert frame["time"] == 1.0
        assert len(frame["layers"]) == 1

    def test_layer_not_visible_at_time(self):
        comp = VideoCompositor(duration=5.0)
        comp.add_text_layer("Late", start=3, end=5)
        frame = comp.render_frame(1.0)
        assert len(frame["layers"]) == 0  # not visible yet

    def test_render_all_frames(self):
        comp = VideoCompositor(duration=1.0, fps=10)
        comp.add_text_layer("X")
        frames = comp.render_all_frames()
        assert len(frames) >= 10

    def test_layer_keyframes(self):
        comp = VideoCompositor()
        layer = comp.create_layer("test", LayerType.TEXT)
        layer.add_keyframe(0.0, x=0, opacity=0)
        layer.add_keyframe(1.0, x=100, opacity=1)
        t = layer.evaluate_transform(0.5)
        assert t.x == 50.0
        assert t.opacity == 0.5

    def test_move_layer(self):
        comp = VideoCompositor()
        l1 = comp.create_layer("A", LayerType.TEXT)
        l2 = comp.create_layer("B", LayerType.TEXT)
        comp.move_layer(l2.id, 0)
        assert comp.layers[0].id == l2.id

    def test_remove_layer(self):
        comp = VideoCompositor()
        layer = comp.create_layer("X", LayerType.TEXT)
        comp.remove_layer(layer.id)
        assert len(comp.layers) == 0

    def test_ffmpeg_command(self):
        comp = VideoCompositor(1920, 1080, fps=30)
        cmd = comp.generate_ffmpeg_command("output.mp4")
        assert "ffmpeg" in cmd
        assert "1920x1080" in cmd

    def test_to_dict(self):
        comp = VideoCompositor()
        comp.add_text_layer("Test")
        data = comp.to_dict()
        assert data["width"] == 1920
        assert len(data["layers"]) == 1


class TestLayerTransform:
    def test_css_transform(self):
        t = LayerTransform(x=100, y=50, rotation=45, scale_x=2)
        css = t.to_css_transform()
        assert "translate" in css
        assert "rotate" in css
        assert "scale" in css

    def test_identity_transform(self):
        t = LayerTransform()
        assert t.to_css_transform() == "none"


# -----------------------------------------------------------------------
# Export
# -----------------------------------------------------------------------

class TestExport:
    def test_preset_sizes(self):
        assert len(PRESET_SIZES) >= 9
        assert PRESET_SIZES[ExportPreset.SOCIAL_SQUARE]["width"] == 1080
        assert PRESET_SIZES[ExportPreset.SOCIAL_SQUARE]["height"] == 1080

    def test_export_config_preset(self):
        config = ExportConfig(preset=ExportPreset.APP_STORE)
        assert config.width == 1290
        assert config.height == 2796

    def test_exporter_command(self):
        exporter = VideoExporter(ExportConfig(width=1080, height=1080, fps=30))
        cmd = exporter.generate_command("./frames", "output.mp4")
        assert "1080x1080" in cmd
        assert "output.mp4" in cmd


# -----------------------------------------------------------------------
# Promo Templates
# -----------------------------------------------------------------------

class TestPromoTemplates:
    def test_templates_loaded(self):
        assert len(PROMO_TEMPLATES) >= 6

    def test_get_template(self):
        tmpl = get_template("social_square")
        assert tmpl is not None
        assert tmpl.width == 1080
        assert tmpl.height == 1080

    def test_get_missing_template(self):
        assert get_template("nonexistent") is None

    def test_create_compositor(self):
        tmpl = get_template("social_square")
        comp = tmpl.create_compositor(product_name="TestApp", tagline="Best app ever")
        assert comp.width == 1080
        assert len(comp.layers) > 0

    def test_variable_substitution(self):
        tmpl = get_template("twitter_card")
        comp = tmpl.create_compositor(title="My Title", subtitle="My Sub")
        # Check that text layers have substituted values
        for layer in comp.layers:
            if layer.content.get("text"):
                assert "{title}" not in layer.content["text"]

    def test_categories(self):
        cats = template_categories()
        assert "social" in cats

    def test_list_by_category(self):
        social = list_templates("social")
        assert len(social) >= 3

    def test_app_store_template(self):
        tmpl = get_template("app_store_preview")
        assert tmpl.width == 1290
        assert tmpl.height == 2796
        assert tmpl.category == "app_store"

    def test_product_launch(self):
        tmpl = get_template("product_launch")
        assert tmpl.duration == 15.0
        comp = tmpl.create_compositor(product_name="EoStudio")
        frames = comp.render_all_frames()
        assert len(frames) > 0
