"""EoStudio editor panels — one per design domain.

Requires tkinter (desktop display). Gracefully skipped on headless
environments (Docker, CI, servers). All CLI and AI features remain
fully functional without a display.
"""

import logging

_log = logging.getLogger(__name__)

GUI_AVAILABLE = False

try:
    from eostudio.gui.editors.modeler_3d import Modeler3DEditor
    from eostudio.gui.editors.cad_editor import CADEditor
    from eostudio.gui.editors.image_editor import ImageEditor
    from eostudio.gui.editors.game_editor import GameEditor
    from eostudio.gui.editors.ui_designer import UIDesigner
    from eostudio.gui.editors.product_designer import ProductDesigner
    from eostudio.gui.editors.interior_editor import InteriorEditor
    from eostudio.gui.editors.uml_editor import UMLEditor
    from eostudio.gui.editors.simulation_editor import SimulationEditor
    from eostudio.gui.editors.database_editor import DatabaseEditor
    from eostudio.gui.editors.ide_editor import IDEEditor
    from eostudio.gui.editors.promo_editor import PromoEditor

    GUI_AVAILABLE = True
    __all__ = [
        "Modeler3DEditor",
        "CADEditor",
        "ImageEditor",
        "GameEditor",
        "UIDesigner",
        "ProductDesigner",
        "InteriorEditor",
        "UMLEditor",
        "SimulationEditor",
        "DatabaseEditor",
        "IDEEditor",
        "PromoEditor",
        "GUI_AVAILABLE",
    ]
except ImportError as _e:
    _log.debug("GUI editors unavailable (no display/tkinter): %s", _e)
    __all__ = ["GUI_AVAILABLE"]
