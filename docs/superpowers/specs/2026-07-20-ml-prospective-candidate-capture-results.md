# 个股 ML Prospective 候选采集链结果

## 实现边界

新增独立 paper/shadow 数据采集支路：

- `theme_sector_radar/ml/prospective_candidate_archive.py`
- `scripts/capture_ml_candidate_prospective_snapshot.py`
- `tests/theme_sector_radar/test_ml_prospective_candidate_archive.py`

旧 round1-round20、historical v9、正式排序、predictor、registry、broker/order/live 和事件增强均未接入或重算。

## 日归档合同

每个 observed source 必须是本地 content-addressed JSON，且 source envelope 与 capture request 同时声明一致的 `as_of_date`、`available_at`、绝对路径、SHA-256 和版本。日目录固定包含：

- `schema_a.json`：逐候选日/逐股票宽表，17 个 raw feature、显式 missing indicator 和逐 feature 最大日期。
- `schema_b.json`：逐 feature 长表，保留 family、value/null、missing、source path/SHA、available_at、版本和 eligibility state。
- `snapshot.json`：11 类源 identity 及原始 payload 的不可变副本；stock event features 只有 approved、disabled adjustment manifest 才能读取。
- `manifest.json`：上述文件物理 SHA、不可变 input SHA、质量状态和 5 日目标日期。

archive index 使用前序 entry SHA 串联；同内容重复返回幂等结果，同日修订、源文件事后变化和倒序补录均拒绝。

## Bootstrap 状态

目录：`reports/paper_shadow/ml_stock_ranker/prospective_candidate_capture_v1_20260720`

| 项目 | 当前值 |
| --- | --- |
| prospective snapshot dates | 0 |
| candidate rows | 0 |
| label maturity queue | 0 |
| data quality | `awaiting_first_new_trading_day` |
| future comparison ready | `false` |
| model training allowed | `false` |

没有把 99 日 reconstruction、675 条 direction 同名观察或当前 Linkage/membership 文件复制进 prospective archive。首个真实交易日到来前，0 日状态是预期阻断，不是数据缺失的数值回填。

## Bootstrap 物理 SHA

| Artifact | SHA-256 |
| --- | --- |
| `daily_snapshot_manifest.json` | `ac935178c30ba96f0ba2d2c2a11ba4b21ba1d7e039b610811495b7fd8e2ab944` |
| `coverage_report.json` | `b6cc3a52d2109d30cf605a44e08bb90943c33705c495551425f7689819bce267` |
| `label_maturity_queue.json` | `6c6b1610f4da2c11c1f431119e7a5b2d69f7d1ce70a145c9c53412389111ac9d` |
| `readiness_report.json` | `4ba6bbf173a8d33923a29804b3e7b909cbe9c4dd0c9f75f351db61888f966452` |
| `data_quality_status.json` | `c960444b7ed28b39d96ab4daaee3a8d46107d2dc7c2103363a59cba940b54834` |
| `source_status_report.json` | `fb00a65d700f00abdf229a704de2d14e3f5c55c408a702daba17bfef0dad97ea` |

每份报告均含 logical SHA，且可由空 archive 和 `report_as_of_date=2026-07-20` 重新构建并逐字节比较；source status 的 latest identity 在 0 日时为 `null`。

## 验证结果

- prospective capture 聚焦测试：`14 passed`。
- 全部 `test_ml_*.py`：采集链完成时为 `128 passed`；加入 prospective comparison runner 与 event manifest gate 后，当前扩展套件为 `135 passed in 39.33s`。
- `python -m compileall -q theme_sector_radar scripts tests/theme_sector_radar`：通过。
- tracked 文件 `git diff --check`：通过；本轮新增代码、测试、文档和 6 份 bootstrap JSON 的 untracked diff-check：通过。
- 报告重建验证：0 snapshot、0 candidate row，6 份 bootstrap 物理 SHA 与文档一致；source status 明确为 awaiting first trading day。
