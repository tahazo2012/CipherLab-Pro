# Run ONCE on a computer WITH internet. Copy the whole project (incl. wheelhouse\) to the offline machine.
# -c constraints.txt makes the download use exactly the versions the test suite was run against.
py -3.12 -m pip download -r requirements-dev.txt -c constraints.txt -d wheelhouse
Write-Host "Wheels saved in .\wheelhouse (download on the same OS / CPU / Python version as the target)."
Write-Host "Runtime only (smaller): py -3.12 -m pip download -r requirements.txt -c constraints.txt -d wheelhouse"
