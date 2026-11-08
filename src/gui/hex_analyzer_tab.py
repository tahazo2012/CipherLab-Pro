"""Hex Analyzer tab: runs the local analysis engine in a background worker."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QPushButton, QSpinBox, QSplitter, QVBoxLayout

from src.core.hex_analyzer import AnalyzerOptions, analyze_hex
from src.gui.widgets import BaseTab, CandidateView, FileDropEdit, TextPane
from src.models.analysis_result import AnalysisReport


class HexAnalyzerTab(BaseTab):
    title = "Hex Analyzer"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.input = TextPane(ctx, "Hexadecimal input", placeholder="dcdcdcd324ad81ad8254dcdbddfcdcc7dcde24ad81af88acb0af88")
        self.input.edit.setMaximumHeight(110)
        self.repeat = QCheckBox("Include bounded repeating-key XOR analysis")
        self.maxkey = QSpinBox()
        self.maxkey.setRange(2, 64)
        self.maxkey.setValue(24)
        self.maxkey.setPrefix("max key length ")
        self.run_btn = QPushButton("Analyze")
        self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self.run)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.ctx.runner.cancel_all)
        self.summary = FileDropEdit("The analysis report appears here.", read_only=True)
        self.view = CandidateView(ctx)
        row = QHBoxLayout()
        for w in (self.repeat, self.maxkey):
            row.addWidget(w)
        row.addStretch(1)
        row.addWidget(self.cancel_btn)
        row.addWidget(self.run_btn)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.summary)
        split.addWidget(self.view)
        split.setSizes([450, 550])
        layout = QVBoxLayout(self)
        layout.addWidget(self.input)
        layout.addLayout(row)
        layout.addWidget(self.error_label)
        layout.addWidget(split, 1)
        self.input.changed.connect(self.update_counts)

    def options(self) -> AnalyzerOptions:
        s = self.ctx.settings
        return AnalyzerOptions(persian_enabled=s.persian_scoring, persian_table=s.persian_table(),
                               repeating_xor=self.repeat.isChecked(), max_key_len=self.maxkey.value(),
                               max_bytes=min(s.max_file_bytes, 1_048_576))

    def run(self) -> None:
        self.clear_error()
        text, opts = self.input.text(), self.options()
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.ctx.runner.submit(lambda progress, cancel: analyze_hex(text, opts, progress=progress, cancel=cancel),
                               self._done, self._failed)

    def _failed(self, message: str) -> None:
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.show_error(message)

    def _done(self, rep: AnalysisReport) -> None:
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.summary.setPlainText(rep.to_text())
        self.view.set_candidates(rep.candidates)
        verdict = "inconclusive" if rep.inconclusive else "see candidates"
        self.ctx.bus.message.emit(f"Analysis finished: {rep.input_info.get('bytes', '?')} bytes, {verdict}.")
        self.ctx.history.add("hex-analyze", f"{rep.input_info.get('bytes', '?')} bytes, {verdict}",
                             input_preview=self.input.text(), params={"repeating_xor": self.repeat.isChecked()})

    def clear_all(self) -> None:
        self.input.clear()
        self.summary.clear()
        self.view.set_candidates([])
        self.clear_error()

    def update_counts(self) -> None:
        self.emit_counts(self.input.text())

    def input_pane(self):
        return self.input
