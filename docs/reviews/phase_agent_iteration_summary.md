# Phase G: Agent 组迭代最终总结（合并两轮）

**迭代日期**: 2026-07-03  
**测试结果**: 864 passed, 0 failed, 19 warnings (预存在)

---

## 1. 修改文件完整列表

| # | 文件 | 类型 | 说明 |
|---|------|------|------|
| 1 | `opinion.py` | 增强 | AgentOpinion +signal_profile +decision_impact 字段 |
| 2 | `coordinator.py` | 修复+增强 | 删 3 个死代码 Agent; 修 result 变量 bug; confidence 不再硬编码 |
| 3 | `agent_vote_aggregator.py` | 增强 | 排除 low_information Agent 的投票 |
| 4 | `catalyst_event_agent.py` | 增强 | 所有 return 加 decision_impact="report_only" |
| 5 | `confidence_calibration_agent.py` | **Bug 修复** | data_quality_score → history_coverage_ratio |
| 6 | `sector_research_report.py` | 可读性 | Top 10 + 分数语义表 + Agent 决策说明 |
| 7 | `tests/test_signal_profile.py` | 更新 | expected_agents 列表 |
| 8 | `tests/test_agent_opinion_contract.py` | **新增** | 14 个契约测试 |

---

## 2. 修复的 Bug（含第二轮）

| # | 严重度 | Bug | 影响 | 修复 |
|---|--------|-----|------|------|
| 1 | P0 | PersistenceStrengthAgent 接收过期 result 变量 | 传入上一轮数据 | 传入空 dict |
| 2 | P0 | _convert_to_opinions() 硬编码 confidence=0.8 | 7 个 Agent 丧失区分度 | 从 view_dict 提取 |
| 3 | P0 | ConfidenceCalibrationAgent 读取不存在的 data_quality_score | calibrated_confidence 永远 0 | 改为 history_coverage_ratio |
| 4 | P0 | CapitalVolumeAgent 已实例化但未调用 | 死代码 | 删除 |
| 5 | P1 | NarrativeAgent neutral vote 稀释投票比例 | 投票正向/负向比例失真 | decision_impact="excluded" |
| 6 | P1 | _convert_to_opinions() 不保留 metadata/veto/evidence | AgentOpinion 信息丢失 | 完整提取 |
| 7 | P1 | AgentOpinion 缺 signal_profile/decision_impact 字段 | 不可扩展 | 新增字段 |
| 8 | P1 | capital_volume signal_profile 映射误导 | 已删除 Agent 仍有 profile | 移除映射 |

---

## 3. 不建议修改的部分

| 组件 | 原因 |
|------|------|
| ConsensusDecisionAgent 15 条标签规则 | 经 phase25/29/38/57/59 迭代调优 |
| RiskControlAgent vote 逻辑 | 低风险环境 positive 是正确语义 |
| MarketContextAgent vote 逻辑 | 0% neutral 是市场状态特征 |
| 评分层 sector_composite_score.py | 不在迭代范围 |
| VetoRuleAgent | 规则合理 |

---

## 4. 仍然 report-only / excluded 的 Agent

| Agent | decision_impact | 原因 |
|-------|----------------|------|
| catalyst_event | report_only | 外部事件仅作复盘解释 |
| narrative | excluded | low_information，投票稀释 |

---

## 5. 深度分析关键发现（第二轮）

### 5.1 Confidence 反向预测
- high confidence (>=0.7): 5d -0.72%, 正率 37%
- medium confidence (0.4-0.7): 5d +1.01%, 正率 59%
- **高 confidence ≠ 好机会**，confidence 反映的是标签可信度而非机会强度

### 5.2 标签覆盖率
- 15 个标签中 4 个从未触发: rotation_candidate, defensive_watch, weak_continuation, data_limited_neutral
- oversold_rebound_candidate 占 26.2%（过度集中）
- 建议下一轮考虑收窄 oversold_rebound_candidate 条件

### 5.3 标签稳定性
- 板块级标签切换频率 49.2%（几乎一半时间在变）
- 建议下一轮考虑增加"标签惯性"（连续 2 天同标签才确认）

### 5.4 short_term_active_unconfirmed 20 日反转
- 5d +3.45%（最佳），但 20d **-23.69%**（最差）
- 短线反弹后大跌，不适合长期持有

---

## 6. 测试结果

```
864 passed, 19 warnings in 144s
```

### 测试覆盖
- 契约测试: 14 (新增)
- Agent 投票: 7
- Agent 可靠性: 多个
- 语义测试: 多个
- 报告测试: 17
- Signal Profile: 9
- 其他: ~800

---

## 7. 是否修改评分公式
**否**

## 8. 是否修改 Agent 决策规则
**否**（仅修复 bug 和输出结构）

## 9. 是否修改 ai-hedge-fund
**否**

---

## 10. 下一阶段建议

| 优先级 | 建议 | 预期收益 |
|--------|------|----------|
| P0 | 收窄 oversold_rebound_candidate 条件（当前占 26%） | 减少噪声标签 |
| P1 | 增加标签惯性机制（连续 2 天确认） | 降低切换频率 |
| P1 | 校验 rotation_candidate 为何从未触发 | 可能条件过严 |
| P2 | 分析 confidence 反向预测的根因 | 改进置信度语义 |
| P2 | 多月回测（跨 7/8 月） | 验证标签在牛市中的表现 |
| P3 | 考虑给 short_term_heat 更高 ranking 权重 | 它是最可靠 Agent |
