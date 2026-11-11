"""Detail-preserving bilateral smoothing on a heightfield block.

A bilateral filter averages neighbours with two weights: a spatial Gaussian and a
range Gaussian on the height difference. The range term suppresses neighbours on
the far side of a sharp step, so crests and cliff edges survive where ordinary
Laplacian smoothing rounds them off.

The handoff's normal-similarity term is replaced by height difference. On a
heightfield the surface normal is a deterministic function of the height gradient,
so the height difference is the same discriminator without a per-cell normal
buffer. ``sigma_r_mm`` is in millimetres, matching the heightfield's units.
"""

from __future__ import annotations

import math

import numpy as np

# 3x3 is the smallest neighbourhood that still has diagonal support. A wider
# kernel costs O(k^2) per cell and is not needed to preserve a cliff edge.
_OFFSETS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def smooth_bilateral(
    block: np.ndarray,
    weights: np.ndarray,
    *,
    sigma_spatial: float = 1.0,
    sigma_range_mm: float = 0.25,
) -> np.ndarray:
    """Return the bilateral-filtered block blended by the brush weights.

    ``sigma_spatial`` is in cells; ``sigma_range_mm`` is in millimetres. The input
    block is not modified. ``weights`` already carries the brush strength and
    falloff.
    """
    values = np.asarray(block, dtype=np.float32)
    influence = np.asarray(weights, dtype=np.float32)
    if values.shape != influence.shape:
        raise ValueError("Bilateral weights must match the block shape")
    if not math.isfinite(sigma_spatial) or sigma_spatial <= 0.0:
        raise ValueError("Bilateral spatial sigma must be finite and positive")
    if not math.isfinite(sigma_range_mm) or sigma_range_mm <= 0.0:
        raise ValueError("Bilateral range sigma must be finite and positive")

    padded = np.pad(values, 1, mode="edge")
    height, width = values.shape
    total = np.zeros_like(values)
    normalizer = np.zeros_like(values)
    spatial_denominator = 2.0 * sigma_spatial * sigma_spatial
    range_denominator = 2.0 * sigma_range_mm * sigma_range_mm
    for offset_row, offset_column in _OFFSETS:
        neighbour = padded[1 + offset_row : 1 + offset_row + height, 1 + offset_column : 1 + offset_column + width]
        spatial = math.exp(-(offset_row * offset_row + offset_column * offset_column) / spatial_denominator)
        difference = neighbour - values
        range_weight = np.exp(-(difference * difference) / range_denominator)
        combined = spatial * range_weight
        total += combined * neighbour
        normalizer += combined
    average = total / np.maximum(normalizer, 1e-12)
    return (values + influence * (average - values)).astype(np.float32)
