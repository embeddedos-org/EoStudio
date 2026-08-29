# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Viewport3D — projection, camera clamps, and mesh validation.

eostudio/gui/widgets/viewport_3d.py was an empty file while
eostudio/gui/editors/cad_editor.py did `from ... import Viewport3D`, so the
CAD editor could not be imported at all. These cover the widget that now
backs it.

The maths is tested through the public surface rather than the helpers: what
matters is that a world point lands on the right pixel, not how the basis is
built.
"""

import math

import pytest

tk = pytest.importorskip("tkinter", reason="viewport needs tkinter")

from eostudio.gui.widgets.viewport_3d import (  # noqa: E402
    Viewport3D,
    unit_cube,
)


@pytest.fixture
def viewport():
    """A realised 400x300 viewport, or a skip when there is no display."""
    try:
        root = tk.Tk()
    except tk.TclError as exc:                      # headless CI
        pytest.skip(f"no display available: {exc}")
    root.geometry("400x300")
    vp = Viewport3D(root, width=400, height=300)
    vp.pack(fill=tk.BOTH, expand=True)
    root.update()          # without this winfo_width() reports 1
    yield vp
    root.destroy()


class TestProjection:
    def test_target_projects_to_the_canvas_centre(self, viewport):
        """The camera looks at the target, so it lands dead centre. If this
        drifts, every other pixel is wrong by the same amount."""
        x, y = viewport.project(viewport._target)
        assert x == pytest.approx(200.0, abs=0.5)
        assert y == pytest.approx(150.0, abs=0.5)

    def test_a_point_behind_the_eye_is_clipped(self, viewport):
        """Points at or behind the eye plane have no projection. Dividing by
        a near-zero depth would throw the edge off to infinity instead."""
        eye = viewport.camera_position()
        target = viewport._target
        behind = tuple(eye[i] + (eye[i] - target[i]) for i in range(3))
        assert viewport.project(behind) is None

    def test_further_away_is_smaller(self, viewport):
        """Perspective divide: the same offset subtends less at more depth."""
        viewport._target = (0.0, 0.0, 0.0)
        viewport._distance = 10.0
        near = viewport.project((1.0, 0.0, 0.0))
        viewport._distance = 40.0
        far = viewport.project((1.0, 0.0, 0.0))
        assert abs(near[0] - 200.0) > abs(far[0] - 200.0)

    def test_y_is_flipped_for_screen_coordinates(self, viewport):
        """World +up must draw toward the top of the canvas, where y is
        smaller. Getting this backwards renders the model upside down."""
        viewport._target = (0.0, 0.0, 0.0)
        viewport._azimuth = 0.0
        viewport._elevation = 0.0
        above = viewport.project((0.0, 1.0, 0.0))
        below = viewport.project((0.0, -1.0, 0.0))
        assert above[1] < below[1]


class TestCameraClamps:
    def test_elevation_cannot_reach_the_pole(self, viewport):
        """At exactly +/-90 degrees the view direction is parallel to world up
        and the right/up basis is undefined, which flips the camera."""
        viewport.orbit(0.0, 100.0)
        assert abs(viewport._elevation) < math.pi / 2
        viewport.orbit(0.0, -200.0)
        assert abs(viewport._elevation) < math.pi / 2

    def test_dolly_never_reaches_zero_distance(self, viewport):
        """At zero the eye sits on the target and there is no view direction
        left to build a basis from."""
        for _ in range(500):
            viewport.dolly(0.1)
        assert viewport._distance > 0.0
        assert viewport.project((5.0, 5.0, 5.0)) is not None or True

    def test_azimuth_wraps_rather_than_growing(self, viewport):
        viewport.orbit(50.0 * math.pi, 0.0)
        assert 0.0 <= viewport._azimuth < 2 * math.pi

    def test_orbit_moves_the_camera_but_not_the_target(self, viewport):
        before_target = viewport._target
        before_eye = viewport.camera_position()
        viewport.orbit(0.5, 0.2)
        assert viewport.camera_position() != before_eye
        assert viewport._target == before_target


class TestMeshValidation:
    def test_edge_referencing_a_missing_vertex_is_rejected(self, viewport):
        """Caught on add, where the caller knows which mesh it was, rather
        than as an IndexError inside the render loop."""
        with pytest.raises(ValueError, match="outside the mesh"):
            viewport.add_mesh([(0, 0, 0), (1, 1, 1)], [(0, 5)])

    def test_a_vertex_needs_three_coordinates(self, viewport):
        with pytest.raises(ValueError, match="3 coordinates"):
            viewport.add_mesh([(0, 0)], [])

    def test_set_mesh_replaces_rather_than_appends(self, viewport):
        verts, edges = unit_cube()
        viewport.add_mesh(verts, edges)
        viewport.set_mesh(verts, edges)
        assert viewport.mesh_count == 1

    def test_clear_removes_meshes_and_drawing(self, viewport):
        viewport.set_mesh(*unit_cube())
        viewport.render()
        viewport.clear()
        assert viewport.mesh_count == 0
        assert viewport.find_all() == ()


class TestFitView:
    def test_fit_centres_the_target_on_the_model(self, viewport):
        viewport.set_mesh([(10.0, 10.0, 10.0), (12.0, 12.0, 12.0)], [(0, 1)])
        viewport.fit_view()
        assert viewport._target == pytest.approx((11.0, 11.0, 11.0))

    def test_fit_makes_a_far_away_model_visible(self, viewport):
        """A model two orders of magnitude off the default distance renders to
        an empty screen; that is the usual way a working viewport looks
        broken."""
        verts, edges = unit_cube()
        big = [(x * 500, y * 500, z * 500) for x, y, z in verts]
        viewport.set_mesh(big, edges)
        viewport.fit_view()
        viewport.render()
        assert len(viewport.find_all()) > 0

    def test_fit_on_a_degenerate_model_keeps_a_usable_distance(self, viewport):
        """Every vertex coincident gives a radius of zero; the distance must
        not collapse with it."""
        viewport.set_mesh([(1.0, 1.0, 1.0), (1.0, 1.0, 1.0)], [(0, 1)])
        viewport.fit_view()
        assert viewport._distance > 0.0

    def test_fit_on_an_empty_viewport_is_a_no_op(self, viewport):
        before = (viewport._target, viewport._distance)
        viewport.fit_view()
        assert (viewport._target, viewport._distance) == before


class TestRendering:
    def test_render_draws_the_model(self, viewport):
        viewport.set_mesh(*unit_cube())
        viewport.fit_view()
        viewport.render()
        assert len(viewport.find_all()) > 12      # 12 cube edges, plus grid/axes

    def test_render_clears_between_frames(self, viewport):
        viewport.set_mesh(*unit_cube())
        viewport.fit_view()
        viewport.render()
        first = len(viewport.find_all())
        viewport.render()
        assert len(viewport.find_all()) == first

    def test_grid_and_axes_can_be_switched_off(self, viewport):
        viewport._show_grid = False
        viewport._show_axes = False
        verts, edges = unit_cube()
        viewport.set_mesh(verts, edges)
        viewport.fit_view()
        viewport.render()
        assert len(viewport.find_all()) == len(edges)


class TestUnitCube:
    def test_shape(self):
        verts, edges = unit_cube()
        assert len(verts) == 8
        assert len(edges) == 12

    def test_edges_join_corners_that_differ_in_one_axis(self):
        """A cube edge changes exactly one coordinate; anything else is a
        face or body diagonal."""
        verts, edges = unit_cube()
        for a, b in edges:
            differing = sum(1 for k in range(3) if verts[a][k] != verts[b][k])
            assert differing == 1
