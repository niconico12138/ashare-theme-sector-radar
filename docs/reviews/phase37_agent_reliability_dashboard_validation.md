# Phase 37: Agent Reliability Dashboard Validation

## 修改内容

1. 新增 `agent_reliability.py` 模块：Agent 可靠性评估
2. 新增 `agent_reliability_report.py` 模块：报告生成
3. 修改 `cli.py`：新增 `--analyze-agent-reliability` 参数
4. 新增 `test_agent_reliability.py`：9 个测试

## Agent Reliability Ranking

| Agent | Layer | 样本数 | 正向票 | 负向票 | 可靠性评分 | 可靠性标签 |
|-------|-------|--------|--------|--------|------------|------------|
| short_term_heat | L2_specialized | 280 | 43 | 108 | **0.71** | **high_reliability** |
| rotation_analysis | L2_specialized | 280 | 64 | 216 | **0.54** | **moderate_reliability** |
| technical_trend | L2_specialized | 280 | 10 | 202 | 0.38 | low_reliability |
| data_quality | L1_data_evidence | 280 | 271 | 3 | 0.31 | low_reliability |
| risk_control | L2_specialized | 280 | 280 | 0 | 0.30 | low_reliability |
| market_context | L2_specialized | 280 | 0 | 280 | 0.30 | low_reliability |
| narrative | L2_specialized | 280 | 0 | 280 | 0.30 | low_reliability |

## Vote Distribution 核心结果

| Agent | Positive | Neutral | Negative | 分布特点 |
|-------|----------|---------|----------|----------|
| short_term_heat | 43 (15%) | 129 (46%) | 108 (39%) | **分布均衡** |
| rotation_analysis | 64 (23%) | 0 (0%) | 216 (77%) | 偏负向 |
| technical_trend | 10 (4%) | 68 (24%) | 202 (72%) | 偏负向 |
| data_quality | 271 (97%) | 6 (2%) | 3 (1%) | **几乎全正向** |
| risk_control | 280 (100%) | 0 (0%) | 0 (0%) | **全正向** |
| market_context | 0 (0%) | 0 (0%) | 280 (100%) | **全负向** |
| narrative | 0 (0%) | 280 (100%) | 0 (0%) | **全中性** |

## Vote Performance 核心结果

| Agent | Vote | 5日均值 | 5日正收益率 |
|-------|------|---------|------------|
| short_term_heat | positive | **+3.42%** | **78%** |
| short_term_heat | negative | +0.44% | 50% |
| rotation_analysis | positive | **+2.03%** | **59%** |
| rotation_analysis | negative | +0.10% | 49% |
| technical_trend | positive | +0.71% | 80% |
| technical_trend | negative | +0.43% | 52% |
| data_quality | positive | +0.54% | 51% |
| risk_control | positive | +0.54% | 51% |
| market_context | negative | +0.54% | 51% |
| narrative | neutral | +0.54% | 51% |

## 误判样本

| 类型 | 数量 |
|------|------|
| positive_false_signal | 20 |
| negative_missed_signal | 20 |
| neutral_missed_move | 20 |

## 哪些 Agent 区分度不足

1. **risk_control**: 100% positive vote，完全没有区分度
2. **market_context**: 100% negative vote，完全没有区分度
3. **narrative**: 100% neutral vote，完全没有区分度
4. **data_quality**: 97% positive vote，区分度极低

## 是否建议 Phase 38 新增 PersistenceStrengthAgent

**建议：暂不新增。**

理由：
1. short_term_heat 已经是高可靠性 Agent（0.71），其 positive vote 有 78% 正收益率
2. rotation_analysis 也是中等可靠性（0.54）
3. 其他 Agent 区分度不足，需要先解决现有 Agent 的问题
4. 建议先优化 technical_trend、risk_control、market_context、narrative 的 vote 逻辑

## 是否影响 Agent 决策逻辑

**否。** 只是评估现有 Agent 的表现，不改变任何决策逻辑。

## 测试结果

9 个新增测试全部通过。

## 是否仍未修改 ai-hedge-fund 项目

**未修改。**

---

*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不构成投资建议。*
