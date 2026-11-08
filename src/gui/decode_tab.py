"""Decode tab: representation → exact bytes → text (strict by default)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QSplitter, QVBoxLayout

from src.core.encodings import (ByteFormat, EncodingError, TEXT_CHARSETS, bytes_to_text, count_decode_errors,
                                decode_to_bytes, detect_formats)
from src.gui.widgets import BaseTab, TextPane

RAW_HEX = "Raw bytes as hexadecimal (no text decoding)"


class DecodeTab(BaseTab):
    title = "Decode"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.input = TextPane(ctx, "Encoded input", placeholder="e.g. 48 65 6c 6c 6f   or   SGVsbG8=   or   %D8%B3%D9%84%D8%A7%D9%85")
        self.output = TextPane(ctx, "Decoded result", read_only=True)
        self.fmt = QComboBox()
        self.fmt.addItems([f.value for f in ByteFormat])
        self.charset = QComboBox()
        self.charset.addItems(list(TEXT_CHARSETS) + [RAW_HEX])
        self.policy = QComboBox()
        self.policy.addItems(["Strict: report invalid bytes", "Replace invalid bytes with U+FFFD (lossy)"])
        self.detect_btn = QPushButton("Suggest format")
        self.detect_btn.setToolTip("List the formats the input could be written in (ambiguity is reported, not hidden)")
        self.detect_btn.clicked.connect(self.detect)
        self.run_btn = QPushButton("Decode")
        self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self.run)
        row = QHBoxLayout()
        for w in (QLabel("Input format:"), self.fmt, QLabel("Interpret bytes as:"), self.charset, self.policy, self.detect_btn):
            row.addWidget(w)
        row.addStretch(1)
        row.addWidget(self.run_btn)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.input)
        split.addWidget(self.output)
        layout = QVBoxLayout(self)
        layout.addLayout(row)
        layout.addWidget(self.error_label)
        layout.addWidget(self.warn_label)
        layout.addWidget(split, 1)
        self.input.changed.connect(self.update_counts)

    def detect(self) -> None:
        self.clear_error()
        guesses = detect_formats(self.input.text())
        if not guesses:
            self.show_error("The input is not syntactically valid in any supported format.")
            return
        self.output.set_text("\n".join(f"{g.fmt.value}: {g.note}" for g in guesses))
        self.show_warning("Suggestions are heuristics. Pick the format you expect; a valid parse does not prove it is the right one.")

    def run(self) -> None:
        self.clear_error()
        self.show_warning("")
        fmt = list(ByteFormat)[self.fmt.currentIndex()]
        try:
            data = decode_to_bytes(self.input.text(), fmt)
        except EncodingError as exc:
            self.show_error(str(exc))
            return
        is_raw = self.charset.currentIndex() == self.charset.count() - 1  # last item = raw hex
        charset = "raw hex" if is_raw else self.charset.currentText()
        if is_raw:
            result = data.hex(" ")
        else:
            lossy = self.policy.currentIndex() == 1
            try:
                result = bytes_to_text(data, charset, "replace" if lossy else "strict")
                if lossy and (n := count_decode_errors(data, charset)):
                    self.show_warning(f"{n} invalid sequence(s) were replaced with U+FFFD: the original bytes are NOT fully preserved.")
            except EncodingError as exc:
                self.show_error(f"{exc} The raw bytes are shown below as hexadecimal instead.")
                result = data.hex(" ")
        self.output.set_text(result)
        self.ctx.bus.message.emit(f"Decoded {len(data):,} bytes from {fmt.value}.")
        self.ctx.history.add("decode", f"{fmt.value} → {charset} ({len(data)} bytes)", input_preview=self.input.text(),
                             output_preview=result, params={"format": fmt.value, "charset": charset})

    def clear_all(self) -> None:
        self.input.clear()
        self.output.clear()
        self.clear_error()
        self.show_warning("")

    def update_counts(self) -> None:
        self.emit_counts(self.input.text())

    def input_pane(self):
        return self.input

    def output_pane(self):
        return self.output
