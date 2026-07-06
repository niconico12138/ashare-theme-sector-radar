# Phase 58: 全项目同类问题审计

> 审计日期: 2026-07-02
> 审计范围: theme-sector-radar-dev 全项目
> 审计类型: 跨模块语义一致性审计 (不修复代码)
> 前置: Phase 57 趋势评分层修复

---

## 1. 审计范围

本审计对 theme-sector-radar-dev 项目进行系统性扫描，检查 Phase 57 已修复的问题类型是否在其他模块中仍然存在。审计覆盖以下目录和文件：

| 目录/文件 | 说明 |
|-----------|------|
| `scoring/` | 评分层: sector_composite_score, short_term_burst_score, risk_score, focus_level, concept_score, industry_score |
| `agents/` | Agent 层: sector_scoring, sector_research (coordinator, vote_aggregator, veto, catalyst, market_regime), sector_rotation, sector_diagnosis, multi_window_consensus |
| `backtest/` | 回测层: sector_research_backtest, agent_layer_backtest, catalyst_event_backtest, opportunity_rebound_analysis, market_regime_analysis, replay_daily |
| `reports/` | 报告层: markdown_report, json_report, sector_score_report, sector_research_report |
| `data/` | 数据层: benchmark_provider, akshare_provider, providers |
| `cli.py` | CLI 入口: 历史指标计算, 趋势窗口截取 |
| `analysis/` | 分析工具: sector_history_analyzer |

---

## 2. Phase 57 已修复问题摘要

Phase 57 修复了以下 6 个关键问题：

| # | 问题 | 文件 | 修复内容 |
|---|------|------|----------|
| 1 | 收益率单位混用 | `sector_composite_score.py` | `recent_returns` / `total_return` / `max_drawdown` / `volatility` 统一为百分数点 |
| 2 | max_drawdown 重复 *100 | `sector_composite_score.py` | 移除 `drawdown_pct * 100` 错误放大 |
| 3 | 动量加权方向错误 | `sector_composite_score.py:145` | `recent_returns[i] * (i + 1)` → 晚期(近期)权重更高 |
| 4 | trend_window 与 benchmark window 对齐 | `sector_scoring_agent.py:160` | benchmark_key 根据 trend_window 选择对应窗口 |
| 5 | insufficient_history 无上限 | `sector_composite_score.py:694-715` | 新增 `apply_insufficient_history_cap`，上限 34.9 |
| 6 | 测试通过 | 838 passed | — |

---

## 3. 全项目同类问题扫描结果

### 3.1 收益率单位混用 (Type 1)

**扫描方法**: 搜索 `*100`, `/100`, `pct_change`, `change_pct`, 百分号格式

**结论**: 整体一致性较好。以下是与收益率单位相关的分析要点：

#### ✅ 一致的用法 (无问题):

| 文件 | 行号 | 代码 | 说明 |
|------|------|------|------|
| `data/benchmark_provider.py` | 207 | `(curr-prev)/prev * 100` | 生成百分数点，与 scoring 层一致 |
| `backtest/sector_research_backtest.py` | 203 | `(close-prev)/prev * 100` | 生成百分数点，forward return 一致 |
| `backtest/catalyst_event_backtest.py` | 246 | `(close-prev)/prev * 100` | 同上 |
| `backtest/opportunity_rebound_analysis.py` | 276,309,344,364 | `* 100` | 同上 |
| `backtest/agent_reliability.py` | 212 | `* 100` | 同上 |
| `backtest/agent_layer_backtest.py` | 221 | `* 100` | 同上 |
| `backtest/market_regime_analysis.py` | 265,270,274,461 | `* 100` | 同上 |
| `cli.py` | 2436 | `(curr-prev)/prev * 100` | 同上 |
| `analysis/sector_history_analyzer.py` | 170,199 | `* 100` | 同上 |

**所有收益率生成路径统一使用 `(new-old)/old * 100` 模式，输出百分数点。评分层阈值均按百分数点设计。** 收益率单位混用问题在 Phase 57 修复后，**其余模块无新增混用**。

#### ❌ 发现问题: `generate_risk_reasons` 格式串单位不匹配

详见下方 4.1 节。

---

### 3.2 窗口不一致 (Type 2)

**扫描方法**: 搜索 `trend_window`, `benchmark_window`, `forward_`, `lookahead`

#### ✅ 正确的对齐:

| 检查项 | 文件 | 结论 |
|--------|------|------|
| trend_window 传到 scoring | `sector_scoring_agent.py:110-140` | 正确截取 `recent_returns[-trend_window:]` |
| benchmark_key 映射 | `sector_scoring_agent.py:160` | `f"{trend_window}d"` 映射正确 |
| benchmark_returns 支持 1/3/5/10/20d | `benchmark_provider.py:220-273` | 返回所有窗口 |
| 非标准窗口回退 | `sector_scoring_agent.py:163-164` | 有 warning 回退 |
| lookahead 检查存在 | `replay_daily_from_sector_history.py:536-542` | 有完整检查 |
| lookahead 检查存在 | `market_regime_analysis.py:650-651` | 有完整检查 |
| signal_date 对齐 | `generate_research_range.py:100` | `history_end = signal_date` |

**结论**: 窗口对齐机制已完善，未发现 lookahead 违规。

#### ⚠️ 边界情况 (非 bug，但值得注意):

- `sector_scoring_agent.py:141`: `trend_window * 0.5` 作为 insufficient 阈值——如果 trend_window=20 且实际只有 10 天，会被标记为 "ok"。这意味着 **50% 覆盖率就算 ok**，可能太宽松。建议观察回测数据。
- `replay_daily_from_sector_history.py:303`: 使用 history_end_date 当天数据计算 change_pct，但在回测中 `history_end = signal_date`，依赖调用方正确设置。

---

### 3.3 权重方向错误 (Type 3)

**扫描方法**: 搜索 `weighted_sum`, `(i+1)`, `(n-i)`, 权重注释

#### ✅ Phase 57 已修复:

| 文件 | 函数 | 代码 | 方向 |
|------|------|------|------|
| `sector_composite_score.py:145` | `calculate_momentum_component` | `recent_returns[i] * (i + 1)` | ✅ 近期权重更高 |

#### ⚠️ 发现反向权重:

| 文件 | 行号 | 函数 | 代码 | 方向 |
|------|------|------|------|------|
| `agents/sector_rotation/sector_rotation_agent.py:101` | `_calculate_momentum_change` | `recent_returns[i] * (n - i)` | ❌ 早期权重更高 |

**详情**: `_calculate_momentum_change` 中 `recent_returns[i] * (n - i)` 给 i=0 (最早期的数据) 权重 n，给 i=n-1 (最近期的数据) 权重 1。这与 `calculate_momentum_component` 中 `(i+1)` 的方向相反。

**影响**: 这个函数用于 `sector_rotation_agent` 的动量变化判断（非 scoring 主线），用于判断板块轮动阶段。权重方向反转会导致对近期价格变化不敏感，偏向长期趋势。**中等影响**。

---

### 3.4 缺数据反而得分 (Type 4)

**扫描方法**: 搜索 `history_days == 0`, `insufficient_history`, 基础分/默认分赋值

#### ✅ 已有防护:

| 位置 | 机制 | 效果 |
|------|------|------|
| `sector_composite_score.py:694-715` | `apply_insufficient_history_cap` | 趋势分上限 34.9 |
| `sector_scoring_agent.py:231-239` | 调用 cap | 应用到最终趋势分 |
| `sector_composite_score.py:718-745` | `generate_data_warnings` | 生成 warning 文本 |
| `multi_window_consensus_agent.py:137-138` | `_check_insufficient_history` | 返回 insufficient_history 标签 |
| `veto_rule_agent.py:45-52` | data 不足 veto | 触发 veto + ranking_penalty |

#### ⚠️ 发现缺口: 短线爆发分 (burst score) 无 insufficient_history cap

`short_term_burst_score.py` 的 `calculate_short_term_burst_score`:
- 当 `history_days=0` 且 `price_change_available=False` 时，仅 radar_score 和默认分贡献
- `radar_today_component` (0-30分) 不依赖历史数据，可以直接给分
- `one_day_change_component` 缺失时给 0
- `three_day_momentum_component` 不足 3 天时给 `weight * 0.3 = 4.5`
- `data_quality_component` 用 `history_factor = 0.7` (当 history_days=0)
- `burst_risk_penalty` 最大减免（无 one_day_change 时不扣分）

**结果**: 一个 history_days=0 的板块，如果 radar_score 很高 (如 90)，可以得到：
- radar_today: 27
- one_day_change: 0
- three_day_momentum: 4.5
- volume_or_heat: ~5 (中性)
- rank_jump: ~5 (中性)
- data_quality: ~1.4
- burst_risk: 0
- **总计: ~42.9** → burst_fading (>= 35)

**但趋势分会因 insufficient_history_cap 被限制到 34.9。** 问题在于：趋势分和爆发分给出了不一致的信号——趋势分说 "不够数据不敢信"，但爆发分说 "短线看还行"。

**建议**: 对 burst_score 也添加 insufficient_history_cap 或至少将 data_warnings 传递到 burst 上下文。中等优先级。

---

### 3.5 风险扣分语义 (Type 5)

**扫描方法**: 搜索 `risk_penalty`, `final_score`, `positive_score - risk`

#### ✅ 全部正确:

所有风险扣分路径均使用 **正数扣分 + `final_score = positive_score - risk_penalty`** 语义。扫描结果：

| 文件 | 行号 | 语义 | 状态 |
|------|------|------|------|
| `scoring/sector_composite_score.py` | 542 | `final_score = max(positive_score - risk_penalty, 0.0)` | ✅ |
| `scoring/short_term_burst_score.py` | 416 | `final_score = max(positive_score - burst_risk, 0.0)` | ✅ |
| `scoring/focus_level.py` | 38 | `final_score = positive_score - risk_penalty` | ✅ |
| `scoring/risk_score.py` | 173 | `risk_penalty 为正数，表示总扣分值` | ✅ |
| `scoring/risk_score.py` | 37 | `penalty += abs(penalty_config.get("overheat_max", -20)) * 0.6` | ✅ |
| `agents/ranking_report/sector_ranking_agent.py` | 59-60 | `risk_penalty = risk_breakdown["total_penalty"]`; `final_score = positive_score - risk_penalty` | ✅ |
| `agents/defense_risk/sector_risk_agent.py` | 28 | 调用 `calculate_risk_penalty` | ✅ |
| `agents/sector_diagnosis/sector_diagnosis_agent.py` | 118-124 | `if risk_penalty >= 15/10/5:` | ✅ |
| `agents/sector_research/risk_control_agent.py` | 39-40 | `risk_penalty = score_data.get("risk_penalty", 0.0)`; `score = 1.0 - (risk_penalty / 20.0)` | ✅ |

**结论**: 风险扣分语义在全部模块中一致，未发现旧版负数语义残留。

---

### 3.6 Report-only Agent 是否误入决策 (Type 6)

**扫描方法**: 搜索 `report_only`, `decision_impact`, `vote`, `veto`

#### ✅ Report-only 标记正确:

| Agent | 文件 | decision_impact | vote | veto |
|-------|------|-----------------|------|------|
| CatalystEventAgent | `catalyst_event_agent.py:74,99,128` | report_only | neutral | False |
| MarketRegimeContext | `market_regime_context.py:132,234` | report_only | — | — |

两个 report-only Agent 均正确标记，且 vote 始终为 "neutral"，veto 始终为 False。

#### ❌ 发现问题: Vote 聚合器不区分 report-only

`coordinator.py:316-328`:
```python
all_opinions = self._convert_to_opinions([...7 agents...])
all_opinions.append(persistence_opinion)
all_opinions.append(catalyst_opinion)  # <-- report-only, vote=neutral
```

`agent_vote_aggregator.py:36-44`:
```python
positive_votes = sum(1 for o in opinions if o.vote == "positive")
neutral_votes = sum(1 for o in opinions if o.vote == "neutral")  # <-- 包括 catalyst
negative_votes = sum(1 for o in opinions if o.vote == "negative")
# ...
positive_ratio = positive_votes / total_votes  # <-- total 包含 report-only
```

**影响**: CatalystEvent agent (vote=neutral) 被计入 `total_votes`，稀释了 `positive_ratio`。
- 如果 7 个决策 agent 中 4 个 positive，`positive_ratio = 4/8 = 0.5` → "mixed_signals"
- 如果排除 report-only，`positive_ratio = 4/7 ≈ 0.57` → 仍是 "mixed_signals" 但更接近 majority
- 边际影响约 6-8% 的比率偏移。

同时，`vote_opinion` 被传递给 `confidence_calibration_agent.calibrate()` (coordinator.py:343)，间接影响 `calibrated_confidence_score`。

**严重程度**: 中等。report-only agent 不应该参与 vote aggregation。建议在 `agent_vote_aggregator.aggregate()` 或 `coordinator` 中过滤 `decision_impact == "report_only"` 的 opinions。

---

### 3.7 回测 Forward Return 正确性 (Type 7)

**扫描方法**: 搜索 `_compute_forward_returns`, `forward_`, signal_date 逻辑

#### ✅ 所有回测模块的 forward return 计算正确:

| 模块 | 起始基准 | Lookahead | 状态 |
|------|----------|-----------|------|
| `sector_research_backtest.py:173-210` | signal_date 之后的记录 | 无 (record_date > signal_date) | ✅ |
| `catalyst_event_backtest.py:226-261` | signal_date_idx+1 | 无 | ✅ |
| `opportunity_rebound_analysis.py:264-291` | signal_idx+1 | 无 | ✅ |
| `agent_layer_backtest.py:86-88` | 使用 sector_research_backtest 的 `_compute_forward_returns` 逻辑 | 无 | ✅ |

#### ⚠️ 边界情况: Forward return 第一日计算

以 `sector_research_backtest.py:190-207` 为例：
```python
prev_close = None
for record in future_records:
    close = record.get("收盘价", 0)
    record_prev_close = record.get("前收盘", 0)
    if record_prev_close > 0:
        prev_close = record_prev_close      # 使用该记录的"前收盘"
    elif prev_close is None:
        prev_close = close                   # 第一天：使用当天的收盘价
    if prev_close > 0:
        ret = (close - prev_close) / prev_close * 100
    ...
```

当第一天记录有"前收盘"字段且值等于 signal_date 收盘价时，计算正确。
当没有"前收盘"字段时，第一天 ret = 0（因为 prev_close = close），相当于丢失了这 1 天的收益。

**影响**: 保守估计，略微低估 forward return。不会造成误判（不会把差的板块判成好的）。低优先级。

---

### 3.8 中英文报告字段一致性 (Type 8)

**扫描方法**: 搜索中文 label 翻译，markdown 建议措辞

#### ✅ 双语字段正确分离:

| 文件 | 英文字段 | 中文字段 | 状态 |
|------|----------|----------|------|
| `sector_scoring_agent.py:257-258` | `selection_level` | `selection_level_cn` | ✅ |
| `sector_scoring_agent.py:262-263` | `trend_level` | `trend_level_cn` | ✅ |
| `sector_scoring_agent.py:266-267` | `burst_level` | `burst_level_cn` | ✅ |
| `sector_research_report.py:184` | `volatility_regime` | `波动率` | ✅ |

#### ✅ Markdown 报告无买卖建议:

扫描了所有 `reports/*.py` 文件，未发现 "买入"、"卖出"、"建议操作" 等措辞。报告使用研究导向语言：观察、关注、回避、谨慎。

---

## 4. 高优先级问题列表

### 4.1 `generate_risk_reasons` — max_drawdown 格式串单位不匹配

| 属性 | 值 |
|------|-----|
| **文件** | `scoring/sector_composite_score.py:637-640` |
| **函数** | `generate_risk_reasons` |
| **类型** | 收益率单位混用 + 格式串错误 |
| **严重程度** | 高 (显示文本错误，但影响用户判断) |

**证据**:
```python
# 第 637-640 行
if abs(max_drawdown) > 0.1:           # ← 阈值是小数标准 (0.1 = 0.1% 太小了)
    reasons.append(f"最大回撤较大 ({max_drawdown:.1%})")    # ← .1% 格式会把 -8.68 渲染为 -868.0%
elif abs(max_drawdown) > 0.05:        # ← 同上
    reasons.append(f"存在一定回撤 ({max_drawdown:.1%})")
```

**分析**: 
- `max_drawdown` 参数实际接收百分数点值 (如 -8.68)
- 阈值 `0.1` / `0.05` 是针对小数值设计的
- `:.1%` Python 格式化会把值 × 100 再添加 `%`，导致 -8.68 显示为 "-868.0%"
- 正确阈值应为约 `5.0` / `3.0` (百分数点)
- 正确格式应为 `{max_drawdown:.1f}%` (对于百分数点输入)

**影响**: 风险原因文本中显示错误的回撤百分比，可能误导使用者。不影响评分计算。

**修复建议**: 
```python
if abs(max_drawdown) > 5.0:
    reasons.append(f"最大回撤较大 ({max_drawdown:.1f}%)")
elif abs(max_drawdown) > 3.0:
    reasons.append(f"存在一定回撤 ({max_drawdown:.1f}%)")
```

### 4.2 Vote 聚合器包含 report-only Agent

| 属性 | 值 |
|------|-----|
| **文件** | `agents/sector_research/coordinator.py:316-328`, `agents/sector_research/agent_vote_aggregator.py:36-44` |
| **函数** | `coordinator.analyze_sectors`, `AgentVoteAggregator.aggregate` |
| **类型** | report-only Agent 误入决策 |
| **严重程度** | 高 (影响 vote ratio 和 confidence calibration) |

**证据**:
```python
# coordinator.py:316-328
all_opinions = self._convert_to_opinions([...7 agents...])
all_opinions.append(persistence_opinion)
all_opinions.append(catalyst_opinion)  # ← report-only, vote=neutral

# agent_vote_aggregator.py:36-44
positive_votes = sum(1 for o in opinions if o.vote == "positive")
neutral_votes = sum(1 for o in opinions if o.vote == "neutral")  # ← 包含 catalyst
positive_ratio = positive_votes / total_votes  # ← total_votes 含 report-only
```

- `catalyst_opinion` 明确设置了 `decision_impact: "report_only"`, `vote="neutral"`, `veto=False`
- 但 `AgentVoteAggregator` 不检查 `decision_impact`，直接统计所有 opinion
- `catalyst_opinion` 的 neutral vote 被纳入统计，稀释了 positive_ratio
- `vote_opinion` 还被传递给 `ConfidenceCalibrationAgent.calibrate()`，间接影响置信度校准

**影响**: vote 聚合结果的 positive_ratio 偏低约 6-8%。confidence_calibration 可能受轻微影响。

**修复建议**: 在 `AgentVoteAggregator.aggregate()` 中过滤 `decision_impact == "report_only"` 的 opinions，或在 `coordinator` 中不将 report-only opinions 传入 vote aggregator。

---

## 5. 中优先级问题列表

### 5.1 短线爆发分 (burst score) 无 insufficient_history cap

| 属性 | 值 |
|------|-----|
| **文件** | `scoring/short_term_burst_score.py:327-436` |
| **函数** | `calculate_short_term_burst_score` |
| **类型** | 缺数据反而得分 |
| **严重程度** | 中 |

**证据**: 趋势分有 `apply_insufficient_history_cap` (cap 到 34.9)，但 burst score 没有。history_days=0 的板块可以获得来自 radar_score 的 0-30 分。

**修复建议**: 对 `calculate_short_term_burst_score` 添加 history_days / coverage 检查，或在 `sector_scoring_agent` 中对 burst score 也应用上限。

### 5.2 `_calculate_momentum_change` 权重方向反转

| 属性 | 值 |
|------|-----|
| **文件** | `agents/sector_rotation/sector_rotation_agent.py:101` |
| **函数** | `_calculate_momentum_change` |
| **类型** | 权重方向错误 |
| **严重程度** | 中 |

**证据**: `recent_returns[i] * (n - i)` — 早期数据获得更高权重 (与 Phase 57 修复的方向相反)。

**影响**: 这个函数用于板块轮动判断（非主评分链），影响 rotation_phase 的判断。数据点较少时影响可能较大。

**修复建议**: 改为 `recent_returns[i] * (i + 1)` 或至少添加注释解释为什么此处故意使用相反方向。

### 5.3 `sector_history_analyzer._calculate_max_drawdown` 符号约定与 scoring 层不一致

| 属性 | 值 |
|------|-----|
| **文件** | `analysis/sector_history_analyzer.py:199` |
| **函数** | `_calculate_max_drawdown` |
| **类型** | 符号约定不一致 |
| **严重程度** | 中 (分析层与评分层隔离，但容易引起混淆) |

**证据**:
```python
# sector_history_analyzer.py:199 — 返回正数
drawdown = (peak - trough) / peak * 100
max_drawdown = max(max_drawdown, drawdown)  # 如 8.68

# scoring/sector_composite_score.py:271 — 期望负数
drawdown_pct = abs(max_drawdown)  # max_drawdown 是负数百分数点

# cli.py:2456-2458 — 生成负数
drawdown = cumulative - peak  # 如 -8.68
if drawdown < max_drawdown:
    max_drawdown = drawdown
```

**影响**: `sector_history_analyzer` 输出的 max_drawdown_5d 是正数 (如 8.68)，而 scoring 层期望负数 (如 -8.68)。由于这两个路径隔离（分析结果不进入评分），当前不会导致计算错误，但未来如果有人混用这两个路径，会导致 `abs(-8.68)` vs `abs(8.68)` 虽然结果相同但语义混乱。

**修复建议**: 在 `sector_history_analyzer.py:199` 统一为负数约定，或至少添加文档说明符号约定。

---

## 6. 暂不修复 / 非问题列表

| # | 描述 | 位置 | 判定 |
|---|------|------|------|
| 1 | Forward return 第一日 calc 保守 | `sector_research_backtest.py:195` | 非 bug：保守估计，不会造成误判 |
| 2 | `* 100` 转换一致性 | 全项目 | 非问题：所有模块统一使用百分数点 |
| 3 | Lookahead 检查 | `replay_daily`, `market_regime_analysis` | 非问题：检查机制完整 |
| 4 | `benchmark_returns` 回退逻辑 | `sector_scoring_agent.py:163-164` | 非问题：有 warning + 回退 |
| 5 | `risk_score.py:37,43,84` 使用 `abs()` | `scoring/risk_score.py` | 非问题：config 值可能为负数，abs() 后正数使用 |
| 6 | `concept_score.py:32,184,226` price_change_available 检查 | `scoring/concept_score.py` | 非问题：正确处理了缺数据情况 |
| 7 | `focus_level.py:43-47` 涨跌幅不可用降级 | `scoring/focus_level.py` | 非问题：正确处理 |
| 8 | `market_regime_analysis.py:354-370` 波动率判断 | `backtest/market_regime_analysis.py` | 非问题：逻辑正确 |
| 9 | Markdown 报告无买卖建议 | `reports/*.py` | 非问题：符合要求 |
| 10 | 中英文字段分离 | 全项目 | 非问题：英文字段保留，中文仅展示 |
| 11 | CatalystEventAgent 保持 report-only | `catalyst_event_agent.py` | 非问题：vote=neutral, veto=False，无违规 |
| 12 | MarketRegimeContext report-only | `market_regime_context.py` | 非问题：decision_impact=report_only |
| 13 | Risk penalty 全模块正数语义 | 全项目 | 非问题：无旧版负数语义残留 |

---

## 7. 建议 Phase 59 修复计划

按优先级排序：

### Phase 59a: 高优先级修复 (预计 2-3 小时)

1. **`generate_risk_reasons` 格式串修复** (`sector_composite_score.py:637-640`)
   - 将阈值从 0.1/0.05 改为 5.0/3.0
   - 将格式串从 `:.1%` 改为 `:.1f}%`
   - 新增单元测试覆盖 `generate_risk_reasons` 的边界情况

2. **Vote 聚合器过滤 report-only Agent** (`agent_vote_aggregator.py`)
   - 在 `aggregate()` 中添加 `decision_impact == "report_only"` 过滤
   - 或添加 `include_report_only: bool = False` 参数
   - 新增测试验证 report-only agents 不参与 vote 计算

### Phase 59b: 中优先级修复 (预计 1-2 小时)

3. **Burst score insufficient_history cap** (`short_term_burst_score.py`)
   - 添加与 trend score 类似的上限机制
   - 或至少在 burst score 输出中包含 data coverage 的 warning/flag

4. **`_calculate_momentum_change` 权重方向** (`sector_rotation_agent.py:101`)
   - 确认这是否为有意设计（"动量变化"可能需要反向权重）
   - 如非有意，改为 `recent_returns[i] * (i + 1)`

5. **`sector_history_analyzer` max_drawdown 符号约定** (`sector_history_analyzer.py:199`)
   - 统一为负数约定，或在 docstring 中明确说明

---

## 8. 建议新增测试清单

### 8.1 单元测试

| 测试文件 | 测试内容 | 对应问题 |
|----------|----------|----------|
| `test_sector_composite_score.py` | `test_generate_risk_reasons_drawdown_format` | 4.1 |
| `test_sector_composite_score.py` | `test_generate_risk_reasons_drawdown_thresholds` | 4.1 |
| `test_sector_composite_score.py` | `test_burst_score_insufficient_history` | 5.1 |
| `test_agent_vote_aggregator.py` (新增) | `test_report_only_agents_excluded` | 4.2 |
| `test_agent_vote_aggregator.py` (新增) | `test_vote_ratio_without_report_only` | 4.2 |
| `test_sector_rotation_agent.py` | `test_momentum_change_weight_direction` | 5.2 |
| `test_sector_history_analyzer.py` | `test_max_drawdown_sign_convention` | 5.3 |

### 8.2 集成测试

| 测试内容 | 对应问题 |
|----------|----------|
| 验证 score_mode=dual 时 burst_score 不受 insufficient_history cap 影响 | 5.1 |
| 验证 sector_research 输出中 vote 统计不含 catalyst_event | 4.2 |
| 端到端: history_days=0 板块的趋势分 + 爆发分对比 | 5.1 |

---

## 9. 是否修改 ai-hedge-fund: 否

本次审计及后续修复范围**严格限定在 theme-sector-radar-dev 项目内**，不涉及 ai-hedge-fund 项目。

---

## 附录: 审计搜索结果统计

| 搜索关键词 | 匹配次数 | 有问题的匹配 |
|------------|---------|-------------|
| `*100` / `* 100` | 22+ | 0 (全部一致) |
| `max_drawdown` | 40+ | 2 (格式串 + 符号约定) |
| `volatility` | 50+ | 0 |
| `recent_returns` | 50+ | 0 |
| `forward_` | 30+ | 0 (保守边界) |
| `benchmark_returns` | 3 | 0 |
| `history_days` | 40+ | 0 |
| `coverage` | 30+ | 0 |
| `insufficient_history` | 15+ | 0 |
| `price_change_available` | 30+ | 0 |
| `risk_penalty` | 40+ | 0 |
| `final_score` | 25+ | 0 |
| `decision_impact` | 6 | 2 (未过滤) |
| `report_only` | 8 | 0 |
| `vote` | 40+ | 1 (聚合器) |
| `veto` | 30+ | 0 |
| `lookahead` | 15+ | 0 |
