# Phase 49: Catalyst Coverage Rebuild and Signal Revalidation

## 修改内容

本阶段未修改代码，仅重新运行分析流程。

## fixture rebuild 结果

| 指标 | 值 |
|------|-----|
| 日期范围 | 2026-06-01 ~ 2026-06-29 |
| 生成日期 | 29 |
| 跳过日期 | 0 |
| 失败日期 | 0 |
| 总事件数 | 145 |
| 真实事件 | 0 |
| Fixture 事件 | 145 |
| 映射率 | 80% |

## network smoke 结果

未执行网络验证（离线环境）。

## mapping_rate 结果

- Phase 47: 20%
- Phase 48: 80%
- Phase 49: 80%（保持）

## Phase 46 vs Phase 49 cache 覆盖率对比

| 指标 | Phase 46 | Phase 49 |
|------|----------|----------|
| cache 覆盖率 | 4% | **100%** |
| 有 cache 样本 | 10 | 280 |
| missing_cache | 270 | 0 |

## Phase 46 vs Phase 49 fixture / real / missing 对比

| 指标 | Phase 46 | Phase 49 |
|------|----------|----------|
| fixture | 10 | 280 |
| real | 0 | 0 |
| missing_cache | 270 | 0 |

## catalyst_label 分布

| Label | Phase 46 | Phase 49 |
|-------|----------|----------|
| catalyst_unknown | 280 (100%) | 0 (0%) |
| catalyst_observed | 0 (0%) | 3 (1.1%) |
| no_catalyst_observed | 0 (0%) | 277 (98.9%) |

## catalyst_label performance

| Label | 样本数 | 5日均值 | 5日正收益率 |
|--------|--------|---------|------------|
| catalyst_observed | 3 | +1.67% | 50% |
| no_catalyst_observed | 277 | +0.53% | 51% |

## catalyst x short_term_heat 结果

| 组合 | 样本数 | 5日均值 | 5日正收益率 |
|------|--------|---------|------------|
| no_catalyst + heat_positive | 32 | +3.42% | 78% |

**说明**: catalyst_observed 样本太少（3个），无法做有意义的叠加分析。

## catalyst x persistence_strength 结果

无足够数据进行分析。

## catalyst x market_regime 结果

无足够数据进行分析。

## 是否建议 Phase 50 调整 vote

**否。**

理由：
1. 所有数据都是 fixture，标记为 limited_fixture_validation
2. catalyst_observed 样本仅 3 个，远不足以支撑 vote 校准
3. 需要真实网络事件数据才能验证信号有效性

## 是否仍保持 report-only

**是。** CatalystEventAgent 继续保持 report-only。

## 是否影响生产决策规则

**否。**

## 测试结果

无新增测试。所有现有测试通过。

## 是否仍未修改 ai-hedge-fund 项目

**未修改。**

---

*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不构成投资建议。*
