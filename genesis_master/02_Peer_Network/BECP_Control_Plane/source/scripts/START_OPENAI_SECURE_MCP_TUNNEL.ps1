$ErrorActionPreference = 'Stop'
$Root = '<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\BECP'
$TunnelClient = Join-Path $Root 'runtime\openai_tunnel\v0.0.10\tunnel-client.exe'
$Profile = Join-Path $Root 'runtime\openai_tunnel\profiles\becp-openai.yaml'
$RuntimeDir = Join-Path $Root 'runtime\openai_tunnel'
$StatusFile = Join-Path $RuntimeDir 'START_STATUS.json'

if (-not $env:CONTROL_PLANE_TUNNEL_ID) {
    throw 'CONTROL_PLANE_TUNNEL_ID is not set.'
}
if (-not $env:CONTROL_PLANE_API_KEY) {
    throw 'CONTROL_PLANE_API_KEY is not set.'
}
if (-not (Test-Path $TunnelClient)) {
    throw "OpenAI tunnel-client not found: $TunnelClient"
}

$doctor = & $TunnelClient doctor --profile-file $Profile --json 2>&1
if ($LASTEXITCODE -ne 0) {
    $doctor | Set-Content -Encoding UTF8 (Join-Path $RuntimeDir 'doctor_failure.json')
    throw 'OpenAI Secure MCP Tunnel doctor failed.'
}
$existingPidFile = Join-Path $RuntimeDir 'tunnel-client.pid'
if (Test-Path $existingPidFile) {
    $existingPid = Get-Content $existingPidFile -ErrorAction SilentlyContinue
    if ($existingPid -and (Get-Process -Id $existingPid -ErrorAction SilentlyContinue)) {
        Write-Output "Tunnel already running with PID $existingPid"
        exit 0
    }
}

$proc = Start-Process -FilePath $TunnelClient `
    -ArgumentList @('run','--profile-file',$Profile) `
    -WorkingDirectory $Root `
    -WindowStyle Hidden `
    -PassThru

$deadline = (Get-Date).AddSeconds(30)
$ready = $false
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 500
    try {
        $response = Invoke-RestMethod -Uri 'http://127.0.0.1:8788/readyz' -TimeoutSec 2
        if ($response) { $ready = $true; break }
    } catch {}
}
$status = [ordered]@{
    generated_utc = (Get-Date).ToUniversalTime().ToString('o')
    process_id = $proc.Id
    ready = $ready
    profile = $Profile
    mcp_target = 'https://127.0.0.1:8767/mcp'
    health_url = 'http://127.0.0.1:8788'
    secrets_embedded_in_profile = $false
}
$status | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $StatusFile

if (-not $ready) {
    throw "Tunnel process started but readiness was not reached. See $RuntimeDir\tunnel-client.log"
}
Write-Output ($status | ConvertTo-Json -Depth 4)
