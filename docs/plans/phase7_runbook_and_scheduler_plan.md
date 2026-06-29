# Phase 7 一键运行脚本与 Windows 盘后执行工作流计划

日期：2026-06-29  
目标：让用户可以每天盘后用一个脚本稳定运行日报

## 1. 一键运行脚本设计

### 1.1 脚本列表
- `scripts/run_daily.ps1`: 真实 AkShare 日报脚本
- `scripts/run_daily_fixture.ps1`: Fixture smoke test 脚本

### 1.2 脚本行为
- 读取配置文件
- 调用 CLI 命令
- 输出清晰摘要
- 失败时退出非 0

## 2. 配置文件设计

### 2.1 文件结构
```
config/
  daily.example.json  # 示例配置
  daily.local.json    # 本地配置（.gitignore）
```

### 2.2 daily.example.json
```json
{
  "as_of": "auto",
  "provider": "akshare",
  "refresh": true,
  "fallback_cache_days": 7,
  "lookback_days": 5,
  "report_root": "reports/theme_sector_radar",
  "top_n": 10,
  "offline_fixture": false,
  "fixture_profile": null,
  "log_root": "logs/daily_runs"
}
```

## 3. 日志目录设计

### 3.1 目录结构
```
logs/
  daily_runs/
    YYYY-MM-DD-run.log  # PowerShell 脚本日志
```

### 3.2 日志内容
- 执行命令
- 开始/结束时间
- 状态
- 报告路径
- 错误信息

## 4. Windows PowerShell 使用方式

### 4.1 运行真实日报
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_daily.ps1
```

### 4.2 运行 Fixture Smoke Test
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_daily_fixture.ps1
```

## 5. 可选任务计划说明

### 5.1 手动创建任务
用户确认后自行创建 Windows 任务计划

### 5.2 建议配置
- 触发器: 交易日 16:30
- 操作: powershell.exe -ExecutionPolicy Bypass -File scripts/run_daily.ps1
- 起始目录: 项目根目录

## 6. 失败排查流程

### 6.1 检查 run_log
```
reports/theme_sector_radar/YYYY-MM-DD/run_log.json
```

### 6.2 检查脚本日志
```
logs/daily_runs/YYYY-MM-DD-run.log
```

### 6.3 运行 fixture smoke test 验证环境

## 7. 测试与验收命令

```bash
# 默认测试
python -m pytest tests/theme_sector_radar/ -v

# Fixture smoke test
powershell -ExecutionPolicy Bypass -File scripts/run_daily_fixture.ps1

# 真实 daily（如果网络可用）
powershell -ExecutionPolicy Bypass -File scripts/run_daily.ps1
```
