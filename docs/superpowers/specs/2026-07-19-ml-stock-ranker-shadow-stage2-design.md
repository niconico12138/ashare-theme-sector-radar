# ML Stock Ranker Shadow Stage 2 Design Addendum

## Scope

This addendum extends the independent LightGBM LambdaRank paper/shadow path. It does
not change the formal unified pipeline, candidate scoring formulas, candidate pool
fields, or protected score fields.

## Evidence Lifecycle

The active selected relation set is archived once per trading day. The archive records
candidate report SHA, selected-pool identity, dated constituent SHAs, qfq 1d bars,
calendar identity, derived feature rows, and separate Quant/Linkage V2 baseline rows.
An append-only hash chain rejects both silent rewrite and historical insertion.

`captured_at` is timezone-aware and is the prospective witness. Existing unified reports
with naive `generated_at` are not rewritten. Their source timestamp quality is recorded
as naive, while same-day capture may still be prospective because the archive witness
is bound to source SHA and source `as_of_date`. A source date mismatch or capture after
the signal date remains blocking.

Mature label snapshots retain raw stock and sector price rows and are replayed by the
verifier. Labels are not written before the exact target trading date exists.

## Dataset Handoff

`scripts/build_ml_stock_dataset_from_archive.py` is the machine entry point from the
verified archive to a training dataset. It embeds the PIT evidence and binds the
independent baseline document SHA. Below the unchanged 60 prospective mature-date,
strict-PIT, 5-day-label, coverage, and purged-walk-forward requirements it emits a
successful blocked artifact and no trainable strict dataset.

## Evaluation Baselines

When independent baseline rows are present, evaluation compares Quant, full Linkage V2,
percentile Hybrid, and ML on the same day and candidate identities. Hybrid weights are
configurable. Partial Linkage receives an effective 0.20 weight; unavailable Linkage is
excluded from its own baseline and is Quant-only/low-confidence in Hybrid. All outputs
are shadow reports.

Raw prediction distributions, not daily percentile means, drive prediction drift.
