"""Encode tab: text → bytes (chosen charset) → chosen representation."""
from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QSplitter, QVBoxLayout
from PySide6.QtCore import Qt

from src.core.encodings import ByteFormat, EncodingError, TEXT_CHARSETS, encode_bytes, text_to_bytes
from src.gui.widgets import BaseTab, TextPane


class EncodeTab(BaseTab):
    title = "Encode"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.input = TextPane(ctx, "Text to encode", placeholder="Type or paste text (Persian, Arabic, English, emoji…)")
        self.output = TextPane(ctx, "Encoded result", read_only=True)
        self.charset = QComboBox()
        self.charset.addItems(TEXT_CHARSETS)
        self.charset.setCurrentText(ctx.settings.default_charset if ctx.settings.default_charset in TEXT_CHARSETS else "UTF-8")
        self.fmt = QComboBox()
        self.fmt.addItems([f.value for f in ByteFormat])
        self.sep = QComboBox()
        self.sep.addItems(["Hex separator: space", "Hex separator: none"])
        self.upper = QCheckBox("Uppercase hex")
        self.run_btn = QPushButton("Encode")
        self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self.run)
        row = QHBoxLayout()
        for w in (QLabel("Text encoding:"), self.charset, QLabel("Output format:"), self.fmt, self.sep, self.upper):
            row.addWidget(w)
        row.addStretch(1)
        row.addWidget(self.run_btn)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.input)
        split.addWidget(self.output)
        layout = QVBoxLayout(self)
        layout.addLayout(row)
        layout.addWidget(self.error_label)
        layout.addWidget(split, 1)
        self.input.changed.connect(self.update_counts)

    def run(self) -> None:
        self.clear_error()
        text = self.input.text()
        if not text:
            self.show_error("Input is empty.")
            return
        fmt = list(ByteFormat)[self.fmt.currentIndex()]
        charset = self.charset.currentText()
        try:
            data = text_to_bytes(text, charset)
            result = encode_bytes(data, fmt, hex_sep=" " if self.sep.currentIndex() == 0 else "",
                                  upper=self.upper.isChecked(), text_charset=charset)
        except EncodingError as exc:
            self.show_error(str(exc))
            return
        self.output.set_text(result)
        self.ctx.bus.message.emit(f"Encoded {len(data):,} bytes as {fmt.value}.")
        self.ctx.history.add("encode", f"{charset} → {fmt.value} ({len(data)} bytes)", input_preview=text,
                             output_preview=result, params={"charset": charset, "format": fmt.value})

    def clear_all(self) -> None:
        self.input.clear()
        self.output.clear()
        self.clear_error()

    def update_counts(self) -> None:
        self.emit_counts(self.input.text())

    def input_pane(self):
        return self.input

    def output_pane(self):
        return self.output
