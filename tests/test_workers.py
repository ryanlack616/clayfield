"""Regression tests for worker-safe processing tasks."""

from pathlib import Path

import cv2
import numpy as np
import pytest
import trimesh

from clayfield.app.worker import WorkerCancelled
from clayfield.export.heightmap import export_heightmap
from clayfield.export.stl import export_stl
from clayfield.export.tasks import (
    analyze_image_export_task,
    analyze_procedural_export_task,
    export_heightmap_task,
    export_mesh_task,
    export_procedural_heightmap_task,
    export_procedural_mesh_task,
)
from clayfield.field import PipelineSnapshot, SourceDescriptor
from clayfield.geometry.mesh_generator import generate_solid_mesh
from clayfield.image.pipeline import AdjustmentCache, apply_adjustments
from clayfield.terrain.heightfield import PhysicalDimensions
from clayfield.terrain.mapping import MappingSettings


def _raise_value_error():
    raise ValueError("worker boom")


def test_worker_reports_traceback_on_failure() -> None:
    from clayfield.app.worker import FunctionWorker

    failures: list[str] = []
    worker = FunctionWorker(_raise_value_error)
    worker.signals.failed.connect(failures.append)
    worker.run()

    assert len(failures) == 1
    assert "ValueError: worker boom" in failures[0]
    assert "Traceback (most recent call last)" in failures[0]


def test_worker_reports_cancellation_without_a_traceback() -> None:
    from clayfield.app.worker import FunctionWorker

    failures: list[str] = []
    cancellations: list[bool] = []
    worker = FunctionWorker(lambda: (_ for _ in ()).throw(WorkerCancelled()))
    worker.signals.failed.connect(failures.append)
    worker.signals.cancelled.connect(lambda: cancellations.append(True))
    worker.run()

    assert cancellations == [True]
    assert not failures


def test_pipeline_applies_persisted_inversion() -> None:
    image = np.array([[0.0, 1.0]], dtype=np.float32)
    result = apply_adjustments(image, {"inverted": True}, [(0.0, 0.0), (1.0, 1.0)])
    np.testing.assert_allclose(result, [[1.0, 0.0]])


def test_heightmap_task_honors_cancellation(tmp_path: Path) -> None:
    with pytest.raises(WorkerCancelled):
        export_heightmap_task(
            np.zeros((4, 4), dtype=np.float32),
            PhysicalDimensions(),
            (8, 8),
            tmp_path / "cancelled.png",
            cancel_check=lambda: True,
        )


def test_mesh_task_honors_cancellation_before_writing(tmp_path: Path) -> None:
    output = tmp_path / "cancelled.stl"
    with pytest.raises(WorkerCancelled):
        export_mesh_task(
            np.zeros((4, 4), dtype=np.float32),
            PhysicalDimensions(),
            (8, 8),
            5.0,
            "positive",
            output,
            "stl",
            cancel_check=lambda: True,
        )
    assert not output.exists()


def test_mesh_task_reports_progress(tmp_path: Path) -> None:
    progress: list[tuple[int, str]] = []
    export_mesh_task(
        np.zeros((4, 4), dtype=np.float32),
        PhysicalDimensions(),
        (8, 8),
        5.0,
        "positive",
        tmp_path / "mesh.stl",
        "stl",
        progress_callback=lambda percent, message: progress.append((percent, message)),
    )
    assert progress[0][0] == 10
    assert progress[-1][0] == 100


def test_mesh_export_is_flat_on_the_build_plate(tmp_path: Path) -> None:
    path = export_mesh_task(
        np.array([[0.0, 1.0], [0.0, 1.0]], dtype=np.float32),
        PhysicalDimensions(60, 40, 0, 3), (8, 8), 5, "positive",
        tmp_path / "flat.stl", "stl",
    )
    mesh = trimesh.load(path, force="mesh")
    np.testing.assert_allclose(mesh.extents, [60, 40, 8], atol=1e-4)
    assert mesh.bounds[0, 2] == pytest.approx(0)
    assert mesh.is_watertight and mesh.volume > 0


def test_heightmap_task_reports_progress(tmp_path: Path) -> None:
    progress: list[tuple[int, str]] = []
    export_heightmap_task(
        np.zeros((4, 4), dtype=np.float32),
        PhysicalDimensions(),
        (8, 8),
        tmp_path / "heightmap.png",
        progress_callback=lambda percent, message: progress.append((percent, message)),
    )
    assert progress[0][0] == 10
    assert progress[-1][0] == 100


def _procedural_snapshot() -> PipelineSnapshot:
    source = SourceDescriptor(
        source_type="fractal_noise",
        algorithm="value_fbm",
        algorithm_version="1",
        seed=8,
        parameters={"seed": 8, "base_frequency": 2.0, "octaves": 3, "persistence": 0.5, "lacunarity": 2.0, "amplitude": 1.0, "normalization": "auto", "tileable": False},
    )
    return PipelineSnapshot.from_settings(source, mapping=MappingSettings(maximum_height_mm=5.0))


def test_procedural_mesh_and_heightmap_tasks_export_at_requested_resolution(tmp_path: Path) -> None:
    snapshot = _procedural_snapshot()
    mesh_path = export_procedural_mesh_task(snapshot, PhysicalDimensions(100, 100, 0, 5), (8, 8), 3, "positive", tmp_path / "procedural.stl", "stl")
    mesh = trimesh.load(mesh_path, force="mesh")
    np.testing.assert_allclose(mesh.extents, [100, 100, 8], atol=1e-4)
    assert mesh.is_watertight
    heightmap_path = export_procedural_heightmap_task(snapshot, (8, 8), tmp_path / "procedural.png")
    assert cv2.imread(str(heightmap_path), cv2.IMREAD_UNCHANGED).shape == (8, 8)


def test_procedural_export_analysis_uses_requested_resolution() -> None:
    metrics = analyze_procedural_export_task(
        _procedural_snapshot(),
        (12, 10),
        100.0,
        80.0,
        3.0,
        "positive",
    )
    assert metrics.sample_spacing_mm == pytest.approx(min(100 / 11, 80 / 9))
    assert metrics.maximum_height_mm <= 5.0


def test_image_export_analysis_uses_legacy_export_mapping() -> None:
    metrics = analyze_image_export_task(
        np.array([[0.0, 1.0], [0.5, 0.25]], dtype=np.float32),
        PhysicalDimensions(100.0, 80.0, 0.0, 5.0),
        (12, 10),
        3.0,
        "positive",
    )
    assert metrics.maximum_height_mm == pytest.approx(5.0)


def test_negative_heightmap_represents_recessed_surface(tmp_path: Path) -> None:
    image = np.array([[0.0, 1.0], [0.0, 1.0]], dtype=np.float32)
    path = export_heightmap_task(image, PhysicalDimensions(), (2, 2), tmp_path / "negative.png", relief_mode="negative")
    pixels = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    assert pixels[0, 0] == 65535
    assert pixels[0, 1] == 0


def test_adjustment_cache_reuses_unaffected_stages(monkeypatch):
    import clayfield.image.pipeline as pipeline
    image = np.random.default_rng(1).random((32, 32), dtype=np.float32)
    points = [(0.0, 0.0), (0.4, 0.6), (1.0, 1.0)]
    cache = AdjustmentCache()
    cache.apply(image, {"Brightness": 0.1}, points)
    expected = apply_adjustments(image, {"Brightness": 0.1, "Blur": 1.0}, points)
    monkeypatch.setattr(pipeline, "apply_levels", lambda *args: pytest.fail("levels recomputed"))
    monkeypatch.setattr(pipeline, "apply_curve", lambda *args: pytest.fail("curve recomputed"))
    np.testing.assert_allclose(cache.apply(image, {"Brightness": 0.1, "Blur": 1.0}, points), expected)


def test_mesh_generation_checks_cancellation_between_chunks():
    calls = 0
    def cancelled():
        nonlocal calls
        calls += 1
        return calls >= 4
    with pytest.raises(WorkerCancelled):
        generate_solid_mesh(np.zeros((512, 512), dtype=np.float32), 100, 100, 5, cancel_check=cancelled)


def test_cancelled_stl_write_preserves_existing_destination(tmp_path: Path):
    mesh = generate_solid_mesh(np.zeros((4, 4), dtype=np.float32), 20, 20, 3)
    output = tmp_path / "existing.stl"
    output.write_bytes(b"previous")
    def cancelled():
        return bool(list(tmp_path.glob(".existing.stl.*.tmp")))
    with pytest.raises(WorkerCancelled):
        export_stl(mesh, output, cancel_check=cancelled)
    assert output.read_bytes() == b"previous"
    assert not list(tmp_path.glob(".existing.stl.*.tmp"))


def test_cancelled_heightmap_write_preserves_existing_destination(tmp_path: Path):
    output = tmp_path / "existing.png"
    output.write_bytes(b"previous")
    def cancelled():
        return bool(list(tmp_path.glob(".existing.png.*.png")))
    with pytest.raises(WorkerCancelled):
        export_heightmap(np.ones((4, 4), dtype=np.float32), output, cancel_check=cancelled)
    assert output.read_bytes() == b"previous"
    assert not list(tmp_path.glob(".existing.png.*.png"))
