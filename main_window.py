"""Main window: tabs, menus, shortcuts and status bar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (QLabel, QMainWindow, QMessageBox, QProgressBar, QPushButton, QTabWidget)

from src.gui.about_tab import AboutTab
from src.gui.compare_tab import CompareTab
from src.gui.context import AppContext
from src.gui.decode_tab import DecodeTab
from src.gui.decrypt_tab import DecryptTab
from src.gui.encode_tab import EncodeTab
from src.gui.encrypt_tab import EncryptTab
from src.gui.hex_analyzer_tab import HexAnalyzerTab
from src.gui.history_tab import HistoryTab
from src.gui.settings_dialog import SettingsTab
from src.gui.xor_analyzer_tab import XorAnalyzerTab

APP_NAME = "CipherLab Pro"


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(f"{APP_NAME} — offline")
        self.resize(1200, 780)
        self.tabs = QTabWidget()
        self.compare_tab = CompareTab(ctx)
        self.history_tab = HistoryTab(ctx)
        self.all_tabs = [EncodeTab(ctx), DecodeTab(ctx), EncryptTab(ctx), DecryptTab(ctx), HexAnalyzerTab(ctx),
                         XorAnalyzerTab(ctx), self.compare_tab, self.history_tab, AboutTab(ctx), SettingsTab(ctx)]
        for tab in self.all_tabs:
            self.tabs.addTab(tab, tab.title)
        self.setCentralWidget(self.tabs)
        ctx.send_to_compare = self._send_to_compare
        self._build_status_bar()
        self._build_menus()
        self.tabs.currentChanged.connect(self._tab_changed)

    # -- status bar
    def _build_status_bar(self) -> None:
        bar = self.statusBar()
        self.counts_label = QLabel("Input: 0 chars · 0 bytes")
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(170)
        self.progress.hide()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.hide()
        self.cancel_btn.clicked.connect(self.ctx.runner.cancel_all)
        offline = QLabel("● OFFLINE · no network access")
        offline.setStyleSheet("color: #00ff41;")
        for w in (self.counts_label, self.progress, self.cancel_btn, offline):
            bar.addPermanentWidget(w)
        bar.showMessage("Ready. All processing happens locally on this computer.")
        bus = self.ctx.bus
        bus.message.connect(lambda m: bar.showMessage(m, 10000))
        bus.counts.connect(lambda b, c: self.counts_label.setText(f"Input: {c:,} chars · {b:,} bytes"))
        bus.progress.connect(self._on_progress)

    def _on_progress(self, percent: int, message: str) -> None:
        if percent == -2:
            self.progress.hide()
            self.cancel_btn.hide()
            return
        self.progress.show()
        self.cancel_btn.show()
        if percent < 0:
            self.progress.setRange(0, 0)
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(percent)
        if message:
            self.statusBar().showMessage(message, 3000)

    # -- menus / shortcuts
    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        for text, key, slot in (("&Import into input…", "Ctrl+O", self._import), ("&Export output…", "Ctrl+S", self._export),
                                ("&Quit", "Ctrl+Q", self.close)):
            act = QAction(text, self)
            act.setShortcut(QKeySequence(key))
            act.triggered.connect(slot)
            file_menu.addAction(act)
        edit_menu = self.menuBar().addMenu("&Edit")
        for text, key, slot in (("&Run current tab", "Ctrl+Return", self._run), ("&Clear current tab", "Ctrl+L", self._clear)):
            act = QAction(text, self)
            act.setShortcut(QKeySequence(key))
            act.triggered.connect(slot)
            edit_menu.addAction(act)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self._run)
        for i in range(min(10, len(self.all_tabs))):
            QShortcut(QKeySequence(f"Ctrl+{(i + 1) % 10}"), self, activated=lambda i=i: self.tabs.setCurrentIndex(i))
        help_menu = self.menuBar().addMenu("&Help")
        about = QAction("&About / offline guarantee", self)
        about.triggered.connect(self._about)
        help_menu.addAction(about)

    def _current(self):
        return self.tabs.currentWidget()

    def _run(self) -> None:
        tab = self._current()
        if hasattr(tab, "run") and not isinstance(tab, (CompareTab, HistoryTab, SettingsTab)):
            tab.run()

    def _clear(self) -> None:
        self._current().clear_all()

    def _import(self) -> None:
        pane = self._current().input_pane()
        if pane:
            pane.import_dialog()

    def _export(self) -> None:
        tab = self._current()
        pane = tab.output_pane() or tab.input_pane()
        if pane:
            pane.export_dialog()

    def _tab_changed(self, _index: int) -> None:
        tab = self._current()
        tab.update_counts()
        if tab is self.history_tab:
            self.history_tab.refresh()

    def _send_to_compare(self, cands) -> None:
        self.compare_tab.add_candidates(cands)
        self.ctx.bus.message.emit(f"{len(cands)} candidate(s) sent to Compare Results (Ctrl+7).")

    def _about(self) -> None:
        QMessageBox.information(self, "About CipherLab Pro",
                                "CipherLab Pro: local encoding, cryptography and analysis experiments.\n\n"
                                "• No network connections, telemetry, update checks or accounts.\n"
                                "• No AI or cloud services: analysis uses deterministic local algorithms.\n"
                                "• Passwords and keys are never saved to history, settings or logs.\n\n"
                                "Shortcuts: Ctrl+Enter run · Ctrl+L clear · Ctrl+O import · Ctrl+S export · Ctrl+1…9 switch tabs.")
