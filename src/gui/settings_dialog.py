"""Settings (shown as a tab): all values are stored locally in the app data folder."""
from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QSpinBox, QVBoxLayout)

from src.core.encodings import TEXT_CHARSETS
from src.core.settings import get_data_dir
from src.gui.i18n import LANGS
from src.gui.theme import THEME_NAMES
from src.gui.widgets import BaseTab
from src.models.crypto_envelope import MAX_ITERATIONS, MIN_ITERATIONS


class SettingsTab(BaseTab):
    title = "Settings"

    def __init__(self, ctx):
        super().__init__(ctx)
        s = ctx.settings
        self.lang = QComboBox()
        for code, name in LANGS.items():
            self.lang.addItem(name, code)
        self.theme = QComboBox()
        for code, label in THEME_NAMES.items():
            self.theme.addItem(label, code)
        self.history = QCheckBox("Record local history")
        self.previews = QCheckBox("Store short input/output previews in history (never for encrypt/decrypt/HMAC)")
        self.max_hist = QSpinBox()
        self.max_hist.setRange(10, 100_000)
        self.max_file = QSpinBox()
        self.max_file.setRange(1, 100)
        self.max_file.setSuffix(" MB")
        self.iterations = QSpinBox()
        self.iterations.setRange(MIN_ITERATIONS, MAX_ITERATIONS)
        self.iterations.setSingleStep(50_000)
        self.clear_pw = QCheckBox("Clear password field after each Encrypt/Decrypt run")
        self.charset = QComboBox()
        self.charset.addItems(list(TEXT_CHARSETS))
        self.persian = QCheckBox("Enable Persian text scoring in analyzers")
        self.table_path = QLineEdit()
        self.table_path.setPlaceholderText("Optional JSON file {\"ا\": 13.0, ...} to override the built-in Persian table")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        save = QPushButton("Save settings")
        save.setObjectName("primary")
        save.clicked.connect(self.save)
        self._load(s)
        self.lang.currentIndexChanged.connect(self._language_changed)
        self.theme.currentIndexChanged.connect(self._theme_changed)
        form = QFormLayout()
        form.addRow("Language:", self.lang)
        form.addRow("Theme:", self.theme)
        form.addRow(self.history)
        form.addRow(self.previews)
        form.addRow("Maximum history records:", self.max_hist)
        form.addRow("Maximum import file size:", self.max_file)
        form.addRow("PBKDF2 iterations (new encryptions):", self.iterations)
        form.addRow(self.clear_pw)
        form.addRow("Default text encoding:", self.charset)
        form.addRow(self.persian)
        trow = QHBoxLayout()
        trow.addWidget(self.table_path, 1)
        trow.addWidget(browse)
        form.addRow("Persian frequency table:", trow)
        info = QLabel(
            f"<b>Data folder:</b> {get_data_dir()}<br>Contains <code>settings.json</code>, <code>history.db</code> and "
            "<code>cipherlab.log</code>. Nothing else is written; passwords and keys are never stored.<br><br>"
            "<b>Offline:</b> CipherLab Pro has no telemetry, no update check, no cloud sync and makes no network "
            "connections. Python-level socket access is blocked at start-up as a safeguard.")
        info.setWordWrap(True)
        info.setObjectName("muted")
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(save)
        layout.addWidget(self.error_label)
        layout.addWidget(info)
        layout.addStretch(1)

    def _language_changed(self) -> None:
        code = self.lang.currentData()
        self.ctx.settings.language = code
        try:
            self.ctx.settings.save()
        except OSError:
            pass
        self.ctx.set_language(code)

    def _theme_changed(self) -> None:
        code = self.theme.currentData()
        self.ctx.settings.theme = code
        try:
            self.ctx.settings.save()
        except OSError:
            pass
        self.ctx.set_theme(code)

    def _load(self, s) -> None:
        self.lang.setCurrentIndex(max(0, self.lang.findData(s.language)))
        self.theme.setCurrentIndex(max(0, self.theme.findData(s.theme)))
        self.history.setChecked(s.history_enabled)
        self.previews.setChecked(s.history_store_previews)
        self.max_hist.setValue(s.max_history_records)
        self.max_file.setValue(s.max_file_mb)
        self.iterations.setValue(s.pbkdf2_iterations)
        self.clear_pw.setChecked(s.clear_password_after_use)
        self.charset.setCurrentText(s.default_charset)
        self.persian.setChecked(s.persian_scoring)
        self.table_path.setText(s.persian_table_path)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Persian frequency table", "", "JSON (*.json)")
        if path:
            self.table_path.setText(path)

    def save(self) -> None:
        self.clear_error()
        s = self.ctx.settings
        s.history_enabled, s.history_store_previews = self.history.isChecked(), self.previews.isChecked()
        s.max_history_records, s.max_file_mb = self.max_hist.value(), self.max_file.value()
        s.pbkdf2_iterations, s.clear_password_after_use = self.iterations.value(), self.clear_pw.isChecked()
        s.default_charset, s.persian_scoring = self.charset.currentText(), self.persian.isChecked()
        s.persian_table_path = self.table_path.text().strip()
        if s.persian_table_path and s.persian_table() is None:
            self.show_error("The Persian frequency table could not be read; the built-in table will be used.")
        try:
            s.save()
        except OSError as exc:
            self.show_error(f"Could not save settings: {exc}")
            return
        self.ctx.apply_settings()
        self.ctx.bus.message.emit("Settings saved.")
