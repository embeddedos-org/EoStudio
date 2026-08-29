"""Scene hierarchy tree — parent/child structure of the open document."""

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

from typing import Any, Callable, Dict, List, Optional

#: Returned by `selected_id()` when nothing is selected. `None` would be
#: ambiguous with a node whose id is legitimately absent.
NO_SELECTION: Optional[str] = None


class HierarchyPanel(ttk.Frame):
    """A tree of scene nodes, with selection reported to a callback.

    The panel owns no scene state. It renders whatever `set_nodes()` is given
    and reports selection outward, so the editor stays the single source of
    truth for the document.
    """

    def __init__(
        self,
        master: tk.Widget,
        on_select: Optional[Callable[[str], None]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        self._on_select = on_select
        self._tree = ttk.Treeview(self, show="tree", selectmode="browse")
        self._scroll = ttk.Scrollbar(self, orient="vertical",
                                     command=self._tree.yview)
        self._tree.configure(yscrollcommand=self._scroll.set)
        self._tree.pack(side="left", fill="both", expand=True)
        self._scroll.pack(side="right", fill="y")
        self._tree.bind("<<TreeviewSelect>>", self._emit_selection)

    # ── model ────────────────────────────────────────────────────────────

    def set_nodes(self, nodes: List[Dict[str, Any]]) -> None:
        """Replace the tree.

        Each node is ``{"id": str, "name": str, "children": [...]}``. Ids must
        be unique across the whole tree: Treeview keys items by id, and a
        duplicate would silently attach the second node to the first's parent.
        """
        self._tree.delete(*self._tree.get_children())
        seen: set = set()
        self._insert("", nodes, seen)

    def _insert(self, parent: str, nodes: List[Dict[str, Any]],
                seen: set) -> None:
        for node in nodes:
            node_id = str(node.get("id", ""))
            if not node_id:
                raise ValueError(f"hierarchy node {node!r} has no 'id'")
            if node_id in seen:
                raise ValueError(f"duplicate hierarchy node id {node_id!r}")
            seen.add(node_id)
            self._tree.insert(parent, "end", iid=node_id,
                              text=str(node.get("name", node_id)), open=True)
            self._insert(node_id, node.get("children", []) or [], seen)

    # ── selection ────────────────────────────────────────────────────────

    def selected_id(self) -> Optional[str]:
        sel = self._tree.selection()
        return sel[0] if sel else NO_SELECTION

    def select(self, node_id: str) -> None:
        """Select a node and reveal it, opening any collapsed ancestors."""
        if not self._tree.exists(node_id):
            raise KeyError(f"no hierarchy node with id {node_id!r}")
        self._tree.see(node_id)
        self._tree.selection_set(node_id)

    def node_ids(self) -> List[str]:
        """Every id in the tree, depth-first."""
        out: List[str] = []

        def walk(parent: str) -> None:
            for child in self._tree.get_children(parent):
                out.append(child)
                walk(child)

        walk("")
        return out

    def _emit_selection(self, _event: "tk.Event") -> None:
        if self._on_select is None:
            return
        current = self.selected_id()
        if current is not None:
            self._on_select(current)
