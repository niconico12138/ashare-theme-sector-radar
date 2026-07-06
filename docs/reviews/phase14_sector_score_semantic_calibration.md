# Phase 14: Sector Score Semantic Calibration

**审计日期**: 2026-06-30
**审计目标**: 校准"分数和等级的语义"，确认 neutral/cooling/avoid 是否符合真实历史走势

---

## 1. 核心问题回答

### 1.1 为什么半导体排名第一但只有 51.0？

**原因分析**:

| 组件 | 得分 | 满分 | 利用率 | 说明 |
|------|------|------|--------|------|
| radar_score_component | 8.8 | 25 | 35% | 日报雷达分偏低 (35/100) |
| momentum_component | 12.0 | 20 | 60% | 动量中等 |
| relative_strength_component | 15.0 | 15 | 100% | 相对强度满分 |
| persistence_component | 11.2 | 15 | 75% | 持续性较好 |
| drawdown_component | 0.0 | 10 | 0% | 回撤组件未使用 |
| volatility_component | 4.0 | 5 | 80% | 波动率较低 |
| data_quality_component | 8.0 | 10 | 80% | 数据质量良好 |
| risk_penalty | 8.0 | 20 | - | 风险扣分较高 |

**结论**: 半导体相对表现最好 (relative_strength=15.0 满分)，但被 radar_score (8.8/25) 和 risk_penalty (8.0) 压分。这是合理的，因为：
- 日报雷达分本身偏低 (35/100)
- 风险扣分反映了板块的波动性和不确定性

### 1.2 为什么医疗/医药链从 raw_snapshot strong_watch 变成 sector_history cooling/avoid？

**原因分析**:

| 板块 | raw_snapshot 分数 | sector_history 分数 | 差异原因 |
|------|------------------|---------------------|----------|
| 医疗服务 | 80.3 | 40.0 | 历史数据不足导致评分高估 |
| 化学制药 | 80.3 | 35.75 | 历史数据不足导致评分高估 |
| 生物制品 | 80.3 | 31.25 | 历史数据不足导致评分高估 |

**关键发现**:
- raw_snapshot_fallback 只有 2 天数据，无法准确评估持续性和动量
- sector_history_cache 有 9 天数据，更能反映真实走势
- 医药链在 9 天窗口内表现一般，持续性不足

### 1.3 哪些组件压分最多？

**组件利用率统计**:

| 组件 | 均值 | 满分 | 利用率 | 压力等级 |
|------|------|------|--------|----------|
| radar_score_component | 9.47 | 25 | 37.9% | 🔴 高压 |
| momentum_component | 6.00 | 20 | 30.0% | 🔴 高压 |
| persistence_component | 5.25 | 15 | 35.0% | 🔴 高压 |
| relative_strength_component | 7.88 | 15 | 52.5% | 🟡 中压 |
| volatility_component | 3.30 | 5 | 66.0% | 🟢 低压 |
| data_quality_component | 8.00 | 10 | 80.0% | 🟢 低压 |
| drawdown_component | 0.00 | 10 | 0.0% | ⚪ 未使用 |
| risk_penalty | 13.40 | 20 | 67.0% | 🔴 高压 |

**最大压分项**:
1. **radar_score_component** (37.9%): 日报雷达分本身偏低
2. **momentum_component** (30.0%): 动量不足
3. **persistence_component** (35.0%): 持续性不足
4. **risk_penalty** (67.0%): 风险扣分较高

### 1.4 当前等级阈值是否过严？

**阈值分析**:

| 等级 | 阈值 | 当前分布 | 评估 |
|------|------|----------|------|
| strong_watch | >= 80 | 0% | 过严，无板块达到 |
| watch | >= 65 | 0% | 过严，无板块达到 |
| neutral | >= 50 | 10% (1个) | 合理 |
| cooling | >= 35 | 20% (2个) | 合理 |
| avoid | < 35 | 70% (7个) | 偏多 |

**结论**: 阈值设计本身合理，但当前市场环境下大部分板块都处于 avoid 状态。这可能反映了：
- 市场整体偏弱
- 评分算法偏保守
- 数据质量问题

### 1.5 当前评分是否更偏向"趋势持续型"，而不是"短线爆发型"？

**分析**:

| 评分维度 | 权重 | 适用场景 |
|----------|------|----------|
| radar_score_component | 25% | 短线爆发 |
| momentum_component | 20% | 趋势持续 |
| relative_strength_component | 15% | 趋势持续 |
| persistence_component | 15% | 趋势持续 |
| drawdown_component | 10% | 风险控制 |
| volatility_component | 5% | 风险控制 |
| data_quality_component | 10% | 数据质量 |

**结论**: 当前评分确实更偏向**趋势持续型** (momentum + relative_strength + persistence = 50%)，而不是短线爆发型 (radar_score = 25%)。这是设计意图，但可能不适合捕捉短线机会。

### 1.6 是否需要拆分两个评分？

**建议**:

| 评分类型 | 适用场景 | 建议 |
|----------|----------|------|
| trend_continuation_score | 趋势持续确认 | ✅ 保留当前综合评分 |
| short_term_burst_score | 短线爆发捕捉 | 🔜 Phase 15 新增 |

**理由**:
- 当前综合评分适合判断趋势是否持续
- 短线爆发需要更看重当日雷达、1日涨幅、资金流
- 两个评分可以并列展示，各有侧重

---

## 2. 评分语义审计发现

### 2.1 核心发现

1. **评分偏保守**: 当前评分更倾向于确认趋势，而非捕捉机会
2. **风险扣分较高**: risk_penalty 平均 13.4/20，反映市场不确定性
3. **动量不足**: momentum_component 平均利用率仅 30%
4. **持续性不足**: persistence_component 平均利用率仅 35%

### 2.2 数据质量问题

1. **drawdown_component 未使用**: 所有板块 drawdown=0.0
2. **volatility_component 未充分利用**: 平均利用率仅 66%
3. **data_quality_component 固定**: 所有板块都是 8.0/10

### 2.3 语义解释

| 等级 | 语义解释 | 适用场景 |
|------|----------|----------|
| strong_watch | 趋势强劲，风险可控 | 长期持有 |
| watch | 趋势良好，需观察 | 中期持有 |
| neutral | 表现中性 | 观望 |
| cooling | 板块降温 | 减仓/观望 |
| avoid | 板块弱势 | 回避 |

---

## 3. 建议

### 3.1 短期 (Phase 14)

1. **不调权重**: 当前权重设计合理，问题在于数据质量
2. **保留当前综合评分**: 作为趋势持续分
3. **记录审计结论**: 明确评分语义和适用场景

### 3.2 中期 (Phase 15)

1. **新增短线爆发分**: 与趋势持续分并列展示
2. **优化 drawdown_component**: 使用真实回撤数据
3. **优化 volatility_component**: 使用真实波动率数据

### 3.3 长期

1. **数据质量提升**: 增加历史数据深度
2. **评分校准**: 根据实际表现调整阈值
3. **多维度评分**: 支持不同投资策略

---

## 4. 结论

当前评分算法**逻辑正确**，问题在于：
1. 数据质量不足 (drawdown=0, volatility 偏低)
2. 评分偏保守 (趋势持续型)
3. 阈值设计合理但市场整体偏弱

**建议**:
- 不调整权重
- 保留当前综合评分作为趋势持续分
- Phase 15 新增短线爆发分
