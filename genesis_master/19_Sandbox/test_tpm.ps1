$ErrorActionPreference='Stop'
$name='ENTITY-TPM-QUALIFY-'+[Guid]::NewGuid().ToString('N')
$provider=[System.Security.Cryptography.CngProvider]::new('Microsoft Platform Crypto Provider')
$params=[System.Security.Cryptography.CngKeyCreationParameters]::new()
$params.Provider=$provider
$params.KeyUsage=[System.Security.Cryptography.CngKeyUsages]::Decryption
$params.ExportPolicy=[System.Security.Cryptography.CngExportPolicies]::None
$key=[System.Security.Cryptography.CngKey]::Create([System.Security.Cryptography.CngAlgorithm]::Rsa,$name,$params)
try {
  $rsa=[System.Security.Cryptography.RSACng]::new($key)
  $plain=New-Object byte[] 32
  $rng=[System.Security.Cryptography.RandomNumberGenerator]::Create()
  $rng.GetBytes($plain)
  $rng.Dispose()
  $cipher=$rsa.Encrypt($plain,[System.Security.Cryptography.RSAEncryptionPadding]::OaepSHA256)
  $round=$rsa.Decrypt($cipher,[System.Security.Cryptography.RSAEncryptionPadding]::OaepSHA256)
  $same=[System.Linq.Enumerable]::SequenceEqual($plain,$round)
  $exportBlocked=$false
  try { $null=$key.Export([System.Security.Cryptography.CngKeyBlobFormat]::Pkcs8PrivateBlob) } catch { $exportBlocked=$true }
  [pscustomobject]@{KeyName=$name;Provider=$key.Provider.Provider;Algorithm=$key.Algorithm.Algorithm;RoundTrip=$same;PrivateExportBlocked=$exportBlocked;IsMachineKey=$key.IsMachineKey} | ConvertTo-Json -Compress
} finally { $key.Delete(); $key.Dispose() }
