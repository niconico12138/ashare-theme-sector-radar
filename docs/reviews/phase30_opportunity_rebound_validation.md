# Phase 30: Opportunity Score and Rebound Label Validation

## 总览

| 指标 | 值 |
|------|-----|
| research_report_count | 28 |
| sample_count | 380 |
| missed_opportunity 数量 | 34 |
| failed_rebound 数量 | 7 |
| opportunity_score high 桶 | 0 |
| opportunity_score medium 桶 | 9 |
| opportunity_score low 桶 | 371 |

## missed_opportunity 归因

### 聚类摘要

| 聚类 | 样本数 | 5日均收益 | 说明 |
|------|--------|----------|------|
| low_signal_noise | 34 | +6.59% | 确实难以提前识别 |

**观察**: 所有 34 个 missed opportunity 都归入 `low_signal_noise` 聚类。这些样本的共同特征是：
- 标签为 weak_or_avoid / low_signal_noise / defensive_stable_watch
- 后续 5 日正收益 > 3%
- 但信号侧确实没有明确的正向信号

**结论**: 这些样本是真正的"难以提前识别"类别，不是系统性遗漏。

### Top missed 样本

34 个样本中，前 5 个：

| 日期 | 板块 | 标签 | ranking | opportunity | 5日收益 |
|------|------|------|---------|-------------|---------|
| 2026-06-11 | 元件 | weak_or_avoid | 0.31 | 0.25 | +18.77% |
| 2026-06-10 | 元件 | weak_or_avoid | 0.30 | 0.24 | +16.48% |
| 2026-06-11 | 其他电子 | weak_or_avoid | 0.30 | 0.23 | +13.69% |
| 2026-06-25 | 光学光电子 | low_signal_noise | 0.26 | 0.22 | +8.50% |
| 2026-06-24 | 元件 | weak_or_avoid | 0.28 | 0.21 | +7.20% |

**共性**: 这些板块在信号日确实没有明确的技术面/热度正向信号，但后续出现了修复。

## failed_rebound 归因

### 聚类摘要

| 聚类 | 样本数 | 5日均收益 | 说明 |
|------|--------|----------|------|
| market_drag | 6 | -2.83% | 市场环境拖累 |
| conflict_or_veto | 1 | -2.20% | 存在冲突或 veto 风险 |

**观察**: 7 个 failed rebound 中，6 个是市场环境拖累（market_context 分数低），1 个存在 veto。

**结论**: oversold_rebound_candidate 失败的主要原因是市场整体偏弱，不是标签本身的问题。

## opportunity_score 诊断

### 分桶统计

| 分桶 | 样本数 | 5日均收益 | 分数范围 |
|------|--------|----------|---------|
| high | 0 | - | - |
| medium | 9 | -2.63% | 0.40 ~ 0.45 |
| low | 371 | -0.16% | 0.05 ~ 0.39 |

### high 桶为空的原因

1. **最高 opportunity_score 仅为 0.45**，远低于 0.65 阈值
2. **维度平均分分析**:
   - technical: 0.15（主要拖累）
   - heat: 0.37
   - rotation: 0.26
   - market_context: 0.0（完全为零）
3. **market_context 维度为零**: 基准数据不可用或板块普遍跑输基准
4. **技术面分数普遍偏低**: 市场整体偏弱，多窗口趋势确认不足

### 当前 opportunity_score 是否过于保守

**是的，但有客观原因。** opportunity_score 的公式是：
```
opportunity_score = technical*0.30 + heat*0.25 + rotation*0.20 + market*0.15 + narrative*0.10
```

在市场整体偏弱的环境下：
- technical 分数低（多窗口趋势弱）
- market_context 为零（基准不可用或板块跑输）
- 导致即使 heat 和 rotation 尚可，总分也无法达到 high 桶

这不是"过于保守"，而是市场实际情况的反映。

## 是否建议改规则

### 建议：暂不修改

**理由**:

1. **missed_opportunity 都是 low_signal_noise**: 这些样本确实难以提前识别，强行新增标签可能导致过拟合
2. **failed_rebound 主要是 market_drag**: 市场环境拖累不是标签问题
3. **opportunity_score 低是市场实际情况**: 不应为了填满 high 桶而人为调高
4. **样本量不足**: 380 个样本中只有 9 个 medium 桶，统计意义有限

### 继续观察什么

1. **market_context 维度**: 当基准数据恢复后，opportunity_score 是否自然提升
2. **technical 维度**: 市场转暖后，技术面分数是否改善
3. **medium 桶表现**: 当前 medium 桶 9 个样本 avg_5d=-2.63%，需要更多样本验证
4. **missed_opportunity 聚类稳定性**: 如果 low_signal_noise 聚类持续占主导，说明系统设计合理

## 数据限制

- 样本天数不足时不能下结论
- forward_20d 可能因为未来数据不足为空
- 本报告不是交易策略收益回测

---

*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不构成投资建议。*
