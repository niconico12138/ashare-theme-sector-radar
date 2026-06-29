# 每日盘后工作流

## 1. 手动运行真实 AkShare 日报

### 1.1 使用 PowerShell 脚本
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_daily.ps1
```

### 1.2 直接运行 CLI
```bash
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --provider akshare --refresh --lookback-days 5 --report-root reports/theme_sector_radar
```

### 1.3 配置文件
- 默认读取: `config/daily.local.json`
- 备选: `config/daily.example.json`
- 复制示例配置: `Copy-Item config\daily.example.json config\daily.local.json`

## 2. 手动运行 Fixture Smoke Test

### 2.1 使用 PowerShell 脚本
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_daily_fixture.ps1
```

### 2.2 直接运行 CLI
```bash
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --offline-fixture --fixture-profile rotation-day2 --lookback-days 5 --report-root reports/theme_sector_radar
```

## 3. 查看报告

### 3.1 报告目录
```
reports/theme_sector_radar/YYYY-MM-DD/
  ├── theme_sector_radar.json
  ├── theme_sector_radar.md
  ├── raw_snapshot.json
  └── run_log.json
```

### 3.2 打开 Markdown 报告
```powershell
Start-Process "reports\theme_sector_radar\2026-06-28\theme_sector_radar.md"
```

## 4. 查看索引

### 4.1 索引文件
```
reports/theme_sector_radar/
  ├── index.json
  └── index.md
```

### 4.2 打开索引
```powershell
Start-Process "reports\theme_sector_radar\index.md"
```

## 5. 查看运行日志

### 5.1 报告内 run_log
```
reports/theme_sector_radar/YYYY-MM-DD/run_log.json
```

### 5.2 脚本日志
```
logs/daily_runs/YYYY-MM-DD-run.log
```

## 6. Replay-Cache 回放

### 6.1 回放指定日期范围
```bash
python -m theme_sector_radar.cli --replay-cache --start-date 2026-06-24 --end-date 2026-06-28 --lookback-days 5 --report-root reports/theme_sector_radar
```

### 6.2 重新生成索引
回放完成后会自动重新生成 index.json 和 index.md。
