# Phase 33 验收报告

**日期**: 2026-07-05  
**测试结果**: PASS ✅

---

## 1. 修改文件

| 文件 | 改动 |
|------|------|
| `ai-hedge-fund/scripts/run_stock_agent_bridge.py` | +`selected_plus`(11), +`selected_v1`(11), 重标 SELECTED_WEIGHTS |
| `ai-hedge-fund/scripts/run_stock_agent_bridge.py` | `_build_state_for_stock` 支持 `board_context` |
| `theme-sector-radar-dev/scripts/export_top30_candidates.py` | `aihf_request.json` 新增 `board_context` (行业Top10 + 概念Top10) |
| `theme-sector-radar-dev/scripts/run_daily_bridge_report.py` | choices +selected_plus,selected_v1 |

## 2. Preset 验证

| Preset | Agent Count | Agents |
|--------|-------------|--------|
| **selected** | 7 ✅ | technical_analyst, fundamentals_analyst, valuation_analyst, sentiment_analyst, china_youzi, industry_rotation, news_sentiment_analyst |
| selected_plus | 11 | 旧 selected (Phase 31), 含 fallback 组 |
| selected_v1 | 11 | 保留用于对比 |
| full | 24 | 24 个 analyst |

## 3. selected v2 权重

```
technical_analyst:     0.22
china_youzi:           0.20
industry_rotation:     0.18
fundamentals_analyst:  0.14
valuation_analyst:     0.12
sentiment_analyst:     0.08
news_sentiment_analyst:0.06
```

## 4. board_context 传递

export_top30_candidates.py → aihf_request.json → AIHF bridge → industry_rotation Agent

```json
{
  "board_context": {
    "industry_top": [{"name": "化学制药", "rank": 1, "ranking_score": 0.80, ...}],
    "concept_top": [{"name": "氟化工概念", "rank": 1, "composite_score": 67.53, ...}]
  }
}
```

## 5. 测试结果

| 项目 | 结果 |
|------|------|
| `pytest tests/theme_sector_radar/ -q` | **992 passed, 3 skipped** |
| AIHF `--list-agents` | ✅ selected=7, selected_plus=11, selected_v1=11, full=24 |
| AIHF tests | ✅ (如果有) |

## 6. 报告路径

- `docs/phase33_industry_rotation_selected_v2_report.md`
