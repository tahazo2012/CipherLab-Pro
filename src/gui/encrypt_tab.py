"""Encrypt tab: AES-GCM, educational XOR, and (non-encryption) hashes / HMAC."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSplitter,
                               QVBoxLayout)

from src.core import crypto_engine as ce
from src.core.encodings import EncodingError
from src.core.xor_tools import XorError, parse_key, xor_repeating
from src.gui.widgets import BaseTab, TextPane
from src.utils.validation import ValidationError, hex_to_bytes

ALGOS = [
    "AES-256-GCM (password)",
    "AES-GCM (raw key, hex)",
    "Repeating-key XOR (educational, NOT secure)",
    "SHA-256 hash (not encryption)",
    "SHA-512 hash (not encryption)",
    "HMAC-SHA256 (authentication, not encryption)",
    "HMAC-SHA512 (authentication, not encryption)",
]
WARNINGS = {
    2: "XOR with a repeating key is trivially breakable. Use it only to learn how XOR works.",
    3: "A hash is one-way and cannot be decrypted. It is neither encryption nor encoding.",
    4: "A hash is one-way and cannot be decrypted. It is neither encryption nor encoding.",
    5: "HMAC proves integrity/authenticity with a secret key; it does not hide the message.",
    6: "HMAC proves integrity/authenticity with a secret key; it does not hide the message.",
}


class EncryptTab(BaseTab):
    title = "Encrypt"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.input = TextPane(ctx, "Plaintext / message", placeholder="Message to encrypt or hash")
        self.output = TextPane(ctx, "Result", read_only=True)
        self.algo = QComboBox()
        self.algo.addItems(ALGOS)
        self.interp = QComboBox()
        self.interp.addItems(["Input is UTF-8 text", "Input is hexadecimal bytes"])
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Password (never saved or logged)")
        self.show_pw = QCheckBox("Show")
        self.show_pw.toggled.connect(lambda on: self.password.setEchoMode(QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password))
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("Key (never saved or logged)")
        self.key_mode = QComboBox()
        self.key_mode.addItems(["Key as text", "Key as hex"])
        self.run_btn = QPushButton("Run")
        self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self.run)
        row1 = QHBoxLayout()
        for w in (QLabel("Algorithm:"), self.algo, self.interp):
            row1.addWidget(w)
        row1.addStretch(1)
        row1.addWidget(self.run_btn)
        row2 = QHBoxLayout()
        for w in (self.password, self.show_pw, self.key, self.key_mode):
            row2.addWidget(w)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.input)
        split.addWidget(self.output)
        layout = QVBoxLayout(self)
        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addWidget(self.warn_label)
        layout.addWidget(self.error_label)
        layout.addWidget(split, 1)
        self.algo.currentIndexChanged.connect(self._algo_changed)
        self._algo_changed()
        self.input.changed.connect(self.update_counts)

    def _algo_changed(self) -> None:
        i = self.algo.currentIndex()
        self.password.setEnabled(i == 0)
        self.show_pw.setEnabled(i == 0)
        self.key.setEnabled(i in (1, 2, 5, 6))
        self.key_mode.setEnabled(i in (2, 5, 6))
        if i == 1:
            self.key_mode.setCurrentIndex(1)
        self.show_warning(WARNINGS.get(i, ""))

    def _plaintext(self) -> bytes:
        text = self.input.text()
        if self.interp.currentIndex() == 1:
            return hex_to_bytes(text)
        return text.encode("utf-8")

    def _key_bytes(self, hex_only: bool = False) -> bytes:
        mode = "hex" if hex_only or self.key_mode.currentIndex() == 1 else "text"
        return parse_key(self.key.text(), mode)

    def run(self) -> None:
        self.clear_error()
        i = self.algo.currentIndex()
        try:
            data = self._plaintext()
            if i == 0 and not self.password.text():
                raise ce.CryptoError("Enter a password.")
            password = self.password.text()
            key = self._key_bytes(hex_only=(i == 1)) if i in (1, 2, 5, 6) else b""
        except (ValidationError, EncodingError, XorError, ce.CryptoError) as exc:
            self.show_error(str(exc))
            return
        iterations = self.ctx.settings.pbkdf2_iterations

        def work(progress, cancel):
            if i == 0:
                return ce.encrypt_with_password(data, password, iterations=iterations).to_json()
            if i == 1:
                return ce.encrypt_with_key(data, key).to_json()
            if i == 2:
                return xor_repeating(data, key).hex(" ")
            if i in (3, 4):
                return ce.hash_bytes(data, "SHA-256" if i == 3 else "SHA-512").hex()
            return ce.hmac_digest(key, data, "SHA-256" if i == 5 else "SHA-512").hex()

        self.run_btn.setEnabled(False)
        self.ctx.runner.submit(work, lambda res: self._done(res, i, len(data)), self._failed)
        if self.ctx.settings.clear_password_after_use:
            self.password.clear()

    def _failed(self, message: str) -> None:
        self.run_btn.setEnabled(True)
        self.show_error(message)

    def _done(self, result: str, i: int, n: int) -> None:
        self.run_btn.setEnabled(True)
        self.output.set_text(result)
        name = ALGOS[i].split(" (")[0]
        self.ctx.bus.message.emit(f"{name}: processed {n:,} bytes.")
        op = "hmac" if i in (5, 6) else "encrypt"
        self.ctx.history.add(op, f"{name} on {n} bytes", params={"algorithm": name, "bytes": n})

    def clear_all(self) -> None:
        self.input.clear()
        self.output.clear()
        self.password.clear()
        self.key.clear()
        self.clear_error()

    def update_counts(self) -> None:
        self.emit_counts(self.input.text())

    def input_pane(self):
        return self.input

    def output_pane(self):
        return self.output
