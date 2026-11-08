"""Offline guarantees: no network libraries imported, no connections attempted."""
import ast
import socket
from pathlib import Path

import pytest

from src.core import crypto_engine as ce
from src.core.encodings import ByteFormat, decode_to_bytes, encode_bytes
from src.core.hex_analyzer import AnalyzerOptions, analyze_hex
from src.core.history_manager import HistoryManager
from src.utils.offline_guard import OfflineViolation, install_offline_guard, violation_count

ROOT = Path(__file__).resolve().parent.parent
BANNED = {"socket", "ssl", "http", "urllib3", "requests", "httpx", "aiohttp", "ftplib", "smtplib", "poplib",
          "imaplib", "telnetlib", "xmlrpc", "websocket", "websockets", "asyncio", "webbrowser", "wsgiref",
          "socketserver", "paramiko", "pycurl"}
ALLOWED_FILES = {"offline_guard.py"}  # the guard must import socket to block it


def _imports(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module


def test_no_network_modules_imported_in_source():
    offenders = []
    for path in list((ROOT / "src").rglob("*.py")) + [ROOT / "main.py"]:
        if path.name in ALLOWED_FILES:
            continue
        for mod in _imports(path):
            root = mod.split(".")[0]
            if root in BANNED or mod.startswith("urllib.request") or "QtNetwork" in mod or "QtWebEngine" in mod:
                offenders.append((path.name, mod))
    assert not offenders, offenders


def test_urllib_usage_is_parse_only():
    for path in (ROOT / "src").rglob("*.py"):
        src = path.read_text(encoding="utf-8")
        assert "urllib.request" not in src and "urlopen" not in src


def test_requirements_have_no_http_clients():
    reqs = (ROOT / "requirements.txt").read_text().lower()
    for name in ("requests", "httpx", "aiohttp", "urllib3", "anthropic", "openai", "google"):
        assert name not in reqs


def test_no_remote_urls_in_gui_or_core():
    for path in (ROOT / "src").rglob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            code = line.split("#")[0]
            assert "http://" not in code and "https://" not in code, (path.name, line)


@pytest.fixture
def guard():
    restore = install_offline_guard()
    before = violation_count()
    yield before
    restore()


def test_guard_blocks_connections(guard):
    with pytest.raises(OfflineViolation):
        socket.create_connection(("example.com", 80))
    with pytest.raises(OfflineViolation):
        socket.socket().connect(("127.0.0.1", 9))
    with pytest.raises(OfflineViolation):
        socket.getaddrinfo("example.com", 80)
    assert violation_count() == guard + 3


def test_core_operations_make_no_connection_attempts(guard, tmp_path):
    assert decode_to_bytes(encode_bytes("سلام".encode(), ByteFormat.BASE64), ByteFormat.BASE64)
    env = ce.encrypt_with_password(b"offline", "pw", iterations=100_000)
    assert ce.decrypt_json(env.to_json(), password="pw") == b"offline"
    ce.hash_bytes(b"x"), ce.hmac_digest(b"k", b"x")
    analyze_hex("48656c6c6f20776f726c64", AnalyzerOptions(repeating_xor=True))
    h = HistoryManager(tmp_path / "h.db")
    h.add("encode", "ok")
    h.list()
    assert violation_count() == guard
