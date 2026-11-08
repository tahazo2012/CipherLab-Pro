"""Decrypt tab: CipherLab Pro AES-GCM containers and repeating-key XOR."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSplitter,
                               QVBoxLayout)

from src.core import crypto_engine as ce
from src.core.xor_tools import XorError, parse_key, xor_repeating
from src.gui.widgets import BaseTab, TextPane
from src.models.crypto_envelope import EnvelopeError
from src.utils.validation import ValidationError, hex_to_bytes

ALGOS = ["AES-GCM container (JSON from the Encrypt tab)", "Repeating-key XOR (input as hex)"]


class DecryptTab(BaseTab):
    title = "Decrypt"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.input = TextPane(ctx, "Encrypted data", placeholder="Paste the CipherLab Pro JSON container (or XOR hex)")
        self.output = TextPane(ctx, "Decrypted result", read_only=True)
        self.algo = QComboBox()
        self.algo.addItems(ALGOS)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Password (never saved or logged)")
        self.show_pw = QCheckBox("Show")
        self.show_pw.toggled.connect(lambda on: self.password.setEchoMode(QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password))
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setPlaceholderText("Raw key (AES key-mode / XOR; never saved or logged)")
        self.key_mode = QComboBox()
        self.key_mode.addItems(["Key as hex", "Key as text"])
        self.run_btn = QPushButton("Decrypt")
        self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self.run)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Algorithm:"))
        row1.addWidget(self.algo)
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
        self.input.changed.connect(self.update_counts)

    def run(self) -> None:
        self.clear_error()
        self.show_warning("")
        text = self.input.text()
        password, xor_mode = self.password.text(), self.algo.currentIndex() == 1
        try:
            if xor_mode:
                data = hex_to_bytes(text)
                key = parse_key(self.key.text(), "hex" if self.key_mode.currentIndex() == 0 else "text")
            else:
                data, key = b"", None
                if self.key.text():
                    key = parse_key(self.key.text(), "hex" if self.key_mode.currentIndex() == 0 else "text")
        except (ValidationError, XorError) as exc:
            self.show_error(str(exc))
            return

        def work(progress, cancel):
            if xor_mode:
                return xor_repeating(data, key)
            return ce.decrypt_json(text, password=password or None, key=key)

        self.run_btn.setEnabled(False)
        self.ctx.runner.submit(work, lambda r: self._done(r, xor_mode), self._failed)
        if self.ctx.settings.clear_password_after_use:
            self.password.clear()

    def _failed(self, message: str) -> None:
        self.run_btn.setEnabled(True)
        self.output.clear()
        self.show_error(message)

    def _done(self, plaintext: bytes, xor_mode: bool) -> None:
        self.run_btn.setEnabled(True)
        try:
            shown = plaintext.decode("utf-8")
            note = ""
        except UnicodeDecodeError:
            shown, note = plaintext.hex(" "), "Decrypted bytes are not valid UTF-8, so they are shown as hexadecimal."
        if xor_mode:
            note = (note + " " if note else "") + "XOR has no authentication: a wrong key silently gives garbage."
        self.show_warning(note)
        self.output.set_text(shown)
        self.ctx.bus.message.emit(f"Decrypted {len(plaintext):,} bytes.")
        self.ctx.history.add("decrypt", ("XOR" if xor_mode else "AES-GCM") + f" → {len(plaintext)} bytes",
                             params={"algorithm": "XOR" if xor_mode else "AES-GCM", "bytes": len(plaintext)})

    def clear_all(self) -> None:
        self.input.clear()
        self.output.clear()
        self.password.clear()
        self.key.clear()
        self.clear_error()
        self.show_warning("")

    def update_counts(self) -> None:
        self.emit_counts(self.input.text())

    def input_pane(self):
        return self.input

    def output_pane(self):
        return self.output
