param(
    [string]$VenvPath = ""
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
if (-not $VenvPath) {
    $workspace = Split-Path -Parent $repo
    $VenvPath = Join-Path $workspace "_venv_entity_v3"
}

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    throw "Python is not available on PATH. Install Python 3.10+ or pass through a shell where python is available."
}

if (-not (Test-Path (Join-Path $VenvPath "Scripts\python.exe"))) {
    & $pythonCmd.Source -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) { throw "Failed to create v3 virtual environment." }
}

$venvPython = Join-Path $VenvPath "Scripts\python.exe"
& $venvPython -m pip install --disable-pip-version-check -r (Join-Path $repo "requirements.txt") pytest
if ($LASTEXITCODE -ne 0) { throw "Failed to install ENTITY v3 test dependencies." }
Write-Output $venvPython