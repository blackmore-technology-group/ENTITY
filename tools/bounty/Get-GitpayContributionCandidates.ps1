[CmdletBinding()]
param(
    [int]$MaxClaims = 2,
    [int]$MaxResults = 60,
    [switch]$IncludeAssigned,
    [switch]$AsJson
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$base = 'https://gitpay.me/tasks/list'
$page = 0
$limit = 100
$all = @()
$total = [int]::MaxValue

Write-Host 'Querying Gitpay public task inventory...' -ForegroundColor Cyan

while ($all.Count -lt $total) {
    $uri = "${base}?status=open&limit=$limit&page=$page&sortBy=value&sortDirection=desc"
    $response = Invoke-RestMethod -Uri $uri -Method Get

    if ($null -ne $response.data) {
        $batch = @($response.data)
        $total = if ($null -ne $response.totalCount) { [int]$response.totalCount } else { $all.Count + $batch.Count }
    }
    else {
        $batch = @($response)
        $total = $all.Count + $batch.Count
    }

    if ($batch.Count -eq 0) { break }

    $all += $batch
    $page++

    if ($batch.Count -lt $limit -and $null -eq $response.totalCount) { break }
}

$priority = @{
    FUNDED               = 1
    PROMISED_CONTINGENT  = 2
    PRO_BONO             = 3
}

$candidates = foreach ($task in $all) {
    $orders = @($task.Orders)
    $assigns = @($task.Assigns)
    $paidOrders = @($orders | Where-Object { $_.status -eq 'succeeded' })
    $claims = $assigns.Count
    $value = if ($null -eq $task.value) { 0.0 } else { [double]$task.value }

    $class = if ($paidOrders.Count -gt 0) {
        'FUNDED'
    }
    elseif ($value -gt 0) {
        'PROMISED_CONTINGENT'
    }
    else {
        'PRO_BONO'
    }

    $fundedRaw = ($paidOrders | Measure-Object -Property amount -Sum).Sum
    if ($null -eq $fundedRaw) { $fundedRaw = 0 }

    $repo = $null
    if ($null -ne $task.Project) { $repo = $task.Project.repo }

    [pscustomobject]@{
        Class           = $class
        Priority        = $priority[$class]
        Id              = $task.id
        Bounty          = $value
        FundedRaw       = [double]$fundedRaw
        Currency        = (($paidOrders | ForEach-Object { $_.currency } | Where-Object { $_ } | Sort-Object -Unique) -join ',')
        Claims          = $claims
        ClaimStates     = (($assigns | ForEach-Object { $_.status } | Where-Object { $_ }) -join ',')
        Assigned        = $task.assigned
        Repo            = $repo
        Title           = $task.title
        Issue           = $task.url
        Created         = $task.createdAt
        Updated         = $task.updatedAt
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
    $filtered | Select-Object Class,Bounty,FundedRaw,Claims,Repo,Title,Issue | Format-Table -AutoSize
}
