# run_daily_fixture.ps1
# Fixture Smoke Test script
# Uses offline fixture data to validate daily report pipeline

param(
    [string]$AsOfDate = (Get-Date -Format "yyyy-MM-dd"),
    [int]$TopN = 10,
    [string]$ReportRoot = "reports/theme_sector_radar",
    [string]$FixtureProfile = "full"
)

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

    # Read run_log using python to avoid encoding issues
    $Status = "unknown"
    if (Test-Path $RunLogPath) {
        $Status = python -c "import json; print(json.load(open(r'$RunLogPath', encoding='utf-8')).get('status', 'unknown'))"
        $Status = $Status.Trim()
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

    # Verify report file using python
    if (Test-Path $ReportPath) {
        Write-Host ""
        Write-Host "Report Verification:" -ForegroundColor Cyan

        # Use python to parse JSON safely
        $VerifyScript = @"
import json
try:
    with open(r'$ReportPath', encoding='utf-8') as f:
        data = json.load(f)
    print('report_type: ' + str(data.get('report_type', 'N/A')))
    print('fixture_profile: ' + str(data.get('fixture_profile', 'N/A')))
    print('offline_fixture: ' + str(data.get('offline_fixture', 'N/A')))
    print('data_source_mode: ' + str(data.get('data_source_mode', 'N/A')))
    print('industry_top_count: ' + str(len(data.get('industry_top', []))))
    print('concept_top_count: ' + str(len(data.get('concept_top', []))))
    fixture_profile = data.get('fixture_profile', '')
    expected = '$FixtureProfile'
    if fixture_profile == expected:
        print('fixture_profile_match: OK')
    else:
        print('fixture_profile_match: FAIL (expected ' + expected + ', got ' + str(fixture_profile) + ')')
except Exception as e:
    print('error: ' + str(e))
"@

        $VerifyResult = python -c $VerifyScript
        foreach ($Line in $VerifyResult) {
            Write-Host "  - $Line"
        }
    }

    Write-Host ""
    Write-Host "Smoke Test completed!" -ForegroundColor Green

} finally {
    Pop-Location
}
