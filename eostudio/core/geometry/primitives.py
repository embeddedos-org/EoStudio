"""Geometry primitives — vectors, matrices, bounding boxes, meshes, and factory functions."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Vec2:
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vec2:
        return Vec2(self.x * scalar, self.y * scalar)

    def dot(self, other: Vec2) -> float:
        return self.x * other.x + self.y * other.y

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def normalized(self) -> Vec2:
        ln = self.length()
        if ln == 0:
            return Vec2()
        return Vec2(self.x / ln, self.y / ln)


@dataclass
class Vec3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: Vec3) -> Vec3:
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vec3) -> Vec3:
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vec3:
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def dot(self, other: Vec3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vec3) -> Vec3:
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalized(self) -> Vec3:
        ln = self.length()
        if ln == 0:
            return Vec3()
        return Vec3(self.x / ln, self.y / ln, self.z / ln)


@dataclass
class Vec4:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 1.0


class Matrix4:
    def __init__(self, data: Optional[List[List[float]]] = None) -> None:
        if data is not None:
            self.data = data
        else:
            self.data = [[0.0] * 4 for _ in range(4)]

    @classmethod
    def identity(cls) -> Matrix4:
        m = cls()
        for i in range(4):
            m.data[i][i] = 1.0
        return m

    @classmethod
    def translation(cls, tx: float, ty: float, tz: float) -> Matrix4:
        m = cls.identity()
        m.data[0][3] = tx
        m.data[1][3] = ty
        m.data[2][3] = tz
        return m

    @classmethod
    def scaling(cls, sx: float, sy: float, sz: float) -> Matrix4:
        m = cls()
        m.data[0][0] = sx
        m.data[1][1] = sy
        m.data[2][2] = sz
        m.data[3][3] = 1.0
        return m

    def __mul__(self, other: Matrix4) -> Matrix4:
        result = Matrix4()
        for i in range(4):
            for j in range(4):
                s = 0.0
                for k in range(4):
                    s += self.data[i][k] * other.data[k][j]
                result.data[i][j] = s
        return result


@dataclass
class BoundingBox:
    min_point: Vec3
    max_point: Vec3

    def contains(self, point: Vec3) -> bool:
        return (
            self.min_point.x <= point.x <= self.max_point.x
            and self.min_point.y <= point.y <= self.max_point.y
            and self.min_point.z <= point.z <= self.max_point.z
        )

    def size(self) -> Vec3:
        return self.max_point - self.min_point

    def center(self) -> Vec3:
        return Vec3(
            (self.min_point.x + self.max_point.x) / 2.0,
            (self.min_point.y + self.max_point.y) / 2.0,
            (self.min_point.z + self.max_point.z) / 2.0,
        )


@dataclass
class Face:
    v0: int
    v1: int
    v2: int


@dataclass
class Mesh:
    name: str = ""
    vertices: List[Vec3] = field(default_factory=list)
    faces: List[Face] = field(default_factory=list)
    normals: List[Vec3] = field(default_factory=list)

    def compute_normals(self) -> None:
        """Compute vertex normals by averaging face normals."""
        self.normals = [Vec3(0, 0, 0) for _ in range(len(self.vertices))]
        for face in self.faces:
            if face.v0 >= len(self.vertices) or face.v1 >= len(self.vertices) or face.v2 >= len(self.vertices):
                continue
            v0 = self.vertices[face.v0]
            v1 = self.vertices[face.v1]
            v2 = self.vertices[face.v2]
            edge1 = v1 - v0
            edge2 = v2 - v0
            n = edge1.cross(edge2).normalized()
            self.normals[face.v0] += n
            self.normals[face.v1] += n
            self.normals[face.v2] += n
        self.normals = [n.normalized() for n in self.normals]


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------

def create_cube(size: float = 1.0) -> Mesh:
    h = size / 2.0
    vertices = [
        Vec3(-h, -h, -h), Vec3(h, -h, -h), Vec3(h, h, -h), Vec3(-h, h, -h),
        Vec3(-h, -h, h), Vec3(h, -h, h), Vec3(h, h, h), Vec3(-h, h, h),
    ]
    faces = [
        Face(0, 1, 2), Face(0, 2, 3),
        Face(4, 6, 5), Face(4, 7, 6),
        Face(0, 4, 5), Face(0, 5, 1),
        Face(2, 6, 7), Face(2, 7, 3),
        Face(0, 3, 7), Face(0, 7, 4),
        Face(1, 5, 6), Face(1, 6, 2),
    ]
    return Mesh(name="Cube", vertices=vertices, faces=faces)


def create_sphere(radius: float = 1.0, segments: int = 16, rings: int = 12) -> Mesh:
    vertices: List[Vec3] = []
    faces: List[Face] = []
    for i in range(rings + 1):
        phi = math.pi * i / rings
        for j in range(segments):
            theta = 2.0 * math.pi * j / segments
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.cos(phi)
            z = radius * math.sin(phi) * math.sin(theta)
            vertices.append(Vec3(x, y, z))
    for i in range(rings):
        for j in range(segments):
            a = i * segments + j
            b = i * segments + (j + 1) % segments
            c = (i + 1) * segments + (j + 1) % segments
            d = (i + 1) * segments + j
            faces.append(Face(a, b, c))
            faces.append(Face(a, c, d))
    return Mesh(name="Sphere", vertices=vertices, faces=faces)


def create_cylinder(radius: float = 1.0, height: float = 2.0, segments: int = 16) -> Mesh:
    vertices: List[Vec3] = []
    faces: List[Face] = []
    h2 = height / 2.0
    for i in range(segments):
        theta = 2.0 * math.pi * i / segments
        x = radius * math.cos(theta)
        z = radius * math.sin(theta)
        vertices.append(Vec3(x, -h2, z))
        vertices.append(Vec3(x, h2, z))
    for i in range(segments):
        a = i * 2
        b = i * 2 + 1
        c = ((i + 1) % segments) * 2 + 1
        d = ((i + 1) % segments) * 2
        faces.append(Face(a, d, c))
        faces.append(Face(a, c, b))
    return Mesh(name="Cylinder", vertices=vertices, faces=faces)


def create_cone(radius: float = 1.0, height: float = 2.0, segments: int = 16) -> Mesh:
    vertices: List[Vec3] = []
    faces: List[Face] = []
    h2 = height / 2.0
    tip_idx = 0
    vertices.append(Vec3(0, h2, 0))
    for i in range(segments):
        theta = 2.0 * math.pi * i / segments
        vertices.append(Vec3(radius * math.cos(theta), -h2, radius * math.sin(theta)))
    for i in range(segments):
        a = 1 + i
        b = 1 + (i + 1) % segments
        faces.append(Face(tip_idx, a, b))
    return Mesh(name="Cone", vertices=vertices, faces=faces)


def create_torus(major_radius: float = 2.0, minor_radius: float = 0.5,
                 major_segments: int = 24, minor_segments: int = 12) -> Mesh:
    vertices: List[Vec3] = []
    faces: List[Face] = []
    for i in range(major_segments):
        theta = 2.0 * math.pi * i / major_segments
        for j in range(minor_segments):
            phi = 2.0 * math.pi * j / minor_segments
            x = (major_radius + minor_radius * math.cos(phi)) * math.cos(theta)
            y = minor_radius * math.sin(phi)
            z = (major_radius + minor_radius * math.cos(phi)) * math.sin(theta)
            vertices.append(Vec3(x, y, z))
    for i in range(major_segments):
        for j in range(minor_segments):
            a = i * minor_segments + j
            b = i * minor_segments + (j + 1) % minor_segments
            c = ((i + 1) % major_segments) * minor_segments + (j + 1) % minor_segments
            d = ((i + 1) % major_segments) * minor_segments + j
            faces.append(Face(a, b, c))
            faces.append(Face(a, c, d))
    return Mesh(name="Torus", vertices=vertices, faces=faces)


def create_plane(width: float = 1.0, height: float = 1.0) -> Mesh:
    hw, hh = width / 2.0, height / 2.0
    vertices = [
        Vec3(-hw, 0, -hh), Vec3(hw, 0, -hh),
        Vec3(hw, 0, hh), Vec3(-hw, 0, hh),
    ]
    faces = [Face(0, 1, 2), Face(0, 2, 3)]
    return Mesh(name="Plane", vertices=vertices, faces=faces)
