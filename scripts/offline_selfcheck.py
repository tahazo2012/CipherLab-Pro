"""Runs core operations with Python-level networking blocked and reports any attempt.

Usage:  python scripts/offline_selfcheck.py
For a stronger test, disconnect Wi-Fi / unplug Ethernet first (see README "Testing offline").
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.offline_guard import install_offline_guard, violation_count  # noqa: E402

install_offline_guard()

from src.core import crypto_engine as ce  # noqa: E402
from src.core.encodings import ByteFormat, decode_to_bytes, encode_bytes  # noqa: E402
from src.core.hex_analyzer import AnalyzerOptions, analyze_hex  # noqa: E402

text = "سلام دنیا / Hello 😀"
assert decode_to_bytes(encode_bytes(text.encode(), ByteFormat.BASE64), ByteFormat.BASE64).decode() == text
env = ce.encrypt_with_password(text.encode(), "offline-password")
assert ce.decrypt_json(env.to_json(), password="offline-password").decode() == text
rep = analyze_hex("dcdcdcd324ad81ad8254dcdbddfcdcc7dcde24ad81af88acb0af88", AnalyzerOptions(repeating_xor=True))
print("analysis verdict:", "inconclusive" if rep.inconclusive else "candidates found")
print("network attempts blocked:", violation_count())
sys.exit(1 if violation_count() else 0)
