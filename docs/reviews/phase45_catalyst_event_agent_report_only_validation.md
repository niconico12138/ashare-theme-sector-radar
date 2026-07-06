# Phase 45: CatalystEventAgent Report-Only Integration Validation

## 修改内容

1. 新增 `theme_sector_radar/agents/sector_research/catalyst_event_agent.py`
2. 修改 `theme_sector_radar/agents/sector_research/coordinator.py`：集成 CatalystEventAgent
3. 修改 `theme_sector_radar/agents/sector_research/opinion.py`：新增 sparse_event_signal profile
4. 修改 `theme_sector_radar/reports/sector_research_report.py`：展示催化事件信息
5. 新增 `tests/theme_sector_radar/test_catalyst_event_agent.py`：9 个测试
6. 新增 `docs/plans/phase45_catalyst_event_agent_report_only_plan.md`

## CatalystEventAgent 输入输出

**输入**: sector_name, sector_type, as_of_date, current_result, catalyst_events, source_status

**输出**: AgentOpinion with catalyst_label, score, confidence, vote=neutral, veto=False, metadata.decision_impact="report_only"

## catalyst labels

| Label | 中文 | 条件 |
|-------|------|------|
| catalyst_observed | 观察到外部事件 | 匹配到事件，freshness 好，confidence >= 0.5 |
| catalyst_sparse | 事件稀少或置信度低 | 匹配到事件但质量低 |
| no_catalyst_observed | 未观察到匹配事件 | 有 cache 但无匹配 |
| catalyst_unknown | 事件数据不足 | cache 不存在 |

## vote 规则

- 所有 label 的 vote 都为 neutral（report-only）
- veto 永远 False
- decision_impact = "report_only"

## sector_research.json 示例

```json
{
  "agent_opinions": [
    {
      "agent_id": "catalyst_event",
      "layer": "L2_specialized",
      "label": "catalyst_observed",
      "score": 0.4,
      "confidence": 0.7,
      "evidence": ["匹配到 2 条外部事件", "事件来源: akshare_stock_news_em"],
      "vote": "neutral",
      "veto": false,
      "metadata": {
        "decision_impact": "report_only",
        "matched_event_count": 2
      }
    }
  ]
}
```

## sector_research.md 展示摘要

```
- **外部催化事件**: 观察到外部事件 (2 条事件，report-only)
  - 匹配到 2 条外部事件
  - 事件来源: akshare_stock_news_em
  - 说明: 外部事件仅作为复盘解释，不参与当前评分和标签决策
```

## 是否影响 consensus_label

**否。** CatalystEventAgent 只是 report-only。

## 是否影响 ranking_score / opportunity_score / confidence_score

**否。**

## 是否影响 vote / veto

**否。** vote 永远 neutral，veto 永远 False。

## 是否新增 CatalystEventAgent 决策能力

**否。** 本阶段只做 report-only 接入。

## 测试结果

9 个新增测试全部通过。

## 是否仍未修改 ai-hedge-fund 项目

**未修改。**

---

*本报告由 Theme Sector Radar 自动生成，外部催化事件仅用于复盘解释，不参与当前决策。*
