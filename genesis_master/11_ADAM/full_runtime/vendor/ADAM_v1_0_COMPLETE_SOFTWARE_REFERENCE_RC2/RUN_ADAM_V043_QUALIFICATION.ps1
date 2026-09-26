$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $Root
try {
  New-Item -ItemType Directory -Force -Path .\artifacts\v43_test_logs | Out-Null
  python -m pytest -q tests/test_v40_compat.py tests/test_v41_adversarial.py tests/test_v41_universe.py tests/test_v42_distributed.py tests/test_v42_o1_chemistry_query.py tests/test_v42_perception_time_formal.py tests/test_v42_reactions_soak.py --disable-warnings | Tee-Object .\artifacts\v43_test_logs\group1.log
  python -m pytest -q tests/test_v42_recreation.py tests/test_v42_security.py --disable-warnings | Tee-Object .\artifacts\v43_test_logs\group2.log
  python -m pytest -q tests_v43 --disable-warnings | Tee-Object .\artifacts\v43_test_logs\group3.log
  python .\run_v43_gap_closure_audit.py
  Write-Host "ADAM v0.43 qualification complete."
} finally {
  Pop-Location
}
