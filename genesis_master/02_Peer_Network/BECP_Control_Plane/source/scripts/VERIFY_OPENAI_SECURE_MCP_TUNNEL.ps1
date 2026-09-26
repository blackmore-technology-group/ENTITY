$ErrorActionPreference = 'Stop'
$Root = '<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\BECP'
$RuntimeDir = Join-Path $Root 'runtime\openai_tunnel'
$TunnelClient = Join-Path $RuntimeDir 'v0.0.10\tunnel-client.exe'
$Profile = Join-Path $RuntimeDir 'profiles\becp-openai.yaml'

$health = $null
$ready = $null
try { $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8788/healthz' -TimeoutSec 3 } catch {}
try { $ready = Invoke-RestMethod -Uri 'http://127.0.0.1:8788/readyz' -TimeoutSec 3 } catch {}

$doctorExit = $null
$doctorText = $null
if ($env:CONTROL_PLANE_TUNNEL_ID -and $env:CONTROL_PLANE_API_KEY) {
    $doctorText = & $TunnelClient doctor --profile-file $Profile --json 2>&1
    $doctorExit = $LASTEXITCODE
}

$status = [ordered]@{
    verified_utc = (Get-Date).ToUniversalTime().ToString('o')
    tunnel_credentials_present = [bool]($env:CONTROL_PLANE_TUNNEL_ID -and $env:CONTROL_PLANE_API_KEY)
    health_ok = [bool]$health
    ready_ok = [bool]$ready
    doctor_exit_code = $doctorExit
    doctor_ok = ($doctorExit -eq 0)
    local_becp_mcp = 'https://127.0.0.1:8767/mcp'
}
$statusPath = Join-Path $RuntimeDir 'VERIFY_STATUS.json'
$status | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $statusPath
Write-Output ($status | ConvertTo-Json -Depth 4)

if ($status.tunnel_credentials_present -and (-not $status.ready_ok -or -not $status.doctor_ok)) {
    exit 2
}
exit 0
