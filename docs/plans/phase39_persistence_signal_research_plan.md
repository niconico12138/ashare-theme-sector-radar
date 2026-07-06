# Phase 39: Persistence Signal Research

## 本阶段目标

研究多日持续性信号是否对后续表现有解释力。

## 坚持原则

- 只做持续性信号研究
- 不新增 Agent
- 不修改生产规则
- 使用 Phase 36 research index 和历史 forward returns
- 目标是判断 Phase 40 是否值得新增 PersistenceStrengthAgent

## 持续性信号

1. top_watch_streak: 连续出现在 top_watch_names 的天数
2. label_persistence: 同一标签连续出现的天数
3. label_transition: 标签变化路径
4. ranking_score_trend: 分数趋势
5. opportunity_score_trend: 分数趋势
6. persistence x regime: 不同 regime 下的表现
7. persistence x short_term_heat: 与最佳 Agent 的叠加

## 输出

- reports/backtests/persistence_signals/analysis.json
- reports/backtests/persistence_signals/analysis.md
- Phase 40 新增 Agent 建议
