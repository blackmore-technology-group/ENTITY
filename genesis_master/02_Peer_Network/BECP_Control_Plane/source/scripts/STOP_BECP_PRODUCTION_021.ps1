$ErrorActionPreference = 'Stop'
$Names = @('BECP_Gateway_v0.2.1.exe','BECP_Workstation_Agent_v0.2.1.exe')
$Processes = Get-CimInstance Win32_Process | Where-Object { $Names -contains $_.Name }
foreach ($Process in $Processes) {
    Stop-Process -Id $Process.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1
$Remaining = Get-CimInstance Win32_Process | Where-Object { $Names -contains $_.Name }
$Ports = @{}
foreach ($Port in 8765,8766,8767) {
    $Listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    $Ports["$Port"] = if ($Listener) { [int]$Listener.OwningProcess } else { $null }
}
$Pass = -not $Remaining -and -not $Ports['8765'] -and -not $Ports['8766'] -and -not $Ports['8767']
[ordered]@{status=if($Pass){'PASS'}else{'FAIL'}; remaining_processes=@($Remaining).Count; listeners=$Ports} | ConvertTo-Json -Depth 4
if (-not $Pass) { exit 2 }
