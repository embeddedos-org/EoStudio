"""glTF 2.0 exporter for EoStudio meshes.

This module was an empty file while `eostudio/formats/project.py` imported
`export_gltf` from it at the top of `EoStudioProject.export()`. Because that
import runs before the format is dispatched on, **every** export — obj, stl,
svg, dxf included — raised ImportError. glTF is also the CLI's default
`--format`, so the default export path was the broken one.

The output is a self-contained `.gltf`: JSON with the binary buffer inlined as
a base64 data URI. A single file survives being emailed, attached to an issue
or dropped into a viewer, which is what an exporter's output is usually for.
`.glb` would be smaller; it is not what callers of this function ask for.
"""

from __future__ import annotations

import base64
import json
import os
import struct
from typing import Any, Dict, List

from eostudio.core.geometry.primitives import Mesh

#: glTF component and target constants, from the 2.0 specification.
_FLOAT = 5126
_UNSIGNED_INT = 5125
_ARRAY_BUFFER = 34962
_ELEMENT_ARRAY_BUFFER = 34963
_TRIANGLES = 4

#: Buffer views must start on a multiple of the component size.
_ALIGNMENT = 4


class GLTFExporter:
    """Export a :class:`Mesh` to glTF 2.0.

    Kept as a class for symmetry with :class:`~eostudio.formats.obj.OBJExporter`
    and :class:`~eostudio.formats.svg.SVGExporter`; `export_gltf` below is the
    function form the project exporter calls.
    """

    def export(self, mesh: Mesh, name: str | None = None) -> str:
        """Return the mesh as a glTF 2.0 JSON document."""
        return json.dumps(self.export_dict(mesh, name), indent=2)

    def export_dict(self, mesh: Mesh, name: str | None = None) -> Dict[str, Any]:
        """Return the glTF document as a dict, before serialisation."""
        if not mesh.vertices:
            raise ValueError("cannot export a mesh with no vertices to glTF")
        if not mesh.faces:
            raise ValueError("cannot export a mesh with no faces to glTF")

        n_verts = len(mesh.vertices)
        for f in mesh.faces:
            for idx in (f.v0, f.v1, f.v2):
                if not 0 <= idx < n_verts:
                    raise ValueError(
                        f"face references vertex {idx}, outside the mesh's "
                        f"{n_verts} vertices"
                    )

        positions = bytearray()
        for v in mesh.vertices:
            positions += struct.pack("<3f", float(v.x), float(v.y), float(v.z))

        indices = bytearray()
        for f in mesh.faces:
            indices += struct.pack("<3I", int(f.v0), int(f.v1), int(f.v2))

        # Pad so the index view starts on an aligned offset. A viewer reading
        # a misaligned accessor is entitled to reject the file.
        pad = (-len(positions)) % _ALIGNMENT
        index_offset = len(positions) + pad
        blob = bytes(positions) + b"\x00" * pad + bytes(indices)

        accessors: List[Dict[str, Any]] = [
            {
                "bufferView": 0,
                "componentType": _FLOAT,
                "count": n_verts,
                "type": "VEC3",
                # min/max on POSITION is required by the spec — viewers use it
                # to frame the model without walking every vertex.
                "min": [min(float(v.x) for v in mesh.vertices),
                        min(float(v.y) for v in mesh.vertices),
                        min(float(v.z) for v in mesh.vertices)],
                "max": [max(float(v.x) for v in mesh.vertices),
                        max(float(v.y) for v in mesh.vertices),
                        max(float(v.z) for v in mesh.vertices)],
            },
            {
                "bufferView": 1,
                "componentType": _UNSIGNED_INT,
                "count": len(mesh.faces) * 3,
                "type": "SCALAR",
            },
        ]

        attributes: Dict[str, int] = {"POSITION": 0}
        buffer_views: List[Dict[str, Any]] = [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(positions),
             "target": _ARRAY_BUFFER},
            {"buffer": 0, "byteOffset": index_offset, "byteLength": len(indices),
             "target": _ELEMENT_ARRAY_BUFFER},
        ]

        if mesh.normals and len(mesh.normals) == n_verts:
            normals = bytearray()
            for nv in mesh.normals:
                normals += struct.pack("<3f", float(nv.x), float(nv.y), float(nv.z))
            normal_offset = len(blob) + ((-len(blob)) % _ALIGNMENT)
            blob = blob + b"\x00" * (normal_offset - len(blob)) + bytes(normals)
            buffer_views.append({"buffer": 0, "byteOffset": normal_offset,
                                 "byteLength": len(normals),
                                 "target": _ARRAY_BUFFER})
            accessors.append({"bufferView": 2, "componentType": _FLOAT,
                              "count": n_verts, "type": "VEC3"})
            attributes["NORMAL"] = 2

        mesh_name = name or mesh.name or "mesh"
        return {
            "asset": {"version": "2.0", "generator": "EoStudio glTF exporter"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0, "name": mesh_name}],
            "meshes": [{
                "name": mesh_name,
                "primitives": [{
                    "attributes": attributes,
                    "indices": 1,
                    "mode": _TRIANGLES,
                }],
            }],
            "accessors": accessors,
            "bufferViews": buffer_views,
            "buffers": [{
                "byteLength": len(blob),
                "uri": "data:application/octet-stream;base64,"
                       + base64.b64encode(blob).decode("ascii"),
            }],
        }

    def export_to_file(self, mesh: Mesh, filepath: str,
                       name: str | None = None) -> None:
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(self.export(mesh, name))


def export_gltf(mesh: Mesh, filepath: str, name: str | None = None) -> None:
    """Write ``mesh`` to ``filepath`` as a self-contained glTF 2.0 file.

    Args:
        mesh: The mesh to export.
        filepath: Destination ``.gltf`` file path.
        name: Optional node/mesh name. Defaults to ``mesh.name``.
    """
    GLTFExporter().export_to_file(mesh, filepath, name)
