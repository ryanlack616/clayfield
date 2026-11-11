"""Optional end-to-end test using an independently installed PrusaSlicer CLI."""

import os
import shutil
import subprocess

import numpy as np
import pytest

from clayfield.export.tasks import export_mesh_task
from clayfield.terrain.heightfield import PhysicalDimensions


@pytest.mark.parametrize("kind", ["stl", "3mf"])
def test_printable_export_slices_in_prusaslicer(tmp_path, kind):
    slicer = os.environ.get("CLAYFIELD_PRUSA_SLICER") or shutil.which("prusa-slicer")
    if not slicer:
        pytest.skip("PrusaSlicer CLI is not installed")
    image = np.array([[0.0, 0.3, 1.0], [0.2, 0.5, 0.8]], dtype=np.float32)
    model = export_mesh_task(
        image, PhysicalDimensions(60, 40, 0, 3), (48, 32), 5, "positive", tmp_path / f"tile.{kind}", kind
    )
    info = subprocess.run([slicer, "--info", str(model)], check=True, capture_output=True, text=True, timeout=60).stdout
    assert "manifold = yes" in info
    for dimension in ("size_x = 60.000000", "size_y = 40.000000", "size_z = 8.000000"):
        assert dimension in info
    gcode = tmp_path / f"tile-{kind}.gcode"
    subprocess.run(
        [slicer, "--export-gcode", "--output", str(gcode), str(model)],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert gcode.exists() and gcode.stat().st_size > 1000
