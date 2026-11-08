"""Safe local file import/export. Files are only read as data, never executed or uploaded."""
from __future__ import annotations

import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_MAX_BYTES = 10 * 1024 * 1024
KIND_BY_EXT = {".txt": "txt", ".hex": "hex", ".json": "json", ".bin": "bin"}


class FileHandlerError(Exception):
    """Friendly, user-facing file error."""


@dataclass
class LoadedFile:
    path: Path
    kind: str                # txt | hex | json | bin
    data: bytes              # exact original bytes (never modified)
    text: Optional[str]      # strict UTF-8 text, or None if not valid UTF-8
    note: str = ""


def read_file_bytes(path: str | Path, max_bytes: int = DEFAULT_MAX_BYTES) -> bytes:
    p = Path(path)
    try:
        st = p.stat()
    except OSError as exc:
        raise FileHandlerError(f"Cannot access '{p.name}': {exc.strerror or exc}.") from exc
    if not stat.S_ISREG(st.st_mode):
        raise FileHandlerError(f"'{p.name}' is not a regular file.")
    if st.st_size > max_bytes:
        raise FileHandlerError(f"'{p.name}' is {st.st_size:,} bytes; the limit is {max_bytes:,} bytes (see Settings).")
    try:
        with open(p, "rb") as fh:
            data = fh.read(max_bytes + 1)
    except OSError as exc:
        raise FileHandlerError(f"Cannot read '{p.name}': {exc.strerror or exc}.") from exc
    if len(data) > max_bytes:
        raise FileHandlerError(f"'{p.name}' grew beyond the {max_bytes:,}-byte limit while reading.")
    return data


def load_file(path: str | Path, max_bytes: int = DEFAULT_MAX_BYTES) -> LoadedFile:
    """Read a file, keeping the original bytes; unknown extensions are treated as binary."""
    p = Path(path)
    data = read_file_bytes(p, max_bytes)
    kind = KIND_BY_EXT.get(p.suffix.lower(), "bin")
    try:
        text: Optional[str] = data.decode("utf-8")
        note = ""
    except UnicodeDecodeError:
        text, note = None, "File is not valid UTF-8; treat it as binary."
    if kind in ("txt", "hex", "json") and text is None:
        kind = "bin"
    return LoadedFile(p, kind, data, text, note)


def write_bytes(path: str | Path, data: bytes, *, overwrite: bool = False, max_bytes: int = DEFAULT_MAX_BYTES * 10) -> None:
    """Write atomically. Raises FileExistsError unless ``overwrite`` is True."""
    p = Path(path)
    if len(data) > max_bytes:
        raise FileHandlerError(f"Refusing to write {len(data):,} bytes (limit {max_bytes:,}).")
    if p.exists() and not overwrite:
        raise FileExistsError(str(p))
    if p.is_dir():
        raise FileHandlerError(f"'{p.name}' is a directory.")
    try:
        fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".cipherlab-", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
            os.replace(tmp, p)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    except OSError as exc:
        raise FileHandlerError(f"Cannot write '{p.name}': {exc.strerror or exc}.") from exc


def write_text(path: str | Path, text: str, *, overwrite: bool = False) -> None:
    write_bytes(path, text.encode("utf-8"), overwrite=overwrite)
