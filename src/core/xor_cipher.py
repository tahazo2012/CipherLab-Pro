"""Custom-password repeating-key XOR encoder / decoder (educational; XOR is NOT secure encryption).

Password rules (the password is HEX DATA, never ordinary text):
* any length is accepted - the application imposes no limit (only available memory does);
* an optional ``0x`` / ``0X`` prefix is accepted, and so are separators (space ``:`` ``-`` ``,`` ``_``)
  and ``\\xNN`` style prefixes; they are stripped, nothing else is changed;
* leading zeros are preserved: ``0001`` is the two bytes ``00 01``, not the one byte ``01``;
* an odd number of digits is read as a hexadecimal NUMBER, i.e. one leading ``0`` is implied
  (``0x474`` = ``0x0474`` = bytes ``04 74``). ``strict_even=True`` rejects odd lengths instead;
* the whole password is used: byte i of the data is XORed with password byte ``i mod len(password)``;
* nothing is hardcoded and the password is never modified, trimmed or truncated.

Text is converted with UTF-8, so Persian, Arabic, Chinese, emoji and any other Unicode text round-trips.
"""
from __future__ import annotations

import string
from dataclasses import dataclass
from typing import Optional

from src.core.xor_tools import xor_repeating

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")
_SEPARATORS = frozenset(" \t\r\n:-,_")
_ASCII_ALNUM = frozenset(string.ascii_letters + string.digits)


class XorCipherError(ValueError):
    """User-correctable problem (invalid hex, empty password, not valid UTF-8, ...)."""


@dataclass(frozen=True)
class ParsedHex:
    """A parsed hexadecimal value."""

    data: bytes          # the bytes actually used
    digits: str          # the hex digits exactly as typed (prefix/separators removed, case kept)
    padded: bool         # True when one leading 0 was implied because the digit count was odd

    def preview(self, limit: int = 32) -> str:
        shown = self.data[:limit].hex(" ")
        return shown + (f" … (+{len(self.data) - limit} more)" if len(self.data) > limit else "")


def _extract_digits(text: str, what: str) -> str:
    """Return the hex digits in ``text`` (prefixes and separators skipped); reject anything else."""
    digits: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "\\" and i + 1 < n and text[i + 1] in "xX":
            i += 2
        elif ch == "0" and i + 1 < n and text[i + 1] in "xX" and (i == 0 or text[i - 1] not in _ASCII_ALNUM):
            i += 2
        elif ch in _SEPARATORS:
            i += 1
        elif ch in _HEX_DIGITS:
            digits.append(ch)
            i += 1
        else:
            hint = ""
            if 0x0600 <= ord(ch) <= 0x06FF:
                hint = " Persian/Arabic letters and digits are not accepted: switch the keyboard to English and use 0-9, a-f."
            raise XorCipherError(
                f"{what}: invalid hexadecimal character {ch!r} (U+{ord(ch):04X}) at position {i + 1}. "
                f"Allowed: 0-9, a-f, A-F, an optional 0x prefix and the separators space : - , _ .{hint}")
    return "".join(digits)


def parse_hex_password(text: str, *, strict_even: bool = False) -> ParsedHex:
    """Parse a hexadecimal password of ANY length into bytes (see the module docstring for the rules)."""
    digits = _extract_digits(text, "Password")
    if not digits:
        raise XorCipherError("Password is empty: enter a hexadecimal password such as 0xA1B2C3 or 00ff10.")
    padded = len(digits) % 2 == 1
    if padded and strict_even:
        raise XorCipherError(
            f"Password has an odd number of hex digits ({len(digits)}) and strict mode is on. "
            "Add or remove a digit, or turn strict mode off to read it as a number (0x474 = 0x0474).")
    return ParsedHex(bytes.fromhex(("0" + digits) if padded else digits), digits, padded)


def parse_hex_data(text: str, what: str = "Encrypted data") -> bytes:
    """Parse hexadecimal data. Odd digit counts are an error: data bytes are never padded or guessed."""
    digits = _extract_digits(text, what)
    if not digits:
        raise XorCipherError(f"{what} is empty: paste the HEX output of the XOR Encoder.")
    if len(digits) % 2:
        raise XorCipherError(f"{what} has an odd number of hex digits ({len(digits)}); every byte needs two digits, "
                             "so some digits are missing or extra.")
    return bytes.fromhex(digits)


def encrypt_text(plaintext: str, password: str, *, strict_even: bool = False, separator: str = " ",
                 upper: bool = False) -> str:
    """UTF-8 encode ``plaintext``, XOR it with the whole hex ``password`` and return the result as HEX."""
    if plaintext == "":
        raise XorCipherError("Plaintext is empty: type or paste some text to encrypt.")
    try:
        data = plaintext.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise XorCipherError(f"The text contains a character that is not valid Unicode (position {exc.start + 1}).") from exc
    key = parse_hex_password(password, strict_even=strict_even).data
    out = xor_repeating(data, key).hex(separator) if separator else xor_repeating(data, key).hex()
    return out.upper() if upper else out


@dataclass(frozen=True)
class DecryptResult:
    data: bytes                   # the XOR result (always available)
    text: Optional[str]           # UTF-8 text, or None if the bytes are not valid UTF-8
    utf8_error: Optional[str] = None


def decrypt_hex(cipher_hex: str, password: str, *, strict_even: bool = False) -> DecryptResult:
    """XOR the HEX data with the same password and decode the result as UTF-8."""
    data = parse_hex_data(cipher_hex)
    key = parse_hex_password(password, strict_even=strict_even).data
    plain = xor_repeating(data, key)
    try:
        return DecryptResult(plain, plain.decode("utf-8"))
    except UnicodeDecodeError as exc:
        return DecryptResult(plain, None, (
            f"The result is not valid UTF-8 (invalid byte at offset {exc.start}). The password is probably wrong, or the "
            "data was not produced by the XOR Encoder."))
