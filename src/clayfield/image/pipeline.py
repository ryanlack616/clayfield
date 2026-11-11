"""Pure image-adjustment pipeline suitable for worker execution."""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock

import numpy as np

from clayfield.core.cancellation import check_cancelled
from clayfield.image.curves import apply_curve
from clayfield.image.filters import adjust_brightness_contrast, gaussian_blur, sharpen, threshold
from clayfield.image.grayscale import invert
from clayfield.image.levels import apply_levels

# Adjustment stages are full-resolution float32 arrays. A 16384x16384 stage is
# 1 GiB, so an unbounded six-stage cache can retain 6 GiB per source. The cache
# is therefore byte-budgeted and evicts least-recently-used stages.
DEFAULT_ADJUSTMENT_CACHE_BYTES = 2 * 1024 * 1024 * 1024


def apply_adjustments(
    image: np.ndarray,
    settings: dict[str, float | bool],
    curve_points: list[tuple[float, float]],
) -> np.ndarray:
    """Apply all image adjustments without accessing Qt or mutable UI state.

    The input array is treated as read-only. When no adjustment changes the
    image, the returned array may be the input itself; callers must not mutate
    it. Every stage operation otherwise returns a new owned array.
    """
    def get(name: str, default: float) -> float:
        value: float | bool = settings.get(name, default)
        return float(value)

    result = invert(image) if bool(settings.get("inverted", False)) else image
    result = apply_levels(
        result,
        get("Black point", 0.0),
        get("Gamma", 1.0),
        get("White point", 1.0),
        get("Output black", 0.0),
        get("Output white", 1.0),
    )
    result = apply_curve(result, curve_points, str(settings.get("Curve interpolation", "linear")))
    result = adjust_brightness_contrast(result, get("Brightness", 0.0), get("Contrast", 1.0))
    result = gaussian_blur(result, get("Blur", 0.0))
    result = sharpen(result, get("Sharpen", 0.0))
    if bool(settings.get("threshold_enabled", False)):
        result = threshold(result, get("Threshold", 0.5))
    return result.astype(np.float32, copy=False)


class AdjustmentCache:
    """Cache ordered stages for one immutable grayscale source at a time.

    Stages are full-resolution arrays. The cache is byte-budgeted and evicts
    least-recently-used stage results so a long adjustment session cannot retain
    an unbounded number of 1 GiB planes. ``clear`` releases every cached stage;
    callers should invoke it when the heightfield is invalidated.
    """

    def __init__(self, max_bytes: int = DEFAULT_ADJUSTMENT_CACHE_BYTES) -> None:
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
            raise ValueError("Adjustment cache budget must be a positive integer")
        self._lock = Lock()
        self._source = None
        self._max_bytes = max_bytes
        self._total_bytes = 0
        self._stages: OrderedDict[tuple[int, tuple], tuple[np.ndarray, int]] = OrderedDict()

    def _clear_locked(self) -> None:
        self._stages.clear()
        self._total_bytes = 0

    def clear(self) -> None:
        """Drop all cached stage results."""
        with self._lock:
            self._clear_locked()

    def _store(self, key, result) -> bool:
        """Retain one stage result when it fits the byte budget.

        A single stage larger than the whole budget cannot be cached without
        breaking the bound. Caching it while evicting everything else would
        pin one oversized full-resolution array indefinitely, which is exactly
        the failure this budget exists to prevent. Such a stage is returned to
        the caller but not retained; the cache is emptied so previously cached
        stages are released too. Returns ``True`` when the stage was retained.
        """
        nbytes = int(getattr(result, "nbytes", 0))
        if nbytes > self._max_bytes:
            self._clear_locked()
            return False
        previous = self._stages.pop(key, None)
        if previous is not None:
            self._total_bytes -= previous[1]
        self._stages[key] = (result, nbytes)
        self._total_bytes += nbytes
        # Evict oldest stages first, including the last one: the cache may be
        # smaller than a single stage, and keeping a stale entry would violate
        # the byte budget rather than protect it.
        while self._total_bytes > self._max_bytes and self._stages:
            _, (_, evicted_bytes) = self._stages.popitem(last=False)
            self._total_bytes -= evicted_bytes
        return key in self._stages

    def apply(self, image, settings, curve_points, *, cancel_check=None):
        def get(name: str, default: float) -> float:
            value: float | bool = settings.get(name, default)
            return float(value)

        level = (bool(settings.get("inverted", False)), get("Black point", 0), get("Gamma", 1),
                 get("White point", 1), get("Output black", 0), get("Output white", 1))
        curve = (tuple(tuple(p) for p in curve_points), str(settings.get("Curve interpolation", "linear")))
        contrast = (get("Brightness", 0), get("Contrast", 1))
        blur = get("Blur", 0)
        sharp = get("Sharpen", 0)
        cutoff = (bool(settings.get("threshold_enabled", False)), get("Threshold", 0.5))
        operations = (
            (level, lambda x: apply_levels(invert(x) if level[0] else x, *level[1:])),
            (curve, lambda x: apply_curve(x, list(curve[0]), curve[1])),
            (contrast, lambda x: adjust_brightness_contrast(x, *contrast)),
            (blur, lambda x: gaussian_blur(x, blur) if blur else x),
            (sharp, lambda x: sharpen(x, sharp) if sharp else x),
            (cutoff, lambda x: threshold(x, cutoff[1]) if cutoff[0] else x),
        )
        with self._lock:
            check_cancelled(cancel_check)
            if self._source is not image:
                self._source = image
                self._clear_locked()
            result = image
            key = ()
            for index, (parameters, operation) in enumerate(operations):
                check_cancelled(cancel_check)
                key = (key, parameters)
                cached = self._stages.get((index, key))
                if cached is not None:
                    self._stages.move_to_end((index, key))
                    result = cached[0]
                else:
                    result = operation(result)
                    check_cancelled(cancel_check)
                    self._store((index, key), result)
            return result.astype(np.float32, copy=False)
