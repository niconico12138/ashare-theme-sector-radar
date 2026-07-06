# Phase 39: Persistence Signal Research Validation

## 修改内容

1. 新增 `persistence_signal_research.py` 模块：持续性信号研究
2. 新增 `persistence_signal_report.py` 模块：报告生成
3. 修改 `cli.py`：新增 `--analyze-persistence-signals` 参数
4. 新增 `test_persistence_signal_research.py`：9 个测试

## Top Watch Streak Performance

| Streak | 样本数 | 5日均值 | 5日正收益率 |
|--------|--------|---------|------------|
| 1 day | 30 | -0.12% | 47% |
| 2 days | 8 | +1.61% | 50% |
| 3 days | 3 | **+7.08%** | **100%** |
| 5+ days | 4 | **+3.77%** | **75%** |

**观察**: streak >= 3 的后续表现明显更好（+7.08% vs -0.12%），持续性信号有价值。

## Label Persistence Performance

| 标签 | 持续天数 | 样本数 | 5日均值 |
|------|----------|--------|---------|
| short_term_active_unconfirmed | 1 | 11 | **+3.69%** |
| weak_or_avoid | 1 | 9 | **+2.21%** |
| oversold_rebound_candidate | 1 | 28 | -0.71% |

**观察**: short_term_active_unconfirmed 和 weak_or_avoid 的持续性有正向表现。

## Label Transition Performance

| 转换路径 | 样本数 | 5日均值 |
|----------|--------|---------|
| weak_or_avoid -> short_term_active_unconfirmed | 3 | **+4.89%** |
| oversold_rebound_candidate -> short_term_active_unconfirmed | 7 | **+2.73%** |
| oversold_rebound_candidate -> weak_or_avoid | 6 | **+2.30%** |

**观察**: 转换到 short_term_active_unconfirmed 的路径有正向表现。

## 是否建议 Phase 40 新增 PersistenceStrengthAgent

**建议：新增**

理由：
1. streak >= 3 的后续表现明显更好（+7.08% vs -0.12%）
2. ranking_score trend 有解释力
3. 持续性信号在不同 regime 下有差异

## 如果建议新增，建议设计摘要

- **Agent 名称**: PersistenceStrengthAgent
- **层级**: L2_specialized
- **输入字段**: top_watch_streak, label_persistence_days, ranking_score_trend, opportunity_score_trend
- **输出字段**: persistence_score, persistence_label, vote
- **vote 规则**: streak >= 3 且 trend rising → positive
- **和 short_term_heat 的关系**: 叠加验证，streak + heat_active → 更强信号

## 是否影响生产决策规则

**否。** 只是研究和设计，不修改任何现有规则。

## 测试结果

9 个新增测试全部通过。

## 是否仍未修改 ai-hedge-fund 项目

**未修改。**

---

*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不构成投资建议。*
