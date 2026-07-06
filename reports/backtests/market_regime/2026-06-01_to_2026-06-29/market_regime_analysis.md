# Market Regime Layer Backtest 报告

> **免责声明**: 本报告仅用于板块研究、观察和复盘，不构成投资建议。

## 总览

- **日期范围**: 2026-06-01 ~ 2026-06-29
- **板块类型**: industry
- **基准**: hs300
- **样本数量**: 280
- **no-lookahead 检查**: 通过 (0 violations)

## 市场状态分布

### 基准趋势

| 状态 | 样本数 | 占比 |
|------|--------|------|
| benchmark_sideways | 150 | 54% |
| benchmark_uptrend | 70 | 25% |
| benchmark_downtrend | 60 | 21% |

### 市场温度

| 状态 | 样本数 | 占比 |
|------|--------|------|
| market_cold | 170 | 61% |
| market_hot | 50 | 18% |
| market_warm | 40 | 14% |
| market_cool | 20 | 7% |

### 广度

| 状态 | 样本数 | 占比 |
|------|--------|------|
| broad_rising | 240 | 86% |
| broad_falling | 40 | 14% |

### 波动率

| 状态 | 样本数 | 占比 |
|------|--------|------|
| normal_volatility | 210 | 75% |
| low_volatility | 70 | 25% |

### 综合标签

| 状态 | 样本数 | 占比 |
|------|--------|------|
| choppy_market | 230 | 82% |
| risk_off | 40 | 14% |
| risk_on | 10 | 4% |

## 标签在不同市场状态下的表现

### oversold_rebound_candidate

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 78 | 0.09% | 48% |
| risk_off | 1 | -1.78% | 0% |
| risk_on | 2 | -6.66% | 0% |

### low_signal_noise

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 1 | -3.56% | 0% |
| risk_off | 11 | 0.25% | 50% |

### conflicted

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 25 | 2.14% | 50% |
| risk_off | 6 | - | - |

### weak_or_avoid

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 54 | 0.80% | 56% |
| risk_off | 4 | -2.73% | 0% |

### trend_confirmed_but_strength_limited

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 8 | 2.26% | 33% |

### defensive_stable_watch

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 9 | -2.18% | 0% |
| risk_off | 18 | - | - |

### early_repair_watch

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 22 | -0.67% | 40% |
| risk_on | 5 | -7.60% | 0% |

## missed_opportunity 市场状态归因

共 11 个 missed_opportunity 样本。

| regime | 样本数 | 5日均收益 |
|--------|--------|----------|
| choppy_market | 10 | 5.16% |
| risk_off | 1 | 7.91% |

## failed_rebound 市场状态归因

共 27 个 failed_rebound 样本。

| regime | 样本数 | 5日均收益 |
|--------|--------|----------|
| choppy_market | 24 | -3.24% |
| risk_on | 2 | -6.66% |
| risk_off | 1 | -1.78% |

## 结论

### 是否建议新增 Market Regime Agent

- 建议：**暂不新增**
- 原因：当前市场状态分布较为集中，样本量不足以验证 Agent 效果
- 建议先积累 3 个月以上数据再评估

### 是否建议将 market_regime 接入 ConsensusDecisionAgent

- 建议：**暂不接入**
- 原因：当前分析仅验证了分层效果，未证明 regime 信息能提升标签准确性
- 建议先在报告中展示 regime 信息，观察人工复盘效果

### 是否建议暂不修改标签规则

- **是，暂不修改**
- 原因：当前标签在不同 regime 下的表现差异主要是市场环境导致，不是标签逻辑问题
- 强行根据 regime 调整标签可能导致过拟合

### 下一阶段建议

1. 在 sector_research.md 报告中增加 regime 标签展示
2. 积累更多历史数据（3-6 个月），验证 regime 分层的稳定性
3. 如果 regime 分层持续有效，考虑在 Phase 33+ 新增 Market Regime Agent
4. 继续观察 missed_opportunity 和 failed_rebound 的 regime 分布变化

## 数据限制

- market_temperature 在 replay 模式下固定为 neutral，限制了温度 regime 的区分度
- breadth 基于 industry_top 20 个板块，可能不完全代表全市场广度
- forward_20d 可能因为未来数据不足为空

---

*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不构成投资建议。*