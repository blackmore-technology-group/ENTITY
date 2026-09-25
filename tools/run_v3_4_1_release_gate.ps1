$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$py = Join-Path (Split-Path -Parent $repo) '_venv_entity_v3\Scripts\python.exe'
$git='E:\ENTITY_ACTIVE\TOOLS\PortableGit\cmd\git.exe'
if (-not (Test-Path $py)) { throw "ENTITY v3 environment not found: $py" }
Push-Location $repo
try {
  & $git -C $repo diff --check; if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
  & powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'run_v3_regression.ps1'); if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
  $baseTag=(& $git -C $repo rev-list -n 1 v3.4.0).Trim(); if($baseTag -ne '2db5bff64507b8d67642122a5ff2fc73dfef9152'){throw 'v3.4.0 tag moved'};
  $currentBlob=(& $git -C $repo hash-object 'ENTITY_V3_4_0_RELEASE_MANIFEST.json').Trim(); $tagBlob=(& $git -C $repo rev-parse 'v3.4.0:ENTITY_V3_4_0_RELEASE_MANIFEST.json').Trim(); if($currentBlob -ne $tagBlob){throw 'v3.4.0 release manifest differs from immutable tag'}
  & $py (Join-Path $PSScriptRoot 'build_v3_4_cleanroom_kit.py'); if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
  & $py (Join-Path $PSScriptRoot 'verify_v3_4_global_passport_release.py'); if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
  & $py (Join-Path $PSScriptRoot 'verify_v3_4_implementation_packages.py'); if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
  & $py (Join-Path $PSScriptRoot 'build_v3_4_1_qualification.py'); if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
  & $py (Join-Path $PSScriptRoot 'build_v3_4_1_release.py'); if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
  & $py (Join-Path $PSScriptRoot 'verify_v3_4_1_release_manifest.py'); if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
  Write-Host 'ENTITY v3.4.1 release gate PASS'; exit 0
} finally { Pop-Location }