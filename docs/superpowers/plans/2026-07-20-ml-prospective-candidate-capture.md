# 个股 ML Prospective 候选原始快照采集计划

## 当前阶段

- [x] 保留 round1-round20 和 historical v9，不重算、不训练新模型。
- [x] 建立独立 `prospective_candidate_archive_v1`，不复用旧评分基线 accumulation。
- [x] 定义 11 类日源 envelope：候选池、factor snapshot、1m bar identity、1d bar identity、板块 membership、direction inputs、Linkage V2 inputs、交易日历、计算版本、stock event features 和 stock event adjustment manifest。
- [x] 每个 observed 日源绑定 `as_of_date`、`available_at`、绝对路径、SHA-256、`source_version`；direction/Linkage 缺失只能记录为 `unknown` 或 `blocked`。
- [x] 定义 raw-only Schema A/B，覆盖技术/价格结构、支撑压力、成交与流动性、波动风险和板块上下文共 17 个原始特征。
- [x] 建立 5 个交易日标签成熟度队列，以及 manifest、coverage、readiness、data-quality 报告。
- [x] 生成 0 日 bootstrap 报告，保持 `future_comparison_ready=false`。

## 每日运行约束

1. 只允许在 `as_of_date` 当日采集；迟到回填和倒序补录直接拒绝。
2. 同日相同输入幂等；同日任何路径、SHA、版本、记录或特征修订直接拒绝。
3. membership source 的 `as_of_date` 必须与候选日完全一致，当前快照不能冒充历史。
4. 任何未来日期、未来标签字段或受保护评分字段直接拒绝。
5. stock event features 只有在 `stock_event_adjustment` manifest `review_status=approved` 且 `enabled=false` 时才允许读取；否则在读取事件 payload 前拒绝。
6. 缺失特征写为 `null`，同时写 `missing=true`；不允许用数值 0 代替未知。
7. 日快照只生成 raw Schema A/B 和质量状态，不生成模型、registry、预测或正式评分。

## 下一次交易日

准备 11 类符合 source envelope v1 的本地 JSON 源，运行：

```powershell
python scripts\capture_ml_candidate_prospective_snapshot.py `
  --archive-root reports\paper_shadow\ml_stock_ranker\prospective_candidate_archive_v1 `
  --output-root reports\paper_shadow\ml_stock_ranker\prospective_candidate_capture_current `
  --report-as-of-date YYYY-MM-DD `
  --capture-request <absolute-request-path>
```

首次真实日采集后仍不训练模型；至少积累 60 个 prospective 日期并完成独立的成熟标签归档与审核，才允许重新评估 future comparison readiness。
