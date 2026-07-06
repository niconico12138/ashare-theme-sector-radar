# Phase 38: Low-Separation Agent Calibration Validation

## 修改内容

1. 修改 `risk_control_agent.py`：基于 risk_label + flags + veto + conflict 投票
2. 修改 `market_context_agent.py`：基于 regime 信息投票
3. 修改 `data_quality_agent.py`：更细粒度的投票逻辑
4. 修改 `narrative_agent.py`：添加 low_information_agent 标记
5. 修改 `coordinator.py`：传递 regime 信息给 market_context_agent
6. 新增 `test_phase38_low_separation_agent_calibration.py`：22 个测试

## Phase 37 Baseline vs Phase 38

### market_context

| 指标 | Phase 37 | Phase 38 |
|------|----------|----------|
| positive | 0 (0%) | 90 (32%) |
| neutral | 0 (0%) | 0 (0%) |
| negative | 280 (100%) | 190 (68%) |
| reliability_score | 0.30 | **0.39** |

**改善**: market_context 从 100% negative 变为有区分度的分布 (+32% / -68%)，reliability 从 0.30 提升到 0.39。

### risk_control

| 指标 | Phase 37 | Phase 38 |
|------|----------|----------|
| positive | 280 (100%) | 280 (100%) |
| neutral | 0 (0%) | 0 (0%) |
| negative | 0 (0%) | 0 (0%) |
| reliability_score | 0.30 | 0.30 |

**说明**: risk_control 仍然 100% positive，因为所有样本的风险评分都是 risk_low 且无风险标志。这是数据本身的特性，不是 Agent 逻辑问题。

### data_quality

| 指标 | Phase 37 | Phase 38 |
|------|----------|----------|
| positive | 271 (97%) | 271 (97%) |
| neutral | 6 (2%) | 9 (3%) |
| negative | 3 (1%) | 0 (0%) |
| reliability_score | 0.31 | 0.31 |

**说明**: data_quality 分布变化不大，因为大部分样本确实是 data_reliable。

### narrative

| 指标 | Phase 37 | Phase 38 |
|------|----------|----------|
| low_information_agent | 无 | **True** |
| vote | neutral | neutral |

**改善**: narrative 现在明确标记为 low_information_agent，不会被误判为无效 Agent。

## Agent Reliability Ranking (Phase 38)

| Agent | Reliability | Vote Distribution |
|-------|-------------|-------------------|
| short_term_heat | **0.71** | +43(15%) =129(46%) -108(39%) |
| rotation_analysis | **0.54** | +64(23%) =0(0%) -216(77%) |
| market_context | 0.39 | +90(32%) =0(0%) -190(68%) |
| technical_trend | 0.38 | +10(4%) =68(24%) -202(72%) |
| data_quality | 0.31 | +271(97%) =9(3%) -0(0%) |
| risk_control | 0.30 | +280(100%) =0(0%) -0(0%) |
| narrative | 0.30 | +0(0%) =280(100%) -0(0%) |

## 是否引入新的明显误判

**否。** 校准后的 Agent 表现更合理，没有引入新的明显误判。

## 是否建议 Phase 39 新增 PersistenceStrengthAgent

**暂不建议。** short_term_heat 已经是高可靠性 Agent（0.71），建议先继续观察现有 Agent 的表现。

## 是否影响 ConsensusDecisionAgent 标签规则

**否。** 只修改了 L2 Agent 的 vote 逻辑，不改变 L4 共识决策。

## 测试结果

22 个新增测试全部通过。

## 是否仍未修改 ai-hedge-fund 项目

**未修改。**

---

*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不构成投资建议。*
