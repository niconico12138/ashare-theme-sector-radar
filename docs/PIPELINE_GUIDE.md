# 三项目联合选股系统 — 完整使用说明

> **最后验证**: 2026-07-06 实际运行通过
> **项目**: theme-sector-radar-dev + market-data-service + ai-hedge-fund

---

## 系统架构

```
┌─────────────────────────────────────────────────────┐
│           theme-sector-radar-dev（板块雷达）           │
│                                                       │
│  板块评分 → 成分股桥接 → 个股评分 → Agent分析 → 日报  │
└──────────┬──────────────────┬────────────────────────┘
           │ 调用HTTP API     │ 调用subprocess
           ▼                  ▼
┌──────────────────┐  ┌──────────────────────────────┐
│ market_data_     │  │ ai-hedge-fund                │
│ service（数据层） │  │ （Agent分析层）               │
│                  │  │                              │
│ StockDB (K线)    │  │ 7个Agent:                    │
│ AkShare (板块)   │  │  technical/fundamentals/     │
│ EM (成分股)      │  │  valuation/sentiment/        │
└──────────────────┘  │  china_youzi/industry_rotation│
                      │  news_sentiment              │
                      └──────────────────────────────┘
```

## 前置条件

| 组件 | 地址 | 用途 |
|------|------|------|
| **StockDB** | 127.0.0.1:7899 | 个股日K线数据（本地数据库） |
| **market_data_service** | http://127.0.0.1:8000 | 板块成分股/行业总览（HTTP API） |
| **ai-hedge-fund** | 无需常驻 | Agent 个股深度分析（被 radar 通过 subprocess 调用） |

### 启动 StockDB

**位置**: `<path-to-stockdb>\\stockdb.exe`

```bash
# 方式1: 双击启动
# 双击 <path-to-stockdb>\\stockdb.exe

# 方式2: 命令行启动
<path-to-stockdb>\\stockdb.exe
```

- 监听 `127.0.0.1:7899`（配置在 `stockdb.conf`，不要修改）
- **数据更新**: 双击同目录下的 `数据更新.exe`（运行前先退出 stockdb.exe）
- 数据更新可多次运行直到完全同步，之后定期运行即可

### 启动 market_data_service API

```bash
cd <path-to-market_data_service>
python -m market_data_service.api_server --host 127.0.0.1 --port 8000
```

> 依赖 StockDB 运行，确保 stockdb.exe 已启动后再启动 API。

### 启动顺序

```
1. stockdb.exe              ← 先启动（数据源）
2. 数据更新.exe             ← 更新数据（首次或定期）
3. api_server (port 8000)   ← 再启动（依赖 StockDB）
4. radar / pipeline         ← 最后运行
```

### 验证前置服务

```bash
# 检查 StockDB 是否在运行
netstat -ano | findstr :7899

# 检查 API 是否在运行
curl http://127.0.0.1:8000/health

# 查看 API 可用数据源
curl http://127.0.0.1:8000/health | python -m json.tool
```

API health 返回示例：
```json
{
  "stockdb": {"ok": true, "latest_daily_date": "20260702"},
  "akshare_ths": {"ok": true, "industry_count": 90, "concept_count": 374},
  "security_master": {"ok": true, "stock_count": 5527}
}
```

> ⚠️ `eastmoney_em` 可能为 false（被 Clash 代理拦截），这是预期行为，系统会自动降级到同花顺数据。

---

## 每日运行流程（7步）

### Step 1: Daily Radar — 板块筛选基础数据

```bash
cd <path-to-a-share-theme-sector-radar>

python -m theme_sector_radar.cli --daily --as-of 2026-07-04 --provider akshare --refresh --lookback-days 5 --report-root reports/theme_sector_radar
```

**耗时**: ~10秒
**输出**:
- `reports/theme_sector_radar/2026-07-04/theme_sector_radar.json`
- `reports/theme_sector_radar/2026-07-04/theme_sector_radar.md`

### Step 2: Sector Score — 综合评分

```bash
python -m theme_sector_radar.cli --score-sectors --as-of 2026-07-04 --sector-type both --top-n 100 --report-root reports/theme_sector_radar
```

**耗时**: ~5秒
**输出**: `reports/sector_scores/2026-07-04/sector_scores.json`

### Step 3: Multi-Window Consensus — 多窗口趋势共识

```bash
python -m theme_sector_radar.cli --multi-window-consensus --as-of 2026-07-04 --sector-type both --report-root reports/theme_sector_radar
```

**耗时**: ~3秒
**输出**: `reports/sector_consensus/2026-07-04/multi_window_consensus.json`

### Step 4: Sector Research — Agent 综合研判

```bash
python -m theme_sector_radar.cli --research-agents --as-of 2026-07-04 --sector-type both --report-root reports/theme_sector_radar
```

**耗时**: ~5秒
**输出**: `reports/sector_research/2026-07-04/sector_research.json`

### Step 5: Unified Pipeline — 联合选股

```bash
python unified_pipeline.py --as-of 2026-07-04 --mode quick
```

**耗时**: ~30秒
**输出**:
- `reports/unified/2026-07-04/unified_report.json`
- `reports/unified/2026-07-04/unified_report.md`

**模式**:
- `quick` = 快速筛选（默认，~30秒）
- `deep` = 完整分析（含资金流，~2分钟）

### Step 6: Daily AI Stock Report — Agent 个股深度分析

```bash
python scripts/run_daily_ai_stock_report.py --as-of 2026-07-03 --agent-preset core --agent-mode real
```

**耗时**: 3-10分钟（取决于候选股数量和 LLM 响应速度）
**前提**: 需要 Step 1-4 的输出文件在 `reports/full90/` 和 `reports/full_concept/` 目录
**输出**:
- `reports/daily_ai_stock_report/2026-07-03/daily_ai_stock_report.json`
- `reports/daily_ai_stock_report/2026-07-03/daily_ai_stock_report.md`

**Agent Presets**:
| Preset | Agent 数量 | 说明 |
|--------|-----------|------|
| `core` | 7 | 核心Agent（推荐日常使用） |
| `selected` | 7 | = core |
| `selected_plus` | 11 | +growth/northbound/policy/china_sentiment |
| `full` | 22 | 全部Agent（最慢，最全面） |

### Step 7: Bridge Report — 桥接报告（可选）

```bash
python scripts/run_daily_bridge_report.py --as-of 2026-07-03 --agent-preset full
```

**耗时**: 3-10分钟（同样调用 ai-hedge-fund Agent）
**输出**:
- `reports/agent_bridge/2026-07-03/daily_bridge_report.json`
- `reports/agent_bridge/2026-07-03/daily_bridge_report.md`

---

## 一键运行（推荐）

### 方式1: Unified Pipeline（最简单）

```bash
cd <path-to-a-share-theme-sector-radar>
python scripts/run_daily_unified_pipeline.py
```

自动执行: 前置检查 → 板块评分 → 成分股桥接 → 个股评分 → 生成报告

### 方式2: PowerShell 脚本

```powershell
cd <path-to-a-share-theme-sector-radar>
powershell -ExecutionPolicy Bypass -File scripts/run_daily.ps1
```

### 方式3: Windows 定时任务

```powershell
# 创建每日15:30盘后任务（需管理员）
$Action = New-ScheduledTaskAction -Execute "python" `
  -Argument "scripts/run_daily_unified_pipeline.py --fail-on-health-fail" `
  -WorkingDirectory "<path-to-a-share-theme-sector-radar>"

$Trigger = New-ScheduledTaskTrigger -Daily -At "15:30"

Register-ScheduledTask -TaskName "ThemeSectorRadarDaily" `
  -Action $Action -Trigger $Trigger -Description "每日板块雷达联合选股"
```

---

## 项目目录与文件

### theme-sector-radar-dev

| 路径 | 说明 |
|------|------|
| `unified_pipeline.py` | 联合选股主入口 |
| `sector_stock_bridge.py` | 板块→成分股桥接 |
| `scripts/run_daily_ai_stock_report.py` | 每日AI日报（调用ai-hedge-fund） |
| `scripts/run_daily_bridge_report.py` | 桥接报告（合并板块+Agent排名） |
| `scripts/export_top30_candidates.py` | 导出候选池 |
| `reports/theme_sector_radar/DATE/` | 板块雷达日报 |
| `reports/sector_scores/DATE/` | 综合评分 |
| `reports/sector_consensus/DATE/` | 多窗口共识 |
| `reports/sector_research/DATE/` | Agent研判 |
| `reports/unified/DATE/` | 联合选股报告 |
| `reports/daily_ai_stock_report/DATE/` | AI个股日报 |
| `reports/agent_bridge/DATE/` | 桥接报告 |

### market-data-service

| 路径 | 说明 |
|------|------|
| `market_data_service/api_server.py` | HTTP API 服务 |
| `market_data_service/api.py` | API 路由定义 |
| `market_data_service/client.py` | Python 客户端 |
| `market_data_service/providers/` | 数据源（AkShare/EM/StockDB） |

**API 端点**:
| 端点 | 说明 |
|------|------|
| `GET /health` | 轻量健康检查 |
| `GET /health/deep` | 深度健康检查 |
| `GET /boards/industries` | 行业板块列表 |
| `GET /boards/concepts` | 概念板块列表 |
| `GET /boards/{type}/{name}/index` | 板块指数数据 |
| `GET /boards/{type}/{name}/constituents` | 板块成分股 |
| `GET /stocks/{code}/bars` | 个股K线数据 |
| `GET /boards/industry-summary` | 行业总览（涨跌/成交/资金流） |
| `GET /boards/top-industries?limit=N&by=pct_chg` | 行业排行 |

### ai-hedge-fund

| 路径 | 说明 |
|------|------|
| `scripts/run_stock_agent_bridge.py` | Agent桥接脚本（被radar调用） |
| `src/agents/common.py` | Agent公共基础设施（v3） |
| `src/agents/china_youzi.py` | 游资/龙虎榜Agent |
| `src/agents/northbound_flow.py` | 北向资金Agent |
| `src/agents/policy_analyst.py` | 政策面Agent |
| `src/agents/china_sentiment.py` | A股情绪面Agent |
| `src/agents/industry_rotation.py` | 行业轮动Agent |

---

## 故障排除

| 症状 | 可能原因 | 解决方案 |
|------|----------|----------|
| StockDB 不可达 (port 7899) | stockdb.exe 未运行 | 双击 `<path-to-stockdb>\\stockdb.exe` |
| API 不可达 (port 8000) | market_data_service 未启动 | `cd market_data_service && python -m market_data_service.api_server --host 127.0.0.1 --port 8000` |
| API 启动报错 | StockDB 未启动 | 先启动 stockdb.exe，再启动 API |
| 全部 `http_mapping` (WARN) | Eastmoney EM 被代理封锁 | 预期行为，mapping 数据已覆盖 107 板块 |
| `concept_rank` 缺失 | 未运行 full_concept 评分 | 先运行 `--score-sectors` |
| Agent 分析超时 | LLM API 响应慢 | 检查 MiMo API 连通性 |
| akshare 报错 ProxyError | Clash 代理拦截 | 系统自动降级到同花顺 |
| 数据过旧 | 长期未更新 | 运行 `数据更新.exe`（先退出 stockdb.exe） |

### 数据降级说明

系统支持多层 fallback：
1. **sector_history fallback**: 使用历史缓存数据
2. **raw_snapshot fallback**: 使用快照缓存
3. **cache fallback**: 使用最近 N 天缓存

检查 `run_log.json` 中 `cache_fallback_used: true` 确认是否降级。

---

## 注意事项

1. **日期对齐**: `--as-of` 日期必须有对应的数据文件，建议使用最近交易日
2. **东方财富被封**: Clash 代理会拦截 `push2.eastmoney.com`，系统自动降级到同花顺
3. **Agent 分析耗时**: 7个Agent分析约需3-10分钟，取决于LLM响应速度
4. **报告目录**: 只有标准 `YYYY-MM-DD/` 目录是生产报告，带后缀的是实验版本
5. **免责声明**: 所有报告仅供研究观察，不构成投资建议

---

*本文档由 Hermes Agent 基于 2026-07-06 实际运行验证生成*

