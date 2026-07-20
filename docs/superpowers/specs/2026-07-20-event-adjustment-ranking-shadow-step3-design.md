# Event Adjustment Ranking Shadow Step 3 Design

## Gate

Step 3 implements only an independent A/B research adapter. A is an immutable base
ranking snapshot; B is a separate research projection using validated
`event_adjustment_shadow`. No formal score/rank field is overwritten and no formal
selection, ML, broker, order, or live path consumes B.

## A/B Contract

`event_adjustment_ranking_shadow.py` defines:

- `event-ab-base-ranking-snapshot-v1`, with `base_rank`, `base_value`, as-of,
  effective-from, PIT status, and snapshot SHA;
- `event-adjustment-shadow-manifest-v1`, binding adjustment artifact SHA, manifest SHA,
  as-of dates, effective dates, PIT statuses, and explicit post-event exclusion;
- `event-adjustment-ranking-ab-shadow-v1`, preserving A fields and emitting separate B
  fields: `adjustment`, `research_adjusted_value`, `research_rank`, and
  `research_rank_change`.

The adapter rejects mismatched snapshot/manifest SHA, future effective dates, invalid PIT,
duplicate logical-event/target rows, and post-event lineage. Unknown/blocked/conflict
adjustments remain zero and retain manual-review reasons from the adjustment layer.

## Deduplication And PIT

The input adjustment artifact has already performed logical-event and target deduplication;
the A/B boundary independently rejects any remaining logical-event/target duplicate. The
underlying adjustment layer also prefers a direct company event over a shared-evidence
sector/market transmission to the same stock. A/B rows carry no post-event metric.

## Evaluation Registration

`build_event_ab_metric_preregistration()` pre-registers sector Top-3/5/7 and individual
Top-1/3/5 evaluations with forward return, Rank IC, max drawdown, turnover, transaction
cost, and event coverage. The evaluation contract is effect-claim false and returns
`blocked_insufficient_real_event_coverage` when real event coverage is zero.

## Fixture Boundary

The copper fixture is research-only. It demonstrates a positive upstream adjustment
moving a sector upward in B, a zero midstream adjustment, a negative downstream
adjustment, and unchanged/changed research ranks. Fixture movement is not evidence of
out-of-sample effect.
