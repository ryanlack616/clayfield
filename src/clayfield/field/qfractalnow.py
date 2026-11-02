"""Headless QFractalNow rendering for serialized field sources."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np

from clayfield.app.cancellation import check_cancelled
from clayfield.field.model import FieldMetadata, NormalizedField
from clayfield.image.grayscale import to_grayscale


def render_qfractalnow_config(
    config_text: str,
    shape: tuple[int, int],
    *,
    cancel_check=None,
    progress_callback=None,
) -> NormalizedField:
    """Render an embedded QFractalNow config into a normalized field."""
    if not isinstance(config_text, str) or not config_text.strip():
        raise ValueError("QFractalNow configuration is empty")
    rows, columns = shape
    if rows < 2 or columns < 2:
        raise ValueError("QFractalNow render resolution must be at least 2x2")
    executable = shutil.which("fractalnow")
    if executable is None:
        raise RuntimeError("The fractalnow command is not installed or is not on PATH")
    check_cancelled(cancel_check)
    with tempfile.TemporaryDirectory(prefix="clayfield-fractalnow-") as directory:
        root = Path(directory)
        config_path = root / "source.config"
        output_path = root / "render.ppm"
        config_path.write_text(config_text, encoding="utf-8")
        command = [executable, "-q", "-c", os.fspath(config_path), "-x", str(columns), "-y", str(rows), "-o", os.fspath(output_path)]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            while process.poll() is None:
                check_cancelled(cancel_check)
                if progress_callback:
                    progress_callback(50, "Rendering QFractalNow source")
                time.sleep(0.1)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                detail = (stderr or stdout).strip()
                raise RuntimeError(f"QFractalNow render failed{': ' + detail if detail else ''}")
            check_cancelled(cancel_check)
            image = cv2.imread(os.fspath(output_path), cv2.IMREAD_UNCHANGED)
            if image is None:
                raise RuntimeError("QFractalNow did not produce a readable image")
            values = to_grayscale(image)
            if values.shape != (rows, columns):
                values = cv2.resize(values, (columns, rows), interpolation=cv2.INTER_AREA)
            if progress_callback:
                progress_callback(100, "QFractalNow source ready")
            return NormalizedField(np.asarray(values, dtype=np.float32), FieldMetadata("qfractalnow_config", "fractalnow", "1"))
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
