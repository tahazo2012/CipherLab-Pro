"""Local encoders/decoders: charsets plus Hex, Base64, URL, Unicode/JSON escapes, binary, decimal.

All functions are strict by default and raise ``EncodingError`` with an explanation
instead of silently dropping or replacing data.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import quote_from_bytes, unquote_to_bytes

from src.utils.validation import ValidationError, hex_to_bytes, normalize_hex


class EncodingError(ValueError):
    """Raised when text/bytes cannot be converted; the message explains why."""


class ByteFormat(str, Enum):
    HEX = "Hexadecimal"
    BASE64 = "Base64"
    URL = "URL (percent) encoding"
    UNICODE_ESCAPE = "Unicode escape (\\uXXXX)"
    JSON_STRING = "JSON string escape"
    BINARY = "Binary (8-bit groups)"
    DECIMAL = "Decimal bytes"


TEXT_CHARSETS: dict[str, str] = {
    "UTF-8": "utf-8",
    "UTF-16 (with BOM)": "utf-16",
    "UTF-16 LE": "utf-16-le",
    "UTF-16 BE": "utf-16-be",
    "ASCII": "ascii",
    "Latin-1": "latin-1",
}


def _codec(charset: str) -> str:
    try:
        return TEXT_CHARSETS[charset]
    except KeyError:
        raise EncodingError(f"Unsupported text encoding: {charset!r}.") from None


def text_to_bytes(text: str, charset: str = "UTF-8") -> bytes:
    codec = _codec(charset)
    try:
        return text.encode(codec)
    except UnicodeEncodeError as exc:
        ch = text[exc.start]
        raise EncodingError(
            f"Character {ch!r} (U+{ord(ch):04X}) at position {exc.start + 1} cannot be "
            f"represented in {charset}. Choose UTF-8 (or another Unicode encoding)."
        ) from exc


def bytes_to_text(data: bytes, charset: str = "UTF-8", errors: str = "strict") -> str:
    """Decode bytes; ``errors='replace'`` is an explicit, lossy opt-in."""
    codec = _codec(charset)
    if errors not in ("strict", "replace"):
        raise EncodingError("errors must be 'strict' or 'replace'.")
    try:
        return data.decode(codec, errors)
    except UnicodeDecodeError as exc:
        where = f"0x{data[exc.start]:02X} at offset {exc.start}" if exc.start < len(data) else f"end of data (offset {exc.start})"
        raise EncodingError(f"Bytes are not valid {charset}: problem at byte {where} ({exc.reason}).") from exc


def count_decode_errors(data: bytes, charset: str = "UTF-8") -> int:
    """Number of U+FFFD characters produced by lossy decoding (approximate invalid-sequence count)."""
    return data.decode(_codec(charset), "replace").count("\ufffd")


# ---------------------------------------------------------------- escapes
_SIMPLE_ESC = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "\\": "\\", "'": "'", '"': '"', "/": "/", "0": "\0"}
_HEXD = frozenset("0123456789abcdefABCDEF")


def escape_unicode(text: str) -> str:
    parts: list[str] = []
    for ch in text:
        cp = ord(ch)
        if ch == "\\":
            parts.append("\\\\")
        elif ch == "\n":
            parts.append("\\n")
        elif ch == "\r":
            parts.append("\\r")
        elif ch == "\t":
            parts.append("\\t")
        elif 0x20 <= cp < 0x7F:
            parts.append(ch)
        elif cp <= 0xFFFF:
            parts.append(f"\\u{cp:04x}")
        else:
            v = cp - 0x10000
            parts.append(f"\\u{0xD800 + (v >> 10):04x}\\u{0xDC00 + (v & 0x3FF):04x}")
    return "".join(parts)


def unescape_unicode(s: str) -> str:
    """Parse \\uXXXX, \\UXXXXXXXX, \\xHH (code point) and simple escapes; joins surrogate pairs."""
    cps: list[int] = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c != "\\":
            cps.append(ord(c))
            i += 1
            continue
        if i + 1 >= n:
            raise EncodingError("Dangling backslash at the end of the input.")
        k = s[i + 1]
        width = {"u": 4, "U": 8, "x": 2}.get(k)
        if width:
            part = s[i + 2:i + 2 + width]
            if len(part) != width or not all(h in _HEXD for h in part):
                raise EncodingError(f"Incomplete or invalid \\{k} escape at position {i + 1}: expected {width} hex digits.")
            cps.append(int(part, 16))
            i += 2 + width
        elif k in _SIMPLE_ESC:
            cps.append(ord(_SIMPLE_ESC[k]))
            i += 2
        else:
            raise EncodingError(f"Unknown escape sequence '\\{k}' at position {i + 1}.")
    out: list[str] = []
    j = 0
    while j < len(cps):
        cp = cps[j]
        if 0xD800 <= cp <= 0xDBFF:
            if j + 1 < len(cps) and 0xDC00 <= cps[j + 1] <= 0xDFFF:
                out.append(chr(0x10000 + ((cp - 0xD800) << 10) + (cps[j + 1] - 0xDC00)))
                j += 2
                continue
            raise EncodingError("Unpaired high surrogate escape (\\ud800-\\udbff) is not valid Unicode text.")
        if 0xDC00 <= cp <= 0xDFFF:
            raise EncodingError("Unpaired low surrogate escape (\\udc00-\\udfff) is not valid Unicode text.")
        if cp > 0x10FFFF:
            raise EncodingError(f"Code point U+{cp:X} is beyond U+10FFFF.")
        out.append(chr(cp))
        j += 1
    return "".join(out)


# ---------------------------------------------------------------- byte formats
def encode_bytes(data: bytes, fmt: ByteFormat, *, hex_sep: str = " ", upper: bool = False,
                 text_charset: str = "UTF-8") -> str:
    """Represent ``data`` in ``fmt``. Escape formats need ``data`` to be valid text in ``text_charset``."""
    if fmt is ByteFormat.HEX:
        out = data.hex(hex_sep) if hex_sep else data.hex()
        return out.upper() if upper else out
    if fmt is ByteFormat.BASE64:
        return base64.b64encode(data).decode("ascii")
    if fmt is ByteFormat.URL:
        return quote_from_bytes(data, safe="")
    if fmt is ByteFormat.BINARY:
        return " ".join(f"{b:08b}" for b in data)
    if fmt is ByteFormat.DECIMAL:
        return " ".join(str(b) for b in data)
    if fmt in (ByteFormat.UNICODE_ESCAPE, ByteFormat.JSON_STRING):
        text = bytes_to_text(data, text_charset)
        if fmt is ByteFormat.UNICODE_ESCAPE:
            return escape_unicode(text)
        return json.dumps(text, ensure_ascii=False)[1:-1]
    raise EncodingError(f"Unsupported format: {fmt}")


def decode_to_bytes(s: str, fmt: ByteFormat) -> bytes:
    """Parse ``s`` written in ``fmt`` into the exact original bytes."""
    try:
        return _decode_to_bytes(s, fmt)
    except ValidationError as exc:
        raise EncodingError(str(exc)) from exc


def _decode_to_bytes(s: str, fmt: ByteFormat) -> bytes:
    if fmt is ByteFormat.HEX:
        return hex_to_bytes(s)
    if fmt is ByteFormat.BASE64:
        cleaned = "".join(s.split())
        if not cleaned:
            raise EncodingError("Input is empty.")
        bad = re.search(r"[^A-Za-z0-9+/\-_=]", cleaned)
        if bad:
            raise EncodingError(f"Invalid Base64 character {bad.group()!r} at position {bad.start() + 1}.")
        urlsafe = ("-" in cleaned or "_" in cleaned) and "+" not in cleaned and "/" not in cleaned
        body = cleaned.rstrip("=")
        if "=" in body:
            raise EncodingError("Base64 padding ('=') may only appear at the end.")
        if len(body) % 4 == 1:
            raise EncodingError("Invalid Base64 length: a single trailing character cannot encode a byte.")
        padded = body + "=" * (-len(body) % 4)
        try:
            if urlsafe:
                return base64.urlsafe_b64decode(padded)
            return base64.b64decode(padded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise EncodingError(f"Invalid Base64: {exc}") from exc
    if fmt is ByteFormat.URL:
        if not s:
            raise EncodingError("Input is empty.")
        bad = re.search(r"%(?![0-9A-Fa-f]{2})", s)
        if bad:
            raise EncodingError(f"Malformed percent sequence at position {bad.start() + 1}: '%' must be followed by two hex digits.")
        return unquote_to_bytes(s)
    if fmt is ByteFormat.UNICODE_ESCAPE:
        return unescape_unicode(s).encode("utf-8")
    if fmt is ByteFormat.JSON_STRING:
        try:
            return json.loads('"' + s + '"', strict=False).encode("utf-8")
        except json.JSONDecodeError as exc:
            raise EncodingError(f"Invalid JSON string escape: {exc.msg} (position {exc.pos}). Unescaped quotes and invalid backslashes are not allowed.") from exc
        except UnicodeEncodeError as exc:
            raise EncodingError("JSON string contains an unpaired surrogate escape; it is not valid Unicode text.") from exc
    if fmt is ByteFormat.BINARY:
        tokens = s.split()
        if not tokens:
            raise EncodingError("Input is empty.")
        if len(tokens) == 1 and len(tokens[0]) > 8:
            t = tokens[0]
            if len(t) % 8:
                raise EncodingError(f"Binary length {len(t)} is not a multiple of 8.")
            tokens = [t[i:i + 8] for i in range(0, len(t), 8)]
        for t in tokens:
            if len(t) != 8 or set(t) - {"0", "1"}:
                raise EncodingError(f"Invalid binary group {t!r}: each group must be exactly 8 characters of 0/1.")
        return bytes(int(t, 2) for t in tokens)
    if fmt is ByteFormat.DECIMAL:
        tokens = [t for t in re.split(r"[\s,;]+", s.strip()) if t]
        if not tokens:
            raise EncodingError("Input is empty.")
        out = bytearray()
        for t in tokens:
            if not re.fullmatch(r"[0-9]+", t):
                raise EncodingError(f"Invalid decimal byte {t!r}: use ASCII digits 0-9 separated by spaces or commas.")
            v = int(t)
            if v > 255:
                raise EncodingError(f"Decimal byte {v} is out of range 0-255.")
            out.append(v)
        return bytes(out)
    raise EncodingError(f"Unsupported format: {fmt}")


def convert(s: str, src: ByteFormat, dst: ByteFormat, **kw) -> str:
    """Convert between byte representations (exact bytes preserved)."""
    return encode_bytes(decode_to_bytes(s, src), dst, **kw)


@dataclass(frozen=True)
class FormatGuess:
    fmt: ByteFormat
    note: str


def detect_formats(s: str) -> list[FormatGuess]:
    """Heuristically list formats ``s`` could be written in. Ambiguity is expected and reported."""
    guesses: list[FormatGuess] = []
    stripped = s.strip()
    if not stripped:
        return guesses
    for fmt in ByteFormat:
        if fmt is ByteFormat.JSON_STRING:
            continue
        try:
            decode_to_bytes(stripped, fmt)
        except EncodingError:
            continue
        if fmt is ByteFormat.URL and "%" not in stripped:
            continue
        if fmt is ByteFormat.UNICODE_ESCAPE and "\\" not in stripped:
            continue
        guesses.append(FormatGuess(fmt, "syntactically valid"))
    if len(guesses) > 1:
        names = ", ".join(g.fmt.value for g in guesses)
        guesses = [FormatGuess(g.fmt, f"syntactically valid, but ambiguous (also valid as: {names})") for g in guesses]
    return guesses
