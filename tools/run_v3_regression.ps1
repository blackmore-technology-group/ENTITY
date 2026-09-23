param(
    [string]$VenvPath = ""
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
if (-not $VenvPath) {
    $workspace = Split-Path -Parent $repo
    $VenvPath = Join-Path $workspace "_venv_entity_v3"
}
$venvPython = Join-Path $VenvPath "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    $venvPython = & (Join-Path $PSScriptRoot "bootstrap_v3_env.ps1") -VenvPath $VenvPath | Select-Object -Last 1
}

& $venvPython -c "import cryptography, fastapi, uvicorn, jsonschema"
if ($LASTEXITCODE -ne 0) {
    $venvPython = & (Join-Path $PSScriptRoot "bootstrap_v3_env.ps1") -VenvPath $VenvPath | Select-Object -Last 1
}

Push-Location $repo
try {
    & $venvPython -m compileall -q src sdk protocol tests tools
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $venvPython -m unittest discover -s tests -p 'test_*.py' -v
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
