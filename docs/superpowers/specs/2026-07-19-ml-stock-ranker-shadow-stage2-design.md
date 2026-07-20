# ML Stock Ranker Shadow Stage 2 Design Addendum

## Scope

This addendum extends the independent LightGBM LambdaRank paper/shadow path. It does
not change the formal unified pipeline, candidate scoring formulas, candidate pool
fields, or protected score fields.

## Evidence Lifecycle

The active selected relation set is archived once per trading day. The archive records
candidate report SHA, selected-pool identity, dated constituent SHAs, qfq 1d bars,
calendar identity, derived feature rows, and separate Quant/Linkage V2 baseline rows.
Strict prospective status additionally requires absolute, existing, SHA-matching
candidate/constituent/calendar files whose contents reproduce the archived selection,
sector membership, and calendar. Logical or relative source identifiers remain
historical/untrusted and cannot become strict merely by self-attesting a flag.
An append-only hash chain rejects both silent rewrite and historical insertion.

`captured_at` is timezone-aware and is the prospective witness. Existing unified reports
with naive `generated_at` are not rewritten. Their source timestamp quality is recorded
as naive, while same-day capture may still be prospective because the archive witness
is bound to source SHA and source `as_of_date`. A source date mismatch or capture after
the signal date remains blocking.

Mature label snapshots retain raw stock and sector price rows and are replayed by the
verifier. Each mature label also carries an immutable input-evidence file, actual
per-stock source identities, sector-history path/SHA identities, and the exact source
rows used to build labels. Labels are not written before the exact target trading date
exists.

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
assigned a fail-closed lowest rank inside the same common eligible pool and remains
Quant-only/low-confidence in Hybrid. Strict evaluation also binds baseline rows and the
walk-forward prediction universe back to the verified archive and dataset SHA. All
outputs are shadow reports.

Raw prediction distributions, not daily percentile means, drive prediction drift.

## Historical Reconstruction Research Extension (2026-07-20)

The independent historical reconstruction branch reads archived candidate pools,
verified forward-return files, and the explicit A-share trading calendar. It is a
paper/shadow research path only. It uses the separate `stability_core_v1` feature
profile when requested and never feeds the formal predictor or protected score
fields. Historical reconstruction remains `strict_pit_eligible=false`,
`eligible_for_oos_claim=false`, `promotion_allowed=false`, and
`live_trading_allowed=false`.

The branch supports expanding and rolling walk-forward windows, immutable input SHA
binding, fail-closed immature labels, and explicit rejection of historical research
bundles by the formal model loader. This extension does not alter the formal
candidate-selection architecture.

The credibility follow-up requires deterministic replay of every declared historical
walk-forward experiment before metrics are accepted. ML/universe metrics use the full
labeled prediction universe; rule comparisons use a separately disclosed baseline-
available intersection. Five-day labels are arithmetically replayed from `close_t` and
`close_5d`, checked against the trading-calendar maturity boundary, and explicitly
classified as source-bar-not-content-addressed. They therefore remain historical
reconstruction evidence and cannot satisfy strict PIT or OOS gates.
