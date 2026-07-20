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

The observed-data cycle starts from the registered configuration at
`config/ml_stock_ranker_v1.json`. It is content-hashed separately from the physical
JSON file SHA, and any explicit controlled override is merged into an effective
configuration before hashing. The effective configuration is bound into the
walk-forward, training report, and model registry.
The configuration fixes the 5-day sector-excess label, 60-date minimum training
history, 20-date test blocks, 5-date purge, LightGBM parameters, and all paper-only
safety flags. CLI overrides remain available for controlled research fixtures, but the
effective configuration remains visible in every artifact. Observed models must be
strict PIT eligible and carry this experiment contract; only synthetic fixtures may
use the relaxed fixture split and fixture prediction opt-in.

```powershell
python scripts/run_ml_stock_training_cycle.py `
  --archive-root reports/paper_shadow/ml_stock_ranker/observed_archive `
  --output-root test_output/ml_training_cycle_iter1 `
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

## Historical Verification Snapshot (Superseded)

The latest credibility continuation completed with `3253 passed, 19 deselected in
236.06s`; focused ML/archive/experiment/inventory coverage is `82 passed`. The readiness artifact SHA is
`80ea9944c6e2fea4978054fa3f1033c722a4172e559dc2b248b053105fd9ba87` and the cycle report
SHA is `4d910f9657cb31aa285066deba324e7732400b8dd72ae5372eacbcdbc2aaa6af`. The cycle is
still fail-closed: one candidate snapshot, zero prospective dates, zero verified training
dates, zero mature five-day labels, no observed model directory, and both promotion and
live trading remain false. These SHA values refer to the exact `test_output/ml_training_cycle_iter1`
paths used by the command above.

Audit immutable historical artifacts without rewriting their content hashes:

```powershell
python scripts/audit_ml_artifact_inventory.py
```

The current inventory is `test_output/ml_artifact_inventory_iter1.json`, SHA
`0655da8b5be1b71c1000a967a184537183f235bf490680cf2459d10274437ff1`. It binds 68
physical artifacts: 65 strict JSON files and 3 `model.txt` binaries; 63 old JSON files
are `superseded_legacy` and ineligible as current evidence, while 2 current cycle files
contain inline `live_trading_allowed=false`.

For a non-mutating final check, use the recorded expected SHA:

```powershell
python scripts/audit_ml_artifact_inventory.py `
  --verify-existing `
  --expected-sha256 0655da8b5be1b71c1000a967a184537183f235bf490680cf2459d10274437ff1
```

## Historical Verification Snapshot (superseded by v8)

Use these latest identities; earlier values in this runbook are historical snapshots.
Full pytest is `3258 passed, 19 deselected in 246.70s`; the focused ML/archive/
experiment/inventory suite is `87 passed in 34.94s`; and the archive suite is `20 passed
in 28.27s`. The cycle remains `status=blocked` with
`reason=readiness_gate_blocked_training`, and it creates no observed model.

Current readiness SHA is
`7d350962f51239869c66d667c12e932e76e0ad0cfd9a82d59a4fe3d9211797a6`; cycle report SHA
is `91443a9d7b42a47857e5b2827b946f3395f82bbd009e07474b99e25953e52753`; and archive
evidence SHA is `2c3f7058826e19a7d311942598435ad9e83b82692d2e863ca5c0e72eb449ffe2`.
The inventory SHA is
`c6d6f22c3412aaa43c32a30a8a4230d31c6b931f1c48d2c1e54487ccb1ec6e53`; it covers 69
artifacts (66 JSON and 3 model binaries), with 64 immutable legacy JSON artifacts and 2
current cycle artifacts. Strict parsing remains `379 JSON + 1 JSONL/12 lines`.

## Iteration 1: Registered Experiment Contract

The first post-Stage-2 iteration makes training settings reproducible and auditable.
`theme_sector_radar/ml/experiment.py` validates the feature schema SHA, excludes the
legacy relevance field, fixes the label and split contracts, and rejects any promotion
or live-trading flag. The current real-data cycle records the configuration and returns
`readiness_gate_blocked_training` with 1 candidate snapshot, 0 prospective snapshots,
and 0 mature 5-day labels; no model is created.

## Final Current Override After Historical v9 (2026-07-20)

This section supersedes all earlier current/latest values. The current complete ML
inventory is `test_output/ml_artifact_inventory_historical_v9_final.json`, SHA
`d77416eb6d23c540ed17f4d5187774c4d28a1c904dbf2d255bfd4c92f8fbe5bb`.
Verification reports 127 artifacts, 104 superseded legacy artifacts, 11 current or
compatible research artifacts, and 12 model binaries. Full pytest is
`3270 passed, 19 deselected in 254.56s`; focused ML regression is `99 passed`.

The current historical research output is
`reports/paper_shadow/ml_stock_ranker/historical_research_v9_source_rebuild_bound_20260720`.
It is deterministic-replay-bound, paper/shadow-only, non-PIT, non-OOS,
non-promotable, formal-predictor-incompatible, and live-trading-disabled.
