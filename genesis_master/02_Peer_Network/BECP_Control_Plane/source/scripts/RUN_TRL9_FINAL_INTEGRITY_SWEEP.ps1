$ErrorActionPreference = 'Stop'
$Root = '<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\BECP'
$OutDir = Join-Path $Root 'runtime\trl9\BECP_0.2.1_TRL9_20260912'
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
Set-Location $Root

$pytest = (& python -m pytest -q 2>&1 | Out-String)
$pytestExit = $LASTEXITCODE
[IO.File]::WriteAllText((Join-Path $OutDir 'FINAL_REGRESSION_RESULTS.txt'), $pytest + [Environment]::NewLine + 'EXIT=' + $pytestExit, [Text.Encoding]::UTF8)

$compile = (& python -m compileall -q blackmore_ecp api adapters agents scripts 2>&1 | Out-String)
$compileExit = $LASTEXITCODE
[IO.File]::WriteAllText((Join-Path $OutDir 'FINAL_COMPILEALL_RESULTS.txt'), $compile + [Environment]::NewLine + 'EXIT=' + $compileExit, [Text.Encoding]::UTF8)

Write-Output $pytest
Write-Output ('PYTEST_EXIT=' + $pytestExit)
Write-Output ('COMPILE_EXIT=' + $compileExit)
if ($pytestExit -ne 0 -or $compileExit -ne 0) { exit 2 }
