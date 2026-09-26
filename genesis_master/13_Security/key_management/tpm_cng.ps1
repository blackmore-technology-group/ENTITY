param(
  [Parameter(Mandatory=$true)][ValidateSet('ensure','wrap','unwrap','probe','delete')][string]$Action,
  [Parameter(Mandatory=$true)][string]$KeyName,
  [string]$DataB64=''
)
$ErrorActionPreference='Stop'
$provider=[System.Security.Cryptography.CngProvider]::new('Microsoft Platform Crypto Provider')
function Open-Or-Create([string]$name) {
  if ([System.Security.Cryptography.CngKey]::Exists($name,$provider)) {
    return [System.Security.Cryptography.CngKey]::Open($name,$provider)
  }
  $p=[System.Security.Cryptography.CngKeyCreationParameters]::new()
  $p.Provider=$provider
  $p.KeyUsage=[System.Security.Cryptography.CngKeyUsages]::Decryption
  $p.ExportPolicy=[System.Security.Cryptography.CngExportPolicies]::None
  return [System.Security.Cryptography.CngKey]::Create([System.Security.Cryptography.CngAlgorithm]::Rsa,$name,$p)
}
if ($Action -eq 'delete') {
  if ([System.Security.Cryptography.CngKey]::Exists($KeyName,$provider)) {
    $k=[System.Security.Cryptography.CngKey]::Open($KeyName,$provider); $k.Delete(); $k.Dispose()
  }
  '{"deleted":true}'
  exit 0
}
$key=Open-Or-Create $KeyName
try {
  $rsa=[System.Security.Cryptography.RSACng]::new($key)
  if ($Action -eq 'ensure') {
    [pscustomobject]@{ready=$true;key_name=$KeyName;provider=$key.Provider.Provider;algorithm=$key.Algorithm.Algorithm;machine_key=$key.IsMachineKey} | ConvertTo-Json -Compress
  } elseif ($Action -eq 'wrap') {
    $raw=[Convert]::FromBase64String($DataB64)
    $cipher=$rsa.Encrypt($raw,[System.Security.Cryptography.RSAEncryptionPadding]::OaepSHA256)
    [pscustomobject]@{wrapped_b64=[Convert]::ToBase64String($cipher);provider=$key.Provider.Provider;key_name=$KeyName} | ConvertTo-Json -Compress
  } elseif ($Action -eq 'unwrap') {
    $cipher=[Convert]::FromBase64String($DataB64)
    $plain=$rsa.Decrypt($cipher,[System.Security.Cryptography.RSAEncryptionPadding]::OaepSHA256)
    [pscustomobject]@{plain_b64=[Convert]::ToBase64String($plain);provider=$key.Provider.Provider;key_name=$KeyName} | ConvertTo-Json -Compress
  } elseif ($Action -eq 'probe') {
    $exportBlocked=$false
    try { $null=$key.Export([System.Security.Cryptography.CngKeyBlobFormat]::Pkcs8PrivateBlob) } catch { $exportBlocked=$true }
    $tpm=Get-Tpm
    [pscustomobject]@{ready=($tpm.TpmPresent -and $tpm.TpmReady);tpm_present=$tpm.TpmPresent;tpm_ready=$tpm.TpmReady;tpm_enabled=$tpm.TpmEnabled;tpm_activated=$tpm.TpmActivated;provider=$key.Provider.Provider;key_name=$KeyName;algorithm=$key.Algorithm.Algorithm;private_export_blocked=$exportBlocked} | ConvertTo-Json -Compress
  }
} finally {
  $rsa.Dispose(); $key.Dispose()
}
