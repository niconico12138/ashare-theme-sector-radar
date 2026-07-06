# Phase 41: PersistenceStrengthAgent Backtest and Calibration

## 本阶段目标

校准 PersistenceStrengthAgent，提升其区分度。

## 坚持原则

- 只校准 PersistenceStrengthAgent
- 不修改最终决策逻辑
- 先审计再校准
- 校准必须有测试和回测对比
- 避免过拟合，样本少时保持保守

## 校准方向

1. 长 streak (>=5) 不应被 flat trend 过度压低
2. 降低 persistence_building 的 vote 阈值
3. 增加有利 label_transition
4. 保留 conflict/risk penalty

## 输出

- 修改 persistence_strength_agent.py
- 更新测试
- 重新运行可靠性分析
