"""Defence-in-depth guard that blocks Python-level network access.

The application never needs the network. ``install_offline_guard`` replaces the
common ``socket`` entry points with functions that raise ``OfflineViolation`` and
count attempts. It cannot stop native (C++) code, so it complements, and does not
replace, the architecture rule that no module imports a network library.
"""
from __future__ import annotations

import socket
from typing import Callable


class OfflineViolation(ConnectionError):
    """Raised when code tries to open a network connection."""


class _State:
    attempts = 0


def violation_count() -> int:
    return _State.attempts


def install_offline_guard() -> Callable[[], None]:
    """Block network calls; returns a function that restores the originals."""
    originals = {
        "socket.connect": socket.socket.connect,
        "socket.connect_ex": socket.socket.connect_ex,
        "create_connection": socket.create_connection,
        "getaddrinfo": socket.getaddrinfo,
        "gethostbyname": socket.gethostbyname,
    }

    def _blocked(*_a, **_k):
        _State.attempts += 1
        raise OfflineViolation("CipherLab Pro is offline-only: network access is blocked.")

    socket.socket.connect = _blocked  # type: ignore[method-assign]
    socket.socket.connect_ex = _blocked  # type: ignore[method-assign]
    socket.create_connection = _blocked  # type: ignore[assignment]
    socket.getaddrinfo = _blocked  # type: ignore[assignment]
    socket.gethostbyname = _blocked  # type: ignore[assignment]

    def restore() -> None:
        socket.socket.connect = originals["socket.connect"]  # type: ignore[method-assign]
        socket.socket.connect_ex = originals["socket.connect_ex"]  # type: ignore[method-assign]
        socket.create_connection = originals["create_connection"]  # type: ignore[assignment]
        socket.getaddrinfo = originals["getaddrinfo"]  # type: ignore[assignment]
        socket.gethostbyname = originals["gethostbyname"]  # type: ignore[assignment]

    return restore
