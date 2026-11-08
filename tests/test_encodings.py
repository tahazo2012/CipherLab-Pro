import pytest

from src.core.encodings import (ByteFormat, EncodingError, bytes_to_text, convert, decode_to_bytes,
                                detect_formats, encode_bytes, text_to_bytes, unescape_unicode)

SAMPLES = ["Hello, world!", "سلام دنیا", "مرحبا بالعالم", "emoji 😀🚀 ok", 'quote " backslash \\ tab\t nl\n', "ünïcödé ß"]


@pytest.mark.parametrize("fmt", list(ByteFormat))
@pytest.mark.parametrize("text", SAMPLES)
def test_round_trip_all_formats(fmt, text):
    data = text.encode("utf-8")
    assert decode_to_bytes(encode_bytes(data, fmt), fmt) == data


@pytest.mark.parametrize("charset", ["UTF-8", "UTF-16 (with BOM)", "UTF-16 LE", "UTF-16 BE"])
def test_persian_charset_round_trip(charset):
    text = "سلام، این یک آزمون است 😀"
    assert bytes_to_text(text_to_bytes(text, charset), charset) == text


def test_ascii_rejects_persian_with_clear_message():
    with pytest.raises(EncodingError, match="cannot be represented in ASCII"):
        text_to_bytes("سلام", "ASCII")


def test_latin1_and_strict_decode_errors():
    assert bytes_to_text(text_to_bytes("café", "Latin-1"), "Latin-1") == "café"
    with pytest.raises(EncodingError, match="not valid UTF-8"):
        bytes_to_text(b"\xff\xfe\xfa", "UTF-8")
    assert "\ufffd" in bytes_to_text(b"\xff", "UTF-8", errors="replace")  # explicit lossy opt-in


@pytest.mark.parametrize("bad", ["zz", "12 3", "0g", "abc!"])
def test_invalid_hex(bad):
    with pytest.raises(EncodingError):
        decode_to_bytes(bad, ByteFormat.HEX)


def test_odd_length_hex_message():
    with pytest.raises(EncodingError, match="Odd number"):
        decode_to_bytes("abc", ByteFormat.HEX)


def test_hex_separators_and_prefixes():
    assert decode_to_bytes("0xDE 0xAD:be-ef", ByteFormat.HEX) == b"\xde\xad\xbe\xef"
    assert decode_to_bytes("\\xde\\xad", ByteFormat.HEX) == b"\xde\xad"


@pytest.mark.parametrize("fmt", list(ByteFormat))
def test_empty_input_rejected(fmt):
    if fmt is ByteFormat.JSON_STRING or fmt is ByteFormat.UNICODE_ESCAPE:
        assert decode_to_bytes("", fmt) == b""
    else:
        with pytest.raises(EncodingError):
            decode_to_bytes("", fmt)


@pytest.mark.parametrize("fmt,bad", [
    (ByteFormat.BASE64, "ab$d"), (ByteFormat.BASE64, "a"), (ByteFormat.URL, "100%"), (ByteFormat.URL, "%zz"),
    (ByteFormat.BINARY, "0101"), (ByteFormat.BINARY, "01010102"), (ByteFormat.DECIMAL, "256"),
    (ByteFormat.DECIMAL, "12 x"), (ByteFormat.UNICODE_ESCAPE, "\\u12"), (ByteFormat.UNICODE_ESCAPE, "\\ud800"),
    (ByteFormat.UNICODE_ESCAPE, "\\q"), (ByteFormat.JSON_STRING, 'unescaped " quote'),
])
def test_malformed_inputs(fmt, bad):
    with pytest.raises(EncodingError):
        decode_to_bytes(bad, fmt)


def test_surrogate_pair_and_escape_forms():
    assert unescape_unicode("\\ud83d\\ude00") == "😀"
    assert unescape_unicode("\\U0001F600\\x41\\n") == "😀A\n"
    assert encode_bytes("😀".encode(), ByteFormat.UNICODE_ESCAPE) == "\\ud83d\\ude00"


def test_base64_known_values_and_urlsafe():
    assert encode_bytes(b"Hello", ByteFormat.BASE64) == "SGVsbG8="
    assert decode_to_bytes("SGVsbG8", ByteFormat.BASE64) == b"Hello"  # missing padding tolerated
    assert decode_to_bytes("-_-_", ByteFormat.BASE64) == b"\xfb\xff\xbf"


def test_convert_preserves_bytes():
    assert convert("48 65 6c 6c 6f", ByteFormat.HEX, ByteFormat.BINARY).startswith("01001000")
    raw = bytes(range(256))
    assert convert(encode_bytes(raw, ByteFormat.HEX), ByteFormat.HEX, ByteFormat.DECIMAL).split()[255] == "255"


def test_detect_formats_reports_ambiguity():
    guesses = detect_formats("48656c6c6f")
    assert {g.fmt for g in guesses} >= {ByteFormat.HEX, ByteFormat.BASE64}
    assert all("ambiguous" in g.note for g in guesses)
    assert detect_formats("   ") == []
