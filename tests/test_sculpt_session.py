"""Stroke session application, undo/redo, and export compatibility."""

import numpy as np
import pytest

from clayfield.export.stl import export_stl
from clayfield.export.three_mf import export_3mf
from clayfield.geometry.mesh_generator import generate_solid_mesh
from clayfield.sculpt.brush import BrushSettings
from clayfield.sculpt.history import SculptHistory, apply_stroke
from clayfield.sculpt.session import SculptSession

SIZE = 41
WIDTH_MM = 100.0
DEPTH_MM = 100.0


def _bump_field():
    heightfield = np.zeros((SIZE, SIZE), dtype=np.float32)
    centre = SIZE // 2
    heightfield[centre - 2 : centre + 2, centre - 2 : centre + 2] = 2.0
    return heightfield


def _session(heightfield, settings=None, history=None):
    settings = settings or BrushSettings(radius_mm=15.0, strength=0.6)
    base = heightfield.copy()
    offsets = np.zeros_like(heightfield)
    session = SculptSession(heightfield, offsets, WIDTH_MM, DEPTH_MM, settings, history)
    return session, base


def test_session_preserves_the_base_plus_offsets_identity():
    heightfield = _bump_field()
    session, base = _session(heightfield)
    session.begin_stroke(0.0, 0.0)
    session.apply_stroke(20.0, 0.0)
    session.finish()
    np.testing.assert_allclose(session.heightfield - session.offsets, base, atol=1e-6)


def test_session_stroke_smooths_the_surface():
    heightfield = _bump_field()
    session, base = _session(heightfield)
    session.begin_stroke(0.0, 0.0)
    session.apply_stroke(20.0, 0.0)
    stroke = session.finish()
    assert stroke is not None
    assert stroke.edits
    assert float(session.heightfield.max()) < float(base.max())
    assert np.isfinite(session.heightfield).all()


def test_session_stroke_on_a_flat_surface_records_nothing():
    heightfield = np.zeros((SIZE, SIZE), dtype=np.float32)
    history = SculptHistory()
    session, _ = _session(heightfield, history=history)
    session.begin_stroke(0.0, 0.0)
    session.apply_stroke(20.0, 0.0)
    assert session.finish() is None
    assert not history.can_undo


def test_session_undo_restores_the_original_surface():
    heightfield = _bump_field()
    history = SculptHistory()
    session, base = _session(heightfield, history=history)
    session.begin_stroke(0.0, 0.0)
    session.apply_stroke(20.0, 0.0)
    session.finish()
    stroke = history.undo()
    assert stroke is not None
    apply_stroke(session.heightfield, session.offsets, stroke, forward=False)
    np.testing.assert_allclose(session.heightfield, base, atol=1e-6)
    np.testing.assert_allclose(session.offsets, 0.0, atol=1e-6)


def test_session_redo_reapplies_the_stroke():
    heightfield = _bump_field()
    history = SculptHistory()
    session, _ = _session(heightfield, history=history)
    session.begin_stroke(0.0, 0.0)
    session.apply_stroke(20.0, 0.0)
    session.finish()
    modified = session.heightfield.copy()
    stroke = history.undo()
    assert stroke is not None
    apply_stroke(session.heightfield, session.offsets, stroke, forward=False)
    redo = history.redo()
    assert redo is not None
    apply_stroke(session.heightfield, session.offsets, redo, forward=True)
    np.testing.assert_allclose(session.heightfield, modified, atol=1e-6)


def test_session_multiple_strokes_undo_in_reverse_order():
    heightfield = _bump_field()
    history = SculptHistory()
    session, base = _session(heightfield, history=history)
    session.begin_stroke(-10.0, 0.0)
    session.apply_stroke(10.0, 0.0)
    first = session.finish()
    first_state = session.heightfield.copy()
    session.begin_stroke(10.0, 0.0)
    session.apply_stroke(25.0, 0.0)
    session.finish()
    second = history.undo()
    assert second is not None
    apply_stroke(session.heightfield, session.offsets, second, forward=False)
    np.testing.assert_allclose(session.heightfield, first_state, atol=1e-6)
    first_undo = history.undo()
    assert first_undo is first
    apply_stroke(session.heightfield, session.offsets, first_undo, forward=False)
    np.testing.assert_allclose(session.heightfield, base, atol=1e-6)


def test_session_applies_each_algorithm_without_nan():
    heightfield = _bump_field()
    for algorithm in ("laplacian", "taubin", "bilateral"):
        session, _ = _session(heightfield.copy(), BrushSettings(radius_mm=15.0, strength=0.6, algorithm=algorithm))
        session.begin_stroke(0.0, 0.0)
        session.apply_stroke(15.0, 0.0)
        session.finish()
        assert np.isfinite(session.heightfield).all()
        # Laplacian and Taubin may undershoot below the base plane when they
        # smooth a peak, which is a legitimate dent in the surface rather than an
        # error. Bound the excursion instead of requiring non-negative heights.
        assert session.heightfield.min() >= -5.0


def test_session_rejects_mismatched_offsets():
    heightfield = _bump_field()
    with pytest.raises(ValueError, match="offsets"):
        SculptSession(heightfield, np.zeros((2, 2), dtype=np.float32), WIDTH_MM, DEPTH_MM, BrushSettings())


def test_session_rejects_degenerate_heightfield():
    with pytest.raises(ValueError, match="2x2"):
        SculptSession(
            np.zeros((1, 1), dtype=np.float32), np.zeros((1, 1), dtype=np.float32), 100.0, 100.0, BrushSettings()
        )


def test_sculpted_heightfield_still_exports():
    heightfield = _bump_field()
    session, _ = _session(heightfield)
    session.begin_stroke(0.0, 0.0)
    session.apply_stroke(20.0, 0.0)
    session.finish()
    mesh = generate_solid_mesh(session.heightfield, WIDTH_MM, DEPTH_MM, 5.0, "positive")
    assert np.isfinite(mesh.vertices).all()
    assert mesh.faces.max() < len(mesh.vertices)


def test_sculpted_heightfield_exports_to_stl_and_3mf(tmp_path):
    heightfield = _bump_field()
    session, _ = _session(heightfield)
    session.begin_stroke(0.0, 0.0)
    session.apply_stroke(20.0, 0.0)
    session.finish()
    mesh = generate_solid_mesh(session.heightfield, WIDTH_MM, DEPTH_MM, 5.0, "positive")
    stl_path = export_stl(mesh, tmp_path / "sculpted.stl")
    three_mf_path = export_3mf(mesh, tmp_path / "sculpted.3mf")
    assert stl_path.exists() and stl_path.stat().st_size > 0
    assert three_mf_path.exists() and three_mf_path.stat().st_size > 0


def test_session_spacing_controls_dab_count():
    heightfield = _bump_field()
    dense, _ = _session(heightfield.copy(), BrushSettings(radius_mm=15.0, strength=0.6, spacing_mm=1.0))
    sparse, _ = _session(heightfield.copy(), BrushSettings(radius_mm=15.0, strength=0.6, spacing_mm=8.0))
    dense.begin_stroke(-20.0, 0.0)
    dense.apply_stroke(20.0, 0.0)
    dense_stroke = dense.finish()
    sparse.begin_stroke(-20.0, 0.0)
    sparse.apply_stroke(20.0, 0.0)
    sparse_stroke = sparse.finish()
    assert dense_stroke is not None and sparse_stroke is not None
    assert len(dense_stroke.edits) > len(sparse_stroke.edits)
