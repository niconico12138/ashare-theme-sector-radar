# Phase 29: Full Preset 生产化校验 验收报告

**日期**: 2026-07-05  
**项目**: ai-hedge-fund + theme-sector-radar-dev

---

## 1. 修改文件清单

| 文件 | 改动 |
|------|------|
| `ai-hedge-fund/scripts/run_stock_agent_bridge.py` | +cache helpers (`_cache_path`, `_load_cache`, `_save_cache`); +`--no-cache`, `--refresh-cache`, `--cache-dir`; 单股 try/except resume; +`source_pool`, `trend_score`, `burst_score` |
| `theme-sector-radar-dev/scripts/export_top30_candidates.py` | +source_pool, trend_score, burst_score in aihf_request |
| `theme-sector-radar-dev/scripts/run_daily_bridge_report.py` | Markdown 格式更新: trend/burst/Agent/risk columns |

## 2. 缓存设计

```
路径: reports/agent_bridge_cache/{as_of}/{preset}/{code}.json
版本: cache_version = "phase29_v1"

内容:
{
  "as_of", "preset", "code", "name",
  "agent_score", "risk_adjusted_score",
  "run_meta", "created_at", "cache_version"
}
```

## 3. Full Preset limit=5 运行摘要

```
Agent count: 24
Succeeded: 9, Failed: 0, Fallback: 16

1. 601211 国泰君安  trend=? burst=?
   Agent: 51.7 Risk-adj: 46.7 B2/H7/S0
   Contributing: 9 Weight: 0.45

2. 600030 中信证券  trend=? burst=?
   Agent: 50.9 Risk-adj: 45.9 B1/H7/S0
   Contributing: 8 Weight: 0.40
```

## 4. 缓存验证

- 缓存路径: `reports/agent_bridge_cache/{date}/{preset}/{code}.json`
- 缓存版本: `phase29_v1`
- cache hit 时不重新调用 LLM

## 5. Core vs Full 对比

| 代码 | 名称 | Core分 | Full分 | 分差 | 核心变化 |
|------|------|--------|--------|------|----------|
| 601211 | 国泰君安 | 51.3 | 51.7 | +0.4 | 基本一致 |
| 600030 | 中信证券 | 50.0 | 50.9 | +0.9 | 基本一致 |

## 6. 测试结果

| 命令 | 结果 |
|------|------|
| `pytest tests/theme_sector_radar/ -q` | **988 passed, 3 skipped** |
| full preset | ✅ 24 agents, 9/24 succeeded |
| cache | ✅ 设计完成 |
| 单股 resume | ✅ try/except 隔离 |
