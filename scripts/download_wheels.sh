#!/usr/bin/env sh
# Run ONCE on a computer WITH internet. Copy the whole project (incl. wheelhouse/) to the offline machine.
# -c constraints.txt makes the download use exactly the versions the test suite was run against.
set -e
python3 -m pip download -r requirements-dev.txt -c constraints.txt -d wheelhouse
echo "Wheels saved in ./wheelhouse (download on the same OS / CPU / Python version as the target)."
echo "Runtime only (smaller): python3 -m pip download -r requirements.txt -c constraints.txt -d wheelhouse"
# Downloading FOR another system (for example Windows wheels from a Linux machine):
#   python3 -m pip download --platform win_amd64 --python-version 3.12 --implementation cp --abi cp312 \
#       --only-binary=:all: -r requirements.txt -c constraints.txt -d wheelhouse
