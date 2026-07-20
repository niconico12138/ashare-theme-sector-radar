# 个股 ML 候选数据准备结果

## Artifact

目录：
`reports/paper_shadow/ml_stock_ranker/candidate_data_preparation_v2_20260720`

包含：

- `source_inventory.json`：160 个物理候选源、99 个 v9 manifest 源、90 个 industry history 文档、12 个当前 sector membership 文件、2 个 sector score 文件、2 个 Linkage V2 报告的路径和 SHA。
- `schema_contract.json`：候选行式 Schema A、逐 feature 长表 Schema B，以及 rule-only / ML-only / hybrid future comparison contract。
- `coverage_report.json`：可回放、部分覆盖、不可回放分层与阻断事实。

## 关键数字

| 来源 | 结果 |
| --- | --- |
| v9 主 cohort | 99 日、1,730 行 |
| 物理 candidate archive | 160 个合法日期源、2,802 行 |
| 未被 v9 manifest 绑定 | 61 日、1,072 行，仅 inventory，不进训练 |
| v9 完整无未来 1m session bars | 1,353/1,730，78.21% |
| direction | 51 个报告日，v9 重叠 41 日，同名观察 675 行，strict PIT 0 |
| Linkage V2 | 2 个报告、单一日期 2026-07-16、v9 重叠 0、strict 0 |
| historical membership | 只有非 PIT industry history；当前 sector membership 仅 12 个 2026-07-16 文件 |

`feature_inventory.json` 已先行统计 40 个 factor id 和 11 个拟选 raw feature；未来
Schema A 要求每行保留 `as_of_date`、`stock_code`、feature family、missing indicator、
source path/SHA 和 eligibility state；Schema B 要求每个 feature observation 单独记录
`feature_max_date` 与 source SHA。任何未知、未来、保护评分或不可 PIT 的字段都进入
`excluded`，不允许回填。

当前 `future_comparison_ready=false`。规则 baseline、ML-only、rule-gated/ML blend
仅完成接口设计，尚未运行新模型或正式排序对照。
