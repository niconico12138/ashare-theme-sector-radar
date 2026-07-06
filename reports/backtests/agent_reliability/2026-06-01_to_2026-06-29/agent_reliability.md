# Agent 可靠性仪表盘

> **免责声明**: 本报告仅用于板块研究、观察和复盘，不作为操作依据。

## 总览

- **日期范围**: 2026-06-01 ~ 2026-06-29
- **样本数量**: 2520
- **Agent 数量**: 9

## Agent 可靠性排名

| Agent | Layer | Signal Profile | 样本数 | 正向票 | 负向票 | 可靠性评分 | 可靠性标签 | 诊断 |
|-------|-------|----------------|--------|--------|--------|------------|------------|------|
| short_term_heat | L2_specialized | broad_signal | 280 | 43 | 108 | 0.72 | high_reliability | positive vote has higher forward returns |
| rotation_analysis | L2_specialized | broad_signal | 280 | 64 | 216 | 0.55 | moderate_reliability | positive vote has higher forward returns |
| technical_trend | L2_specialized | broad_signal | 280 | 10 | 202 | 0.50 | moderate_reliability | positive vote has higher forward returns |
| market_context | L2_specialized | broad_signal | 280 | 90 | 190 | 0.42 | moderate_reliability | positive vote has higher forward returns |
| data_quality | L1_data_evidence | defensive_filter | 280 | 271 | 0 | 0.31 | low_reliability | insufficient data for diagnosis |
| risk_control | L2_specialized | defensive_filter | 280 | 280 | 0 | 0.30 | low_reliability | insufficient data for diagnosis |
| narrative | L2_specialized | low_information | 280 | 0 | 0 | 0.30 | low_reliability | insufficient data for diagnosis |
| persistence_strength | L2_specialized | sparse_high_precision | 280 | 6 | 0 | 0.30 | low_reliability | insufficient data for diagnosis |
| catalyst_event | L2_specialized | sparse_event_signal | 280 | 0 | 0 | 0.30 | low_reliability | insufficient data for diagnosis |

## Signal Profile 说明

| Profile | 说明 |
|---------|------|
| broad_signal | 高覆盖普通信号，大部分样本都有投票，区分度中等 |
| sparse_high_precision | 低覆盖高命中信号，少数样本出手但质量很高 |
| low_information | 低信息 Agent，当前数据不足以产生有效信号 |
| defensive_filter | 防守过滤 Agent，主要识别风险和数据问题 |

## Vote 表现

### short_term_heat

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| positive | 43 | 0.00% | 2.71% | 3.61% | 79% |
| neutral | 129 | 0.00% | -0.67% | -1.20% | 36% |
| negative | 108 | 0.00% | 0.35% | 0.46% | 53% |

### rotation_analysis

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| positive | 64 | 0.00% | 0.72% | 1.88% | 60% |
| negative | 216 | 0.00% | 0.21% | -0.19% | 48% |

### technical_trend

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| positive | 10 | 0.00% | 1.97% | 1.53% | 83% |
| neutral | 68 | 0.00% | 0.41% | 0.96% | 51% |
| negative | 202 | 0.00% | 0.23% | 0.09% | 49% |

### market_context

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| positive | 90 | 0.00% | 0.62% | 0.73% | 54% |
| negative | 190 | 0.00% | 0.23% | 0.15% | 49% |

### data_quality

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| positive | 271 | 0.00% | 0.37% | 0.41% | 51% |
| neutral | 9 | 0.00% | -0.60% | -4.48% | 0% |

### risk_control

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| positive | 280 | 0.00% | 0.33% | 0.32% | 51% |

### narrative

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| neutral | 280 | 0.00% | 0.33% | 0.32% | 51% |

### persistence_strength

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| positive | 6 | 0.00% | 1.77% | 6.47% | 100% |
| neutral | 274 | 0.00% | 0.29% | 0.13% | 49% |

### catalyst_event

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| neutral | 280 | 0.00% | 0.33% | 0.32% | 51% |

## Market Regime 分层

### choppy_market

样本数: 1440

| Agent | 样本数 | 5日均值 | 5日正收益率 |
|-------|--------|---------|------------|
| technical_trend | 160 | -0.25% | - |
| short_term_heat | 160 | -0.25% | - |
| rotation_analysis | 160 | -0.25% | - |
| risk_control | 160 | -0.25% | - |
| data_quality | 160 | -0.25% | - |
| market_context | 160 | -0.25% | - |
| narrative | 160 | -0.25% | - |
| persistence_strength | 160 | -0.25% | - |
| catalyst_event | 160 | -0.25% | - |

### risk_off

样本数: 360

| Agent | 样本数 | 5日均值 | 5日正收益率 |
|-------|--------|---------|------------|
| technical_trend | 40 | -0.26% | - |
| short_term_heat | 40 | -0.26% | - |
| rotation_analysis | 40 | -0.26% | - |
| risk_control | 40 | -0.26% | - |
| data_quality | 40 | -0.26% | - |
| market_context | 40 | -0.26% | - |
| narrative | 40 | -0.26% | - |
| persistence_strength | 40 | -0.26% | - |
| catalyst_event | 40 | -0.26% | - |

### risk_on

样本数: 450

| Agent | 样本数 | 5日均值 | 5日正收益率 |
|-------|--------|---------|------------|
| technical_trend | 50 | 3.39% | - |
| short_term_heat | 50 | 3.39% | - |
| rotation_analysis | 50 | 3.39% | - |
| risk_control | 50 | 3.39% | - |
| data_quality | 50 | 3.39% | - |
| market_context | 50 | 3.39% | - |
| narrative | 50 | 3.39% | - |
| persistence_strength | 50 | 3.39% | - |
| catalyst_event | 50 | 3.39% | - |

### weak_rebound

样本数: 270

| Agent | 样本数 | 5日均值 | 5日正收益率 |
|-------|--------|---------|------------|
| technical_trend | 30 | -0.87% | - |
| short_term_heat | 30 | -0.87% | - |
| rotation_analysis | 30 | -0.87% | - |
| risk_control | 30 | -0.87% | - |
| data_quality | 30 | -0.87% | - |
| market_context | 30 | -0.87% | - |
| narrative | 30 | -0.87% | - |
| persistence_strength | 30 | -0.87% | - |
| catalyst_event | 30 | -0.87% | - |

## 误判样本

### Positive False Signal

Agent vote=positive，但 forward_5d 为负。

| 日期 | 板块 | Agent | 5日收益 |
|------|------|-------|---------|
| 2026-06-22 | 工业金属 | risk_control | -12.18% |
| 2026-06-22 | 工业金属 | data_quality | -12.18% |
| 2026-06-22 | 工业金属 | market_context | -12.18% |
| 2026-06-22 | 能源金属 | risk_control | -9.70% |
| 2026-06-22 | 能源金属 | data_quality | -9.70% |
| 2026-06-22 | 能源金属 | market_context | -9.70% |
| 2026-06-04 | 煤炭开采加工 | rotation_analysis | -8.99% |
| 2026-06-04 | 煤炭开采加工 | risk_control | -8.99% |
| 2026-06-04 | 煤炭开采加工 | data_quality | -8.99% |
| 2026-06-02 | 工业金属 | risk_control | -8.80% |

### Negative Missed Signal

Agent vote=negative，但 forward_5d 为正。

| 日期 | 板块 | Agent | 5日收益 |
|------|------|-------|---------|
| 2026-06-16 | 非金属材料 | rotation_analysis | 12.48% |
| 2026-06-16 | 非金属材料 | market_context | 12.48% |
| 2026-06-15 | 电子化学品 | technical_trend | 12.16% |
| 2026-06-17 | 非金属材料 | market_context | 11.82% |
| 2026-06-15 | 小金属 | technical_trend | 10.47% |
| 2026-06-24 | 半导体 | market_context | 9.62% |
| 2026-06-09 | 电子化学品 | technical_trend | 9.57% |
| 2026-06-09 | 电子化学品 | rotation_analysis | 9.57% |
| 2026-06-10 | 电子化学品 | technical_trend | 9.50% |
| 2026-06-10 | 电子化学品 | short_term_heat | 9.50% |

### Neutral Missed Move

Agent vote=neutral，但 forward_5d 绝对值较大。

| 日期 | 板块 | Agent | 5日收益 |
|------|------|-------|---------|
| 2026-06-16 | 非金属材料 | technical_trend | 12.48% |
| 2026-06-16 | 非金属材料 | narrative | 12.48% |
| 2026-06-16 | 非金属材料 | persistence_strength | 12.48% |
| 2026-06-16 | 非金属材料 | catalyst_event | 12.48% |
| 2026-06-22 | 工业金属 | short_term_heat | -12.18% |
| 2026-06-22 | 工业金属 | narrative | -12.18% |
| 2026-06-22 | 工业金属 | persistence_strength | -12.18% |
| 2026-06-22 | 工业金属 | catalyst_event | -12.18% |
| 2026-06-15 | 电子化学品 | narrative | 12.16% |
| 2026-06-15 | 电子化学品 | persistence_strength | 12.16% |

## 后续优化建议

**高可靠性 Agent**: short_term_heat
- 这些 Agent 的 vote 与后续表现有较好的一致性，可继续保留

**低可靠性 Agent**: data_quality, risk_control, narrative, persistence_strength, catalyst_event
- 这些 Agent 的区分度不足，需要关注是否需要调整

**Phase 38 建议**: 基于以上分析，评估是否需要新增 PersistenceStrengthAgent。

---

*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不作为操作依据。*