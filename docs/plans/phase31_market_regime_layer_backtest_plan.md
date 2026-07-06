# Phase 31: Market Regime Layer Backtest Plan

## 本阶段目标

市场状态分层验证，不直接修改生产标签规则。

验证不同 Agent 标签在不同市场环境下的表现差异，判断：
1. oversold_rebound_candidate 是否只在特定市场状态下有效
2. low_signal_noise 中的 missed_opportunity 是否集中在市场弱转强阶段
3. conflicted / weak_or_avoid / low_signal_noise 是否受市场状态显著影响
4. 是否需要后续新增 Market Regime Agent

## 坚持原则

- 所有市场状态必须 no-lookahead，只使用 signal_date 及之前数据
- 不直接修改生产标签规则
- 输出分析报告和建议，不追求强行优化结果
- 所有结论用"观察、复盘、验证、候选、信号"表达

## Market Regime 维度

1. benchmark_trend: 基准趋势（uptrend/downtrend/sideways/unknown）
2. market_temperature_regime: 市场温度（hot/warm/cool/cold/unknown）
3. breadth_regime: 广度（broad_rising/narrow_rising/broad_falling/mixed/unknown）
4. volatility_regime: 波动率（high/normal/low/unknown）
5. regime_composite_label: 综合标签（risk_on/risk_off/rotation_market/weak_rebound/choppy/unknown）

## 输出

- reports/backtests/market_regime/2026-06-01_to_2026-06-29/market_regime_analysis.json
- reports/backtests/market_regime/2026-06-01_to_2026-06-29/market_regime_analysis.md
