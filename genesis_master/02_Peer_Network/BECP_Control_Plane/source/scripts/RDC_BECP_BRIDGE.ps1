param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('status','devices','health','action','terminal-run')]
    [string]$Operation,
    [string]$Device = 'BTG',
    [string]$Capability,
    [string]$ParamsJson = '{}',
    [string]$Command,
    [string]$Cwd,
    [string]$Shell = 'powershell.exe'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Config = Join-Path $Root 'config\RDC_BECP_BRIDGE.json'
$Exe = Join-Path $Root 'build\BECP_0.2.0\bridge\BECP_RDC_Bridge_v0.2.0.exe'
$Python = (Get-Command python.exe -ErrorAction Stop).Source
$BaseArgs = @('--config', $Config, $Operation)
if ($Operation -in @('health','action','terminal-run')) {
    $BaseArgs += @('--device', $Device)
}
if ($Operation -eq 'action') {
    if (-not $Capability) { throw 'Capability is required for action' }
    $BaseArgs += @($Capability, '--params-json', $ParamsJson)
}
if ($Operation -eq 'terminal-run') {
    if (-not $Command) { throw 'Command is required for terminal-run' }
    $BaseArgs += @('--shell', $Shell)
    if ($Cwd) { $BaseArgs += @('--cwd', $Cwd) }
    $BaseArgs += @('--command', $Command)
}

if (Test-Path $Exe) {
    & $Exe @BaseArgs
} else {
    Push-Location $Root
    try { & $Python -m blackmore_ecp.desktop_commander_bridge @BaseArgs }
    finally { Pop-Location }
}
exit $LASTEXITCODE
