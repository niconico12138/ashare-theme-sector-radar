# ML Historical Research Iteration Plan

## Completed in this continuation

- Re-ran the corrected stability-core historical reconstruction as v6.
- Verified the registry contains exactly 11 stability-core feature names.
- Kept historical reconstruction paper/shadow-only and rejected it from the formal loader.
- Ran focused ML regression and the full test suite.
- Recorded the v6 result in the stage2 design and results documents.

## Current evidence

- 99 mature source dates, 1,696 labeled rows, 7 walk-forward folds.
- Evaluated slice: 34 dates and 594 rows.
- Top3 mean return: 2.106%; candidate-universe mean: 1.797%; lift: +0.309 percentage points.
- Mean Spearman Rank IC: -0.0102; promotion is not justified.

## Next iterations

1. Run nested walk-forward feature stability selection.
2. Add cross-sectional excess-return labels alongside raw forward return.
3. Split evaluation by market regime and sector breadth.
4. Pre-register Top1/Top3/Top5 selection criteria before comparing them.
5. Require a fresh strict-PIT prospective evidence window before any promotion discussion.

## Credibility closure

- v8 deterministically replays walk-forward predictions before accepting metrics.
- ML universe metrics are independent of rule-baseline availability.
- Five-day returns are replayed from stored close summaries and remain explicitly
  source-bar-not-content-addressed.
- Current inventory: 120 artifacts and 11 model binaries; SHA
  `980c5c2d1a3436e82284015c346a926397e9db616370f092f546d280f1d0c435`.
- Final full pytest: 3269 passed, 19 deselected; focused ML regression: 98 passed.

## Final source-rebuild closure

- v9 rejects rehashed in-memory dataset tampering by rebuilding from the physical
  source manifest and comparing the canonical dataset identity.
- Final inventory: 127 artifacts and 12 model binaries; SHA
  `d77416eb6d23c540ed17f4d5187774c4d28a1c904dbf2d255bfd4c92f8fbe5bb`.
- Final full pytest: 3270 passed, 19 deselected; focused ML regression: 99 passed.

## Safety gates

`strict_pit_eligible=false`, `eligible_for_oos_claim=false`, `promotion_allowed=false`,
`live_trading_allowed=false`. No broker integration and no order generation.
