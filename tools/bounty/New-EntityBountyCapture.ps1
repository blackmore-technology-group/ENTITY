[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$ExternalRepository,
    [Parameter(Mandatory = $true)][int]$IssueNumber,
    [Parameter(Mandatory = $true)][string]$BountyPlatform,
    [Parameter(Mandatory = $true)][decimal]$BountyAmount,
    [Parameter(Mandatory = $true)][string]$Currency,
    [ValidateSet("FUNDED", "PROMISED_CONTINGENT", "PRO_BONO")]
    [string]$ContributionClass = "FUNDED",
    [ValidateSet("UNKNOWN", "NOT_APPLICABLE", "ADVERTISED", "PLATFORM_VERIFIED", "ESCROW_VERIFIED")]
    [string]$FundingStatus = "UNKNOWN",
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

if ($ContributionClass -eq "PRO_BONO" -and $BountyAmount -ne 0) {
    throw "PRO_BONO contributions must use BountyAmount 0."
}
if ($ContributionClass -eq "PRO_BONO" -and $EvidenceState -eq "SETTLED") {
    throw "A PRO_BONO contribution cannot be marked SETTLED. Use UPSTREAM_ACCEPTED for an accepted zero-cash contribution."
}

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
            relative_path = $item.Name
            bytes = $item.Length
            sha256 = (Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash.ToLowerInvariant()
        })
    }

    $base = $resolved.TrimEnd('\\','/')
    $files = Get-ChildItem -LiteralPath $base -File -Recurse | Sort-Object FullName
    $rows = foreach ($file in $files) {
        $relative = $file.FullName.Substring($base.Length).TrimStart('\\','/') -replace '\\\\','/'
        [ordered]@{
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
$recordId = "contribution-$stamp-$repoSlug-issue-$IssueNumber"
$outputBase = Join-Path $repoRoot $OutputRoot
$recordDir = Join-Path $outputBase $recordId
New-Item -ItemType Directory -Force -Path $recordDir | Out-Null

$entityRepoHead = (& git rev-parse HEAD).Trim()
$entityBranch = (& git rev-parse --abbrev-ref HEAD).Trim()
$entityOrigin = (& git config --get remote.origin.url).Trim()

$workHashes = @()
if ($WorkPath) { $workHashes = @(Get-PathDigest -Path $WorkPath) }

$entityExportHashes = @()
if ($EntityExportPath) {
    $entityExportHashes = @(Get-PathDigest -Path $EntityExportPath)
    if ($EvidenceState -eq "PREPARED") { $EvidenceState = "ENTITY_RECORDED" }
}

[decimal]$contingentValue = if ($ContributionClass -eq "PROMISED_CONTINGENT") { $BountyAmount } else { 0 }
[decimal]$realizedCash = if ($EvidenceState -eq "SETTLED") { $BountyAmount } else { 0 }

$record = [ordered]@{
    record_version = 2
    record_id = $recordId
    captured_at_utc = $timestampUtc
    experiment = "ENTITY v3.4.3 contribution-value lineage"
    contribution_class = $ContributionClass
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
    opportunity = [ordered]@{
        platform = $BountyPlatform
        url = $BountyUrl
        external_repository = $ExternalRepository
        issue_number = $IssueNumber
        advertised_or_expected_amount = $BountyAmount
        currency = $Currency.ToUpperInvariant()
        funding_status = $FundingStatus
        evidence_state = $EvidenceState
    }
    economic = [ordered]@{
        class = $ContributionClass
        contingent_value = $contingentValue
        realized_cash = $realizedCash
        payment_settled = ($EvidenceState -eq "SETTLED")
        pro_bono_cash_value_is_zero = ($ContributionClass -eq "PRO_BONO")
        promised_value_is_not_revenue_until_settled = $true
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
        work_path_supplied = [bool]$WorkPath
        entity_export_path_supplied = [bool]$EntityExportPath
        work_file_count = @($workHashes).Count
        entity_export_file_count = @($entityExportHashes).Count
        local_absolute_paths_persisted = $false
    }
    claims = [ordered]@{
        upstream_accepted = ($EvidenceState -in @("UPSTREAM_ACCEPTED", "SETTLED"))
        payment_settled = ($EvidenceState -eq "SETTLED")
        rights_claims_must_be_supported_by_upstream_terms = $true
        provenance_record_does_not_override_upstream_license = $true
        external_acceptance_is_independent_validation_when_evidenced = $true
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
    contribution_class = $ContributionClass
    bounty_record = [ordered]@{ file = "bounty_record.json"; sha256 = $recordSha }
    evidence_hashes = [ordered]@{ file = "evidence_hashes.json"; sha256 = $hashesSha }
}
$indexPath = Join-Path $recordDir "INDEX.json"
$index | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $indexPath -Encoding UTF8

Write-Host "ENTITY contribution capture prepared." -ForegroundColor Green
Write-Host "Record: $recordId"
Write-Host "Class: $ContributionClass"
Write-Host "Directory: $recordDir"
Write-Host "State: $EvidenceState"
Write-Host "Contingent value: $contingentValue $($Currency.ToUpperInvariant())"
Write-Host "Realized cash: $realizedCash $($Currency.ToUpperInvariant())"
Write-Host "No local absolute paths were persisted in public evidence."
Write-Host "No ENTITY protocol, schema, source or architecture files were modified by this script."
