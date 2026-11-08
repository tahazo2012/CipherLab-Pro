"""Local settings stored as JSON in the application data folder (never contains secrets)."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Optional

from src.core.crypto_engine import DEFAULT_ITERATIONS
from src.core.statistics import DEFAULT_PERSIAN_FREQ, normalize_persian_table
from src.models.crypto_envelope import MAX_ITERATIONS, MIN_ITERATIONS


def get_data_dir() -> Path:
    """Folder for settings, history and logs. Override with CIPHERLAB_DATA_DIR."""
    override = os.environ.get("CIPHERLAB_DATA_DIR")
    if override:
        return Path(override)
    if sys.platform.startswith("win"):
        return Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "CipherLabPro"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "CipherLabPro"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "CipherLabPro"


@dataclass
class Settings:
    history_enabled: bool = True
    history_store_previews: bool = True
    max_history_records: int = 1000
    max_file_mb: int = 10
    pbkdf2_iterations: int = DEFAULT_ITERATIONS
    clear_password_after_use: bool = True
    default_charset: str = "UTF-8"
    persian_scoring: bool = True
    persian_table_path: str = ""
    language: str = "en"  # en | fa | ar | zh | ru
    theme: str = "blue"  # blue | green

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_mb * 1024 * 1024

    def validate(self) -> "Settings":
        """Clamp values into safe ranges."""
        self.max_file_mb = max(1, min(100, int(self.max_file_mb)))
        self.max_history_records = max(10, min(100_000, int(self.max_history_records)))
        self.pbkdf2_iterations = max(MIN_ITERATIONS, min(MAX_ITERATIONS, int(self.pbkdf2_iterations)))
        if self.language not in ("en", "fa", "ar", "zh", "ru"):
            self.language = "en"
        if self.theme not in ("blue", "green"):
            self.theme = "blue"
        return self

    def persian_table(self) -> Optional[dict[str, float]]:
        """Configured Persian frequency table, or None for the built-in default."""
        if not self.persian_table_path:
            return None
        try:
            raw = json.loads(Path(self.persian_table_path).read_text(encoding="utf-8"))
            return normalize_persian_table(raw)
        except (OSError, ValueError, TypeError, AttributeError):
            return None

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        path = path or get_data_dir() / "settings.json"
        base = cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return base
        if isinstance(raw, dict):
            for f in fields(cls):
                if f.name in raw and isinstance(raw[f.name], type(getattr(base, f.name))):
                    setattr(base, f.name, raw[f.name])
        try:
            return base.validate()
        except (TypeError, ValueError):
            return cls()

    def save(self, path: Path | None = None) -> None:
        path = path or get_data_dir() / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self.validate()), indent=2), encoding="utf-8")


__all__ = ["Settings", "get_data_dir", "DEFAULT_PERSIAN_FREQ"]
