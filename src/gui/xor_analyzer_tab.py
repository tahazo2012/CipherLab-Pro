"""XOR Analyzer tab: key-length ranking, single-byte / repeating-key analysis, known-key XOR."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QSplitter,
                               QVBoxLayout)

from src.core.candidate_ranking import ScoringContext, build_candidate
from src.core.xor_tools import (XorError, break_repeating_key_xor, parse_key, rank_key_lengths,
                                single_byte_xor_analysis, xor_repeating)
from src.gui.widgets import BaseTab, CandidateView, FileDropEdit, TextPane
from src.utils.validation import ValidationError, hex_to_bytes


class XorAnalyzerTab(BaseTab):
    title = "XOR Analyzer"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.input = TextPane(ctx, "Input bytes", placeholder="Ciphertext as hex (or switch to UTF-8 text)")
        self.input.edit.setMaximumHeight(110)
        self.interp = QComboBox()
        self.interp.addItems(["Input is hexadecimal", "Input is UTF-8 text"])
        self.mode = QComboBox()
        self.mode.addItems(["Single-byte XOR analysis", "Repeating-key XOR analysis (bounded)"])
        self.maxkey = QSpinBox()
        self.maxkey.setRange(2, 64)
        self.maxkey.setValue(24)
        self.maxkey.setPrefix("max key length ")
        self.top = QSpinBox()
        self.top.setRange(1, 20)
        self.top.setValue(5)
        self.top.setPrefix("top ")
        self.run_btn = QPushButton("Analyze")
        self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self.run)
        self.key = QLineEdit()
        self.key.setPlaceholderText("Known key (never saved)")
        self.key_mode = QComboBox()
        self.key_mode.addItems(["Key as hex", "Key as text"])
        self.apply_btn = QPushButton("Apply key")
        self.apply_btn.clicked.connect(self.apply_key)
        self.lengths = FileDropEdit("Key-length ranking appears here.", read_only=True)
        self.view = CandidateView(ctx)
        warn = QLabel("XOR is not secure encryption. Results are statistical guesses; readable output is evidence, not proof.")
        warn.setObjectName("muted")
        warn.setWordWrap(True)
        r1 = QHBoxLayout()
        for w in (self.interp, self.mode, self.maxkey, self.top):
            r1.addWidget(w)
        r1.addStretch(1)
        r1.addWidget(self.run_btn)
        r2 = QHBoxLayout()
        for w in (self.key, self.key_mode, self.apply_btn):
            r2.addWidget(w)
        left = QSplitter(Qt.Orientation.Vertical)
        left.addWidget(self.lengths)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.lengths)
        split.addWidget(self.view)
        split.setSizes([300, 700])
        layout = QVBoxLayout(self)
        layout.addWidget(warn)
        layout.addWidget(self.input)
        layout.addLayout(r1)
        layout.addLayout(r2)
        layout.addWidget(self.error_label)
        layout.addWidget(split, 1)
        self.input.changed.connect(self.update_counts)

    def _data(self) -> bytes:
        text = self.input.text()
        if self.interp.currentIndex() == 0:
            return hex_to_bytes(text)
        if not text:
            raise ValidationError("Input is empty.")
        return text.encode("utf-8")

    def _ctx(self) -> ScoringContext:
        return ScoringContext(self.ctx.settings.persian_scoring, self.ctx.settings.persian_table())

    def run(self) -> None:
        self.clear_error()
        try:
            data = self._data()
        except ValidationError as exc:
            self.show_error(str(exc))
            return
        s = self.ctx.settings
        repeating, maxlen, top = self.mode.currentIndex() == 1, self.maxkey.value(), self.top.value()
        table = s.persian_table()
        sctx = self._ctx()

        def work(progress, cancel):
            lengths = [(x.length, x.distance) for x in rank_key_lengths(data, max_len=maxlen)] if repeating else []
            if repeating:
                found = break_repeating_key_xor(data, max_key_len=maxlen, persian_enabled=s.persian_scoring,
                                                persian_table=table, progress=progress, cancel=cancel)[:top]
            else:
                found = single_byte_xor_analysis(data, top=top, persian_enabled=s.persian_scoring,
                                                 persian_table=table, cancel=cancel)
            kind = "xorN" if repeating else "xor1"
            cands = [build_candidate(c.method, c.output, kind=kind, ctx=sctx, key=c.key) for c in found]
            cands.sort(key=lambda c: c.score, reverse=True)
            return lengths, cands

        self.run_btn.setEnabled(False)
        self.ctx.runner.submit(work, lambda r: self._done(r, len(data)), self._failed)

    def _failed(self, message: str) -> None:
        self.run_btn.setEnabled(True)
        self.show_error(message)

    def _done(self, result, n: int) -> None:
        self.run_btn.setEnabled(True)
        lengths, cands = result
        if lengths:
            self.lengths.setPlainText("Key-length ranking (lower = more likely;\nmultiples of the true length also score well)\n\n"
                                      + "\n".join(f"length {a:>2}: {b:.3f} bits/byte" for a, b in lengths[:15]))
        else:
            self.lengths.setPlainText("Key-length ranking applies to repeating-key analysis.\n" if self.mode.currentIndex() == 0
                                      else "Input too short: need at least two blocks of the key length.\n")
        self.view.set_candidates(cands)
        if not cands:
            self.show_error("No candidates could be produced for this input (too short for the chosen analysis?).")
        self.ctx.history.add("xor-analyze", f"{n} bytes, {self.mode.currentText()}", params={"bytes": n})
        self.ctx.bus.message.emit(f"XOR analysis finished: {len(cands)} candidate(s).")

    def apply_key(self) -> None:
        self.clear_error()
        try:
            data = self._data()
            key = parse_key(self.key.text(), "hex" if self.key_mode.currentIndex() == 0 else "text")
        except (ValidationError, XorError) as exc:
            self.show_error(str(exc))
            return
        cand = build_candidate(f"XOR with known key ({len(key)} byte(s))", xor_repeating(data, key), kind="xorN",
                               ctx=self._ctx(), key=key)
        self.view.set_candidates([cand])

    def clear_all(self) -> None:
        self.input.clear()
        self.key.clear()
        self.lengths.clear()
        self.view.set_candidates([])
        self.clear_error()

    def update_counts(self) -> None:
        self.emit_counts(self.input.text())

    def input_pane(self):
        return self.input
