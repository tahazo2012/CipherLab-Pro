import logging

from src.core.history_manager import HistoryManager, scrub_params
from src.core.settings import Settings
from src.utils.logging_config import RedactingFilter


def make(tmp_path, **kw):
    return HistoryManager(tmp_path / "h.db", **kw)


def test_add_list_delete_clear(tmp_path):
    h = make(tmp_path)
    a = h.add("encode", "UTF-8 → Hex", input_preview="سلام", output_preview="d8 b3")
    b = h.add("decode", "Hex → UTF-8")
    assert h.count() == 2 and h.list("سلام")[0].id == a
    h.delete(a)
    assert [r.id for r in h.list()] == [b]
    h.clear()
    assert h.count() == 0


def test_disabled_history_stores_nothing(tmp_path):
    h = make(tmp_path, enabled=False)
    assert h.add("encode", "x") is None
    assert not (tmp_path / "h.db").exists() or h.count() == 0


def test_secrets_never_reach_disk(tmp_path):
    h = make(tmp_path)
    h.add("encrypt AES", "encrypted 5 bytes", input_preview="plain-secret-text", output_preview="cipher",
          params={"password": "hunter2", "aes_key": "deadbeef", "Passphrase": "hunter2", "algorithm": "AES-256-GCM", "iterations": 600000})
    h.add("encode", "ok", params={"api_token": "hunter2", "charset": "UTF-8"})
    blob = b"".join(p.read_bytes() for p in tmp_path.iterdir())
    for needle in (b"hunter2", b"deadbeef", b"plain-secret-text"):
        assert needle not in blob
    rec = h.list()[1]
    assert rec.params == {"algorithm": "AES-256-GCM", "iterations": 600000} and rec.input_preview == ""


def test_previews_can_be_disabled_and_records_pruned(tmp_path):
    h = make(tmp_path, store_previews=False, max_records=10)
    for i in range(15):
        h.add("encode", f"r{i}", input_preview="abc")
    assert h.count() == 10 and h.list()[0].input_preview == ""


def test_scrub_params_drops_nested_and_long():
    out = scrub_params({"a": [1], "b": "x" * 500, "c": 3, "keyboard": 1})
    assert out == {"b": "x" * 100, "c": 3}


def test_settings_never_contain_secrets_and_clamp(tmp_path):
    s = Settings(max_file_mb=9999, pbkdf2_iterations=5)
    s.save(tmp_path / "s.json")
    import json
    stored = json.loads((tmp_path / "s.json").read_text())
    # only known, non-secret fields; every value is a plain bool/int/short string
    assert set(stored) == {f.name for f in __import__("dataclasses").fields(Settings)}
    assert all(isinstance(v, (bool, int, str)) for v in stored.values())
    assert not any(k in stored for k in ("password", "key", "secret", "passphrase"))
    loaded = Settings.load(tmp_path / "s.json")
    assert loaded.max_file_mb == 100 and loaded.pbkdf2_iterations == 100_000
    (tmp_path / "bad.json").write_text("{not json")
    assert Settings.load(tmp_path / "bad.json") == Settings()


def test_log_redaction():
    rec = logging.LogRecord("cipherlab", logging.INFO, "", 0, "encrypting password=hunter2 key: abcd", None, None)
    RedactingFilter().filter(rec)
    assert "hunter2" not in rec.msg and "abcd" not in rec.msg and "[REDACTED]" in rec.msg
