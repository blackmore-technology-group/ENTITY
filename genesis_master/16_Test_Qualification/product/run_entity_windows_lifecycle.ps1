$ErrorActionPreference='Stop'
$cli='<LOCAL_DRIVE>/ENTITY_CLEAN_INSTALL_QUALIFICATION\ENTITY_CLI.exe'
$stateA='<LOCAL_DRIVE>/ENTITY_CLEAN_STATE_A'
$stateB='<LOCAL_DRIVE>/ENTITY_CLEAN_STATE_B'
$work='<LOCAL_DRIVE>/ENTITY_CLEAN_LIFECYCLE_WORK'
$btgState='<LOCAL_DRIVE>/BTG_ENTITY_PRODUCTION_STATE'
$graph='<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\evidence\BTG_ENTITY_ECOSYSTEM_CURRENT.json'
foreach($p in @($stateA,$stateB,$work)){Remove-Item $p -Recurse -Force -ErrorAction SilentlyContinue; New-Item -ItemType Directory -Force -Path $p|Out-Null}
function RunEntity([string[]]$a){
  $out=& $cli @a
  if($LASTEXITCODE -ne 0){throw "ENTITY command failed: $($a -join ' ')`n$($out -join "`n")"}
  return (($out -join "`n") | ConvertFrom-Json)
}
$principal=RunEntity @('--state',$stateA,'create-entity','--name','ENTITY Qualification Principal','--alias','qualification.principal.entity')
$device=RunEntity @('--state',$stateA,'create-device','--name','ENTITY Qualification Windows Device','--alias','qualification.device.entity')
$app=RunEntity @('--state',$stateA,'create-app','--name','ENTITY Qualification Application','--alias','qualification.app.entity','--controller',$principal.entity_id)
$bindingPath=Join-Path $work 'binding.json'
$binding=RunEntity @('--state',$stateA,'pair','--principal',$principal.entity_id,'--app',$app.application_entity_id,'--device',$device.entity_id,'--name','Qualification App Installation','--alias','qualification.installation.entity','--out',$bindingPath)
$dataPath=Join-Path $work 'created_data.txt'
'Sovereign ENTITY Windows lifecycle qualification data.' | Set-Content -LiteralPath $dataPath -Encoding UTF8
$asset=RunEntity @('--state',$stateA,'register','--binding',$bindingPath,'--file',$dataPath,'--title','Qualification Data','--kind','DATA','--classification','PRIVATE','--media-type','text/plain')
$event=RunEntity @('--state',$stateA,'event','--binding',$bindingPath,'--event-type','data.qualification_created','--payload','qualification-event-v1')
$exportDir=Join-Path $work 'export'
$export=RunEntity @('--state',$stateA,'export','--entity',$principal.entity_id,'--dest',$exportDir)
$exportVerify=RunEntity @('--state',$stateA,'verify-export','--dest',$exportDir)
$backupPath=Join-Path $work 'entity_state.backup'
$keyPath=Join-Path $work 'recovery.key'
$backup=RunEntity @('--state',$stateA,'backup','--dest',$backupPath,'--key-out',$keyPath)
$restore=RunEntity @('--state',$stateA,'restore','--backup',$backupPath,'--key-file',$keyPath,'--target-state',$stateB)
$restoredVerify=RunEntity @('--state',$stateB,'verify-state','--entity',$principal.entity_id)
$restoredStatus=RunEntity @('--state',$stateB,'status')
$btg=(Get-Content -LiteralPath $graph -Raw | ConvertFrom-Json)
$btgChecks=@{}
foreach($name in @('HUNTAR','SEARCHAR','HIKEAR','BOUNDARYS_BEST')){
  $entityId=$btg.components.$name.entity_id
  $btgChecks[$name]=RunEntity @('--state',$btgState,'verify-state','--entity',$entityId)
}
$btgValid=$true
foreach($v in $btgChecks.Values){if(-not $v.valid){$btgValid=$false}}
$checks=[ordered]@{
  clean_install_runtime_present=(Test-Path $cli)
  principal_created=[bool]$principal.entity_id
  device_created=[bool]$device.entity_id
  application_created=[bool]$app.application_entity_id
  principal_device_application_pairing=[bool]$binding.installation_entity_id
  governed_data_asset_created=[bool]$asset.asset.asset_id
  governed_event_created=[bool]$event.event.event_id
  export_verified=[bool]$exportVerify.valid
  private_keys_excluded_from_portable_export=($exportVerify.private_keys_included -eq $false)
  encrypted_backup_created=(Test-Path $backupPath)
  encrypted_backup_restored=[bool]$restore.restored
  restored_identity_verified=[bool]$restoredVerify.valid
  restored_entity_id_unchanged=($restoredVerify.entity_id -eq $principal.entity_id)
  btg_huntar_searchar_hikear_boundarys_best_verified=$btgValid
}
$status=if(($checks.Values -notcontains $false)){'PASS'}else{'FAIL'}
$evidence=[ordered]@{
  schema='entity-windows-product-lifecycle-qualification-v1'; status=$status
  product='ENTITY'; version='1.0.0-rc1'; clean_install_scope='ISOLATED_INSTALL_ON_BTG_PC_NOT_SECOND_PHYSICAL_MACHINE'
  checks=$checks; principal_entity_id=$principal.entity_id; device_entity_id=$device.entity_id
  application_entity_id=$app.application_entity_id; installation_entity_id=$binding.installation_entity_id
  asset_id=$asset.asset.asset_id; export_entity_id=$export.entity_id; restored_entity_id=$restoredVerify.entity_id
  btg_application_identity_checks=$btgChecks
  claim_boundary='This proves clean isolated installation and restore on the BTG Windows computer. It does not satisfy the separate two-physical-device external gate.'
}
$out='<LOCAL_DRIVE>/Sovereign_Entity_Network\16_Test_Qualification\evidence\ENTITY_WINDOWS_PRODUCT_LIFECYCLE_CURRENT.json'
$evidence|ConvertTo-Json -Depth 12|Set-Content -LiteralPath $out -Encoding UTF8
$hash=(Get-FileHash $out -Algorithm SHA256).Hash.ToLower()
"$hash  ENTITY_WINDOWS_PRODUCT_LIFECYCLE_CURRENT.json"|Set-Content -LiteralPath ($out+'.sha256') -Encoding ASCII
$evidence|ConvertTo-Json -Depth 12
if($status -ne 'PASS'){exit 2}
