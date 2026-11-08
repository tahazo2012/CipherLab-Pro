"""Main window: tabs, menus, shortcuts and status bar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QLabel, QMainWindow, QMessageBox, QProgressBar, QPushButton, QTabWidget)

from src.gui.about_tab import AboutTab
from src.gui.compare_tab import CompareTab
from src.gui.context import AppContext
from src.gui.decode_tab import DecodeTab
from src.gui.decrypt_tab import DecryptTab
from src.gui.encode_tab import EncodeTab
from src.gui.encrypt_tab import EncryptTab
from src.gui.i18n import retranslate, tr
from src.gui.hex_analyzer_tab import HexAnalyzerTab
from src.gui.history_tab import HistoryTab
from src.gui.settings_dialog import SettingsTab
from src.gui.theme import palette, set_current, stylesheet, ui_families
from src.gui.widgets import BaseTab, CandidateView, TextPane
from src.gui.xor_analyzer_tab import XorAnalyzerTab
from src.gui.xor_decoder_tab import XorDecoderTab
from src.gui.xor_encoder_tab import XorEncoderTab

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
        self.all_tabs = [EncodeTab(ctx), DecodeTab(ctx), EncryptTab(ctx), DecryptTab(ctx),
                         XorEncoderTab(ctx), XorDecoderTab(ctx), HexAnalyzerTab(ctx), XorAnalyzerTab(ctx),
                         self.compare_tab, self.history_tab, AboutTab(ctx), SettingsTab(ctx)]
        for tab in self.all_tabs:
            self.tabs.addTab(tab, tab.title)
        self.setCentralWidget(self.tabs)
        ctx.send_to_compare = self._send_to_compare
        self._build_status_bar()
        self._build_menus()
        self.tabs.currentChanged.connect(self._tab_changed)
        ctx.set_theme = self.apply_theme
        self.apply_theme(ctx.settings.theme)
        ctx.set_language = self.apply_language
        if ctx.settings.language != "en":
            self.apply_language(ctx.settings.language)

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
        self.offline_label = offline
        offline.setStyleSheet(f"color: {palette()['OK']};")
        for w in (self.counts_label, self.progress, self.cancel_btn, offline):
            bar.addPermanentWidget(w)
        bar.showMessage("Ready. All processing happens locally on this computer.")
        bus = self.ctx.bus
        bus.message.connect(lambda m: bar.showMessage(m, 10000))
        bus.counts.connect(lambda b, c: self.counts_label.setText(
            tr("Input: {c} chars · {b} bytes").format(c=f"{c:,}", b=f"{b:,}")))
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

    def apply_theme(self, name: str) -> None:
        """Switch between the blue and green themes immediately."""
        name = set_current(name)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(stylesheet(name))
            font = QFont()
            font.setFamilies(ui_families(name))
            font.setPointSize(10)
            app.setFont(font)
        self.offline_label.setStyleSheet(f"color: {palette()['OK']};")
        for tab in self.all_tabs:
            if hasattr(tab, "apply_theme"):
                tab.apply_theme()
        for view in self.findChildren(CandidateView):
            view.set_candidates(view.candidates)  # re-colour the confidence column

    def apply_language(self, lang: str) -> None:
        """Switch the UI language (fa/ar switch to right-to-left layout)."""
        retranslate(self, lang)
        for pane in self.findChildren(TextPane):
            if pane.count_label.text():
                pane._update_count()
        for tab in self.all_tabs:
            if isinstance(tab, BaseTab):
                tab.error_label.hide()
                tab.show_warning("")
                if hasattr(tab, "_algo_changed"):
                    tab._algo_changed()
                if hasattr(tab, "refresh_language"):
                    tab.refresh_language()
        self.counts_label.setText(tr("Input: {c} chars · {b} bytes").format(c="0", b="0"))
        self._tab_changed(0)
        self.statusBar().showMessage(tr("Ready. All processing happens locally on this computer."))

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
        for i in range(len(self.all_tabs)):
            QShortcut(QKeySequence(self._tab_shortcut(i)), self, activated=lambda i=i: self.tabs.setCurrentIndex(i))
        help_menu = self.menuBar().addMenu("&Help")
        about = QAction("&About / offline guarantee", self)
        about.triggered.connect(self._about)
        help_menu.addAction(about)

    @staticmethod
    def _tab_shortcut(index: int) -> str:
        """Ctrl+1..9 = tabs 1-9, Ctrl+0 = tab 10, Ctrl+Shift+1.. = tabs 11 and up."""
        return f"Ctrl+{(index + 1) % 10}" if index < 10 else f"Ctrl+Shift+{index - 9}"

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
        shortcut = self._tab_shortcut(self.all_tabs.index(self.compare_tab))
        self.ctx.bus.message.emit(f"{len(cands)} candidate(s) sent to Compare Results ({shortcut}).")

    def _about(self) -> None:
        QMessageBox.information(self, "About CipherLab Pro",
                                "CipherLab Pro: local encoding, cryptography and analysis experiments.\n\n"
                                "• No network connections, telemetry, update checks or accounts.\n"
                                "• No AI or cloud services: analysis uses deterministic local algorithms.\n"
                                "• Passwords and keys are never saved to history, settings or logs.\n\n"
                                "Shortcuts: Ctrl+Enter run · Ctrl+L clear · Ctrl+O import · Ctrl+S export · Ctrl+1…9, Ctrl+0, Ctrl+Shift+1/2 switch tabs.")
