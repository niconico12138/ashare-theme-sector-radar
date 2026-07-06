# Phase 29: Agent Signal Calibration Audit

## 审计问题与答案

### 1. 为什么所有 vote 都是 neutral？

**根因**: 7个 L2 Agent（technical_trend, short_term_heat, rotation_analysis, risk_control, data_quality, market_context, narrative）的 `analyze()` 方法返回字典时，没有设置 `vote` 字段。Coordinator 的 `_convert_to_opinions` 读取 `view_dict.get("vote", "neutral")`，始终返回默认值 "neutral"。

**修复**: 为每个 L2 Agent 添加 `_determine_vote()` 方法，根据标签和分数确定投票方向。

### 2. 为什么 conflict 全部 has_conflict？

**根因**: ConflictDetectionAgent 的 `_detect_data_confidence_conflict` 方法检查 "数据质量不足但结论置信度高"，由于 data_limited 标签普遍存在且其他 Agent 置信度默认 0.8，该条件对所有样本触发。

**修复**: 移除 universal data-confidence 冲突，改为检查投票方向是否矛盾（如 positive_votes >= 3 且 data_vote == negative）。

### 3. 为什么 veto 全部 true？

**根因**: VetoRuleAgent 的第3条规则 `opportunity_score < 0.30` 触发 veto。由于 554/560 样本的 opportunity_score < 0.30，该规则对几乎所有样本触发。

**修复**: 移除 `opportunity_score < 0.30` veto。保留 data_quality < 0.3、risk_high/risk_extreme、data_unreliable 三个硬性条件。

### 4. low_signal_noise 为什么占比过高？

**根因**: ConsensusDecisionAgent 的标签决策链中，low_signal_noise 是 "opportunity_score < 0.35 + technical 非强" 的兜底标签。由于市场整体偏弱，大部分样本满足此条件。

**修复**: 收窄 low_signal_noise 触发条件（opportunity < 0.25 + heat弱 + risk非高），新增 early_repair_watch、data_limited_neutral、defensive_stable_watch 三个中间标签。

### 5. oversold_rebound_candidate 为什么表现不好？

**根因**: 原条件 `heat_moderate/active + opportunity < 0.35 + risk >= 0.45` 过于宽松，包含了大量无修复信号的样本。

**修复**: 收紧条件：heat_active/moderate + risk >= 0.55 + opportunity >= 0.30 + 非高风险 + 数据可用 + heat非fading。

### 6. ranking_score high 为什么为空？

**根因**: 公式中 low_signal_noise/weak_continuation/weak_or_avoid 乘以 0.50 惩罚，conflicted 乘以 0.65，加上市场整体偏弱，导致最高分不超过 0.40。

**修复**: 降低惩罚系数（low_signal_noise 0.70, weak_or_avoid 0.60, conflicted 0.75），增加加分项（multi_window_confirmed +0.08, trend_confirmed +0.06）。

### 7. opportunity_score high 为什么为空？

**根因**: opportunity_score 由 technical(0.30) + heat(0.25) + rotation(0.20) + market(0.15) + narrative(0.10) 加权，市场弱导致各维度分数低。

**修复**: 此为市场实际情况，不强行调高。通过降低 ranking_score 惩罚让分桶有样本。

### 8. 哪些规则应该调整，哪些不应调整？

**应调整**:
- L2 Agent 投票逻辑（当前缺失）
- VetoRuleAgent 的 opportunity_score veto（过度触发）
- ConflictDetectionAgent 的 data-confidence 冲突（universal trigger）
- ConsensusDecisionAgent 的 low_signal_noise 兜底（过于宽松）
- ranking_score 惩罚系数（过于保守）

**不应调整**:
- confidence_score 语义（仍为标签可信度）
- CLI 接口
- 数据获取逻辑
- 现有标签名称（只新增，不删除）
