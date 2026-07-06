# Phase 35: Research Report Usability and Daily Workflow Polish

## 本阶段目标

把 sector_research.md 优化成真正适合每日盘后使用的研究日报。

## 坚持原则

- 只优化报告展示和每日工作流
- 不修改 Agent 决策逻辑
- 不修改标签规则
- 不修改评分公式
- 保持 JSON 完整结构，不牺牲回测能力

## 新报告结构

1. 今日摘要（日期、regime、样本数、数据质量）
2. 今日重点观察（Top 3-5 候选）
3. 标签分组概览（各组数量和解释）
4. 市场状态（解释层）
5. Agent 分歧与风险摘要
6. 板块详情（统一格式）
7. 数据与方法说明

## 输出

- 重写 sector_research_report.py
- 新增 daily_summary 到 sector_research.json
- 新增中文标签解释映射
