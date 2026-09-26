$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$env:PYTHONPATH = "$Root;$env:PYTHONPATH"

& python tools\verify_release_manifest.py
if ($LASTEXITCODE -ne 0) { throw "release manifest verification failed" }

& python tools\audit_source_tree.py
if ($LASTEXITCODE -ne 0) { throw "source audit failed" }
& python run_v50_full_audit.py
if ($LASTEXITCODE -ne 0) { throw "integrated logic audit failed" }

$Manifest = Get-Content tools\regression_manifest.json -Raw | ConvertFrom-Json
$Out = Join-Path $Root "artifacts\v501_source_audit_qualification"
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$Results = Join-Path $Out "regression_file_results.tsv"
Set-Content -Path $Results -Value ""
foreach ($Group in $Manifest.groups) {
  foreach ($File in $Group.files) {
    $Safe = ($File -replace '[\\/]', '_') -replace '\.py$', ''
    $LogRel = "artifacts/v501_source_audit_qualification/$($Group.name)__$Safe.log"
    $Log = Join-Path $Root ($LogRel -replace '/', '\\')
    $Started = Get-Date
    & python tools\isolated_pytest_file.py $File *> $Log
    if ($LASTEXITCODE -ne 0) { Get-Content $Log; throw "pytest failed: $File" }
    $Text = Get-Content $Log -Raw
    $Match = [regex]::Match($Text, 'ADAM_PYTEST_RESULT passed=(\d+)')
    if (-not $Match.Success) { throw "unable to parse passing count: $File" }
    $Elapsed = ((Get-Date) - $Started).TotalSeconds
    Add-Content -Path $Results -Value "$($Group.name)`t$File`t$($Match.Groups[1].Value)`t$Elapsed`t$LogRel"
    Write-Host "[PASS] $($Group.name)/$($File): $($Match.Groups[1].Value) tests"
  }
}
& python -m compileall -q adam_v41 adam_v42 adam_v43 adam_v44 adam_v45 adam_v46 adam_v47 adam_v48 adam_v49 adam_v50
if ($LASTEXITCODE -ne 0) { throw "compileall failed" }
& python tools\summarize_regression.py $Results
if ($LASTEXITCODE -ne 0) { throw "regression summary failed" }
Write-Host "[ADAM v0.50.1] R4 qualification complete: 117 tests, 9 integrated logic gates, mechanical source audit PASS"
