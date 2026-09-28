[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[^/\s]+/[^/\s]+$')][string]$Repository,
    [Parameter(Mandatory = $true)][ValidateRange(1, [int]::MaxValue)][int]$IssueNumber,
    [Parameter(Mandatory = $true)][decimal]$ExpectedAmount,
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$')][string]$ContributorGitHubLogin,
    [ValidateSet('FUNDED', 'PROMISED_CONTINGENT', 'PRO_BONO')]
    [string]$ContributionClass = 'FUNDED',
    [string]$Currency = 'USD',
    [string]$BountyPlatform = 'UNKNOWN',
    [ValidateSet('UNKNOWN', 'NOT_APPLICABLE', 'ADVERTISED', 'PLATFORM_VERIFIED', 'ESCROW_VERIFIED')]
    [string]$FundingStatus = 'UNKNOWN',
    [ValidateSet('UNKNOWN', 'NOT_REGISTERED', 'REGISTERED', 'VERIFIED', 'NOT_APPLICABLE')]
    [string]$PlatformAccountStatus = 'UNKNOWN',
    [ValidateSet('UNKNOWN', 'NOT_CONFIGURED', 'PENDING_VERIFICATION', 'READY', 'DIRECT_PAYMENT_CONFIRMED', 'NOT_APPLICABLE')]
    [string]$PayoutStatus = 'UNKNOWN',
    [ValidateSet('UNKNOWN', 'INDIVIDUAL', 'BUSINESS', 'NOT_APPLICABLE')]
    [string]$PayeeType = 'UNKNOWN',
    [string]$PayeeDisplayName = '',
    [string]$PlatformAccountReference = '',
    [ValidateSet('UNKNOWN', 'NONE_REQUIRED', 'REVIEWED', 'REQUIRED_PENDING_SIGNATURE', 'SIGNED')]
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
        'User-Agent' = 'BTG-ENTITY-Contribution-Preflight'
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
    Add-Finding $failures 'LICENSE_NOT_DETECTED' 'GitHub did not expose a repository license. Obtain explicit licensing evidence before using the contribution for rights/provenance proof.'
}
elseif (-not $license.spdx_id -or $license.spdx_id -eq 'NOASSERTION') {
    Add-Finding $failures 'LICENSE_AMBIGUOUS' 'A license file exists but GitHub could not identify a clear SPDX license.'
}

$blockedLabels = @($labelNames | Where-Object { $_ -match '(?i)(rewarded|paid|completed|done|closed|cancelled|canceled|on[ -]?hold|hold|paused)' })
if ($blockedLabels.Count -gt 0) { Add-Finding $failures 'BLOCKING_LABEL' "Blocking label(s): $($blockedLabels -join ', ')" }
if ($combinedText -match '(?i)\b(on hold|bounty paused|bounty cancelled|bounty canceled|already rewarded|already paid)\b') {
    Add-Finding $failures 'BLOCKING_TEXT' 'Issue text indicates the opportunity may be on hold, cancelled, or already rewarded.'
}

$sensitivePattern = '(?is)(paste|include|provide|add).{0,160}(full|complete|entire|verbatim|everything).{0,160}(system prompt|session|initialization|startup|boot context|pre[- ]?task context|platform instructions|runtime instructions|instructions and guidelines|context before)'
if ($combinedText -match $sensitivePattern) {
    Add-Finding $failures 'UNSAFE_PRIVATE_CONTEXT_REQUIREMENT' 'Issue appears to require disclosure of private session/system initialization material. Reject this opportunity.'
}

if ($AiContributionPolicy -eq 'PROHIBITED') { Add-Finding $failures 'AI_CONTRIBUTION_PROHIBITED' 'Repository policy prohibits the intended AI-assisted contribution workflow.' }
if ($ClaStatus -eq 'UNKNOWN') { Add-Finding $warnings 'CLA_NOT_REVIEWED' 'Contributor agreement/CLA status still requires review before submission.' }
if ($ClaStatus -eq 'REQUIRED_PENDING_SIGNATURE') { Add-Finding $warnings 'CLA_SIGNATURE_PENDING' 'The repository requires a CLA and signature is still pending. A PREPARED record is allowed, but do not submit the external PR until the required CLA is completed.' }
if ($AiContributionPolicy -eq 'UNKNOWN') { Add-Finding $warnings 'AI_POLICY_NOT_REVIEWED' 'AI-assisted contribution policy still requires review before submission.' }

$hasBountySignal = $combinedText -match '(?i)(/bounty\s+\$?\s*[0-9]|\bbounty\b|reward\s*[:=]?\s*\$\s*[0-9])'
$amountCandidates = [System.Collections.Generic.List[decimal]]::new()
foreach ($m in [regex]::Matches($combinedText, '(?i)(?:/bounty\s*)?\$\s*([0-9]+(?:\.[0-9]{1,2})?)')) {
    $value = 0m
    if ([decimal]::TryParse($m.Groups[1].Value, [Globalization.NumberStyles]::Number, [Globalization.CultureInfo]::InvariantCulture, [ref]$value)) {
        $amountCandidates.Add($value) | Out-Null
    }
}
$amountSeen = @($amountCandidates | Sort-Object -Unique)

switch ($ContributionClass) {
    'FUNDED' {
        if ($ExpectedAmount -le 0) { Add-Finding $failures 'FUNDED_AMOUNT_INVALID' 'FUNDED contributions require ExpectedAmount > 0.' }
        if (-not $hasBountySignal) { Add-Finding $warnings 'NO_EXPLICIT_BOUNTY_SIGNAL' 'No bounty signal was detected in the GitHub issue; preserve separate platform funding evidence.' }
        if ($amountSeen.Count -gt 0 -and $ExpectedAmount -notin $amountSeen) { Add-Finding $failures 'AMOUNT_MISMATCH' "Expected $ExpectedAmount; detected in GitHub issue: $($amountSeen -join ', ')." }
        if ($FundingStatus -notin @('PLATFORM_VERIFIED', 'ESCROW_VERIFIED')) { Add-Finding $failures 'FUNDING_NOT_VERIFIED' "FUNDED requires PLATFORM_VERIFIED or ESCROW_VERIFIED; got '$FundingStatus'." }
        if ([string]::IsNullOrWhiteSpace($BountyPlatform) -or $BountyPlatform -eq 'UNKNOWN') { Add-Finding $failures 'BOUNTY_PLATFORM_UNKNOWN' 'Identify the payment/bounty platform for a FUNDED contribution.' }
        if ($PlatformAccountStatus -notin @('REGISTERED', 'VERIFIED')) { Add-Finding $failures 'PLATFORM_ACCOUNT_NOT_READY' "PlatformAccountStatus is '$PlatformAccountStatus'." }
        if ($PayoutStatus -notin @('READY', 'DIRECT_PAYMENT_CONFIRMED')) { Add-Finding $failures 'PAYOUT_NOT_READY' "PayoutStatus is '$PayoutStatus'." }
        if ($PayeeType -notin @('INDIVIDUAL', 'BUSINESS')) { Add-Finding $failures 'PAYEE_TYPE_UNKNOWN' 'Identify the economic payee for a FUNDED contribution.' }
        if ([string]::IsNullOrWhiteSpace($PayeeDisplayName)) { Add-Finding $failures 'PAYEE_NAME_MISSING' 'A non-sensitive payee display/legal name is required for a FUNDED contribution.' }
    }

    'PROMISED_CONTINGENT' {
        if ($ExpectedAmount -le 0) { Add-Finding $failures 'PROMISED_AMOUNT_INVALID' 'PROMISED_CONTINGENT requires ExpectedAmount > 0.' }
        if (-not $hasBountySignal) { Add-Finding $warnings 'NO_EXPLICIT_BOUNTY_SIGNAL' 'No promise/bounty signal was detected in the GitHub issue; preserve the external promise evidence.' }
        if ($amountSeen.Count -gt 0 -and $ExpectedAmount -notin $amountSeen) { Add-Finding $warnings 'AMOUNT_MISMATCH_REVIEW' "Expected $ExpectedAmount; GitHub issue shows: $($amountSeen -join ', '). Verify the current promise evidence." }
        if ($FundingStatus -notin @('ADVERTISED', 'PLATFORM_VERIFIED', 'ESCROW_VERIFIED')) { Add-Finding $failures 'PROMISE_NOT_EVIDENCED' "PROMISED_CONTINGENT requires at least ADVERTISED evidence; got '$FundingStatus'." }
        if ($PlatformAccountStatus -notin @('REGISTERED', 'VERIFIED', 'NOT_APPLICABLE')) { Add-Finding $warnings 'PLATFORM_ACCOUNT_NOT_READY' 'A platform account is not yet ready. This does not erase the contribution value, but may affect eventual payment eligibility.' }
        if ($PayoutStatus -notin @('READY', 'DIRECT_PAYMENT_CONFIRMED', 'NOT_APPLICABLE')) { Add-Finding $warnings 'PAYOUT_NOT_READY' 'Payout is not yet ready. Keep realized cash at zero unless/until payment is actually settled.' }
    }

    'PRO_BONO' {
        if ($ExpectedAmount -ne 0) { Add-Finding $failures 'PRO_BONO_AMOUNT_MUST_BE_ZERO' 'PRO_BONO requires ExpectedAmount = 0.' }
        if ($FundingStatus -notin @('NOT_APPLICABLE', 'UNKNOWN')) { Add-Finding $warnings 'PRO_BONO_FUNDING_IGNORED' "FundingStatus '$FundingStatus' is not needed for PRO_BONO; realized cash remains zero." }
        if ($PlatformAccountStatus -notin @('NOT_APPLICABLE', 'UNKNOWN', 'REGISTERED', 'VERIFIED')) { Add-Finding $warnings 'PLATFORM_ACCOUNT_IRRELEVANT' 'Platform account state does not block a pro-bono GitHub contribution.' }
        if ($PayoutStatus -notin @('NOT_APPLICABLE', 'UNKNOWN', 'READY', 'DIRECT_PAYMENT_CONFIRMED')) { Add-Finding $warnings 'PAYOUT_IRRELEVANT' 'Payout state does not block a pro-bono GitHub contribution.' }
    }
}

if ([string]::IsNullOrWhiteSpace($PlatformAccountReference) -and $ContributionClass -eq 'FUNDED') { Add-Finding $warnings 'PLATFORM_ACCOUNT_REFERENCE_MISSING' 'No non-sensitive platform account/profile reference was supplied.' }

$ready = $failures.Count -eq 0
$verdict = if ($ready) { 'READY_FOR_ENTITY_PREPARED' } else { 'REJECT_OR_HOLD' }
$contingentValue = if ($ContributionClass -eq 'PROMISED_CONTINGENT') { $ExpectedAmount } else { 0m }

$result = [ordered]@{
    preflight_version = 3
    evaluated_at_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffZ')
    verdict = $verdict
    ready_for_entity_prepared = $ready
    contribution_class = $ContributionClass
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
    economic_classification = [ordered]@{
        class = $ContributionClass
        advertised_or_expected_amount = $ExpectedAmount
        contingent_value_at_preflight = $contingentValue
        realized_cash_at_preflight = 0
        settled_revenue_claimed = $false
    }
    claimant_and_payment_gate = [ordered]@{
        github_contributor_login = $ContributorGitHubLogin
        platform_account_status = $PlatformAccountStatus
        platform_account_reference = $PlatformAccountReference
        payout_status = $PayoutStatus
        payee_type = $PayeeType
        payee_display_name = $PayeeDisplayName
        sensitive_financial_or_kyc_data_recorded = $false
        payment_gate_required_for_this_class = ($ContributionClass -eq 'FUNDED')
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
        preflight_does_not_claim_acceptance = $true
        preflight_does_not_claim_payment = $true
        preflight_does_not_create_entity_rights = $true
        preflight_does_not_store_bank_or_kyc_secrets = $true
        promised_value_is_not_settled_revenue = $true
        pro_bono_realized_cash_is_zero = $true
    }
}

$json = $result | ConvertTo-Json -Depth 10
if ($OutFile) {
    $parent = Split-Path -Parent $OutFile
    if ($parent -and -not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    Set-Content -LiteralPath $OutFile -Value $json -Encoding UTF8
}

Write-Host "Contribution candidate verdict: $verdict" -ForegroundColor $(if ($ready) { 'Green' } else { 'Yellow' })
Write-Host "Class: $ContributionClass"
Write-Host "Repository: $Repository"
Write-Host "Issue: #$IssueNumber - $titleText"
Write-Host "Issue state: $($issue.state)"
Write-Host "Contributor: @$ContributorGitHubLogin"
Write-Host "License: $(if ($license.present) { $license.spdx_id } else { 'NOT DETECTED' })"
Write-Host "CLA: $ClaStatus"
Write-Host "Expected/advertised amount: $ExpectedAmount $($Currency.ToUpperInvariant())"
Write-Host "Funding: $FundingStatus"
Write-Host "Realized cash at preflight: 0"
Write-Host "Failures: $($failures.Count) | Warnings: $($warnings.Count)"
foreach ($f in $failures) { Write-Host "FAIL [$($f.code)] $($f.message)" -ForegroundColor Red }
foreach ($w in $warnings) { Write-Host "WARN [$($w.code)] $($w.message)" -ForegroundColor Yellow }
if ($OutFile) { Write-Host "JSON: $OutFile" }

if (-not $ready) { throw 'Contribution candidate failed preflight. Do not create an ENTITY PREPARED record for this candidate.' }
Write-Host 'PASS: candidate may proceed to an ENTITY PREPARED record, subject to the recorded warnings.' -ForegroundColor Green
