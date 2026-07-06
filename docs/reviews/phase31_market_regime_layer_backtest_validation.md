# Phase 31: Market Regime Layer Backtest Validation

## 总览

| 指标 | 值 |
|------|-----|
| research_report_count | 28 |
| sample_count | 560 |
| no-lookahead | PASS |
| benchmark | hs300 |

## 市场状态分布

### 基准趋势

| 状态 | 样本数 | 占比 |
|------|--------|------|
| benchmark_sideways | 300 | 54% |
| benchmark_uptrend | 140 | 25% |
| benchmark_downtrend | 120 | 21% |

### 市场温度

| 状态 | 样本数 | 占比 |
|------|--------|------|
| market_cool | 560 | 100% |

**观察**: market_temperature 全部为 cool，因为 replay 模式下 temperature 固定为 neutral(50)。

### 广度

| 状态 | 样本数 | 占比 |
|------|--------|------|
| mixed_breadth | 560 | 100% |

**观察**: 广度全部为 mixed，因为 replay 报告中 industry_top 的 change_pct 为 0.0。

### 波动率

| 状态 | 样本数 | 占比 |
|------|--------|------|
| normal_volatility | 420 | 75% |
| low_volatility | 140 | 25% |

### 综合标签

| 状态 | 样本数 | 占比 |
|------|--------|------|
| weak_rebound | 300 | 54% |
| choppy_market | 260 | 46% |

## 标签在不同市场状态下的表现

### oversold_rebound_candidate

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| weak_rebound | 7 | -0.01% | 40% |
| choppy_market | 10 | -0.19% | 43% |

**观察**: oversold_rebound_candidate 在两种 regime 下表现相似，均略为负。该标签的表现与市场状态关系不大。

### low_signal_noise

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| weak_rebound | 49 | -0.07% | 31% |
| choppy_market | 30 | +1.53% | 78% |

**观察**: low_signal_noise 在 choppy_market 下表现显著更好（+1.53% vs -0.07%），正收益率 78% vs 31%。这说明部分 low_signal_noise 样本在市场波动中反而有机会。

### weak_or_avoid

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| weak_rebound | 166 | -0.48% | 33% |
| choppy_market | 54 | +1.56% | 72% |

**观察**: weak_or_avoid 在 choppy_market 下表现也显著更好（+1.56% vs -0.48%），与 low_signal_noise 类似。

### conflicted

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 31 | -2.79% | 20% |

**观察**: conflicted 在 choppy_market 下持续偏弱（-2.79%），标签一致性较好。

### defensive_stable_watch

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 117 | -1.70% | 29% |

**观察**: defensive_stable_watch 在 choppy_market 下偏弱，符合预期。

## missed_opportunity 市场状态归因

| regime | 样本数 | 5日均收益 |
|--------|--------|----------|
| weak_rebound | 16 | +7.51% |
| choppy_market | 18 | +5.78% |

**观察**: missed_opportunity 在两种 regime 下均有分布，weak_rebound 下略多（16 vs 18），但差异不大。这说明 missed_opportunity 不是集中在某一特定市场状态，而是分散在不同环境中。

## failed_rebound 市场状态归因

| regime | 样本数 | 5日均收益 |
|--------|--------|----------|
| weak_rebound | 3 | -3.89% |
| choppy_market | 4 | -1.88% |

**观察**: failed_rebound 在 weak_rebound 下更差（-3.89% vs -1.88%），说明市场弱势环境下反弹候选更容易失败。

## 结论

### 是否建议新增 Market Regime Agent

**建议：暂不新增**

理由：
1. 当前市场温度全部为 cool（replay 模式限制），无法验证温度 regime 的区分度
2. 广度全部为 mixed，同样受限于 replay 数据
3. 综合标签只有 weak_rebound 和 choppy_market 两种，分布不够多样
4. 需要更多真实市场数据（非 replay）才能验证 Market Regime Agent 的价值

### 是否建议将 market_regime 接入 ConsensusDecisionAgent

**建议：暂不接入**

理由：
1. 当前分析仅验证了分层效果，未证明 regime 信息能提升标签准确性
2. low_signal_noise 和 weak_or_avoid 在 choppy_market 下表现更好，但这可能是市场反弹导致，不是 regime 信息的贡献
3. 建议先在报告中展示 regime 信息，观察人工复盘效果

### 是否建议暂不修改标签规则

**是，暂不修改**

理由：
1. 当前标签在不同 regime 下的表现差异主要是市场环境导致，不是标签逻辑问题
2. 强行根据 regime 调整标签可能导致过拟合
3. 样本量不足（560 个），统计意义有限

### 下一阶段建议

1. 在 sector_research.md 报告中增加 regime 标签展示
2. 使用真实市场数据（非 replay）重新分析，验证 regime 分层的区分度
3. 如果 regime 分层在真实数据下持续有效，考虑在 Phase 33+ 新增 Market Regime Agent
4. 继续观察 missed_opportunity 和 failed_rebound 的 regime 分布变化

## 数据限制

- market_temperature 在 replay 模式下固定为 neutral，限制了温度 regime 的区分度
- breadth 基于 industry_top 20 个板块的 change_pct（replay 下为 0.0），限制了广度 regime 的区分度
- 综合标签只有 weak_rebound 和 choppy_market，分布不够多样
- forward_20d 可能因为未来数据不足为空

---

*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不构成投资建议。*
