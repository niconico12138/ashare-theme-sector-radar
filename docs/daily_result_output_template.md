# 每日运行结果输出模板

## 用法

```bash
python scripts/show_daily_result.py --as-of 2026-07-03
python scripts/show_daily_result.py --as-of 2026-07-03 --top-n 10
```

## 输出结构

### 一、运行摘要

| 字段 | 说明 |
|------|------|
| 日期 | 分析日期 (YYYY-MM-DD) |
| 板块评分来源 | stable_full90 / mixed / legacy_sector_scores |
| 健康门禁 | PASS / WARN / FAIL |
| 数据质量 | PASS / WARN / FAIL |
| 报告目录 | reports/unified/{date} |

### 二、行业 Top N

来源: reports/full90/sector_research/{date}/sector_research.json

| 列 | 字段 | 说明 |
|----|------|------|
| 排名 | rank | 序号 |
| 行业 | sector_name | 行业名称 |
| Agent标签 | agent_label / consensus_label | Agent研判结论 |
| 排序分 | ranking_score | 趋势综合排序分 |
| 机会分 | opportunity_score | 机会评分 |
| 置信度 | confidence_score | 置信度 |
| 趋势等级 | trend_level_cn | 趋势等级 |
| 短线等级 | burst_level_cn | 短线等级 |

### 三、概念 Top N

来源: reports/full_concept/unified_rank/{date}/concept_unified_rank.csv

| 列 | 字段 | 说明 |
|----|------|------|
| 排名 | rank | 序号 |
| 概念 | sector_name | 概念名称 |
| 综合分 | concept_final_rank_score | 综合排名分 |
| 趋势分 | trend_continuation_score | 趋势持续分 |
| 趋势等级 | trend_level_cn | 趋势等级 |
| 短线分 | short_term_burst_score | 短线爆发分 |
| 短线等级 | burst_level_cn | 短线等级 |
| Agent标签 | agent_consensus_label | Agent研判结论 |

### 四、趋势观察池个股 Top N

来源: reports/unified/{date}/unified_report.json → trend_top_stocks

| 列 | 字段 | 说明 |
|----|------|------|
| 排名 | rank | 序号 |
| 代码 | code | 股票代码 |
| 名称 | name | 股票名称 |
| 综合分 | final_score | 综合评分 |
| 量化分 | quant_score | 量化评分 |
| 关联度 | relevance_score | 板块关联度 |
| 资金 | score_breakdown.has_fund_flow | ✓=有资金流数据, —=无 |
| 板块 | sector_name | 所属板块 |
| Agent标签 | agent_label | Agent研判结论 |

### 五、短线观察池个股 Top N

与趋势观察池相同结构。

### 六、数据源与风险

| 字段 | 说明 |
|------|------|
| 成分股来源 | constituent_sources 统计 |
| K线/量化来源 | quant_score_sources 统计 |
| 资金流来源 | fund_flow_source |
| 股票基础信息 | stock_info_sources 统计 |
| 数据质量覆盖率 | 各模块覆盖率 |
| 风险提示 | run_health.reasons |
| 数据质量警告 | data_quality.warnings |

## WARN 解释

| WARN 原因 | 含义 | 处理 |
|-----------|------|------|
| 离线映射占比高 | 概念板块依赖 offline mapping | 检查 EM 是否恢复 |
| 股票基础信息缺失 | stock_info_unknown 高 | 检查 SecurityMaster 源 |
| 成分股真实源覆盖率低 | http_mapping 主导 | 检查 local_industry 或 EM |

## 文件路径

| 文件 | 路径 |
|------|------|
| 行业评分 | reports/full90/sector_research/{date}/sector_research.json |
| 概念排名 | reports/full_concept/unified_rank/{date}/concept_unified_rank.csv |
| 统一报告JSON | reports/unified/{date}/unified_report.json |
| 统一报告MD | reports/unified/{date}/unified_report.md |
