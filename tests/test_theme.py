"""Blue / green theme switching."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from src.core.history_manager import HistoryManager  # noqa: E402
from src.core.settings import Settings  # noqa: E402
from src.gui import theme  # noqa: E402
from src.gui.context import AppContext  # noqa: E402
from src.gui.main_window import MainWindow  # noqa: E402


def test_stylesheets_use_their_own_palette():
    blue, green = theme.stylesheet("blue"), theme.stylesheet("green")
    assert blue != green
    assert theme.palette("blue")["BG"] in blue and theme.palette("blue")["BG"] not in green
    assert theme.palette("green")["BG"] in green and theme.palette("green")["ACCENT"] in green
    assert theme.DARK_QSS == blue                       # backwards-compatible constant
    assert "{{" not in blue and "{BG}" not in blue      # f-string fully rendered


def test_set_current_falls_back_to_blue():
    try:
        assert theme.set_current("green") == "green" and theme.palette()["BG"] == "#000000"
        assert theme.set_current("purple") == "blue" and theme.palette()["BG"] == "#14171c"
        assert theme.ui_families("green")[0] == "Cascadia Mono" and theme.ui_families("blue")[0] == "Segoe UI"
    finally:
        theme.set_current("blue")


def test_theme_setting_defaults_and_clamps(tmp_path):
    assert Settings().theme == "blue"
    Settings(theme="rainbow").save(tmp_path / "s.json")
    assert Settings.load(tmp_path / "s.json").theme == "blue"
    Settings(theme="green").save(tmp_path / "s.json")
    assert Settings.load(tmp_path / "s.json").theme == "green"


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("CIPHERLAB_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    w = MainWindow(AppContext(Settings(pbkdf2_iterations=100_000), HistoryManager(tmp_path / "h.db")))
    yield w, app
    w.apply_theme("blue")
    w.close()


def test_switch_from_settings_applies_and_persists(win, tmp_path):
    from src.gui.about_tab import AboutTab
    from src.gui.settings_dialog import SettingsTab
    w, app = win
    st = next(t for t in w.all_tabs if isinstance(t, SettingsTab))
    about = next(t for t in w.all_tabs if isinstance(t, AboutTab))
    assert theme.palette("blue")["BG"] in app.styleSheet()
    st.theme.setCurrentIndex(st.theme.findData("green"))
    assert theme.palette("green")["BG"] in app.styleSheet() and theme.palette("blue")["BG"] not in app.styleSheet()
    assert theme.palette("green")["OK"] in w.offline_label.styleSheet()
    assert theme.palette("green")["ACCENT"] in about.place.styleSheet()
    assert Settings.load(tmp_path / "settings.json").theme == "green"
    st.theme.setCurrentIndex(st.theme.findData("blue"))
    assert theme.palette("blue")["BG"] in app.styleSheet()
    assert theme.palette("blue")["ACCENT"] in about.name.styleSheet()
    assert Settings.load(tmp_path / "settings.json").theme == "blue"


def test_saved_theme_is_applied_at_startup(tmp_path, monkeypatch):
    monkeypatch.setenv("CIPHERLAB_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    w = MainWindow(AppContext(Settings(theme="green", pbkdf2_iterations=100_000), HistoryManager(tmp_path / "h.db")))
    try:
        assert theme.current() == "green" and theme.palette("green")["BG"] in app.styleSheet()
    finally:
        w.apply_theme("blue")
        w.close()


def test_theme_and_language_work_together(win):
    w, app = win
    w.apply_language("fa")
    w.apply_theme("green")
    assert w.tabs.tabText(2) == "رمزنگاری" and theme.palette("green")["BG"] in app.styleSheet()
    w.apply_language("en")
    assert w.tabs.tabText(2) == "Encrypt"


def test_candidate_colors_follow_theme(win):
    from src.core.hex_analyzer import analyze_bytes
    from src.gui.widgets import CandidateView
    w, _ = win
    view = w.findChildren(CandidateView)[0]
    view.set_candidates(analyze_bytes(b"Plain readable English text for scoring.").candidates)
    w.apply_theme("green")
    assert view.table.rowCount() > 0
    assert view.table.item(0, 3).foreground().color().name() in {theme.palette("green")[k] for k in ("OK", "WARN", "MUTED", "ERR")}
