$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$python = 'E:\ENTITY_ACTIVE\_venv_entity_v3\Scripts\python.exe'
if (-not (Test-Path $python)) { throw "ENTITY v3 Python environment missing: $python" }
Push-Location $repo
try {
    & $python -m unittest discover -s tests -p 'test_*.py' -q
    if ($LASTEXITCODE -ne 0) { throw 'v3.0.1 regression failed' }
    & $python tools\verify_v3_0_1_qualification.py
    if ($LASTEXITCODE -ne 0) { throw 'v3.0.1 qualification evidence failed' }
    & $python tools\verify_v3_0_1_release_manifest.py
    if ($LASTEXITCODE -ne 0) { throw 'v3.0.1 release manifest failed' }
    Write-Host 'ENTITY v3.0.1 RELEASE GATE: PASS'
}
finally { Pop-Location }
