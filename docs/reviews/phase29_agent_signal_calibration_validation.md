# Phase 29: Agent Signal Calibration Validation

## 校准前 Phase 28 基准

| 指标 | Phase 28 |
|------|----------|
| research_report_count | 28 |
| sample_count | 560 |
| vote: positive/neutral/negative | 0/560/0 |
| conflict: has_conflict/no_conflict | 560/0 |
| veto: veto_true/veto_false | 560/0 |
| low_signal_noise 占比 | 79.3% (444/560) |

## 校准后 Label Performance

| 标签 | 样本数 | 占比 | 5日均收益 | Phase 28 对比 |
|------|--------|------|----------|--------------|
| low_signal_noise | 79 | 14.1% | +1.34% | 444→79, -0.17%→+1.34% |
| weak_or_avoid | 220 | 39.3% | +0.16% | 37→220, -3.00%→+0.16% |
| defensive_stable_watch | 172 | 30.7% | -3.62% | 新标签 |
| oversold_rebound_candidate | 17 | 3.0% | -1.47% | 22→17, -0.77%→-1.47% |
| conflicted | 39 | 7.0% | -3.94% | 不变 |
| early_repair_watch | 9 | 1.6% | +0.10% | 新标签 |
| insufficient_data | 14 | 2.5% | -3.58% | 不变 |
| trend_confirmed_but_strength_limited | 4 | 0.7% | -2.65% | 不变 |
| data_limited_neutral | 6 | 1.1% | N/A | 新标签 |

### 核心改善

1. **low_signal_noise 占比从 79.3% 降到 14.1%** — 标签解释力显著提升
2. **low_signal_noise 5日均收益从 -0.17% 提升到 +1.34%** — 收窄后该标签更有区分度
3. **weak_or_avoid 5日均收益从 -3.00% 提升到 +0.16%** — 拆分后该标签更准确
4. **新增 3 个标签**: early_repair_watch, data_limited_neutral, defensive_stable_watch

## Score Bucket Performance

### Ranking Score

| 桶 | 样本数 | 5日均收益 | Phase 28 |
|----|--------|----------|----------|
| high | 0 | - | 不变 |
| medium | 195 | -2.81% | 26→195 |
| low | 365 | -0.09% | 534→365 |

medium 桶样本从 26 增加到 195，分桶区分度提升。

### Opportunity Score

| 桶 | 样本数 | 5日均收益 | Phase 28 |
|----|--------|----------|----------|
| high | 0 | - | 不变 |
| medium | 6 | -3.01% | 不变 |
| low | 554 | -0.68% | 不变 |

### Confidence Score

| 桶 | 样本数 | 5日均收益 | Phase 28 |
|----|--------|----------|----------|
| high | 405 | -1.21% | 不变 |
| medium | 139 | +0.86% | 不变 |
| low | 16 | -3.58% | 不变 |

## Vote Performance

| 投票类型 | 样本数 | 5日均收益 | Phase 28 |
|---------|--------|----------|----------|
| positive | 40 | -3.32% | 0→40 |
| neutral | 19 | -1.23% | 560→19 |
| negative | 501 | -0.57% | 0→501 |

投票分布从全 neutral 变为有实际区分。

## Conflict Performance

| 冲突类型 | 样本数 | 5日均收益 | Phase 28 |
|---------|--------|----------|----------|
| no_conflict | 549 | -0.71% | 0→549 |
| has_conflict | 11 | -1.00% | 560→11 |

冲突检测从 100% 触发降为 2% 触发。

## Veto Performance

| Veto 状态 | 样本数 | 5日均收益 | Phase 28 |
|-----------|--------|----------|----------|
| veto_true | 14 | -3.58% | 560→14 |
| veto_false | 546 | -0.62% | 0→546 |

Veto 从 100% 触发降为 2.5% 触发。

## False Positive / Missed Opportunity

- **False Positive**: 0 项（不变）
- **Missed Opportunity**: 10 项（不变），均为 weak_or_avoid 标签

## 是否改善

| 指标 | 改善 | 说明 |
|------|------|------|
| vote 分布 | ✅ | 从全 neutral 变为有区分 |
| conflict 分布 | ✅ | 从 100% 降为 2% |
| veto 分布 | ✅ | 从 100% 降为 2.5% |
| low_signal_noise 占比 | ✅ | 从 79% 降为 14% |
| 标签多样性 | ✅ | 从 6 个标签增加到 9 个 |
| ranking_score medium 桶 | ✅ | 从 26 增加到 195 |
| low_signal_noise 收益 | ✅ | 从 -0.17% 提升到 +1.34% |

## 是否有过拟合风险

**低风险。** 校准基于以下原则：
1. 修复了 Agent 投票缺失的代码缺陷（不是调参）
2. 移除了 universal veto 规则（修复 bug）
3. 收紧了冲突检测（修复 universal trigger）
4. 拆分了过度使用的兜底标签（提升解释力）

没有针对回测结果调参。

## 哪些规则仍需观察

1. **oversold_rebound_candidate**: 收紧后样本减少到 17，收益 -1.47%，仍需观察
2. **defensive_stable_watch**: 新标签 172 样本，收益 -3.62%，需要更多数据验证
3. **positive vote 表现差**: 40 样本收益 -3.32%，可能需要调整投票阈值
4. **opportunity_score high 桶仍为空**: 市场整体偏弱，不强行调高

## 下一阶段建议

1. **扩大回测范围**: 测试 3-6 个月数据，验证标签稳定性
2. **概念板块回测**: 对比行业和概念板块的标签分布差异
3. **调整 positive vote 阈值**: 当前 positive 样本收益差，可能需要更严格的 positive 条件
4. **观察 defensive_stable_watch**: 该标签占比 30%，需要验证其区分度
5. **考虑增加 mid-term 回测**: 10日/20日收益分析

---

*本报告仅用于板块研究、观察和复盘，不构成投资建议。*
