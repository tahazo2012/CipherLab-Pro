import pytest

from src.core.xor_tools import (XorError, break_repeating_key_xor, parse_key, rank_key_lengths,
                                single_byte_xor_analysis, xor_repeating)
from src.utils.progress import OperationCancelled

ENGLISH = (
    "It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of "
    "foolishness, it was the epoch of belief, it was the epoch of incredulity, it was the season of Light, "
    "it was the season of Darkness, it was the spring of hope, it was the winter of despair, we had everything "
    "before us, we had nothing before us, we were all going direct to Heaven, we were all going direct the "
    "other way - in short, the period was so far like the present period, that some of its noisiest "
    "authorities insisted on its being received, for good or for evil, in the superlative degree of comparison only."
).encode()


def test_round_trip_and_involution():
    key = b"k3y"
    assert xor_repeating(xor_repeating(ENGLISH, key), key) == ENGLISH
    assert xor_repeating(b"", b"k") == b""


def test_parse_key_modes_and_errors():
    assert parse_key("AB", "text") == b"AB"
    assert parse_key("de ad", "hex") == b"\xde\xad"
    assert parse_key("کلید", "text") == "کلید".encode()
    with pytest.raises(XorError):
        parse_key("", "text")
    with pytest.raises(XorError):
        parse_key("xyz", "hex")
    with pytest.raises(XorError):
        parse_key("a" * 2000, "text")


def test_single_byte_analysis_finds_key():
    cipher = xor_repeating(ENGLISH, bytes([0x5A]))
    best = single_byte_xor_analysis(cipher)[0]
    assert best.key == bytes([0x5A]) and best.output == ENGLISH


def test_repeating_key_analysis_finds_key_length_and_key():
    key = b"SECRET"
    cipher = xor_repeating(ENGLISH, key)
    lengths = [s.length for s in rank_key_lengths(cipher)[:4]]
    assert 6 in lengths
    best = break_repeating_key_xor(cipher)[0]
    assert best.output == ENGLISH


def test_limits_and_cancel():
    with pytest.raises(XorError):
        single_byte_xor_analysis(b"a" * 70_000)
    with pytest.raises(OperationCancelled):
        single_byte_xor_analysis(ENGLISH, cancel=lambda: True)
    assert single_byte_xor_analysis(b"") == []
