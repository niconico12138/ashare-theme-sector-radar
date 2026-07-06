# Phase 46: CatalystEventAgent Signal Validation

## 修改内容

1. 新增 `theme_sector_radar/backtest/catalyst_event_backtest.py`
2. 新增 `theme_sector_radar/reports/catalyst_event_backtest_report.py`
3. 修改 `cli.py`：新增 `--backtest-catalyst-events` 参数
4. 新增 `tests/theme_sector_radar/test_catalyst_event_backtest.py`：8 个测试
5. 新增 `docs/plans/phase46_catalyst_event_signal_validation_plan.md`

## catalyst cache 覆盖率

- 总样本: 280
- 有 cache 样本: 10 (4%)
- 缺少 cache 样本: 270 (96%)
- fixture 数据: 10 样本
- 真实数据: 0 样本

## fixture / real 数据比例

- fixture: 10 样本
- real: 0 样本
- missing_cache: 270 样本

**结论**: 仅有 fixture 数据，标记为 limited_fixture_validation

## catalyst_label performance

| Label | 样本数 | 5日均值 | 5日正收益率 |
|--------|--------|---------|------------|
| catalyst_unknown | 280 | +0.54% | 51% |

**说明**: 由于大部分样本缺少 catalyst cache，所有样本都被标记为 catalyst_unknown。

## event_count / freshness / confidence 结果

- 0_events: 280 样本 (100%)
- 其他 event_count 桶: 0 样本

**说明**: 由于只有 1 天有 fixture 数据，event_count 分析样本不足。

## catalyst x short_term_heat 结果

| 组合 | 样本数 | 5日均值 | 5日正收益率 |
|------|--------|---------|------------|
| no_catalyst + heat_positive | 32 | +3.42% | 78% |

**说明**: short_term_heat positive 本身表现很好，但由于 catalyst 数据不足，无法验证叠加效果。

## catalyst x persistence_strength 结果

无足够数据进行分析。

## catalyst x market_regime 结果

无足够数据进行分析。

## 是否建议 Phase 47 调整 vote

**否。** 原因：
1. 只有 fixture 数据，标记为 limited_fixture_validation
2. catalyst_observed 样本数为 0（缺少 cache）
3. 需要更多真实事件样本验证

## 是否仍保持 report-only

**是。** CatalystEventAgent 继续保持 report-only。

## 是否影响生产决策规则

**否。**

## 测试结果

8 个新增测试全部通过。

## 是否仍未修改 ai-hedge-fund 项目

**未修改。**

---

*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不构成投资建议。*
