"""Byte/text statistics and transparent, explainable text-likeness scoring.

Scoring formulas (all in the range 0..1):

English (bytes)::

    score = (0.4*printable + 0.3*alpha_space + 0.3*letter_fit) * min(1, n/8)

* printable   - share of bytes that are printable ASCII, TAB, LF or CR
* alpha_space - share of bytes that are letters or spaces
* letter_fit  - 1 - total-variation distance between the observed letter
                distribution and a built-in English frequency table
* the last factor damps very short samples, which are statistically meaningless

Persian (text)::

    score = (0.3*printable + 0.3*script_share + 0.4*letter_fit) * min(1, n/6)

The Persian letter table is approximate and replaceable via Settings.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Mapping, Optional

ENGLISH_LETTER_FREQ = (
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702, 0.02228, 0.02015, 0.06094, 0.06966,
    0.00153, 0.00772, 0.04025, 0.02406, 0.06749, 0.07507, 0.01929, 0.00095, 0.05987,
    0.06327, 0.09056, 0.02758, 0.00978, 0.02360, 0.00150, 0.01974, 0.00074,
)

# Approximate relative frequencies of Persian letters (configurable, not authoritative).
DEFAULT_PERSIAN_FREQ: dict[str, float] = {
    "ا": 13, "ی": 10, "ر": 7, "د": 6, "ن": 6, "و": 6, "م": 5, "ه": 5, "ت": 5, "ب": 4,
    "ک": 3.5, "س": 3.5, "ل": 3.2, "ش": 2.5, "ز": 2, "ف": 1.8, "گ": 1.5, "ق": 1.5,
    "ج": 1.2, "پ": 1.1, "خ": 1.1, "ح": 1, "ع": 1, "چ": 0.8, "ص": 0.7, "ط": 0.5,
    "ض": 0.4, "ث": 0.3, "ذ": 0.3, "غ": 0.3, "ظ": 0.2, "ژ": 0.2, "ئ": 0.5, "ء": 0.2, "آ": 0.9,
}

_PRINTABLE = bytes(list(range(0x20, 0x7F)) + [0x09, 0x0A, 0x0D])
_TEXT_OK_EXTRA = frozenset("\t\n\r\u200c\u200d\u200e\u200f")


@dataclass
class ScoreResult:
    """A score plus the numbers and notes that explain it."""

    score: float
    components: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    language: str = "english"


def byte_histogram(data: bytes) -> list[int]:
    hist = [0] * 256
    for value, count in Counter(data).items():
        hist[value] = count
    return hist


def top_bytes(data: bytes, n: int = 8) -> list[tuple[int, int]]:
    return Counter(data).most_common(n)


def shannon_entropy(data: bytes) -> float:
    """Shannon entropy in bits per byte (0..8)."""
    if not data:
        return 0.0
    total = len(data)
    return -sum((c / total) * math.log2(c / total) for c in Counter(data).values())


def max_entropy_for_length(n: int) -> float:
    """Highest entropy a sample of ``n`` bytes can show (log2(min(n, 256)))."""
    return math.log2(min(n, 256)) if n > 0 else 0.0


def printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    return (len(data) - len(data.translate(None, _PRINTABLE))) / len(data)


def text_printable_ratio(text: str) -> float:
    if not text:
        return 0.0
    return sum(1 for c in text if c.isprintable() or c in _TEXT_OK_EXTRA) / len(text)


def index_of_coincidence(data: bytes) -> float:
    n = len(data)
    if n < 2:
        return 0.0
    return sum(c * (c - 1) for c in Counter(data).values()) / (n * (n - 1))


def hamming_distance(a: bytes, b: bytes) -> int:
    if len(a) != len(b):
        raise ValueError("Hamming distance needs equal-length inputs.")
    return (int.from_bytes(a, "big") ^ int.from_bytes(b, "big")).bit_count()


def _english_parts(hist: list[int]) -> tuple[int, float, float, float]:
    n = sum(hist)
    if n == 0:
        return 0, 0.0, 0.0, 0.0
    printable = sum(hist[b] for b in _PRINTABLE) / n
    letters = [hist[97 + i] + hist[65 + i] for i in range(26)]
    nl = sum(letters)
    alpha_space = (nl + hist[32]) / n
    fit = 0.0
    if nl:
        tvd = 0.5 * sum(abs(letters[i] / nl - ENGLISH_LETTER_FREQ[i]) for i in range(26))
        fit = 1.0 - tvd
    return n, printable, alpha_space, fit


def english_value(hist: list[int]) -> float:
    """Fast numeric English score from a byte histogram."""
    n, p, a, f = _english_parts(hist)
    return 0.0 if n == 0 else (0.4 * p + 0.3 * a + 0.3 * f) * min(1.0, n / 8)


def english_score_hist(hist: list[int]) -> ScoreResult:
    n, p, a, f = _english_parts(hist)
    score = english_value(hist)
    notes = [
        f"printable bytes {p:.0%}",
        f"letters+spaces {a:.0%}",
        f"English letter-frequency fit {f:.0%}",
    ]
    if n < 8:
        notes.append(f"sample of {n} byte(s) is too short; score damped by n/8")
    return ScoreResult(round(score, 4), {"printable": round(p, 4), "alpha_space": round(a, 4),
                                         "letter_fit": round(f, 4)}, notes, "english")


def english_score_bytes(data: bytes) -> ScoreResult:
    return english_score_hist(byte_histogram(data))


def normalize_persian_table(table: Mapping[str, float]) -> dict[str, float]:
    clean = {k: float(v) for k, v in table.items() if len(k) == 1 and float(v) > 0}
    total = sum(clean.values())
    if not clean or total <= 0:
        raise ValueError("Persian frequency table is empty or invalid.")
    return {k: v / total for k, v in clean.items()}


def persian_score(text: str, table: Optional[Mapping[str, float]] = None) -> ScoreResult:
    freq = normalize_persian_table(table or DEFAULT_PERSIAN_FREQ)
    norm = text.replace("ي", "ی").replace("ك", "ک")
    letters = [c for c in norm if c in freq]
    if not letters:
        return ScoreResult(0.0, {}, ["no Persian letters found"], "persian")
    n = len(norm)
    printable = text_printable_ratio(text)
    script_ok = sum(1 for c in norm if c in freq or c.isspace() or c in "\u200c\u200d0123456789۰۱۲۳۴۵۶۷۸۹.,!?؟،؛:()-")
    script = script_ok / n
    counts = Counter(letters)
    nl = len(letters)
    tvd = 0.5 * sum(abs(counts.get(c, 0) / nl - freq.get(c, 0.0)) for c in set(freq) | set(counts))
    fit = 1.0 - tvd
    score = (0.3 * printable + 0.3 * script + 0.4 * fit) * min(1.0, n / 6)
    notes = [f"printable characters {printable:.0%}", f"Persian script/space share {script:.0%}",
             f"Persian letter-frequency fit {fit:.0%}"]
    return ScoreResult(round(score, 4), {"printable": round(printable, 4),
                                         "script_share": round(script, 4),
                                         "letter_fit": round(fit, 4)}, notes, "persian")


def score_text(text: str, *, persian_enabled: bool = True,
               persian_table: Optional[Mapping[str, float]] = None) -> ScoreResult:
    """Best of the English and (optional) Persian scores for decoded text."""
    sample = text[:65536]
    best = english_score_bytes(sample.encode("utf-8", "replace"))
    if persian_enabled:
        per = persian_score(sample, persian_table)
        if per.score > best.score:
            best = per
    return best
