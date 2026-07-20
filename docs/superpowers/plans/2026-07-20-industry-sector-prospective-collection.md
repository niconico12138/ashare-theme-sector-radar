# 行业板块 Prospective/OOS 采集与成熟度监控

## 冻结范围

- Test signal dates：`2026-07-13`、`2026-07-14`、`2026-07-15`、`2026-07-16`。
- 标签 horizon：5 个完整交易日；交易日由全部冻结行业都有 bar 的日期交集决定，不使用自然日推算。
- Required universe：首次采集冻结的 90 个真实行业。
- round28/39/16/18 参数继续冻结；本阶段不训练候选模型、不读取 event enhancement。

## 不可变证据

每个 signal date 保存：

- `snapshots/YYYY-MM-DD.json`：当日行业 bar、截至当日的标准化 prefix SHA、源文件 SHA-at-collection。
- `manifests/YYYY-MM-DD.manifest.json`：snapshot 物理 SHA、行业数和 aggregate prefix SHA。
- `collection_contract.json`：signal dates、required sectors、5 日 horizon 和首次完整交易日终点。
- `candidate_freeze.json`：round28/39/16/18 的固定参数与 aggregate SHA；状态固定为 `frozen_not_trained`。

后续运行允许源文件追加更晚 bars，但不允许修改 signal date 或更早 prefix。既有 snapshot/manifest 不覆盖；物理 SHA、prefix SHA 或 signal bar 重放失败即拒绝。

## Readiness 状态机

- `blocked_pending_label_maturity`：源完整且 SHA 重放通过，但至少一个 signal date 未观察到 5 个后续完整交易日。
- `rejected_source_integrity`：缺失行业、缺失 bar、行业集合漂移、日期漂移、历史修订或 snapshot SHA 重放失败。
- `ready_for_frozen_candidate_evaluation`：四个 signal dates 均有 5 个后续完整交易日、required universe 完整、无缺 bar、所有不可变 SHA 重放通过。

`ready` 只允许后续审核决定是否运行冻结候选评估；不会改变五个安全字段，不代表 OOS claim、promotion、formal predictor 或 live readiness。

## 当前结果

当前真实源完整日期终点为 `2026-07-16`：

- `2026-07-13` 已观察 3 个后续完整交易日，还缺 2 个。
- `2026-07-14` 已观察 2 个，还缺 3 个。
- `2026-07-15` 已观察 1 个，还缺 4 个。
- `2026-07-16` 已观察 0 个，还缺 5 个。

因此当前状态必须保持 `blocked_pending_label_maturity`。

## 输出

`reports/paper_shadow/industry_sector_ml_shadow/prospective_collection/prospective_collection_status.json`

该状态文件记录当前 source manifest aggregate SHA、新增完整交易日、逐 signal maturity、缺失 bar、snapshot/manifest SHA 和拒绝原因；`event_source_read=false`、`candidate_model_training_run=false`。
