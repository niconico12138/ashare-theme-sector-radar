# Phase D: Agent 与评分层协同检查

**日期**: 2026-07-03

---

## 1. 两层架构概览

### Scoring 层 (sector_composite_score.py)
- **输入**: 原始数据（涨跌幅、动量、回撤、波动率等）
- **输出**: `sector_selection_score` (0-100分制)，选择等级 (strong_watch/watch/neutral/cooling/avoid)
- **组件**: radar_score(25) + momentum(20) + relative_strength(15) + persistence(15) + drawdown(10) + volatility(5) + data_quality(10) - risk_penalty(0-20)
- **定位**: 数值评分，量化板块当前表现

### Agent 层 (sector_research/)
- **输入**: scoring 层的输出 + multi_window_consensus + regime 数据
- **输出**: `ranking_score` (0-1制)，consensus_label，各维度分析
- **组件**: opportunity_score(技术+热度+轮动+市场+叙事加权) + evidence_score + risk_control_score + ranking_score(综合)
- **定位**: 解释、冲突检测、风险提示、信号确认

---

## 2. 协同关系检查

### 2.1 Agent 是否重复计算趋势分?

**结论: 无重复**

| 评分层组件 | Agent 层对应 | 输入差异 |
|-----------|-------------|---------|
| momentum_component | TechnicalTrendAgent | 评分层用近期涨跌幅，Agent 用 multi_window_consensus |
| trend_continuation_score | TechnicalTrendAgent | 评分层是原始计算，Agent 读取后做标签转换 |
| relative_strength_component | MarketContextAgent | 评分层计算，Agent 读取后判断 outperforming/underperforming |

Agent 层不重新计算这些分数——它们读取 scoring 层的输出并转换为语义标签。

### 2.2 Agent 是否重新排序?

**结论: 是的——存在两个独立的 ranking**

| 分数 | 来源 | 公式 | 用途 |
|------|------|------|------|
| `sector_selection_score` | Scoring 层 | 100分制加权 | 评分层排序（strong_watch/watch/neutral/...）|
| `ranking_score` | Agent 层 | opportunity * 0.45 + evidence * 0.20 + risk * 0.25 + market * 0.10 + 惩罚/加分 | Agent 层排序（sector_research.md）|

**这是有意设计**: scoring 层是纯数值，Agent 层加入了主观判断（共识标签惩罚、多窗口确认加分等）。两个 ranking 从不同角度排序。

**潜在混淆**: 用户可能不清楚哪个 ranking 用于什么。需要在报告中明确说明。

### 2.3 ranking_score 是否和 sector_selection_score 重复?

**结论: 不重复，但底层共享数据**

- `ranking_score` 的 `opportunity_score` 部分与 `sector_selection_score` 的 `momentum + relative_strength` 部分有数据关联
- 但 ranking_score 额外加入了 consensus_label 惩罚项（如 conflicted × 0.75, insufficient × 0.20）
- sector_selection_score 没有这些主观惩罚

### 2.4 opportunity_score 是否真正代表正向观察强度?

**结论: 是的**

```python
def _calculate_opportunity_score(self, dimension_scores):
    # technical * 0.30 + heat * 0.25 + rotation * 0.20 + market * 0.15 + narrative * 0.10
    weights = [0.30, 0.25, 0.20, 0.15, 0.10]
    scores = [technical, heat, rotation, market_context, narrative]
    total = sum(s * w for s, w in zip(scores, weights))
```

opportunity_score 综合了 5 个维度的"正面"因素，确实是正向观察强度。

### 2.5 confidence_score 是否仅代表标签可信度?

**结论: 是的**

```python
def _calculate_confidence_score(self, dimension_scores, technical_view, heat_view):
    # 数据质量 * 0.5 + 一致性加分 + 热度加分 + 维度一致性加分
```

confidence_score 衡量的是"当前共识标签有多可信"，不是"机会有多强"。两者语义不同。

---

## 3. 建议

### 不需要修改
1. 两层 ranking 设计合理——scoring 是数值排序，Agent 是综合研判排序
2. opportunity_score / confidence_score 语义清晰，不混用
3. Agent 不重新计算趋势分，只做标签转换

### 需要文档化
1. 在报告中明确说明:
   - `ranking_score` = Agent 层排序分（含主观判断惩罚/加分）
   - `sector_selection_score` = 评分层数值排序（纯客观）
   - 两者用途不同，不互相替代
2. 在"数据与方法说明"中增加两个 ranking 的区别说明
