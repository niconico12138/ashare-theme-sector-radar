# Theme Sector Radar - A股行业/概念板块雷达

独立盘后行业/概念板块雷达子系统，服务于 A 股短线板块筛选研究。

## 项目定位

- 独立 CLI 子系统，不接入 LangGraph
- 盘后分析，不支持盘中实时判断
- 规则评分为主，不依赖 LLM
- 只输出板块强弱筛选，不输出个股推荐或买卖建议

## 明确边界

**本项目：**
- ✅ 输出板块强弱筛选
- ✅ 输出行业/概念 Top N
- ✅ 输出板块轮动变化
- ✅ 输出 JSON + Markdown 报告

**本项目不做：**
- ❌ 不输出个股推荐
- ❌ 不输出 buy/sell/hold 建议
- ❌ 不输出买入、卖出、持有建议
- ❌ 不接入自动交易
- ❌ 不做盘中实时交易判断
- ❌ 不修改 ai-hedge-fund 原项目

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行 Fixture Smoke Test

```powershell
# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts/run_daily_fixture.ps1
```

或直接运行 CLI：

```bash
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --offline-fixture --fixture-profile full --lookback-days 5 --report-root reports/theme_sector_radar
```

### 3. 运行真实 AkShare 日报

```powershell
# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts/run_daily.ps1
```

或直接运行 CLI：

```bash
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --provider akshare --refresh --lookback-days 5 --report-root reports/theme_sector_radar
```

### 4. Replay-Cache 回放

```bash
python -m theme_sector_radar.cli --replay-cache --start-date 2026-06-24 --end-date 2026-06-28 --lookback-days 5 --report-root reports/theme_sector_radar
```

## 输出路径

### 报告目录

```text
reports/theme_sector_radar/YYYY-MM-DD/
  ├── theme_sector_radar.json    # JSON 报告
  ├── theme_sector_radar.md      # Markdown 报告
  ├── raw_snapshot.json          # 原始快照
  └── run_log.json               # 运行日志
```

### 索引文件

```text
reports/theme_sector_radar/
  ├── index.json                 # 索引 JSON
  └── index.md                   # 索引 Markdown
```

### 日志目录

```text
logs/daily_runs/
  └── YYYY-MM-DD-run.log         # 脚本日志
```

## 常用命令

```bash
# Fixture Smoke Test
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --offline-fixture --fixture-profile full --lookback-days 5 --report-root reports/theme_sector_radar

# 真实 AkShare Daily
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --provider akshare --refresh --lookback-days 5 --report-root reports/theme_sector_radar

# Replay-Cache
python -m theme_sector_radar.cli --replay-cache --start-date 2026-06-24 --end-date 2026-06-28 --lookback-days 5 --report-root reports/theme_sector_radar

# 运行测试
python -m pytest tests/theme_sector_radar/ -v
```

## 文档入口

- [每日工作流](docs/runbooks/daily_workflow.md)
- [Windows 任务计划配置](docs/runbooks/windows_task_scheduler.md)
- [故障排查指南](docs/runbooks/troubleshooting.md)
- [发布前验收清单](docs/release_checklist.md)

## 当前状态

- **版本**: 0.1.0
- **阶段**: Phase 7.5 发布前验收
- **测试**: 219 passed
- **状态**: 独立 CLI，不接入 ai-hedge-fund LangGraph

## 许可证

本项目仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。
