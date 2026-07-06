# Phase 45: CatalystEventAgent Report-Only Integration

## 本阶段目标

新增 CatalystEventAgent，让 sector_research 报告可以展示外部催化事件，但不让事件影响当前评分、标签、投票、Veto 或排序。

## 坚持原则

- 只做 report-only 接入
- 外部事件仅用于复盘解释
- 不参与当前评分和标签决策
- 不触发 veto
- 后续 Phase 46 再做回测验证

## Agent 设计

- agent_id: catalyst_event
- layer: L2_specialized
- signal_profile: sparse_event_signal
- decision_impact: report_only
- vote: 永远 neutral
- veto: 永远 False

## 输出

- 新增 catalyst_event_agent.py
- 集成到 coordinator
- 更新报告展示
- 新增测试
