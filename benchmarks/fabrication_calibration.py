"""Generate deterministic fabrication calibration panels."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from clayfield.export.orientation import orient_for_print
from clayfield.export.stl import export_stl
from clayfield.export.three_mf import export_3mf
from clayfield.geometry.mesh_generator import generate_solid_mesh


def _write(mesh, output: Path, stem: str) -> None:
    oriented = orient_for_print(mesh)
    export_stl(oriented, output / f"{stem}.stl")
    export_3mf(oriented, output / f"{stem}.3mf")


def generate_calibration_panels(output: Path, size: int = 256) -> list[Path]:
    if size < 16:
        raise ValueError("Calibration resolution must be at least 16")
    output.mkdir(parents=True, exist_ok=True)
    rows, columns = size, size
    feature = np.zeros((rows, columns), dtype=np.float32)
    for width in (1, 2, 4, 8, 16):
        start = sum((1, 2, 4, 8, 16)[:(width.bit_length() - 1)]) * 2
        feature[:, start:start + width] = 5.0
    _write(generate_solid_mesh(feature, 100.0, 40.0, 3.0), output, "calibration-feature-width")

    slope = np.repeat(np.linspace(0.0, 5.0, columns, dtype=np.float32)[None, :], rows, axis=0)
    _write(generate_solid_mesh(slope, 100.0, 40.0, 3.0), output, "calibration-slope")

    wall = np.zeros((rows, columns), dtype=np.float32)
    for index, depth in enumerate((0.5, 1.0, 1.5, 2.0, 2.5)):
        start = index * columns // 5
        stop = (index + 1) * columns // 5
        wall[:, start:stop] = depth
    _write(generate_solid_mesh(wall, 100.0, 40.0, 3.0, "negative"), output, "calibration-wall-thickness")
    return sorted(output.glob("calibration-*.*"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("dist/fabrication-calibration"))
    parser.add_argument("--size", type=int, default=256)
    args = parser.parse_args()
    for path in generate_calibration_panels(args.output.expanduser(), args.size):
        print(path)


if __name__ == "__main__":
    main()
