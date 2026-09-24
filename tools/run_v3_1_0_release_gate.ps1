$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Push-Location $repo
try {
    & powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'run_v3_regression.ps1')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & (Join-Path (Split-Path -Parent $repo) '_venv_entity_v3\Scripts\python.exe') (Join-Path $PSScriptRoot 'verify_v3_global_infrastructure_manifest.py')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & (Join-Path (Split-Path -Parent $repo) '_venv_entity_v3\Scripts\python.exe') (Join-Path $PSScriptRoot 'verify_v3_1_0_release_manifest.py')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host 'ENTITY v3.1.0 release gate PASS'
    exit 0
} finally {
    Pop-Location
}
