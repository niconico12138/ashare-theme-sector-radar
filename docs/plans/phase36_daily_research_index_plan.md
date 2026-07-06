# Phase 36: Daily Research Index and Review Workflow

## 本阶段目标

建立多日 sector_research 日报索引，提升多日复盘效率。

## 坚持原则

- 只做索引和复盘工作流
- 不修改 Agent 决策逻辑
- 不修改标签规则
- 不修改评分公式

## 索引内容

1. 板块出现频率（哪些板块连续出现在今日重点观察中）
2. 标签稳定性（哪些板块标签发生变化）
3. 分数趋势（ranking_score / opportunity_score 随时间变化）
4. 风险信号（veto、conflict 变化）
5. regime 关联（哪些板块在哪些 regime 下反复出现）

## 输出

- reports/sector_research/index.json（多日索引）
- reports/sector_research/index.md（可读索引）
