param(
    [switch]$InstallDependencies,
    [switch]$Full,
    [switch]$RequireRust
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$Python = Get-Command python -ErrorAction Stop
$env:PYTHONPATH = "$Root;$env:PYTHONPATH"
$env:ADAM_FORCE_SPAWN = "1"
$env:ADAM_MP_START_METHOD = "spawn"

$TrustedSigner = "ff864bd4df2cf566a322c6616f72a459df19be051e33e146eb227c604b8d2485"
& $Python.Source .\tools\verify_release_manifest.py --expected-signer-sha256 $TrustedSigner
if ($LASTEXITCODE -ne 0) { throw "ADAM v1 RC2 manifest verification failed" }

if ($InstallDependencies) {
    & $Python.Source -m pip install -c .\PYTHON_DEPENDENCY_LOCK_V1_RC2.txt -e ".[test]"
    if ($LASTEXITCODE -ne 0) { throw "ADAM v1 RC2 dependency installation failed" }
}

& $Python.Source -c "import cryptography, msgpack, numpy, PIL, sympy, pytest"
if ($LASTEXITCODE -ne 0) { throw "Required packages are missing. Rerun with -InstallDependencies." }
if ($Full) {
    & $Python.Source -c "import coverage"
    if ($LASTEXITCODE -ne 0) { throw "The -Full gate requires coverage. Rerun with -InstallDependencies." }
}

& $Python.Source .\run_v1_local_qualification.py
if ($LASTEXITCODE -ne 0) { throw "ADAM v1 RC2 integrated qualification failed" }

& $Python.Source .\tools\run_v1_regression.py
if ($LASTEXITCODE -ne 0) { throw "ADAM v1 RC2 148-test regression failed" }

if ($Full) {
    & $Python.Source -m coverage erase
    & $Python.Source -m coverage run --source=adam_v52,adam_v53,adam_v54,adam_v55,adam_v56,adam_v57,adam_v58,adam_v1 -m pytest -q tests_v1
    if ($LASTEXITCODE -ne 0) { throw "ADAM v1 RC2 focused coverage tests failed" }
    New-Item -ItemType Directory -Force -Path .\artifacts\v1_qualification | Out-Null
    & $Python.Source -m coverage json -o .\artifacts\v1_qualification\ADAM_V1_RC2_COVERAGE.json
    if ($LASTEXITCODE -ne 0) { throw "ADAM v1 RC2 coverage export failed" }
}

if ($RequireRust) {
    & .\RUN_ADAM_V051_FULL_RUST_QUALIFICATION.ps1
    if ($LASTEXITCODE -ne 0) { throw "Strict inherited Rust qualification failed" }
}

& $Python.Source -c "import importlib.metadata as m; import adam_v1; print('ADAM_V1_RC2_IMPORT_PASS version=' + m.version('adam-v1-complete-software-reference'))"
if ($LASTEXITCODE -ne 0) { throw "ADAM v1 RC2 installed-package import failed" }

Write-Host "ADAM_V1_RC2_SOFTWARE_QUALIFICATION_PASS tests=148 gates=12"
if ($RequireRust) { Write-Host "ADAM_V1_RC2_STRICT_RUST_GATE_PASS" }
if ($Full) { Write-Host "ADAM_V1_RC2_FULL_COVERAGE_PASS" }
