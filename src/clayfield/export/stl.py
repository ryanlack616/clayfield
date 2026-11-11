"""Validated STL export."""

from __future__ import annotations

import os
import struct
import tempfile
from pathlib import Path

import numpy as np

from clayfield.core.cancellation import check_cancelled
from clayfield.geometry.mesh_generator import SolidMesh
from clayfield.geometry.validation import validate_mesh


class ExportError(RuntimeError):
    """Raised when an export cannot be completed safely."""


def export_stl(mesh: SolidMesh, path: str | Path, *, cancel_check=None) -> Path:
    """Validate and export a solid mesh as binary STL in millimeters."""
    report = validate_mesh(mesh, cancel_check=cancel_check)
    if not report.valid:
        raise ExportError(report.message)
    output = Path(path).expanduser()
    if output.suffix.lower() != ".stl":
        output = output.with_suffix(".stl")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            if len(mesh.faces) > 0xFFFFFFFF:
                raise ExportError("STL cannot represent more than 2^32-1 triangles")
            temporary.write(b"ClayField binary STL".ljust(80, b"\0"))
            temporary.write(struct.pack("<I", len(mesh.faces)))
            record_type = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
            for start in range(0, len(mesh.faces), 65536):
                check_cancelled(cancel_check)
                triangles = np.asarray(mesh.vertices[mesh.faces[start:start + 65536]], dtype=np.float32)
                normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
                lengths = np.linalg.norm(normals, axis=1)
                normals /= np.maximum(lengths[:, None], np.finfo(np.float32).tiny)
                records = np.zeros(len(triangles), dtype=record_type)
                records["normal"] = normals
                records["vertices"] = triangles
                temporary.write(records.tobytes())
        check_cancelled(cancel_check)
        from clayfield.export.verification import verify_stl_export
        verify_stl_export(temporary_path, mesh, cancel_check=cancel_check)
        check_cancelled(cancel_check)
        os.replace(temporary_path, output)
        temporary_path = None
        return output
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
