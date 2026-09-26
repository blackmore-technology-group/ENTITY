$ErrorActionPreference = 'Stop'
$Root = '<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\BECP'
$Ca = Join-Path $Root 'runtime\pki\ca\ca.cert.pem'
$Registry = Join-Path $Root 'runtime\registry\devices.json'
$HealthJson = python -c "import httpx,json; print(json.dumps(httpx.get('https://127.0.0.1:8765/health',verify=r'$Ca',timeout=10).json()))"
$Health = $HealthJson | ConvertFrom-Json
$Devices = (Get-Content $Registry -Raw | ConvertFrom-Json).devices
$BTG = $Devices | Where-Object device_id -eq '56d7ed92-c5b4-4cca-addd-02ab1384ca74'
$Ports = @{}
foreach ($Port in 8765,8766,8767) {
    $Listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    $Ports["$Port"] = if ($Listener) { [int]$Listener.OwningProcess } else { $null }
}
$Pass = $Health.ok -and $Health.online_devices -eq 1 -and $BTG.online -and $BTG.agent_version -eq '0.2.1'
$Pass = $Pass -and $Ports['8765'] -and $Ports['8766'] -and $Ports['8767']
$Result = [ordered]@{
    status = if ($Pass) { 'PASS' } else { 'FAIL' }
    gateway_health = $Health
    btg_online = $BTG.online
    btg_agent_version = $BTG.agent_version
    connected_session_id = $BTG.connected_session_id
    listeners = $Ports
}
$Result | ConvertTo-Json -Depth 6
if (-not $Pass) { exit 2 }
