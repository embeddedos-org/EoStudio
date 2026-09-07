"""Interior design editor for EoStudio."""

from __future__ import annotations

# GUI_AVAILABLE guard — headless/server compatibility
import sys as _sys

try:
    import tkinter as _tkinter_check

    _TKINTER_OK = True
except ImportError:
    _TKINTER_OK = False
if not _TKINTER_OK:
    import types as _types

    _mod = _types.ModuleType(__name__)
    _mod.GUI_AVAILABLE = False
    _sys.modules[__name__] = _mod
    raise ImportError(f"tkinter not available — {__name__} requires a display environment")
GUI_AVAILABLE = True


try:
    import tkinter as tk
except ImportError:
    raise ImportError("tkinter not available — install python3-tk or run in GUI mode")
from typing import Any


class InteriorEditor(tk.Frame):
    """Interior / architectural design editor with room planner."""

    def __init__(self, master: tk.Widget, bg: str = "#1e1e2e", fg: str = "#cdd6f4", **kw: Any) -> None:
        super().__init__(master, bg=bg, **kw)
        self._bg = bg
        self._fg = fg
        self._build_ui()

    def _build_ui(self) -> None:
        header = tk.Label(self, text="Interior Editor", bg=self._bg, fg=self._fg, font=("Segoe UI", 12, "bold"))
        header.pack(fill=tk.X, padx=8, pady=8)
        self._canvas = tk.Canvas(self, bg="#11111b", highlightthickness=0)
        self._canvas.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
