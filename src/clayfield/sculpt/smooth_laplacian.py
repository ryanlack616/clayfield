"""Uniform Laplacian smoothing on a heightfield block.

The heightfield is a regular grid, so the discrete Laplacian is the 4-neighbour
stencil rather than the cotangent-weighted mesh operator from the handoff. The
handoff's cotangent formula is the general triangle-mesh form; on a regular quad
grid its weights are constant and the stencil below is its exact grid
specialization. ClayField has no interactive mesh, so this is the operator that
matches the geometry the viewport and exports actually use.

Boundary cells are clamped to their nearest interior neighbour (``edge`` padding),
which preserves the outer rim of the terrain instead of pulling it toward zero.
"""

from __future__ import annotations

import numpy as np

# ``laplacian_delta`` is the raw 4-neighbour Laplacian ``sum - 4*centre``. Its
# largest eigenvalue is 8, so the explicit step ``v + lambda * L`` only stays
# stable while ``lambda <= 1/8``... measured against the neighbour *count*, the
# average difference ``mean - centre`` has a largest eigenvalue of 2 and is stable
# while the blend fraction is at most 1. The kernels below therefore divide the
# raw Laplacian by four: the parameter they expose is the fraction of the way
# toward the neighbour average, not the raw operator gain.
NEIGHBOURS = 4.0


def laplacian_delta(block: np.ndarray) -> np.ndarray:
    """Return the 4-neighbour Laplacian of ``block`` with edge-clamped borders."""
    values = np.asarray(block, dtype=np.float32)
    if values.ndim != 2:
        raise ValueError("Laplacian input must be 2D")
    padded = np.pad(values, 1, mode="edge")
    centre = padded[1:-1, 1:-1]
    total = padded[:-2, 1:-1] + padded[2:, 1:-1] + padded[1:-1, :-2] + padded[1:-1, 2:]
    return (total - 4.0 * centre).astype(np.float32)


def smooth_laplacian(block: np.ndarray, weights: np.ndarray, lambda_: float = 1.0) -> np.ndarray:
    """Blend ``block`` toward its neighbour average by ``lambda * weights``.

    ``weights`` already carries the brush strength and falloff, so the effective
    blend is ``lambda * strength`` and stays below one for the documented ranges.
    The raw Laplacian is divided by the neighbour count first: at the full step it
    would otherwise multiply the highest-frequency component by ``1 - 8*lambda``,
    which is a runaway for any ``lambda`` above ``0.25`` and a checkerboard
    inversion at exactly ``0.25``. Repeated dabs then grow without bound until the
    surface leaves the model entirely. The input block is not modified; the caller
    owns the returned array. The zero-weight stencil margin in ``weights`` keeps
    the region's support ring untouched, so repeated dabs do not creep outward.
    """
    values = np.asarray(block, dtype=np.float32)
    influence = np.asarray(weights, dtype=np.float32)
    if values.shape != influence.shape:
        raise ValueError("Laplacian weights must match the block shape")
    if not np.isfinite(lambda_) or lambda_ <= 0.0:
        raise ValueError("Laplacian lambda must be finite and positive")
    step = float(lambda_) * influence / NEIGHBOURS
    return (values + step * laplacian_delta(values)).astype(np.float32)
