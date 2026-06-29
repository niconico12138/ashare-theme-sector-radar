# run_daily.ps1
# 每日盘后日报运行脚本
# 读取配置文件，调用 CLI 生成日报

param(
    [string]$ConfigPath = "config/daily.local.json",
    [string]$FallbackConfigPath = "config/daily.example.json"
)

# 设置控制台编码
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 获取项目根目录
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot

try {
    # 读取配置文件
    $ConfigFile = $ConfigPath
    if (-not (Test-Path $ConfigFile)) {
        $ConfigFile = $FallbackConfigPath
        Write-Host "使用默认配置: $ConfigFile" -ForegroundColor Yellow
    }

    if (-not (Test-Path $ConfigFile)) {
        Write-Host "错误: 找不到配置文件" -ForegroundColor Red
        exit 1
    }

    $Config = Get-Content $ConfigFile | ConvertFrom-Json

    # 获取当前日期
    $AsOfDate = if ($Config.as_of -eq "auto") {
        Get-Date -Format "yyyy-MM-dd"
    } else {
        $Config.as_of
    }

    # 构建命令参数
    $Args = @(
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
        $Args += "--refresh"
    }

    if ($Config.offline_fixture) {
        $Args += "--offline-fixture"
        if ($Config.fixture_profile) {
            $Args += "--fixture-profile"
            $Args += $Config.fixture_profile
        }
    }

    # 记录开始时间
    $StartTime = Get-Date
    $StartTimeStr = $StartTime.ToString("yyyy-MM-dd HH:mm:ss")

    Write-Host "=" * 60
    Write-Host "Theme Sector Radar - 每日日报" -ForegroundColor Cyan
    Write-Host "=" * 60
    Write-Host "日期: $AsOfDate"
    Write-Host "Provider: $($Config.provider)"
    Write-Host "配置文件: $ConfigFile"
    Write-Host "开始时间: $StartTimeStr"
    Write-Host "-" * 60

    # 运行 CLI
    $Process = Start-Process -FilePath "python" -ArgumentList $Args -NoNewWindow -Wait -PassThru

    # 记录结束时间
    $EndTime = Get-Date
    $EndTimeStr = $EndTime.ToString("yyyy-MM-dd HH:mm:ss")
    $Duration = ($EndTime - $StartTime).TotalSeconds

    # 获取报告路径
    $ReportDir = Join-Path $Config.report_root $AsOfDate
    $ReportPath = Join-Path $ReportDir "theme_sector_radar.json"
    $RunLogPath = Join-Path $ReportDir "run_log.json"
    $IndexPath = Join-Path $Config.report_root "index.json"

    # 生成脚本日志
    $LogDir = Join-Path $Config.log_root $AsOfDate
    if (-not (Test-Path $LogDir)) {
        New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    }
    $LogFilePath = Join-Path $LogDir "$AsOfDate-run.log"

    # 读取 run_log 获取状态
    $Status = "unknown"
    if (Test-Path $RunLogPath) {
        $RunLog = Get-Content $RunLogPath | ConvertFrom-Json
        $Status = $RunLog.status
    }

    # 构建日志内容
    $LogContent = @"
Theme Sector Daily Run Log
==========================
日期: $AsOfDate
开始时间: $StartTimeStr
结束时间: $EndTimeStr
耗时: $($Duration.ToString("F1")) 秒
Provider: $($Config.provider)
配置文件: $ConfigFile
状态: $Status
退出码: $($Process.ExitCode)

报告路径: $ReportPath
运行日志: $RunLogPath
索引文件: $IndexPath
"@

    # 保存日志
    $LogContent | Out-File -FilePath $LogFilePath -Encoding UTF8

    # 输出摘要
    Write-Host "-" * 60
    Write-Host "执行摘要" -ForegroundColor Cyan
    Write-Host "-" * 60
    Write-Host "状态: $Status" -ForegroundColor $(if ($Status -eq "ok") { "Green" } elseif ($Status -eq "degraded") { "Yellow" } else { "Red" })
    Write-Host "报告路径: $ReportPath"
    Write-Host "索引文件: $IndexPath"
    Write-Host "运行日志: $RunLogPath"
    Write-Host "脚本日志: $LogFilePath"
    Write-Host "耗时: $($Duration.ToString("F1")) 秒"

    # 检查是否成功
    if ($Process.ExitCode -ne 0) {
        Write-Host ""
        Write-Host "错误: 执行失败，退出码 $($Process.ExitCode)" -ForegroundColor Red
        Write-Host "请查看 run_log: $RunLogPath" -ForegroundColor Yellow
        exit $Process.ExitCode
    }

    Write-Host ""
    Write-Host "执行完成!" -ForegroundColor Green

} finally {
    Pop-Location
}
