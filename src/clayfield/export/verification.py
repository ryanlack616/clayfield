"""Independent verification of serialized ClayField exports."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import cv2
import numpy as np
import trimesh

from clayfield.core.cancellation import check_cancelled
from clayfield.export.stl import ExportError
from clayfield.geometry.mesh_generator import SolidMesh

MODEL_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"


def verify_stl_export(path: str | Path, expected: SolidMesh, *, cancel_check=None) -> None:
    """Reopen an STL and verify core solid-mesh invariants."""
    check_cancelled(cancel_check)
    try:
        loaded = trimesh.load(str(path), file_type="stl", force="mesh", process=True)
    except Exception as error:
        raise ExportError(f"Written STL could not be reopened: {error}") from error
    check_cancelled(cancel_check)
    if not isinstance(loaded, trimesh.Trimesh):
        raise ExportError("Written STL did not contain a triangle mesh")
    if len(loaded.vertices) == 0 or len(loaded.faces) == 0:
        raise ExportError("Written STL contains no geometry")
    if not np.isfinite(loaded.vertices).all():
        raise ExportError("Written STL contains non-finite coordinates")
    if not loaded.is_watertight or loaded.volume <= 0:
        raise ExportError("Written STL is not a watertight positive-volume solid")
    check_cancelled(cancel_check)
    expected_bounds = np.asarray([expected.vertices.min(axis=0), expected.vertices.max(axis=0)])
    actual_bounds = np.asarray([loaded.vertices.min(axis=0), loaded.vertices.max(axis=0)])
    if not np.allclose(actual_bounds, expected_bounds, rtol=1e-5, atol=1e-4):
        raise ExportError("Written STL bounds do not match the source mesh")


def verify_heightmap_export(path: str | Path, expected: np.ndarray, *, cancel_check=None) -> None:
    """Reopen an exported heightmap and verify its pixel shape and dtype."""
    check_cancelled(cancel_check)
    try:
        loaded = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    except cv2.error as error:
        raise ExportError(f"Written heightmap could not be reopened: {error}") from error
    if loaded is None:
        raise ExportError("Written heightmap could not be reopened")
    if loaded.shape != expected.shape:
        raise ExportError(f"Written heightmap shape {loaded.shape} does not match the source {expected.shape}")
    if loaded.dtype != expected.dtype:
        raise ExportError(f"Written heightmap dtype {loaded.dtype} does not match the source {expected.dtype}")


def verify_3mf_export(path: str | Path, expected: SolidMesh, *, cancel_check=None) -> None:
    """Reopen a 3MF package and verify its required model payload."""
    try:
        check_cancelled(cancel_check)
        with ZipFile(path) as archive:
            required = {"[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"}
            if not required.issubset(archive.namelist()):
                raise ExportError("Written 3MF is missing required package parts")
            vertex_count = triangle_count = 0
            stack = []
            with archive.open("3D/3dmodel.model") as model:
                for event, element in ET.iterparse(model, events=("start", "end")):
                    if event == "start":
                        if not stack and (
                            element.tag != f"{{{MODEL_NS}}}model" or element.attrib.get("unit") != "millimeter"
                        ):
                            raise ExportError("Written 3MF has invalid model metadata")
                        stack.append(element)
                    else:
                        if element.tag == f"{{{MODEL_NS}}}vertex":
                            vertex_count += 1
                        elif element.tag == f"{{{MODEL_NS}}}triangle":
                            triangle_count += 1
                        if (vertex_count + triangle_count) % 8192 == 0:
                            check_cancelled(cancel_check)
                        stack.pop()
                        if stack:
                            stack[-1].remove(element)
                        element.clear()
    except (OSError, BadZipFile, ET.ParseError) as error:
        raise ExportError(f"Written 3MF could not be reopened: {error}") from error
    if vertex_count != len(expected.vertices) or triangle_count != len(expected.faces):
        raise ExportError("Written 3MF geometry counts do not match the source mesh")
