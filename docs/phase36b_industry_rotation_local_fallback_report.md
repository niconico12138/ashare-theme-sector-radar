# Phase 36B 验收报告：industry_rotation 本地化 fallback

## 1. 改造目标

让 ai-hedge-fund 的 industry_rotation Agent 在 FINANCIAL_DATASETS_API_KEY 不可用时，仍然能基于 theme-sector-radar 的板块上下文和股票所属板块给出有效信号。

## 2. 修改文件清单

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `ai-hedge-fund/src/agents/industry_rotation.py` | 修改 | 新增 `_board_context_fallback` 函数，修改 `_analyze_single_ticker` 使用 board_context fallback |
| `ai-hedge-fund/scripts/run_stock_agent_bridge.py` | 修改 | 修改 `_build_state_for_stock` 函数，添加 board_types, source_pool, trend_score, burst_score 参数 |

## 3. 本地 fallback 规则

### 触发条件
1. 外部 API (FINANCIAL_DATASETS_API_KEY) 不可用
2. LLM 返回置信度 < 10
3. 价格数据获取失败

### 评分逻辑

1. **板块趋势强度**:
   - trend_score >= 70 或 composite_score >= 70: signal=buy, confidence=0.35
   - trend_score 60-70: signal=buy, confidence=0.28
   - trend_score 50-60: confidence=0.22
   - trend_score < 50: confidence=0.15

2. **短线热度**:
   - burst_score >= 70 且 source_pool == "burst": confidence += 0.08
   - burst_score >= 60: confidence += 0.03

3. **排名加成**:
   - rank <= 3: confidence += 0.05
   - rank <= 10: confidence += 0.02

4. **Agent 标签加成**:
   - strong_consensus / trend_confirmed: confidence += 0.04
   - defensive_watch / oversold_rebound_candidate: confidence -= 0.05

5. **股票来源池加成**:
   - source_pool == "trend": confidence += 0.02
   - source_pool == "both": confidence += 0.03

### 输出格式

```json
{
  "signal": "buy",
  "confidence": 45.0,
  "reasoning": "[board_context_fallback] 本地板块轮动分析：股票属于concept板块「光刻胶」，排名 #2，趋势分 74.2，短线分 58.8，综合分 74.4，source_pool=trend，板块标签=strong_consensus。板块趋势强 板块排名靠前 板块标签积极 股票来自趋势池",
  "data_sources": ["theme_sector_radar_board_context", "local_fallback"]
}
```

## 4. 测试结果

### 直接测试

```
=== Test 1: Strong concept match ===
Signal: buy
Confidence: 45.0
Reasoning: [board_context_fallback] 本地板块轮动分析：股票属于concept板块「光刻胶」，排名 #2，趋势分 74.2，短线分 58.8，综合分 74.4，source_pool=trend，板块标签=strong_consensus。板块趋势强 板块排名靠前 板块标签积极 股票来自趋势池

=== Test 2: No match ===
Result: None

=== Test 3: Burst pool match ===
Signal: buy
Confidence: 44.0
Reasoning: [board_context_fallback] 本地板块轮动分析：股票属于concept板块「光刻胶」，排名 #2，趋势分 74.2，短线分 58.8，综合分 74.4，source_pool=burst，板块标签=strong_consensus。板块趋势强 板块排名靠前 板块标签积极
```

### 集成测试

```
[industry_rotation] 000062: LLM confidence too low (0.0), trying board_context fallback
[industry_rotation] 000062: board_context fallback returned signal=SignalAction.BUY, confidence=45.0
```

## 5. 2026-07-01 重跑结果

### per_agent_status

| Agent | success | fallback | fail |
|-------|---------|----------|------|
| technical_analyst | 10 | 3 | 0 |
| fundamentals_analyst | 13 | 0 | 0 |
| valuation_analyst | 13 | 0 | 0 |
| sentiment_analyst | 3 | 10 | 0 |
| china_youzi | 13 | 0 | 0 |
| **industry_rotation** | **7** | **6** | **0** |
| news_sentiment_analyst | 13 | 0 | 0 |

### 首只股票 (TCL科技) Agent 分析

```
contributing_agents: 6
top_positive_agents:
  1. industry_rotation: signal=buy, confidence=0.45, weight=0.1957
     reason: [board_context_fallback] 本地板块轮动分析：股票属于concept板块「光刻胶」，排名 #2，趋势分 74.2，短线分 58.8，综合分 74.4，source_pool=trend，板块标签=strong_consensus
  2. china_youzi: signal=buy, confidence=0.29, weight=0.2174
  3. news_sentiment_analyst: signal=buy, confidence=0.15, weight=0.0652
fallback_agents:
  - sentiment_analyst: reason=data_insufficient
```

## 6. industry_rotation Before/After

| 指标 | Before (Phase 36A) | After (Phase 36B) | 变化 |
|------|---------------------|---------------------|------|
| industry_rotation success | 0 | **7** | ✅ +7 |
| industry_rotation fallback | 13 | **6** | ✅ -7 |
| industry_rotation in top_positive | 0 | **7** | ✅ +7 |
| industry_rotation in fallback_agents | 13 | **6** | ✅ -7 |

## 7. 个股 Agent Top10

| # | 代码 | 名称 | 池 | 板块 | 趋势 | 短线 | Agent | 风险 | fallback |
|---|------|------|-----|------|------|------|-------|------|----------|
| 1 | 000100 | TCL科技 | trend | 光刻胶 | 74.2 | 58.8 | 54.5 | 54.5 | sentiment_analyst |
| 2 | 000021 | 深科技 | trend | 光刻胶 | 74.2 | 58.8 | 54.1 | 54.1 | sentiment_analyst |
| 3 | 000536 | 华映科技 | trend | 光刻胶 | 74.2 | 58.8 | 54.0 | 54.0 | sentiment_analyst |
| 4 | 600196 | 复星医药 | burst | 猴痘概念 | 38.5 | 72.3 | 52.9 | 52.9 | sentiment_analyst |
| 5 | 002399 | 海普瑞 | burst | 猴痘概念 | 38.5 | 72.3 | 52.2 | 52.2 | sentiment_analyst |
| 6 | 000153 | 丰原药业 | burst | 创新药 | 40.2 | 69.8 | 52.2 | 52.2 | sentiment_analyst |
| 7 | 000504 | 南华生物 | burst | 创新药 | 40.2 | 69.8 | 50.9 | 50.9 | sentiment_analyst |
| 8 | 603160 | 汇顶科技 | trend | 光刻机 | 66.2 | 45.8 | 50.8 | 50.8 | sentiment_analyst |
| 9 | 000565 | 渝三峡A | both | 氟化工概念 | 70.2 | 69.8 | 50.6 | 50.6 | sentiment_analyst |
| 10 | 000411 | 英特集团 | burst | 创新药 | 40.2 | 69.8 | 50.6 | 50.6 | sentiment_analyst |

## 8. 剩余问题

1. **industry_rotation 仍有 6 个 fallback**: 这是因为部分股票没有匹配的板块（boards 为空或不在 board_context 中）
2. **sentiment_analyst 仍有 10 个 fallback**: 这是外部 API 问题，非 Phase 36B 范围
3. **LLM 不可用**: LLM 返回 confidence=0，触发 board_context fallback

## 9. 下一步建议

1. **扩展 board_context**: 增加更多板块到 concept_top 和 industry_top
2. **优化 fallback 规则**: 根据实际效果调整评分逻辑
3. **修复 sentiment_analyst**: 解决 sentiment_analyst 的 data_insufficient 问题

## 报告路径

- [docs/phase36b_industry_rotation_local_fallback_report.md](docs/phase36b_industry_rotation_local_fallback_report.md)
- [reports/agent_bridge/2026-07-01/aihf_stock_ranking.json](reports/agent_bridge/2026-07-01/aihf_stock_ranking.json)
- [reports/daily_ai_stock_report/2026-07-01/daily_ai_stock_report.json](reports/daily_ai_stock_report/2026-07-01/daily_ai_stock_report.json)
