param([switch]$InstallDependencies, [switch]$Full, [switch]$RequireRust)
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $Root "RUN_ADAM_V1_RC2_QUALIFICATION.ps1") -InstallDependencies:$InstallDependencies -Full:$Full -RequireRust:$RequireRust
exit $LASTEXITCODE
