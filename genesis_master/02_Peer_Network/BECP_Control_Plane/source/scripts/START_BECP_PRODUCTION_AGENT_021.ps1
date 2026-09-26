$ErrorActionPreference = 'Stop'
$Root = '<LOCAL_DRIVE>/Blackmore_Technology_Group\Software Development\BECP'
$DeviceId = '56d7ed92-c5b4-4cca-addd-02ab1384ca74'
$Exe = Join-Path $Root 'build\BECP_0.2.1\agent\BECP_Workstation_Agent_v0.2.1.exe'
$Config = Join-Path $Root 'config\BTG_ENGINEERING_WORKSTATION.json'
$Cert = Join-Path $Root "runtime\pki\devices\$DeviceId\device.cert.pem"
$Key = Join-Path $Root "runtime\pki\devices\$DeviceId\device.key.pem"
$CA = Join-Path $Root 'runtime\pki\ca\ca.cert.pem'
& $Exe --config $Config --gateway 'wss://127.0.0.1:8766/agent' --device-cert $Cert --device-key $Key --ca-cert $CA --heartbeat-seconds 5 --reconnect-seconds 5
