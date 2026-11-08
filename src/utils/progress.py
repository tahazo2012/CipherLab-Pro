"""Tiny helpers for progress reporting and cooperative cancellation."""
from __future__ import annotations

from typing import Callable, Optional

ProgressCallback = Callable[[int, str], None]
CancelCheck = Callable[[], bool]


class OperationCancelled(Exception):
    """Raised when the user cancels a long-running local operation."""


def check_cancel(cancel: Optional[CancelCheck]) -> None:
    if cancel is not None and cancel():
        raise OperationCancelled("Operation cancelled by user.")


def report(progress: Optional[ProgressCallback], percent: int, message: str) -> None:
    if progress is not None:
        progress(percent, message)
