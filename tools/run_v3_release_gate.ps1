param(
    [string]$VenvPath = ""
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
if (-not $VenvPath) {
    $workspace = Split-Path -Parent $repo
    $VenvPath = Join-Path $workspace "_venv_entity_v3"
}
$python = Join-Path $VenvPath "Scripts\python.exe"

& (Join-Path $PSScriptRoot "run_v3_regression.ps1") -VenvPath $VenvPath
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Push-Location $repo
try {
    & $python tools\qualify_v3_release.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python tools\verify_v3_development_manifest.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python tools\verify_v3_release_manifest.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    exit 0
} finally {
    Pop-Location
}