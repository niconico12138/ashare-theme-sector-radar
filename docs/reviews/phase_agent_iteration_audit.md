# Phase A: Agent 组现状审计

**审计日期**: 2026-07-03  
**审计范围**: `theme_sector_radar/agents/sector_research/` 全部 20 个 .py 文件  
**审计目的**: 盘点 Agent 组当前状态，不修改代码

---

## 1. 当前 Agent 列表

### 1.1 架构概览

Agent 组采用 L1-L4 四层架构：

| 层级 | 角色 | Agent 数 |
|------|------|----------|
| L1 数据与证据层 | 数据准备、标准化 | 2 |
| L2 专项分析层 | 独立维度分析 | 8 |
| L3 冲突与一致性层 | 投票聚合、冲突检测、Veto、置信度校准 | 4 |
| L4 决策层 | 最终共识 | 1 |

协调器: `SectorResearchCoordinator` (coordinator.py)

### 1.2 Agent 清单

| # | Agent | 文件 | 层级 | 输出类型 | signal_profile | 参与投票 |
|---|-------|------|------|----------|----------------|----------|
| 1 | EvidenceExtractionAgent | evidence_extraction_agent.py | L1 | AgentOpinion | — | 未参与 |
| 2 | SignalNormalizationAgent | signal_normalization_agent.py | L1 | List[AgentOpinion] | — | 未参与 |
| 3 | TechnicalTrendAgent | technical_trend_agent.py | L2 | Dict → _convert_to_opinions | broad_signal | ✅ |
| 4 | ShortTermHeatAgent | short_term_heat_agent.py | L2 | Dict → _convert_to_opinions | broad_signal | ✅ |
| 5 | RotationAnalysisAgent | rotation_analysis_agent.py | L2 | Dict → _convert_to_opinions | broad_signal | ✅ |
| 6 | CapitalVolumeAgent | capital_volume_agent.py | L2 | AgentOpinion | broad_signal | ❌ 未调用 |
| 7 | RiskControlAgent | risk_control_agent.py | L2 | Dict → _convert_to_opinions | defensive_filter | ✅ |
| 8 | DataQualityAgent | data_quality_agent.py | L2 | Dict → _convert_to_opinions | defensive_filter | ✅ |
| 9 | MarketContextAgent | market_context_agent.py | L2 | Dict → _convert_to_opinions | broad_signal | ✅ |
| 10 | NarrativeAgent | narrative_agent.py | L2 | Dict → _convert_to_opinions | low_information | ✅ (neutral) |
| 11 | PersistenceStrengthAgent | persistence_strength_agent.py | L2 | AgentOpinion (直接) | sparse_high_precision | ✅ |
| 12 | CatalystEventAgent | catalyst_event_agent.py | L2 | AgentOpinion (直接) | sparse_event_signal | ❌ (report_only) |
| 13 | AgentVoteAggregator | agent_vote_aggregator.py | L3 | AgentOpinion | — | — |
| 14 | ConflictDetectionAgent | conflict_detection_agent.py | L3 | AgentOpinion | — | — |
| 15 | VetoRuleAgent | veto_rule_agent.py | L3 | AgentOpinion | — | — |
| 16 | ConfidenceCalibrationAgent | confidence_calibration_agent.py | L3 | AgentOpinion | — | — |
| 17 | ConsensusDecisionAgent | consensus_decision_agent.py | L4 | Dict | — | — |

额外辅助: `MarketRegimeContext` (market_regime_context.py) — 解释层，不参与决策。

---

## 2. 每个 Agent 的 Vote 规则

### 2.1 TechnicalTrendAgent
| 条件 | Vote |
|------|------|
| trend_confirmed + consensus_score >= 50 | positive |
| trend_forming / trend_short_active / trend_long_stable | neutral |
| trend_weak / trend_unreliable | negative |
| 其他 (trend_conflicted / trend_neutral 等) | neutral |

**语义**: 技术面趋势是否确认。只有多窗口确认+共识分数高才 positive。设计合理。

### 2.2 ShortTermHeatAgent
| 条件 | Vote |
|------|------|
| heat_active (burst >= 65) | positive |
| heat_moderate (50-65) | neutral |
| heat_fading / heat_weak (< 50) | negative |

**语义**: 短线爆发强度。阈值清晰，无灰色地带。

### 2.3 RotationAnalysisAgent
| 条件 | Vote |
|------|------|
| rotation_rising / rotation_improving | positive |
| rotation_neutral | neutral |
| rotation_weakening / rotation_lagging / rotation_weak | negative |

**语义**: 轮动阶段。正向=领先/改善，负向=弱化/落后。

### 2.4 RiskControlAgent
| 条件 | Vote |
|------|------|
| risk_high / risk_extreme | negative |
| 有风险标志 | negative |
| veto 触发 | negative |
| conflict_level == high | negative |
| risk_low + score >= 0.7 | positive |
| 其他 | neutral |

**语义**: 防守型 Agent，主要输出负向信号。positive 仅在风险极低时出现。正确行为。

### 2.5 DataQualityAgent
| 条件 | Vote |
|------|------|
| data_unreliable | negative |
| trend_window_status != ok | negative |
| coverage < 0.5 | negative |
| 有关键警告 | negative |
| data_reliable + coverage >= 0.9 | positive |
| data_usable + coverage >= 0.7 | neutral |
| data_limited | neutral |

**语义**: 防守型 Agent，过滤数据质量差的板块。

### 2.6 MarketContextAgent
| 条件 | Vote |
|------|------|
| outperforming_benchmark | positive |
| risk_on | positive |
| risk_off | negative |
| broad_falling | negative |
| market_cold | negative |
| choppy_market + neutral | neutral |
| choppy_market + underperforming | negative |
| weak_rebound | neutral |
| 其他 | neutral |

**语义**: 综合市场环境。使用 regime 信息较多，逻辑较复杂。

### 2.7 NarrativeAgent
| 条件 | Vote |
|------|------|
| 所有情况 | neutral |

**语义**: 纯规则映射，永远 neutral。标记为 low_information_agent=True。

### 2.8 PersistenceStrengthAgent
| 条件 | Vote |
|------|------|
| persistence_confirmed | positive |
| persistence_building + score >= 0.55 | positive |
| persistence_deteriorating | negative |
| 其他 | neutral |

**语义**: sparse_high_precision，基于多日 timeline 判断信号持续性。数据不足时 confidence=0.3。

### 2.9 CatalystEventAgent
| 条件 | Vote |
|------|------|
| 所有情况 | neutral |

**语义**: report-only，永远 neutral，永远不 veto。metadata.decision_impact = "report_only"。

---

## 3. Signal Profile 分配

| Agent | signal_profile | 说明 |
|-------|----------------|------|
| technical_trend | broad_signal | 高覆盖，大部分样本都有投票 |
| short_term_heat | broad_signal | 高覆盖 |
| rotation_analysis | broad_signal | 高覆盖 |
| risk_control | defensive_filter | 主要识别风险 |
| data_quality | defensive_filter | 主要识别数据问题 |
| market_context | broad_signal | 高覆盖 |
| narrative | low_information | 当前数据不足以产生有效信号 |
| capital_volume | broad_signal | ⚠️ 已定义但未在管线中使用 |
| persistence_strength | sparse_high_precision | 少数样本出手但质量高 |
| catalyst_event | sparse_event_signal | 低覆盖事件驱动信号 |

---

## 4. AgentVoteAggregator 报告排除检查

✅ **正确排除 report-only Agent**

```python
decision_opinions = [
    o for o in opinions
    if o.metadata.get("decision_impact") != "report_only"
]
```

CatalystEventAgent 设置了 `metadata.decision_impact = "report_only"`，会被正确排除。

✅ **PersistenceStrengthAgent 正确参与投票**（虽然 sparse，但不是 report-only）

⚠️ **NarrativeAgent 未被排除**：它总是 neutral，标记了 `low_information_agent: True`，但这个标记在 AgentOpinion 层面没有被 vote aggregator 识别。low_information 的 neutral vote 会稀释正向/负向投票比例。

---

## 5. ConsensusDecisionAgent 依赖分析

### 5.1 输入字段

ConsensusDecisionAgent 接收 7 个维度视图：
- technical_view
- heat_view
- rotation_view
- risk_view
- data_quality_view
- market_context_view
- narrative_view

**不直接依赖**: persistence_strength, catalyst_event (这两个通过 vote/报告间接影响)

### 5.2 标签判定逻辑（15 条规则，按优先级）

| 优先级 | 标签 | 关键条件 |
|--------|------|----------|
| 1 | insufficient_data | data_unreliable |
| 2 | conflicted | trend_conflicted + 无强热度/轮动 |
| 3 | strong_consensus | trend_confirmed + heat_active/moderate + risk_low/moderate + opportunity >= 0.65 |
| 4 | trend_confirmed | trend_confirmed (不满足 strong 条件) |
| 5 | trend_confirmed_but_strength_limited | trend_forming |
| 6 | short_term_active_unconfirmed | heat_active + trend_weak/unreliable |
| 7 | rotation_candidate | rotation_rising + 非弱趋势 + opportunity >= 0.50 + risk_control >= 0.55 |
| 8 | defensive_watch | 医药/金融防御属性 + risk_low/moderate + 技术分 >= 0.35 |
| 9 | oversold_rebound_candidate | heat_active/moderate + risk_control >= 0.55 + opportunity >= 0.30 |
| 10 | early_repair_watch | trend_weak/unreliable + heat_moderate/active + risk_control >= 0.55 |
| 11 | weak_continuation | trend_weak/unreliable + heat_weak/fading + opportunity < 0.30 + risk < 0.65 |
| 12 | data_limited_neutral | data_limited + risk_low/moderate + opportunity < 0.35 |
| 13 | defensive_stable_watch | risk_low + heat_weak/fading + trend_neutral/weak + opportunity < 0.35 |
| 14 | low_signal_noise | opportunity < 0.25 + 弱趋势 + 弱热度 |
| 15 | weak_or_avoid | 默认 |

**潜在重叠**:
- Rule 6 (short_term_active_unconfirmed) vs Rule 9 (oversold_rebound_candidate): 
  - Rule 6 匹配 heat_active + weak trend → 无条件截断
  - Rule 9 匹配 heat_active/moderate + 多个条件
  - 语义区别: "短线活跃但未确认" vs "弱势修复+有支撑"，逻辑上可区分

### 5.3 四个分数

| 分数 | 计算方式 | 语义 |
|------|----------|------|
| evidence_score | data_quality * 0.7 + market_context * 0.3 | 证据充分度 |
| opportunity_score | technical * 0.30 + heat * 0.25 + rotation * 0.20 + market * 0.15 + narrative * 0.10 | 正向观察强度 |
| risk_control_score | 直接取 dimension_scores["risk"] | 风险可控度 |
| confidence_score | data_quality * 0.5 + 一致性加分 + 热度加分 + 维度一致性加分 | 标签可信度（≠机会强度）|
| ranking_score | opportunity * 0.45 + evidence * 0.20 + risk * 0.25 + market * 0.10 + 惩罚/加分项 | 排序辅助 |

**语义清晰度**: ✅ opportunity_score 是正向观察强度，confidence_score 是标签可信度，两者不混用。

---

## 6. 发现的问题

### P0 — 必须修复

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 1 | **CapitalVolumeAgent 已实例化但未在管线中调用** | coordinator.py L51, L261-328 | agent 定义了 broad_signal 但从未参与分析和投票 |
| 2 | **PersistenceStrengthAgent 接收过期的 `result` 变量** | coordinator.py L302-303 | `result if 'result' in dir() else {}` — 使用 dir() 检查局部变量是反模式，且 result 可能指上一轮迭代的旧数据 |
| 3 | **_convert_to_opinions() 硬编码 confidence=0.8** | coordinator.py L202 | 7 个通过 dict→opinion 转换的 Agent 全部使用 0.8 置信度，丧失了区分能力 |

### P1 — 建议修复

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 4 | **EvidenceExtractionAgent 和 SignalNormalizationAgent 已实例化但未在管线中调用** | coordinator.py L44-45 | L1 层 Agent 实际上是死代码 |
| 5 | **NarrativeAgent 的 low_information 标记不被 vote aggregator 识别** | narrative_agent.py L110, agent_vote_aggregator.py | neutral vote 稀释正向/负向比例 |
| 6 | **_convert_to_opinions() 不设置 veto、metadata、signal_profile** | coordinator.py L197-206 | 转换后的 AgentOpinion 缺少关键元数据 |
| 7 | **AgentOpinion 没有 signal_profile 和 decision_impact 字段** | opinion.py | signal_profile 只在 opinion.py 的 AGENT_SIGNAL_PROFILES dict 中定义，不在 AgentOpinion dataclass 上 |
| 8 | **capital_volume 的 signal_profile 映射存在但 Agent 未使用** | opinion.py L83 | 误导性映射 |

### P2 — 观察/文档不足

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 9 | **ConsensusDecisionAgent 的 ranking_score 与 scoring 层的 sector_selection_score 是两个独立分数** | consensus_decision_agent.py, sector_composite_score.py | 用户可能混淆两个 ranking 分数 |
| 10 | **MarketContextAgent 的 vote 逻辑较复杂，使用了 regime 信息** | market_context_agent.py L142-194 | 与其他 Agent 相比逻辑分支较多，维护成本高 |
| 11 | **15 条标签规则的优先级关系未文档化** | consensus_decision_agent.py L304-418 | 新增规则时容易产生冲突 |

---

## 7. 优先级排序

1. **P0-2 (result 变量)**: 功能正确性问题，可能传入错误数据
2. **P0-3 (confidence 硬编码)**: 影响置信度校准的准确性
3. **P0-1 (CapitalVolume 未使用)**: 死代码清理，如果不需要就删除实例化
4. **P1-5 (low_information 稀释)**: 影响投票比例准确性
5. **P1-6 (convert_to_opinions 缺字段)**: 影响报告可读性和回测分析
6. **P1-7 (AgentOpinion 缺字段)**: 影响可扩展性
7. **P1-4 (L1 死代码)**: 清理性问题
8. **P1-8 (capital_volume profile 误导)**: 文档一致性
9. **P2-9/10/11**: 文档和可维护性

---

## 8. 不建议修改的部分

1. **ConsensusDecisionAgent 的标签判定逻辑** — 15 条规则经过多次迭代调优（phase25/29/38/57/59），改动风险大
2. **CatalystEventAgent 的 report-only 设计** — 正确隔离了事件驱动信号和决策层
3. **MarketRegimeContext 的解释层定位** — 正确的架构分离
4. **PersistenceStrengthAgent 的 sparse_high_precision 设计** — 只在有足够 timeline 数据时出手，设计合理
5. **VetoRuleAgent 的 veto 规则** — 数据不足/高风险 veto 是合理的防守机制
6. **ConflictDetectionAgent 的冲突检测逻辑** — 趋势-热度、轮动-趋势、风险-机会三类冲突检测覆盖全面
7. **评分层 (sector_composite_score.py)** — 不在本次迭代范围，评分公式稳定

---

## 9. 下一步建议

1. Phase B: 修复 P0-2 (result 变量)、P0-3 (confidence 硬编码)、补充 AgentOpinion 缺失字段
2. Phase C: 校准各 Agent vote 语义，确认 low_information Agent 是否应排除投票
3. Phase D: 明确 Agent 层与 scoring 层的边界，文档化两个 ranking_score 的区别
4. Phase E: 报告可读性优化，限制 Top 10
5. Phase F: 回测验证修改效果
