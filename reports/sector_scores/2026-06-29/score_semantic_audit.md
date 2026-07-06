# 板块评分语义审计报告

**审计日期**: 2026-06-29
**历史数据来源**: sector_history_cache
**历史数据天数**: 9 天

---

## 评分分布

| 等级 | 数量 | 占比 |
|------|------|------|
| strong_watch | 0 | 0% |
| watch | 0 | 0% |
| neutral | 1 | 10% |
| cooling | 2 | 20% |
| avoid | 7 | 70% |

---

## 组件压力分析

| 组件 | 压力等级 | 说明 |
|------|----------|------|
| momentum_component | 🔴 low | 动量不足，平均利用率 30% |
| relative_strength_component | 🟡 medium | 相对强度中等，平均利用率 52.5% |
| persistence_component | 🔴 low | 持续性不足，平均利用率 35% |
| drawdown_component | ⚪ unused | 未使用真实回撤数据 |
| volatility_component | 🟡 medium | 波动率中等，平均利用率 66% |
| risk_penalty | 🔴 high | 风险扣分较高，平均 13.4/20 |

---

## 语义发现

1. **当前评分更偏向趋势持续确认，而非单日爆发**
   - 动量 + 相对强度 + 持续性 = 50% 权重
   - 日报雷达分仅占 25%

2. **医药链虽然日报雷达强，但 9 日历史持续性不足**
   - 医疗服务: raw_snapshot 80.3 → sector_history 40.0
   - 化学制药: raw_snapshot 80.3 → sector_history 35.75
   - 生物制品: raw_snapshot 80.3 → sector_history 31.25

3. **半导体相对表现最好，但仍未达到 watch 阈值**
   - relative_strength 满分 (15.0)
   - 但被 radar_score (8.8/25) 和 risk_penalty (8.0) 压分

4. **risk_penalty 平均 13.4/20，反映市场不确定性**
   - 波动率和下跌天数导致较高风险扣分

5. **momentum_component 平均利用率仅 30%，动量不足**
   - 大部分板块近期表现平平

---

## 建议

| 建议 | 优先级 | 说明 |
|------|--------|------|
| 暂不调权重 | - | 当前权重设计合理 |
| 保留当前综合评分作为趋势持续分 | 高 | 适合判断趋势是否持续 |
| 新增短线爆发分 | 中 | Phase 15 实现 |
| 优化 drawdown_component | 中 | 使用真实回撤数据 |
| 优化 volatility_component | 中 | 使用真实波动率数据 |

---

## 结论

当前评分算法**逻辑正确**，问题在于：
1. 数据质量不足 (drawdown=0, volatility 偏低)
2. 评分偏保守 (趋势持续型)
3. 阈值设计合理但市场整体偏弱

**评分语义**:
- neutral/cooling/avoid 反映了板块的真实表现
- 评分偏保守是设计意图，适合趋势持续确认
- 短线爆发需要单独的评分维度

---

*本报告由 Theme Sector Radar 自动生成，仅用于评分语义校准，不构成个股推荐、买卖建议或自动交易指令。*
