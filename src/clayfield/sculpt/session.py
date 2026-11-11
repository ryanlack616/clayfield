"""Stroke session that applies brush dabs to the heightfield.

A session is created when the pointer is pressed and finished when it is released.
It owns the evaluated heightfield, the displacement layer, and the pending stroke.
Every dab reads the current evaluated surface, smooths its footprint, writes the
result back to both arrays, and appends a bounded edit for history.
"""

from __future__ import annotations

import numpy as np

from clayfield.sculpt.brush import BrushSettings
from clayfield.sculpt.brush_query import BrushRegion, compute_region
from clayfield.sculpt.history import SculptEdit, SculptHistory, SculptStroke
from clayfield.sculpt.smooth_bilateral import smooth_bilateral
from clayfield.sculpt.smooth_laplacian import smooth_laplacian
from clayfield.sculpt.smooth_taubin import smooth_taubin
from clayfield.sculpt.stroke import StrokePoint, interpolate_stroke


class SculptSession:
    """Apply one continuous stroke to a heightfield and its displacement layer.

    ``heightfield`` is the evaluated surface (``base + offsets``) and is modified in
    place; ``offsets`` receives the same displacement so the layer stays consistent.
    ``history`` is optional: without it the stroke is applied but not recorded.
    """

    def __init__(
        self,
        heightfield: np.ndarray,
        offsets: np.ndarray,
        width_mm: float,
        depth_mm: float,
        settings: BrushSettings,
        history: SculptHistory | None = None,
    ) -> None:
        surface = np.asarray(heightfield)
        layer = np.asarray(offsets)
        if surface.ndim != 2 or surface.shape[0] < 2 or surface.shape[1] < 2:
            raise ValueError("Sculpt heightfield must be a 2D grid of at least 2x2")
        if layer.shape != surface.shape:
            raise ValueError("Sculpt offsets must match the heightfield shape")
        if not np.isfinite(width_mm) or not np.isfinite(depth_mm) or width_mm <= 0.0 or depth_mm <= 0.0:
            raise ValueError("Sculpt dimensions must be finite and positive")
        settings.validate()
        self.heightfield = surface
        self.offsets = layer
        self.width_mm = float(width_mm)
        self.depth_mm = float(depth_mm)
        self.settings = settings
        self.history = history
        self._last: StrokePoint | None = None
        self._edits: list[SculptEdit] = []
        self._region: BrushRegion | None = None

    @property
    def edited(self) -> bool:
        """True once this stroke has changed at least one cell."""
        return bool(self._edits)

    def begin_stroke(self, x_mm: float, z_mm: float) -> bool:
        """Start a stroke and apply the first dab at the press position."""
        self._last = StrokePoint(float(x_mm), float(z_mm))
        self._edits = []
        self._region = None
        return self._apply_dab(self._last)

    def apply_stroke(self, x_mm: float, z_mm: float) -> bool:
        """Continue the stroke to ``(x_mm, z_mm)``, filling the gap with spaced dabs.

        Returns True when at least one dab changed the heightfield.
        """
        if self._last is None:
            return self.begin_stroke(x_mm, z_mm)
        points = interpolate_stroke(self._last, (x_mm, z_mm), self.settings.spacing, include_start=False)
        changed = False
        for point in points:
            changed = self._apply_dab(point) or changed
        self._last = StrokePoint(float(x_mm), float(z_mm))
        return changed

    def finish(self) -> SculptStroke | None:
        """Close the stroke and record it as one undo entry."""
        if not self._edits:
            self._last = None
            return None
        stroke = SculptStroke(tuple(self._edits))
        self._edits = []
        self._last = None
        self._region = None
        if self.history is not None:
            self.history.record(stroke)
        return stroke

    def _apply_dab(self, point: StrokePoint) -> bool:
        region = compute_region(self.heightfield, point.x_mm, point.z_mm, self.width_mm, self.depth_mm, self.settings)
        if region is None:
            return False
        before = self.heightfield[region.block_slice].copy()
        after = self._smooth(before, region.weights)
        if np.array_equal(before, after):
            return False
        self.heightfield[region.block_slice] = after
        self.offsets[region.block_slice] += after - before
        self._edits.append(
            SculptEdit(
                row0=region.row0,
                row1=region.row1,
                col0=region.col0,
                col1=region.col1,
                before=before,
                after=after.copy(),
            )
        )
        self._region = region
        return True

    def _smooth(self, block: np.ndarray, weights: np.ndarray) -> np.ndarray:
        algorithm = self.settings.algorithm
        if algorithm == "taubin":
            return smooth_taubin(block, weights)
        if algorithm == "bilateral":
            return smooth_bilateral(
                block,
                weights,
                sigma_spatial=self.settings.bilateral_spatial,
                sigma_range_mm=self.settings.bilateral_range_mm,
            )
        return smooth_laplacian(block, weights)
