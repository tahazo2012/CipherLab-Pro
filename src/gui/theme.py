"""Themes (pure local QSS; no remote fonts, images or stylesheets).

Two themes are available and can be switched at run time from Settings:
  * "blue"  - dark blue (default)
  * "green" - green text on black ("hacker" look)
"""
from __future__ import annotations

MONO_FAMILIES = ["Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Menlo", "monospace"]
_BLUE_UI_FAMILIES = ["Segoe UI", "Noto Sans", "DejaVu Sans", "Arial"]

THEMES = ("blue", "green")
THEME_NAMES = {"blue": "Blue (dark)", "green": "Green (hacker)"}

PALETTES: dict[str, dict[str, str]] = {
    "blue": {"BG": "#14171c", "PANEL": "#1b1f26", "BORDER": "#2c323c", "TEXT": "#e6e9ef", "MUTED": "#8b95a5",
             "ACCENT": "#4c9aff", "OK": "#4cd08b", "WARN": "#f0c05a", "ERR": "#ff6b6b"},
    "green": {"BG": "#000000", "PANEL": "#030a03", "BORDER": "#0c5a1e", "TEXT": "#00ff41", "MUTED": "#1fa83c",
              "ACCENT": "#00ff41", "OK": "#00ff41", "WARN": "#e5ff00", "ERR": "#ff3b3b", "SEL": "#00401a"},
}

_current = "blue"


def current() -> str:
    return _current


def set_current(name: str) -> str:
    """Select the active theme (unknown names fall back to blue); returns the name in use."""
    global _current
    _current = name if name in PALETTES else "blue"
    return _current


def palette(name: str | None = None) -> dict[str, str]:
    """Colour table of ``name`` (or of the active theme)."""
    return PALETTES[name or _current]


def ui_families(name: str | None = None) -> list[str]:
    return MONO_FAMILIES if (name or _current) == "green" else _BLUE_UI_FAMILIES


def _qss_blue(p: dict) -> str:
    BG, PANEL, BORDER, TEXT, MUTED, ACCENT, ERR, WARN = (p[k] for k in ("BG", "PANEL", "BORDER", "TEXT", "MUTED", "ACCENT", "ERR", "WARN"))
    return f"""
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


def _qss_green(p: dict) -> str:
    BG, PANEL, BORDER, TEXT, MUTED, ACCENT, ERR, WARN, SEL = (p[k] for k in ("BG", "PANEL", "BORDER", "TEXT", "MUTED", "ACCENT", "ERR", "WARN", "SEL"))
    return f"""
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


def stylesheet(name: str | None = None) -> str:
    """Qt stylesheet for ``name`` (or for the active theme)."""
    name = name or _current
    return _qss_green(PALETTES["green"]) if name == "green" else _qss_blue(PALETTES["blue"])


# Backwards-compatible names (default = blue)
UI_FAMILIES = _BLUE_UI_FAMILIES
DARK_QSS = stylesheet("blue")
