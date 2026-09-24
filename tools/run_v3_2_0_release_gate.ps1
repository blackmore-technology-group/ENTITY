$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path (Split-Path -Parent $repo) '_venv_entity_v3\Scripts\python.exe'

if (-not (Test-Path $venvPython)) {
    throw "ENTITY v3 environment not found: $venvPython"
}

Push-Location $repo
try {
    & powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'run_v3_regression.ps1')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $venvPython (Join-Path $PSScriptRoot 'verify_v3_global_infrastructure_manifest.py')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $venvPython (Join-Path $PSScriptRoot 'verify_v3_1_0_release_manifest.py')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $venvPython (Join-Path $PSScriptRoot 'verify_v3_2_adoption_release.py')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $venvPython (Join-Path $PSScriptRoot 'verify_v3_2_0_release_manifest.py')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host 'ENTITY v3.2.0 release gate PASS'
    exit 0
} finally {
    Pop-Location
}
