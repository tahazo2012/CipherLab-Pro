"""Hacker theme: green text on black (pure local QSS; no remote fonts, images or stylesheets)."""

MONO_FAMILIES = ["Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Menlo", "monospace"]
UI_FAMILIES = MONO_FAMILIES  # monospace everywhere for the terminal look

BG, PANEL, BORDER = "#000000", "#030a03", "#0c5a1e"
TEXT, MUTED, ACCENT = "#00ff41", "#1fa83c", "#00ff41"
OK, WARN, ERR = "#00ff41", "#e5ff00", "#ff3b3b"
SEL = "#00401a"

DARK_QSS = f"""
QWidget {{ background: {BG}; color: {TEXT}; font-size: 13px; }}
QMainWindow, QDialog {{ background: {BG}; }}
QTabWidget::pane {{ border: 1px solid {BORDER}; top: -1px; }}
QTabBar::tab {{ background: {PANEL}; color: {MUTED}; padding: 8px 14px; border: 1px solid {BORDER};
    border-bottom: none; margin-right: 2px; }}
QTabBar::tab:selected {{ color: {ACCENT}; background: {BG}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover {{ color: {ACCENT}; }}
QPlainTextEdit, QTextEdit, QLineEdit, QTableWidget, QListWidget, QSpinBox, QComboBox {{
    background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; padding: 4px;
    selection-background-color: {ACCENT}; selection-color: #000000; }}
QPlainTextEdit:focus, QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {ACCENT}; }}
QPlainTextEdit[readOnly="true"] {{ background: #010601; }}
QComboBox QAbstractItemView {{ background: {PANEL}; color: {TEXT}; selection-background-color: {ACCENT}; selection-color: #000000; }}
QPushButton {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; padding: 6px 12px; }}
QPushButton:hover {{ border-color: {ACCENT}; background: #041404; }}
QPushButton:pressed {{ background: {SEL}; }}
QPushButton:disabled {{ color: #0f5a22; border-color: #072a10; }}
QPushButton#primary {{ background: {ACCENT}; color: #000000; border: none; font-weight: 700; }}
QPushButton#primary:hover {{ background: #66ff8c; }}
QPushButton#primary:disabled {{ background: #063a14; color: #0f7a2c; }}
QHeaderView::section {{ background: {PANEL}; color: {MUTED}; border: none; border-bottom: 1px solid {BORDER}; padding: 5px; }}
QTableWidget {{ gridline-color: #062a10; alternate-background-color: #020802; }}
QTableWidget::item:selected {{ background: {SEL}; color: {TEXT}; }}
QLabel#errorLabel {{ color: {ERR}; background: #1a0505; border: 1px solid #5a1a1a; padding: 6px; }}
QLabel#warnLabel {{ color: {WARN}; background: #141400; border: 1px solid #5a5a00; padding: 6px; }}
QLabel#muted, QLabel#paneTitle {{ color: {MUTED}; }}
QLabel#paneTitle {{ font-weight: 700; }}
QStatusBar {{ background: {PANEL}; border-top: 1px solid {BORDER}; }}
QStatusBar QLabel {{ background: transparent; }}
QProgressBar {{ border: 1px solid {BORDER}; background: {PANEL}; text-align: center; max-height: 14px; color: {TEXT}; }}
QProgressBar::chunk {{ background: {ACCENT}; }}
QSplitter::handle {{ background: {BORDER}; }}
QMenuBar, QMenu {{ background: {PANEL}; color: {TEXT}; }}
QMenu::item:selected, QMenuBar::item:selected {{ background: {SEL}; }}
QScrollBar:vertical {{ background: {BG}; width: 12px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; min-height: 24px; }}
QScrollBar:horizontal {{ background: {BG}; height: 12px; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; min-width: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border: 1px solid {BORDER}; background: {PANEL}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; }}
QToolTip {{ background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER}; }}
"""
