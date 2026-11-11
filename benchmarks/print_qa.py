"""Generate and independently slice the standard ClayField print QA tile."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np

from clayfield.export.tasks import export_mesh_task
from clayfield.terrain.heightfield import PhysicalDimensions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("dist/print-qa"))
    parser.add_argument("--slicer", type=Path, default=None)
    args = parser.parse_args()
    output = args.output.expanduser()
    output.mkdir(parents=True, exist_ok=True)
    image = np.array([[0.0, 0.2, 0.5, 0.8, 1.0], [0.1, 0.35, 0.6, 0.9, 0.7], [0.0, 0.25, 0.55, 0.85, 1.0]], dtype=np.float32)
    dimensions = PhysicalDimensions(60, 40, 0, 3)
    models = []
    for kind in ("stl", "3mf"):
        model = export_mesh_task(image, dimensions, (96, 64), 5, "positive", output / f"clayfield-qa.{kind}", kind)
        models.append(model)
    slicer = args.slicer or (Path(os.environ["CLAYFIELD_PRUSA_SLICER"]) if os.environ.get("CLAYFIELD_PRUSA_SLICER") else None)
    if slicer is None:
        slicer_name = shutil.which("prusa-slicer")
        slicer = Path(slicer_name) if slicer_name else None
    if slicer:
        for model in models:
            info = subprocess.run([str(slicer), "--info", str(model)], check=True, capture_output=True, text=True, timeout=120).stdout
            suffix = model.suffix.lstrip(".")
            (output / f"{model.stem}-{suffix}.info.txt").write_text(info, encoding="utf-8")
            gcode = output / f"{model.stem}-{suffix}.gcode"
            subprocess.run([str(slicer), "--export-gcode", "--output", str(gcode), str(model)], check=True, capture_output=True, text=True, timeout=180)
    print(f"Print QA artifacts: {output}")
    for model in models:
        print(model)


if __name__ == "__main__":
    main()
