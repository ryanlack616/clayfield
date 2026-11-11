"""Taubin (lambda/mu) smoothing on a heightfield block.

Two alternating Laplacian passes with a positive lambda and a negative mu shrink
high-frequency detail while largely cancelling the low-frequency volume loss of a
single repeated Laplacian filter. The default pair ``(0.5, -0.53)`` is the classic
Taubin choice and satisfies ``1/lambda + 1/mu > 0``, the passivity condition that
keeps the filter from amplifying frequencies.

The same brush weights are applied to both passes so the smoothed footprint stays
localized to the dab.
"""

from __future__ import annotations

import numpy as np

from clayfield.sculpt.smooth_laplacian import laplacian_delta

DEFAULT_LAMBDA = 0.5
DEFAULT_MU = -0.53


def smooth_taubin(
    block: np.ndarray,
    weights: np.ndarray,
    lambda_: float = DEFAULT_LAMBDA,
    mu: float = DEFAULT_MU,
) -> np.ndarray:
    """Return one Taubin pass over ``block`` using the supplied brush weights.

    The input block is not modified. ``weights`` already carries the brush
    strength and falloff.
    """
    values = np.asarray(block, dtype=np.float32)
    influence = np.asarray(weights, dtype=np.float32)
    if values.shape != influence.shape:
        raise ValueError("Taubin weights must match the block shape")
    if lambda_ <= 0.0:
        raise ValueError("Taubin lambda must be positive")
    if mu >= 0.0:
        raise ValueError("Taubin mu must be negative")
    first = values + float(lambda_) * influence * laplacian_delta(values)
    second = first + float(mu) * influence * laplacian_delta(first)
    return second.astype(np.float32)
