"""Dark theme (pure local QSS; no remote fonts, images or stylesheets)."""

MONO_FAMILIES = ["Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Menlo", "monospace"]
UI_FAMILIES = ["Segoe UI", "Noto Sans", "DejaVu Sans", "Arial"]

BG, PANEL, BORDER = "#14171c", "#1b1f26", "#2c323c"
TEXT, MUTED, ACCENT = "#e6e9ef", "#8b95a5", "#4c9aff"
OK, WARN, ERR = "#4cd08b", "#f0c05a", "#ff6b6b"

DARK_QSS = f"""
QWidget {{ background: {BG}; color: {TEXT}; font-size: 13px; }}
QMainWindow, QDialog {{ background: {BG}; }}
QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 6px; top: -1px; }}
QTabBar::tab {{ background: {PANEL}; color: {MUTED}; padding: 8px 14px; border: 1px solid {BORDER};
    border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; }}
QTabBar::tab:selected {{ color: {TEXT}; background: {BG}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover {{ color: {TEXT}; }}
QPlainTextEdit, QTextEdit, QLineEdit, QTableWidget, QListWidget, QSpinBox, QComboBox {{
    background: {PANEL}; border: 1px solid {BORDER}; border-radius: 5px; padding: 4px;
    selection-background-color: {ACCENT}; selection-color: #0b0d10; }}
QPlainTextEdit:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {ACCENT}; }}
QPlainTextEdit[readOnly="true"] {{ background: #181c22; }}
QComboBox QAbstractItemView {{ background: {PANEL}; selection-background-color: {ACCENT}; selection-color: #0b0d10; }}
QPushButton {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 5px; padding: 6px 12px; }}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:pressed {{ background: #232932; }}
QPushButton:disabled {{ color: #566070; }}
QPushButton#primary {{ background: {ACCENT}; color: #0b0d10; border: none; font-weight: 600; }}
QPushButton#primary:hover {{ background: #6cb0ff; }}
QPushButton#primary:disabled {{ background: #2d4766; color: #7d8ea5; }}
QHeaderView::section {{ background: {PANEL}; color: {MUTED}; border: none; border-bottom: 1px solid {BORDER}; padding: 5px; }}
QTableWidget {{ gridline-color: {BORDER}; alternate-background-color: #171b21; }}
QTableWidget::item:selected {{ background: #25456e; color: {TEXT}; }}
QLabel#errorLabel {{ color: {ERR}; background: #2a1a1d; border: 1px solid #5a2a30; border-radius: 5px; padding: 6px; }}
QLabel#warnLabel {{ color: {WARN}; background: #2a2518; border: 1px solid #5a4d22; border-radius: 5px; padding: 6px; }}
QLabel#muted, QLabel#paneTitle {{ color: {MUTED}; }}
QLabel#paneTitle {{ font-weight: 600; }}
QStatusBar {{ background: {PANEL}; border-top: 1px solid {BORDER}; }}
QStatusBar QLabel {{ background: transparent; }}
QProgressBar {{ border: 1px solid {BORDER}; border-radius: 4px; background: {PANEL}; text-align: center; max-height: 14px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}
QSplitter::handle {{ background: {BORDER}; }}
QMenuBar, QMenu {{ background: {PANEL}; }}
QMenu::item:selected, QMenuBar::item:selected {{ background: #25456e; }}
QScrollBar:vertical {{ background: {BG}; width: 12px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 24px; }}
QScrollBar:horizontal {{ background: {BG}; height: 12px; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; border-radius: 5px; min-width: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {BORDER}; border-radius: 3px; background: {PANEL}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; }}
QToolTip {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; }}
"""
