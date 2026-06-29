# run_daily_fixture.ps1
# Fixture Smoke Test script
# Uses offline fixture data to validate daily report pipeline

param(
    [string]$AsOfDate = (Get-Date -Format "yyyy-MM-dd"),
    [int]$TopN = 10,
    [string]$ReportRoot = "reports/theme_sector_radar",
    [string]$FixtureProfile = "full"
)

# Set console encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Get project root directory
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot

try {
    # Build command arguments
    $CliArgs = @(
        "-m", "theme_sector_radar.cli",
        "--daily",
        "--as-of", $AsOfDate,
        "--offline-fixture",
        "--fixture-profile", $FixtureProfile,
        "--top-n", $TopN,
        "--lookback-days", 5,
        "--report-root", $ReportRoot
    )

    # Record start time
    $StartTime = Get-Date
    $StartTimeStr = $StartTime.ToString("yyyy-MM-dd HH:mm:ss")

    Write-Host "============================================================"
    Write-Host "Theme Sector Radar - Fixture Smoke Test" -ForegroundColor Cyan
    Write-Host "============================================================"
    Write-Host "Date: $AsOfDate"
    Write-Host "Fixture Profile: $FixtureProfile"
    Write-Host "Start Time: $StartTimeStr"
    Write-Host "------------------------------------------------------------"

    # Run CLI
    $Process = Start-Process -FilePath "python" -ArgumentList $CliArgs -NoNewWindow -Wait -PassThru

    # Record end time
    $EndTime = Get-Date
    $EndTimeStr = $EndTime.ToString("yyyy-MM-dd HH:mm:ss")
    $Duration = ($EndTime - $StartTime).TotalSeconds

    # Get report path
    $ReportDir = Join-Path $ReportRoot $AsOfDate
    $ReportPath = Join-Path $ReportDir "theme_sector_radar.json"
    $RunLogPath = Join-Path $ReportDir "run_log.json"

    # Read run_log to get status
    $Status = "unknown"
    if (Test-Path $RunLogPath) {
        $RunLog = Get-Content $RunLogPath | ConvertFrom-Json
        $Status = $RunLog.status
    }

    # Output summary
    Write-Host "------------------------------------------------------------"
    Write-Host "Smoke Test Result" -ForegroundColor Cyan
    Write-Host "------------------------------------------------------------"

    if ($Status -eq "ok") {
        Write-Host "Status: $Status" -ForegroundColor Green
    } elseif ($Status -eq "degraded") {
        Write-Host "Status: $Status" -ForegroundColor Yellow
    } else {
        Write-Host "Status: $Status" -ForegroundColor Red
    }

    Write-Host "Report Path: $ReportPath"
    Write-Host "Duration: $($Duration.ToString("F1")) seconds"

    # Check if failed
    if ($Process.ExitCode -ne 0) {
        Write-Host ""
        Write-Host "ERROR: Smoke Test failed with exit code $($Process.ExitCode)" -ForegroundColor Red
        Write-Host "Please check run_log: $RunLogPath" -ForegroundColor Yellow
        exit $Process.ExitCode
    }

    # Verify report file
    if (Test-Path $ReportPath) {
        try {
            $ReportContent = Get-Content $ReportPath -Raw
            $Report = $ReportContent | ConvertFrom-Json

            Write-Host ""
            Write-Host "Report Verification:" -ForegroundColor Cyan
            Write-Host "  - report_type: $($Report.report_type)"
            Write-Host "  - fixture_profile: $($Report.fixture_profile)"
            Write-Host "  - offline_fixture: $($Report.offline_fixture)"
            Write-Host "  - data_source_mode: $($Report.data_source_mode)"
            Write-Host "  - industry_top count: $($Report.industry_top.Count)"
            Write-Host "  - concept_top count: $($Report.concept_top.Count)"

            # Verify fixture_profile passed correctly
            if ($Report.fixture_profile -eq $FixtureProfile) {
                Write-Host "  - fixture_profile pass: OK" -ForegroundColor Green
            } else {
                Write-Host "  - fixture_profile pass: FAIL (expected $FixtureProfile, got $($Report.fixture_profile))" -ForegroundColor Red
            }
        } catch {
            Write-Host "  - Report verification failed: $_" -ForegroundColor Yellow
        }
    }

    Write-Host ""
    Write-Host "Smoke Test completed!" -ForegroundColor Green

} finally {
    Pop-Location
}
