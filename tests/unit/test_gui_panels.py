# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""HierarchyPanel and LayersPanel.

Both modules were empty files shipped inside the widgets package. Nothing
imported them, so nothing failed — they were simply absent capability in a
tool whose job is designing scenes.
"""

import pytest

tk = pytest.importorskip("tkinter", reason="panels need tkinter")

from eostudio.gui.widgets.hierarchy import HierarchyPanel      # noqa: E402
from eostudio.gui.widgets.layers_panel import Layer, LayersPanel  # noqa: E402


@pytest.fixture
def root():
    try:
        r = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"no display available: {exc}")
    r.withdraw()
    yield r
    r.destroy()


TREE = [
    {"id": "root", "name": "Scene", "children": [
        {"id": "a", "name": "Chassis", "children": [
            {"id": "a1", "name": "Bracket"},
        ]},
        {"id": "b", "name": "Camera"},
    ]},
]


class TestHierarchyPanel:
    def test_nested_nodes_are_all_inserted(self, root):
        p = HierarchyPanel(root)
        p.set_nodes(TREE)
        assert set(p.node_ids()) == {"root", "a", "a1", "b"}

    def test_set_nodes_replaces_rather_than_appends(self, root):
        p = HierarchyPanel(root)
        p.set_nodes(TREE)
        p.set_nodes([{"id": "only", "name": "Only"}])
        assert p.node_ids() == ["only"]

    def test_duplicate_ids_are_rejected(self, root):
        """Treeview keys items by id; a duplicate silently reparents the
        second node instead of erroring, which is worse than refusing."""
        p = HierarchyPanel(root)
        with pytest.raises(ValueError, match="duplicate"):
            p.set_nodes([{"id": "x", "name": "A"}, {"id": "x", "name": "B"}])

    def test_a_node_without_an_id_is_rejected(self, root):
        p = HierarchyPanel(root)
        with pytest.raises(ValueError, match="no 'id'"):
            p.set_nodes([{"name": "nameless"}])

    def test_nothing_selected_initially(self, root):
        p = HierarchyPanel(root)
        p.set_nodes(TREE)
        assert p.selected_id() is None

    def test_select_reports_back(self, root):
        p = HierarchyPanel(root)
        p.set_nodes(TREE)
        p.select("a1")
        assert p.selected_id() == "a1"

    def test_selecting_an_unknown_node_raises(self, root):
        p = HierarchyPanel(root)
        p.set_nodes(TREE)
        with pytest.raises(KeyError):
            p.select("nope")

    def test_selection_fires_the_callback(self, root):
        seen = []
        p = HierarchyPanel(root, on_select=seen.append)
        p.set_nodes(TREE)
        p.select("b")
        root.update()
        assert seen == ["b"]


class TestLayersPanel:
    def test_new_layers_go_on_top(self, root):
        p = LayersPanel(root)
        p.add_layer("base")
        p.add_layer("detail")
        assert [l.name for l in p.layers] == ["detail", "base"]

    def test_duplicate_names_are_rejected(self, root):
        p = LayersPanel(root)
        p.add_layer("outline")
        with pytest.raises(ValueError, match="already exists"):
            p.add_layer("outline")

    def test_set_layers_rejects_duplicates_too(self, root):
        p = LayersPanel(root)
        with pytest.raises(ValueError, match="unique"):
            p.set_layers([Layer("a"), Layer("a")])

    def test_visibility_and_lock_are_independent(self, root):
        """A locked layer is still drawn; a hidden layer can still be edited
        by a tool that addresses it directly."""
        p = LayersPanel(root)
        p.add_layer("guides")
        assert p.toggle_locked("guides") is True
        assert p.layers[0].visible is True
        assert p.toggle_visible("guides") is False
        assert p.layers[0].locked is True

    def test_visible_layers_filters(self, root):
        p = LayersPanel(root)
        p.set_layers([Layer("a"), Layer("b", visible=False), Layer("c")])
        assert [l.name for l in p.visible_layers()] == ["a", "c"]

    def test_remove_unknown_layer_raises(self, root):
        p = LayersPanel(root)
        with pytest.raises(KeyError):
            p.remove_layer("ghost")

    def test_move_clamps_instead_of_wrapping(self, root):
        """Dragging past the end should rest at the end, not reappear at the
        other side of the list."""
        p = LayersPanel(root)
        p.set_layers([Layer("a"), Layer("b"), Layer("c")])
        assert p.move("a", -5) == 0
        assert [l.name for l in p.layers] == ["a", "b", "c"]
        assert p.move("a", 99) == 2
        assert [l.name for l in p.layers] == ["b", "c", "a"]

    def test_move_reorders_by_delta(self, root):
        p = LayersPanel(root)
        p.set_layers([Layer("a"), Layer("b"), Layer("c")])
        p.move("c", -1)
        assert [l.name for l in p.layers] == ["a", "c", "b"]

    def test_layers_property_is_a_copy(self, root):
        """Handing out the live list would let a caller reorder the model
        without the view ever being refreshed."""
        p = LayersPanel(root)
        p.add_layer("a")
        p.layers.clear()
        assert len(p.layers) == 1

    def test_on_change_fires_for_every_mutation(self, root):
        calls = []
        p = LayersPanel(root, on_change=lambda ls: calls.append(len(ls)))
        p.add_layer("a")            # [a]
        p.add_layer("b")            # [b, a]
        p.toggle_visible("a")       # state change, same length
        p.move("a", -1)             # [a, b]
        p.remove_layer("b")         # [a]
        assert calls == [1, 2, 2, 2, 1]

    def test_a_move_that_changes_nothing_does_not_fire(self, root):
        """`a` is already last, so moving it down is a no-op. Firing
        on_change there would make every consumer re-render for nothing."""
        calls = []
        p = LayersPanel(root, on_change=lambda ls: calls.append(len(ls)))
        p.set_layers([Layer("b"), Layer("a")])
        before = len(calls)
        assert p.move("a", 1) == 1
        assert len(calls) == before
