# Build a single-folder Windows app with PyInstaller (run inside the activated venv).
pyinstaller --noconfirm --clean --windowed --name CipherLabPro --exclude-module PySide6.QtNetwork main.py
Write-Host "Output: dist\CipherLabPro\CipherLabPro.exe"
