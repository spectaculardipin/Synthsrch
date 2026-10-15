# Synthsrch Windows installer.
# Run this from the repo root (the folder containing pyproject.toml):
#   cd Synthsrch
#   .\install.ps1
$ErrorActionPreference = "Stop"

# 1. Python 3.11+ via the py launcher is required.
try { $pyVersion = py --version 2>&1 } catch {
  Write-Host "ERROR: 'py' launcher not found. Install Python 3.11+ from https://www.python.org/downloads/ (tick 'Add python.exe to PATH' / install the py launcher), then retry." -ForegroundColor Red
  exit 1
}
Write-Host "Found $pyVersion"
py -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)'
if ($LASTEXITCODE -ne 0) {
  Write-Host "ERROR: Python 3.11+ is required. Install 3.11+ and retry." -ForegroundColor Red
  exit 1
}

# 2. Must run from the repo root: the trailing dot in pip install means this folder.
if (-not (Test-Path '.\pyproject.toml')) {
  Write-Host 'ERROR: pyproject.toml not found here. Did you forget cd Synthsrch first?' -ForegroundColor Red
  Write-Host 'Fix: git clone https://github.com/spectaculardipin/Synthsrch.git'
  Write-Host 'Then: cd Synthsrch'
  Write-Host 'Then: .\install.ps1'
  exit 1
}

Write-Host 'Upgrading pip ...'
py -m pip install --upgrade pip

Write-Host 'Installing Synthsrch (the trailing dot means install the package in this folder) ...'
py -m pip install .

# 3. Entry-point scripts (synthsrch, crawl4ai-setup) land in Python Scripts dir,
# which is often missing from PATH on fresh Windows installs. Fix that here.
$scriptsDir = (py -c 'import sysconfig; print(sysconfig.get_path("scripts"))').Trim()
Write-Host "Scripts dir: $scriptsDir"
$sessionHasIt = ($env:Path -split ';') -contains $scriptsDir
if (-not $sessionHasIt) { $env:Path += ";$scriptsDir" }
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ((($userPath -split ';') -notcontains $scriptsDir)) {
  [Environment]::SetEnvironmentVariable('Path', "$userPath;$scriptsDir", 'User')
  Write-Host 'Added Scripts dir to your user PATH (new terminals will pick it up).'
}

# 4. Browser engine for JS-page fallback (~300MB, one time). Optional:
# plain pages extract via trafilatura without it, so never fail the install here.
Write-Host 'Installing browser engine for JS-page extraction (crawl4ai fallback, ~300MB) ...'
try {
  crawl4ai-setup
} catch {
  Write-Host 'WARNING: crawl4ai-setup did not run. Plain pages still work; JS-only pages will report EXTRACT_FAILED.' -ForegroundColor Yellow
  Write-Host 'Retry in a NEW terminal with: crawl4ai-setup'
  Write-Host 'If that is still not recognized, run: py -m pip install --force-reinstall crawl4ai'
}

# 5. Verify the install works even without PATH (py -m bypasses the exe lookup).
Write-Host 'Verifying install ...'
py -m synthsrch doctor

Write-Host ''
if (Get-Command synthsrch -ErrorAction SilentlyContinue) {
  Write-Host 'OK. Run: synthsrch  (opens http://127.0.0.1:8765)'
} else {
  Write-Host 'Installed, but this terminal cannot see the synthsrch command yet.' -ForegroundColor Yellow
  Write-Host 'Open a NEW terminal, then run: synthsrch'
  Write-Host 'Or in any terminal run the fallback: py -m synthsrch'
}
Write-Host 'Doctor: synthsrch doctor  (or: py -m synthsrch doctor)'
