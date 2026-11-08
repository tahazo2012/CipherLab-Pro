"""History tab: browse, search, delete single records or clear everything."""
from __future__ import annotations

from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout)

from src.gui.widgets import BaseTab


class HistoryTab(BaseTab):
    title = "History"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search history…")
        self.search.textChanged.connect(self.refresh)
        self.enabled = QCheckBox("Record history")
        self.enabled.setChecked(ctx.settings.history_enabled)
        self.enabled.toggled.connect(self._toggle)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Time (UTC)", "Operation", "Summary", "Input preview"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        delete = QPushButton("Delete selected")
        delete.clicked.connect(self.delete_selected)
        clear = QPushButton("Clear all")
        clear.clicked.connect(self.clear_history)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        note = QLabel(f"Stored locally in {ctx.history.db_path}. Passwords and keys are never stored; encrypt/decrypt records keep no content.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        row = QHBoxLayout()
        row.addWidget(self.search, 1)
        for w in (self.enabled, refresh, delete, clear):
            row.addWidget(w)
        layout = QVBoxLayout(self)
        layout.addLayout(row)
        layout.addWidget(note)
        layout.addWidget(self.table, 1)
        self._ids: list[int] = []

    def refresh(self) -> None:
        try:
            records = self.ctx.history.list(self.search.text())
        except Exception as exc:  # noqa: BLE001 - e.g. unreadable database
            self.show_error(f"Cannot read history: {exc}")
            return
        self._ids = [r.id for r in records]
        self.table.setRowCount(len(records))
        for row, r in enumerate(records):
            for col, v in enumerate((r.timestamp, r.operation, r.summary, r.input_preview.replace("\n", " ⏎ "))):
                self.table.setItem(row, col, QTableWidgetItem(v))

    def _toggle(self, on: bool) -> None:
        self.ctx.settings.history_enabled = on
        self.ctx.apply_settings()
        try:
            self.ctx.settings.save()
        except OSError:
            pass

    def delete_selected(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        for r in rows:
            if r < len(self._ids):
                self.ctx.history.delete(self._ids[r])
        self.refresh()

    def clear_history(self) -> None:
        if QMessageBox.question(self, "Clear history", "Delete ALL history records?") == QMessageBox.StandardButton.Yes:
            self.ctx.history.clear()
            self.refresh()
