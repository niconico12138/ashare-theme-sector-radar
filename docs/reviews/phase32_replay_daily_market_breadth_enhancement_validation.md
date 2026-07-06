# Phase 32: Replay Daily Market Breadth Enhancement Validation

## 修改内容

在 `replay_daily_from_sector_history.py` 中新增 `_compute_market_breadth` 方法，基于 `data_cache/sector_history/industry/*.json` 为每个 signal_date 计算市场广度指标。

### 修复的问题

1. **涨跌幅计算**: 原代码使用 `前收盘` 字段（不存在），改为使用前一日收盘价
2. **市场温度**: 从硬编码 `score=50, label=neutral` 改为基于广度计算
3. **广度数据**: 新增 `market_breadth` 字段，包含完整的广度指标

## 增强前 vs 增强后

### 市场温度

| 日期 | 增强前 | 增强后 |
|------|--------|--------|
| 2026-06-10 | neutral(50) | cold(26) |
| 2026-06-15 | neutral(50) | hot(80) |
| 2026-06-20 | neutral(50) | cold(37) |
| 2026-06-24 | neutral(50) | cold(23) |
| 2026-06-28 | neutral(50) | cold(8) |

### 广度

| 日期 | 增强前 | 增强后 |
|------|--------|--------|
| 2026-06-10 | mixed(0/0) | narrow_rising(10/80) |
| 2026-06-15 | mixed(0/0) | broad_rising(68/80) |
| 2026-06-20 | mixed(0/0) | narrow_rising(21/83) |
| 2026-06-24 | mixed(0/0) | narrow_rising(12/83) |
| 2026-06-28 | mixed(0/0) | broad_falling(3/83) |

### Regime 分布

| Regime | 增强前 | 增强后 |
|--------|--------|--------|
| choppy_market | 260 | 420 |
| weak_rebound | 300 | 40 |
| risk_off | 0 | 80 |
| risk_on | 0 | 20 |

**结论**: 增强后 regime 分布从 2 类增加到 4 类，区分度显著提升。

## Label x Regime 核心结果

### oversold_rebound_candidate

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 15 | +0.38% | 50% |
| weak_rebound | 1 | -2.20% | 0% |
| risk_on | 1 | -2.96% | 0% |

**观察**: oversold_rebound 在 choppy_market 下表现最好（+0.38%, 50%正），在 risk_on 和 weak_rebound 下表现差。

### low_signal_noise

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 50 | **+1.86%** | **64%** |
| risk_off | 18 | +0.21% | 60% |
| weak_rebound | 11 | -2.82% | 0% |

**观察**: low_signal_noise 在 choppy_market 下表现显著更好（+1.86%, 64%正），在 weak_rebound 下表现差。

### weak_or_avoid

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 198 | +0.25% | 44% |
| risk_off | 11 | +1.38% | 60% |
| weak_rebound | 9 | -1.93% | 38% |

**观察**: weak_or_avoid 在 risk_off 下表现最好（+1.38%, 60%正），与直觉相反。

### conflicted

| regime | 样本数 | 5日均收益 | 5日正收益率 |
|--------|--------|----------|-----------|
| choppy_market | 26 | -2.01% | 14% |
| risk_on | 3 | -4.60% | 33% |

**观察**: conflicted 在所有 regime 下都偏弱，标签一致性较好。

## 结论

### 是否建议新增 Market Regime Agent

**建议：暂不新增，但值得继续观察**

理由：
1. regime 分布已从 2 类增加到 4 类，区分度显著提升
2. low_signal_noise 在不同 regime 下表现差异明显（choppy +1.86% vs weak_rebound -2.82%）
3. 但样本量仍不足（risk_on 仅 20 个），需要更多数据验证

### 是否建议将 market_regime 接入 ConsensusDecisionAgent

**建议：暂不接入，但可在报告中展示 regime 信息**

理由：
1. regime 信息有助于理解标签表现差异
2. 但尚未证明接入后能提升标签准确性
3. 建议先在 sector_research.md 中展示 regime，观察人工复盘效果

### 是否建议暂不修改标签规则

**是，暂不修改**

理由：
1. 当前标签在不同 regime 下的表现差异主要是市场环境导致
2. 强行根据 regime 调整标签可能导致过拟合
3. 需要更多数据验证

### 下一阶段建议

1. 在 sector_research.md 报告中增加 regime 标签展示
2. 积累更多历史数据（3-6 个月），验证 regime 分层的稳定性
3. 如果 regime 分层持续有效，考虑在 Phase 34+ 新增 Market Regime Agent

## 数据限制

- forward_20d 可能因为未来数据不足为空
- market_breadth 基于 80+ 个行业板块，但部分板块数据不完整

---

*本报告由 Theme Sector Radar 自动生成，仅用于板块研究、观察和复盘，不构成投资建议。*
