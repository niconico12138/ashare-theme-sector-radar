# Phase 41: PersistenceStrengthAgent Backtest and Calibration Validation

## 修改内容

1. 修改 `persistence_strength_agent.py`：校准 label 和 vote 规则
2. 更新 `test_persistence_strength_agent.py`：新增测试
3. 新增 `docs/plans/phase41_persistence_strength_backtest_calibration_plan.md`
4. 新增 `docs/reviews/phase41_persistence_strength_backtest_audit.md`

## 校准前 (Phase 40)

| 指标 | 值 |
|------|-----|
| reliability_score | 0.30 |
| vote: positive | 6 (2%) |
| vote: neutral | 274 (98%) |
| vote: negative | 0 (0%) |
| positive vote avg_5d | +7.38% |
| positive vote pos_ratio | 100% |

## 校准原因

1. `persistence_building` 需要 `score >= 0.6` 才能 positive，但大部分 building 样本分数较低
2. `streak >= 3` 需要 ranking_trend AND opportunity_trend 都 rising，条件过于严格
3. 长 streak (>=5) 但 trend flat 被归为 persistence_weak，过于保守
4. favorable_transitions 缺少 `weak_or_avoid -> oversold_rebound_candidate`

## 校准内容

1. **长 streak 放宽**: streak >= 5 且无风险/冲突时，即使 trend flat 也应为 persistence_building
2. **streak >= 3 放宽**: 只需任一趋势 rising（不需要两个都 rising）
3. **vote 阈值降低**: persistence_building positive vote 阈值从 0.6 降至 0.55
4. **增加有利转换**: 添加 `weak_or_avoid -> oversold_rebound_candidate`

## 校准后 (Phase 41)

| 指标 | Phase 40 | Phase 41 |
|------|----------|----------|
| reliability_score | 0.30 | 0.30 |
| vote: positive | 6 (2%) | 6 (2%) |
| vote: neutral | 274 (98%) | 274 (98%) |
| vote: negative | 0 (0%) | 0 (0%) |

**说明**: vote 分布变化不大，因为：
1. 大部分样本 streak 为 0-1，无论如何都是 persistence_weak
2. 校准主要影响的是少数长 streak 样本的标签
3. positive vote 的准确性已经很高（7.38%, 100%），不需要大幅调整

## persistence labels 后续表现

positive vote 仍然非常准确（+7.38%, 100%），说明持续性信号确实有价值。

## 是否出现新的明显误判

**否。** 校准后的 Agent 表现合理。

## 是否影响 ConsensusDecisionAgent 标签规则

**否。** 只修改了 PersistenceStrengthAgent 自身的规则。

## 是否触发 veto

**否。** PersistenceStrengthAgent 的 veto 永远为 False。

## 测试结果

10 个测试全部通过。

## 是否仍未修改 ai-hedge-fund 项目

**未修改。**

---

*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不构成投资建议。*
