# Phase 33: Market Regime Revalidation and Agent Integration Proposal

## 本阶段目标

在 Phase 32 增强后的 replay daily 基础上，重新跑完整历史链路，产出正式评估：
1. 增强后的 market_regime 是否稳定改善解释力
2. Agent 标签在不同 regime 下是否有稳定差异
3. 是否建议新增 MarketRegimeAgent
4. 如果建议新增，应先作为"解释层 Agent"还是进入 ConsensusDecisionAgent 决策层

## 坚持原则

- 不直接改生产决策
- 使用 Phase 32 增强后的 replay daily
- 必须做 no-lookahead 检查
- 最终输出"是否接入 Market Regime Agent"的建议
- 所有结论用"观察、复盘、验证、候选、信号"表达

## 执行链路

1. replay daily (refresh)
2. generate research range (refresh)
3. sector research backtest
4. agent layer backtest
5. market regime analysis
6. opportunity rebound analysis
7. 交叉验证 regime x label
8. 产出正式建议

## 输出

- docs/plans/phase33_market_regime_revalidation_plan.md
- docs/reviews/phase33_market_regime_revalidation_validation.md
