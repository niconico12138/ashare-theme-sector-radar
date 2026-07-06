# Phase B: Agent 输出结构增强 — 完成总结

**日期**: 2026-07-03

## 修改文件

| 文件 | 修改内容 |
|------|----------|
| `opinion.py` | AgentOpinion 新增 `signal_profile` 和 `decision_impact` 字段；to_dict() 输出包含新字段 |
| `coordinator.py` | 修复 P0 三处：(1) 删除未使用的 EvidenceExtractionAgent/SignalNormalizationAgent/CapitalVolumeAgent；(2) 修复 PersistenceStrengthAgent 传入过期 result 变量；(3) _convert_to_opinions() 不再硬编码 confidence=0.8，改为从 view_dict 提取 + signal_profile 默认值 |
| `agent_vote_aggregator.py` | 排除逻辑扩展：同时排除 report_only 和 excluded (low_information) Agent |
| `catalyst_event_agent.py` | 3 处 return 语句均增加 `decision_impact="report_only"` 字段 |
| `tests/test_signal_profile.py` | 更新 expected_agents 列表：移除 capital_volume，新增 catalyst_event |

## 修复的 P0 问题

1. **P0-2 (result 变量)**: PersistenceStrengthAgent 不再接收过期的 `result` 变量，改为传入空 dict `{}`
2. **P0-3 (confidence 硬编码)**: _convert_to_opinions() 现在从 view_dict 提取 confidence，低信息 Agent 默认 0.3，其他默认 0.7
3. **P0-1 (CapitalVolumeAgent 死代码)**: 已从 coordinator.py 中删除实例化和 import

## 新增字段语义

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| signal_profile | str | "" | 从 AGENT_SIGNAL_PROFILES 映射，标识 Agent 信号类型 |
| decision_impact | str | "participates" | "participates" / "report_only" / "excluded" |

## 决策影响分类

| Agent | decision_impact | 原因 |
|-------|----------------|------|
| narrative | excluded | low_information，投票稀释正向/负向比例 |
| catalyst_event | report_only | 仅用于复盘解释 |
| 其他 7 个 L2 Agent | participates | 正常参与投票 |
| persistence_strength | participates | sparse_high_precision，有数据时出手 |

## 测试结果

34 passed (vote_aggregator 7 + signal_profile 9 + persistence 10 + catalyst 8)

## 未修改的部分

- ConsensusDecisionAgent 标签判定逻辑
- 评分层 sector_composite_score.py
- 报告生成 sector_research_report.py（Phase E 处理）
- 所有 Agent 的内部分析逻辑
