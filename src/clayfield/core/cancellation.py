"""Cooperative cancellation shared by GUI workers and CPU processing.

This lives in ``clayfield.core`` rather than ``clayfield.app`` so geometry,
field, image, and export modules can import a leaf primitive without reaching
up into the application layer. ``clayfield.app.cancellation`` re-exports these
names for existing callers.
"""


class WorkerCancelled(Exception):
    """Raised when a background operation is cancelled."""


def check_cancelled(cancel_check) -> None:
    if cancel_check is not None and cancel_check():
        raise WorkerCancelled()
