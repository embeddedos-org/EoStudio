"""Layers panel — visibility, lock state, and z-order for a document."""

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
    from tkinter import ttk
except ImportError:
    raise ImportError("tkinter not available — install python3-tk or run in GUI mode")

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional


@dataclass
class Layer:
    """One layer. `visible` and `locked` are independent: a locked layer is
    still drawn, and a hidden layer can still be edited by a tool that
    addresses it directly."""

    name: str
    visible: bool = True
    locked: bool = False


class LayersPanel(ttk.Frame):
    """Ordered list of layers with visibility and lock toggles.

    Index 0 is the topmost layer, matching how the list reads on screen. The
    panel holds the layer list because ordering is a property of the panel's
    own presentation; the document is told about changes through `on_change`.
    """

    def __init__(
        self,
        master: tk.Widget,
        on_change: Optional[Callable[[List[Layer]], None]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        self._layers: List[Layer] = []
        self._on_change = on_change

        self._list = tk.Listbox(self, activestyle="none", exportselection=False)
        self._list.pack(fill="both", expand=True)

    # ── model ────────────────────────────────────────────────────────────

    @property
    def layers(self) -> List[Layer]:
        """A copy — callers must go through the methods so the view stays in
        step with the list."""
        return list(self._layers)

    def set_layers(self, layers: List[Layer]) -> None:
        names = [l.name for l in layers]
        if len(set(names)) != len(names):
            raise ValueError("layer names must be unique")
        self._layers = list(layers)
        self._refresh()

    def add_layer(self, name: str, visible: bool = True,
                  locked: bool = False) -> Layer:
        if any(l.name == name for l in self._layers):
            raise ValueError(f"a layer named {name!r} already exists")
        layer = Layer(name=name, visible=visible, locked=locked)
        self._layers.insert(0, layer)     # new layers go on top
        self._refresh()
        return layer

    def remove_layer(self, name: str) -> None:
        before = len(self._layers)
        self._layers = [l for l in self._layers if l.name != name]
        if len(self._layers) == before:
            raise KeyError(f"no layer named {name!r}")
        self._refresh()

    def index_of(self, name: str) -> int:
        for i, layer in enumerate(self._layers):
            if layer.name == name:
                return i
        raise KeyError(f"no layer named {name!r}")

    # ── state ────────────────────────────────────────────────────────────

    def toggle_visible(self, name: str) -> bool:
        layer = self._layers[self.index_of(name)]
        layer.visible = not layer.visible
        self._refresh()
        return layer.visible

    def toggle_locked(self, name: str) -> bool:
        layer = self._layers[self.index_of(name)]
        layer.locked = not layer.locked
        self._refresh()
        return layer.locked

    def visible_layers(self) -> List[Layer]:
        return [l for l in self._layers if l.visible]

    # ── ordering ─────────────────────────────────────────────────────────

    def move(self, name: str, delta: int) -> int:
        """Move a layer by `delta` positions; negative is toward the top.

        Clamped rather than wrapped: dragging past the end of the list should
        rest at the end, not reappear at the other side.
        """
        i = self.index_of(name)
        j = max(0, min(len(self._layers) - 1, i + delta))
        if i != j:
            self._layers.insert(j, self._layers.pop(i))
            self._refresh()
        return j

    # ── view ─────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        self._list.delete(0, tk.END)
        for layer in self._layers:
            marks = ("  " if layer.visible else "· ") + ("🔒" if layer.locked else "")
            self._list.insert(tk.END, f"{marks}{layer.name}")
        if self._on_change is not None:
            self._on_change(self.layers)
