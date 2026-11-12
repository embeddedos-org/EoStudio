"""Tests for STL import format detection.

A binary STL's 80-byte header is free text, and many exporters start it with
"solid". import_stl() tells the two formats apart by comparing the file size
with the size a binary file of that triangle count would have, but it read
only the 80-byte header, so the triangle count at bytes 80-84 always came out
as 0. Every binary STL whose header began with "solid" was then handed to the
ASCII parser and failed with UnicodeDecodeError.
"""

from __future__ import annotations

import struct
from pathlib import Path

from eostudio.core.geometry.primitives import create_cube
from eostudio.formats.stl import export_stl_binary, import_stl

TRIANGLES = [
    # normal, v0, v1, v2
    ((0.0, 0.0, 1.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    ((0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)),
]


def _write_binary_stl(path: Path, header: bytes) -> None:
    with open(path, "wb") as fh:
        fh.write(header[:80].ljust(80, b" "))
        fh.write(struct.pack("<I", len(TRIANGLES)))
        for normal, v0, v1, v2 in TRIANGLES:
            fh.write(struct.pack("<12f", *normal, *v0, *v1, *v2))
            fh.write(struct.pack("<H", 0))


def _coords(mesh) -> list:
    return [(v.x, v.y, v.z) for v in mesh.vertices]


def test_binary_stl_with_solid_header_is_read_as_binary(tmp_path: Path) -> None:
    path = tmp_path / "part.stl"
    _write_binary_stl(path, b"solid part exported by a CAD tool")

    mesh = import_stl(str(path))

    assert len(mesh.faces) == 2
    assert _coords(mesh) == [v for _n, *vs in TRIANGLES for v in vs]


def test_binary_stl_with_bare_solid_header(tmp_path: Path) -> None:
    path = tmp_path / "bare.stl"
    _write_binary_stl(path, b"solid")

    assert len(import_stl(str(path)).faces) == 2


def test_ascii_stl_is_still_read_as_ascii(tmp_path: Path) -> None:
    path = tmp_path / "ascii.stl"
    lines = ["solid tri"]
    for normal, *verts in TRIANGLES:
        lines.append("  facet normal {} {} {}".format(*normal))
        lines.append("    outer loop")
        for v in verts:
            lines.append("      vertex {} {} {}".format(*v))
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append("endsolid tri")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    mesh = import_stl(str(path))

    assert len(mesh.faces) == 2
    assert _coords(mesh) == [v for _n, *vs in TRIANGLES for v in vs]


def test_own_binary_export_round_trips(tmp_path: Path) -> None:
    cube = create_cube()
    path = tmp_path / "cube.stl"
    export_stl_binary(cube, str(path))

    assert len(import_stl(str(path)).faces) == len(cube.faces)
