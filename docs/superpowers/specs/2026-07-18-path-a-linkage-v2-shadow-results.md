# Path A Linkage V2 Shadow Results

## 2026-07-16 observation

- Direction candidates: 5 core sectors, 1 supplemental sector, 0 confirmation
  sectors, and 4 observations excluded from the eligible branch.
- Direction stock-sector rows: 1,029 across 554 unique stocks.
- The original HTTP-offline baseline produced 1,029 unavailable rows and zero
  selected. That artifact remains preserved as a fail-closed baseline.
- The new StockDB run selected `stockdb-sdk` because HTTP was unavailable and
  observed latest daily data `2026-07-17`.
- Daily bars were usable for 540/554 unique stocks (97.4729%) and 1,001/1,029
  stock-sector rows. Linkage V2 produced 1,001 `partial`, 28 `unavailable`, and
  30 paper/shadow selections.
- Missing constituent weights and individual fund flow keep usable rows
  `partial`; no unavailable factor receives a neutral reward.
- The final selected portfolio's maximum cluster share is 33.33%, below the
  frozen 40% cap.

## A/B/C evidence

The current evaluator artifact contains one date. `strict_pit_eligible` is false,
forward-label coverage is insufficient, and all material promotion gates fail.
The result is `promotion_status=insufficient_evidence`. No performance improvement
is claimed and the production baseline is unchanged.

## Verification snapshot

- Focused Path A regression before review corrections: `228 passed`.
- First full-suite run: `3042 passed, 19 deselected`.
- Review corrections added strict final-ratio concentration, effective-policy SHA,
  A/C coverage parity, PIT evidence verification, consumed-payload SHA, and shadow
  request isolation.
- Post-correction focused regression: `234 passed`.
- Post-correction full suite: `3048 passed, 19 deselected`.
- Final `compileall`, `git diff --check`, strict JSON/SHA machine acceptance, and
  protected-field scans passed. Fresh independent review counts remain the final gate.

## Post-review corrections

- The evaluator CLI now accepts a verified PIT evidence file; ordinary replay
  remains unverified by default.
- Promotion now requires C observations on at least 60 dates and 90% of replay
  dates. Empty C dates cannot improve the concentration gate.
- Legacy and direction stock-info/fund-flow runtime statistics are isolated.
- A SHA-bound sector-cluster map is applied consistently to selection and A/C
  concentration evaluation; unmapped sectors fail closed as one conservative cluster.
- The project forward-return builder now accepts unified linkage reports directly.
- The six current direction sectors span four enforceable clusters, so a 40%
  cap can form a non-empty diversified portfolio when V2 evidence becomes usable.
- Focused integration regression after final provenance corrections: `294 passed`.
- StockDB integration focused regression: `245 passed`.
- Final full suite: `3070 passed, 19 deselected`.
- Final compileall, diff, strict JSON, CLI-contract, SHA, paper-only, and
  protected-field machine checks passed.
- Cluster-map SHA: `06cd454ce47cdb690a0a1c3f67a699528ca93e8e710935ae81be501a0fa4c77b`.
- Cluster mapping SHA: `162d0931899222e06e7f932a7d3c45cde9862cfd0d17f1b8b2877d4595a19f2c`.
- HTTP-offline baseline unified SHA:
  `ebdc8e7c61903e1e888afa9614f611a6144d5ee6da252d22171e0de7e34b1eaf`.
- Current StockDB unified SHA:
  `877efcc5bcaac814de3f76bdaa62443027f951af1c38cf57937680f9ecf1daae`.
- Evaluation artifact SHA: `7d64f3d588130e9896be18793d13cddd1f54c5fe5b4260789e23e4fdc1ca8357`.
- Stage 7 bounded recheck A: `Critical=0, Important=0, Minor=0`.
- Stage 7 bounded recheck B: `Critical=0, Important=0, Minor=0`.
- Those two Stage 7 reviews predate StockDB activation and are not reused as
  Stage 8 completion evidence.
- Stage 8 replacement review A: `Critical=0, Important=0, Minor=0`.
- Stage 8 replacement review B: `Critical=0, Important=0, Minor=0`.

## Artifacts

- `reports/paper_shadow/industry_direction_2026-07-16/industry_direction_candidates.json`
- `reports/paper_shadow/linkage_v2_unified/2026-07-16/unified_report.json` (HTTP-offline baseline)
- `reports/paper_shadow/linkage_v2_unified_stockdb/2026-07-16/unified_report.json` (current StockDB shadow run)
- `reports/paper_shadow/linkage_v2_evaluation_2026-07-16/stock_sector_linkage_shadow_evaluation.json`
