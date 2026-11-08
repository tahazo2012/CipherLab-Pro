"""Safe logging: secrets and sensitive content must never reach the log file."""
import logging

import pytest

from src.utils.logging_config import RedactingFilter, setup_logging


@pytest.fixture(autouse=True)
def _clean_logger():
    yield
    logger = logging.getLogger("cipherlab")
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
    logger.setLevel(logging.NOTSET)


def log_text(folder) -> str:
    for handler in logging.getLogger("cipherlab").handlers:
        handler.flush()
    return (folder / "cipherlab.log").read_text(encoding="utf-8")


@pytest.mark.parametrize("message,secret", [
    ("opening vault password=hunter2", "hunter2"),
    ("key: deadbeefdeadbeef", "deadbeefdeadbeef"),
    ("token=abc123XYZ and more", "abc123XYZ"),
    ('passphrase = "correct horse battery"', "horse"),
    ("secret='two words'", "words"),
    ("HMAC_KEY=00ff00ff", "00ff00ff"),
    ("Password: پسورد-فارسی", "پسورد"),
])
def test_secret_values_are_masked(tmp_path, message, secret):
    log = setup_logging(tmp_path)
    log.info(message)
    text = log_text(tmp_path)
    assert secret not in text and "[REDACTED]" in text


def test_message_arguments_are_masked_too(tmp_path):
    log = setup_logging(tmp_path)
    log.warning("login with password=%s", "hunter2")
    assert "hunter2" not in log_text(tmp_path)


def test_exception_message_and_traceback_are_withheld(tmp_path):
    log = setup_logging(tmp_path)
    try:
        raise ValueError("decrypted text was: top-secret-message-42")
    except ValueError:
        log.exception("task failed")
    text = log_text(tmp_path)
    assert "ValueError" in text and "top-secret-message-42" not in text and "Traceback" not in text


def test_normal_text_is_untouched_and_children_share_the_file(tmp_path):
    setup_logging(tmp_path)
    logging.getLogger("cipherlab.gui").info("window opened; 3 tabs ready; keyboard layout ok")
    text = log_text(tmp_path)
    assert "window opened; 3 tabs ready; keyboard layout ok" in text and "[REDACTED]" not in text


def test_levels_and_missing_or_unwritable_folder(tmp_path):
    log = setup_logging(tmp_path, level=logging.INFO)
    log.debug("debug detail")
    assert "debug detail" not in log_text(tmp_path)
    log = setup_logging(tmp_path, level=logging.DEBUG)
    log.debug("debug detail")
    assert "debug detail" in log_text(tmp_path)
    log = setup_logging(None)                                  # no folder -> silent, never crashes
    log.error("nothing is written")
    blocker = tmp_path / "a-file"
    blocker.write_text("x")
    setup_logging(blocker / "sub").error("folder cannot be created")   # OSError handled


def test_failed_background_task_logs_only_the_exception_type(tmp_path):
    pytest.importorskip("PySide6")
    from src.gui.context import Worker
    log = setup_logging(tmp_path, level=logging.DEBUG)

    def boom(progress, cancel):
        raise ValueError("my password is hunter2")

    Worker(1, boom).run()                                       # runs synchronously
    text = log_text(tmp_path)
    assert "ValueError" in text and "hunter2" not in text and log is not None


def test_core_modules_never_log_anything(caplog):
    """The cryptographic and analysis code has no logging calls: nothing can leak from it."""
    from src.core import crypto_engine as ce
    from src.core.hex_analyzer import analyze_hex
    from src.core.xor_cipher import decrypt_hex, encrypt_text
    caplog.set_level(logging.DEBUG)
    env = ce.encrypt_with_password(b"secret data", "hunter2", iterations=100_000)
    ce.decrypt_json(env.to_json(), password="hunter2")
    with pytest.raises(ce.DecryptionError):
        ce.decrypt_with_password(env, "wrong")
    decrypt_hex(encrypt_text("سلام 😀", "a1b2c3"), "a1b2c3")
    analyze_hex("48656c6c6f")
    assert caplog.records == []
