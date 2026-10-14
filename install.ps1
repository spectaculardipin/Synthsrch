# Synthsrch Windows installer.
$ErrorActionPreference = "Stop"
Write-Host "Installing Synthsrch ..."
py -m pip install .
Write-Host "Installing browser engine for JS-page extraction (crawl4ai fallback, ~300MB) ..."
crawl4ai-setup
Write-Host "OK. Run: synthsrch  (opens http://127.0.0.1:8765)"
Write-Host "Doctor: synthsrch doctor"
