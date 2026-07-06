# Phase 29: Agent Signal Calibration Plan

## Phase 28 问题摘要

1. **All votes neutral**: Agents return dictionaries without `vote` field. Coordinator defaults to "neutral".
2. **All conflicts trigger**: data-confidence conflict fires universally (data_limited + any high confidence).
3. **All vetoes trigger**: `opportunity_score < 0.30` veto hits 554/560 samples.
4. **low_signal_noise dominates**: 444/560 (79%) samples use this fallback label.
5. **oversold_rebound_candidate表现差**: 5日均收益 -0.77%, 无修复优势。
6. **ranking_score/opportunity_score high桶为空**: 分数过于保守。
7. **Agent层无区分度**: 所有Agent表现一致，投票无差异。

## 校准目标

- 让 Agent 投票产生 positive/neutral/negative 分布
- 让 conflict 只在明显矛盾时触发
- 让 veto 只用于硬性降权
- 拆分 low_signal_noise，提升标签解释力
- 收紧 oversold_rebound_candidate
- 让 ranking_score/opportunity_score 分桶有样本

## 不做事项

- 不过拟合回测结果
- 不删除任何现有标签
- 不修改 confidence_score 语义（仍为标签可信度）
- 不新增外部依赖
- 不修改 CLI 接口

## 校准对象

1. 7个 L2 Agent: 添加 vote 字段
2. VetoRuleAgent: 移除 opportunity_score < 0.30 veto
3. ConflictDetectionAgent: 收紧冲突规则
4. ConsensusDecisionAgent: 拆分标签 + 收紧 oversold_rebound
5. ranking_score 公式: 调整权重和惩罚

## 验证方式

- 重新生成 2026-06-01 到 2026-06-29 报告
- 重新跑 sector research backtest 和 agent layer backtest
- 与 Phase 28 结果对比
- 检查 vote/conflict/veto/label 分布

## 回滚标准

- 如果校准后回测结果显著变差，回滚到 Phase 28 版本
- 如果新标签导致测试失败，修复测试而非回滚
