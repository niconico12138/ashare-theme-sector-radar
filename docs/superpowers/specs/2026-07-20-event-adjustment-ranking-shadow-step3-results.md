# Event Adjustment Ranking Shadow Step 3 Results

## Delivered

- Added independent A/B base snapshot and event-adjustment manifest contracts with
  SHA/PIT/effective-date binding.
- Added A/B output preserving `base_rank`, `base_value`, `adjustment`,
  `research_adjusted_value`, and `research_rank_change` as separate fields.
- Added duplicate rejection, direct-company/sector-transmission protection through the
  adjustment input, unknown/blocked/conflict review propagation, and post-event exclusion.
- Added pre-registered sector Top-3/5/7 and individual Top-1/3/5 metrics:
  forward return, Rank IC, max drawdown, turnover, transaction cost, and event coverage.
- Added the copper research-only A/B demonstration. It is explicitly fixture-only and
  makes no effect claim.

## Verification

- Step 3 focused tests: `6 passed`.
- Step 1 + Step 2 + Step 3 event-data related tests: `50 passed`.
- `compileall`: passed.
- `git diff --check`: passed.

## Gate Status

No formal score/rank fields, formal selection, ML input, broker, order, or live path was
modified. Step 4 and any formal ranking integration remain pending review.

## Read-Only Audit

- No imports from scoring, ML, broker, formal pipeline, or execution modules were found
  in the enhancement/adjustment/A-B Shadow chain.
- No exact formal `score` or `rank` output key was found; only explicit base/research
  fields and protected-field rejection constants are present.
- Post-event data appears only in exclusion/audit metadata and pre-registered evaluation
  fields; adjustment lineage and B PIT binding keep it excluded.
- All formal-ranking, promotion, and live-trading flags are false.
- Final module SHA-256 for `event_adjustment_ranking_shadow.py`:
  `EEAF9F9EC5137FBB6344B379442E5550A56E10758B52F2B1089AB7B042C70DCD`.
