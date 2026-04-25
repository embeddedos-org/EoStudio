"""Video and promo generation engine — recording, compositing, and export."""

from eostudio.core.video.recorder import ScreenRecorder, RecordingConfig
from eostudio.core.video.compositor import VideoCompositor, Layer, LayerType
from eostudio.core.video.export import VideoExporter, ExportFormat, ExportConfig
from eostudio.core.video.promo_templates import PromoTemplate, PROMO_TEMPLATES, get_template

__all__ = [
    "ScreenRecorder", "RecordingConfig",
    "VideoCompositor", "Layer", "LayerType",
    "VideoExporter", "ExportFormat", "ExportConfig",
    "PromoTemplate", "PROMO_TEMPLATES", "get_template",
]
