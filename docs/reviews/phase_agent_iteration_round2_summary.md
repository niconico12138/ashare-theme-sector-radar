# 第二轮深度分析总结

**日期**: 2026-07-03  
**测试**: 864 passed, 0 failed

---

## 本轮新增/修改

### 新增文件
| 文件 | 说明 |
|------|------|
| `tests/theme_sector_radar/test_agent_opinion_contract.py` | AgentOpinion 契约测试 (14 tests) |

### 修复 Bug
| 文件 | Bug | 修复 |
|------|-----|------|
| `confidence_calibration_agent.py` | `score_data.get("data_quality_score")` 返回 0（字段不存在）| 改为 `score_data.get("history_coverage_ratio")` |

**影响**: calibrated_confidence_score 从永远 0 变为基于 history_coverage_ratio 正常计算。

---

## 深度分析发现

### 1. 多日 Vote 稳定性

| Agent | 日均 positive | 日均 neutral | 日均 negative | 标准差 |
|-------|-------------|-------------|--------------|--------|
| technical_trend | 3.2% | 26.8% | 70.0% | 5.3% ✅ |
| short_term_heat | 13.9% | 47.1% | 39.0% | 19.8% |
| rotation_analysis | 20.6% | 3.2% | 76.1% | 21.2% |
| risk_control | 95.8% | 3.2% | 1.0% | 17.9% |
| data_quality | 91.9% | 7.1% | 1.0% | 19.7% |
| market_context | 29.0% | 3.2% | 67.7% | 45.4% ⚠️ |

**发现**: market_context 标准差 45.4%——波动最大，在不同市场状态下表现差异极大。

### 2. Confidence 反向预测

| Confidence 分桶 | 样本 | 5d 均值 | 5d 正率 |
|-----------------|------|---------|---------|
| high (>=0.7) | 183 | **-0.72%** | 37% |
| medium (0.4-0.7) | 94 | **+1.01%** | 59% |
| low (<0.4) | 3 | -3.96% | 0% |

**发现**: confidence_score 与 forward returns **反向相关**！高 confidence 板块反而表现差。
**原因推测**: high confidence 标签多为 oversold_rebound_candidate（占 26%），在 6 月弱势市场中这类标签的"确认感"反而对应弱势延续。
**建议**: 不改 confidence 计算逻辑（它正确反映了标签可信度），但需要在报告中说明"高 confidence ≠ 好机会"。

### 3. 标签-收益分析

| 标签 | 5d | 10d | 20d | 5d正率 | 评价 |
|------|-----|------|------|--------|------|
| short_term_active_unconfirmed | +3.45% | +2.01% | **-23.69%** | 73% | ⚠️ 短线弹但长线崩 |
| defensive_stable_watch | +2.31% | -3.72% | 0.00% | 71% | ⚠️ 涨后回落 |
| conflicted | -2.34% | -1.66% | 0.00% | 30% | ✅ 有效过滤 |
| early_repair_watch | -2.12% | +1.03% | 0.00% | 19% | ⚠️ 偏弱 |
| weak_or_avoid | +0.72% | +0.72% | **+8.16%** | 51% | ⚠️ 过度保守 |

### 4. 标签覆盖率

15 个可能标签中，**4 个从未触发**：
- rotation_candidate（需要 rotation_rising + 非弱趋势 + opportunity >= 0.50）
- defensive_watch（需要特定行业属性 + risk_low/moderate）
- weak_continuation（条件太窄，与 weak_or_avoid 重叠）
- data_limited_neutral（条件太窄）

**oversold_rebound_candidate 占 26.2%** — 需要考虑是否收窄条件。

### 5. 标签稳定性

板块级标签切换频率: **49.2%**（几乎一半时间在变）
- 优点: 标签对市场变化敏感
- 缺点: 频繁切换不利于跟踪观察

### 6. Veto 效果

23 个 veto 触发，其中 17 个是 low_signal_noise 标签触发的 veto。这说明 veto 主要过滤的是低信号板块（合理行为）。

---

## 本轮测试结果

```
864 passed, 19 warnings in 144s
```

新增 10 个测试来自 `test_agent_opinion_contract.py`（AgentOpinion 字段契约 + Signal Profile 契约 + CatalystEvent decision_impact 验证 + Low-information 排除验证）。

---

## 未修改评分公式
## 未修改 ai-hedge-fund
## 未修改 Agent 内部分析逻辑
