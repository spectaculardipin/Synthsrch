# Synthsrch Windows installer — adds pipx/pip install + first run hint.
$ErrorActionPreference = "Stop"
Write-Host "Installing Synthsrch (pip install -e .) ..."
py -m pip install -e .
Write-Host "OK. Run: synthsrch  (opens http://127.0.0.1:8765)"
Write-Host "Doctor: synthsrch doctor"
