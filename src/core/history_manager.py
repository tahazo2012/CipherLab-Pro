"""Optional local history in SQLite. Secrets are never stored.

Privacy rules enforced here (not left to callers):
* parameter names that look secret (password, key, secret, token, ...) are dropped;
* encrypt/decrypt/HMAC operations never store input/output previews;
* history can be disabled, cleared, or pruned per record; no network, no sync.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

PREVIEW_CHARS = 200
SECRET_NAME_PARTS = ("pass", "key", "secret", "token", "pwd", "credential")
NO_PREVIEW_OPERATIONS = ("encrypt", "decrypt", "hmac")


@dataclass
class HistoryRecord:
    id: int
    timestamp: str
    operation: str
    summary: str
    input_preview: str
    output_preview: str
    params: dict[str, Any]


def scrub_params(params: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Keep only short primitive values whose names do not look secret."""
    clean: dict[str, Any] = {}
    for name, value in (params or {}).items():
        if any(part in str(name).lower() for part in SECRET_NAME_PARTS):
            continue
        if isinstance(value, (int, float, bool)) or value is None:
            clean[str(name)] = value
        elif isinstance(value, str):
            clean[str(name)] = value[:100]
    return clean


class HistoryManager:
    def __init__(self, db_path: Path, *, enabled: bool = True, store_previews: bool = True, max_records: int = 1000):
        self.db_path = Path(db_path)
        self.enabled = enabled
        self.store_previews = store_previews
        self.max_records = max_records

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, operation TEXT NOT NULL,
            summary TEXT NOT NULL, input_preview TEXT NOT NULL DEFAULT '',
            output_preview TEXT NOT NULL DEFAULT '', params TEXT NOT NULL DEFAULT '{}')""")
        return conn

    def add(self, operation: str, summary: str, *, input_preview: str = "", output_preview: str = "",
            params: Optional[dict[str, Any]] = None) -> Optional[int]:
        """Store a record (no-op when disabled). Returns the new id or None."""
        if not self.enabled:
            return None
        if not self.store_previews or any(operation.lower().startswith(p) for p in NO_PREVIEW_OPERATIONS):
            input_preview = output_preview = ""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "INSERT INTO history (ts, operation, summary, input_preview, output_preview, params) VALUES (?,?,?,?,?,?)",
                (ts, operation[:60], summary[:300], input_preview[:PREVIEW_CHARS], output_preview[:PREVIEW_CHARS],
                 json.dumps(scrub_params(params))))
            conn.execute("DELETE FROM history WHERE id NOT IN (SELECT id FROM history ORDER BY id DESC LIMIT ?)",
                         (self.max_records,))
            return cur.lastrowid

    def list(self, search: str = "", limit: int = 500) -> list[HistoryRecord]:
        like = f"%{search}%"
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, ts, operation, summary, input_preview, output_preview, params FROM history "
                "WHERE operation LIKE ? OR summary LIKE ? OR input_preview LIKE ? ORDER BY id DESC LIMIT ?",
                (like, like, like, limit)).fetchall()
        return [HistoryRecord(r[0], r[1], r[2], r[3], r[4], r[5], json.loads(r[6] or "{}")) for r in rows]

    def count(self) -> int:
        with closing(self._connect()) as conn:
            return conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]

    def delete(self, record_id: int) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM history WHERE id = ?", (record_id,))

    def clear(self) -> None:
        with closing(self._connect()) as conn:
            with conn:
                conn.execute("DELETE FROM history")
            conn.execute("VACUUM")
