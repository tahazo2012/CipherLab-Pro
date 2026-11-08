#!/usr/bin/env sh
# Linux build (same PyInstaller options as Windows).
pyinstaller --noconfirm --clean --windowed --name CipherLabPro --exclude-module PySide6.QtNetwork main.py
echo "Output: dist/CipherLabPro/CipherLabPro"
