"""Backward-compatible re-export of the shared cancellation primitive.

The implementation lives in :mod:`clayfield.core.cancellation` so leaf modules
do not import the application layer. New code should import from there.
"""

from clayfield.core.cancellation import WorkerCancelled, check_cancelled

__all__ = ["WorkerCancelled", "check_cancelled"]
