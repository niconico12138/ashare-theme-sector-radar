# Phase 33: Market Regime Revalidation and Agent Integration Proposal

## 总览

| 指标 | Phase 32 | Phase 33 |
|------|----------|----------|
| sample_count | 560 | 280 |
| regime 类型 | 4 (choppy, risk_off, weak_rebound, risk_on) | 3 (choppy, risk_off, risk_on) |
| no-lookahead | PASS | PASS |

**注意**: Phase 33 样本数减少是因为 research range 重新生成后只覆盖 28 个日期（2026-06-01 因数据不足跳过）。

## Regime 分布

| regime | Phase 32 | Phase 33 |
|--------|----------|----------|
| choppy_market | 420 (75%) | 230 (82%) |
| risk_off | 80 (14%) | 40 (14%) |
| weak_rebound | 40 (7%) | 0 (0%) |
| risk_on | 20 (4%) | 10 (4%) |

**观察**: weak_rebound 在 Phase 33 中消失，可能因为样本量减少导致某些日期的 regime 计算结果变化。

## Label x Regime 核心结果

### oversold_rebound_candidate

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 78 | +0.09% | 48% |
| risk_off | 1 | -1.78% | 0% |
| risk_on | 2 | -6.66% | 0% |

**观察**: oversold_rebound 在 choppy_market 下表现中性（+0.09%, 48%正），在 risk_on 下表现差。与 Phase 32 结论一致。

### low_signal_noise

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 1 | -3.56% | 0% |
| risk_off | 11 | +0.25% | 50% |

**观察**: low_signal_noise 样本量大幅减少（Phase 32: 79 → Phase 33: 12），在 risk_off 下表现略好。

### conflicted

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 25 | **+2.14%** | **50%** |
| risk_off | 6 | N/A | N/A |

**观察**: conflicted 在 choppy_market 下表现改善（Phase 32: -2.01% → Phase 33: +2.14%），但样本量较少。

### weak_or_avoid

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 54 | +0.80% | 56% |
| risk_off | 4 | -2.73% | 0% |

**观察**: weak_or_avoid 在 choppy_market 下表现好（+0.80%, 56%正），在 risk_off 下表现差。

### short_term_active_unconfirmed

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 25 | **+4.69%** | **84%** |
| risk_on | 1 | -5.81% | 0% |

**观察**: short_term_active_unconfirmed 在 choppy_market 下表现显著好（+4.69%, 84%正），是所有标签中表现最好的。

### early_repair_watch

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 22 | -0.67% | 40% |
| risk_on | 5 | -7.60% | 0% |

**观察**: early_repair_watch 在 risk_on 下表现极差（-7.60%），在 choppy_market 下略负。

## Opportunity Score 诊断

| 分桶 | 样本数 | 5日均收益 |
|------|--------|----------|
| high | 1 | -7.63% |
| medium | 39 | +2.14% |
| low | 150 | +0.23% |

**观察**: high 桶终于有 1 个样本，但表现差。medium 桶表现最好（+2.14%），low 桶中性。

## 正式评估

### 1. 增强后的 market_regime 是否稳定改善解释力

**是的，但有限。**

- regime 分布从 2 类扩展到 3-4 类，区分度提升
- low_signal_noise 在不同 regime 下仍有差异（risk_off +0.25% vs choppy -3.56%）
- 但样本量不足（特别是 risk_on 仅 10 个），统计意义有限

### 2. Agent 标签在不同 regime 下是否有稳定差异

**部分标签有稳定差异：**

| 标签 | choppy 表现 | risk_off 表现 | 差异 |
|------|------------|--------------|------|
| oversold_rebound | +0.09% | -1.78% | 有差异 |
| weak_or_avoid | +0.80% | -2.73% | 有差异 |
| conflicted | +2.14% | N/A | 样本不足 |
| short_term_active | +4.69% | N/A | 样本不足 |

**结论**: 标签在不同 regime 下确实有差异，但需要更多样本验证稳定性。

### 3. 是否建议新增 MarketRegimeAgent

**建议：暂不新增，但可在报告中展示 regime 信息。**

理由：

1. **样本量不足**: risk_on 仅 10 个样本，weak_rebound 消失，统计意义有限
2. **regime 分布不稳定**: Phase 32 和 Phase 33 的 regime 分布有差异（weak_rebound 消失）
3. **标签差异需要更多验证**: 当前差异可能是市场环境导致，不是 regime 信息的贡献
4. **已有替代方案**: 可在 sector_research.md 中展示 regime 信息，观察人工复盘效果

### 4. 如果建议新增，应先作为"解释层 Agent"还是进入 ConsensusDecisionAgent 决策层

**如果未来新增，建议先作为"解释层 Agent"。**

理由：

1. **解释层 Agent**: 只提供 regime 信息，不直接影响标签决策。可以在报告中展示，帮助人工复盘。
2. **决策层 Agent**: 直接影响标签决策，需要更多验证才能确保不会引入偏差。
3. **渐进式接入**: 先解释层 → 人工验证 → 决策层

### 5. 是否建议修改生产标签规则

**否，暂不修改。**

理由：

1. 当前标签在不同 regime 下的表现差异主要是市场环境导致
2. 强行根据 regime 调整标签可能导致过拟合
3. 样本量不足，需要更多数据验证

## 下一阶段建议

1. **在 sector_research.md 中展示 regime 信息**: 让人工复盘可以参考 regime 标签
2. **积累更多历史数据**: 扩展到 3-6 个月，验证 regime 分层的稳定性
3. **如果 regime 分层持续有效**: 在 Phase 35+ 考虑新增 MarketRegimeAgent 作为解释层
4. **继续观察 short_term_active_unconfirmed**: 该标签在 choppy_market 下表现显著好，值得深入分析

## 数据限制

- 样本期仅 1 个月（2026-06-01 ~ 2026-06-29），统计意义有限
- risk_on 仅 10 个样本，weak_rebound 消失
- forward_20d 可能因为未来数据不足为空

---

*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不构成投资建议。*
