"""Geometric transforms — quaternions and transform nodes."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from eostudio.core.geometry.primitives import Vec3


@dataclass
class Quaternion:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 1.0

    def length(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2 + self.w ** 2)

    def normalized(self) -> Quaternion:
        ln = self.length()
        if ln == 0:
            return Quaternion()
        return Quaternion(self.x / ln, self.y / ln, self.z / ln, self.w / ln)

    @classmethod
    def from_axis_angle(cls, axis: Vec3, angle: float) -> Quaternion:
        a = axis.normalized()
        half = angle / 2.0
        s = math.sin(half)
        return cls(a.x * s, a.y * s, a.z * s, math.cos(half))

    def __mul__(self, other: Quaternion) -> Quaternion:
        return Quaternion(
            self.w * other.x + self.x * other.w + self.y * other.z - self.z * other.y,
            self.w * other.y - self.x * other.z + self.y * other.w + self.z * other.x,
            self.w * other.z + self.x * other.y - self.y * other.x + self.z * other.w,
            self.w * other.w - self.x * other.x - self.y * other.y - self.z * other.z,
        )


@dataclass
class Transform:
    position: Vec3 = field(default_factory=Vec3)
    rotation: Quaternion = field(default_factory=Quaternion)
    scale: Vec3 = field(default_factory=lambda: Vec3(1.0, 1.0, 1.0))

    def apply_to_point(self, point: Vec3) -> Vec3:
        scaled = Vec3(point.x * self.scale.x, point.y * self.scale.y, point.z * self.scale.z)
        return scaled + self.position
