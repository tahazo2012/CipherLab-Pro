import bz2
import lzma
import random
import zlib

import pytest

from src.core.hex_analyzer import AnalyzerOptions, analyze_bytes, analyze_hex
from src.core.xor_tools import xor_repeating
from src.utils.progress import OperationCancelled
from src.utils.validation import ValidationError, hex_to_bytes, normalize_hex

SAMPLE = "dcdcdcd324ad81ad8254dcdbddfcdcc7dcde24ad81af88acb0af88"
ENGLISH = (b"Analysis must be honest: readable output from a guessed key is evidence, not proof, and short "
           b"samples prove almost nothing at all.")


def test_sample_parses_and_is_inconclusive():
    assert len(hex_to_bytes(SAMPLE)) == 27
    rep = analyze_hex(SAMPLE, AnalyzerOptions(repeating_xor=True))
    assert rep.inconclusive
    assert not any(c.confidence in ("medium", "high") for c in rep.candidates)
    assert any("NOT valid UTF-8" in r for r in rep.reliable)
    assert "INCONCLUSIVE" in rep.to_text()


def test_normalization_reports_details():
    n = normalize_hex("DC:DC 0xd3\n24")
    assert n.digits == "DCDCd324" and n.removed_prefixes == 1 and not n.invalid


@pytest.mark.parametrize("bad,msg", [("", "empty"), ("   ", "empty"), ("abc", "Odd number"), ("12gz", "Invalid hexadecimal character")])
def test_invalid_hex_messages(bad, msg):
    with pytest.raises(ValidationError, match=msg):
        analyze_hex(bad)


def test_plain_text_hex_gets_high_confidence():
    rep = analyze_hex(ENGLISH.hex())
    assert rep.candidates[0].method == "Raw bytes as UTF-8 text" and rep.candidates[0].confidence == "high"
    assert not rep.inconclusive


def test_persian_text_scores_as_text():
    text = "این یک متن فارسی برای آزمایش تحلیل‌گر است و باید خوانا تشخیص داده شود"
    rep = analyze_bytes(text.encode())
    assert rep.candidates[0].method == "Raw bytes as UTF-8 text"
    assert rep.candidates[0].confidence in ("medium", "high")
    off = analyze_bytes(text.encode(), AnalyzerOptions(persian_enabled=False))
    assert off.candidates[0].score < rep.candidates[0].score


def test_single_byte_xor_found_but_never_overclaimed():
    rep = analyze_bytes(xor_repeating(ENGLISH, b"\x5a"))
    top = rep.candidates[0]
    assert top.method.startswith("Single-byte XOR") and top.key == b"\x5a" and top.output == ENGLISH
    assert top.confidence in ("medium", "high")
    short = analyze_bytes(xor_repeating(b"Hello World", b"\x5a"))
    assert all(c.confidence in ("none", "low") for c in short.candidates if c.kind == "xor1")


def test_repeating_key_optional():
    cipher = xor_repeating(ENGLISH * 3, b"KEY!")
    off = analyze_bytes(cipher)
    assert not any(c.kind == "xorN" for c in off.candidates)
    on = analyze_bytes(cipher, AnalyzerOptions(repeating_xor=True))
    assert any(c.kind == "xorN" for c in on.candidates)


def test_random_data_is_inconclusive():
    data = random.Random(1234).randbytes(256)
    rep = analyze_bytes(data, AnalyzerOptions(repeating_xor=True))
    assert rep.inconclusive and all(c.confidence in ("none", "low") for c in rep.candidates)


@pytest.mark.parametrize("compress", [zlib.compress, bz2.compress, lzma.compress,
                                      lambda d: __import__("gzip").compress(d)])
def test_compression_detected(compress):
    rep = analyze_bytes(compress(ENGLISH * 4))
    assert any(c.method.startswith("Decompress") and c.output == ENGLISH * 4 for c in rep.candidates)
    assert rep.compression


def test_decompression_bomb_is_bounded():
    rep = analyze_bytes(zlib.compress(b"\0" * 5_000_000), AnalyzerOptions(max_decompressed=1000))
    assert not any(c.method.startswith("Decompress") for c in rep.candidates)
    assert any("safety limit" in w for w in rep.warnings)


def test_signature_and_nested_base64():
    png = analyze_bytes(b"\x89PNG\r\n\x1a\n" + bytes(40))
    assert "PNG image" in png.signatures
    import base64
    rep = analyze_bytes(base64.b64encode(ENGLISH))
    assert any(c.method == "Decode inner Base64" and c.output == ENGLISH for c in rep.candidates)


def test_limits_cancel_and_progress():
    with pytest.raises(ValidationError):
        analyze_bytes(b"a" * 100, AnalyzerOptions(max_bytes=10))
    with pytest.raises(OperationCancelled):
        analyze_bytes(ENGLISH, cancel=lambda: True)
    seen = []
    analyze_bytes(ENGLISH, progress=lambda p, m: seen.append(p))
    assert seen[-1] == 100 and seen == sorted(seen)
