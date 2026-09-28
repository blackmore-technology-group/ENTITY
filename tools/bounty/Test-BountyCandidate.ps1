[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[^/\s]+/[^/\s]+$')][string]$Repository,
    [Parameter(Mandatory = $true)][ValidateRange(1, [int]::MaxValue)][int]$IssueNumber,
    [Parameter(Mandatory = $true)][decimal]$ExpectedAmount,
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$')][string]$ContributorGitHubLogin,
    [string]$Currency = 'USD',
    [string]$BountyPlatform = 'UNKNOWN',
    [ValidateSet('UNKNOWN', 'ADVERTISED', 'PLATFORM_VERIFIED', 'ESCROW_VERIFIED')]
    [string]$FundingStatus = 'UNKNOWN',
    [ValidateSet('UNKNOWN', 'NOT_REGISTERED', 'REGISTERED', 'VERIFIED')]
    [string]$PlatformAccountStatus = 'UNKNOWN',
    [ValidateSet('UNKNOWN', 'NOT_CONFIGURED', 'PENDING_VERIFICATION', 'READY', 'DIRECT_PAYMENT_CONFIRMED')]
    [string]$PayoutStatus = 'UNKNOWN',
    [ValidateSet('UNKNOWN', 'INDIVIDUAL', 'BUSINESS')]
    [string]$PayeeType = 'UNKNOWN',
    [string]$PayeeDisplayName = '',
    [string]$PlatformAccountReference = '',
    [ValidateSet('UNKNOWN', 'NONE_REQUIRED', 'REVIEWED')]
    [string]$ClaStatus = 'UNKNOWN',
    [ValidateSet('UNKNOWN', 'ALLOWED', 'DISCLOSED_ALLOWED', 'PROHIBITED')]
    [string]$AiContributionPolicy = 'UNKNOWN',
    [string]$OutFile = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-GitHubPublicGet {
    param([Parameter(Mandatory = $true)][string]$Uri)
    $headers = @{
        Accept = 'application/vnd.github+json'
        'X-GitHub-Api-Version' = '2022-11-28'
        'User-Agent' = 'BTG-ENTITY-Bounty-Preflight'
    }
    if ($env:GITHUB_TOKEN) { $headers.Authorization = "Bearer $($env:GITHUB_TOKEN)" }
    Invoke-RestMethod -Method Get -Uri $Uri -Headers $headers
}

function Get-LicenseInfo {
    param([Parameter(Mandatory = $true)][string]$RepositoryName)
    try {
        $r = Invoke-GitHubPublicGet "https://api.github.com/repos/$RepositoryName/license"
        [ordered]@{
            present = $true
            name = [string]$r.license.name
            spdx_id = [string]$r.license.spdx_id
            path = [string]$r.path
            html_url = [string]$r.html_url
        }
    }
    catch {
        [ordered]@{ present = $false; name = ''; spdx_id = ''; path = ''; html_url = '' }
    }
}

function Add-Finding {
    param(
        [Parameter(Mandatory = $true)][System.Collections.Generic.List[object]]$List,
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][string]$Message
    )
    $List.Add([ordered]@{ code = $Code; message = $Message }) | Out-Null
}

$repoApi = "https://api.github.com/repos/$Repository"
$repo = Invoke-GitHubPublicGet $repoApi
$issue = Invoke-GitHubPublicGet "$repoApi/issues/$IssueNumber"
$license = Get-LicenseInfo $Repository

# The issues endpoint also returns PRs. Test property existence without violating StrictMode.
$isPullRequest = $issue.PSObject.Properties.Name -contains 'pull_request'
$labelNames = @($issue.labels | ForEach-Object { [string]$_.name })
$titleText = [string]$issue.title
$bodyText = [string]$issue.body
$combinedText = "$titleText`n$bodyText`n$($labelNames -join ' | ')"

$failures = [System.Collections.Generic.List[object]]::new()
$warnings = [System.Collections.Generic.List[object]]::new()

if ([string]$issue.state -ne 'open') { Add-Finding $failures 'ISSUE_NOT_OPEN' "Issue state is '$($issue.state)', not open." }
if ($isPullRequest) { Add-Finding $failures 'ISSUE_IS_PULL_REQUEST' 'The supplied number resolves to a pull request.' }
if ([bool]$repo.archived) { Add-Finding $failures 'REPOSITORY_ARCHIVED' 'Repository is archived.' }
if ([bool]$repo.disabled) { Add-Finding $failures 'REPOSITORY_DISABLED' 'Repository is disabled.' }

if (-not $license.present) {
    Add-Finding $failures 'LICENSE_NOT_DETECTED' 'GitHub did not expose a repository license. Do not use this as the first rights/provenance proof without explicit licensing evidence.'
}
elseif (-not $license.spdx_id -or $license.spdx_id -eq 'NOASSERTION') {
    Add-Finding $failures 'LICENSE_AMBIGUOUS' 'A license file exists but GitHub could not identify a clear SPDX license.'
}

$blockedLabels = @($labelNames | Where-Object { $_ -match '(?i)(rewarded|paid|completed|done|closed|cancelled|canceled|on[ -]?hold|hold|paused)' })
if ($blockedLabels.Count -gt 0) { Add-Finding $failures 'BLOCKING_LABEL' "Blocking label(s): $($blockedLabels -join ', ')" }
if ($combinedText -match '(?i)\b(on hold|bounty paused|bounty cancelled|bounty canceled|already rewarded|already paid)\b') {
    Add-Finding $failures 'BLOCKING_TEXT' 'Issue text indicates the bounty may be on hold, cancelled, or already rewarded.'
}

if ($combinedText -notmatch '(?i)(/bounty\s+\$?\s*[0-9]|\bbounty\b|reward\s*[:=]?\s*\$\s*[0-9])') {
    Add-Finding $failures 'NO_EXPLICIT_BOUNTY_SIGNAL' 'No explicit bounty/reward signal was detected in title, body, or labels.'
}

$amountCandidates = [System.Collections.Generic.List[decimal]]::new()
foreach ($m in [regex]::Matches($combinedText, '(?i)(?:/bounty\s*)?\$\s*([0-9]+(?:\.[0-9]{1,2})?)')) {
    $value = 0m
    if ([decimal]::TryParse($m.Groups[1].Value, [Globalization.NumberStyles]::Number, [Globalization.CultureInfo]::InvariantCulture, [ref]$value)) {
        $amountCandidates.Add($value) | Out-Null
    }
}
$amountSeen = @($amountCandidates | Sort-Object -Unique)
if ($amountSeen.Count -eq 0) {
    Add-Finding $warnings 'AMOUNT_NOT_MACHINE_DETECTED' "Expected $ExpectedAmount $Currency but no dollar amount was machine-detected; verify the platform evidence manually."
}
elseif ($ExpectedAmount -notin $amountSeen) {
    Add-Finding $failures 'AMOUNT_MISMATCH' "Expected $ExpectedAmount; detected: $($amountSeen -join ', ')."
}

if ([string]::IsNullOrWhiteSpace($BountyPlatform) -or $BountyPlatform -eq 'UNKNOWN') {
    Add-Finding $failures 'BOUNTY_PLATFORM_UNKNOWN' 'The bounty platform must be identified before a PREPARED record can be created.'
}
if ($FundingStatus -notin @('PLATFORM_VERIFIED', 'ESCROW_VERIFIED')) {
    Add-Finding $failures 'FUNDING_NOT_VERIFIED' "FundingStatus is '$FundingStatus'. An advertised amount alone is not enough for the first economic-lineage proof."
}

# Payment-readiness gate: provenance without an identified, payable claimant is not a complete bounty-economy proof.
if ($PlatformAccountStatus -notin @('REGISTERED', 'VERIFIED')) {
    Add-Finding $failures 'PLATFORM_ACCOUNT_NOT_READY' "PlatformAccountStatus is '$PlatformAccountStatus'. Register the GitHub contributor identity with the bounty platform before creating an ENTITY PREPARED record."
}
if ($PayoutStatus -notin @('READY', 'DIRECT_PAYMENT_CONFIRMED')) {
    Add-Finding $failures 'PAYOUT_NOT_READY' "PayoutStatus is '$PayoutStatus'. Complete platform payout/KYC setup or confirm the direct-payment arrangement before proceeding."
}
if ($PayeeType -eq 'UNKNOWN') {
    Add-Finding $failures 'PAYEE_TYPE_UNKNOWN' 'Identify whether the economic payee is an INDIVIDUAL or BUSINESS.'
}
if ([string]::IsNullOrWhiteSpace($PayeeDisplayName)) {
    Add-Finding $failures 'PAYEE_NAME_MISSING' 'A non-sensitive payee display/legal name is required for the economic lineage record.'
}
if ([string]::IsNullOrWhiteSpace($PlatformAccountReference)) {
    Add-Finding $warnings 'PLATFORM_ACCOUNT_REFERENCE_MISSING' 'No non-sensitive platform account/profile reference was supplied. Record one when the platform exposes it.'
}

if ($ClaStatus -eq 'UNKNOWN') { Add-Finding $warnings 'CLA_NOT_REVIEWED' 'Contributor agreement/CLA status still requires review.' }
if ($AiContributionPolicy -eq 'UNKNOWN') { Add-Finding $warnings 'AI_POLICY_NOT_REVIEWED' 'AI-assisted contribution policy still requires review.' }
if ($AiContributionPolicy -eq 'PROHIBITED') { Add-Finding $failures 'AI_CONTRIBUTION_PROHIBITED' 'Repository policy prohibits the intended AI-assisted contribution workflow.' }

$sensitivePattern = '(?is)(paste|include|provide|add).{0,160}(full|complete|entire|verbatim|everything).{0,160}(system prompt|session|initialization|startup|boot context|pre[- ]?task context|platform instructions|runtime instructions|instructions and guidelines|context before)'
if ($combinedText -match $sensitivePattern) {
    Add-Finding $failures 'UNSAFE_PRIVATE_CONTEXT_REQUIREMENT' 'Issue appears to require disclosure of private session/system initialization material. Reject this opportunity.'
}

$ready = $failures.Count -eq 0
$verdict = if ($ready) { 'READY_FOR_ENTITY_PREPARED' } else { 'REJECT_OR_HOLD' }
$result = [ordered]@{
    preflight_version = 2
    evaluated_at_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffZ')
    verdict = $verdict
    ready_for_entity_prepared = $ready
    candidate = [ordered]@{
        repository = $Repository
        issue_number = $IssueNumber
        issue_url = [string]$issue.html_url
        issue_title = $titleText
        issue_state = [string]$issue.state
        repository_archived = [bool]$repo.archived
        repository_disabled = [bool]$repo.disabled
        default_branch = [string]$repo.default_branch
        platform = $BountyPlatform
        expected_amount = $ExpectedAmount
        currency = $Currency.ToUpperInvariant()
        funding_status = $FundingStatus
        detected_dollar_amounts = @($amountSeen)
        labels = @($labelNames)
    }
    claimant_and_payment_gate = [ordered]@{
        github_contributor_login = $ContributorGitHubLogin
        platform_account_status = $PlatformAccountStatus
        platform_account_reference = $PlatformAccountReference
        payout_status = $PayoutStatus
        payee_type = $PayeeType
        payee_display_name = $PayeeDisplayName
        sensitive_financial_or_kyc_data_recorded = $false
    }
    rights_gate = [ordered]@{
        license_present = [bool]$license.present
        license_name = [string]$license.name
        license_spdx_id = [string]$license.spdx_id
        license_url = [string]$license.html_url
        cla_status = $ClaStatus
        ai_contribution_policy = $AiContributionPolicy
    }
    failures = @($failures)
    warnings = @($warnings)
    claim_boundary = [ordered]@{
        preflight_does_not_claim_bounty = $true
        preflight_does_not_claim_acceptance = $true
        preflight_does_not_claim_payment = $true
        preflight_does_not_create_entity_rights = $true
        preflight_does_not_store_bank_or_kyc_secrets = $true
    }
}

$json = $result | ConvertTo-Json -Depth 10
if ($OutFile) {
    $parent = Split-Path -Parent $OutFile
    if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    Set-Content -LiteralPath $OutFile -Value $json -Encoding UTF8
}

Write-Host "Bounty candidate verdict: $verdict" -ForegroundColor $(if ($ready) { 'Green' } else { 'Yellow' })
Write-Host "Repository: $Repository"
Write-Host "Issue: #$IssueNumber - $titleText"
Write-Host "Issue state: $($issue.state)"
Write-Host "Contributor: @$ContributorGitHubLogin"
Write-Host "Platform account: $PlatformAccountStatus"
Write-Host "Payout: $PayoutStatus"
Write-Host "Payee: $PayeeType / $PayeeDisplayName"
Write-Host "License: $(if ($license.present) { $license.spdx_id } else { 'NOT DETECTED' })"
Write-Host "Funding: $FundingStatus"
Write-Host "Failures: $($failures.Count) | Warnings: $($warnings.Count)"
foreach ($f in $failures) { Write-Host "FAIL [$($f.code)] $($f.message)" -ForegroundColor Red }
foreach ($w in $warnings) { Write-Host "WARN [$($w.code)] $($w.message)" -ForegroundColor Yellow }
if ($OutFile) { Write-Host "JSON: $OutFile" }

if (-not $ready) { throw 'Bounty candidate failed preflight. Do not create an ENTITY PREPARED record for this candidate.' }
Write-Host 'PASS: candidate is eligible to proceed to an ENTITY PREPARED record, subject to the recorded warnings.' -ForegroundColor Green
