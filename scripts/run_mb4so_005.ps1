$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeDirectory = Join-Path $repositoryRoot "runtime"
$logPath = Join-Path $runtimeDirectory "mb4so-005.log"
$endpoint = "https://script.google.com/macros/s/AKfycbygWuNvfFPiG9rKbW_tXgbo1LKssBhmqfO9JYxQP7BFLz4iamOHiiMnftEdaH6KeRrV/exec?action=daily005"
$workflowApi = "https://api.github.com/repos/nguyenlinhns-arch/mb-daily-control/actions/workflows/daily-report-midnight.yml/dispatches"

New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null

function Write-RunLog([string]$Message) {
    $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"
    Add-Content -LiteralPath $logPath -Encoding utf8 -Value "$stamp $Message"
}

function Invoke-PrivatePipeline {
    for ($attempt = 1; $attempt -le 6; $attempt += 1) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $endpoint -TimeoutSec 330
            $body = [string]$response.Content
            if ($body -match "DAILY_MB_005_(OK|ALREADY_DONE)") {
                Write-RunLog "Private pipeline verified on attempt $attempt."
                return
            }
            Write-RunLog "Private pipeline attempt $attempt did not pass: $($body.Substring(0, [Math]::Min(300, $body.Length)))"
        }
        catch {
            Write-RunLog "Private pipeline attempt $attempt failed: $($_.Exception.Message)"
        }
        if ($attempt -lt 6) { Start-Sleep -Seconds 300 }
    }
    throw "Private 00:05 pipeline failed after 6 attempts; website was not advanced."
}

function Get-GitHubToken {
    $credentialInput = "protocol=https`nhost=github.com`n`n"
    $credentialLines = $credentialInput | git credential fill
    $passwordLine = $credentialLines | Where-Object { $_ -like "password=*" } | Select-Object -First 1
    if (-not $passwordLine) { throw "No configured GitHub credential is available." }
    return $passwordLine.Substring(9)
}

function Start-PublicWebsiteSync {
    $token = Get-GitHubToken
    $lockDate = (Get-Date).Date.AddDays(-1).ToString("yyyy-MM-dd")
    $headers = @{
        Authorization = "Bearer $token"
        Accept = "application/vnd.github+json"
        "X-GitHub-Api-Version" = "2022-11-28"
        "User-Agent" = "MB4SO-Daily-0005"
    }
    $payload = @{ ref = "main"; inputs = @{ lock_date = $lockDate } } | ConvertTo-Json -Depth 4
    Invoke-RestMethod -Method Post -Uri $workflowApi -Headers $headers -ContentType "application/json" -Body $payload | Out-Null
    Write-RunLog "GitHub website workflow dispatched for DATA_LOCK=$lockDate."
}

Set-Location -LiteralPath $repositoryRoot
Write-RunLog "Run started."
Invoke-PrivatePipeline
Start-PublicWebsiteSync
Write-RunLog "Run completed successfully."
