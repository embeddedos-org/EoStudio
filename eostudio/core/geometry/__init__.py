"""Geometry subpackage — vectors, matrices, meshes, transforms, curves."""

from eostudio.core.geometry.primitives import (
    Vec2, Vec3, Vec4, Matrix4, BoundingBox, Face, Mesh,
    create_cube, create_sphere, create_cylinder, create_cone, create_torus, create_plane,
)
from eostudio.core.geometry.transforms import Quaternion, Transform
from eostudio.core.geometry.curves import BezierCurve, BSplineCurve

__all__ = [
    "Vec2", "Vec3", "Vec4", "Matrix4", "BoundingBox", "Face", "Mesh",
    "create_cube", "create_sphere", "create_cylinder", "create_cone", "create_torus", "create_plane",
    "Quaternion", "Transform", "BezierCurve", "BSplineCurve",
]
