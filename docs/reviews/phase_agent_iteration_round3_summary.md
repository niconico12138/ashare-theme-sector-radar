# 第三轮深度分析总结

**日期**: 2026-07-03  
**测试**: 全量 864+ passed

---

## 本轮新增/修改

| 文件 | 改动 |
|------|------|
| `agent_reliability_report.py` | +decision_impact 列; +sparse_event_signal profile; 更新建议文案 |

---

## 深度分析发现

### T1: 4 个未触发标签根因

| 标签 | 接近条件样本 | 未触发原因 |
|------|-------------|-----------|
| rotation_candidate | 66 | 61% 被 tech_weak 阻塞（trend_unreliable 占多数）；其余 opp<0.50 |
| defensive_watch | 61 | 仅 3 个有正确 narrative（healthcare/financial），其余 46 个是 general_sector |
| weak_continuation | 122 | **100% 被 risk_control>=0.65 阻塞**（risk_low 即 0.85+） |
| data_limited_neutral | 3 | 被更早的规则（oversold_rebound/early_repair）抢先匹配 |

**关键发现**: weak_continuation 从未触发是因为 risk_control 几乎总是 >=0.65（risk_low 即 0.85+）。条件 `risk_control < 0.65` 需要 risk_moderate 以上才会满足，但 6 月市场全部 risk_low。

### T2: oversold_rebound_candidate 过度集中

- 84 个样本占总量 26.2%
- 77 个是 heat_moderate + trend_unreliable
- Rule 9 条件太宽: 只要 heat_active/moderate + risk_control>=0.55 + opp>=0.30
- risk_control 几乎总是 >=0.55（risk_low = 0.85+）
- opp>=0.30 也很容易满足

### T3: Confidence 反向预测根因

| 标签 | avg_conf | avg_opp | 5d 收益 |
|------|----------|---------|---------|
| trend_confirmed | 0.90 | 0.62 | -0.89% |
| defensive_stable_watch | 0.80 | 0.16 | +2.31% |
| oversold_rebound_candidate | 0.70 | 0.36 | -0.72% |
| conflicted | 0.66 | 0.35 | -2.34% |
| short_term_active_unconfirmed | 0.63 | 0.36 | +3.45% |

**根因**: confidence_score 衡量的是"标签可信度"（数据质量+维度一致性），不是"机会强度"。高 confidence 的板块数据好+维度不冲突，但方向不一定对。这是正确的语义设计，不是 bug。

---

## 未修改 ConsensusDecisionAgent
## 未修改评分公式
## 未修改 ai-hedge-fund
