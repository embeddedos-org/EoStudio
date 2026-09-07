"""EoStudio GUI widgets — require tkinter/display environment.

Gracefully skipped on headless servers, Docker, and CI environments.
"""

import logging

_log = logging.getLogger(__name__)
GUI_AVAILABLE = False
try:
    from eostudio.gui.widgets.canvas_2d import Canvas2D
    from eostudio.gui.widgets.color_picker import ColorPicker
    from eostudio.gui.widgets.properties import PropertiesPanel
    from eostudio.gui.widgets.timeline import TimelineWidget
    from eostudio.gui.widgets.toolbar import Toolbar

    GUI_AVAILABLE = True
    __all__ = ["Canvas2D", "ColorPicker", "PropertiesPanel", "TimelineWidget", "Toolbar", "GUI_AVAILABLE"]
except ImportError as _e:
    _log.debug("GUI widgets unavailable (no display/tkinter): %s", _e)
    __all__ = ["GUI_AVAILABLE"]
