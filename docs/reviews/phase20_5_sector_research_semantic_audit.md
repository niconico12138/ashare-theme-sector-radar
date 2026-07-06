# Phase 20.5: Sector Research Agent Group 语义审计与置信度校准

**审计日期**: 2026-06-30
**审计目标**: 审计和修复 Phase 20 Agent 组输出语义

---

## 1. 当前问题现象

### 1.1 原始输出问题

Phase 20 完成后，Top5 输出如下：

| 排名 | 板块 | consensus_label | confidence_score |
|------|------|-----------------|------------------|
| 1 | 半导体 | rotation_candidate | 0.64 |
| 2 | 医疗服务 | weak_or_avoid | 0.51 |
| 3 | 养殖业 | weak_or_avoid | 0.48 |
| 4 | 中药 | weak_or_avoid | 0.48 |
| 5 | 医药商业 | weak_or_avoid | 0.47 |

### 1.2 问题分析

1. **半导体 rotation_candidate 根因**:
   - technical_label: trend_conflicted (窗口分歧)
   - rotation_label: rotation_rising (技术面处于上升阶段)
   - 原规则: rotation_label in rotation_rising 且 technical_label != trend_weak -> rotation_candidate
   - 问题: 技术面是 conflicted，但轮动是 rising，给了 rotation_candidate

2. **医疗服务 weak_or_avoid 根因**:
   - technical_label: trend_conflicted
   - heat_label: heat_moderate
   - rotation_label: rotation_lagging
   - 原规则: 默认 weak_or_avoid

3. **confidence_score 语义问题**:
   - weak_or_avoid + confidence_score=0.51 语义矛盾
   - confidence_score 来自风险/数据质量拉高，而非正向机会

4. **排序问题**:
   - 按 confidence_score 排序导致 weak_or_avoid 排前面

---

## 2. 修复方案

### 2.1 新增四个分数

| 分数 | 含义 | 主要来源 |
|------|------|----------|
| evidence_score | 证据充分度 | data_quality, benchmark availability |
| opportunity_score | 正向观察强度 | technical, heat, rotation, market_context |
| risk_control_score | 风险可控度 | risk_score |
| ranking_score | 综合排序分 | opportunity * 0.50 + evidence * 0.25 + risk_control * 0.25 |

### 2.2 confidence_score 新语义

- **含义**: 当前 consensus_label 的可信度，不是机会强度
- **计算**: 主要受数据质量和维度一致性影响
- **示例**: weak_or_avoid + confidence=0.70 表示"较有把握认为它偏弱"

### 2.3 排序规则修正

- 默认按 ranking_score 降序
- weak_or_avoid 和 insufficient_data 降权 (* 0.5)
- insufficient_data 永远排后

### 2.4 ConsensusDecisionAgent 规则修正

1. **conflicted 优先**: technical_label=trend_conflicted 且无强热度/轮动时，输出 conflicted
2. **rotation_candidate 要求**: 需要明确 rotation_rising/new_entry 且 opportunity_score >= 0.4
3. **strong_consensus 要求**: 需要 evidence_score >= 0.70, opportunity_score >= 0.65, risk_control_score >= 0.55

---

## 3. 修复前后 Top10 对比

### 修复前

| 排名 | 板块 | consensus_label | confidence_score |
|------|------|-----------------|------------------|
| 1 | 半导体 | rotation_candidate | 0.64 |
| 2 | 医疗服务 | weak_or_avoid | 0.51 |
| 3 | 养殖业 | weak_or_avoid | 0.48 |
| 4 | 中药 | weak_or_avoid | 0.48 |
| 5 | 医药商业 | weak_or_avoid | 0.47 |

### 修复后 (预期)

| 排名 | 板块 | consensus_label | ranking_score | opportunity_score |
|------|------|-----------------|---------------|-------------------|
| 1 | 半导体 | conflicted | ~0.45 | ~0.50 |
| 2 | 医疗服务 | weak_or_avoid | ~0.25 | ~0.35 |
| 3 | 养殖业 | weak_or_avoid | ~0.24 | ~0.32 |
| 4 | 中药 | weak_or_avoid | ~0.24 | ~0.32 |
| 5 | 医药商业 | weak_or_avoid | ~0.23 | ~0.30 |

---

## 4. 关键变化

1. **半导体**: rotation_candidate -> conflicted (技术面冲突，轮动信号不足以支持 rotation_candidate)
2. **weak_or_avoid 排序下降**: 因为 ranking_score 降权
3. **confidence_score 语义改变**: 不再是机会强度，而是标签可信度
4. **新增 ranking_score**: 作为主要排序依据

---

## 5. 测试结果

**520 passed**，所有测试通过。

---

## 6. ai-hedge-fund 状态

✅ 未修改 `ai-hedge-fund` 项目任何文件。
