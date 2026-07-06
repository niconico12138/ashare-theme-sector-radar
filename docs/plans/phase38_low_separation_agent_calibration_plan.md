# Phase 38: Low-Separation Agent Calibration

## 本阶段目标

校准低区分度 Agent 的 vote 规则，让它们提供更有信息量的 positive / neutral / negative 信号。

## 坚持原则

- 只校准低区分度 Agent
- 目标是提升 vote 分布的信息量
- 不追求强行均衡分布
- 不修改总决策规则
- 需要用 Phase 37 作为基线对比

## 校准对象

1. RiskControlAgent: 100% positive → 根据风险状态分层
2. MarketContextAgent: 100% negative → 根据 regime 分层
3. DataQualityAgent: 97% positive → 根据数据质量分层
4. NarrativeAgent: 100% neutral → 添加 low_information_agent 标记

## 输出

- 修改 4 个 Agent 的 vote 逻辑
- 新增测试
- 重新运行 Agent Reliability 分析
