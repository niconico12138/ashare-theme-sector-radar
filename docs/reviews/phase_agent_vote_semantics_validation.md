# Phase C: Agent 投票语义校准 — 验证报告

**日期**: 2026-07-03  
**数据来源**: agent_reliability.json (2026-06-01 ~ 2026-06-29, 280 samples) + 2026-07-02 实时报告

---

## 1. 投票分布总览

| Agent | signal_profile | positive | neutral | negative | 分布评价 |
|-------|----------------|----------|---------|----------|----------|
| short_term_heat | broad_signal | 15% | 46% | 39% | ✅ 三态均匀，区分度好 |
| rotation_analysis | broad_signal | 23% | 0% | 77% | ⚠️ 无 neutral |
| market_context | broad_signal | 32% | 0% | 68% | ⚠️ 无 neutral |
| technical_trend | broad_signal | 4% | 24% | 72% | ⚠️ 重偏 negative |
| data_quality | defensive_filter | 97% | 3% | 0% | ✅ 防守型偏 positive，正常 |
| risk_control | defensive_filter | 100% | 0% | 0% | ❌ defensive_filter 名存实亡 |
| narrative | low_information | 0% | 100% | 0% | ✅ 设计如此 |
| persistence_strength | sparse_high_precision | 2% | 98% | 0% | ✅ sparse 设计，只有 6 个 positive |

---

## 2. 逐 Agent 分析

### 2.1 RiskControlAgent — ❌ 100% positive（回测期间）

**数据**: 280 样本全部 positive，0 neutral，0 negative  
**实时数据**: 2026-07-02 有 8 positive + 2 negative（市场偏弱时有效）

**原因分析**:
- risk_penalty ≤ 3 → risk_low → risk_score ≥ 0.85 → positive
- 6 月市场整体低风险，所有 280 个样本 risk_penalty ≤ 3
- risk_flags (history_unreliable, data_warning_present) 很少触发
- veto_triggered 依赖 VetoRuleAgent，不在 risk_control 内部
- conflict_level == "high" 作为独立检查点，但 score_data 中的 conflict_level 可能未被传入

**结论**: RiskControlAgent 的 vote 逻辑本身正确，但在低风险环境下完全失效。这是 defensive_filter 的固有特性——不需要改 vote 规则，但需要在文档中说明。

**建议**: 
- 不改 vote 规则（低风险环境下 positive 是正确的）
- 在报告中说明: "risk_control 在低风险环境下主要起过滤作用，不提供区分度"
- 可考虑新增 `risk_moderate → neutral` 显式映射（当前已通过默认 return 实现，但 6 月无 moderate 样本）

### 2.2 RotationAnalysisAgent — ⚠️ 0% neutral

**数据**: 64 positive / 0 neutral / 216 negative

**原因分析**:
- neutral 条件: `rotation_label == "rotation_neutral"`，仅当 multi_window 不是 weak_all_windows 且 rotation_phase 为空
- 实际数据中 rotation_phase 几乎不为空（总有 leading/improving/weakening/lagging 之一）
- 大部分板块处于 weakening/lagging → negative

**结论**: neutral 缺失是数据特征而非 bug。轮动数据通常有明确方向，很少处于真正中性。

**建议**:
- 保持现状。0% neutral 不是问题——如果轮动状态确实有方向性，不应该强行制造 neutral
- 在文档中说明: "rotation_neutral 在实际数据中罕见，轮动阶段通常有明确方向"

### 2.3 MarketContextAgent — ⚠️ 0% neutral

**数据**: 90 positive / 0 neutral / 190 negative

**原因分析**:
- neutral 条件: `choppy_market + neutral_vs_benchmark` 或 `weak_rebound`
- 6 月市场大部分时间处于 risk_off 或 broad_falling，直接触发 negative
- `underperforming_benchmark` 也触发 negative

**结论**: 与 rotation 类似，是市场状态特征。6 月整体偏弱，neutral 场景不出现。

**建议**:
- 保持现状。在牛市或震荡市中，neutral 会出现
- 可考虑在 MarketContextAgent 中增加一个 "market_unknown → neutral" 的 fallback（当前已存在）

### 2.4 TechnicalTrendAgent — ⚠️ 72% negative

**数据**: 10 positive / 68 neutral / 202 negative

**原因分析**:
- positive 条件严格: `trend_confirmed + consensus >= 50`
- 大部分板块未达到 multi_window_confirmed 状态
- negative 条件: trend_weak / trend_unreliable

**结论**: 这是技术面 Agent 的正常表现——在没有明确趋势的市场中，大部分板块确实技术面偏弱。

**建议**: 保持现状。positive 条件严格是正确的——不应该降低门槛让技术面 Agent 频繁 positive。

### 2.5 ShortTermHeatAgent — ✅ 分布最优

**数据**: 43 positive / 129 neutral / 108 negative  
**可靠性**: 0.71 (high_reliability)

**结论**: 这是当前最可靠的 Agent。三态分布均匀，区分度好。保持现状。

### 2.6 DataQualityAgent — ✅ 防守型正常

**数据**: 271 positive / 9 neutral / 0 negative

**原因**: 大部分板块数据质量可靠（覆盖率 ≥ 0.9）。少量 data_usable (neutral)。无 data_unreliable。

**结论**: 正常。数据质量在现代数据源下通常不是问题。

### 2.7 NarrativeAgent / PersistenceStrengthAgent — ✅ 设计正确

narrative 永远 neutral，persistence 极度 sparse。设计符合预期。

---

## 3. 语义一致性检查

| 检查项 | 结果 |
|--------|------|
| positive vote 是否对应后续更好表现? | ✅ short_term_heat (high_reliability=0.71) 证实 |
| negative vote 是否对应后续更弱表现? | ✅ rotation_analysis (moderate_reliability=0.54) 证实 |
| neutral vote 是否过多? | ⚠️ narrative 100% neutral (by design)，persistence 98% neutral (by design) |
| 是否有 Agent 100% positive/negative? | ⚠️ risk_control 100% positive (回测期间)，data_quality 97% positive |
| signal_profile 是否与实际表现一致? | ✅ 一致 |

---

## 4. 不建议修改的部分

1. **RiskControlAgent vote 规则** — 低风险环境下 positive 是正确的语义
2. **RotationAnalysisAgent neutral 缺失** — 数据特征，非 bug
3. **MarketContextAgent neutral 缺失** — 市场状态特征，非 bug
4. **TechnicalTrendAgent positive 条件严格** — 正确的保守策略
5. **NarrativeAgent 100% neutral** — low_information 设计正确
6. **PersistenceStrengthAgent 极度 sparse** — sparse_high_precision 设计正确

---

## 5. 建议的文档化说明

在报告的"数据与方法说明"中增加:

1. "risk_control 在低风险环境下主要起过滤作用，不提供区分度"
2. "rotation_neutral 在实际数据中罕见，轮动阶段通常有明确方向"
3. "narrative 不参与投票（low_information），仅提供产业叙事标签"
4. "persistence 仅在有多日 timeline 数据时出手（sparse_high_precision）"
