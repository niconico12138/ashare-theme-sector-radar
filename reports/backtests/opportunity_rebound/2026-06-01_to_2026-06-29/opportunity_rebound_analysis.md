# Opportunity Score and Rebound Label 归因分析报告

> **免责声明**: 本报告仅用于板块研究、观察和复盘，不构成投资建议。

## 总览

- **日期范围**: 2026-06-01 ~ 2026-06-29
- **板块类型**: industry
- **样本数量**: 190
- **missed_opportunity 数量**: 11
- **failed_rebound 数量**: 27

## opportunity_score 分桶统计

| 分桶 | 样本数 | 5日均收益 | 10日均收益 | 5日正收益率 | 分数范围 |
|------|--------|----------|-----------|-----------|---------|
| high | 1 | -7.63% | - | - | 0.65 ~ 0.65 |
| medium | 39 | 2.14% | 4.30% | 59% | 0.40 ~ 0.64 |
| low | 150 | 0.23% | 2.53% | 50% | 0.10 ~ 0.38 |

## missed_opportunity 归因

共 11 个样本被标记为弱标签但后续 5 日正收益 > 3%。

### 聚类摘要

| 聚类 | 样本数 | 5日均收益 | 说明 |
|------|--------|----------|------|
| low_signal_noise | 11 | 5.41% | 确实难以提前识别 |

### Top missed 样本

| 日期 | 板块 | 标签 | ranking | opportunity | 5日收益 | pre_5d | 聚类 |
|------|------|------|---------|-------------|---------|--------|------|
| 2026-06-10 | 电子化学品 | weak_or_avoid | 0.34 | 0.38 | 9.50% | 7.01% | low_signal_noise |
| 2026-06-08 | 保险 | low_signal_noise | 0.35 | 0.24 | 7.91% | -1.91% | low_signal_noise |
| 2026-06-12 | 其他电源设备 | weak_or_avoid | 0.31 | 0.27 | 6.79% | -5.39% | low_signal_noise |
| 2026-06-10 | 机场航运 | weak_or_avoid | 0.31 | 0.28 | 5.54% | -6.11% | low_signal_noise |
| 2026-06-02 | 电子化学品 | weak_or_avoid | 0.30 | 0.26 | 5.28% | -6.16% | low_signal_noise |
| 2026-06-10 | 塑料制品 | weak_or_avoid | 0.33 | 0.37 | 4.54% | -0.56% | low_signal_noise |
| 2026-06-11 | 工业金属 | weak_or_avoid | 0.30 | 0.25 | 4.30% | -10.23% | low_signal_noise |
| 2026-06-11 | 军工电子 | weak_or_avoid | 0.31 | 0.27 | 4.09% | -1.44% | low_signal_noise |
| 2026-06-10 | 多元金融 | weak_or_avoid | 0.31 | 0.28 | 3.95% | -7.91% | low_signal_noise |
| 2026-06-03 | 元件 | weak_or_avoid | 0.34 | 0.38 | 3.92% | -0.94% | low_signal_noise |

## failed_rebound 归因

共 27 个 oversold_rebound_candidate 样本后续 5 日为负。

### 聚类摘要

| 聚类 | 样本数 | 5日均收益 | 说明 |
|------|--------|----------|------|
| conflict_or_veto | 2 | -5.60% | 存在冲突或 veto 风险 |
| market_drag | 25 | -3.27% | 市场环境拖累 |

### Top failed 样本

| 日期 | 板块 | ranking | opportunity | 5日收益 | pre_5d | heat | 聚类 |
|------|------|---------|-------------|---------|--------|------|------|
| 2026-06-04 | 煤炭开采加工 | 0.59 | 0.45 | -8.99% | 10.18% | heat_moderate | conflict_or_veto |
| 2026-06-02 | 工业金属 | 0.53 | 0.31 | -8.80% | -4.36% | heat_moderate | market_drag |
| 2026-06-02 | 贵金属 | 0.54 | 0.33 | -8.61% | -7.24% | heat_moderate | market_drag |
| 2026-06-22 | 小金属 | 0.67 | 0.52 | -8.50% | 13.21% | heat_active | market_drag |
| 2026-06-12 | 机场航运 | 0.54 | 0.34 | -7.47% | -2.84% | heat_moderate | market_drag |
| 2026-06-03 | 油气开采及服务 | 0.56 | 0.37 | -6.01% | 1.87% | heat_moderate | market_drag |
| 2026-06-04 | 其他电子 | 0.53 | 0.32 | -5.12% | -2.13% | heat_moderate | market_drag |
| 2026-06-22 | 化学原料 | 0.53 | 0.30 | -4.81% | -0.01% | heat_moderate | market_drag |
| 2026-06-03 | 小金属 | 0.53 | 0.32 | -4.10% | -2.00% | heat_moderate | market_drag |
| 2026-06-12 | 能源金属 | 0.54 | 0.34 | -4.06% | -2.91% | heat_moderate | market_drag |

## opportunity_score 诊断

- **high 桶样本数**: 1
- **near high (0.50~0.65) 样本数**: 10
- **最高 opportunity_score**: 0.65

### 维度平均分

| 维度 | 平均分 | 权重 |
|------|--------|------|
| technical | 0.26 | 0.3 |
| heat | 0.54 | 0.25 |
| rotation | 0.32 | 0.2 |
| market_context | 0.0 | 0.15 |

### high 桶为空的原因分析


## 是否建议改规则

### 建议：暂不修改

- missed_opportunity 主要集中在 low_signal_noise 和 weak_or_avoid
- 这些样本的共同特征是信号确实不足，难以提前识别
- 强行新增标签可能导致过拟合
- 建议继续观察 1-2 个月，积累更多样本

### 继续观察什么

- momentum_repair 聚类是否稳定出现
- oversold_rebound_candidate 收紧后是否改善
- opportunity_score medium 桶表现是否优于 low 桶

## 数据限制

- 样本天数不足时不能下结论
- forward_20d 可能因为未来数据不足为空
- 本报告不是交易策略收益回测

---

*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不构成投资建议。*