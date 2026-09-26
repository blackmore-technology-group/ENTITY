$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYTHONPATH = $PSScriptRoot
New-Item -ItemType Directory -Force -Path "artifacts/test_logs" | Out-Null
pytest -q tests/test_v40_compat.py tests/test_v41_adversarial.py tests/test_v41_universe.py | Tee-Object -FilePath artifacts/test_logs/v040_v041.log
pytest -q tests/test_v42_distributed.py tests/test_v42_security.py tests/test_v42_perception_time_formal.py tests/test_v42_reactions_soak.py | Tee-Object -FilePath artifacts/test_logs/v042_core.log
pytest -q tests/test_v42_o1_chemistry_query.py | Tee-Object -FilePath artifacts/test_logs/v042_o1.log
pytest -q tests/test_v42_recreation.py | Tee-Object -FilePath artifacts/test_logs/v042_recreation.log
Get-FileHash artifacts/test_logs/*.log -Algorithm SHA256 | Format-Table -AutoSize | Out-String | Set-Content artifacts/test_logs/SHA256SUMS_WINDOWS.txt
python -u run_v42_audit.py --output artifacts/full_audit
python -u run_v42_living_recreation_audit.py
