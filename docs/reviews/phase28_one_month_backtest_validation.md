# Phase 28: One Month Backtest Validation

## 数据覆盖情况

| 指标 | 值 |
|------|-----|
| 行业板块文件数 | 83 |
| 概念板块文件数 | 120 |
| 空文件数 | 0 |
| 日期范围 | 2026-05-20 ~ 2026-06-29 |
| 唯一日期数 | 28 |
| 6月交易日覆盖 | 20/20 (100%) |
| 7月数据 | 未下载 (无网络访问) |

历史数据完整覆盖 2026-06-01 至 2026-06-29 的所有交易日。无需额外下载。

## Replay Daily 结果

| 指标 | 值 |
|------|-----|
| Generated Dates | 29 |
| Reused Dates | 0 |
| Skipped Dates | 0 |
| Failed Dates | 0 |
| No-lookahead Violations | 0 |

所有 29 个交易日均成功生成日报，无数据泄露。

## Generate Research Range 结果

| 指标 | 值 |
|------|-----|
| Generated Dates | 28 |
| Reused Dates | 0 |
| Skipped Dates | 1 (2026-06-01: insufficient history) |
| Failed Dates | 0 |

2026-06-01 因历史数据不足（仅 1 个交易日）被跳过，其余 28 日均成功生成 sector research 报告。

## No-Lookahead 检查结果

- Replay daily: 0 violations
- Generate research range: 每个 signal_date 的 history_end_date 均等于 signal_date
- 无未来数据泄露

## Research Backtest 核心结果

### 基础统计

| 指标 | 值 |
|------|-----|
| research_report_count | 28 |
| sample_count | 560 |
| skipped_dates | 1 |

### Label Performance

| 标签 | 样本数 | 5日均收益 | 5日正收益率 | 10日均收益 | 10日正收益率 |
|------|--------|----------|------------|----------|------------|
| low_signal_noise | 444 | -0.17% | 45.05% | +0.58% | 54.10% |
| weak_or_avoid | 37 | -3.00% | 20.69% | +8.30% | 66.67% |
| oversold_rebound_candidate | 22 | -0.77% | 28.57% | -5.22% | 14.29% |
| conflicted | 39 | -3.94% | 4.55% | - | - |
| trend_confirmed_but_strength_limited | 4 | -2.65% | 0.00% | - | - |
| insufficient_data | 14 | -3.58% | 0.00% | - | - |

### Ranking Score Bucket Performance

| 桶 | 样本数 | 5日均收益 |
|----|--------|----------|
| high | 0 | - |
| medium | 26 | -0.86% |
| low | 534 | -0.71% |

### Opportunity Score Bucket Performance

| 桶 | 样本数 | 5日均收益 |
|----|--------|----------|
| high | 0 | - |
| medium | 6 | -3.01% |
| low | 554 | -0.68% |

### Confidence Score Bucket Performance

| 桶 | 样本数 | 5日均收益 |
|----|--------|----------|
| high | 405 | -1.21% |
| medium | 139 | +0.86% |
| low | 16 | -3.58% |

### False Positive / Missed Opportunity 示例

**False Positive Candidates**: 0 项

**Missed Opportunity Candidates** (5日正收益 > 10% 但标签为 low_signal_noise):

| 日期 | 板块 | 标签 | ranking_score | 5日收益 |
|------|------|------|--------------|--------|
| 2026-06-11 | 元件 | low_signal_noise | 0.26 | +18.77% |
| 2026-06-10 | 元件 | low_signal_noise | 0.25 | +16.48% |
| 2026-06-11 | 其他电子 | low_signal_noise | 0.25 | +13.69% |

## Agent Layer Backtest 核心结果

### Layer Performance

| 层 | 样本数 | 5日均收益 | 5日正收益率 |
|----|--------|----------|------------|
| L1_data_evidence | 560 | -0.72% | 38.81% |
| L2_specialized | 3360 | -0.72% | 38.81% |

### Agent Performance

所有 7 个 Agent（technical_trend, short_term_heat, rotation_analysis, risk_control, data_quality, market_context, narrative）的性能指标完全一致（5日均收益 -0.72%），表明 Agent 级别的投票差异未被当前回测框架区分。

### Vote Performance

| 投票类型 | 样本数 | 5日均收益 |
|---------|--------|----------|
| positive | 0 | - |
| neutral | 560 | -0.72% |
| negative | 0 | - |
| veto | 0 | - |

### Conflict Performance

| 冲突类型 | 样本数 | 5日均收益 |
|---------|--------|----------|
| has_conflict | 560 | -0.72% |

### Veto Performance

| Veto 状态 | 样本数 | 5日均收益 |
|-----------|--------|----------|
| veto_true | 560 | -0.72% |
| veto_false | 0 | - |

### Confidence Calibration Performance

| 置信度 | 样本数 | 5日均收益 |
|--------|--------|----------|
| high | 403 | -1.21% |
| medium | 143 | +0.86% |
| low | 14 | -3.58% |

### Opportunity-Confidence Matrix

| opportunity:confidence | 样本数 | 5日均收益 |
|----------------------|--------|----------|
| low:high | 339 | -1.14% |
| low:medium | 131 | +0.90% |
| medium:high | 64 | -1.50% |
| low:low | 14 | -3.58% |
| medium:medium | 12 | -3.85% |

### Missed Opportunity by Agent

10 项 missed opportunity 均为 low_signal_noise 标签，其中 3 项 5 日正收益超过 10%。

## 当前结论

### 1. ranking_score 高分桶是否优于低分桶

**不明显。** 高分桶样本为 0，中分桶（26 样本）5日均收益 -0.86%，低分桶（534 样本）5日均收益 -0.71%。中分桶反而略差。ranking_score 的区分度不足。

### 2. opportunity_score 是否有解释力

**有限。** 高分桶样本为 0，中分桶（6 样本）5日均收益 -3.01%，低分桶（554 样本）-0.68%。中分桶表现更差，与预期相反。

### 3. confidence_score 是否只是标签可信度而非机会强度

**是。** 高置信度（405 样本）5日均收益 -1.21%，中置信度（139 样本）+0.86%，低置信度（16 样本）-3.58%。中置信度反而表现最好，说明 confidence_score 反映的是标签确定性而非机会强度。

### 4. conflicted 标签后续表现是否偏弱

**是。** conflicted（39 样本）5日均收益 -3.94%，正收益率仅 4.55%，是所有标签中最差的。conflicted 标签有效识别了弱势板块。

### 5. oversold_rebound_candidate 是否有 3-5 日修复特征

**不明显。** oversold_rebound_candidate（22 样本）3日均收益 -0.32%，5日均收益 -0.77%，未见明显修复。10日均收益 -5.22% 更差。

### 6. low_signal_noise 是否样本过多、区分度不足

**是。** low_signal_noise 占总样本的 79.3%（444/560），5日均收益 -0.17%，接近市场均值。该标签区分度不足，未能有效筛选板块。

### 7. insufficient_data 是否被正确排除或降权

**部分正确。** insufficient_data（14 样本）5日均收益 -3.58%，表现较差。但该标签仍参与了排名，未被完全排除。

### 8. Agent 级别分析的局限性

当前 Agent 回测显示所有 Agent 性能一致，原因是 research report 中的 agent_votes 均为 neutral，未产生有效的 Agent 级别区分。需要进一步检查 Agent 投票逻辑。

## 下一步建议

1. **优化 low_signal_noise 标签**: 当前 79% 的样本被标记为 low_signal_noise，需要调整阈值或增加新的标签维度，提高区分度。

2. **检查 Agent 投票逻辑**: 所有 Agent 均投 neutral 票，需要检查 Agent 评分和投票机制是否正常工作。

3. **增加高分样本**: ranking_score 和 opportunity_score 的高分桶样本为 0，需要检查评分分布，可能需要调整评分公式。

4. **验证 oversold_rebound_candidate**: 该标签未显示预期的修复特征，需要检查超卖判断逻辑。

5. **考虑时间窗口**: 当前回测使用固定 5/10 日窗口，可能需要测试不同时间窗口的敏感性。

6. **补充概念板块回测**: 本次仅运行行业板块回测，概念板块数据已就绪，可作为对照组。

## 附录：报告路径

| 报告 | 路径 |
|------|------|
| Replay daily summary | `reports/theme_sector_radar/replay_runs/2026-06-01_to_2026-06-29/` |
| Research range summary | `reports/sector_research/range_runs/2026-06-01_to_2026-06-29/` |
| Sector research backtest | `reports/backtests/sector_research/2026-06-01_to_2026-06-29/` |
| Agent layer backtest | `reports/backtests/agent_layers/2026-06-01_to_2026-06-29/` |

---

*本报告仅用于板块研究、观察和复盘，不构成投资建议。*
