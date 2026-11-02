"""Tests for mesh topology and memory estimates."""

from __future__ import annotations

import pytest

from clayfield.geometry.estimates import estimate_solid_mesh, recommended_resolution


def test_estimate_matches_small_solid_topology() -> None:
    estimate = estimate_solid_mesh(3, 4)

    assert estimate.vertex_count == 24
    assert estimate.triangle_count == 4 * 2 * 3 + 2 * (2 * 3 + 2 * 4 - 4)
    assert estimate.vertex_bytes == 24 * 3 * 4
    assert estimate.face_bytes == estimate.triangle_count * 3 * 8
    assert estimate.working_bytes == estimate.total_bytes * 20


@pytest.mark.parametrize("rows, columns", [(0, 4), (1, 4), (4, 1), (-2, 3)])
def test_estimate_rejects_small_resolution(rows: int, columns: int) -> None:
    with pytest.raises(ValueError, match="at least 2"):
        estimate_solid_mesh(rows, columns)


def test_estimate_reports_mebibytes() -> None:
    estimate = estimate_solid_mesh(2048, 2048)

    assert estimate.total_mebibytes > 0
    assert estimate.working_mebibytes == pytest.approx(estimate.total_mebibytes * 20)
    assert estimate.triangle_count > 8_000_000


def test_recommended_resolution_preserves_budget() -> None:
    rows, columns = recommended_resolution(4096, 4096, 8_000_000)
    estimate = estimate_solid_mesh(rows, columns)
    assert rows >= 2 and columns >= 2
    assert estimate.triangle_count <= 8_000_000
    assert rows / columns == pytest.approx(1.0, abs=0.02)
