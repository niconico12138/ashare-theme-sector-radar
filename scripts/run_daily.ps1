# run_daily.ps1
# Daily report runner script
# Reads config file and calls CLI to generate daily report

param(
    [string]$ConfigPath = "config/daily.local.json",
    [string]$FallbackConfigPath = "config/daily.example.json"
)

# Get project root directory
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot

try {
    # Read config file using python to avoid encoding issues
    $ConfigFile = $ConfigPath
    if (-not (Test-Path $ConfigFile)) {
        $ConfigFile = $FallbackConfigPath
        Write-Host "Using fallback config: $ConfigFile" -ForegroundColor Yellow
    }

    if (-not (Test-Path $ConfigFile)) {
        Write-Host "ERROR: Config file not found" -ForegroundColor Red
        exit 1
    }

    # Parse config using python
    $ConfigScript = @"
import json
with open(r'$ConfigFile', encoding='utf-8') as f:
    config = json.load(f)
print(json.dumps(config))
"@
    $ConfigJson = python -c $ConfigScript
    $Config = $ConfigJson | ConvertFrom-Json

    # Get current date
    $AsOfDate = if ($Config.as_of -eq "auto") {
        Get-Date -Format "yyyy-MM-dd"
    } else {
        $Config.as_of
    }

    # Build command arguments
    $CliArgs = @(
        "-m", "theme_sector_radar.cli",
        "--daily",
        "--as-of", $AsOfDate,
        "--provider", $Config.provider,
        "--top-n", $Config.top_n,
        "--lookback-days", $Config.lookback_days,
        "--fallback-cache-days", $Config.fallback_cache_days,
        "--report-root", $Config.report_root
    )

    if ($Config.refresh) {
        $CliArgs += "--refresh"
    }

    if ($Config.offline_fixture) {
        $CliArgs += "--offline-fixture"
        if ($Config.fixture_profile) {
            $CliArgs += "--fixture-profile"
            $CliArgs += $Config.fixture_profile
        }
    }

    # Record start time
    $StartTime = Get-Date
    $StartTimeStr = $StartTime.ToString("yyyy-MM-dd HH:mm:ss")

    Write-Host "============================================================"
    Write-Host "Theme Sector Radar - Daily Report" -ForegroundColor Cyan
    Write-Host "============================================================"
    Write-Host "Date: $AsOfDate"
    Write-Host "Provider: $($Config.provider)"
    Write-Host "Config: $ConfigFile"
    Write-Host "Start Time: $StartTimeStr"
    Write-Host "------------------------------------------------------------"

    # Run CLI
    $Process = Start-Process -FilePath "python" -ArgumentList $CliArgs -NoNewWindow -Wait -PassThru

    # Record end time
    $EndTime = Get-Date
    $EndTimeStr = $EndTime.ToString("yyyy-MM-dd HH:mm:ss")
    $Duration = ($EndTime - $StartTime).TotalSeconds

    # Get report paths
    $ReportDir = Join-Path $Config.report_root $AsOfDate
    $ReportPath = Join-Path $ReportDir "theme_sector_radar.json"
    $RunLogPath = Join-Path $ReportDir "run_log.json"
    $IndexPath = Join-Path $Config.report_root "index.json"

    # Generate script log directory
    $LogDir = Join-Path $Config.log_root $AsOfDate
    if (-not (Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }
    $LogFilePath = Join-Path $LogDir "$AsOfDate-run.log"

    # Read run_log using python to avoid encoding issues
    $Status = "unknown"
    if (Test-Path $RunLogPath) {
        $Status = python -c "import json; print(json.load(open(r'$RunLogPath', encoding='utf-8')).get('status', 'unknown'))"
        $Status = $Status.Trim()
    }

    # Build log content
    $LogContent = @"
Theme Sector Daily Run Log
==========================
Date: $AsOfDate
Start Time: $StartTimeStr
End Time: $EndTimeStr
Duration: $($Duration.ToString("F1")) seconds
Provider: $($Config.provider)
Config: $ConfigFile
Status: $Status
Exit Code: $($Process.ExitCode)

Report Path: $ReportPath
Run Log: $RunLogPath
Index: $IndexPath
"@

    # Save log
    $LogContent | Out-File -FilePath $LogFilePath -Encoding ASCII

    # Output summary
    Write-Host "------------------------------------------------------------"
    Write-Host "Execution Summary" -ForegroundColor Cyan
    Write-Host "------------------------------------------------------------"

    if ($Status -eq "ok") {
        Write-Host "Status: $Status" -ForegroundColor Green
    } elseif ($Status -eq "degraded") {
        Write-Host "Status: $Status" -ForegroundColor Yellow
    } else {
        Write-Host "Status: $Status" -ForegroundColor Red
    }

    Write-Host "Report Path: $ReportPath"
    Write-Host "Index: $IndexPath"
    Write-Host "Run Log: $RunLogPath"
    Write-Host "Script Log: $LogFilePath"
    Write-Host "Duration: $($Duration.ToString("F1")) seconds"

    # Check if failed
    if ($Process.ExitCode -ne 0) {
        Write-Host ""
        Write-Host "ERROR: Execution failed with exit code $($Process.ExitCode)" -ForegroundColor Red
        Write-Host "Please check run_log: $RunLogPath" -ForegroundColor Yellow
        exit $Process.ExitCode
    }

    Write-Host ""
    Write-Host "Execution completed!" -ForegroundColor Green

} finally {
    Pop-Location
}
