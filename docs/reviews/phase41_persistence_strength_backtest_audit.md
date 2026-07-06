# Phase 41: PersistenceStrengthAgent 审计报告

## persistence_strength vote 分布

| Vote | 样本数 | 占比 |
|------|--------|------|
| positive | 6 | 2% |
| neutral | 274 | 98% |
| negative | 0 | 0% |

## persistence labels 分布

大部分样本为 persistence_weak，因为：
1. streak >= 3 且 trend rising 的条件过于严格
2. persistence_building 需要 score >= 0.6 才能 positive
3. flat trend 在长 streak 时被过度惩罚

## positive vote 表现

- sample_count: 6
- forward_5d_avg: +7.38%
- forward_5d_positive_ratio: 100%

**观察**: positive vote 非常准确，但样本太少。

## neutral vote 表现

- sample_count: 274
- forward_5d_avg: +0.34%
- forward_5d_positive_ratio: 50%

**观察**: neutral 接近市场均值，区分度不足。

## reliability_score=0.30 的原因

1. positive 样本过少 (6/280 = 2%)
2. vote 分布过于集中在 neutral
3. separation_score 低 (positive 和 neutral 差异不大)

## 校准建议

1. 长 streak (>=5) 且无风险/冲突时，应为 persistence_building
2. 降低 persistence_building 的 positive vote 阈值
3. 增加有利 label_transition
4. 保留 conflict/risk penalty
