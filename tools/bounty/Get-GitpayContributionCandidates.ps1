[CmdletBinding()]
param(
    [int]$MaxClaims = 2,
    [int]$MaxResults = 60,
    [switch]$IncludeAssigned,
    [switch]$AsJson
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-OptionalProperty {
    param(
        [Parameter(Mandatory = $false)]$Object,
        [Parameter(Mandatory = $true)][string]$Name,
        $Default = $null
    )

    if ($null -eq $Object) { return $Default }
    $prop = $Object.PSObject.Properties[$Name]
    if ($null -eq $prop) { return $Default }
    return $prop.Value
}

$base = 'https://gitpay.me/tasks/list'
$page = 0
$limit = 100
$all = @()
$total = [int]::MaxValue

Write-Host 'Querying Gitpay public task inventory...' -ForegroundColor Cyan

while ($all.Count -lt $total) {
    $uri = "${base}?status=open&limit=$limit&page=$page&sortBy=value&sortDirection=desc"
    $response = Invoke-RestMethod -Uri $uri -Method Get

    $responseData = Get-OptionalProperty -Object $response -Name 'data'
    $responseTotal = Get-OptionalProperty -Object $response -Name 'totalCount'

    if ($null -ne $responseData) {
        $batch = @($responseData)
        $total = if ($null -ne $responseTotal) { [int]$responseTotal } else { $all.Count + $batch.Count }
    }
    else {
        $batch = @($response)
        $total = $all.Count + $batch.Count
    }

    if ($batch.Count -eq 0) { break }

    $all += $batch
    $page++

    if ($batch.Count -lt $limit -and $null -eq $responseTotal) { break }
}

$priority = @{
    FUNDED              = 1
    PROMISED_CONTINGENT = 2
    PRO_BONO            = 3
}

$candidates = foreach ($task in $all) {
    $orders = @(Get-OptionalProperty -Object $task -Name 'Orders' -Default @())
    $assigns = @(Get-OptionalProperty -Object $task -Name 'Assigns' -Default @())
    $paidOrders = @($orders | Where-Object { (Get-OptionalProperty -Object $_ -Name 'status') -eq 'succeeded' })
    $claims = $assigns.Count

    $rawValue = Get-OptionalProperty -Object $task -Name 'value' -Default 0
    $value = if ($null -eq $rawValue) { 0.0 } else { [double]$rawValue }

    $class = if ($paidOrders.Count -gt 0) {
        'FUNDED'
    }
    elseif ($value -gt 0) {
        'PROMISED_CONTINGENT'
    }
    else {
        'PRO_BONO'
    }

    $amounts = @($paidOrders | ForEach-Object {
        $a = Get-OptionalProperty -Object $_ -Name 'amount' -Default 0
        if ($null -eq $a) { 0 } else { [double]$a }
    })
    $fundedRaw = if ($amounts.Count -gt 0) { ($amounts | Measure-Object -Sum).Sum } else { 0 }

    $project = Get-OptionalProperty -Object $task -Name 'Project'
    $repo = Get-OptionalProperty -Object $project -Name 'repo'
    $assigned = Get-OptionalProperty -Object $task -Name 'assigned'
    $issueUrl = [string](Get-OptionalProperty -Object $task -Name 'url' -Default '')
    $issueNumber = $null

    # Some Gitpay rows omit Project. Derive canonical GitHub repo/issue metadata from the issue URL.
    if ($issueUrl -match '^https://github\.com/([^/]+)/([^/]+)/(?:issues|pull)/(\d+)(?:$|[/?#])') {
        if ([string]::IsNullOrWhiteSpace([string]$repo)) {
            $repo = "$($Matches[1])/$($Matches[2])"
        }
        $issueNumber = [int]$Matches[3]
    }

    [pscustomobject]@{
        Class           = $class
        Priority        = $priority[$class]
        Id              = Get-OptionalProperty -Object $task -Name 'id'
        Bounty          = $value
        FundedRaw       = [double]$fundedRaw
        Currency        = (($paidOrders | ForEach-Object { Get-OptionalProperty -Object $_ -Name 'currency' } | Where-Object { $_ } | Sort-Object -Unique) -join ',')
        Claims          = $claims
        ClaimStates     = (($assigns | ForEach-Object { Get-OptionalProperty -Object $_ -Name 'status' } | Where-Object { $_ }) -join ',')
        Assigned        = $assigned
        Repo            = $repo
        IssueNumber     = $issueNumber
        Title           = Get-OptionalProperty -Object $task -Name 'title'
        Issue           = $issueUrl
        Created         = Get-OptionalProperty -Object $task -Name 'createdAt'
        Updated         = Get-OptionalProperty -Object $task -Name 'updatedAt'
        SucceededOrders = $paidOrders.Count
    }
}

$filtered = @($candidates | Where-Object {
    $_.Claims -le $MaxClaims -and ($IncludeAssigned -or -not $_.Assigned)
} | Sort-Object `
    @{ Expression = { $_.Priority }; Ascending = $true }, `
    @{ Expression = { $_.Claims }; Ascending = $true }, `
    @{ Expression = { $_.FundedRaw }; Descending = $true }, `
    @{ Expression = { $_.Bounty }; Descending = $true }, `
    @{ Expression = { $_.Updated }; Descending = $true } | Select-Object -First $MaxResults)

Write-Host "Open tasks scanned: $($all.Count)" -ForegroundColor DarkGray
Write-Host "Candidates after claim/assignment filter: $($filtered.Count)" -ForegroundColor DarkGray
Write-Host ''
Write-Host 'Classification:' -ForegroundColor Cyan
Write-Host '  FUNDED              = succeeded payment order exists' -ForegroundColor DarkGray
Write-Host '  PROMISED_CONTINGENT = advertised task value, no verified succeeded payment order' -ForegroundColor DarkGray
Write-Host '  PRO_BONO            = zero-dollar contribution opportunity' -ForegroundColor DarkGray
Write-Host ''

if ($AsJson) {
    $filtered | ConvertTo-Json -Depth 8
}
else {
    $filtered | Select-Object Class,Bounty,FundedRaw,Claims,Repo,IssueNumber,Title,Issue | Format-Table -AutoSize
}
