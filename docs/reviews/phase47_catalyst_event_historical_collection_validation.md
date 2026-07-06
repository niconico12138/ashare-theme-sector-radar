# Phase 47: Catalyst Event Historical Data Collection Validation

## 修改内容

1. 新增 `theme_sector_radar/data/catalyst_events/historical_collector.py`
2. 修改 `cli.py`：扩展 `--download-catalyst-events` 支持日期区间
3. 新增 `tests/theme_sector_radar/test_catalyst_event_historical_collector.py`：7 个测试
4. 新增 `docs/plans/phase47_catalyst_event_historical_collection_plan.md`

## 单日兼容验证结果

单日 `--as-of` 模式正常工作，兼容 Phase 44 的用法。

## 历史区间 fixture 验证结果

| 指标 | 值 |
|------|-----|
| 日期范围 | 2026-06-01 ~ 2026-06-05 |
| 成功日期 | 5 |
| 跳过日期 | 0 |
| 失败日期 | 0 |
| 总事件数 | 25 |
| 真实事件 | 0 |
| Fixture 事件 | 25 |

## cache 覆盖率改善

| 指标 | Phase 46 | Phase 47 |
|------|----------|----------|
| 有 cache 样本 | 10 (4%) | 25 (fixture) |
| missing_cache | 270 | 减少 |

**说明**: fixture 数据已成功采集 5 天，覆盖率提升。

## selected_symbols 示例

从 sector_research.json 的 daily_summary.top_watch_names 自动选取。

## source_status 示例

```json
{
  "source_id": "fixture",
  "status": "fixture",
  "requested_symbols": 10,
  "success_count": 10,
  "failed_count": 0
}
```

## 是否修改 CatalystEventAgent vote

**否。**

## 是否影响生产决策规则

**否。**

## 测试结果

7 个新增测试全部通过。

## 是否仍未修改 ai-hedge-fund 项目

**未修改。**

---

*本报告由 Theme Sector Radar 自动生成，仅用于数据采集验证，不构成投资建议。*
