[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[^/\s]+/[^/\s]+$')][string]$Repository,
    [Parameter(Mandatory = $true)][ValidateRange(1, [int]::MaxValue)][int]$IssueNumber,
    [Parameter(Mandatory = $true)][decimal]$ExpectedAmount,
    [string]$Currency = 'USD',
    [string]$BountyPlatform = 'UNKNOWN',
    [ValidateSet('UNKNOWN', 'ADVERTISED', 'PLATFORM_VERIFIED', 'ESCROW_VERIFIED')]
    [string]$FundingStatus = 'UNKNOWN',
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
        'Accept' = 'application/vnd.github+json'
        'X-GitHub-Api-Version' = '2022-11-28'
        'User-Agent' = 'BTG-ENTITY-Bounty-Preflight'
    }

    if ($env:GITHUB_TOKEN) {
        $headers['Authorization'] = "Bearer $($env:GITHUB_TOKEN)"
    }

    return Invoke-RestMethod -Method Get -Uri $Uri -Headers $headers
}

function Get-LicenseInfo {
    param([Parameter(Mandatory = $true)][string]$RepositoryName)

    try {
        $licenseResponse = Invoke-GitHubPublicGet -Uri "https://api.github.com/repos/$RepositoryName/license"
        return [ordered]@{
            present = $true
            name = [string]$licenseResponse.license.name
            spdx_id = [string]$licenseResponse.license.spdx_id
            path = [string]$licenseResponse.path
            html_url = [string]$licenseResponse.html_url
        }
    }
    catch {
        return [ordered]@{
            present = $false
            name = ''
            spdx_id = ''
            path = ''
            html_url = ''
        }
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
$issueApi = "$repoApi/issues/$IssueNumber"

$repo = Invoke-GitHubPublicGet -Uri $repoApi
$issue = Invoke-GitHubPublicGet -Uri $issueApi
$license = Get-LicenseInfo -RepositoryName $Repository

# GitHub's issues endpoint also returns pull requests. Reject those here.
$isPullRequest = $null -ne $issue.pull_request

$labelNames = @($issue.labels | ForEach-Object { [string]$_.name })
$labelText = ($labelNames -join ' | ')
$bodyText = [string]$issue.body
$titleText = [string]$issue.title
$combinedText = "$titleText`n$bodyText`n$labelText"

$failures = [System.Collections.Generic.List[object]]::new()
$warnings = [System.Collections.Generic.List[object]]::new()

if ([string]$issue.state -ne 'open') {
    Add-Finding -List $failures -Code 'ISSUE_NOT_OPEN' -Message "Issue state is '$($issue.state)', not open."
}
if ($isPullRequest) {
    Add-Finding -List $failures -Code 'ISSUE_IS_PULL_REQUEST' -Message 'The supplied issue number resolves to a pull request.'
}
if ([bool]$repo.archived) {
    Add-Finding -List $failures -Code 'REPOSITORY_ARCHIVED' -Message 'Repository is archived.'
}
if ([bool]$repo.disabled) {
    Add-Finding -List $failures -Code 'REPOSITORY_DISABLED' -Message 'Repository is disabled.'
}
if (-not $license.present) {
    Add-Finding -List $failures -Code 'LICENSE_NOT_DETECTED' -Message 'GitHub did not expose a repository license. Do not use this as the first rights/provenance proof without explicit licensing evidence.'
}
elseif (-not $license.spdx_id -or $license.spdx_id -eq 'NOASSERTION') {
    Add-Finding -List $warnings -Code 'LICENSE_NEEDS_REVIEW' -Message 'A license file exists but SPDX identification is unavailable or ambiguous.'
}

$blockedLabelPattern = '(?i)(rewarded|paid|completed|done|closed|cancelled|canceled|on[ -]?hold|hold|paused)'
$blockedLabels = @($labelNames | Where-Object { $_ -match $blockedLabelPattern })
if ($blockedLabels.Count -gt 0) {
    Add-Finding -List $failures -Code 'BLOCKING_LABEL' -Message "Blocking label(s) detected: $($blockedLabels -join ', ')"
}

if ($combinedText -match '(?i)\b(on hold|bounty paused|bounty cancelled|bounty canceled|already rewarded|already paid)\b') {
    Add-Finding -List $failures -Code 'BLOCKING_TEXT' -Message 'Issue text indicates the bounty may be on hold, cancelled, or already rewarded.'
}

$hasBountySignal = ($combinedText -match '(?i)(/bounty\s+\$?\s*[0-9]|\bbounty\b|reward\s*[:=]?\s*\$\s*[0-9])')
if (-not $hasBountySignal) {
    Add-Finding -List $failures -Code 'NO_EXPLICIT_BOUNTY_SIGNAL' -Message 'No explicit bounty/reward signal was detected in the issue title, body, or labels.'
}

$amountCandidates = [System.Collections.Generic.List[decimal]]::new()
$moneyMatches = [regex]::Matches($combinedText, '(?i)(?:/bounty\s*)?\$\s*([0-9]+(?:\.[0-9]{1,2})?)')
foreach ($match in $moneyMatches) {
    $value = 0m
    if ([decimal]::TryParse($match.Groups[1].Value, [Globalization.NumberStyles]::Number, [Globalization.CultureInfo]::InvariantCulture, [ref]$value)) {
        $amountCandidates.Add($value) | Out-Null
    }
}

$amountSeen = @($amountCandidates | Sort-Object -Unique)
if ($amountSeen.Count -eq 0) {
    Add-Finding -List $warnings -Code 'AMOUNT_NOT_MACHINE_DETECTED' -Message "Expected amount is $ExpectedAmount $Currency, but no dollar amount was machine-detected in issue text/labels. Verify platform evidence manually."
}
elseif ($ExpectedAmount -notin $amountSeen) {
    Add-Finding -List $failures -Code 'AMOUNT_MISMATCH' -Message "Expected amount $ExpectedAmount was not among detected amount(s): $($amountSeen -join ', ')."
}

if ($FundingStatus -notin @('PLATFORM_VERIFIED', 'ESCROW_VERIFIED')) {
    Add-Finding -List $failures -Code 'FUNDING_NOT_VERIFIED' -Message "FundingStatus is '$FundingStatus'. A listing or issue text alone is not enough for the first economic-lineage proof."
}
if ($ClaStatus -eq 'UNKNOWN') {
    Add-Finding -List $warnings -Code 'CLA_NOT_REVIEWED' -Message 'Contributor agreement/CLA status still requires review.'
}
if ($AiContributionPolicy -eq 'UNKNOWN') {
    Add-Finding -List $warnings -Code 'AI_POLICY_NOT_REVIEWED' -Message 'Repository policy for AI-assisted contributions still requires review.'
}
elseif ($AiContributionPolicy -eq 'PROHIBITED') {
    Add-Finding -List $failures -Code 'AI_CONTRIBUTION_PROHIBITED' -Message 'Repository policy prohibits the intended AI-assisted contribution workflow.'
}

# Never accept an issue that asks for private model/session/bootstrap instructions,
# secrets, tokens, or complete runtime initialization context in the contribution.
$sensitiveInstructionPattern = '(?i)(full|complete|entire|verbatim).{0,80}(system prompt|session instructions|initialization context|startup instructions|boot context|pre[- ]?task context|platform instructions|runtime instructions)'
if ($combinedText -match $sensitiveInstructionPattern) {
    Add-Finding -List $failures -Code 'UNSAFE_PRIVATE_CONTEXT_REQUIREMENT' -Message 'Issue appears to require disclosure of private session/system initialization material. Reject this opportunity.'
}

$ready = ($failures.Count -eq 0)
$verdict = if ($ready) { 'READY_FOR_ENTITY_PREPARED' } else { 'REJECT_OR_HOLD' }

$result = [ordered]@{
    preflight_version = 1
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
    }
}

$json = $result | ConvertTo-Json -Depth 10
if ($OutFile) {
    $parent = Split-Path -Parent $OutFile
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    Set-Content -LiteralPath $OutFile -Value $json -Encoding UTF8
}

Write-Host "Bounty candidate verdict: $verdict" -ForegroundColor $(if ($ready) { 'Green' } else { 'Yellow' })
Write-Host "Repository: $Repository"
Write-Host "Issue: #$IssueNumber - $titleText"
Write-Host "Issue state: $($issue.state)"
Write-Host "License: $(if ($license.present) { $license.spdx_id } else { 'NOT DETECTED' })"
Write-Host "Funding: $FundingStatus"
Write-Host "Failures: $($failures.Count) | Warnings: $($warnings.Count)"
foreach ($failure in $failures) { Write-Host "FAIL [$($failure.code)] $($failure.message)" -ForegroundColor Red }
foreach ($warning in $warnings) { Write-Host "WARN [$($warning.code)] $($warning.message)" -ForegroundColor Yellow }

if ($OutFile) { Write-Host "JSON: $OutFile" }

if (-not $ready) { exit 2 }
exit 0
