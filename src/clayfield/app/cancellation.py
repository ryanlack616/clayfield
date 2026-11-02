"""Cooperative cancellation shared by GUI workers and CPU processing."""


class WorkerCancelled(Exception):
    """Raised when a background operation is cancelled."""


def check_cancelled(cancel_check) -> None:
    if cancel_check is not None and cancel_check():
        raise WorkerCancelled()
