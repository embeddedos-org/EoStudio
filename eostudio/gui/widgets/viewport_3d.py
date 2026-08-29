"""3D wireframe viewport with orbit, pan, and zoom.

The CAD editor imports `Viewport3D` from here; the module was empty, so
`eostudio.gui.editors.cad_editor` could not be imported at all.

Rendering is wireframe on a tk.Canvas rather than an OpenGL surface: EoStudio
already depends on tkinter and nothing else for its widgets, and a CAD model
being inspected for shape and scale reads perfectly well as edges. Filled
surfaces would need a depth buffer, which is where a canvas stops being the
right tool.
"""

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

import math
from typing import Any, Iterable, List, Optional, Sequence, Tuple

try:
    import tkinter as tk
except ImportError:
    raise ImportError("tkinter not available — install python3-tk or run in GUI mode")

Vec3 = Tuple[float, float, float]
Edge = Tuple[int, int]

#: Clip anything at or behind the eye plane. Points there have no projection,
#: and dividing by a near-zero depth throws an edge off to infinity.
_NEAR_PLANE = 1e-3

#: Elevation is clamped just inside the poles. At exactly +/-90 degrees the
#: view direction is parallel to the world up vector and the right/up basis
#: is undefined, which makes the camera flip.
_MAX_ELEVATION = math.radians(89.5)


class Viewport3D(tk.Canvas):
    """Orbiting wireframe view of a set of 3D meshes.

    Left-drag orbits, Shift-left-drag or middle-drag pans, the wheel dollies
    in and out. The camera looks at ``target`` from a spherical position; that
    parameterisation is what makes orbiting a rotation of two scalars rather
    than a matrix the caller has to maintain.
    """

    def __init__(
        self,
        master: tk.Widget,
        bg: str = "#11111b",
        width: int = 800,
        height: int = 600,
        fov_degrees: float = 50.0,
        grid: bool = True,
        axes: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, bg=bg, width=width, height=height,
                         highlightthickness=0, **kwargs)

        self._meshes: List[Tuple[List[Vec3], List[Edge], str]] = []
        self._show_grid = grid
        self._show_axes = axes

        self._fov = math.radians(fov_degrees)
        self._azimuth = math.radians(35.0)
        self._elevation = math.radians(25.0)
        self._distance = 10.0
        self._target: Vec3 = (0.0, 0.0, 0.0)

        self._drag_origin: Optional[Tuple[int, int]] = None
        self._drag_mode: Optional[str] = None

        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<ButtonPress-2>", self._on_press_pan)
        self.bind("<B2-Motion>", self._on_drag)
        self.bind("<ButtonRelease-2>", self._on_release)
        self.bind("<MouseWheel>", self._on_wheel)          # Windows / macOS
        self.bind("<Button-4>", lambda e: self._dolly(0.9))  # X11 wheel up
        self.bind("<Button-5>", lambda e: self._dolly(1.1))  # X11 wheel down
        self.bind("<Configure>", lambda e: self.render())

    # ── model ────────────────────────────────────────────────────────────

    def add_mesh(self, vertices: Sequence[Vec3], edges: Sequence[Edge],
                 color: str = "#89b4fa") -> None:
        """Add a wireframe mesh.

        Edges referencing a vertex that does not exist are rejected here
        rather than at draw time, so a malformed mesh fails where the caller
        can see which mesh it was.
        """
        verts = [tuple(float(c) for c in v) for v in vertices]
        for v in verts:
            if len(v) != 3:
                raise ValueError(f"vertex must have 3 coordinates, got {len(v)}")
        n = len(verts)
        clean: List[Edge] = []
        for a, b in edges:
            if not (0 <= a < n and 0 <= b < n):
                raise ValueError(
                    f"edge ({a}, {b}) references a vertex outside the mesh's "
                    f"{n} vertices"
                )
            clean.append((int(a), int(b)))
        self._meshes.append((verts, clean, color))  # type: ignore[arg-type]

    def set_mesh(self, vertices: Sequence[Vec3], edges: Sequence[Edge],
                 color: str = "#89b4fa") -> None:
        """Replace everything with one mesh."""
        self._meshes.clear()
        self.add_mesh(vertices, edges, color)

    def clear(self) -> None:
        self._meshes.clear()
        self.delete("all")

    @property
    def mesh_count(self) -> int:
        return len(self._meshes)

    # ── camera ───────────────────────────────────────────────────────────

    def orbit(self, d_azimuth: float, d_elevation: float) -> None:
        self._azimuth = (self._azimuth + d_azimuth) % (2.0 * math.pi)
        self._elevation = max(-_MAX_ELEVATION,
                              min(_MAX_ELEVATION, self._elevation + d_elevation))

    def dolly(self, factor: float) -> None:
        """Move the eye toward or away from the target.

        The distance is clamped above zero: at zero the eye sits on the target
        and there is no view direction left to build a basis from.
        """
        self._distance = max(_NEAR_PLANE, self._distance * float(factor))

    def pan(self, dx: float, dy: float) -> None:
        """Slide the target across the view plane, in world units."""
        right, up, _ = self._basis()
        tx, ty, tz = self._target
        self._target = (tx + right[0] * dx + up[0] * dy,
                        ty + right[1] * dx + up[1] * dy,
                        tz + right[2] * dx + up[2] * dy)

    def fit_view(self, margin: float = 1.4) -> None:
        """Frame every mesh: centre the target and back the eye off far enough.

        A viewport that opens on an empty screen because the model is two
        orders of magnitude larger or smaller than the default distance is the
        most common way a working renderer looks broken.
        """
        pts = [v for verts, _e, _c in self._meshes for v in verts]
        if not pts:
            return
        lo = [min(p[i] for p in pts) for i in range(3)]
        hi = [max(p[i] for p in pts) for i in range(3)]
        self._target = tuple((lo[i] + hi[i]) / 2.0 for i in range(3))  # type: ignore[assignment]
        radius = max(
            math.dist(self._target, p) for p in pts
        )
        if radius <= 0.0:
            # A single point, or every vertex coincident: there is no extent to
            # frame, so keep a usable distance rather than collapsing to zero.
            self._distance = 1.0
            return
        self._distance = max(_NEAR_PLANE,
                             margin * radius / math.sin(self._fov / 2.0))

    def camera_position(self) -> Vec3:
        ce = math.cos(self._elevation)
        tx, ty, tz = self._target
        return (tx + self._distance * ce * math.cos(self._azimuth),
                ty + self._distance * math.sin(self._elevation),
                tz + self._distance * ce * math.sin(self._azimuth))

    # ── projection ───────────────────────────────────────────────────────

    def _basis(self) -> Tuple[Vec3, Vec3, Vec3]:
        """Right, up and forward unit vectors for the current camera."""
        eye = self.camera_position()
        fwd = _normalise(_sub(self._target, eye))
        right = _normalise(_cross(fwd, (0.0, 1.0, 0.0)))
        up = _cross(right, fwd)
        return right, up, fwd

    def project(self, point: Vec3) -> Optional[Tuple[float, float]]:
        """Canvas coordinates for a world point, or None if it is behind the eye."""
        w = max(1, int(self.winfo_width()))
        h = max(1, int(self.winfo_height()))
        right, up, fwd = self._basis()
        rel = _sub(point, self.camera_position())

        depth = _dot(rel, fwd)
        if depth <= _NEAR_PLANE:
            return None

        scale = (h / 2.0) / math.tan(self._fov / 2.0)
        return (w / 2.0 + _dot(rel, right) * scale / depth,
                h / 2.0 - _dot(rel, up) * scale / depth)

    # ── rendering ────────────────────────────────────────────────────────

    def render(self) -> None:
        self.delete("all")
        if self._show_grid:
            self._draw_grid()
        if self._show_axes:
            self._draw_axes()
        for verts, edges, color in self._meshes:
            for a, b in edges:
                pa = self.project(verts[a])
                pb = self.project(verts[b])
                # Both ends must be in front of the eye. Drawing an edge with
                # one end clipped would need the intersection with the near
                # plane; dropping it is honest and cheap.
                if pa is None or pb is None:
                    continue
                self.create_line(pa[0], pa[1], pb[0], pb[1], fill=color, width=1)

    def _draw_grid(self, half: int = 5, step: float = 1.0,
                   color: str = "#313244") -> None:
        extent = half * step
        for i in range(-half, half + 1):
            d = i * step
            for a, b in (((-extent, 0.0, d), (extent, 0.0, d)),
                         ((d, 0.0, -extent), (d, 0.0, extent))):
                pa, pb = self.project(a), self.project(b)
                if pa and pb:
                    self.create_line(pa[0], pa[1], pb[0], pb[1], fill=color)

    def _draw_axes(self, length: float = 1.0) -> None:
        origin = self.project((0.0, 0.0, 0.0))
        if origin is None:
            return
        for vec, color in (((length, 0.0, 0.0), "#f38ba8"),
                           ((0.0, length, 0.0), "#a6e3a1"),
                           ((0.0, 0.0, length), "#89b4fa")):
            tip = self.project(vec)
            if tip:
                self.create_line(origin[0], origin[1], tip[0], tip[1],
                                 fill=color, width=2)

    # ── interaction ──────────────────────────────────────────────────────

    def _on_press(self, event: "tk.Event") -> None:
        self._drag_origin = (event.x, event.y)
        # Shift turns the primary drag into a pan, which is the convention in
        # every CAD tool a user is likely to arrive from.
        self._drag_mode = "pan" if (event.state & 0x0001) else "orbit"

    def _on_press_pan(self, event: "tk.Event") -> None:
        self._drag_origin = (event.x, event.y)
        self._drag_mode = "pan"

    def _on_release(self, _event: "tk.Event") -> None:
        self._drag_origin = None
        self._drag_mode = None

    def _on_drag(self, event: "tk.Event") -> None:
        if self._drag_origin is None:
            return
        dx = event.x - self._drag_origin[0]
        dy = event.y - self._drag_origin[1]
        self._drag_origin = (event.x, event.y)

        if self._drag_mode == "pan":
            # Scale by distance so a drag moves the model by the same amount
            # on screen whether the camera is close in or far out.
            k = self._distance / max(1, int(self.winfo_height()))
            self.pan(-dx * k, dy * k)
        else:
            self.orbit(dx * 0.01, -dy * 0.01)
        self.render()

    def _on_wheel(self, event: "tk.Event") -> None:
        self._dolly(0.9 if event.delta > 0 else 1.1)

    def _dolly(self, factor: float) -> None:
        self.dolly(factor)
        self.render()


# ── vector helpers ───────────────────────────────────────────────────────

def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _normalise(v: Vec3) -> Vec3:
    n = math.sqrt(_dot(v, v))
    if n == 0.0:
        # Only reachable if the eye coincides with the target, which dolly()
        # and fit_view() both clamp against; returning a fixed axis keeps the
        # basis well-formed rather than propagating a NaN through every point.
        return (0.0, 0.0, 1.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def unit_cube() -> Tuple[List[Vec3], List[Edge]]:
    """A 1x1x1 wireframe cube centred on the origin — handy as a placeholder."""
    verts: List[Vec3] = [(x, y, z)
                         for x in (-0.5, 0.5)
                         for y in (-0.5, 0.5)
                         for z in (-0.5, 0.5)]
    edges: List[Edge] = [(i, j)
                         for i in range(8) for j in range(i + 1, 8)
                         if sum(1 for k in range(3)
                                if verts[i][k] != verts[j][k]) == 1]
    return verts, edges
