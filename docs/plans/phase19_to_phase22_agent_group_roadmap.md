# Phase 19-22 Agent Group Roadmap

## 目标

本路线图用于规划板块评分项目后续的 Agent 组建设。

当前项目已经具备：

- 日报雷达数据链路
- AkShare + THS fallback 数据源
- 行业/概念历史数据下载
- 5/10/20 标准趋势窗口
- trend_weight_profile 权重方案
- trend_continuation_score 趋势持续分
- short_term_burst_score 短线爆发分
- sector_scores JSON/Markdown 报告

后续目标不是替代现有评分公式，而是在现有结构化评分基础上新增多维 Agent 组，用于输出更清晰、可解释、可测试的板块综合研判结果。

## 总体原则

1. 不修改 `E:\Workspace\ai-stock-projects\ai-hedge-fund` 原项目。
2. 不输出 buy/sell/hold、买入、卖出、持有、个股推荐、建仓、止盈、止损等交易建议。
3. 第一版 Agent 组必须是规则型、可测试、可解释，不依赖 LLM 和联网新闻。
4. Agent 只做观察、确认、分歧识别、风险提示和复盘辅助，不做自动交易决策。
5. 保留现有评分公式，新增 Agent 只消费现有评分结果和数据质量信息。
6. 每个阶段必须有测试、样例命令、报告输出和完成汇总。

## 推荐执行顺序

```text
Phase 19: Multi-window Consensus Agent
Phase 20: Sector Research Agent Group
Phase 21: Sector Research Report
Phase 22: Agent Group Backtest and Stability Evaluation
```

建议先做 Phase 19，再做 Phase 20。原因是 Agent 组的技术面判断需要先建立在 5/10/20 多窗口共识之上。

---

# Phase 19: Multi-window Consensus Agent

## 阶段目标

新增多窗口趋势共识智能体，把同一板块在 5日、10日、20日窗口下的趋势评分合并为一个可解释的共识判断。

它解决的问题是：不要只看单一窗口的 Top5，而是判断趋势是否跨窗口成立。

## 新增 Agent

建议新增目录：

```text
theme_sector_radar/agents/multi_window_consensus/
```

建议新增文件：

```text
theme_sector_radar/agents/multi_window_consensus/__init__.py
theme_sector_radar/agents/multi_window_consensus/multi_window_consensus_agent.py
```

## 输入

每个板块需要输入 5/10/20 三个窗口下的评分结果：

```text
sector_name
sector_type
window_5.trend_continuation_score
window_10.trend_continuation_score
window_20.trend_continuation_score
window_5.trend_level
window_10.trend_level
window_20.trend_level
window_5.actual_history_days
window_10.actual_history_days
window_20.actual_history_days
window_5.history_coverage_ratio
window_10.history_coverage_ratio
window_20.history_coverage_ratio
window_5.trend_window_status
window_10.trend_window_status
window_20.trend_window_status
```

## 输出

每个板块输出：

```json
{
  "sector_name": "医疗服务",
  "multi_window_label": "short_mid_strong_long_weak",
  "consensus_score": 62.5,
  "consensus_strength": "medium",
  "window_scores": {
    "5": 48.1,
    "10": 43.1,
    "20": 28.1
  },
  "window_conflicts": [
    "20日趋势分明显弱于5日和10日"
  ],
  "watch_points": [
    "观察20日趋势分是否继续抬升"
  ],
  "data_warnings": []
}
```

## 标签规则

建议第一版使用以下标签：

```text
multi_window_confirmed
5日、10日、20日窗口均较强，趋势跨窗口确认。

short_mid_strong_long_weak
5日和10日相对较强，但20日偏弱，说明趋势可能正在形成但中期确认不足。

short_active_only
只有5日窗口较强，短线活跃但趋势未确认。

long_stable_short_cooling
20日较稳，但5日转弱，说明中期趋势仍在，但短线降温。

weak_all_windows
5日、10日、20日均弱。

conflicted_windows
窗口之间分歧较大，暂不形成明确结论。

insufficient_history
任一关键窗口历史覆盖不足，不能确认。
```

## 建议阈值

第一版可采用保守阈值：

```text
强: trend_continuation_score >= 65
中: trend_continuation_score >= 50
弱: trend_continuation_score < 50

coverage ok: history_coverage_ratio >= 1.0
coverage warning: history_coverage_ratio < 1.0
```

如实际分数整体偏低，可以先输出相对排名和分位数，但不要直接放宽阈值。

## CLI 建议

新增命令模式或参数：

```text
--multi-window-consensus
```

样例命令：

```bash
python -m theme_sector_radar.cli --multi-window-consensus \
  --as-of 2026-06-29 \
  --sector-type industry \
  --history-start-date 2026-05-20 \
  --history-end-date 2026-06-30 \
  --top-n 20 \
  --score-mode dual \
  --benchmark hs300 \
  --trend-weight-profile trend_confirmation
```

该命令内部应分别运行或读取 5/10/20 三个窗口结果，然后生成共识报告。

## 输出路径

```text
reports/sector_consensus/YYYY-MM-DD/multi_window_consensus.json
reports/sector_consensus/YYYY-MM-DD/multi_window_consensus.md
```

## 测试要求

新增测试文件建议：

```text
tests/theme_sector_radar/test_multi_window_consensus_agent.py
tests/theme_sector_radar/test_cli_multi_window_consensus.py
tests/theme_sector_radar/test_multi_window_consensus_report.py
```

测试点：

```text
1. 5/10/20 均强 -> multi_window_confirmed
2. 5/10 强、20弱 -> short_mid_strong_long_weak
3. 只有5日强 -> short_active_only
4. 20日强、5日弱 -> long_stable_short_cooling
5. 全窗口弱 -> weak_all_windows
6. coverage 不足 -> insufficient_history
7. JSON 报告字段完整
8. Markdown 报告不包含交易建议词
9. CLI 可正常生成报告
```

## 完成标准

```text
- 新 Agent 可以独立测试
- 5/10/20 窗口结果能被合并
- 输出 multi_window_label、consensus_score、window_conflicts、watch_points
- 报告路径固定
- 全量测试通过
```

---

# Phase 20: Sector Research Agent Group

## 阶段目标

建立板块综合研判 Agent 组，从技术面、短线热度、轮动、风险、数据质量、市场环境、产业叙事等多个维度输出综合确认结论。

这一阶段不改变现有评分公式，只读取已有评分结果和 Phase 19 多窗口共识结果。

## 新增目录

```text
theme_sector_radar/agents/sector_research/
```

建议文件：

```text
theme_sector_radar/agents/sector_research/__init__.py
theme_sector_radar/agents/sector_research/technical_trend_agent.py
theme_sector_radar/agents/sector_research/short_term_heat_agent.py
theme_sector_radar/agents/sector_research/rotation_analysis_agent.py
theme_sector_radar/agents/sector_research/risk_control_agent.py
theme_sector_radar/agents/sector_research/data_quality_agent.py
theme_sector_radar/agents/sector_research/market_context_agent.py
theme_sector_radar/agents/sector_research/narrative_agent.py
theme_sector_radar/agents/sector_research/consensus_decision_agent.py
theme_sector_radar/agents/sector_research/coordinator.py
```

## Agent 分工

### 1. TechnicalTrendAgent

技术面趋势智能体。

输入：

```text
trend_continuation_score
trend_level
trend_breakdown
trend_window
trend_weight_profile
multi_window_label
consensus_score
relative_strength_component
momentum_component
persistence_component
drawdown_component
volatility_component
```

输出：

```text
technical_label
technical_score
technical_reasons
technical_conflicts
technical_watch_points
```

### 2. ShortTermHeatAgent

短线热度智能体。

输入：

```text
short_term_burst_score
burst_level
burst_breakdown
radar_score
one_day_change
three_day_momentum
volume_or_heat_component
```

输出：

```text
heat_label
heat_score
heat_reasons
heat_conflicts
heat_watch_points
```

### 3. RotationAnalysisAgent

轮动分析智能体。

输入：

```text
rotation_phase
rank_change
score_change
rotation_tags
multi_window_label
```

输出：

```text
rotation_label
rotation_score
rotation_reasons
rotation_watch_points
```

### 4. RiskControlAgent

风险控制智能体。

输入：

```text
risk_penalty
risk_reasons
max_drawdown
volatility
drawdown_component
volatility_component
trend_window_status
```

输出：

```text
risk_label
risk_score
risk_flags
risk_summary
```

### 5. DataQualityAgent

数据质量智能体。

输入：

```text
history_source
actual_history_days
history_coverage_ratio
trend_window_status
provider_status
data_warnings
price_change_available
benchmark_status
```

输出：

```text
data_quality_label
data_quality_score
data_quality_warnings
data_reliability_summary
```

### 6. MarketContextAgent

市场环境智能体。

输入：

```text
market_temperature
benchmark_id
benchmark_name
benchmark_status
relative_strength_component
market_temperature_label
```

输出：

```text
market_context_label
market_context_score
market_context_summary
market_watch_points
```

### 7. NarrativeAgent

产业叙事智能体。

第一版必须是规则型，不联网，不接 LLM。

输入：

```text
sector_name
sector_type
known_sector_tags
```

输出：

```text
narrative_label
narrative_summary
narrative_watch_points
```

示例：

```text
医疗服务: 防御修复属性，关注行业景气和政策边际变化。
半导体: 科技成长属性，关注周期、国产替代、资本开支和风险偏好。
```

### 8. ConsensusDecisionAgent

最终共识确认智能体。

输入：

```text
technical_view
heat_view
rotation_view
risk_view
data_quality_view
market_context_view
narrative_view
```

输出：

```json
{
  "sector_name": "医疗服务",
  "consensus_label": "trend_confirmed_but_strength_limited",
  "confirm_level": "medium",
  "confidence_score": 0.68,
  "dimension_scores": {
    "technical": 0.62,
    "heat": 0.48,
    "rotation": 0.55,
    "risk": 0.70,
    "data_quality": 1.0,
    "market_context": 0.58,
    "narrative": 0.50
  },
  "main_reasons": [],
  "conflict_points": [],
  "watch_points": [],
  "data_warnings": []
}
```

## 共识标签

建议第一版标签：

```text
strong_consensus
技术、短线、轮动、市场环境多方一致。

trend_confirmed
趋势确认，但短线热度不一定强。

trend_confirmed_but_strength_limited
排名靠前但绝对分数不高，说明相对强但趋势强度有限。

short_term_active_unconfirmed
短线活跃，但趋势未确认。

rotation_candidate
轮动候选，正在升温但未充分确认。

defensive_watch
偏防御观察，强度有限但风险相对可控。

conflicted
多维信号冲突。

weak_or_avoid
趋势弱、风险高或多维评分偏低。

insufficient_data
数据不足，不能确认。
```

## 输出路径

Phase 20 可以先只生成 JSON，不急着做完整 Markdown：

```text
reports/sector_research/YYYY-MM-DD/sector_research.json
```

## 测试要求

新增测试建议：

```text
tests/theme_sector_radar/test_sector_research_agents.py
tests/theme_sector_radar/test_sector_research_coordinator.py
tests/theme_sector_radar/test_sector_research_contract.py
```

测试点：

```text
1. 每个子 Agent 输入输出字段稳定
2. data_quality 不足时最终 label 为 insufficient_data 或 confidence 降低
3. 技术强但短线弱时输出 trend_confirmed
4. 短线强但趋势弱时输出 short_term_active_unconfirmed
5. 风险高时 confirm_level 降级
6. 多维冲突时输出 conflicted
7. 输出不包含交易建议词
```

## 完成标准

```text
- Agent 组可以读取 sector_scores 和 multi_window_consensus
- 每个维度都有独立结论
- ConsensusDecisionAgent 输出最终综合确认结果
- JSON 报告字段稳定
- 全量测试通过
```

---

# Phase 21: Sector Research Report

## 阶段目标

把 Phase 20 的 Agent 组输出转换成可读 Markdown 报告，让结果更像投研复盘，而不是只有 JSON 字段。

## 新增报告模块

建议新增：

```text
theme_sector_radar/reports/sector_research_report.py
```

## 输出路径

```text
reports/sector_research/YYYY-MM-DD/sector_research.json
reports/sector_research/YYYY-MM-DD/sector_research.md
```

## Markdown 报告结构

```text
# 板块综合研判报告

## 免责声明
仅用于研究、观察和复盘，不构成投资建议。

## 综合确认 Top N
展示 consensus_label、confirm_level、confidence_score。

## 多窗口趋势共识
展示 5/10/20 日趋势分和 multi_window_label。

## 技术面观点
展示 TechnicalTrendAgent 输出。

## 短线热度观点
展示 ShortTermHeatAgent 输出。

## 轮动状态
展示 RotationAnalysisAgent 输出。

## 风险与冲突
展示 RiskControlAgent 和 conflict_points。

## 数据质量说明
展示 DataQualityAgent 输出。

## 市场环境说明
展示 MarketContextAgent 输出。

## 产业叙事说明
展示 NarrativeAgent 输出。

## 观察要点
展示 watch_points。
```

## 用词约束

允许：

```text
观察
确认
强弱
风险
分歧
待验证
跟踪
复盘
```

禁止：

```text
买入
卖出
持有
推荐
建仓
加仓
减仓
止盈
止损
目标价
```

## CLI 建议

新增参数：

```text
--research-agents
```

样例：

```bash
python -m theme_sector_radar.cli --research-agents \
  --as-of 2026-06-29 \
  --sector-type industry \
  --history-start-date 2026-05-20 \
  --history-end-date 2026-06-30 \
  --top-n 20 \
  --score-mode dual \
  --benchmark hs300 \
  --trend-weight-profile trend_confirmation
```

## 测试要求

新增测试建议：

```text
tests/theme_sector_radar/test_sector_research_report.py
tests/theme_sector_radar/test_cli_research_agents.py
```

测试点：

```text
1. Markdown 包含所有核心章节
2. JSON 和 Markdown 输出路径正确
3. 报告不包含交易建议词
4. CLI 能生成完整报告
5. 缺少 multi_window_consensus 时能降级或自动生成
```

## 完成标准

```text
- sector_research.md 可读
- JSON 字段稳定
- CLI 可一键生成
- 报告明确显示多 Agent 维度观点
- 全量测试通过
```

---

# Phase 22: Agent Group Backtest and Stability Evaluation

## 阶段目标

验证 Agent 组的综合研判是否有复盘价值，而不是只看起来合理。

## 输入

```text
多日 sector_scores
多日 multi_window_consensus
多日 sector_research
sector_history_cache
benchmark_cache
```

## 输出路径

```text
reports/backtests/sector_research/YYYY-MM-DD_to_YYYY-MM-DD/
  research_backtest.json
  research_backtest.md
```

## 评估维度

```text
1. 连续确认天数
2. 确认后 5/10/20 日板块表现
3. strong_consensus 样本后续表现
4. trend_confirmed 样本后续表现
5. short_term_active_unconfirmed 样本后续表现
6. conflicted 样本后续表现
7. insufficient_data 样本占比
8. 高 confidence_score 与后续表现的关系
9. 误判样本列表
10. 冲突样本列表
```

## CLI 建议

新增参数：

```text
--backtest-research-agents
--start-date
--end-date
```

样例：

```bash
python -m theme_sector_radar.cli --backtest-research-agents \
  --start-date 2026-06-01 \
  --end-date 2026-06-30 \
  --sector-type industry \
  --benchmark hs300
```

## 测试要求

新增测试建议：

```text
tests/theme_sector_radar/test_sector_research_backtest.py
```

测试点：

```text
1. 能读取多日 research 报告
2. 能计算各 label 后续表现
3. 能识别误判样本
4. 能生成 Markdown 复盘报告
5. 数据不足时不崩溃
```

## 完成标准

```text
- 可以评估 Agent 组输出的稳定性
- 可以区分哪些 consensus_label 更有复盘价值
- 输出误判和冲突样本
- 全量测试通过
```

---

# 当前推荐的下一步

优先做 Phase 19。

原因：

```text
1. 当前已经有 5/10/20 trend_window。
2. 历史数据已经补齐，20日窗口 actual_history_days=20，coverage_ratio=1.0。
3. Agent 组最核心的技术面依据就是多窗口共识。
4. 先把多窗口共识做好，Phase 20 的综合研判会更稳。
```

Phase 19 完成后，再进入 Phase 20。

# 后续提示词生成规则

每次只给 VS Code 一个阶段的提示词。

不要一次性要求实现 Phase 19-22。建议顺序：

```text
先给 Phase 19 提示词
等待完成汇总和测试结果
审计 Phase 19
再给 Phase 20 提示词
等待完成汇总和测试结果
审计 Phase 20
再给 Phase 21 提示词
最后做 Phase 22
```

这样可以保证 Agent 组不会变成不可测试的黑盒。
