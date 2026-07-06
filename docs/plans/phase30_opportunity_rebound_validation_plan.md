# Phase 30: Opportunity Score and Rebound Label Validation Plan

## 本阶段目标

样本归因分析，不是直接调参。分析 missed opportunities、oversold_rebound_candidate 失败样本、opportunity_score 分布，找出共性特征，为后续规则调整提供证据。

## 坚持原则

- no-lookahead：信号侧字段只使用 <= signal_date 的数据
- 不为了提高回测结果而过拟合规则
- 若没有足够证据，不修改生产规则
- 所有结论用"观察、复盘、验证、候选、信号"表达

## 分析对象

1. missed_opportunity：weak/low_signal 标签 + forward_5d > 3%
2. failed_rebound：oversold_rebound_candidate + forward_5d < 0
3. opportunity_score 分桶：high/medium/low 的 forward 表现

## 输出

- reports/backtests/opportunity_rebound/2026-06-01_to_2026-06-29/opportunity_rebound_analysis.json
- reports/backtests/opportunity_rebound/2026-06-01_to_2026-06-29/opportunity_rebound_analysis.md
