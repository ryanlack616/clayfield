"""Generate deterministic V2 sample projects and validated mesh artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from clayfield.app.project_io import save_project
from clayfield.app.project_state import ProjectState
from clayfield.export.tasks import export_procedural_heightmap_task, export_procedural_mesh_task
from clayfield.field import MandelbrotParameters, NoiseParameters, PipelineSnapshot, SourceDescriptor, WaveParameters
from clayfield.terrain.heightfield import PhysicalDimensions
from clayfield.terrain.mapping import MappingSettings


def _descriptor(kind: str) -> SourceDescriptor:
    if kind == "noise":
        parameters = NoiseParameters(
            seed=42,
            base_frequency=2.0,
            octaves=6,
            persistence=0.55,
            lacunarity=2.0,
            amplitude=1.0,
            normalization="fixed",
        )
        return SourceDescriptor(
            source_type="fractal_noise",
            parameters=parameters.__dict__.copy(),
            algorithm="value_fbm",
            algorithm_version="1",
            seed=42,
        )
    if kind == "waves":
        parameters = WaveParameters(mode="radial", radial_frequency=6.0, output_amplitude=1.0)
        return SourceDescriptor(
            source_type="wave_interference",
            parameters=parameters.__dict__.copy(),
            algorithm="wave_interference",
            algorithm_version="1",
        )
    parameters = MandelbrotParameters(zoom=1.0, iterations=100, contrast=1.0, invert=False)
    return SourceDescriptor(
        source_type="mandelbrot",
        parameters=parameters.__dict__.copy(),
        algorithm="smooth_escape_time",
        algorithm_version="1",
    )


def generate_samples(output: Path, resolution: tuple[int, int]) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    dimensions = PhysicalDimensions(width_mm=100.0, depth_mm=100.0, minimum_height_mm=0.0, maximum_height_mm=5.0)
    results = []
    for kind in ("noise", "waves", "mandelbrot"):
        source = _descriptor(kind)
        snapshot = PipelineSnapshot.from_settings(source, mapping=MappingSettings(maximum_height_mm=5.0))
        state = ProjectState(
            source_type=source.source_type, source_descriptor=source.to_dict(), pipeline_snapshot=snapshot.to_dict()
        )
        project = save_project(state, output / f"v2-{kind}.clayfield")
        export_procedural_mesh_task(snapshot, dimensions, resolution, 3.0, "positive", output / f"v2-{kind}.stl", "stl")
        export_procedural_heightmap_task(snapshot, resolution, output / f"v2-{kind}.png")
        results.append(project)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("dist/v2-samples"))
    parser.add_argument("--size", type=int, default=128)
    args = parser.parse_args()
    if args.size < 2:
        parser.error("--size must be at least 2")
    paths = generate_samples(args.output.expanduser(), (args.size, args.size))
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
