"""Transform.apply_to_point must apply the rotation it carries.

`Transform` holds a position, a rotation quaternion and a scale, but
`apply_to_point()` used only the scale and the position: a point given a
90-degree turn about Z came back where it started.
"""

from __future__ import annotations

import math

import pytest

from eostudio.core.geometry.primitives import Vec3
from eostudio.core.geometry.transforms import Quaternion, Transform


def _close(a: Vec3, b: Vec3) -> bool:
    return all(math.isclose(p, q, abs_tol=1e-9) for p, q in ((a.x, b.x), (a.y, b.y), (a.z, b.z)))


@pytest.mark.parametrize(
    "axis, point, expected",
    [
        (Vec3(0, 0, 1), Vec3(1, 0, 0), Vec3(0, 1, 0)),
        (Vec3(0, 0, 1), Vec3(0, 1, 0), Vec3(-1, 0, 0)),
        (Vec3(0, 1, 0), Vec3(0, 0, 1), Vec3(1, 0, 0)),
        (Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1)),
    ],
)
def test_quarter_turn_rotates_the_point(axis: Vec3, point: Vec3, expected: Vec3) -> None:
    t = Transform(rotation=Quaternion.from_axis_angle(axis, math.pi / 2))

    assert _close(t.apply_to_point(point), expected)


def test_scale_then_rotate_then_translate() -> None:
    t = Transform(
        position=Vec3(10, 0, 0),
        rotation=Quaternion.from_axis_angle(Vec3(0, 0, 1), math.pi / 2),
        scale=Vec3(2, 3, 1),
    )

    # (1, 0, 0) -> scale (2, 0, 0) -> rotate (0, 2, 0) -> translate (10, 2, 0)
    assert _close(t.apply_to_point(Vec3(1, 0, 0)), Vec3(10, 2, 0))


def test_rotation_need_not_be_unit_length() -> None:
    q = Quaternion.from_axis_angle(Vec3(0, 0, 1), math.pi / 2)
    t = Transform(rotation=Quaternion(q.x * 3, q.y * 3, q.z * 3, q.w * 3))

    assert _close(t.apply_to_point(Vec3(1, 0, 0)), Vec3(0, 1, 0))


def test_identity_rotation_keeps_scale_and_translation() -> None:
    t = Transform(position=Vec3(1, 2, 3), scale=Vec3(2, 2, 2))

    assert _close(t.apply_to_point(Vec3(1, 1, 1)), Vec3(3, 4, 5))


def test_rotate_agrees_with_quaternion_product() -> None:
    a = Quaternion.from_axis_angle(Vec3(0, 0, 1), 0.7)
    b = Quaternion.from_axis_angle(Vec3(1, 2, 0.5), 1.3)
    v = Vec3(0.3, -1.2, 2.0)

    assert _close((a * b).rotate(v), a.rotate(b.rotate(v)))
