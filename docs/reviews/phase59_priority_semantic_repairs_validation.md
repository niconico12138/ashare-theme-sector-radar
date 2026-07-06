# Phase 59: 高优先级语义修复 验证文档

> 验证日期: 2026-07-02
> 基于: Phase 59 plan docs/plans/phase59_priority_semantic_repairs_plan.md

---

## 1. 修改文件列表

| 文件 | 修改类型 | 变动说明 |
|------|----------|----------|
| `theme_sector_radar/scoring/sector_composite_score.py` | H1 修复 | `generate_risk_reasons`: 阈值 0.1→10, 0.05→5; 格式 `:.1%`→`:.1f}%` |
| `theme_sector_radar/scoring/short_term_burst_score.py` | M1 新增 | 新增 `apply_burst_insufficient_history_cap()` |
| `theme_sector_radar/scoring/__init__.py` | M1 导出 | 导出新函数 |
| `theme_sector_radar/agents/sector_research/agent_vote_aggregator.py` | H2 修复 | `aggregate()` 过滤 `decision_impact=="report_only"` 的 opinions |
| `theme_sector_radar/agents/sector_scoring/sector_scoring_agent.py` | M1 应用 | 导入 `apply_burst_insufficient_history_cap` + `get_burst_level`; 在 `burst_result` 后应用 cap |
| `tests/theme_sector_radar/test_sector_composite_score.py` | H1 测试 | 新增 3 个测试: `test_risk_reasons_drawdown_format_pct_points`, `test_risk_reasons_drawdown_thresholds`, `test_risk_reasons_volatility_format` |
| `tests/theme_sector_radar/test_agent_vote_aggregator.py` | H2 测试 | 新增 4 个测试: `test_report_only_excluded_from_voting`, `test_report_only_majority_positive_excludes_neutral_report_only`, `test_all_report_only_no_division_by_zero`, `test_market_regime_report_only_excluded` |
| `tests/theme_sector_radar/test_dual_sector_scores.py` | M1 测试 | 新增 1 个测试类 `TestBurstInsufficientHistoryCap` (9 个测试) |

---

## 2. H1 修复说明和示例

**修复前**:
```python
# threshold 0.1 (小数) — 几乎任何 max_drawdown 都会触发
if abs(max_drawdown) > 0.1:
    reasons.append(f"最大回撤较大 ({max_drawdown:.1%})")  # -8.68 → "-868.0%"
```

**修复后**:
```python
# threshold 10 (百分数点) — 只有 >10% 回撤才触发
if abs(max_drawdown) > 10:
    reasons.append(f"最大回撤较大 ({max_drawdown:.1f}%)")  # -8.68 → "-8.7%"
elif abs(max_drawdown) > 5:
    reasons.append(f"存在一定回撤 ({max_drawdown:.1f}%)")
```

**验证**: `max_drawdown=-8.68` → 显示 "存在一定回撤 (-8.7%)"，不显示 "-868.0%"

---

## 3. H2 Report-only Vote 隔离说明

**修复前**: 9 个 opinions (7 决策 + 1 persistence + 1 catalyst)，catalyst 的 neutral 计入 total_votes=9。positive_ratio = positive/9。

**修复后**: 8 个决策 opinions (7 + persistence)，catalyst(report_only) 被过滤。total_votes=8。positive_ratio = positive/8。

**影响**:
- positive_ratio 不再被 report-only neutral vote 稀释（约 +6-8% 偏移消除）
- 如果所有 opinions 都是 report-only，返回 `no_decision_opinions` 标签（score=0, confidence=0）
- report_only opinions 仍保留在 `agent_opinions` 中，用于报告展示
- CatalystEventAgent 不影响 ranking_score / opportunity_score / confidence_score

---

## 4. M1 Burst Insufficient_history Cap 规则

| 条件 | Cap | 最高 burst_level |
|------|-----|------------------|
| `history_days == 0` | 34.9 | burst_avoid (短线偏弱) |
| `0 < actual_history_days < 3` | 49.9 | burst_fading (短线降温) |
| `actual_history_days >= 3` | 无 cap | 正常 |

**与 trend cap 的关系**:
- trend cap: `insufficient_history` 或 `coverage < 0.5` → cap 34.9
- burst cap: 更细粒度（3 个级别），因为短线评分本身就依赖更少历史数据
- 两个 cap 独立运作，互不影响

**元数据字段**:
- `_burst_history_cap_applied`: true/false
- `_burst_history_cap_reason`: 解释字符串

---

## 5. 新增/更新测试清单

### H1 测试 (3 个, test_sector_composite_score.py)
- `test_risk_reasons_drawdown_format_pct_points`: -8.68 → 包含 "-8.7%"，不包含 "-868.0%"
- `test_risk_reasons_drawdown_thresholds`: >10% "最大回撤较大", >5% "存在一定回撤", ≤5% 无回撤原因
- `test_risk_reasons_volatility_format`: 3.5 波动率显示正确

### H2 测试 (4 个, test_agent_vote_aggregator.py)
- `test_report_only_excluded_from_voting`: 1 positive + 1 catalyst(report_only) → ratio=1.0
- `test_report_only_majority_positive_excludes_neutral_report_only`: 4 positive + 1 catalyst → ratio=1.0
- `test_all_report_only_no_division_by_zero`: 只有 report-only → 不除零
- `test_market_regime_report_only_excluded`: market_context report-only 也不参与

### M1 测试 (9 个, test_dual_sector_scores.py)
- `test_history_days_zero_caps_to_34_9`: history_days=0 + 80分 → cap 34.9
- `test_history_days_zero_no_cap_if_below`: history_days=0 + 20分 → 不触发 cap
- `test_actual_history_days_1_caps_to_49_9`: 1天 + 70分 → cap 49.9
- `test_actual_history_days_2_caps_to_49_9`: 2天 + 55分 → cap 49.9
- `test_actual_history_days_2_no_cap_if_below`: 2天 + 40分 → 不触发 cap
- `test_actual_history_days_3_no_cap`: 3天 + 80分 → 不触发 cap
- `test_actual_history_days_5_no_cap`: 5天 + 90分 → 不触发 cap
- `test_actual_history_days_none_falls_back_to_history_days`: None → 退回到 history_days
- `test_burst_score_with_history_days_zero_gets_capped`: 端到端验证

---

## 6. 2026-07-01 Score-sectors 运行结果摘要

```
Date: 2026-07-01
Sector Type: industry
Benchmark: hs300 (ok)

Top 5 Sectors:
1. 证券: 34.9 (偏弱)
2. 化学制药: 29.3 (偏弱)
3. 银行: 28.3 (偏弱)
4. 医疗服务: 27.9 (偏弱)
5. 养殖业: 26.1 (偏弱)
```

趋势分全部被 cap 到 ≤34.9（insufficient_history cap 生效），验证 2026-05-20 到 2026-07-01 窗口下历史数据确实不足。

---

## 7. 测试结果

| 测试集 | 结果 |
|--------|------|
| Targeted (H1+H2+M1) | 78 passed |
| Full suite | **854 passed**, 20 warnings |
| CLI score-sectors | 运行成功，输出到 `reports/sector_scores/2026-07-01/` |

---

## 8. 是否修改 ai-hedge-fund: **否**

未修改 ai-hedge-fund 项目。
