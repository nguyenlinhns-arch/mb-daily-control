$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeDirectory = Join-Path $repositoryRoot "runtime"
$logPath = Join-Path $runtimeDirectory "mb4so-005.log"
$endpoint = "https://script.google.com/macros/s/AKfycbygWuNvfFPiG9rKbW_tXgbo1LKssBhmqfO9JYxQP7BFLz4iamOHiiMnftEdaH6KeRrV/exec?action=daily005"
$workflowApi = "https://api.github.com/repos/nguyenlinhns-arch/mb-daily-control/actions/workflows/daily-report-midnight.yml/dispatches"
$liveWebsite = "https://lemienbac.com/"
$retrySeconds = 60
$websitePollSeconds = 15
$websitePollAttempts = 80

New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null

function Write-RunLog([string]$Message) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
    Add-Content -LiteralPath $logPath -Encoding utf8 -Value "$stamp $Message"
}

function Invoke-PrivatePipeline {
    $attempt = 0
    while ($true) {
        $attempt += 1
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $endpoint -TimeoutSec 330
            $body = [string]$response.Content
            if ($body -match "DAILY_MB_005_OK lock=(\d{4}-\d{2}-\d{2}) target=(\d{4}-\d{2}-\d{2})") {
                Write-RunLog "Private pipeline verified on attempt $attempt."
                return [pscustomobject]@{ LockDate = $Matches[1]; TargetDate = $Matches[2] }
            }
            if ($body -match "DAILY_MB_005_ALREADY_DONE target=(\d{4}-\d{2}-\d{2})") {
                $targetDate = [datetime]::ParseExact($Matches[1], "yyyy-MM-dd", [Globalization.CultureInfo]::InvariantCulture)
                Write-RunLog "Private pipeline was already verified for $($Matches[1])."
                return [pscustomobject]@{
                    LockDate = $targetDate.AddDays(-1).ToString("yyyy-MM-dd")
                    TargetDate = $targetDate.ToString("yyyy-MM-dd")
                }
            }
            Write-RunLog "Private pipeline attempt $attempt did not pass: $($body.Substring(0, [Math]::Min(300, $body.Length)))"
        }
        catch {
            Write-RunLog "Private pipeline attempt $attempt failed: $($_.Exception.Message)"
        }
        Write-RunLog "Conditions are not ready; retrying in $retrySeconds seconds."
        Start-Sleep -Seconds $retrySeconds
    }
}

function Get-GitHubToken {
    $credentialInput = "protocol=https`nhost=github.com`n`n"
    $credentialLines = $credentialInput | git credential fill
    $passwordLine = $credentialLines | Where-Object { $_ -like "password=*" } | Select-Object -First 1
    if (-not $passwordLine) { throw "No configured GitHub credential is available." }
    return $passwordLine.Substring(9)
}

function Test-LiveWebsite([string]$LockDate, [string]$TargetDate) {
    try {
        $cacheBust = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        $websiteCheckUri = "{0}?mb005={1}" -f $liveWebsite, $cacheBust
        $response = Invoke-WebRequest -UseBasicParsing -Uri $websiteCheckUri -TimeoutSec 45
        $html = [string]$response.Content
        $targetVi = ([datetime]::ParseExact($TargetDate, "yyyy-MM-dd", [Globalization.CultureInfo]::InvariantCulture)).ToString("dd/MM/yyyy")
        $lockVi = ([datetime]::ParseExact($LockDate, "yyyy-MM-dd", [Globalization.CultureInfo]::InvariantCulture)).ToString("dd/MM/yyyy")
        $reportNeedle = 'data-report-date="' + $targetVi + '"'
        $lockNeedle = 'data-lock-date="' + $lockVi + '"'
        return $response.StatusCode -eq 200 -and $html.Contains($reportNeedle) -and $html.Contains($lockNeedle)
    }
    catch {
        return $false
    }
}

function Start-PublicWebsiteSync([string]$LockDate, [string]$TargetDate) {
    if (Test-LiveWebsite -LockDate $LockDate -TargetDate $TargetDate) {
        Write-RunLog "Live website is already current for REPORT_DATE=$TargetDate and DATA_LOCK=$LockDate."
        return
    }
    $token = Get-GitHubToken
    $headers = @{
        Authorization = "Bearer $token"
        Accept = "application/vnd.github+json"
        "X-GitHub-Api-Version" = "2022-11-28"
        "User-Agent" = "MB4SO-Daily-0005"
    }
    $payload = @{ ref = "main"; inputs = @{ lock_date = $LockDate } } | ConvertTo-Json -Depth 4
    $dispatchAttempt = 0
    while ($true) {
        $dispatchAttempt += 1
        try {
            Invoke-RestMethod -Method Post -Uri $workflowApi -Headers $headers -ContentType "application/json" -Body $payload -TimeoutSec 60 | Out-Null
            Write-RunLog "GitHub website workflow dispatched for DATA_LOCK=$LockDate."
            for ($poll = 1; $poll -le $websitePollAttempts; $poll += 1) {
                if (Test-LiveWebsite -LockDate $LockDate -TargetDate $TargetDate) {
                    Write-RunLog "Live website verified for REPORT_DATE=$TargetDate and DATA_LOCK=$LockDate."
                    return
                }
                Start-Sleep -Seconds $websitePollSeconds
            }
            Write-RunLog "Live website did not advance after dispatch attempt $dispatchAttempt."
        }
        catch {
            Write-RunLog "Website dispatch attempt $dispatchAttempt failed: $($_.Exception.Message)"
        }
        Write-RunLog "Website sync is incomplete; retrying in $retrySeconds seconds."
        Start-Sleep -Seconds $retrySeconds
    }
}

Set-Location -LiteralPath $repositoryRoot
Write-RunLog "Run started."
$privateResult = Invoke-PrivatePipeline
Start-PublicWebsiteSync -LockDate $privateResult.LockDate -TargetDate $privateResult.TargetDate
Write-RunLog "Run completed successfully."
