"""Compare Results tab: candidates side by side (one column per candidate)."""
from __future__ import annotations

import json

from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from src.core.file_handler import FileHandlerError, write_text
from src.gui.widgets import BaseTab
from src.models.analysis_result import Candidate

ROWS = ["Method", "Score", "Quality × prior", "Confidence", "Printable ratio", "Decoding errors", "Entropy (bits/byte)",
        "Key (hex)", "Output preview", "Why"]


class CompareTab(BaseTab):
    title = "Compare Results"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.candidates: list[Candidate] = []
        self.table = QTableWidget(len(ROWS), 0)
        self.table.setVerticalHeaderLabels(ROWS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.hint = QLabel("Send candidates here from the Hex Analyzer or XOR Analyzer tabs to compare them side by side.")
        self.hint.setObjectName("muted")
        remove = QPushButton("Remove selected column")
        remove.clicked.connect(self.remove_selected)
        clear = QPushButton("Clear")
        clear.clicked.connect(self.clear_all)
        export = QPushButton("Export JSON…")
        export.clicked.connect(self.export_json)
        row = QHBoxLayout()
        for b in (remove, clear, export):
            row.addWidget(b)
        row.addStretch(1)
        layout = QVBoxLayout(self)
        layout.addWidget(self.hint)
        layout.addLayout(row)
        layout.addWidget(self.table, 1)

    def add_candidates(self, cands: list[Candidate]) -> None:
        for c in cands:
            if c not in self.candidates:
                self.candidates.append(c)
        self._rebuild()

    def _rebuild(self) -> None:
        self.table.setColumnCount(len(self.candidates))
        self.table.setHorizontalHeaderLabels([f"#{i + 1}" for i in range(len(self.candidates))])
        for col, c in enumerate(self.candidates):
            values = [c.method, f"{c.score:.3f}", f"{c.quality:.3f} × {c.prior:.2f}", c.confidence, f"{c.printable_ratio:.1%}",
                      str(c.decoding_errors), f"{c.entropy:.3f}", c.key.hex() if c.key else "—", c.preview(160),
                      "\n".join(c.explanation)]
            for r, v in enumerate(values):
                self.table.setItem(r, col, QTableWidgetItem(v))
        self.table.resizeRowsToContents()

    def remove_selected(self) -> None:
        cols = sorted({i.column() for i in self.table.selectedIndexes()}, reverse=True)
        for col in cols:
            if col < len(self.candidates):
                del self.candidates[col]
        self._rebuild()

    def clear_all(self) -> None:
        self.candidates.clear()
        self._rebuild()

    def export_json(self) -> None:
        if not self.candidates:
            self.show_error("Nothing to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export comparison", "comparison.json", "JSON (*.json)",
                                              options=QFileDialog.Option.DontConfirmOverwrite)
        if not path:
            return
        payload = json.dumps([c.to_dict() for c in self.candidates], indent=2, ensure_ascii=False)
        try:
            try:
                write_text(path, payload, overwrite=False)
            except FileExistsError:
                if QMessageBox.question(self, "Overwrite?", f"'{path}' exists. Overwrite it?") != QMessageBox.StandardButton.Yes:
                    return
                write_text(path, payload, overwrite=True)
        except FileHandlerError as exc:
            QMessageBox.warning(self, "Export failed", str(exc))
