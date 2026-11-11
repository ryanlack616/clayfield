"""Heightmap image export."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import cv2
import numpy as np

from clayfield.core.cancellation import check_cancelled
from clayfield.export.stl import ExportError
from clayfield.resource_budget import DEFAULT_BUDGET, preflight_heightfield


def export_heightmap(
    heightfield: np.ndarray,
    path: str | Path,
    bit_depth: int = 16,
    *,
    budget=None,
    cancel_check=None,
) -> Path:
    """Export normalized or physical height data as an image."""
    check_cancelled(cancel_check)
    values = np.asarray(heightfield, dtype=np.float32)
    if values.ndim != 2 or values.size == 0 or not np.isfinite(values).all():
        raise ExportError("Heightmap must be non-empty finite 2D data")
    if bit_depth not in (8, 16):
        raise ExportError("Heightmap bit depth must be 8 or 16")
    preflight_heightfield(values.shape[0], values.shape[1], budget=budget or DEFAULT_BUDGET)
    minimum, maximum = float(values.min()), float(values.max())
    normalized = np.zeros_like(values) if maximum <= minimum else (values - minimum) / (maximum - minimum)
    maximum_pixel = 255 if bit_depth == 8 else 65535
    pixels = np.rint(np.clip(normalized, 0.0, 1.0) * maximum_pixel).astype(np.uint8 if bit_depth == 8 else np.uint16)
    output = Path(path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=output.suffix or ".png",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        check_cancelled(cancel_check)
        if not cv2.imwrite(str(temporary_path), pixels):
            raise ExportError(f"Could not write heightmap: {output}")
        check_cancelled(cancel_check)
        # Reopen the written file before replacing the destination. The mesh
        # paths already verify; the heightmap path previously trusted imwrite's
        # return value alone. Import lazily so verification's Trimesh dependency
        # is not pulled into every heightmap-only session.
        from clayfield.export.verification import verify_heightmap_export

        verify_heightmap_export(temporary_path, pixels, cancel_check=cancel_check)
        check_cancelled(cancel_check)
        os.replace(temporary_path, output)
        temporary_path = None
        return output
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
