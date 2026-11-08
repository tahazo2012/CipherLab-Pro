"""CipherLab Pro entry point. Fully offline: no network access is needed or allowed."""
from __future__ import annotations

import sys
from pathlib import Path

from src.utils.offline_guard import install_offline_guard

APP_ID = "CipherLabPro.Desktop.1"


def resource_path(name: str) -> Path:
    """Locate a bundled file (works from source and from a PyInstaller build)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def set_windows_app_id() -> None:
    """Lets Windows show our own icon on the taskbar instead of grouping under python.exe."""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except (AttributeError, OSError):
            pass


def main() -> int:
    install_offline_guard()  # blocks Python-level sockets before anything else runs
    set_windows_app_id()

    from PySide6.QtGui import QFont, QIcon
    from PySide6.QtWidgets import QApplication

    from src.core.history_manager import HistoryManager
    from src.core.settings import Settings, get_data_dir
    from src.gui.context import AppContext
    from src.gui.main_window import MainWindow
    from src.gui.theme import DARK_QSS, UI_FAMILIES
    from src.utils.logging_config import setup_logging

    data_dir = get_data_dir()
    setup_logging(data_dir)
    settings = Settings.load()
    history = HistoryManager(data_dir / "history.db", enabled=settings.history_enabled,
                             store_previews=settings.history_store_previews, max_records=settings.max_history_records)
    app = QApplication(sys.argv)
    app.setApplicationName("CipherLab Pro")
    app.setStyle("Fusion")
    font = QFont()
    font.setFamilies(UI_FAMILIES)
    font.setPointSize(10)
    app.setFont(font)
    app.setStyleSheet(DARK_QSS)
    icon_file = resource_path("icon.ico")
    icon = QIcon(str(icon_file)) if icon_file.exists() else QIcon()
    if not icon.isNull():
        app.setWindowIcon(icon)
    window = MainWindow(AppContext(settings, history))
    if not icon.isNull():
        window.setWindowIcon(icon)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
