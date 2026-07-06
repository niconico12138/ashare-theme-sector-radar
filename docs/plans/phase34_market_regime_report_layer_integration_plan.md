# Phase 34: Market Regime Report Layer Integration

## 本阶段目标

将 market_regime 信息接入 sector_research 报告，作为解释层展示。

## 坚持原则

- 不参与 vote
- 不触发 veto
- 不改变 consensus_label
- 不改变 ranking_score / opportunity_score / confidence_score
- 不修改 ConsensusDecisionAgent 生产决策规则
- 继续坚持 no-lookahead

## 设计

新增 `market_regime_context.py` 模块，为每个 research result 生成 regime 解释信息：
- `market_regime`: regime 各维度状态
- `regime_interpretation`: 人类可读的 regime 解释

在 coordinator 的 `research_sectors` 方法末尾注入 regime context。

## 输出

- sector_research.json 中新增 `market_regime` 和 `regime_interpretation` 字段
- sector_research.md 中新增"市场状态"章节
