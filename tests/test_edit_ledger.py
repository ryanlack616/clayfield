"""Ordering of parameter and sculpt actions for undo and redo."""

import pytest

from clayfield.app.history import PARAMETER_EDIT, SCULPT_EDIT, EditLedger


def test_empty_ledger_cannot_undo_or_redo():
    ledger = EditLedger()
    assert not ledger.can_undo
    assert not ledger.can_redo
    assert ledger.undo() is None
    assert ledger.redo() is None


def test_ledger_walks_actions_in_chronological_order():
    ledger = EditLedger()
    ledger.record(PARAMETER_EDIT)
    ledger.record(SCULPT_EDIT)
    ledger.record(PARAMETER_EDIT)
    assert ledger.undo() == PARAMETER_EDIT
    assert ledger.undo() == SCULPT_EDIT
    assert ledger.undo() == PARAMETER_EDIT
    assert ledger.undo() is None
    assert ledger.can_redo


def test_redo_replays_the_undone_actions_in_order():
    ledger = EditLedger()
    ledger.record(PARAMETER_EDIT)
    ledger.record(SCULPT_EDIT)
    ledger.undo()
    ledger.undo()
    assert ledger.redo() == PARAMETER_EDIT
    assert ledger.redo() == SCULPT_EDIT
    assert ledger.redo() is None
    assert ledger.can_undo


def test_recording_after_undo_drops_the_redo_tail():
    ledger = EditLedger()
    ledger.record(PARAMETER_EDIT)
    ledger.record(SCULPT_EDIT)
    ledger.undo()
    ledger.record(PARAMETER_EDIT)
    assert not ledger.can_redo
    assert ledger.undo() == PARAMETER_EDIT
    assert ledger.undo() == PARAMETER_EDIT


def test_discard_removes_one_kind_and_keeps_the_index_consistent():
    ledger = EditLedger()
    ledger.record(PARAMETER_EDIT)
    ledger.record(SCULPT_EDIT)
    ledger.record(SCULPT_EDIT)
    ledger.undo()
    # The undone sculpt action is dropped along with the applied one, leaving only
    # the parameter action and the index pointing past it.
    ledger.discard(SCULPT_EDIT)
    assert ledger.can_undo
    assert ledger.undo() == PARAMETER_EDIT
    assert ledger.undo() is None
    assert ledger.can_redo
    assert ledger.redo() == PARAMETER_EDIT


def test_discard_of_an_unrecorded_kind_is_a_no_op():
    ledger = EditLedger()
    ledger.record(PARAMETER_EDIT)
    ledger.discard(SCULPT_EDIT)
    assert ledger.can_undo


def test_drop_oldest_mirrors_a_trimmed_stack():
    ledger = EditLedger()
    for _ in range(3):
        ledger.record(PARAMETER_EDIT)
    ledger.drop_oldest(PARAMETER_EDIT)
    assert ledger.undo() == PARAMETER_EDIT
    assert ledger.undo() == PARAMETER_EDIT
    assert ledger.undo() is None


def test_drop_oldest_does_not_move_the_index_past_an_undone_action():
    ledger = EditLedger()
    ledger.record(PARAMETER_EDIT)
    ledger.record(PARAMETER_EDIT)
    ledger.undo()
    # One action is applied and one is undone; dropping the oldest (the applied
    # one) leaves the undone action in the redo stack.
    ledger.drop_oldest(PARAMETER_EDIT)
    assert not ledger.can_undo
    assert ledger.can_redo
    assert ledger.redo() == PARAMETER_EDIT


def test_clear_discards_both_directions():
    ledger = EditLedger()
    ledger.record(SCULPT_EDIT)
    ledger.undo()
    ledger.clear()
    assert not ledger.can_undo
    assert not ledger.can_redo


def test_unknown_edit_kind_is_rejected():
    ledger = EditLedger()
    with pytest.raises(ValueError, match="Unknown edit kind"):
        ledger.record("flatten")
