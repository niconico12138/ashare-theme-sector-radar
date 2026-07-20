# 个股 ML Prospective Comparison 计划

## 预注册合同

- 最少真实 prospective snapshot：60 个交易日。
- 标签：5 日成熟、逐候选覆盖、source SHA 通过，且 `label_as_of_date <= report_as_of_date`。
- 固定策略：`rule-only`、`ML-only`、`rule-gated+ML/hybrid`。
- 横截面：按 `as_of_date` 分组；Top1/3/5；Rank IC、胜率、最大回撤、换手；0/10/25bps 成本。
- 原始特征：支撑压力/价格结构只有在快照 source/PIT 门禁通过后进入评估，缺失仍保留 indicator。
- ML prediction：只接受带 model artifact SHA、model parameter SHA、feature contract SHA 和 comparison contract SHA 的外部 paper prediction evidence；runner 不训练。
- event adjustment：合同固定 disabled；有未审核 manifest 或 `enabled=true` 直接拒绝。
- 所有输出保持 `eligible_for_oos_claim=false`、`promotion_allowed=false`、`live_trading_allowed=false`、`formal_predictor_compatible=false`。

## 运行

```powershell
python scripts\run_ml_prospective_comparison.py `
  --archive-root reports\paper_shadow\ml_stock_ranker\prospective_candidate_archive_v1 `
  --output-root reports\paper_shadow\ml_stock_ranker\prospective_comparison_current `
  --report-as-of-date YYYY-MM-DD `
  --labels <labels-path> --labels-sha256 <sha256> `
  --predictions <predictions-path> --predictions-sha256 <sha256>
```

未达到 60 日、快照 source/PIT 不完整、5 日标签未成熟或 prediction evidence 不完整时，runner 只写 blocked report，不生成评估指标、模型或 registry。
