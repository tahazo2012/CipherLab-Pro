# Installs from .\wheelhouse only; --no-index forbids pip from contacting any package server.
# For runtime only, use requirements.txt instead of requirements-dev.txt.
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-index --find-links wheelhouse -r requirements-dev.txt -c constraints.txt
.\.venv\Scripts\python.exe -m pip check
Write-Host "Installed offline. Run: .\.venv\Scripts\python.exe main.py"
