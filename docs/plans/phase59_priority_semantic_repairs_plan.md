# Phase 59: 高优先级语义修复 实施计划

> 计划日期: 2026-07-02
> 基于: Phase 58 审计文档 docs/reviews/phase58_cross_module_semantic_audit.md
> 范围: 仅修复 H1 + H2 + M1，不修 M2/M3

---

## 1. 修复范围

| ID | 类型 | 问题 | 文件 |
|----|------|------|------|
| H1 | 单位混用 | `generate_risk_reasons` max_drawdown 格式串 | `scoring/sector_composite_score.py:637-640` |
| H2 | 架构 | Vote 聚合器不区分 report-only Agent | `agents/sector_research/agent_vote_aggregator.py:36-44` |
| M1 | 缺数据得分 | Burst score 无 insufficient_history cap | `scoring/short_term_burst_score.py` + `agents/sector_scoring/sector_scoring_agent.py` |

---

## 2. 修改文件清单

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `theme_sector_radar/scoring/sector_composite_score.py` | Edit | H1: 修复 `generate_risk_reasons` 阈值和格式串 |
| `theme_sector_radar/scoring/short_term_burst_score.py` | Edit | M1: 新增 `apply_burst_insufficient_history_cap` |
| `theme_sector_radar/scoring/__init__.py` | Edit | M1: 导出新函数 |
| `theme_sector_radar/agents/sector_research/agent_vote_aggregator.py` | Edit | H2: 过滤 report-only opinions |
| `theme_sector_radar/agents/sector_scoring/sector_scoring_agent.py` | Edit | M1: 导入并应用 burst cap |
| `tests/theme_sector_radar/test_sector_composite_score.py` | Edit | H1: 新增 3 个测试 |
| `tests/theme_sector_radar/test_agent_vote_aggregator.py` | Edit | H2: 新增 4 个测试 |
| `tests/theme_sector_radar/test_dual_sector_scores.py` | Edit | M1: 新增 1 个测试类 (9 个测试) |

---

## 3. 实现方法

### H1: 格式串修复

- 将阈值从 `0.1` / `0.05` (小数) 改为 `10` / `5` (百分数点)
- 将格式串从 `{max_drawdown:.1%}` (Python 会 ×100) 改为 `{max_drawdown:.1f}%`
- 示例: `max_drawdown=-8.68` → 显示 "最大回撤较大 (-8.7%)"

### H2: Vote 隔离

- 在 `AgentVoteAggregator.aggregate()` 内部过滤 `decision_impact == "report_only"` 的 opinions
- 过滤后的 opinions 用于投票统计
- report-only opinions 仍保留在 `agent_opinions` 中用于报告展示
- 当所有 opinions 都是 report-only 时，返回 `no_decision_opinions` 标签，避免除零
- 不修改 coordinator.py（aggregator 内部过滤，更稳的防御式设计）

### M1: Burst Cap

- 新增 `apply_burst_insufficient_history_cap()` 函数，规则：
  - `history_days=0`: cap 到 34.9 (burst_avoid)
  - `0 < actual_history_days < 3`: cap 到 49.9 (burst_fading)
  - `actual_history_days >= 3`: 不 cap
- 在 `sector_scoring_agent.py` 的 `burst_result` 计算后应用 cap
- Cap 后重新计算 `burst_level`，写入 `_burst_history_cap_applied` / `_burst_history_cap_reason` 元数据

---

## 4. 不变更范围

- M2 (`_calculate_momentum_change` 权重方向): 不修
- M3 (`sector_history_analyzer` 符号约定): 不修
- ai-hedge-fund: 不修改
- CatalystEventAgent report-only 行为: 保持不变
- Trend score insufficient_history cap: 保持不变
