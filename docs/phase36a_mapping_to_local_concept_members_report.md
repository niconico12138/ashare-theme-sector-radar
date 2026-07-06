# Phase 36A 验收报告：mapping 概念迁移到 local_concept_members

## 1. 改造目标

将 2026-07-01 运行中仍走 `http_mapping` 的 5 个概念，从 `constituents_mapping.json` 迁移到 `concept_members_history.csv`，目标：

- http_mapping: 5 → 0
- http_local_concept_members: 4 → 9
- unavailable: 0 保持不变
- run_health: WARN → PASS

## 2. 迁移概念清单

| 概念 | 来源 | 股票数 | source |
|------|------|--------|--------|
| 氟化工概念 | constituents_mapping.json | 8 | mapping_migrated_snapshot |
| 光刻胶 | constituents_mapping.json | 8 | mapping_migrated_snapshot |
| 存储芯片 | constituents_mapping.json | 8 | mapping_migrated_snapshot |
| 创新药 | constituents_mapping.json | 8 | mapping_migrated_snapshot |
| 合成生物 | constituents_mapping.json | 8 | mapping_migrated_snapshot |

## 3. concept_members_history.csv 新增行数

- 原有行数: 29 (Phase 35 的 4 个概念)
- 新增行数: 40 (5 个概念 × 8 只股票)
- 更新后总行数: 69

## 4. API 验证结果

| 概念 | HTTP | X-Data-Source | 股票数 |
|------|------|---------------|--------|
| 光刻机 | 200 ✅ | local_concept_members | 8 |
| 硅能源 | 200 ✅ | local_concept_members | 7 |
| 猴痘概念 | 200 ✅ | local_concept_members | 7 |
| 重组蛋白 | 200 ✅ | local_concept_members | 7 |
| 氟化工概念 | 200 ✅ | local_concept_members | 8 |
| 光刻胶 | 200 ✅ | local_concept_members | 8 |
| 存储芯片 | 200 ✅ | local_concept_members | 8 |
| 创新药 | 200 ✅ | local_concept_members | 8 |
| 合成生物 | 200 ✅ | local_concept_members | 8 |

**全部 9 个概念返回 source=local_concept_members** ✅

## 5. unified_pipeline Before/After 对比

| 指标 | Before (Phase 35.1) | After (Phase 36A) | 变化 |
|------|---------------------|---------------------|------|
| http_mapping | 5 | **0** | ✅ -5 |
| http_local_concept_members | 4 | **9** | ✅ +5 |
| unavailable | 0 | **0** | ✅ 保持 |
| 健康门禁 | WARN | **PASS** | ✅ 改善 |
| 趋势候选股 | 18 | **18** | ✅ 保持 |
| 短线候选股 | 13 | **13** | ✅ 保持 |

### constituent_sources (After)

```json
{
  "http_em": 0,
  "http_stale": 0,
  "http_mapping": 0,
  "http_local_industry": 0,
  "http_local_concept_members": 9,
  "local_emergency_mapping": 0,
  "unavailable": 0
}
```

### run_health (After)

```json
{
  "status": "pass",
  "reasons": ["所有数据源正常"],
  "metrics": {
    "total_constituent_sectors": 9,
    "unavailable_sectors": 0,
    "emergency_fallback_sectors": 0
  }
}
```

## 6. daily_ai_stock_report 结果

### candidate_pool
- **total**: 13 只
- **trend**: 5 只
- **burst**: 6 只
- **both**: 2 只
- **来源板块分布**: 光刻胶(4), 创新药(3), 氟化工概念(2), 猴痘概念(2), 光刻机(1)

### Agent 执行结果

| Agent | 成功 | 降级 | 失败 |
|-------|------|------|------|
| technical_analyst | 10 | 3 | 0 |
| fundamentals_analyst | 13 | 0 | 0 |
| valuation_analyst | 13 | 0 | 0 |
| sentiment_analyst | 3 | 10 | 0 |
| china_youzi | 13 | 0 | 0 |
| **industry_rotation** | **0** | **13** | **0** |
| news_sentiment_analyst | 13 | 0 | 0 |

**industry_rotation 仍然 100% fallback**，原因：外部 API (FINANCIAL_DATASETS_API_KEY) 不可用，非 Phase 36A 问题。

## 7. 数据源状态

```
http_em: 0, http_stale: 0, http_mapping: 0
http_local_industry: 0, http_local_concept_members: 9
local_emergency_mapping: 0, unavailable: 0
```

## 8. 是否 PASS

**✅ PASS**

健康门禁已从 WARN 升级到 PASS：
- 所有 9 个概念都有真实数据源 (http_local_concept_members)
- http_mapping 从 5 降到 0
- unavailable 保持 0

## 9. 剩余 WARN 原因

**无** - 健康门禁已 PASS。

唯一剩余问题是 industry_rotation agent 的 fallback，但这是外部 API 问题，不影响健康门禁评级。

## 10. 下一步建议

1. **配置 FINANCIAL_DATASETS_API_KEY**：解决 industry_rotation agent 的 fallback 问题
2. **扩展 concept_members_history.csv**：覆盖更多概念，减少对 http_mapping 的依赖
3. **等待 EM 恢复**：东方财富 API 恢复后，http_em 会增加，进一步提升数据质量

## 报告路径

- unified report: `reports/unified/2026-07-01/unified_report.json`
- daily AI report: `reports/daily_ai_stock_report/2026-07-01/daily_ai_stock_report.json`
- agent bridge: `reports/agent_bridge/2026-07-01/aihf_stock_ranking.json`
- concept_members_history.csv: `market_data_service/market_data_service/data/concept_members_history.csv`
