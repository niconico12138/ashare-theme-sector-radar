# 每日操作指南 (Daily Operator Guide)

**版本**: Phase 51
**最后更新**: 2026-07-01

---

## 1. 每日流程总览

每个交易日盘后，按以下顺序执行：

```
1. Daily Radar          → 板块筛选基础数据
2. Catalyst Events      → 催化事件缓存 (report-only)
3. Sector Score         → 综合评分
4. Multi-Window Consensus → 多窗口趋势共识
5. Sector Research      → Agent 综合研判
6. Research Index       → 多日索引更新
7. Daily Health Check   → 流程完整性验证
```

---

## 2. 详细操作步骤

### Step 1: Daily Radar

**目的**: 获取当日行业/概念板块 Top N 筛选结果

```bash
# 真实 AkShare 日报
python -m theme_sector_radar.cli --daily --as-of YYYY-MM-DD --provider akshare --refresh --lookback-days 5 --report-root reports/theme_sector_radar

# 或使用 PowerShell 脚本
powershell -ExecutionPolicy Bypass -File scripts/run_daily.ps1
```

**输出**:
- `reports/theme_sector_radar/YYYY-MM-DD/theme_sector_radar.json`
- `reports/theme_sector_radar/YYYY-MM-DD/theme_sector_radar.md`
- `reports/theme_sector_radar/YYYY-MM-DD/raw_snapshot.json`
- `reports/theme_sector_radar/YYYY-MM-DD/run_log.json`

**验证**: 检查 `run_log.json` 中 `status: "ok"` 且 `data_source_mode` 不为 `fixture`

### Step 2: Catalyst Events

**目的**: 下载并缓存催化事件数据 (当前 report-only)

```bash
python -m theme_sector_radar.cli --download-catalyst-events --as-of YYYY-MM-DD --report-root reports/theme_sector_radar
```

**输出**: `data_cache/catalyst_events/YYYY-MM-DD/events.json`

**注意**: 当前所有事件均为 fixture，无真实网络事件。健康检查会标记 `catalyst_status`。

### Step 3: Sector Score

**目的**: 计算板块综合评分 (趋势持续分 + 综合选择分)

```bash
python -m theme_sector_radar.cli --score-sectors --as-of YYYY-MM-DD --sector-type both --history-start-date YYYY-MM-DD --history-end-date YYYY-MM-DD --report-root reports/theme_sector_radar
```

**输出**: `reports/sector_scores/YYYY-MM-DD/sector_scores.json` + `.md`

### Step 4: Multi-Window Consensus

**目的**: 5/10/20 日窗口趋势共识分析

```bash
python -m theme_sector_radar.cli --multi-window-consensus --as-of YYYY-MM-DD --sector-type both --report-root reports/theme_sector_radar
```

**输出**: `reports/sector_consensus/YYYY-MM-DD/multi_window_consensus.json`

### Step 5: Sector Research

**目的**: L1-L4 分层 Agent 综合研判

```bash
python -m theme_sector_radar.cli --research-agents --as-of YYYY-MM-DD --sector-type both --report-root reports/theme_sector_radar
```

**输出**:
- `reports/sector_research/YYYY-MM-DD/sector_research.json`
- `reports/sector_research/YYYY-MM-DD/sector_research.md`

### Step 6: Research Index

**目的**: 构建多日 sector_research 索引

```bash
python -m theme_sector_radar.cli --build-research-index --start-date YYYY-MM-DD --end-date YYYY-MM-DD --report-root reports/theme_sector_radar
```

**输出**: `reports/sector_research/index/research_index.json` + `.md`

### Step 7: Daily Health Check

**目的**: 验证每日流程完整性

```bash
python -m theme_sector_radar.cli --daily-health-check --as-of YYYY-MM-DD --report-root reports/theme_sector_radar
```

**输出**:
- `reports/daily_health/YYYY-MM-DD/daily_health_check.json`
- `reports/daily_health/YYYY-MM-DD/daily_health_check.md`

**健康检查项**:
- Radar report 存在且 status=ok
- Sector score 存在
- Multi-window consensus 存在
- Sector research 存在且有 daily_summary
- Research index 存在
- Catalyst cache 存在
- Data source mode 不为 fixture/replay

---

## 3. 数据模式区分

### real (生产模式)
- 命令: `--daily --provider akshare --refresh`
- 数据来源: AkShare/THS 实时接口
- `data_source_mode`: `akshare_refresh` 或 `cache_fallback`
- 健康检查: 应为 `ok`

### fixture (测试模式)
- 命令: `--daily --offline-fixture`
- 数据来源: 本地模拟数据
- `data_source_mode`: `fixture`
- 健康检查: 会标记 `audit_required`

### replay (回放模式)
- 命令: `--replay-cache` 或 `--replay-daily-from-sector-history`
- 数据来源: 缓存/sector_history 历史数据
- `data_source_mode`: `cache_replay` 或 `sector_history_replay`
- 健康检查: 会标记 `audit_required`

**重要**: fixture/replay 数据不可混入 real daily 报告。健康检查会自动检测并标记。

---

## 4. Health Check 路径和解读

### 健康检查结果解读

| overall_status | 含义 | 操作 |
|----------------|------|------|
| `ok` | 流程完整，数据来源正确 | 无需操作 |
| `degraded` | 部分报告缺失或降级 | 检查缺失报告，手动补跑 |
| `failed` | 核心报告缺失 | 必须重新运行完整流程 |
| `audit_required` | 检测到 fixture/replay 混入 | 确认是否为预期行为 |

### 常见警告

| 警告 | 原因 | 处理 |
|------|------|------|
| `检测到 fixture 数据混入 real daily` | data_source_mode=fixture | 使用 `--provider akshare --refresh` |
| `检测到 replay 数据混入 real daily` | data_source_mode=sector_history_replay | 使用 real 模式重新运行 |
| `catalyst cache 缺失` | 未运行 catalyst 下载 | 运行 `--download-catalyst-events` |

---

## 5. 网络失败处理

### AkShare 接口失败

系统自动执行多层 fallback：

1. **sector_history fallback**: 使用 `data_cache/sector_history/` 中的历史数据
2. **raw_snapshot fallback**: 使用 `data_cache/YYYY-MM-DD/raw_snapshot.json` 缓存
3. **cache fallback**: 使用最近 N 天的缓存数据

**fallback 识别**: `run_log.json` 中 `cache_fallback_used: true`，`provider_status.fallback_used: true`

### 手动补救

```bash
# 如果 sector_history 有数据，可从历史回放
python -m theme_sector_radar.cli --replay-daily-from-sector-history --as-of YYYY-MM-DD --start-date YYYY-MM-DD --end-date YYYY-MM-DD

# 如果有缓存，可从缓存回放
python -m theme_sector_radar.cli --replay-cache --start-date YYYY-MM-DD --end-date YYYY-MM-DD
```

---

## 6. 避免 fixture/replay 与 real daily 串台

### 检查清单

1. **run_log.json**: 确认 `data_source_mode` 不为 `fixture` 或 `replay`
2. **provider_status**: 确认 `effective_provider` 为 `akshare`
3. **health check**: 确认 `overall_status` 为 `ok` 而非 `audit_required`
4. **报告目录**: real daily 报告在 `reports/theme_sector_radar/YYYY-MM-DD/`，不含实验后缀

### 目录命名规范

| 目录模式 | 含义 |
|----------|------|
| `2026-06-30/` | 标准 real daily |
| `2026-06-30-v2/` | 实验版本 |
| `2026-06-30-rotation-day1/` | 轮动测试 |
| `2026-06-30-akshare/` | AkShare 测试 |

**原则**: 只有标准 `YYYY-MM-DD/` 目录是生产报告。

---

## 7. 常用命令速查

```bash
# === 生产流程 ===

# 1. Daily Radar (real)
python -m theme_sector_radar.cli --daily --as-of 2026-06-30 --provider akshare --refresh --lookback-days 5 --report-root reports/theme_sector_radar

# 2. Catalyst Events
python -m theme_sector_radar.cli --download-catalyst-events --as-of 2026-06-30 --report-root reports/theme_sector_radar

# 3. Sector Score
python -m theme_sector_radar.cli --score-sectors --as-of 2026-06-30 --sector-type both --report-root reports/theme_sector_radar

# 4. Multi-Window Consensus
python -m theme_sector_radar.cli --multi-window-consensus --as-of 2026-06-30 --sector-type both --report-root reports/theme_sector_radar

# 5. Sector Research
python -m theme_sector_radar.cli --research-agents --as-of 2026-06-30 --sector-type both --report-root reports/theme_sector_radar

# 6. Research Index
python -m theme_sector_radar.cli --build-research-index --start-date 2026-06-24 --end-date 2026-06-30 --report-root reports/theme_sector_radar

# 7. Health Check
python -m theme_sector_radar.cli --daily-health-check --as-of 2026-06-30 --report-root reports/theme_sector_radar

# === 测试流程 ===

# Fixture Smoke Test
python -m theme_sector_radar.cli --daily --as-of 2026-06-30 --offline-fixture --fixture-profile full --lookback-days 5 --report-root reports/theme_sector_radar

# Replay Cache
python -m theme_sector_radar.cli --replay-cache --start-date 2026-06-24 --end-date 2026-06-30 --lookback-days 5 --report-root reports/theme_sector_radar

# === 回测分析 ===

# Agent Layer Backtest
python -m theme_sector_radar.cli --backtest-agent-layers --start-date 2026-06-01 --end-date 2026-06-30 --report-root reports/theme_sector_radar

# Market Regime Analysis
python -m theme_sector_radar.cli --analyze-market-regime --start-date 2026-06-01 --end-date 2026-06-30 --report-root reports/theme_sector_radar

# === 运行测试 ===
python -m pytest tests/theme_sector_radar/ -v
```

---

## 8. 报告查看

```bash
# 打开当日 Markdown 报告
Start-Process "reports\theme_sector_radar\2026-06-30\theme_sector_radar.md"

# 打开索引
Start-Process "reports\theme_sector_radar\index.md"

# 打开健康检查
Start-Process "reports\daily_health\2026-06-30\daily_health_check.md"
```

---

*本指南由 Phase 51 自动生成，仅用于板块研究、观察和复盘，不构成投资建议。*
