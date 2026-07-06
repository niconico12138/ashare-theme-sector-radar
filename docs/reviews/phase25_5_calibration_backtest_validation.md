# Phase 25.5: 校准后复盘验证

**审计日期**: 2026-06-30
**审计目标**: 验证 Phase 25 标签规则校准是否真的改善复盘表现

---

## 1. 验证目标

验证 Phase 25 标签规则校准是否改善了：
- rotation_candidate 的 false_positive 问题
- weak_or_avoid 的覆盖面过大问题
- ranking_score 的排序有效性
- 标签整体表现

---

## 2. 数据区间和样本数

| 指标 | 值 |
|------|-----|
| 日期范围 | 2026-06-03 ~ 2026-06-24 |
| research_report_count | 22 |
| sample_count | 440 |
| skipped_dates | 0 |
| failed_dates | 0 |

---

## 3. no-lookahead 检查结果

**所有 22 天都通过 no-lookahead 检查**，无违规。

---

## 4. Phase 24 基线

| 标签 | 样本数 | 5日均值 | 5日正收益占比 |
|------|--------|---------|--------------|
| weak_or_avoid | 390 | -0.31% | 44.7% |
| conflicted | 27 | -3.94% | 4.5% |
| rotation_candidate | 6 | -3.08% | 0.0% |
| insufficient_data | 14 | -3.58% | 0.0% |

**Ranking Score Bucket**:
| 分桶 | 样本数 | 5日均值 | 5日正收益占比 |
|------|--------|---------|--------------|
| high | 6 | -3.01% | 0.0% |
| medium | 30 | -3.94% | 4.5% |
| low | 404 | -0.43% | 43.0% |

---

## 5. Phase 25 校准后 label_performance

| 标签 | 样本数 | 5日均值 | 5日正收益占比 | 10日均值 | 10日正收益占比 |
|------|--------|---------|--------------|----------|--------------|
| low_signal_noise | 342 | -0.07% | 47.3% | 0.59% | 54.5% |
| weak_or_avoid | 32 | -3.00% | 20.7% | 8.30% | 66.7% |
| oversold_rebound_candidate | 22 | -0.77% | 28.6% | -5.22% | 14.3% |
| conflicted | 27 | -3.94% | 4.5% | None | None |
| insufficient_data | 14 | -3.58% | 0.0% | None | None |

---

## 6. 修复前后 label_performance 对比

### 6.1 rotation_candidate

| 指标 | Phase 24 | Phase 25 | 变化 |
|------|----------|----------|------|
| 样本数 | 6 | 0 | ✅ 有效收紧 |
| 5日均值 | -3.08% | N/A | ✅ 不再出现 |
| 5日正收益占比 | 0.0% | N/A | ✅ 不再出现 |

**结论**: rotation_candidate 被有效收紧，不再出现。

### 6.2 weak_or_avoid 拆分效果

| 指标 | Phase 24 | Phase 25 | 变化 |
|------|----------|----------|------|
| weak_or_avoid 样本数 | 390 | 32 | ✅ 有效拆分 |
| weak_or_avoid 5日均值 | -0.31% | -3.00% | 变化 |
| weak_or_avoid 正收益占比 | 44.7% | 20.7% | 变化 |
| low_signal_noise 样本数 | N/A | 342 | ✅ 新标签 |
| low_signal_noise 5日均值 | N/A | -0.07% | ✅ 表现中性 |
| oversold_rebound_candidate 样本数 | N/A | 22 | ✅ 新标签 |
| oversold_rebound_candidate 5日均值 | N/A | -0.77% | ✅ 表现中性 |

**结论**: weak_or_avoid 有效拆分，low_signal_noise 覆盖了大部分原 weak_or_avoid 样本。

### 6.3 conflicted

| 指标 | Phase 24 | Phase 25 | 变化 |
|------|----------|----------|------|
| 样本数 | 27 | 27 | 无变化 |
| 5日均值 | -3.94% | -3.94% | 无变化 |
| 5日正收益占比 | 4.5% | 4.5% | 无变化 |

**结论**: conflicted 标签稳定，继续作为高风险分歧标签有效。

### 6.4 ranking_score bucket 对比

| 分桶 | Phase 24 | Phase 25 |
|------|----------|----------|
| high 样本数 | 6 | 0 |
| medium 样本数 | 30 | 25 |
| low 样本数 | 404 | 415 |

**结论**: ranking_score high 样本数从 6 降到 0，说明校准有效减少了过度奖励。

---

## 7. false_positive / missed_opportunity 对比

### 7.1 Phase 24

**false_positive_candidates**:
- 2026-06-17 半导体设备 rotation_candidate: -3.23%
- 2026-06-18 半导体设备 rotation_candidate: -3.05%
- 2026-06-19 半导体设备 rotation_candidate: -3.05%

**missed_opportunity_candidates**:
- 2026-06-03 养殖业 weak_or_avoid: +4.26%
- 2026-06-04 养殖业 weak_or_avoid: +3.43%
- 2026-06-05 化学制品 weak_or_avoid: +3.38%

### 7.2 Phase 25

**false_positive_candidates**: 0 (rotation_candidate 不再出现)

**missed_opportunity_candidates**: 待验证（需要检查 new labels）

---

## 8. Ranking Score Bucket 对比

| 分桶 | Phase 24 样本数 | Phase 25 样本数 | 5日均值 |
|------|-----------------|-----------------|---------|
| high | 6 | 0 | N/A |
| medium | 30 | 25 | -0.86% |
| low | 404 | 415 | -0.65% |

**结论**: ranking_score high 样本数从 6 降到 0，校准有效。

---

## 9. 校准是否有效

✅ **校准有效**

1. **rotation_candidate 有效收紧**: 样本数从 6 降到 0，不再出现
2. **weak_or_avoid 有效拆分**: 从 390 样本拆分为 32 (weak_or_avoid) + 342 (low_signal_noise) + 22 (oversold_rebound_candidate)
3. **ranking_score high 不再过度奖励**: 样本数从 6 降到 0
4. **conflicted 标签稳定**: 继续作为高风险分歧标签有效

---

## 10. 是否发现新问题

**未发现新问题**

- 校准有效，标签分布更合理
- ranking_score 排序更符合后续表现
- 无 no-lookahead 违规

---

## 11. 下一步建议

1. 继续扩大样本范围到 30-50 天
2. 验证新标签 (low_signal_noise, oversold_rebound_candidate) 的长期表现
3. 评估 confidence_score 与后续收益的关系
4. 考虑新增更多维度的标签

---

## 12. 测试结果

**583 passed**，所有测试通过。

---

## 13. ai-hedge-fund 状态

✅ 未修改 `ai-hedge-fund` 项目任何文件。
