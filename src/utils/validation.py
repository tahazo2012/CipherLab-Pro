"""Input validation helpers shared by the core modules and the GUI."""
from __future__ import annotations

import re
from dataclasses import dataclass

MAX_TEXT_CHARS = 50_000_000
HEX_SEPARATORS = " \t\r\n:-,_"
_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


class ValidationError(ValueError):
    """User-correctable input problem with a human-readable message."""


@dataclass(frozen=True)
class NormalizedHex:
    """Result of normalising a hexadecimal string."""

    digits: str
    removed_separators: int
    removed_prefixes: int
    invalid: tuple[tuple[int, str], ...]

    @property
    def odd_length(self) -> bool:
        return len(self.digits) % 2 == 1


def ensure_size(length: int, limit: int, what: str = "Input") -> None:
    """Raise ValidationError if ``length`` exceeds ``limit``."""
    if length > limit:
        raise ValidationError(f"{what} is too large ({length:,} > {limit:,} allowed).")


def normalize_hex(text: str) -> NormalizedHex:
    """Strip permitted separators / ``0x`` / ``\\x`` prefixes and report problems.

    Nothing is silently repaired: invalid characters and odd length are reported.
    """
    ensure_size(len(text), MAX_TEXT_CHARS, "Hexadecimal text")
    body, n_bs = re.subn(r"\\x", "", text)
    body, n_0x = re.subn(r"(?<![0-9A-Za-z])0[xX]", "", body)
    digits: list[str] = []
    invalid: list[tuple[int, str]] = []
    removed = 0
    for index, ch in enumerate(body):
        if ch in HEX_SEPARATORS:
            removed += 1
        elif ch in _HEX_DIGITS:
            digits.append(ch)
        else:
            invalid.append((index, ch))
    return NormalizedHex("".join(digits), removed, n_bs + n_0x, tuple(invalid))


def hex_to_bytes(text: str) -> bytes:
    """Strictly convert hexadecimal text to bytes, raising ValidationError."""
    norm = normalize_hex(text)
    if norm.invalid:
        pos, ch = norm.invalid[0]
        more = f" (+{len(norm.invalid) - 1} more)" if len(norm.invalid) > 1 else ""
        raise ValidationError(
            f"Invalid hexadecimal character {ch!r} (U+{ord(ch):04X}) at position {pos + 1}{more}. "
            "Allowed: 0-9, a-f, A-F and separators (space, ':', '-', ',', '_')."
        )
    if not norm.digits:
        raise ValidationError("Input is empty: no hexadecimal digits found.")
    if norm.odd_length:
        raise ValidationError(
            f"Odd number of hexadecimal digits ({len(norm.digits)}). Every byte needs exactly two "
            "digits; add or remove one digit (the input is not padded automatically)."
        )
    return bytes.fromhex(norm.digits)
