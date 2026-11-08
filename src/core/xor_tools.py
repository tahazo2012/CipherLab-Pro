"""Educational XOR tools and bounded, deterministic XOR analysis.

XOR with a repeating key is NOT secure encryption. These tools exist for learning
and for analysing simple obfuscation; results are statistical guesses, not proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from src.core.statistics import (ScoreResult, byte_histogram, english_score_hist, english_value,
                                 score_text)
from src.utils.progress import CancelCheck, ProgressCallback, check_cancel, report
from src.utils.validation import ValidationError, hex_to_bytes

MAX_KEY_BYTES = 1024
MAX_ANALYSIS_BYTES = 65_536
MAX_KEY_LENGTH = 64


class XorError(ValueError):
    """Invalid XOR parameters or inputs beyond the safety limits."""


@dataclass
class XorCandidate:
    method: str
    key: bytes
    output: bytes
    score: ScoreResult


@dataclass(frozen=True)
class KeyLengthScore:
    length: int
    distance: float  # normalised Hamming distance, bits per byte


def parse_key(key: str, mode: str = "text") -> bytes:
    """Parse a key typed as UTF-8 text (mode 'text') or hexadecimal (mode 'hex')."""
    if mode == "hex":
        try:
            raw = hex_to_bytes(key)
        except ValidationError as exc:
            raise XorError(f"Key: {exc}") from exc
    elif mode == "text":
        raw = key.encode("utf-8")
    else:
        raise XorError("Key mode must be 'text' or 'hex'.")
    if not raw:
        raise XorError("Key must not be empty.")
    if len(raw) > MAX_KEY_BYTES:
        raise XorError(f"Key is too long ({len(raw)} > {MAX_KEY_BYTES} bytes).")
    return raw


def xor_repeating(data: bytes, key: bytes) -> bytes:
    """XOR ``data`` with ``key`` repeated; applying it twice restores the input."""
    if not key:
        raise XorError("Key must not be empty.")
    n = len(data)
    if n == 0:
        return b""
    stream = (key * (n // len(key) + 1))[:n]
    return (int.from_bytes(data, "big") ^ int.from_bytes(stream, "big")).to_bytes(n, "big")


def _text_score(output: bytes, fallback: ScoreResult, persian: bool, table: Optional[Mapping[str, float]]) -> ScoreResult:
    try:
        return score_text(output.decode("utf-8"), persian_enabled=persian, persian_table=table)
    except UnicodeDecodeError:
        return fallback


def single_byte_xor_analysis(data: bytes, *, top: int = 5, persian_enabled: bool = True,
                             persian_table: Optional[Mapping[str, float]] = None,
                             skip_identity: bool = True,
                             cancel: Optional[CancelCheck] = None) -> list[XorCandidate]:
    """Try all 256 single-byte keys and return the ``top`` best-scoring candidates."""
    if len(data) > MAX_ANALYSIS_BYTES:
        raise XorError(f"Input too large for XOR analysis ({len(data):,} > {MAX_ANALYSIS_BYTES:,} bytes).")
    if not data:
        return []
    hist = byte_histogram(data)
    ranked: list[tuple[float, int]] = []
    for k in range(256):
        if skip_identity and k == 0:
            continue
        check_cancel(cancel)
        ranked.append((english_value([hist[b ^ k] for b in range(256)]), k))
    ranked.sort(reverse=True)
    out: list[XorCandidate] = []
    for _, k in ranked[: max(top * 3, 10)]:
        output = xor_repeating(data, bytes([k]))
        fallback = english_score_hist([hist[b ^ k] for b in range(256)])
        out.append(XorCandidate(f"Single-byte XOR (key 0x{k:02x})", bytes([k]), output,
                                _text_score(output, fallback, persian_enabled, persian_table)))
    out.sort(key=lambda c: c.score.score, reverse=True)
    return out[:top]


def rank_key_lengths(data: bytes, *, min_len: int = 2, max_len: int = 40, max_blocks: int = 8) -> list[KeyLengthScore]:
    """Rank candidate key lengths by average normalised Hamming distance between blocks.

    Lower is better. Multiples of the true length also score well, so ties between
    a length and its multiples are expected.
    """
    max_len = min(max_len, MAX_KEY_LENGTH)
    scores: list[KeyLengthScore] = []
    for length in range(max(1, min_len), max_len + 1):
        nblocks = min(max_blocks, len(data) // length)
        if nblocks < 2:
            continue
        blocks = [int.from_bytes(data[i * length:(i + 1) * length], "big") for i in range(nblocks)]
        total = pairs = 0
        for i in range(nblocks):
            for j in range(i + 1, nblocks):
                total += (blocks[i] ^ blocks[j]).bit_count()
                pairs += 1
        scores.append(KeyLengthScore(length, total / pairs / length))
    scores.sort(key=lambda s: (round(s.distance, 6), s.length))
    return scores


def break_repeating_key_xor(data: bytes, *, max_key_len: int = 40, top_lengths: int = 3,
                            persian_enabled: bool = True,
                            persian_table: Optional[Mapping[str, float]] = None,
                            progress: Optional[ProgressCallback] = None,
                            cancel: Optional[CancelCheck] = None) -> list[XorCandidate]:
    """Bounded statistical attack: pick likely key lengths, solve each key byte as single-byte XOR."""
    if len(data) > MAX_ANALYSIS_BYTES:
        raise XorError(f"Input too large for repeating-key analysis ({len(data):,} > {MAX_ANALYSIS_BYTES:,} bytes).")
    lengths = [s.length for s in rank_key_lengths(data, max_len=max_key_len)[:top_lengths]]
    results: dict[bytes, XorCandidate] = {}
    for idx, length in enumerate(lengths):
        report(progress, int(100 * idx / max(1, len(lengths))), f"Solving key length {length}")
        key = bytearray()
        for col in range(length):
            check_cancel(cancel)
            hist = byte_histogram(data[col::length])
            best = max(range(256), key=lambda k: english_value([hist[b ^ k] for b in range(256)]))
            key.append(best)
        kb = bytes(key)
        if kb in results or len(set(kb)) == 1 and len(kb) > 1 and bytes([kb[0]]) in results:
            continue
        output = xor_repeating(data, kb)
        fallback = english_score_hist(byte_histogram(output))
        results[kb] = XorCandidate(f"Repeating-key XOR (key length {length})", kb, output,
                                   _text_score(output, fallback, persian_enabled, persian_table))
    return sorted(results.values(), key=lambda c: c.score.score, reverse=True)
