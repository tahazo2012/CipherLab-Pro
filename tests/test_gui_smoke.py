"""Headless GUI smoke tests (Qt 'offscreen' platform). Skipped if PySide6 is unavailable."""
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from src.core.history_manager import HistoryManager  # noqa: E402
from src.core.settings import Settings  # noqa: E402
from src.gui.context import AppContext  # noqa: E402
from src.gui.main_window import MainWindow  # noqa: E402
from src.gui.theme import DARK_QSS  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(DARK_QSS)
    return a


@pytest.fixture
def win(app, tmp_path):
    s = Settings(pbkdf2_iterations=100_000)
    w = MainWindow(AppContext(s, HistoryManager(tmp_path / "h.db")))
    yield w
    w.close()


def wait_idle(app, win, timeout=15.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if not win.ctx.runner.busy:
            app.processEvents()
            return
        time.sleep(0.01)
    raise TimeoutError("background task did not finish")


def tab(win, cls):
    return next(t for t in win.all_tabs if isinstance(t, cls))


def test_all_twelve_tabs_exist(win):
    assert [win.tabs.tabText(i) for i in range(win.tabs.count())] == [
        "Encode", "Decode", "Encrypt", "Decrypt", "XOR Encoder", "XOR Decoder", "Hex Analyzer", "XOR Analyzer", "Compare Results", "History", "About", "Settings"]


def test_encode_decode_persian(win):
    from src.gui.decode_tab import DecodeTab
    from src.gui.encode_tab import EncodeTab
    enc, dec = tab(win, EncodeTab), tab(win, DecodeTab)
    enc.input.set_text("سلام دنیا 😀")
    enc.fmt.setCurrentIndex(1)  # Base64
    enc.run()
    encoded = enc.output.text()
    assert encoded and enc.error_label.isHidden()
    dec.fmt.setCurrentIndex(1)
    dec.input.set_text(encoded)
    dec.run()
    assert dec.output.text() == "سلام دنیا 😀"


def test_invalid_input_shows_error_not_crash(win):
    from src.gui.decode_tab import DecodeTab
    dec = tab(win, DecodeTab)
    dec.input.set_text("zz")
    dec.run()
    assert not dec.error_label.isHidden() and "hexadecimal" in dec.error_label.text().lower()


def test_encrypt_decrypt_round_trip_and_history_privacy(app, win, tmp_path):
    from src.gui.decrypt_tab import DecryptTab
    from src.gui.encrypt_tab import EncryptTab
    enc, dec = tab(win, EncryptTab), tab(win, DecryptTab)
    enc.input.set_text("پیام محرمانه 🔐")
    enc.password.setText("hunter2-پسورد")
    enc.run()
    assert enc.password.text() == ""  # cleared after use (default setting)
    wait_idle(app, win)
    envelope = enc.output.text()
    assert '"CipherLabPro"' in envelope
    dec.input.set_text(envelope)
    dec.password.setText("wrong")
    dec.run()
    wait_idle(app, win)
    assert not dec.error_label.isHidden()
    dec.password.setText("hunter2-پسورد")
    dec.run()
    wait_idle(app, win)
    assert dec.output.text() == "پیام محرمانه 🔐"
    blob = b"".join(p.read_bytes() for p in tmp_path.iterdir())
    assert b"hunter2" not in blob and "پیام".encode() not in blob


def test_hex_analyzer_worker_and_compare(app, win):
    from src.gui.hex_analyzer_tab import HexAnalyzerTab
    t = tab(win, HexAnalyzerTab)
    t.input.set_text("dcdcdcd324ad81ad8254dcdbddfcdcc7dcde24ad81af88acb0af88")
    t.repeat.setChecked(True)
    t.run()
    wait_idle(app, win)
    assert "INCONCLUSIVE" in t.summary.toPlainText()
    t.view.table.selectRow(0)
    t.view._send(True)
    assert len(win.compare_tab.candidates) == 1 and win.compare_tab.table.columnCount() == 1


def test_hex_analyzer_invalid_and_odd(app, win):
    from src.gui.hex_analyzer_tab import HexAnalyzerTab
    t = tab(win, HexAnalyzerTab)
    for bad, msg in (("abc", "odd number"), ("", "empty"), ("xyz!", "invalid")):
        t.input.set_text(bad)
        t.run()
        wait_idle(app, win)
        assert msg in t.error_label.text().lower()


def test_xor_analyzer_tab(app, win):
    from src.core.xor_tools import xor_repeating
    from src.gui.xor_analyzer_tab import XorAnalyzerTab
    t = tab(win, XorAnalyzerTab)
    plain = b"Offline analysis tools must stay honest about what they can and cannot prove."
    t.input.set_text(xor_repeating(plain, b"\x21").hex())
    t.run()
    wait_idle(app, win)
    assert t.view.candidates and t.view.candidates[0].output == plain


def test_about_tab_is_english_and_credits_developer(win):
    from src.gui.about_tab import AboutTab
    t = tab(win, AboutTab)
    labels = [w.text() for w in t.findChildren(__import__("PySide6.QtWidgets", fromlist=["QLabel"]).QLabel)]
    assert any("IRAN" in s and "SHIRAZ" in s for s in labels) and "TAHA ZOHRABI" in labels
    text = t.browser.toPlainText() + " ".join(labels)
    assert "Taha Zohrabi" in text and "Shiraz, Iran" in text
    assert not any("\u0600" <= ch <= "\u06ff" for ch in text), "About page must be English only"
    for section in ("Overview", "Quick Start", "Keyboard Shortcuts", "Troubleshooting", "Security Notes"):
        assert section in text
