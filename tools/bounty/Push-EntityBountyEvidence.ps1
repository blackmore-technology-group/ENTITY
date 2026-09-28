[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RecordDirectory,
    [Parameter(Mandatory = $true)][string]$CommitMessage,
    [string]$Remote = "origin",
    [switch]$NoPush
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Args)
    $output = & git @Args 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Args -join ' ') failed:`n$($output -join [Environment]::NewLine)"
    }
    return @($output)
}

$repoRoot = (Invoke-Git @("rev-parse", "--show-toplevel") | Select-Object -First 1).Trim()
if (-not $repoRoot) { throw "Run this script from inside the ENTITY repository." }
$repoRoot = (Resolve-Path $repoRoot).Path
Set-Location $repoRoot

$resolvedRecord = (Resolve-Path -LiteralPath $RecordDirectory).Path
$evidenceRoot = (Join-Path $repoRoot "evidence\bounty")
if (-not (Test-Path -LiteralPath $evidenceRoot)) {
    throw "Expected evidence root does not exist: $evidenceRoot"
}
$resolvedEvidenceRoot = (Resolve-Path -LiteralPath $evidenceRoot).Path.TrimEnd('\','/')

if (-not $resolvedRecord.StartsWith($resolvedEvidenceRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to stage path outside evidence/bounty: $resolvedRecord"
}

$required = @("bounty_record.json", "evidence_hashes.json", "INDEX.json")
foreach ($name in $required) {
    if (-not (Test-Path -LiteralPath (Join-Path $resolvedRecord $name) -PathType Leaf)) {
        throw "Missing required evidence file: $name"
    }
}

$branch = (Invoke-Git @("rev-parse", "--abbrev-ref", "HEAD") | Select-Object -First 1).Trim()
if ($branch -eq "HEAD") { throw "Detached HEAD is not allowed for evidence push." }

# Refuse to proceed when something unrelated is already staged.
$alreadyStaged = @(Invoke-Git @("diff", "--cached", "--name-only")) | Where-Object { $_ -and $_.Trim() }
if ($alreadyStaged.Count -gt 0) {
    throw "Index is not clean. Commit/unstage existing staged files before running this script: $($alreadyStaged -join ', ')"
}

$recordRelative = [IO.Path]::GetRelativePath($repoRoot, $resolvedRecord) -replace '\\','/'
if (-not $recordRelative.StartsWith("evidence/bounty/", [StringComparison]::OrdinalIgnoreCase)) {
    throw "Internal scope check failed for record path: $recordRelative"
}

Invoke-Git @("add", "--", $recordRelative) | Out-Null

$staged = @(Invoke-Git @("diff", "--cached", "--name-only")) | Where-Object { $_ -and $_.Trim() }
if ($staged.Count -eq 0) {
    throw "No evidence changes were staged."
}

$forbidden = @($staged | Where-Object { -not $_.StartsWith("evidence/bounty/", [StringComparison]::OrdinalIgnoreCase) })
if ($forbidden.Count -gt 0) {
    & git reset --quiet
    throw "Guardrail stopped commit because non-evidence paths were staged: $($forbidden -join ', ')"
}

# Explicitly protect ENTITY implementation/protocol areas even if a future path check changes.
$protectedPrefixes = @("protocol/", "src/", "sdk/", "profiles/", "tests/")
$protected = foreach ($path in $staged) {
    foreach ($prefix in $protectedPrefixes) {
        if ($path.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) { $path }
    }
}
if (@($protected).Count -gt 0) {
    & git reset --quiet
    throw "Protected ENTITY paths cannot be part of a bounty evidence commit: $(@($protected) -join ', ')"
}

Invoke-Git @("commit", "-m", $CommitMessage) | Out-Host
$commit = (Invoke-Git @("rev-parse", "HEAD") | Select-Object -First 1).Trim()

if (-not $NoPush) {
    Invoke-Git @("push", "-u", $Remote, $branch) | Out-Host
}

Write-Host "Bounty evidence commit created: $commit" -ForegroundColor Green
Write-Host "Branch: $branch"
Write-Host "Files:"
$staged | ForEach-Object { Write-Host "  $_" }
if ($NoPush) {
    Write-Host "Push skipped because -NoPush was specified."
} else {
    Write-Host "Evidence pushed to $Remote/$branch."
}
Write-Host "No protocol/source/schema paths were staged by this operation."
