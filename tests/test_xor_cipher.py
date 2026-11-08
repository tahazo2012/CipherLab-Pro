"""XOR Encoder / Decoder with custom HEX passwords (core logic + GUI tabs)."""
import os
import random

import pytest

from src.core.xor_cipher import (XorCipherError, decrypt_hex, encrypt_text, parse_hex_data, parse_hex_password)

TEXTS = {
    "english": "Hello, world! The quick brown fox jumps over the lazy dog.",
    "persian": "سلام دنیا! این یک آزمایش رمزنگاری با کلید دلخواه است.",
    "arabic": "مرحبا بالعالم، هذا اختبار للتشفير.",
    "chinese": "你好,世界!这是一个加密测试。",
    "russian": "Привет, мир! Это тест шифрования.",
    "emoji": "😀🚀🔐 family 👩‍💻👨‍👩‍👧 flags 🇮🇷🇺🇳",
    "mixed": "Taha طاها 😀 تست test 你好\nline2\t tab  trailing spaces   ",
    "nul_and_controls": "a\x00b\x01c\x7fd",
    "single_char": "x",
}

PASSWORDS = [
    "37", "0x37", "0X37", "ff", "00", "0x00",              # one byte, incl. all-zero key
    "474", "0x474", "0474", "1", "abc",                    # odd lengths (read as numbers)
    "0001", "000000", "0x00ff10", "00ff", "0x0000ffff",    # leading zeros preserved
    "DEADBEEF", "de ad be ef", "DE:AD:BE:EF", "de-ad-be-ef", "\\xde\\xad\\xbe\\xef", "0xde 0xad 0xbe 0xef",
    "a1b2c3d4e5f60718293a4b5c6d7e8f90",                    # 16 bytes
    "ab" * 64,                                            # 64 bytes
    "".join(random.Random(7).choice("0123456789abcdef") for _ in range(2048)),   # 1024-byte password
    "".join(random.Random(8).choice("0123456789ABCDEF") for _ in range(20_000)),  # 10 000-byte password, no limit
]


def reference_xor(data: bytes, key: bytes) -> bytes:
    """Independent, obviously-correct implementation: byte i XOR key[i mod len(key)]."""
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


@pytest.mark.parametrize("text_name", list(TEXTS))
@pytest.mark.parametrize("password", PASSWORDS)
def test_round_trip_every_text_and_password(text_name, password):
    text = TEXTS[text_name]
    cipher = encrypt_text(text, password)
    result = decrypt_hex(cipher, password)
    assert result.text == text and result.utf8_error is None


@pytest.mark.parametrize("password", PASSWORDS)
def test_matches_independent_reference(password):
    text = TEXTS["mixed"]
    key = parse_hex_password(password).data
    expected = reference_xor(text.encode("utf-8"), key).hex(" ")
    assert encrypt_text(text, password) == expected


def test_known_vectors():
    assert encrypt_text("Hello", "0x37") == "7f 52 5b 5b 58"
    assert encrypt_text("Hello", "0x474") == "4c 11 68 18 6b"        # 0x474 = bytes 04 74
    assert encrypt_text("Hello", "0x0011") == "48 74 6c 7d 6f"       # leading zero byte kept
    assert encrypt_text("Hi", "00") == "48 69"                       # zero key leaves data unchanged
    assert encrypt_text("Hi", "ffff") == "b7 96"


def test_whole_password_is_used_and_longer_than_data():
    pw = "0102030405060708090a0b0c0d0e0f10"
    out = encrypt_text("Hi", pw, separator="")
    assert out == bytes(b ^ k for b, k in zip(b"Hi", bytes.fromhex(pw))).hex()   # uses key[0], key[1] only
    long_text = "x" * 1000
    assert decrypt_hex(encrypt_text(long_text, pw), pw).text == long_text
    # every byte of the password influences the result
    base = encrypt_text("A" * 16, "00" * 16)
    for i in range(16):
        key = bytearray(16)
        key[i] = 1
        assert encrypt_text("A" * 16, key.hex()) != base


def test_leading_zeros_are_preserved_not_dropped():
    assert parse_hex_password("0001").data == b"\x00\x01"
    assert parse_hex_password("000000").data == b"\x00\x00\x00"
    assert parse_hex_password("0x0000").data == b"\x00\x00"
    assert encrypt_text("ABCD", "0001") != encrypt_text("ABCD", "01")
    assert encrypt_text("ABCD", "0001") == "41 43 43 45"      # 41^00 42^01 43^00 44^01
    assert encrypt_text("ABCD", "01") == "40 43 42 45"


def test_password_is_never_modified_or_truncated():
    p = parse_hex_password("  0xAB cd:EF  ")
    assert p.digits == "ABcdEF" and p.data == bytes.fromhex("abcdef") and not p.padded
    odd = parse_hex_password("0x474")
    assert odd.data == b"\x04\x74" and odd.padded and odd.digits == "474"
    with pytest.raises(XorCipherError, match="odd"):
        parse_hex_password("0x474", strict_even=True)
    assert parse_hex_password("0474", strict_even=True).data == b"\x04\x74"
    big = "ab" * 100_000
    assert len(parse_hex_password(big).data) == 100_000


def test_prefix_is_optional_and_case_insensitive():
    for pw in ("a1b2c3", "0xa1b2c3", "0XA1B2C3", "0xA1B2C3"):
        assert parse_hex_password(pw).data == bytes.fromhex("a1b2c3")


def test_output_format_options_and_decoder_accepts_all():
    text, pw = TEXTS["persian"], "0x00A1b2"
    spaced = encrypt_text(text, pw)
    cont = encrypt_text(text, pw, separator="")
    upper = encrypt_text(text, pw, separator="", upper=True)
    assert " " in spaced and " " not in cont and upper == cont.upper()
    for variant in (spaced, cont, upper, "0x" + cont, spaced.replace(" ", ":")):
        assert decrypt_hex(variant, pw).text == text


def test_wrong_password_gives_other_bytes_never_the_plaintext():
    text = TEXTS["english"]
    cipher = encrypt_text(text, "a1b2c3")
    for wrong in ("a1b2c4", "a1b2", "0000a1b2c3", "b2c3a1"):
        res = decrypt_hex(cipher, wrong)
        assert res.text != text
        assert res.data != text.encode()


def test_non_utf8_result_keeps_raw_bytes_and_reports_clearly():
    res = decrypt_hex("ff fe fd", "00")
    assert res.text is None and res.data == b"\xff\xfe\xfd" and "not valid UTF-8" in res.utf8_error


@pytest.mark.parametrize("bad,match", [
    ("", "empty"), ("   ", "empty"), ("0x", "empty"), ("0X ", "empty"), (" : - ", "empty"),
    ("xyz", "invalid hexadecimal"), ("12g4", "invalid hexadecimal"), ("0xGG", "invalid hexadecimal"),
    ("a1 b2 c!", "invalid hexadecimal"), ("۱۲۳۴", "keyboard"), ("اب", "keyboard"), ("12\u200b34", "invalid hexadecimal"),
])
def test_invalid_passwords_are_rejected_safely(bad, match):
    with pytest.raises(XorCipherError, match=match):
        parse_hex_password(bad)
    with pytest.raises(XorCipherError):
        encrypt_text("text", bad)
    with pytest.raises(XorCipherError):
        decrypt_hex("00ff", bad)


def test_invalid_text_and_data_inputs():
    with pytest.raises(XorCipherError, match="Plaintext is empty"):
        encrypt_text("", "37")
    with pytest.raises(XorCipherError, match="empty"):
        decrypt_hex("", "37")
    with pytest.raises(XorCipherError, match="odd number"):
        decrypt_hex("abc", "37")
    with pytest.raises(XorCipherError, match="invalid hexadecimal"):
        decrypt_hex("zz", "37")
    with pytest.raises(XorCipherError, match="Unicode"):
        encrypt_text("bad \ud800 surrogate", "37")
    assert parse_hex_data("00 ff 10").hex() == "00ff10"


def test_large_data_round_trip():
    text = ("سلام 😀 hello " * 20_000)
    pw = "0x00" + "a1" * 300
    assert decrypt_hex(encrypt_text(text, pw), pw).text == text


def test_no_hardcoded_passwords_in_source():
    """No source file of the feature contains a hex-looking string literal that could be a built-in key."""
    import ast
    import pathlib
    import re
    root = pathlib.Path(__file__).resolve().parent.parent / "src"
    allowed = {"0123456789abcdefABCDEF"}                      # the alphabet used for validation
    for name in ("core/xor_cipher.py", "gui/xor_encoder_tab.py", "gui/xor_decoder_tab.py", "gui/xor_password.py"):
        tree = ast.parse((root / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value not in allowed:
                assert not re.fullmatch(r"(0[xX])?[0-9a-fA-F]{2,}", node.value), (name, node.value)
            if isinstance(node, ast.Constant) and isinstance(node.value, bytes):
                assert len(node.value) == 0, (name, node.value)


# ----------------------------------------------------------------------------- GUI
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from src.core.history_manager import HistoryManager  # noqa: E402
from src.core.settings import Settings  # noqa: E402
from src.gui.context import AppContext  # noqa: E402
from src.gui.main_window import MainWindow  # noqa: E402
from src.gui.xor_decoder_tab import XorDecoderTab  # noqa: E402
from src.gui.xor_encoder_tab import XorEncoderTab  # noqa: E402


def _destroy(w, app):
    """Close AND delete the window: a leaked window makes every later stylesheet change slower."""
    from PySide6.QtCore import QEvent
    w.apply_language("en")
    w.apply_theme("blue")
    w.close()
    w.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture
def win(tmp_path, monkeypatch):
    monkeypatch.setenv("CIPHERLAB_DATA_DIR", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    w = MainWindow(AppContext(Settings(pbkdf2_iterations=100_000), HistoryManager(tmp_path / "h.db")))
    yield w, app, tmp_path
    _destroy(w, app)


@pytest.fixture(scope="module")
def shared_win(tmp_path_factory):
    """One window for the many parametrized round trips (state is reset by each test)."""
    tmp = tmp_path_factory.mktemp("xor_shared")
    os.environ["CIPHERLAB_DATA_DIR"] = str(tmp)
    app = QApplication.instance() or QApplication([])
    w = MainWindow(AppContext(Settings(pbkdf2_iterations=100_000), HistoryManager(tmp / "h.db")))
    w._keep_alive = True
    yield w
    w._keep_alive = False
    _destroy(w, app)


def tabs_of(w):
    enc = next(t for t in w.all_tabs if isinstance(t, XorEncoderTab))
    dec = next(t for t in w.all_tabs if isinstance(t, XorDecoderTab))
    return enc, dec


def test_both_tabs_exist_and_old_features_remain(win):
    w, _, _ = win
    names = [w.tabs.tabText(i) for i in range(w.tabs.count())]
    for old in ("Encode", "Decode", "Encrypt", "Decrypt", "Hex Analyzer", "XOR Analyzer", "Compare Results", "History", "About", "Settings"):
        assert old in names
    assert "XOR Encoder" in names and "XOR Decoder" in names and len(names) == 12


@pytest.mark.parametrize("password", ["0x37", "0x474", "0001", "a1b2c3d4e5f6", "ab" * 200, "DE:AD:BE:EF"])
@pytest.mark.parametrize("text", [TEXTS["persian"], TEXTS["english"], TEXTS["emoji"], TEXTS["mixed"], TEXTS["chinese"]])
def test_gui_round_trip(shared_win, password, text):
    enc, dec = tabs_of(shared_win)
    enc.clear_all()
    dec.clear_all()
    enc.input.set_text(text)
    enc.pw.edit.setText(password)
    enc.run()
    assert enc.error_label.isHidden()
    hex_out = enc.output.text()
    dec.input.set_text(hex_out)
    dec.pw.edit.setText(password)
    dec.run()
    assert dec.error_label.isHidden() and dec.output.text() == text
    assert enc.pw.text() == password and dec.pw.text() == password      # the password was never changed or cleared


def test_gui_errors_are_shown_not_raised(win):
    w, _, _ = win
    enc, dec = tabs_of(w)
    enc.input.set_text("text")
    for pw in ("", "0x", "zz", "۱۲"):
        enc.pw.edit.setText(pw)
        enc.run()
        assert not enc.error_label.isHidden()
    enc.pw.edit.setText("37")
    enc.input.set_text("")
    enc.run()
    assert "empty" in enc.error_label.text().lower()
    dec.input.set_text("abc")
    dec.pw.edit.setText("37")
    dec.run()
    assert "odd number" in dec.error_label.text().lower()
    dec.input.set_text("ff fe")
    dec.pw.edit.setText("00")
    dec.run()
    assert "not valid UTF-8" in dec.error_label.text() and dec.output.text() == "ff fe"


def test_live_password_status_and_strict_mode(win):
    w, _, _ = win
    enc, _ = tabs_of(w)
    assert "Enter a HEX password" in enc.pw.status.text()
    enc.pw.edit.setText("0x474")
    assert "04 74" in enc.pw.status.text() and "leading 0" in enc.pw.status.text()
    enc.pw.strict_chk.setChecked(True)
    assert "odd" in enc.pw.status.text() and "strict" in enc.pw.status.text().lower()
    enc.pw.edit.setText("0001")
    assert "00 01" in enc.pw.status.text() and "2 byte" in enc.pw.status.text()
    enc.pw.edit.setText("0xZZ")
    assert enc.pw.status.text().startswith("⚠")


def test_output_options_clear_and_hide(win):
    from PySide6.QtWidgets import QLineEdit
    w, _, _ = win
    enc, _ = tabs_of(w)
    enc.input.set_text("Hi")
    enc.pw.edit.setText("ff")
    enc.sep.setCurrentIndex(1)
    enc.upper.setChecked(True)
    enc.run()
    assert enc.output.text() == "B796"
    enc.pw.hide_chk.setChecked(True)
    assert enc.pw.edit.echoMode() == QLineEdit.EchoMode.Password
    enc.clear_all()
    assert enc.input.text() == enc.output.text() == enc.pw.text() == ""


def test_history_never_stores_password_or_content(win):
    w, _, tmp = win
    enc, dec = tabs_of(w)
    enc.input.set_text("super secret متن 😀")
    enc.pw.edit.setText("c0ffee1234")
    enc.run()
    dec.input.set_text(enc.output.text())
    dec.pw.edit.setText("c0ffee1234")
    dec.run()
    blob = b"".join(p.read_bytes() for p in tmp.iterdir())
    assert b"c0ffee1234" not in blob.lower() and b"super secret" not in blob and "متن".encode() not in blob
    assert w.ctx.history.count() == 2


def test_works_in_other_languages_and_themes(win):
    w, _, _ = win
    enc, dec = tabs_of(w)
    for lang, title in (("fa", "رمزگذار XOR"), ("ar", "مرمّز XOR"), ("zh", "XOR 编码器"), ("ru", "XOR-шифратор")):
        w.apply_language(lang)
        assert enc.title == "XOR Encoder" and w.tabs.tabText(w.tabs.indexOf(enc)) == title
        enc.input.set_text(TEXTS["persian"])
        enc.pw.edit.setText("0x474")
        assert "04 74" in enc.pw.status.text()
        enc.run()
        dec.input.set_text(enc.output.text())
        dec.pw.edit.setText("0x474")
        dec.run()
        assert dec.output.text() == TEXTS["persian"]
    w.apply_language("en")
    w.apply_theme("green")
    enc.pw.edit.setText("zz")
    assert "#ff3b3b" in enc.pw.status.styleSheet()
    w.apply_theme("blue")
    assert "#ff6b6b" in enc.pw.status.styleSheet()
