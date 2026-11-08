"""Language switching (English, Persian, Arabic, Chinese) - headless Qt tests."""
import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from src.core.history_manager import HistoryManager  # noqa: E402
from src.core.settings import Settings  # noqa: E402
from src.gui import i18n  # noqa: E402
from src.gui.context import AppContext  # noqa: E402
from src.gui.main_window import MainWindow  # noqa: E402
from src.gui.theme import DARK_QSS  # noqa: E402


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(DARK_QSS)
    yield a
    a.setLayoutDirection(Qt.LayoutDirection.LeftToRight)


@pytest.fixture
def win(app, tmp_path, monkeypatch):
    monkeypatch.setenv("CIPHERLAB_DATA_DIR", str(tmp_path))
    w = MainWindow(AppContext(Settings(pbkdf2_iterations=100_000), HistoryManager(tmp_path / "h.db")))
    yield w
    w.apply_language("en")
    w.close()


def tabs(w):
    return [w.tabs.tabText(i) for i in range(w.tabs.count())]


def test_table_is_complete():
    assert set(i18n._TABLE["ru"]) == i18n.known_sources()   # Russian covers every string
    for lang in ("fa", "ar", "zh", "ru"):
        for en in i18n.known_sources():
            out = i18n.translate(en, lang)
            assert out and out != en, (lang, en)
    # templates keep their placeholders
    for lang in ("fa", "ar", "zh", "ru"):
        assert "{c}" in i18n.translate("Input: {c} chars · {b} bytes", lang)
        assert "{b}" in i18n.translate("{c} chars · {b} bytes (UTF-8)", lang)


def test_translate_basics():
    assert i18n.translate("Encrypt", "en") == "Encrypt"
    assert i18n.translate("Encrypt", "fa") == "رمزنگاری"
    assert i18n.translate("Encrypt", "ar") == "تشفير"
    assert i18n.translate("Encrypt", "zh") == "加密"
    assert i18n.translate("Encrypt", "ru") == "Шифрование"
    assert i18n.translate("&File", "zh") == "文件"
    assert i18n.translate("&File", "ru") == "Файл"
    assert i18n.translate("max key length ", "zh") == "最大密钥长度 "   # keeps trailing space
    assert i18n.translate("Unknown technical text", "fa") == "Unknown technical text"
    assert i18n.translate("Run (x)", "fa") == "Run (x)"


def test_every_ui_text_is_translated_or_technical(win):
    technical = {"#", "ASCII", "Base64", "Latin-1", "UTF-8", "UTF-16 (with BOM)", "UTF-16 BE", "UTF-16 LE", "English",
                 "فارسی", "العربية", "中文", "Русский", "IRAN  ·  SHIRAZ", "TAHA ZOHRABI", "Programmer", " MB"}
    dynamic_prefixes = ("<b>Data folder", "Stored locally", "Input: 0", "CipherLab Pro  v", "Optional JSON", "e.g. ",
                        "dcdcdc")
    missing = [s for s in i18n.english_sources(win)
               if i18n.translate(s, "fa") == s and s not in technical and not s.startswith(dynamic_prefixes)]
    assert not missing, missing


def test_switch_languages_and_back(app, win):
    assert tabs(win)[2] == "Encrypt"
    win.apply_language("fa")
    assert tabs(win)[:4] == ["کدگذاری", "کدگشایی", "رمزنگاری", "رمزگشایی"]
    assert app.layoutDirection() == Qt.LayoutDirection.RightToLeft
    win.apply_language("ar")
    assert tabs(win)[2] == "تشفير" and app.layoutDirection() == Qt.LayoutDirection.RightToLeft
    win.apply_language("zh")
    assert tabs(win)[:4] == ["编码", "解码", "加密", "解密"] and app.layoutDirection() == Qt.LayoutDirection.LeftToRight
    assert win.menuBar().actions()[0].text() == "文件"
    win.apply_language("ru")
    assert tabs(win)[:4] == ["Кодирование", "Декодирование", "Шифрование", "Расшифровка"]
    assert app.layoutDirection() == Qt.LayoutDirection.LeftToRight
    win.apply_language("en")
    assert tabs(win)[2] == "Encrypt" and win.menuBar().actions()[0].text() == "&File"
    assert win.windowTitle() == "CipherLab Pro — offline"


def test_widgets_texts_restore_exactly(win):
    before = sorted(i18n.english_sources(win))
    for lang in ("fa", "ar", "zh", "ru", "fa", "en"):
        win.apply_language(lang)
    after = sorted(i18n.english_sources(win))
    # only the dynamic status/counter labels may differ
    diff = set(before) ^ set(after)
    assert all(d.startswith(("Input:", "Ready")) or d.endswith("bytes") for d in diff), diff


def test_app_still_works_in_other_languages(app, win):
    from src.gui.decode_tab import DecodeTab
    from src.gui.encode_tab import EncodeTab
    win.apply_language("fa")
    enc = next(t for t in win.all_tabs if isinstance(t, EncodeTab))
    dec = next(t for t in win.all_tabs if isinstance(t, DecodeTab))
    enc.input.set_text("سلام")
    enc.run()
    assert enc.output.text() == "d8 b3 d9 84 d8 a7 d9 85"
    assert "نویسه" in enc.input.count_label.text()        # counters follow the language
    dec.fmt.setCurrentIndex(0)
    dec.input.set_text("d8 b3 d9 84 d8 a7 d9 85")
    dec.charset.setCurrentIndex(dec.charset.count() - 1)   # "raw bytes as hex" must still work when translated
    dec.run()
    assert dec.output.text() == "d8 b3 d9 84 d8 a7 d9 85"
    dec.charset.setCurrentIndex(0)
    dec.run()
    assert dec.output.text() == "سلام"


def test_language_setting_persists_and_applies(app, win, tmp_path):
    from src.gui.settings_dialog import SettingsTab
    st = next(t for t in win.all_tabs if isinstance(t, SettingsTab))
    st.lang.setCurrentIndex(st.lang.findData("zh"))
    assert win.tabs.tabText(2) == "加密"
    assert Settings.load(tmp_path / "settings.json").language == "zh"
    st.lang.setCurrentIndex(st.lang.findData("en"))
    assert win.tabs.tabText(2) == "Encrypt"


def test_invalid_language_in_settings_falls_back(tmp_path):
    s = Settings(language="xx")
    s.save(tmp_path / "s.json")
    assert Settings.load(tmp_path / "s.json").language == "en"


def test_russian_selectable_in_settings_and_persisted(app, win, tmp_path):
    from src.gui.settings_dialog import SettingsTab
    st = next(t for t in win.all_tabs if isinstance(t, SettingsTab))
    st.lang.setCurrentIndex(st.lang.findData("ru"))
    assert win.tabs.tabText(2) == "Шифрование"
    assert Settings.load(tmp_path / "settings.json").language == "ru"
    assert "симв." in win.counts_label.text()
