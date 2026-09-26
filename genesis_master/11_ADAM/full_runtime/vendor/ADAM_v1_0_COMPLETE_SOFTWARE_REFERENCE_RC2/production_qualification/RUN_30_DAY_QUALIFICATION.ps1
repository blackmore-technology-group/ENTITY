param(
  [string]$Root = "$PSScriptRoot\qualification-state",
  [double]$DurationDays = 30,
  [double]$CycleSeconds = 60
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Push-Location $repo
try {
  python .\production_qualification\run_30_day_qualification.py --root $Root --duration-days $DurationDays --cycle-seconds $CycleSeconds
} finally {
  Pop-Location
}
