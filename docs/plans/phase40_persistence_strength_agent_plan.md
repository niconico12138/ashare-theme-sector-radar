# Phase 40: PersistenceStrengthAgent Implementation

## 本阶段目标

新增 PersistenceStrengthAgent，分析板块多日持续性信号。

## 坚持原则

- 新 Agent 是"持续性观察员"，不是裁判
- 只作为 L2_specialized Agent 接入
- 不触发 veto
- 不修改 ConsensusDecisionAgent 标签规则
- 不改变 ranking_score / opportunity_score / confidence_score
- 初期以解释和 vote 为主

## Agent 设计

- agent_id: persistence_strength
- layer: L2_specialized
- 输入: sector_name, as_of_date, current_result, sector_timeline, daily_summary, research_index
- 输出: persistence_label, score, confidence, vote, evidence, warnings

## Persistence Labels

1. persistence_confirmed: streak >= 3, trend rising
2. persistence_building: streak == 2, or favorable transition
3. persistence_weak: streak <= 1, flat/falling
4. persistence_deteriorating: falling trends, risk/conflict
5. persistence_unknown: insufficient data

## 输出

- 新增 persistence_strength_agent.py
- 集成到 coordinator
- 更新报告展示
- 新增测试
