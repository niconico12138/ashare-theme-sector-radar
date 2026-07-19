# ML Stock Ranker Shadow Stage 2 Runbook

All commands in this runbook are paper/shadow research only. They never connect to a
broker and never create an order instruction. Protected fields are never written:
`quant_score`, `final_score`, `v2_score`, `selection_score`, and
`selection_score_adjusted`.

## Daily Capture

Capture the active direction+Linkage V2 selected pool, dated constituents, qfq daily
bars, and exchange calendar into an append-only archive:

```powershell
python scripts/accumulate_ml_stock_shadow.py `
  --unified-report reports/paper_shadow/linkage_v2_unified_stockdb/2026-07-16/unified_report.json `
  --archive-root reports/paper_shadow/ml_stock_ranker/observed_archive `
  --constituent-root data_cache/sector_stocks `
  --sector-history-root data_cache/sector_history/industry `
  --trading-calendar-path <calendar.json> `
  --expected-calendar-sha256 <calendar-sha256> `
  --output reports/paper_shadow/ml_stock_ranker/daily_cycle_2026-07-16.json
```

Each snapshot binds the source bytes, source `as_of_date`, timezone-aware archive
`captured_at`, constituents, qfq 1d bars, calendar, feature rows, and independent
baseline rows. A naive upstream `generated_at` is retained as source timestamp quality
metadata; it is not a permanent blocker when the archive capture is same-day and
timezone-aware. A capture after the signal date is historical reconstruction and does
not count as strict PIT.

Labels are only written after the exact 1/3/5 trading-day targets mature. Re-running a
day is idempotent; changing its input is rejected rather than overwritten.

## Archive To Dataset

This is the explicit handoff between accumulation and training:

```powershell
python scripts/build_ml_stock_dataset_from_archive.py `
  --archive-root reports/paper_shadow/ml_stock_ranker/observed_archive `
  --dataset-output reports/paper_shadow/ml_stock_ranker/archive_build/dataset.json `
  --baseline-output reports/paper_shadow/ml_stock_ranker/archive_build/baseline_rows.json `
  --readiness-output reports/paper_shadow/ml_stock_ranker/archive_build/readiness.json `
  --report-output reports/paper_shadow/ml_stock_ranker/archive_build/build_report.json `
  --sector-history-root data_cache/sector_history/industry
```

Below 60 verified prospective mature dates, it exits successfully with `status=blocked`
and writes blocked evidence. It never fabricates a strict dataset. At or above the
unchanged 60-date gate, complete 5-day labels, strict PIT evidence, and purged
walk-forward eligibility are bound into the dataset. The baseline document SHA is also
bound into the dataset source manifest.

## Train And Evaluate

```powershell
python scripts/run_ml_stock_training_cycle.py `
  --archive-root reports/paper_shadow/ml_stock_ranker/observed_archive `
  --output-root reports/paper_shadow/ml_stock_ranker/training_cycle `
  --model-dir models/paper_shadow/stock_ranker_lgbm_v1_observed `
  --model-version stock_ranker_lgbm_v1_observed `
  --sector-history-root data_cache/sector_history/industry
```

The cycle re-verifies the archive, then either stops at readiness or runs strict dataset
build, LightGBM LambdaRank purged expanding walk-forward, bundle registration, and
evaluation. Evaluation emits independent same-day Top10/20/30 strategies:

- `A_quant`: full Quant baseline percentile ranking.
- `B_linkage_v2`: Linkage V2 percentile ranking; unavailable rows are fail-closed.
- `C_hybrid`: default Quant 0.65 / Linkage V2 0.35; partial Linkage effective weight
  0.20; unavailable Linkage becomes low-confidence Quant-only.
- `D_ml`: ML shadow ranking.

Feature drift is reported from feature distributions. Prediction drift is reported from
raw model predictions using chronological mean, standard deviation, and IQR shifts;
daily percentile means are not used as a drift signal.

## Current Evidence

The current observed archive contains one historical reconstruction day (2026-07-16),
30 selected candidates, zero prospective dates, zero mature 5-day label dates, and 128
sector-history dates. The archive-to-dataset and training-cycle outputs are both
`blocked`; no observed model directory was created. `promotion_allowed` remains false.
