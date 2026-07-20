# 行业板块 Frozen OOS Evaluation Runner

## 执行门禁

runner 在任何模型代码前验证：

- prospective status schema、冻结四日期和五个安全字段。
- collection contract、candidate freeze、4 snapshots、4 manifests，共10个不可变文件的限定路径和物理 SHA。
- 每个 manifest 引用的 snapshot SHA 与 signal date。
- round28/39/16/18 的完整参数与 aggregate SHA。
- 四个 signal date 各有5个后续完整交易日、maturity date 与第五日一致。
- source complete、snapshot replay、all labels mature、collection ready 均为 true。

任何完整性错误输出 `rejected_frozen_oos_preflight`；标签或 collection 未 ready 输出 `blocked_frozen_oos_not_ready`。两种情况都固定 `candidate_model_training_run=false`，不创建模型目录。

## Ready 后冻结执行

只有 preflight ready 后，才使用 validation end 之前且 label maturity 早于 test start 的记录训练。四候选共享 `2026-07-13..2026-07-16` test window，不允许改 feature profile、窗口、seed、estimators、leaves、Top-k 或成本口径。

预实现报告包括：

- Top3/5/7 gross raw/excess。
- 0/10/25 bps turnover cost 后 net excess。
- Rank IC、NDCG、胜率、换手。
- gross/net path cumulative return 和 max drawdown。
- risk-on/mixed/risk-off 分层。
- 以 round28 为 baseline 的 paired daily excess、胜率、IC/NDCG 和 drawdown delta。

评估完成仍保持 paper-only，所有 promotion/formal/live flags 为 false。

## Event A/B 接口

默认 `disabled`，不读取事件输出。传入事件 manifest 时，只接受 schema 固定、`review_status=approved`、`approved_for_frozen_oos_ab=true` 且 adjustment artifact SHA 匹配的审核输入；未审核时在读取 adjustment artifact 前拒绝。当前 runner 只验证并登记接口，不自动修改正式特征或选股链。

## 当前预期

当前 prospective source 仅到 `2026-07-16`，四个测试日期尚未全部成熟。因此真实运行必须只生成 `frozen_oos_evaluation_readiness.json`，状态为 blocked，不训练候选模型。
# Target architecture adaptation (2026-07-20)

The runner now exposes a fixed three-arm paper-only contract:

- `industry_ml_baseline` (A): enabled only after frozen prospective readiness; current state is `reserved_blocked`.
- `industry_ml_event_features` (B): disabled by default; no event source is read.
- `industry_ml_event_adjustment` (C): disabled by default; no event source is read.

Every arm report carries candidate id, arm id, frozen signal dates, prospective status SHA, dataset SHA, gross/net excess, Rank IC, NDCG, win rate, turnover, drawdown, regime metrics, and paired deltas. Protected formal score fields are rejected recursively.

An event manifest is rejected before its adjustment artifact is opened unless it is reviewed for the requested B/C arm and supplies strict PIT, effective-from/as-of, no-future-revision, source-manifest SHA, and event-record time-field contracts. The formal selection chain, Linkage V2, broker/order, and live paths remain outside this module.

The 2026-07-20 refresh observed 90 sectors through `2026-07-16`; maturity was only 3/5, 2/5, 1/5, and 0/5 future trading dates for the four frozen signal dates. The persisted status is `blocked_pending_label_maturity`; frozen OOS remains `blocked_frozen_oos_not_ready`, with `candidate_model_training_run=false` and no model directory created. No event artifact was read.
