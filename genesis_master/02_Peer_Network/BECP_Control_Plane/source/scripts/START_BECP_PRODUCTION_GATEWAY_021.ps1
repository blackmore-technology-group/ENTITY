$ErrorActionPreference = 'Stop'
$Root = '<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\BECP'
$Exe = Join-Path $Root 'build\BECP_0.2.1\server\BECP_Gateway_v0.2.1.exe'
$Config = Join-Path $Root 'config\GATEWAY_LOCAL_QUALIFICATION.json'
& $Exe --config $Config
