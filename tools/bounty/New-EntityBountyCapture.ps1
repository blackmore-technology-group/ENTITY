[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ExternalRepository,
    [Parameter(Mandatory = $true)][int]$IssueNumber,
    [Parameter(Mandatory = $true)][string]$BountyPlatform,
    [Parameter(Mandatory = $true)][decimal]$BountyAmount,
    [Parameter(Mandatory = $true)][string]$Currency,
    [string]$BountyUrl = "",
    [string]$ExternalCommit = "",
    [string]$ExternalPullRequest = "",
    [string]$UpstreamLicense = "UNKNOWN",
    [string]$ClaStatus = "UNKNOWN",
    [string]$HumanAuthor = "Shawn Blackmore",
    [string]$CorporateContributor = "Blackmore Technology Group Limited",
    [string]$WorkPath = "",
    [string]$EntityExportPath = "",
    [ValidateSet("PREPARED", "ENTITY_RECORDED", "UPSTREAM_ACCEPTED", "SETTLED")]
    [string]$EvidenceState = "PREPARED",
    [string]$OutputRoot = "evidence/bounty"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    $root = (& git rev-parse --show-toplevel 2>$null).Trim()
    if (-not $root) { throw "Run this script from inside a Git repository." }
    return (Resolve-Path $root).Path
}

function Get-PathDigest {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Evidence path does not exist: $Path"
    }

    $resolved = (Resolve-Path -LiteralPath $Path).Path
    if (Test-Path -LiteralPath $resolved -PathType Leaf) {
        $item = Get-Item -LiteralPath $resolved
        return @([ordered]@{
            path = $resolved
            relative_path = $item.Name
            bytes = $item.Length
            sha256 = (Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash.ToLowerInvariant()
        })
    }

    $base = $resolved.TrimEnd('\','/')
    $files = Get-ChildItem -LiteralPath $base -File -Recurse | Sort-Object FullName
    $rows = foreach ($file in $files) {
        $relative = $file.FullName.Substring($base.Length).TrimStart('\','/') -replace '\\','/'
        [ordered]@{
            path = $file.FullName
            relative_path = $relative
            bytes = $file.Length
            sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    }
    return @($rows)
}

$repoRoot = Get-RepoRoot
Set-Location $repoRoot

$timestampUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
$repoSlug = ($ExternalRepository -replace '[^A-Za-z0-9._-]', '-')
$recordId = "bounty-$stamp-$repoSlug-issue-$IssueNumber"
$outputBase = Join-Path $repoRoot $OutputRoot
$recordDir = Join-Path $outputBase $recordId
New-Item -ItemType Directory -Force -Path $recordDir | Out-Null

$entityRepoHead = (& git rev-parse HEAD).Trim()
$entityBranch = (& git rev-parse --abbrev-ref HEAD).Trim()
$entityOrigin = (& git config --get remote.origin.url).Trim()

$workHashes = @()
if ($WorkPath) {
    $workHashes = @(Get-PathDigest -Path $WorkPath)
}

$entityExportHashes = @()
if ($EntityExportPath) {
    $entityExportHashes = @(Get-PathDigest -Path $EntityExportPath)
    if ($EvidenceState -eq "PREPARED") {
        $EvidenceState = "ENTITY_RECORDED"
    }
}

$record = [ordered]@{
    record_version = 1
    record_id = $recordId
    captured_at_utc = $timestampUtc
    experiment = "ENTITY v3.4.2 bounty lineage"
    scope = [ordered]@{
        architecture_change = $false
        protocol_change = $false
        schema_change = $false
        implementation_change_required_by_harness = $false
        installed_entity_is_source_of_lineage_record = $true
        powershell_harness_is_evidence_capture_only = $true
    }
    contributor = [ordered]@{
        human_author = $HumanAuthor
        corporate_contributor = $CorporateContributor
    }
    bounty = [ordered]@{
        platform = $BountyPlatform
        url = $BountyUrl
        external_repository = $ExternalRepository
        issue_number = $IssueNumber
        amount = $BountyAmount
        currency = $Currency.ToUpperInvariant()
        state = $EvidenceState
    }
    upstream = [ordered]@{
        commit = $ExternalCommit
        pull_request = $ExternalPullRequest
        license = $UpstreamLicense
        cla_status = $ClaStatus
    }
    entity_repository_context = [ordered]@{
        origin = $entityOrigin
        branch = $entityBranch
        head = $entityRepoHead
    }
    evidence = [ordered]@{
        work_path = $WorkPath
        entity_export_path = $EntityExportPath
        work_file_count = @($workHashes).Count
        entity_export_file_count = @($entityExportHashes).Count
    }
    claims = [ordered]@{
        upstream_accepted = ($EvidenceState -in @("UPSTREAM_ACCEPTED", "SETTLED"))
        payment_settled = ($EvidenceState -eq "SETTLED")
        rights_claims_must_be_supported_by_upstream_terms = $true
        provenance_record_does_not_override_upstream_license = $true
    }
}

$recordPath = Join-Path $recordDir "bounty_record.json"
$hashesPath = Join-Path $recordDir "evidence_hashes.json"

$record | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $recordPath -Encoding UTF8
([ordered]@{
    record_id = $recordId
    generated_at_utc = $timestampUtc
    work = @($workHashes)
    entity_export = @($entityExportHashes)
}) | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $hashesPath -Encoding UTF8

$recordSha = (Get-FileHash -LiteralPath $recordPath -Algorithm SHA256).Hash.ToLowerInvariant()
$hashesSha = (Get-FileHash -LiteralPath $hashesPath -Algorithm SHA256).Hash.ToLowerInvariant()

$index = [ordered]@{
    record_id = $recordId
    bounty_record = [ordered]@{ file = "bounty_record.json"; sha256 = $recordSha }
    evidence_hashes = [ordered]@{ file = "evidence_hashes.json"; sha256 = $hashesSha }
}
$indexPath = Join-Path $recordDir "INDEX.json"
$index | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $indexPath -Encoding UTF8

Write-Host "ENTITY bounty capture prepared." -ForegroundColor Green
Write-Host "Record: $recordId"
Write-Host "Directory: $recordDir"
Write-Host "State: $EvidenceState"
Write-Host "No ENTITY protocol, schema, source or architecture files were modified by this script."
