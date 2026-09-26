$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$env:PYTHONPATH = "$Root;$env:PYTHONPATH"
$Out = Join-Path $Root "artifacts\v50_full_audit"
New-Item -ItemType Directory -Path $Out -Force | Out-Null

function Run-TestGroup {
    param([string]$Name, [string[]]$Paths)
    Write-Host "[ADAM v0.50] Running $Name"
    $Log = Join-Path $Out "$Name.log"
    & python -m pytest -q @Paths --disable-warnings 2>&1 | Tee-Object -FilePath $Log
    if ($LASTEXITCODE -ne 0) { throw "Test group $Name failed" }
}

Run-TestGroup "v040_v041" @(
    "tests/test_v40_compat.py",
    "tests/test_v41_universe.py",
    "tests/test_v41_adversarial.py"
)
Run-TestGroup "v042_core" @(
    "tests/test_v42_distributed.py",
    "tests/test_v42_perception_time_formal.py",
    "tests/test_v42_reactions_soak.py",
    "tests/test_v42_o1_chemistry_query.py"
)
Run-TestGroup "v042_recreation_security" @(
    "tests/test_v42_security.py",
    "tests/test_v42_recreation.py"
)
Run-TestGroup "v043_gap_closure" @("tests_v43")
Run-TestGroup "v044_v050" @("tests_v44_v50")

if ($env:ADAM_RERUN_INHERITED_AUDITS -eq "1") {
    Write-Host "[ADAM v0.50] Rerunning inherited audits in isolated processes"
    & python run_v42_audit.py
    if ($LASTEXITCODE -ne 0) { throw "v0.42 audit failed" }
    & python run_v42_living_recreation_audit.py
    if ($LASTEXITCODE -ne 0) { throw "v0.42 recreation audit failed" }
    & python run_v43_gap_closure_audit.py
    if ($LASTEXITCODE -ne 0) { throw "v0.43 audit failed" }
} else {
    Write-Host "[ADAM v0.50] Using manifest-verified inherited audit artifacts; set ADAM_RERUN_INHERITED_AUDITS=1 to regenerate them"
}

Write-Host "[ADAM v0.50] Running integrated audit"
& python run_v50_full_audit.py
if ($LASTEXITCODE -ne 0) { throw "v0.50 audit failed" }

Write-Host "[ADAM v0.50] Running demonstration"
& python RUN_ADAM_V050_DEMO.py | Tee-Object -FilePath (Join-Path $Out "ADAM_V050_DEMO_OUTPUT.json")
if ($LASTEXITCODE -ne 0) { throw "v0.50 demo failed" }

Write-Host "[ADAM v0.50] Qualification complete"
