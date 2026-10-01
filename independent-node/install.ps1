$ErrorActionPreference = "Stop"
Write-Host "ENTITY Independent Node Program v1"
$py = Get-Command python -ErrorAction Stop
& python --version
if ($LASTEXITCODE -ne 0) { throw "Python is not available." }
& python independent-node/node.py --help | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Independent Node harness self-check failed." }
Write-Host "Harness ready. Initialize with:"
Write-Host "  python independent-node/node.py init"
Write-Host "No service was installed and no network listener was started automatically."
