# Synthsrch zero-to-running installer for Windows 10/11.
# Needs nothing but PowerShell. Paste this one-liner into PowerShell:
#   powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/spectaculardipin/Synthsrch/main/bootstrap.ps1 | iex"
# It installs Python 3.12 (via winget) if missing, fetches the code,
# installs the package, fixes PATH, then verifies. Steps mirror install.ps1
# (kept inline so PATH fixes apply to your current terminal session).
$ErrorActionPreference = 'Stop'
$Repo = 'https://github.com/spectaculardipin/Synthsrch.git'
$Zip = 'https://codeload.github.com/spectaculardipin/Synthsrch/zip/refs/heads/main'

function Find-Py {
  foreach ($c in @('py', 'python')) {
    try { & $c --version 2>$null | Out-Null; if ($LASTEXITCODE -eq 0) { return $c } } catch {}
  }
  return $null
}

function Test-PyOk($Py) {
  if (-not $Py) { return $false }
  & $Py -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)'
  return ($LASTEXITCODE -eq 0)
}

function Sync-SessionPath {
  $m = [Environment]::GetEnvironmentVariable('Path', 'Machine')
  $u = [Environment]::GetEnvironmentVariable('Path', 'User')
  $env:Path = "$m;$u"
}

# 1. Python 3.11+ (install it if missing).
$Py = Find-Py
if (-not (Test-PyOk $Py)) {
  Write-Host 'Python 3.11+ not found. Installing Python 3.12 via winget ...'
  try { winget --version | Out-Null; if ($LASTEXITCODE -ne 0) { throw 'no winget' } } catch {
    Write-Host 'ERROR: No Python and no winget on this machine.' -ForegroundColor Red
    Write-Host 'Install Python 3.11+ from https://www.python.org/downloads/ (tick Add python.exe to PATH),'
    Write-Host 'then re-run the one-liner.'
    exit 1
  }
  winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
  if ($LASTEXITCODE -ne 0) {
    Write-Host 'ERROR: winget Python install failed. Install from https://www.python.org/downloads/ and re-run.' -ForegroundColor Red
    exit 1
  }
  Sync-SessionPath
  $Py = Find-Py
  if (-not (Test-PyOk $Py)) {
    Write-Host 'Python installed but not visible yet. Open a NEW terminal and re-run the one-liner.' -ForegroundColor Yellow
    exit 1
  }
}
Write-Host "Using $Py ($( & $Py --version ))"
& $Py -m pip install --upgrade pip

# 2. Code (reuse current folder when already inside the checkout).
if (-not (Test-Path '.\pyproject.toml')) {
  if (Test-Path '.\Synthsrch\pyproject.toml') {
    Set-Location '.\Synthsrch'
  } else {
    Write-Host 'Fetching Synthsrch code ...'
    $haveGit = $false
    try { git --version 2>$null | Out-Null; if ($LASTEXITCODE -eq 0) { $haveGit = $true } } catch {}
    if ($haveGit) {
      git clone $Repo Synthsrch
      Set-Location '.\Synthsrch'
    } else {
      $tmp = Join-Path $env:TEMP 'synthsrch-dl'
      if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
      New-Item -ItemType Directory $tmp | Out-Null
      $zipFile = Join-Path $tmp 'repo.zip'
      Invoke-WebRequest $Zip -OutFile $zipFile
      Expand-Archive $zipFile $tmp
      $inner = Join-Path $tmp 'Synthsrch-main'
      if (Test-Path '.\Synthsrch') { Remove-Item '.\Synthsrch' -Recurse -Force }
      Move-Item $inner '.\Synthsrch'
      Remove-Item $tmp -Recurse -Force
      Set-Location '.\Synthsrch'
    }
  }
}
Write-Host "Repo ready in $(Get-Location)"

# 3. Package (the trailing dot means: the package in this folder).
& $Py -m pip install .
if ($LASTEXITCODE -ne 0) {
  Write-Host 'ERROR: pip install failed (see red text above). Fix that error, then re-run.' -ForegroundColor Red
  exit 1
}

# 4. PATH (entry-point exes live in the Scripts dir, often missing on fresh Windows).
$scriptsDir = (& $Py -c "import sysconfig; print(sysconfig.get_path('scripts'))").Trim()
Write-Host "Scripts dir: $scriptsDir"
if ((($env:Path -split ';') -notcontains $scriptsDir)) { $env:Path += ";$scriptsDir" }
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ((($userPath -split ';') -notcontains $scriptsDir)) {
  [Environment]::SetEnvironmentVariable('Path', "$userPath;$scriptsDir", 'User')
  Write-Host 'Added Scripts dir to your user PATH (new terminals pick it up automatically).'
}

# 5. Browser engine for JS-page fallback (~300MB, one time). Optional.
Write-Host 'Installing browser engine for JS-page extraction (crawl4ai fallback, ~300MB) ...'
try {
  crawl4ai-setup
} catch {
  Write-Host 'WARNING: crawl4ai-setup did not run. Plain pages still work; JS-only pages report EXTRACT_FAILED.' -ForegroundColor Yellow
  Write-Host 'Retry in a NEW terminal with: crawl4ai-setup'
}

# 6. Verify (py -m bypasses PATH, so this proves the install even if exes are shy).
Write-Host 'Verifying install ...'
& $Py -m synthsrch doctor

Write-Host ''
if (Get-Command synthsrch -ErrorAction SilentlyContinue) {
  Write-Host 'Done. Launch with: synthsrch  (opens http://127.0.0.1:8765)'
} else {
  Write-Host 'Installed. This terminal cannot see the synthsrch command yet, so either:' -ForegroundColor Yellow
  Write-Host '  - open a NEW terminal and run: synthsrch'
  Write-Host '  - or stay here and run the fallback: py -m synthsrch'
}
Write-Host 'Next: add your search key + NIM key in Settings (chat needs the NIM key).'
