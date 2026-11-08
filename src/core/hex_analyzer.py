"""Local hexadecimal analysis engine (no network, no remote models).

Pipeline: validate/normalise hex → bytes → statistics → encoding checks → signatures →
compression → nested-encoding transforms → single-byte XOR → optional bounded
repeating-key XOR → transparent ranking → honest conclusions.
"""
from __future__ import annotations

import bz2
import lzma
import re
import zlib
from dataclasses import dataclass
from typing import Mapping, Optional

from src.core.candidate_ranking import ScoringContext, build_candidate, rank_candidates
from src.core.encodings import ByteFormat, EncodingError, decode_to_bytes
from src.core.statistics import (index_of_coincidence, max_entropy_for_length, printable_ratio,
                                 shannon_entropy, top_bytes)
from src.core.xor_tools import (MAX_ANALYSIS_BYTES, XorError, break_repeating_key_xor, rank_key_lengths,
                                single_byte_xor_analysis)
from src.models.analysis_result import AnalysisReport, Candidate
from src.utils.progress import CancelCheck, ProgressCallback, check_cancel, report
from src.utils.validation import ValidationError, ensure_size, hex_to_bytes, normalize_hex

SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "PNG image"), (b"\xff\xd8\xff", "JPEG image"), (b"GIF87a", "GIF image"),
    (b"GIF89a", "GIF image"), (b"%PDF-", "PDF document"), (b"PK\x03\x04", "ZIP archive (or OOXML/JAR/APK)"),
    (b"\x1f\x8b", "GZIP stream"), (b"BZh", "BZIP2 stream"), (b"\xfd7zXZ\x00", "XZ stream"),
    (b"7z\xbc\xaf\x27\x1c", "7-Zip archive"), (b"Rar!\x1a\x07", "RAR archive"), (b"\x7fELF", "ELF executable"),
    (b"MZ", "Windows PE/DOS executable (weak 2-byte signature)"), (b"SQLite format 3\x00", "SQLite database"),
    (b"ID3", "MP3 audio with ID3 tag"), (b"OggS", "Ogg container"), (b"BM", "BMP image (weak 2-byte signature)"),
    (b"II*\x00", "TIFF image (little endian)"), (b"MM\x00*", "TIFF image (big endian)"),
    (b"\xca\xfe\xba\xbe", "Java class file / Mach-O fat binary"), (b"\x00asm", "WebAssembly module"),
    (b"{\\rtf", "RTF document"), (b"\xef\xbb\xbf", "UTF-8 byte-order mark"),
]


@dataclass
class AnalyzerOptions:
    persian_enabled: bool = True
    persian_table: Optional[Mapping[str, float]] = None
    repeating_xor: bool = False
    max_key_len: int = 40
    max_bytes: int = 1_048_576
    max_decompressed: int = 16 * 1024 * 1024
    top_xor: int = 5
    max_candidates: int = 25


def find_signatures(data: bytes) -> list[str]:
    found = [name for magic, name in SIGNATURES if data.startswith(magic)]
    if data.startswith(b"RIFF") and len(data) >= 12:
        found.append({b"WAVE": "WAV audio", b"WEBP": "WebP image", b"AVI ": "AVI video"}.get(data[8:12], "RIFF container"))
    if len(data) >= 12 and data[4:8] == b"ftyp":
        found.append("ISO base media (MP4/MOV/HEIC)")
    return found


def try_decompress(data: bytes, limit: int) -> list[tuple[str, Optional[bytes], str]]:
    """Attempt bounded decompression; returns (name, output-or-None, note)."""
    results: list[tuple[str, Optional[bytes], str]] = []

    def attempt(name: str, make):
        try:
            dec = make()
            out = dec.decompress(data, limit + 1)
            if len(out) > limit:
                results.append((name, None, f"output exceeds the {limit:,}-byte safety limit (possible decompression bomb); skipped"))
            elif not getattr(dec, "eof", False):
                results.append((name, out, "stream is truncated/incomplete (checksum not verified)"))
            else:
                results.append((name, out, "complete stream, integrity checks passed"))
        except Exception as exc:  # noqa: BLE001 - any decoder failure just means "not this format"
            results.append((name, None, f"not valid ({type(exc).__name__})"))

    if len(data) >= 2 and data[0] & 0x0F == 8 and data[0] >> 4 <= 7 and (data[0] * 256 + data[1]) % 31 == 0:
        attempt("zlib", lambda: zlib.decompressobj())
    if data.startswith(b"\x1f\x8b"):
        attempt("gzip", lambda: zlib.decompressobj(wbits=31))
    if data.startswith(b"BZh"):
        attempt("bzip2", lambda: bz2.BZ2Decompressor())
    if data.startswith(b"\xfd7zXZ\x00"):
        attempt("xz", lambda: lzma.LZMADecompressor(format=lzma.FORMAT_XZ))
    return results


def _ascii_view(data: bytes) -> Optional[str]:
    try:
        s = data.decode("ascii")
    except UnicodeDecodeError:
        return None
    return s if all(c.isprintable() or c in "\t\r\n" for c in s) else None


_TRANSFORMS: list[tuple[str, ByteFormat, str, int]] = [
    ("Base64", ByteFormat.BASE64, r"[A-Za-z0-9+/=\s\-_]+", 8),
    ("hexadecimal text", ByteFormat.HEX, r"[0-9a-fA-F\s:,\-]+", 6),
    ("binary text", ByteFormat.BINARY, r"[01\s]+", 16),
    ("decimal byte list", ByteFormat.DECIMAL, r"[0-9\s,;]+", 3),
    ("URL percent-encoding", ByteFormat.URL, r".*%[0-9A-Fa-f]{2}.*", 3),
    ("Unicode escapes", ByteFormat.UNICODE_ESCAPE, r".*\\u[0-9a-fA-F]{4}.*", 6),
]


def analyze_hex(text: str, options: Optional[AnalyzerOptions] = None, *,
                progress: Optional[ProgressCallback] = None,
                cancel: Optional[CancelCheck] = None) -> AnalysisReport:
    """Validate hexadecimal text and analyse the resulting bytes."""
    norm = normalize_hex(text)
    data = hex_to_bytes(text)  # raises ValidationError with a precise message
    info = {
        "hex digits": len(norm.digits), "separators removed": norm.removed_separators,
        "0x / \\x prefixes removed": norm.removed_prefixes, "odd length": "no", "bytes": len(data),
    }
    return analyze_bytes(data, options, input_info=info, progress=progress, cancel=cancel)


def analyze_bytes(data: bytes, options: Optional[AnalyzerOptions] = None, *,
                  input_info: Optional[dict] = None, progress: Optional[ProgressCallback] = None,
                  cancel: Optional[CancelCheck] = None) -> AnalysisReport:
    opts = options or AnalyzerOptions()
    if not data:
        raise ValidationError("No bytes to analyze (empty input).")
    ensure_size(len(data), opts.max_bytes, "Input for analysis")
    ctx = ScoringContext(opts.persian_enabled, opts.persian_table)
    rep = AnalysisReport(input_info=dict(input_info or {"bytes": len(data)}))
    cands: list[Candidate] = []
    n = len(data)

    # 1. statistics
    report(progress, 5, "Byte statistics")
    ent = shannon_entropy(data)
    rep.byte_stats = {
        "length": f"{n} bytes", "Shannon entropy": f"{ent:.3f} bits/byte (maximum possible for this length: {max_entropy_for_length(n):.3f})",
        "distinct byte values": len(set(data)), "printable-ASCII ratio": f"{printable_ratio(data):.1%}",
        "NUL bytes": data.count(0), "index of coincidence": f"{index_of_coincidence(data):.4f}",
        "most frequent bytes": ", ".join(f"0x{b:02x}×{c}" for b, c in top_bytes(data, 8)),
    }
    if n < 16:
        rep.warnings.append("Very short input: statistical scores are unreliable.")
    if n >= 256 and ent > 7.5:
        rep.uncertain.append(f"Entropy {ent:.2f} bits/byte is consistent with compressed, encrypted or random data (not proof of any).")
    elif n < 256:
        rep.uncertain.append("Input is too short for entropy to say whether the data is encrypted, compressed or structured.")
    check_cancel(cancel)

    # 2. encoding checks
    report(progress, 15, "Checking text encodings")
    utf8_ok = False
    for label, codec in (("UTF-8", "utf-8"), ("ASCII", "ascii"), ("UTF-16 LE", "utf-16-le"), ("UTF-16 BE", "utf-16-be")):
        try:
            if codec.startswith("utf-16") and n % 2:
                raise UnicodeDecodeError(codec, data, n - 1, n, "odd byte count")
            data.decode(codec)
            rep.encoding_checks.append(f"{label}: decodes without errors")
            utf8_ok = utf8_ok or codec == "utf-8"
        except UnicodeDecodeError as exc:
            rep.encoding_checks.append(f"{label}: invalid ({exc.reason} at byte {exc.start})")
    rep.encoding_checks.append("Latin-1: always decodes (every byte is valid), so this check proves nothing")
    if utf8_ok:
        cands.append(build_candidate("Raw bytes as UTF-8 text", data, kind="raw", ctx=ctx))
    for label, codec in (("UTF-16 LE", "utf-16-le"), ("UTF-16 BE", "utf-16-be")):
        if n % 2 == 0:
            try:
                txt = data.decode(codec)
            except UnicodeDecodeError:
                continue
            cands.append(build_candidate(f"Raw bytes as {label} text", txt.encode("utf-8"), kind="utf16", ctx=ctx, text=txt))
    if not utf8_ok:
        txt = data.decode("latin-1")
        cands.append(build_candidate("Raw bytes as Latin-1 text", txt.encode("utf-8"), kind="latin1", ctx=ctx, text=txt))
    check_cancel(cancel)

    # 3. signatures
    report(progress, 25, "Looking for file signatures")
    rep.signatures = find_signatures(data)
    for name in rep.signatures:
        cands.append(build_candidate(f"File signature: {name}", data, kind="container", ctx=ctx, structural=0.9,
                                     structural_note="magic bytes at offset 0 match (identifies the container, not its meaning)"))
        rep.reliable.append(f"The data begins with the signature of: {name}.")

    # 4. compression
    report(progress, 35, "Testing compression signatures")
    for name, out, note in try_decompress(data, opts.max_decompressed):
        rep.compression.append(f"{name}: {note}")
        if out is None:
            rep.warnings.append(f"{name} decompression skipped or failed: {note}.")
            continue
        complete = "complete" in note
        cands.append(build_candidate(f"Decompress {name}", out, kind="container", ctx=ctx,
                                     structural=0.9 if complete else 0.5, structural_note=note))
        if complete:
            rep.reliable.append(f"Valid {name} stream; decompressed to {len(out):,} bytes (checksum verified).")
    if not rep.compression:
        rep.compression.append("no zlib/gzip/bzip2/xz signature found")
    check_cancel(cancel)

    # 5. nested encodings
    report(progress, 45, "Testing nested encodings")
    view = _ascii_view(data)
    if view is not None:
        stripped = view.strip()
        for name, fmt, pattern, min_len in _TRANSFORMS:
            if len(stripped) < min_len or not re.fullmatch(pattern, stripped, re.S):
                continue
            try:
                out = decode_to_bytes(stripped, fmt)
            except (EncodingError, ValidationError):
                continue
            cands.append(build_candidate(f"Decode inner {name}", out, kind="transform", ctx=ctx))
    if n >= 4:
        cands.append(build_candidate("Reverse byte order", data[::-1], kind="reverse", ctx=ctx))
    check_cancel(cancel)

    # 6. XOR
    report(progress, 60, "Single-byte XOR analysis")
    try:
        for xc in single_byte_xor_analysis(data, top=opts.top_xor, persian_enabled=opts.persian_enabled,
                                           persian_table=opts.persian_table, cancel=cancel):
            cands.append(build_candidate(xc.method, xc.output, kind="xor1", ctx=ctx, key=xc.key))
        if opts.repeating_xor:
            report(progress, 70, "Repeating-key XOR analysis")
            rep.key_lengths = [(s.length, s.distance) for s in rank_key_lengths(data, max_len=opts.max_key_len)]
            if rep.key_lengths:
                for xc in break_repeating_key_xor(data, max_key_len=opts.max_key_len, persian_enabled=opts.persian_enabled,
                                                  persian_table=opts.persian_table, cancel=cancel,
                                                  progress=lambda p, m: report(progress, 70 + p // 4, m)):
                    cands.append(build_candidate(xc.method, xc.output, kind="xorN", ctx=ctx, key=xc.key))
            else:
                rep.warnings.append("Input too short for repeating-key analysis (needs at least two blocks of the key length).")
    except XorError as exc:
        rep.warnings.append(str(exc))

    # 7. ranking & conclusions
    report(progress, 98, "Ranking candidates")
    rep.candidates = rank_candidates(cands, opts.max_candidates)
    rep.inconclusive = not any(c.confidence in ("medium", "high") for c in rep.candidates)
    if utf8_ok:
        rep.reliable.append("The bytes are valid UTF-8 (strict decoding succeeded).")
    else:
        rep.reliable.append("The bytes are NOT valid UTF-8, so they are not plain UTF-8 text.")
    rep.reliable.insert(0, f"{n} bytes were parsed from the input; byte statistics above are exact.")
    rep.uncertain.append("No encryption algorithm or key can be identified from the bytes alone; nothing here is a decryption claim.")
    if any(c.kind in ("xor1", "xorN") and c.confidence != "none" for c in rep.candidates):
        rep.uncertain.append("XOR candidates are statistical guesses: readable output does not prove that key was used.")
    if rep.inconclusive:
        rep.uncertain.append("The original encoding, cipher and key could not be determined; do not treat any candidate as the answer.")
    report(progress, 100, "Done")
    return rep
