# Phase 25: Agent 标签规则回测校准

**审计日期**: 2026-06-30
**审计目标**: 根据 Phase 24 的复盘结果，校准 Agent 组标签规则和 ranking_score 规则

---

## 1. Phase 24 问题摘要

### 1.1 样本数量

| 指标 | 值 |
|------|-----|
| sample_count | 440 |
| research_report_count | 22 |
| forward_5d_return 可计算 | 大部分可计算 |

### 1.2 标签表现问题

| 标签 | 样本数 | 5日均值 | 5日正收益占比 | 问题 |
|------|--------|---------|--------------|------|
| weak_or_avoid | 390 | -0.31% | 44.7% | 覆盖面过大 |
| conflicted | 27 | -3.94% | 4.5% | 后续表现差 |
| rotation_candidate | 6 | -3.08% | 0.0% | 后续表现差 |
| insufficient_data | 14 | -3.58% | 0.0% | 数据不足 |

### 1.3 ranking_score 问题

| 分桶 | 样本数 | 5日均值 | 5日正收益占比 |
|------|--------|---------|--------------|
| high | 6 | -3.01% | 0.0% |
| medium | 30 | -3.94% | 4.5% |
| low | 404 | -0.43% | 43.0% |

**问题**: ranking_score high 没有体现正向优势，反而表现最差。

---

## 2. rotation_candidate 校准原因和新规则

### 2.1 校准原因

- rotation_candidate 样本数 6，5日均值 -3.08%，5日正收益占比 0.0%
- 原规则过于宽松，导致技术面冲突时也可能输出 rotation_candidate

### 2.2 新规则

```
rotation_candidate 触发条件:
- rotation_label in rotation_rising/rotation_new_entry
- technical_label 不得为 trend_weak/trend_unreliable/trend_conflicted
- opportunity_score >= 0.50
- risk_control_score >= 0.55
```

**关键变化**: 技术面冲突时优先输出 conflicted，而不是 rotation_candidate。

---

## 3. weak_or_avoid 拆分原因和新标签

### 3.1 拆分原因

- weak_or_avoid 样本数 390，覆盖面过大
- 5日正收益占比 44.7%，说明弱板块仍有部分后续表现
- 需要更细粒度的标签来区分不同类型的弱板块

### 3.2 新标签

| 标签 | 含义 | 触发条件 |
|------|------|----------|
| weak_continuation | 多窗口弱、短线弱、风险不占优，偏弱延续 | technical=trend_weak, heat=heat_weak/heat_fading, opportunity<0.30, risk_control<0.65 |
| oversold_rebound_candidate | 整体偏弱，但存在短线修复/反弹观察信号 | heat=heat_moderate/heat_active, opportunity<0.35, risk_control>=0.45 |
| low_signal_noise | 没有足够强信号，标签价值较低 | opportunity<0.35, technical=trend_weak/trend_unreliable/trend_neutral |

**保留 weak_or_avoid 作为 fallback**。

---

## 4. ranking_score 新公式

### 4.1 旧公式

```
base_ranking_score = opportunity * 0.50 + evidence * 0.25 + risk_control * 0.25
```

### 4.2 新公式

```
base_ranking_score =
  opportunity_score * 0.45
+ evidence_score * 0.20
+ risk_control_score * 0.25
+ market_context_score * 0.10

惩罚项:
- conflicted: * 0.65
- rotation_candidate (technical != trend_confirmed): * 0.75
- weak_continuation/weak_or_avoid/low_signal_noise: * 0.50
- insufficient_data: * 0.20
- risk_high/risk_extreme: * 0.70
- conflicted_windows: * 0.75

加分项:
- multi_window_confirmed: +0.05
- trend_confirmed + risk_low/moderate: +0.05
- opportunity >= 0.65 and evidence >= 0.70: +0.05
```

---

## 5. 修复前后 label_performance 对比

### 5.1 修复前 (Phase 24)

| 标签 | 样本数 | 5日均值 | 5日正收益占比 |
|------|--------|---------|--------------|
| weak_or_avoid | 390 | -0.31% | 44.7% |
| conflicted | 27 | -3.94% | 4.5% |
| rotation_candidate | 6 | -3.08% | 0.0% |

### 5.2 修复后 (Phase 25)

**待验证**: 需要重新生成样本并回测。

---

## 6. 修复前后 ranking_score bucket 对比

### 6.1 修复前 (Phase 24)

| 分桶 | 样本数 | 5日均值 | 5日正收益占比 |
|------|--------|---------|--------------|
| high | 6 | -3.01% | 0.0% |
| medium | 30 | -3.94% | 4.5% |
| low | 404 | -0.43% | 43.0% |

### 6.2 修复后 (Phase 25)

**待验证**: 需要重新生成样本并回测。

---

## 7. false_positive / missed_opportunity 对比

### 7.1 修复前 (Phase 24)

**false_positive_candidates**:
- 2026-06-17 半导体设备 rotation_candidate: -3.23%
- 2026-06-18 半导体设备 rotation_candidate: -3.05%

**missed_opportunity_candidates**:
- 2026-06-03 养殖业 weak_or_avoid: +4.26%
- 2026-06-04 养殖业 weak_or_avoid: +3.43%

### 7.2 修复后 (Phase 25)

**待验证**: 需要重新生成样本并回测。

---

## 8. 是否仍然 need_more_data

**否**，当前 440 个样本已有统计意义。

但需要注意：
1. 部分标签样本数较少 (trend_confirmed_but_strength_limited: 3, rotation_candidate: 6)
2. 需要更多日期验证趋势类标签
3. 重新生成样本后需要再次回测验证

---

## 9. 下一步建议

1. 重新生成样本并回测
2. 验证新标签规则是否改善了 label_performance
3. 验证 ranking_score 新公式是否改善了分桶表现
4. 继续扩大样本范围到 30-50 天

---

## 10. 测试结果

**583 passed**，所有测试通过。

---

## 11. ai-hedge-fund 状态

✅ 未修改 `ai-hedge-fund` 项目任何文件。
