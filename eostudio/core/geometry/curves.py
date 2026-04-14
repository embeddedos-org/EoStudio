"""Curve primitives — Bézier and B-spline curves (stubs)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from eostudio.core.geometry.primitives import Vec3


@dataclass
class BezierCurve:
    control_points: List[Vec3] = field(default_factory=list)

    def evaluate(self, t: float) -> Vec3:
        """Evaluate curve at parameter *t* ∈ [0, 1] using De Casteljau."""
        pts = [Vec3(p.x, p.y, p.z) for p in self.control_points]
        n = len(pts)
        for r in range(1, n):
            for i in range(n - r):
                pts[i] = Vec3(
                    (1 - t) * pts[i].x + t * pts[i + 1].x,
                    (1 - t) * pts[i].y + t * pts[i + 1].y,
                    (1 - t) * pts[i].z + t * pts[i + 1].z,
                )
        return pts[0] if pts else Vec3()


@dataclass
class BSplineCurve:
    control_points: List[Vec3] = field(default_factory=list)
    degree: int = 3
    knots: List[float] = field(default_factory=list)

    def evaluate(self, t: float) -> Vec3:
        """Stub — returns first control point."""
        return self.control_points[0] if self.control_points else Vec3()
