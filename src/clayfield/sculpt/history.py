"""Stroke-level undo and redo for the sculpting subsystem.

History stores only the rectangular blocks a dab touched, never a full heightfield
copy. A stroke is one undo entry made of one edit per dab, applied in order on redo
and in reverse on undo. ``apply_stroke`` writes both the evaluated heightfield and
the displacement layer so ``final == base + offsets`` stays true after a restore.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEFAULT_HISTORY_LIMIT = 100


@dataclass(frozen=True)
class SculptEdit:
    """The before and after values of one dab's rectangular footprint."""

    row0: int
    row1: int
    col0: int
    col1: int
    before: np.ndarray
    after: np.ndarray

    @property
    def block_slice(self) -> tuple[slice, slice]:
        """Inclusive bounds expressed as a NumPy basic slice."""
        return slice(self.row0, self.row1 + 1), slice(self.col0, self.col1 + 1)

    def __post_init__(self) -> None:
        if self.row1 < self.row0 or self.col1 < self.col0:
            raise ValueError("Sculpt edit bounds must be inclusive and ordered")
        expected = (self.row1 - self.row0 + 1, self.col1 - self.col0 + 1)
        if self.before.shape != expected or self.after.shape != expected:
            raise ValueError("Sculpt edit blocks must match the addressed region")


@dataclass(frozen=True)
class SculptStroke:
    """All edits produced by one press-drag-release interaction."""

    edits: tuple[SculptEdit, ...]

    def __post_init__(self) -> None:
        if not self.edits:
            raise ValueError("A sculpt stroke must contain at least one edit")


def apply_stroke(
    heightfield: np.ndarray,
    offsets: np.ndarray,
    stroke: SculptStroke,
    *,
    forward: bool,
) -> None:
    """Write a stroke's after values (redo) or before values (undo) in place.

    ``forward`` selects the after values and moves the displacement layer by
    ``after - before``; undo selects the before values and moves it by
    ``before - after``. The stored edit arrays are copied into the targets, so the
    history stays valid for repeated undo and redo.

    Dabs within one stroke can share cells, and each later edit's ``before`` is the
    state left by the earlier one. Undo therefore replays the edits in reverse, so
    the earliest ``before`` wins instead of being overwritten by a later dab's
    intermediate state. Redo replays them in order for the same reason.
    """
    ordered = stroke.edits if forward else tuple(reversed(stroke.edits))
    for edit in ordered:
        target = edit.after if forward else edit.before
        source = edit.before if forward else edit.after
        heightfield[edit.block_slice] = target
        offsets[edit.block_slice] += target - source


class SculptHistory:
    """Bounded undo and redo stacks of completed strokes."""

    def __init__(self, limit: int = DEFAULT_HISTORY_LIMIT) -> None:
        if limit < 1:
            raise ValueError("History limit must be at least one")
        self.limit = int(limit)
        self._undo: list[SculptStroke] = []
        self._redo: list[SculptStroke] = []

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def record(self, stroke: SculptStroke) -> None:
        """Push a completed stroke and drop the oldest beyond the limit."""
        self._undo.append(stroke)
        if len(self._undo) > self.limit:
            del self._undo[0]
        self._redo.clear()

    def undo(self) -> SculptStroke | None:
        """Move the newest stroke to the redo stack and return it."""
        if not self._undo:
            return None
        stroke = self._undo.pop()
        self._redo.append(stroke)
        return stroke

    def redo(self) -> SculptStroke | None:
        """Move the newest undone stroke back to the undo stack and return it."""
        if not self._redo:
            return None
        stroke = self._redo.pop()
        self._undo.append(stroke)
        return stroke

    def clear(self) -> None:
        """Discard both stacks, for example when the base field is replaced."""
        self._undo.clear()
        self._redo.clear()
