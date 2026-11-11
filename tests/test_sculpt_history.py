"""Stroke-level undo and redo for sculpt edits."""

import numpy as np
import pytest

from clayfield.sculpt.history import SculptEdit, SculptHistory, SculptStroke, apply_stroke

AFTER = [[1.0, 2.0], [3.0, 4.0]]


def _edit(after, before=None, row0=2, col0=3):
    """Build an edit whose base is zero: ``before`` is the untouched zero block."""
    block = np.asarray(AFTER, dtype=np.float32) if before is None else np.asarray(before, dtype=np.float32)
    base = np.zeros_like(block)
    return SculptEdit(
        row0=row0,
        row1=row0 + block.shape[0] - 1,
        col0=col0,
        col1=col0 + block.shape[1] - 1,
        before=base,
        after=block,
    )


def _state():
    heightfield = np.zeros((8, 8), dtype=np.float32)
    offsets = np.zeros((8, 8), dtype=np.float32)
    return heightfield, offsets


def test_undo_restores_the_before_values_and_offsets():
    heightfield, offsets = _state()
    edit = _edit(AFTER)
    stroke = SculptStroke((edit,))
    apply_stroke(heightfield, offsets, stroke, forward=True)
    np.testing.assert_array_equal(heightfield[edit.block_slice], edit.after)
    np.testing.assert_array_equal(offsets[edit.block_slice], edit.after)
    apply_stroke(heightfield, offsets, stroke, forward=False)
    np.testing.assert_array_equal(heightfield[edit.block_slice], edit.before)
    np.testing.assert_array_equal(offsets[edit.block_slice], 0.0)


def test_redo_restores_the_after_values_and_offsets():
    heightfield, offsets = _state()
    edit = _edit(AFTER)
    stroke = SculptStroke((edit,))
    apply_stroke(heightfield, offsets, stroke, forward=True)
    np.testing.assert_array_equal(heightfield[edit.block_slice], edit.after)
    np.testing.assert_array_equal(offsets[edit.block_slice], edit.after)


def test_undo_then_redo_round_trips():
    heightfield, offsets = _state()
    edit = _edit(AFTER)
    stroke = SculptStroke((edit,))
    apply_stroke(heightfield, offsets, stroke, forward=True)
    apply_stroke(heightfield, offsets, stroke, forward=False)
    apply_stroke(heightfield, offsets, stroke, forward=True)
    np.testing.assert_array_equal(heightfield[edit.block_slice], edit.after)
    np.testing.assert_array_equal(offsets[edit.block_slice], edit.after)


def test_apply_stroke_reverses_multiple_edits_in_order():
    heightfield, offsets = _state()
    first = _edit([[1.0, 1.0]], row0=1, col0=1)
    second = _edit([[2.0, 2.0]], row0=4, col0=4)
    stroke = SculptStroke((first, second))
    apply_stroke(heightfield, offsets, stroke, forward=True)
    np.testing.assert_array_equal(heightfield[first.block_slice], first.after)
    np.testing.assert_array_equal(heightfield[second.block_slice], second.after)
    apply_stroke(heightfield, offsets, stroke, forward=False)
    np.testing.assert_array_equal(heightfield[first.block_slice], first.before)
    np.testing.assert_array_equal(heightfield[second.block_slice], second.before)
    np.testing.assert_array_equal(offsets, 0.0)


def test_undo_reverses_overlapping_edits_without_leaving_intermediate_state():
    # Two dabs whose blocks overlap. The second edit's before state contains the
    # first edit's after values, so undo must replay in reverse or the earlier
    # before values get overwritten by the intermediate state.
    heightfield, offsets = _state()
    first = _edit([[1.0, 2.0], [3.0, 4.0]], row0=2, col0=2)
    second = _edit([[0.5, 1.5], [2.5, 3.5]], before=first.after, row0=2, col0=2)
    stroke = SculptStroke((first, second))
    apply_stroke(heightfield, offsets, stroke, forward=True)
    np.testing.assert_array_equal(heightfield[first.block_slice], second.after)
    apply_stroke(heightfield, offsets, stroke, forward=False)
    np.testing.assert_array_equal(heightfield[first.block_slice], 0.0)
    np.testing.assert_array_equal(offsets, 0.0)


def test_history_records_and_undoes_in_order():
    history = SculptHistory()
    first = SculptStroke((_edit([[1.0]], row0=0, col0=0),))
    second = SculptStroke((_edit([[2.0]], row0=1, col0=1),))
    history.record(first)
    history.record(second)
    assert history.can_undo
    assert history.undo() is second
    assert history.undo() is first
    assert history.undo() is None
    assert history.can_redo


def test_history_redo_restores_the_undone_stroke():
    history = SculptHistory()
    stroke = SculptStroke((_edit([[1.0]], row0=0, col0=0),))
    history.record(stroke)
    history.undo()
    assert history.redo() is stroke
    assert history.can_undo


def test_history_record_clears_the_redo_stack():
    history = SculptHistory()
    first = SculptStroke((_edit([[1.0]], row0=0, col0=0),))
    second = SculptStroke((_edit([[2.0]], row0=1, col0=1),))
    history.record(first)
    history.undo()
    history.record(second)
    assert not history.can_redo


def test_history_limit_drops_the_oldest_stroke():
    history = SculptHistory(limit=2)
    strokes = [SculptStroke((_edit([[float(index)]], row0=0, col0=0),)) for index in range(3)]
    for stroke in strokes:
        history.record(stroke)
    assert history.undo() is strokes[2]
    assert history.undo() is strokes[1]
    assert history.undo() is None


def test_history_clear_discards_both_stacks():
    history = SculptHistory()
    history.record(SculptStroke((_edit([[1.0]], row0=0, col0=0),)))
    history.undo()
    history.clear()
    assert not history.can_undo
    assert not history.can_redo


def test_empty_stroke_is_rejected():
    with pytest.raises(ValueError, match="at least one edit"):
        SculptStroke(())


def test_edit_rejects_mismatched_bounds_and_blocks():
    with pytest.raises(ValueError, match="inclusive and ordered"):
        SculptEdit(2, 1, 0, 0, np.zeros((1, 1), dtype=np.float32), np.zeros((1, 1), dtype=np.float32))
    with pytest.raises(ValueError, match="match the addressed region"):
        SculptEdit(0, 0, 0, 0, np.zeros((2, 2), dtype=np.float32), np.zeros((2, 2), dtype=np.float32))


def test_history_limit_must_be_positive():
    with pytest.raises(ValueError):
        SculptHistory(limit=0)
