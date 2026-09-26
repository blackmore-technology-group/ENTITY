$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYTHONPATH = $PSScriptRoot
python .\RUN_ADAM_V051_SOURCE_QUALIFICATION.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
