#!/usr/bin/env sh
# Installs from ./wheelhouse only; --no-index forbids pip from contacting any package server.
# For runtime only, use requirements.txt instead of requirements-dev.txt.
set -e
python3 -m venv .venv
. .venv/bin/activate
pip install --no-index --find-links wheelhouse -r requirements-dev.txt -c constraints.txt
pip check
echo "Installed offline. Run: python main.py"
