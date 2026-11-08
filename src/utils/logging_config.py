"""Local, redacting logging configuration (file in the app data folder only)."""
from __future__ import annotations

import logging
import logging.handlers
import re
from pathlib import Path

_REDACT = re.compile(
    r"""(?i)\b(password|passphrase|passwd|secret|token|key|hmac_key)\b(\s*[=:]\s*)("[^"]*"|'[^']*'|\S+)"""
)


class RedactingFilter(logging.Filter):
    """Second line of defence (the first is: never log content).

    * masks the value after secret-looking names (password=..., key: "a b", token='x');
    * replaces tracebacks by the exception TYPE only, because an exception message can contain anything the
      user typed (a password, a key, decrypted text).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        record.msg = _REDACT.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", message)
        record.args = ()
        if record.exc_info:
            exc_type = record.exc_info[0]
            record.msg += f" [exception type: {exc_type.__name__ if exc_type else 'unknown'}; message and traceback withheld]"
            record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True


def setup_logging(data_dir: Path | None = None, level: int = logging.INFO) -> logging.Logger:
    """Configure the ``cipherlab`` logger. Content is never logged by convention."""
    logger = logging.getLogger("cipherlab")
    logger.setLevel(level)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    handler: logging.Handler
    if data_dir is not None:
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
            handler = logging.handlers.RotatingFileHandler(
                data_dir / "cipherlab.log", maxBytes=256_000, backupCount=2, encoding="utf-8"
            )
        except OSError:
            handler = logging.NullHandler()
    else:
        handler = logging.NullHandler()
    handler.addFilter(RedactingFilter())
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    return logger
