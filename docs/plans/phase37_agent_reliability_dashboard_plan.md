# Phase 37: Agent Reliability Dashboard

## 本阶段目标

建立 Agent 可靠性仪表盘，评估每个 Agent 的表现。

## 坚持原则

- 只做可靠性评估
- 不修改 Agent 决策逻辑
- 不新增 Agent
- 不调整 vote / veto / consensus 规则
- 输出结果只用于后续分析和设计

## 分析内容

1. 每个 Agent 的 vote 与后续表现是否一致
2. 每个 Agent 在不同 market_regime 下是否表现不同
3. 哪些 Agent 经常产生有效正向/负向信号
4. 哪些 Agent 区分度不足
5. 误判类型识别

## 输出

- reports/backtests/agent_reliability/agent_reliability.json
- reports/backtests/agent_reliability/agent_reliability.md
