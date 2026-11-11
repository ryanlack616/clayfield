"""Minimal standards-compatible 3MF export."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from clayfield.core.cancellation import check_cancelled
from clayfield.export.stl import ExportError
from clayfield.geometry.mesh_generator import SolidMesh
from clayfield.geometry.validation import validate_mesh

MODEL_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"


def export_3mf(mesh: SolidMesh, path: str | Path, *, cancel_check=None) -> Path:
    """Write a validated mesh as a single-object 3MF package."""
    report = validate_mesh(mesh, cancel_check=cancel_check)
    if not report.valid:
        raise ExportError(report.message)
    output = Path(path).expanduser()
    if output.suffix.lower() != ".3mf":
        output = output.with_suffix(".3mf")
    output.parent.mkdir(parents=True, exist_ok=True)

    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />'
        '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml" />'
        "</Types>"
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" />'
        "</Relationships>"
    )
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        with ZipFile(temporary_path, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", content_types)
            archive.writestr("_rels/.rels", relationships)
            with archive.open("3D/3dmodel.model", "w") as model:
                model.write(
                    (
                        f'<?xml version="1.0" encoding="UTF-8"?><model xmlns="{MODEL_NS}" unit="millimeter" xml:lang="en-US"><resources><object id="1" type="model"><mesh><vertices>'
                    ).encode()
                )
                for start in range(0, len(mesh.vertices), 8192):
                    check_cancelled(cancel_check)
                    vertices = "".join(
                        f'<vertex x="{float(x):.9g}" y="{float(y):.9g}" z="{float(z):.9g}" />'
                        for x, y, z in mesh.vertices[start : start + 8192]
                    )
                    model.write(vertices.encode())
                model.write(b"</vertices><triangles>")
                for start in range(0, len(mesh.faces), 8192):
                    check_cancelled(cancel_check)
                    triangles = "".join(
                        f'<triangle v1="{int(a)}" v2="{int(b)}" v3="{int(c)}" />'
                        for a, b, c in mesh.faces[start : start + 8192]
                    )
                    model.write(triangles.encode())
                model.write(b'</triangles></mesh></object></resources><build><item objectid="1" /></build></model>')
        from clayfield.export.verification import verify_3mf_export

        check_cancelled(cancel_check)
        verify_3mf_export(temporary_path, mesh, cancel_check=cancel_check)
        check_cancelled(cancel_check)
        os.replace(temporary_path, output)
        temporary_path = None
        return output
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
