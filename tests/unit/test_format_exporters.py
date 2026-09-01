# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Format exporters, and the dispatcher that reaches them.

`EoStudioProject.export()` imports five names at the top of the method, before
it dispatches on the format:

    from eostudio.formats.obj import export_obj       # did not exist
    from eostudio.formats.svg import export_svg       # did not exist
    from eostudio.formats.gltf import export_gltf     # empty module

Because the imports run first, **every** format raised ImportError — obj, stl
and dxf included, whose exporters were fine. glTF is also the CLI's default
`--format`, so the default export path was the broken one. The three broken
lines each carried a `# type: ignore[attr-defined]`, which is what kept a type
checker quiet about exactly the attributes that were missing.
"""

import base64
import json
import struct

import pytest

from eostudio.core.geometry.primitives import Mesh, Vec3, Face, create_cube
from eostudio.formats.gltf import GLTFExporter, export_gltf
from eostudio.formats.project import EoStudioProject


@pytest.fixture
def cube():
    return create_cube(2.0)


class TestExportDispatcher:
    """The regression that matters: every format reachable, not just glTF."""

    @pytest.mark.parametrize("fmt,kwargs", [
        ("obj", "mesh"),
        ("stl", "mesh"),
        ("stl_binary", "mesh"),
        ("gltf", "mesh"),
        ("svg", "shapes"),
        ("dxf", "entities"),
    ])
    def test_every_documented_format_exports(self, tmp_path, cube, fmt, kwargs):
        payload = {"mesh": cube} if kwargs == "mesh" else {kwargs: []}
        out = tmp_path / f"out.{fmt}"
        EoStudioProject().export(fmt, str(out), **payload)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_an_unknown_format_is_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="Unsupported export format"):
            EoStudioProject().export("parquet", str(tmp_path / "x"))

    def test_mesh_formats_say_what_they_need(self, tmp_path):
        with pytest.raises(ValueError, match="requires a 'mesh'"):
            EoStudioProject().export("gltf", str(tmp_path / "x.gltf"))


class TestGltfDocument:
    def test_it_is_valid_json_with_a_2_0_asset(self, tmp_path, cube):
        out = tmp_path / "c.gltf"
        export_gltf(cube, str(out))
        doc = json.loads(out.read_text())
        assert doc["asset"]["version"] == "2.0"
        assert doc["scenes"][0]["nodes"] == [0]
        assert doc["meshes"][0]["primitives"][0]["mode"] == 4   # TRIANGLES

    def test_position_carries_min_and_max(self, cube):
        """The spec requires them on POSITION; viewers frame the model from
        these rather than walking every vertex."""
        acc = GLTFExporter().export_dict(cube)["accessors"][0]
        assert acc["min"] == [-1.0, -1.0, -1.0]
        assert acc["max"] == [1.0, 1.0, 1.0]

    def test_the_buffer_is_self_contained(self, cube):
        """A .gltf with an external .bin does not survive being emailed."""
        uri = GLTFExporter().export_dict(cube)["buffers"][0]["uri"]
        assert uri.startswith("data:application/octet-stream;base64,")

    def test_declared_buffer_length_matches_the_payload(self, cube):
        doc = GLTFExporter().export_dict(cube)
        blob = base64.b64decode(doc["buffers"][0]["uri"].split(",", 1)[1])
        assert len(blob) == doc["buffers"][0]["byteLength"]

    def test_positions_round_trip_through_the_buffer(self, cube):
        doc = GLTFExporter().export_dict(cube)
        blob = base64.b64decode(doc["buffers"][0]["uri"].split(",", 1)[1])
        acc = doc["accessors"][0]
        bv = doc["bufferViews"][acc["bufferView"]]
        raw = blob[bv["byteOffset"]:bv["byteOffset"] + bv["byteLength"]]
        got = [struct.unpack_from("<3f", raw, i * 12) for i in range(acc["count"])]
        assert got == [(v.x, v.y, v.z) for v in cube.vertices]

    def test_indices_round_trip_through_the_buffer(self, cube):
        doc = GLTFExporter().export_dict(cube)
        blob = base64.b64decode(doc["buffers"][0]["uri"].split(",", 1)[1])
        acc = doc["accessors"][1]
        bv = doc["bufferViews"][acc["bufferView"]]
        raw = blob[bv["byteOffset"]:bv["byteOffset"] + bv["byteLength"]]
        got = list(struct.unpack_from("<%dI" % acc["count"], raw, 0))
        assert got == [i for f in cube.faces for i in (f.v0, f.v1, f.v2)]

    def test_buffer_views_are_four_byte_aligned(self, cube):
        """A viewer is entitled to reject a misaligned accessor, and a cube's
        position block happens to land on a multiple of 4 by luck — an odd
        vertex count is what exposes missing padding."""
        odd = Mesh(name="odd",
                   vertices=[Vec3(0, 0, 0), Vec3(1, 0, 0), Vec3(0, 1, 0),
                             Vec3(1, 1, 0), Vec3(0, 0, 1)],
                   faces=[Face(0, 1, 2), Face(1, 3, 2), Face(0, 2, 4)])
        doc = GLTFExporter().export_dict(odd)
        for bv in doc["bufferViews"]:
            assert bv["byteOffset"] % 4 == 0

    def test_normals_are_exported_when_present(self, cube):
        cube.compute_normals()
        doc = GLTFExporter().export_dict(cube)
        assert "NORMAL" in doc["meshes"][0]["primitives"][0]["attributes"]

    def test_no_normal_attribute_when_the_mesh_has_none(self):
        flat = Mesh(name="t", vertices=[Vec3(0, 0, 0), Vec3(1, 0, 0), Vec3(0, 1, 0)],
                    faces=[Face(0, 1, 2)])
        doc = GLTFExporter().export_dict(flat)
        assert "NORMAL" not in doc["meshes"][0]["primitives"][0]["attributes"]

    def test_the_node_takes_the_mesh_name(self, cube):
        cube.name = "bracket"
        assert GLTFExporter().export_dict(cube)["nodes"][0]["name"] == "bracket"


class TestGltfRejectsBadInput:
    def test_a_face_pointing_outside_the_mesh_is_rejected(self):
        """Writing it would produce a file that crashes the viewer instead of
        this process, which is a worse place to find out."""
        bad = Mesh(name="bad", vertices=[Vec3(0, 0, 0), Vec3(1, 0, 0)],
                   faces=[Face(0, 1, 9)])
        with pytest.raises(ValueError, match="outside the mesh"):
            GLTFExporter().export_dict(bad)

    def test_a_mesh_with_no_vertices_is_rejected(self):
        with pytest.raises(ValueError, match="no vertices"):
            GLTFExporter().export_dict(Mesh(name="empty"))

    def test_a_mesh_with_no_faces_is_rejected(self):
        with pytest.raises(ValueError, match="no faces"):
            GLTFExporter().export_dict(
                Mesh(name="points", vertices=[Vec3(0, 0, 0)]))


class TestFunctionFormsExist:
    """project.py imports the function form of each exporter. stl and dxf
    already had one; obj, svg and gltf did not."""

    @pytest.mark.parametrize("module,func", [
        ("eostudio.formats.obj", "export_obj"),
        ("eostudio.formats.svg", "export_svg"),
        ("eostudio.formats.gltf", "export_gltf"),
        ("eostudio.formats.stl", "export_stl_ascii"),
        ("eostudio.formats.stl", "export_stl_binary"),
        ("eostudio.formats.dxf", "export_dxf"),
    ])
    def test_function_is_importable(self, module, func):
        import importlib
        assert callable(getattr(importlib.import_module(module), func))

    def test_export_obj_writes_wavefront(self, tmp_path, cube):
        from eostudio.formats.obj import export_obj
        out = tmp_path / "c.obj"
        export_obj(cube, str(out))
        body = out.read_text()
        assert body.count("\nv ") == len(cube.vertices)
        assert body.count("\nf ") == len(cube.faces)

    def test_export_svg_writes_an_svg_root(self, tmp_path):
        from eostudio.formats.svg import export_svg
        out = tmp_path / "s.svg"
        export_svg([{"type": "rect", "x": 1, "y": 2}], str(out), width=64, height=32)
        body = out.read_text()
        assert body.startswith("<svg")
        assert 'width="64"' in body
