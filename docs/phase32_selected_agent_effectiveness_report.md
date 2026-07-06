# Phase 32 Selected Agent 效果评估验收报告

**日期**: 2026-07-05  
**测试结果**: PASS ✅

---

## 1. 运行摘要

| 检查项 | 7/2 | 7/3 |
|--------|-----|-----|
| 生成成功 | ✅ | ✅ |
| preset | selected | selected |
| agent_count | 11 | 11 |
| LLM enabled | true | true |
| StockDB 最新日期 | 20260702 | 20260702 |

## 2. Agent 有效性总表

| Agent | 调用 | 成功 | fallback | 成功率 | 方向 | 有效性 |
|-------|------|------|----------|--------|------|--------|
| china_youzi | 2 | 2 | 0 | 100% | +1.00 | ✅ high_value |
| fundamentals_analyst | 2 | 2 | 0 | 100% | +0.00 | ✅ high_value |
| news_sentiment_analyst | 2 | 2 | 0 | 100% | +1.00 | ✅ high_value |
| sentiment_analyst | 2 | 2 | 0 | 100% | +0.00 | ✅ high_value |
| technical_analyst | 2 | 2 | 0 | 100% | +0.00 | ✅ high_value |
| valuation_analyst | 2 | 2 | 0 | 100% | +0.00 | ✅ high_value |
| china_sentiment | 2 | 0 | 2 | 0% | +0.00 | ⚠️ mostly_fallback |
| growth_analyst | 2 | 0 | 2 | 0% | +0.00 | ⚠️ mostly_fallback |
| industry_rotation | 2 | 0 | 2 | 0% | +0.00 | ⚠️ mostly_fallback |
| northbound_flow | 2 | 0 | 2 | 0% | +0.00 | ⚠️ mostly_fallback |
| policy_analyst | 2 | 0 | 2 | 0% | +0.00 | ⚠️ mostly_fallback |

## 3. 有效性结论

| 标签 | Agent |
|------|-------|
| **high_value** | technical_analyst, fundamentals_analyst, valuation_analyst, sentiment_analyst, china_youzi, news_sentiment_analyst |
| **mostly_fallback** | china_sentiment, growth_analyst, industry_rotation, northbound_flow, policy_analyst |

**6/11 高价值，5/11 大量 fallback。**

## 4. 权重建议

| 调整 | Agent | 建议 |
|------|-------|------|
| 保持 | technical_analyst | 0.18 |
| 保持 | china_youzi | 0.16 |
| 保持 | fundamentals_analyst | 0.12 |
| 保持 | valuation_analyst | 0.10 |
| 保持 | sentiment_analyst | 0.09 |
| 降低 | growth_analyst | 0.02 → 0.00 |
| 降低 | industry_rotation | 0.14 → 0.00 |
| 降低 | northbound_flow | 0.04 → 0.00 |
| 降低 | policy_analyst | 0.06 → 0.00 |
| 降低 | china_sentiment | 0.08 → 0.00 |
| 保持 | news_sentiment_analyst | 0.01 |

**建议**: 当前 selected 组中 5 个 Agent 100% fallback，权重应归零或移除。

## 5. 测试结果

| 项目 | 结果 |
|------|------|
| `pytest tests/theme_sector_radar/ -q` | **992 passed, 3 skipped** |
| evaluation script | ✅ 正常运行 |

## 6. 报告路径

- `reports/agent_bridge/selected_agent_evaluation.json`
- `reports/agent_bridge/selected_agent_evaluation.md`
- `docs/phase32_selected_agent_effectiveness_report.md`
