# Agent 可靠性仪表盘

> **免责声明**: 本报告仅用于板块研究、观察和复盘，不作为操作依据。

## 总览

- **日期范围**: 2026-06-25 ~ 2026-06-29
- **样本数量**: 450
- **Agent 数量**: 9

## Agent 可靠性排名

| Agent | Layer | Signal Profile | Decision Impact | 样本数 | 正向票 | 负向票 | 可靠性评分 | 可靠性标签 | 诊断 |
|-------|-------|----------------|-----------------|--------|--------|--------|------------|------------|------|
| rotation_analysis | L2_specialized | broad_signal | participates | 50 | 11 | 39 | 0.31 | low_reliability | negative vote has higher forward returns |
| technical_trend | L2_specialized | broad_signal | participates | 50 | 1 | 32 | 0.22 | low_reliability | insufficient data for diagnosis |
| short_term_heat | L2_specialized | broad_signal | participates | 50 | 1 | 40 | 0.19 | low_reliability | insufficient data for diagnosis |
| data_quality | L1_data_evidence | defensive_filter | participates | 50 | 44 | 0 | 0.17 | low_reliability | insufficient data for diagnosis |
| risk_control | L2_specialized | defensive_filter | participates | 50 | 50 | 0 | 0.15 | low_reliability | insufficient data for diagnosis |
| market_context | L2_specialized | broad_signal | participates | 50 | 0 | 50 | 0.15 | low_reliability | insufficient data for diagnosis |
| narrative | L2_specialized | low_information | participates | 50 | 0 | 0 | 0.15 | low_reliability | insufficient data for diagnosis |
| persistence_strength | L2_specialized | sparse_high_precision | participates | 50 | 1 | 0 | 0.15 | low_reliability | insufficient data for diagnosis |
| catalyst_event | L2_specialized | sparse_event_signal | participates | 50 | 0 | 0 | 0.15 | low_reliability | insufficient data for diagnosis |

## Signal Profile 说明

| Profile | 说明 |
|---------|------|
| broad_signal | 高覆盖普通信号，大部分样本都有投票，区分度中等 |
| sparse_high_precision | 低覆盖高命中信号，少数样本出手但质量很高 |
| sparse_event_signal | 低覆盖事件驱动信号，需后续验证命中率 |
| low_information | 低信息 Agent，当前数据不足以产生有效信号 |
| defensive_filter | 防守过滤 Agent，主要识别风险和数据问题 |

## Vote 表现

### rotation_analysis

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| positive | 11 | 0.00% | 0.11% | -0.51% | 50% |
| negative | 39 | 0.00% | 1.22% | 0.85% | 67% |

### technical_trend

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| positive | 1 | 0.00% | 1.65% | - | - |
| neutral | 17 | 0.00% | 1.27% | -0.12% | 60% |
| negative | 32 | 0.00% | 0.73% | 0.72% | 60% |

### short_term_heat

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| positive | 1 | 0.00% | 2.49% | - | - |
| neutral | 9 | 0.00% | 1.18% | 0.11% | 50% |
| negative | 40 | 0.00% | 0.78% | 0.43% | 67% |

### data_quality

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| positive | 44 | 0.00% | 0.75% | 0.30% | 60% |
| neutral | 6 | 0.00% | 2.35% | - | - |

### risk_control

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| positive | 50 | 0.00% | 0.96% | 0.30% | 60% |

### market_context

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| negative | 50 | 0.00% | 0.96% | 0.30% | 60% |

### narrative

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| neutral | 50 | 0.00% | 0.96% | 0.30% | 60% |

### persistence_strength

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| positive | 1 | 0.00% | 1.65% | - | - |
| neutral | 49 | 0.00% | 0.94% | 0.30% | 60% |

### catalyst_event

| Vote | 样本数 | 1日均值 | 3日均值 | 5日均值 | 5日正收益率 |
|------|--------|---------|---------|---------|------------|
| neutral | 50 | 0.00% | 0.96% | 0.30% | 60% |

## Market Regime 分层

### choppy_market

样本数: 90

| Agent | 样本数 | 5日均值 | 5日正收益率 |
|-------|--------|---------|------------|
| technical_trend | 10 | 0.30% | - |
| short_term_heat | 10 | 0.30% | - |
| rotation_analysis | 10 | 0.30% | - |
| risk_control | 10 | 0.30% | - |
| data_quality | 10 | 0.30% | - |
| market_context | 10 | 0.30% | - |
| narrative | 10 | 0.30% | - |
| persistence_strength | 10 | 0.30% | - |
| catalyst_event | 10 | 0.30% | - |

### risk_off

样本数: 270

| Agent | 样本数 | 5日均值 | 5日正收益率 |
|-------|--------|---------|------------|
| technical_trend | 30 | - | - |
| short_term_heat | 30 | - | - |
| rotation_analysis | 30 | - | - |
| risk_control | 30 | - | - |
| data_quality | 30 | - | - |
| market_context | 30 | - | - |
| narrative | 30 | - | - |
| persistence_strength | 30 | - | - |
| catalyst_event | 30 | - | - |

### weak_rebound

样本数: 90

| Agent | 样本数 | 5日均值 | 5日正收益率 |
|-------|--------|---------|------------|
| technical_trend | 10 | - | - |
| short_term_heat | 10 | - | - |
| rotation_analysis | 10 | - | - |
| risk_control | 10 | - | - |
| data_quality | 10 | - | - |
| market_context | 10 | - | - |
| narrative | 10 | - | - |
| persistence_strength | 10 | - | - |
| catalyst_event | 10 | - | - |

## 误判样本

### Positive False Signal

Agent vote=positive，但 forward_5d 为负。

| 日期 | 板块 | Agent | 5日收益 |
|------|------|-------|---------|
| 2026-06-25 | 元件 | rotation_analysis | -6.75% |
| 2026-06-25 | 元件 | risk_control | -6.75% |
| 2026-06-25 | 元件 | data_quality | -6.75% |
| 2026-06-25 | 其他电子 | rotation_analysis | -3.69% |
| 2026-06-25 | 其他电子 | risk_control | -3.69% |
| 2026-06-25 | 其他电子 | data_quality | -3.69% |

### Negative Missed Signal

Agent vote=negative，但 forward_5d 为正。

| 日期 | 板块 | Agent | 5日收益 |
|------|------|-------|---------|
| 2026-06-25 | 半导体 | market_context | 4.71% |
| 2026-06-25 | 电子化学品 | market_context | 3.69% |

### Neutral Missed Move

Agent vote=neutral，但 forward_5d 绝对值较大。

| 日期 | 板块 | Agent | 5日收益 |
|------|------|-------|---------|
| 2026-06-25 | 元件 | technical_trend | -6.75% |
| 2026-06-25 | 元件 | short_term_heat | -6.75% |
| 2026-06-25 | 元件 | narrative | -6.75% |
| 2026-06-25 | 元件 | persistence_strength | -6.75% |
| 2026-06-25 | 元件 | catalyst_event | -6.75% |

## 后续优化建议

**低可靠性 Agent**: rotation_analysis, technical_trend, short_term_heat, data_quality, risk_control, market_context, narrative, persistence_strength, catalyst_event
- 这些 Agent 的区分度不足，需要关注是否需要调整

**下一步建议**: 基于以上分析，持续跟踪 Agent 可靠性变化，关注 sparse_high_precision Agent 的命中率。

---

*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不作为操作依据。*