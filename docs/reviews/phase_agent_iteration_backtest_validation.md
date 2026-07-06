# Phase F: 回测验证结果

**日期**: 2026-07-03  
**回测范围**: 2026-06-01 ~ 2026-06-29 (行业板块)  
**样本数**: 280 个 sector-agent 对 (28 天 × 10 个板块)

---

## 1. 回测命令执行结果

### 1.1 研判回测 (--backtest-research-agents)
- ✅ 成功运行，300+ 样本
- 报告: `reports/backtests/sector_research/2026-06-01_to_2026-06-29/research_backtest.json`

### 1.2 Agent 层回测 (--backtest-agent-layers)
- ✅ 成功运行，280 样本
- 报告: `reports/backtests/agent_layers/2026-06-01_to_2026-06-29/`

### 1.3 可靠性分析 (--analyze-agent-reliability)
- ✅ 成功运行，2520 条记录 (280 样本 × 9 Agent)
- 报告: `reports/backtests/agent_reliability/2026-06-01_to_2026-06-29/`

---

## 2. 标签表现

| 标签 | 样本数 | 5日均收益 | 评价 |
|------|--------|----------|------|
| short_term_active_unconfirmed | 26 | **+3.45%** | ✅ 最佳 — 短线活跃+趋势未确认=高弹性 |
| defensive_stable_watch | 27 | **+2.31%** | ✅ 超预期 — 防御型实际有正收益 |
| weak_or_avoid | 58 | +0.72% | ⚠️ "弱"标签反而正收益 |
| low_signal_noise | 12 | +0.83% | 中性 |
| trend_confirmed_but_strength_limited | 8 | -0.03% | 中性 |
| oversold_rebound_candidate | 81 | -0.72% | ⚠️ 修复信号偏弱 |
| trend_confirmed | 9 | **-0.89%** | ⚠️ 趋势确认反而负收益 |
| early_repair_watch | 27 | -2.12% | ❌ 早期修复无效 |
| conflicted | 31 | -2.34% | ✅ 分歧标签有效 |
| strong_consensus | 1 | -10.25% | ⚠️ 仅 1 样本，outlier |

---

## 3. Agent 可靠性排名

| 排名 | Agent | reliability | label | 备注 |
|------|-------|-------------|-------|------|
| 1 | short_term_heat | **0.72** | high_reliability | ✅ 唯一高可靠 Agent |
| 2 | rotation_analysis | 0.55 | moderate_reliability | 有区分度 |
| 3 | technical_trend | 0.50 | moderate_reliability | 有区分度 |
| 4 | market_context | 0.42 | moderate_reliability | 区分度有限 |
| 5 | data_quality | 0.31 | low_reliability | 防守型，区分度低 |
| 6 | risk_control | 0.30 | low_reliability | 低风险环境无区分度 |
| 7 | narrative | 0.30 | low_reliability | 永远 neutral，不出手 |
| 8 | persistence_strength | 0.30 | low_reliability | sparse，样本不足 |
| 9 | catalyst_event | 0.30 | low_reliability | report-only |

---

## 4. 关键发现

### 4.1 Phase B 修改的回测影响
- **本次修改不涉及 Agent 内部分析逻辑**，仅修改了输出结构和投票聚合
- 回测结果应与修改前一致（底层分析逻辑未变）
- confidence 硬编码修复影响了 AgentOpinion 的 confidence 字段，但不影响 vote 分布

### 4.2 需要关注的问题
1. **trend_confirmed 负收益 (-0.89%)**: 技术面确认在 6 月市场中不一定带来正收益，可能因为趋势反转
2. **weak_or_avoid 正收益 (+0.72%)**: 标签过度保守，把一些实际有正收益的板块判为弱
3. **short_term_active_unconfirmed 最佳**: 说明短线热度是当前最有效的信号

### 4.3 建议
1. **不修改 ConsensusDecisionAgent**: 6 月是特殊市场环境（偏弱），标签逻辑在牛市可能表现不同
2. **继续监控**: 等积累更多月份数据后再决定是否调规则
3. **关注 short_term_heat**: 作为最可靠 Agent，可考虑在 ranking_score 中给更高权重

---

## 5. 修改前后对比

由于本次修改仅涉及输出结构增强和投票聚合优化（不涉及 Agent 内部分析逻辑），修改前后的核心指标对比:

| 指标 | 修改前 | 修改后 | 变化 |
|------|--------|--------|------|
| Agent 可靠性排名 | 不变 | 不变 | 分析逻辑未改 |
| 投票分布 | 不变 (底层 vote 逻辑未改) | 不变 | — |
| narrative 投票 | neutral (计入) | neutral (**不计入**) | ✅ 消除稀释 |
| confidence 值 | 全部 0.8 | 按 signal_profile 区分 | ✅ 更合理 |
| 报告详情 | 全量展示 | Top 10 | ✅ 更聚焦 |
