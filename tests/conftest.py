"""Shared test housekeeping: destroy leftover Qt windows after every test.

A window that is only closed (not deleted) stays alive, and every later stylesheet change then has to re-style it,
so a long GUI test run would get slower and slower.
"""
import pytest


@pytest.fixture(autouse=True)
def _delete_leftover_qt_windows():
    yield
    try:
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QApplication
    except ImportError:  # GUI tests are skipped without PySide6
        return
    app = QApplication.instance()
    if app is None:
        return
    for widget in app.topLevelWidgets():
        if getattr(widget, "_keep_alive", False):   # owned by a module-scoped fixture
            continue
        widget.close()
        widget.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
