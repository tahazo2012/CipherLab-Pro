"""Hex password input shared by the XOR Encoder and XOR Decoder tabs (live validation, no storage)."""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from src.core.xor_cipher import ParsedHex, XorCipherError, parse_hex_password
from src.gui.i18n import tr
from src.gui.theme import palette
from src.gui.widgets import mono_font


class HexPasswordBox(QWidget):
    """Label + password field + live status. The text is never saved, logged or modified."""

    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.label = QLabel("HEX password:")
        self.edit = QLineEdit()
        self.edit.setFont(mono_font())
        self.edit.setPlaceholderText("Hex digits, e.g. 0xA1B2C3 or 00ff10 (any length, 0x optional)")
        self.hide_chk = QCheckBox("Hide")
        self.hide_chk.toggled.connect(lambda on: self.edit.setEchoMode(
            QLineEdit.EchoMode.Password if on else QLineEdit.EchoMode.Normal))
        self.strict_chk = QCheckBox("Strict: reject odd-length passwords")
        self.status = QLabel()
        self.status.setWordWrap(True)
        top = QHBoxLayout()
        top.addWidget(self.label)
        top.addWidget(self.edit, 1)
        top.addWidget(self.hide_chk)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top)
        layout.addWidget(self.strict_chk)
        layout.addWidget(self.status)
        self.edit.textChanged.connect(self._on_change)
        self.strict_chk.toggled.connect(self._on_change)
        self.refresh()

    # -- values
    def text(self) -> str:
        """The password exactly as typed."""
        return self.edit.text()

    def strict(self) -> bool:
        return self.strict_chk.isChecked()

    def parsed(self) -> ParsedHex:
        return parse_hex_password(self.text(), strict_even=self.strict())

    def clear(self) -> None:
        self.edit.clear()

    # -- status line
    def _on_change(self, *_args) -> None:
        self.refresh()
        self.changed.emit()

    def refresh(self) -> None:
        """Re-evaluate the status line (also called after a theme or language change)."""
        p = palette()
        if not self.text().strip():
            self.status.setText(tr("Enter a HEX password (digits 0-9, a-f)"))
            self.status.setStyleSheet(f"color:{p['MUTED']};")
            return
        try:
            parsed = self.parsed()
        except XorCipherError as exc:
            self.status.setText("⚠ " + str(exc))
            self.status.setStyleSheet(f"color:{p['ERR']};")
            return
        msg = tr("Password OK: {n} byte(s), {m} hex digits. Key bytes: {k}").format(
            n=len(parsed.data), m=len(parsed.digits), k=parsed.preview())
        if parsed.padded:
            msg += "\n" + tr("A leading 0 was added because the digit count is odd (like 0x474 = 0x0474).")
        self.status.setText(msg)
        self.status.setStyleSheet(f"color:{p['OK']};")
