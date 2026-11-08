"""Reusable widgets: drag-and-drop text editors, text panes, candidate table, base tab."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QTextOption
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
                               QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from src.core.file_handler import FileHandlerError, load_file, write_bytes
from src.gui.context import AppContext
from src.gui.i18n import tr
from src.gui.theme import MONO_FAMILIES, palette
from src.models.analysis_result import Candidate


def mono_font(size: int = 11) -> QFont:
    font = QFont()
    font.setFamilies(MONO_FAMILIES)
    font.setPointSize(size)
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font


class FileDropEdit(QPlainTextEdit):
    """Plain-text editor that accepts a dropped local file and handles RTL/LTR text automatically."""

    fileDropped = Signal(str)

    def __init__(self, placeholder: str = "", read_only: bool = False):
        super().__init__()
        self.setAcceptDrops(not read_only)
        self.setReadOnly(read_only)
        self.setPlaceholderText(placeholder)
        self.setFont(mono_font())
        option = self.document().defaultTextOption()
        option.setTextDirection(Qt.LayoutDirection.LayoutDirectionAuto)
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.document().setDefaultTextOption(option)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.fileDropped.emit(urls[0].toLocalFile())  # read as data only; never executed
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class TextPane(QWidget):
    """Titled editor with Paste / Copy / Clear / Import / Export buttons."""

    changed = Signal()

    def __init__(self, ctx: AppContext, title: str, *, read_only: bool = False, placeholder: str = ""):
        super().__init__()
        self.ctx, self.read_only = ctx, read_only
        self.edit = FileDropEdit(placeholder, read_only)
        self.edit.textChanged.connect(self.changed)
        self.edit.fileDropped.connect(self.load_path)
        self.count_label = QLabel("")
        self.count_label.setObjectName("muted")
        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("paneTitle")
        header.addWidget(title_label)
        header.addStretch(1)
        header.addWidget(self.count_label)
        buttons = QHBoxLayout()
        self._buttons: dict[str, QPushButton] = {}

        def add(name: str, slot: Callable[[], None], tip: str) -> None:
            btn = QPushButton(name)
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            buttons.addWidget(btn)
            self._buttons[name] = btn

        if not read_only:
            add("Paste", self.paste, "Replace the content with the clipboard text")
        add("Copy", self.copy, "Copy to the clipboard")
        add("Clear", self.clear, "Clear this editor")
        if not read_only:
            add("Import…", self.import_dialog, "Load a TXT / HEX / JSON / binary file (or drop one here)")
        add("Export…", self.export_dialog, "Save the content to a file")
        buttons.addStretch(1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(header)
        layout.addWidget(self.edit, 1)
        layout.addLayout(buttons)
        self.edit.textChanged.connect(self._update_count)

    # -- content
    def text(self) -> str:
        return self.edit.toPlainText()

    def set_text(self, value: str) -> None:
        self.edit.setPlainText(value)

    def _update_count(self) -> None:
        t = self.text()
        self.count_label.setText(tr("{c} chars · {b} bytes (UTF-8)").format(
            c=f"{len(t):,}", b=f"{len(t.encode('utf-8', 'replace')):,}"))

    # -- actions
    def paste(self) -> None:
        self.set_text(QApplication.clipboard().text())

    def copy(self) -> None:
        QApplication.clipboard().setText(self.text())
        self.ctx.bus.message.emit("Copied to clipboard.")

    def clear(self) -> None:
        self.edit.clear()

    def load_path(self, path: str) -> None:
        try:
            loaded = load_file(path, self.ctx.settings.max_file_bytes)
        except FileHandlerError as exc:
            QMessageBox.warning(self, "Import failed", str(exc))
            return
        if loaded.text is not None:
            self.set_text(loaded.text)
            self.ctx.bus.message.emit(f"Imported {loaded.path.name} ({len(loaded.data):,} bytes).")
        else:
            self.set_text(loaded.data.hex(" "))
            self.ctx.bus.message.emit(f"{loaded.path.name} is binary: shown as hexadecimal ({len(loaded.data):,} bytes).")

    def import_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import file", "", "Supported (*.txt *.hex *.json *.bin);;All files (*)")
        if path:
            self.load_path(path)

    def export_dialog(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export", "", "Text (*.txt);;Hex (*.hex);;JSON (*.json);;All files (*)",
                                              options=QFileDialog.Option.DontConfirmOverwrite)
        if not path:
            return
        data = self.text().encode("utf-8")
        try:
            try:
                write_bytes(path, data, overwrite=False)
            except FileExistsError:
                if QMessageBox.question(self, "Overwrite?", f"'{path}' already exists. Overwrite it?") != QMessageBox.StandardButton.Yes:
                    return
                write_bytes(path, data, overwrite=True)
            self.ctx.bus.message.emit(f"Exported {len(data):,} bytes to {path}")
        except FileHandlerError as exc:
            QMessageBox.warning(self, "Export failed", str(exc))


class BaseTab(QWidget):
    """Common behaviour for the main tabs."""

    title = "Tab"

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.error_label = QLabel(self)   # parented: never a stray top-level widget
        self.error_label.setObjectName("errorLabel")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        self.warn_label = QLabel(self)
        self.warn_label.setObjectName("warnLabel")
        self.warn_label.setWordWrap(True)
        self.warn_label.hide()

    def show_error(self, message: str) -> None:
        self.error_label.setText("⚠ " + message)
        self.error_label.show()
        self.ctx.bus.message.emit("Error: " + message[:120])

    def clear_error(self) -> None:
        self.error_label.hide()

    def show_warning(self, message: str) -> None:
        self.warn_label.setText(tr(message))
        self.warn_label.setVisible(bool(message))

    def run(self) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def clear_all(self) -> None:
        pass

    def update_counts(self) -> None:
        pass

    def input_pane(self) -> Optional[TextPane]:
        return None

    def output_pane(self) -> Optional[TextPane]:
        return None

    def emit_counts(self, text: str) -> None:
        self.ctx.bus.counts.emit(len(text.encode("utf-8", "replace")), len(text))


def _conf_color(level: str) -> str:
    p = palette()
    return {"high": p["OK"], "medium": p["WARN"], "low": p["MUTED"], "none": p["ERR"]}.get(level, p["MUTED"])


class CandidateView(QWidget):
    """Ranked candidate table with a detail pane (explanations, text and hex output)."""

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.candidates: list[Candidate] = []
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["#", "Method", "Score", "Confidence", "Printable", "Errors"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in (0, 2, 3, 4, 5):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._show_detail)
        self.detail = FileDropEdit("Select a candidate to see how it was scored.", read_only=True)
        buttons = QHBoxLayout()
        for name, slot, tip in (
            ("Copy output (text)", self._copy_text, "Copy the decoded text of the selected candidate"),
            ("Copy output (hex)", self._copy_hex, "Copy the full output bytes as hexadecimal"),
            ("Send selected to Compare", lambda: self._send(True), "Add the selected candidates to the Compare Results tab"),
            ("Send all to Compare", lambda: self._send(False), "Add every candidate to the Compare Results tab"),
        ):
            b = QPushButton(name)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            buttons.addWidget(b)
        buttons.addStretch(1)
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(self.table)
        split.addWidget(self.detail)
        split.setSizes([220, 260])
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(split, 1)
        layout.addLayout(buttons)

    def set_candidates(self, cands: list[Candidate]) -> None:
        self.candidates = list(cands)
        self.table.setRowCount(len(cands))
        for row, c in enumerate(cands):
            values = [str(row + 1), c.method, f"{c.score:.3f}", c.confidence, f"{c.printable_ratio:.0%}", str(c.decoding_errors)]
            for col, v in enumerate(values):
                item = QTableWidgetItem(v)
                if col == 3:
                    item.setForeground(QColor(_conf_color(c.confidence)))
                self.table.setItem(row, col, item)
        if cands:
            self.table.selectRow(0)
        else:
            self.detail.setPlainText("No candidates.")

    def selected(self) -> list[Candidate]:
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return [self.candidates[r] for r in rows if r < len(self.candidates)]

    def _show_detail(self) -> None:
        sel = self.selected()
        if sel:
            self.detail.setPlainText(sel[0].describe())

    def _copy_text(self) -> None:
        sel = self.selected()
        if sel:
            QApplication.clipboard().setText(sel[0].text if sel[0].text is not None else sel[0].output.hex(" "))
            self.ctx.bus.message.emit("Copied.")

    def _copy_hex(self) -> None:
        sel = self.selected()
        if sel:
            QApplication.clipboard().setText(sel[0].output.hex(" "))
            self.ctx.bus.message.emit("Copied output as hex.")

    def _send(self, selected_only: bool) -> None:
        cands = self.selected() if selected_only else self.candidates
        if cands:
            self.ctx.send_to_compare(cands)
