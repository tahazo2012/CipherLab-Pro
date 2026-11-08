"""XOR Encoder tab: plaintext (UTF-8) + custom HEX password -> HEX output."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QPushButton, QSplitter, QVBoxLayout

from src.core.xor_cipher import XorCipherError, encrypt_text
from src.gui.widgets import BaseTab, TextPane
from src.gui.xor_password import HexPasswordBox

WARNING = "Repeating-key XOR is NOT secure encryption. Use it for learning and simple obfuscation only."


class XorEncoderTab(BaseTab):
    title = "XOR Encoder"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.input = TextPane(ctx, "Plaintext", placeholder="Type or paste the text to encrypt…")
        self.output = TextPane(ctx, "Encrypted output (HEX)", read_only=True)
        self.pw = HexPasswordBox()
        self.sep = QComboBox()
        self.sep.addItems(["Output: bytes separated by spaces", "Output: continuous"])
        self.upper = QCheckBox("Uppercase hex")
        self.run_btn = QPushButton("Encrypt")
        self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self.run)
        self.clear_btn = QPushButton("Clear all")
        self.clear_btn.clicked.connect(self.clear_all)
        row = QHBoxLayout()
        row.addWidget(self.sep)
        row.addWidget(self.upper)
        row.addStretch(1)
        row.addWidget(self.clear_btn)
        row.addWidget(self.run_btn)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.input)
        split.addWidget(self.output)
        layout = QVBoxLayout(self)
        layout.addWidget(self.pw)
        layout.addLayout(row)
        layout.addWidget(self.warn_label)
        layout.addWidget(self.error_label)
        layout.addWidget(split, 1)
        self.show_warning(WARNING)
        self.input.changed.connect(self.update_counts)

    def run(self) -> None:
        self.clear_error()
        try:
            result = encrypt_text(self.input.text(), self.pw.text(), strict_even=self.pw.strict(),
                                  separator=" " if self.sep.currentIndex() == 0 else "", upper=self.upper.isChecked())
        except XorCipherError as exc:
            self.show_error(str(exc))
            return
        self.output.set_text(result)
        n = len(self.input.text().encode("utf-8"))
        self.ctx.bus.message.emit(f"XOR encrypted {n:,} bytes.")
        # operation names starting with "encrypt" never store previews; the password is never passed on
        self.ctx.history.add("encrypt xor", f"XOR Encoder: {n} bytes", params={"algorithm": "XOR", "bytes": n})

    def clear_all(self) -> None:
        self.input.clear()
        self.output.clear()
        self.pw.clear()
        self.clear_error()

    def update_counts(self) -> None:
        self.emit_counts(self.input.text())

    def apply_theme(self) -> None:
        self.pw.refresh()

    def refresh_language(self) -> None:
        self.show_warning(WARNING)
        self.pw.refresh()

    def input_pane(self):
        return self.input

    def output_pane(self):
        return self.output
