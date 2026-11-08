"""XOR Decoder tab: encrypted HEX + the same custom HEX password -> original UTF-8 text."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSplitter, QVBoxLayout

from src.core.xor_cipher import XorCipherError, decrypt_hex
from src.gui.widgets import BaseTab, TextPane
from src.gui.xor_password import HexPasswordBox

WARNING = ("XOR has no integrity check: a wrong password gives different bytes, "
           "and only valid UTF-8 can be shown as text.")


class XorDecoderTab(BaseTab):
    title = "XOR Decoder"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.input = TextPane(ctx, "Encrypted HEX data", placeholder="Paste the encrypted HEX output…")
        self.output = TextPane(ctx, "Decrypted text (UTF-8)", read_only=True)
        self.pw = HexPasswordBox()
        self.run_btn = QPushButton("Decrypt")
        self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self.run)
        self.clear_btn = QPushButton("Clear all")
        self.clear_btn.clicked.connect(self.clear_all)
        row = QHBoxLayout()
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
            result = decrypt_hex(self.input.text(), self.pw.text(), strict_even=self.pw.strict())
        except XorCipherError as exc:
            self.output.clear()
            self.show_error(str(exc))
            return
        if result.text is None:
            # keep the raw result visible so nothing is lost, but do not pretend it is text
            self.output.set_text(result.data.hex(" "))
            self.show_error(result.utf8_error + " The raw bytes are shown below as hexadecimal.")
            return
        self.output.set_text(result.text)
        self.ctx.bus.message.emit(f"XOR decrypted {len(result.data):,} bytes.")
        self.ctx.history.add("decrypt xor", f"XOR Decoder: {len(result.data)} bytes",
                             params={"algorithm": "XOR", "bytes": len(result.data)})

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
