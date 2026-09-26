param(
    [string]$ZipPath = "",
    [string]$InstallRoot = "",
    [switch]$Full,
    [switch]$RequireRust,
    [switch]$InstallDependencies
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($ZipPath)) {
    $Candidates = @(
        (Join-Path $Here "ADAM_v0_50_1_SOURCE_AUDITED_WINDOWS_PRODUCTION_REFERENCE_FULL_BUILD.zip"),
        (Join-Path $Here "ADAM_v0_50_1_SOURCE_AUDITED_PRODUCTION_REFERENCE_FULL_BUILD.zip")
    )
    $ZipPath = $Candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}
if ([string]::IsNullOrWhiteSpace($ZipPath) -or -not (Test-Path -LiteralPath $ZipPath -PathType Leaf)) {
    throw "ADAM v0.50.1 ZIP was not found. Place this launcher beside either supported ZIP or pass -ZipPath."
}
$ZipPath = (Resolve-Path -LiteralPath $ZipPath).Path
$HashPath = "$ZipPath.sha256"
if (-not (Test-Path -LiteralPath $HashPath -PathType Leaf)) {
    throw "Checksum file missing: $HashPath"
}
$Expected = ((Get-Content -LiteralPath $HashPath -Raw).Trim() -split '\s+')[0].ToLowerInvariant()
$Actual = (Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($Expected -ne $Actual) {
    throw "ZIP SHA-256 mismatch. Expected $Expected, received $Actual"
}
Write-Host "ZIP_SHA256_PASS $Actual" -ForegroundColor Green

$Python = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $Python) { $Python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $Python) { throw "Python 3.11 or later was not found." }
$VersionText = & $Python.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$VersionParts = $VersionText.Trim().Split('.')
if ([int]$VersionParts[0] -lt 3 -or ([int]$VersionParts[0] -eq 3 -and [int]$VersionParts[1] -lt 11)) {
    throw "Python 3.11 or later is required; found $VersionText"
}

if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $InstallRoot = Join-Path $env:LOCALAPPDATA "ADAM\v0.50.1-source-audited"
}
if (Test-Path -LiteralPath $InstallRoot) {
    Remove-Item -LiteralPath $InstallRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $InstallRoot -Force | Out-Null
Expand-Archive -LiteralPath $ZipPath -DestinationPath $InstallRoot -Force
$Qualification = Get-ChildItem -LiteralPath $InstallRoot -Recurse -File -Filter "RUN_ADAM_V0501_SOURCE_AUDITED_QUALIFICATION.ps1" | Select-Object -First 1
if (-not $Qualification) { throw "Qualification entry point was not found after extraction." }
$Root = Split-Path -Parent $Qualification.FullName

if ($InstallDependencies) {
    & $Python.Source -m pip install --disable-pip-version-check $Root
    if ($LASTEXITCODE -ne 0) { throw "Dependency/package installation failed." }
}
else {
    & $Python.Source -c "import cryptography, msgpack, numpy, PIL, sympy, pytest, coverage"
    if ($LASTEXITCODE -ne 0) {
        throw "Required Python packages are missing. Rerun with -InstallDependencies or install the dependencies listed in pyproject.toml."
    }
}

$env:PYTHONPATH = "$Root;$env:PYTHONPATH"
$env:ADAM_FORCE_SPAWN = "1"
if ($Full) { $env:ADAM_REGENERATE_COVERAGE = "1" } else { $env:ADAM_REGENERATE_COVERAGE = "0" }

Push-Location $Root
try {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $Qualification.FullName
    if ($LASTEXITCODE -ne 0) { throw "ADAM v0.50.1 qualification failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
}
Write-Host "ADAM_V0501_WINDOWS_QUALIFICATION_PASS root=$Root" -ForegroundColor Green
