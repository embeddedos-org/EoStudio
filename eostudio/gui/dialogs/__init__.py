"""EoStudio dialog windows.

GUI components require a display environment (tkinter).
On headless servers or Docker containers without a display,
these are safely skipped — all CLI and AI features remain fully functional.
"""

import logging

_log = logging.getLogger(__name__)

try:
    from eostudio.gui.dialogs.export_dialog import ExportDialog
    from eostudio.gui.dialogs.settings_dialog import SettingsDialog
    from eostudio.gui.dialogs.ai_chat import AIChatDialog
    from eostudio.gui.dialogs.design_system_dialog import DesignSystemDialog

    __all__ = ["ExportDialog", "SettingsDialog", "AIChatDialog", "DesignSystemDialog"]
    GUI_AVAILABLE = True
except ImportError as _e:
    _log.debug("GUI dialogs unavailable (no display/tkinter): %s", _e)
    GUI_AVAILABLE = False
    __all__ = ["GUI_AVAILABLE"]
