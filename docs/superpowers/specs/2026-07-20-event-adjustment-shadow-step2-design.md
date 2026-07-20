# Event Adjustment Shadow Step 2 Design

## Gate

This is Step 2 only: an independent numeric research contract over validated
`event-enhancement-v1` and `event-exposure-mapping-shadow-v1` artifacts. It does not
connect to formal sector or stock ranking. Step 3 is not started.

## Allowed Inputs And PIT

`event_adjustment_shadow.py` reads only the enhancement fact, lifecycle,
evidence-quality, and `market_feedback_view.as_of_snapshot` views plus validated exposure
mappings. It builds a dedicated allowed-input SHA lineage from those fields.

`post_event_backtest` is always excluded. Its status, numeric-data presence, and payload
SHA are recorded in `excluded_post_event_backtests`, while every adjustment lineage row
sets `post_event_backtest_included=false`. An observed post-event result cannot change
the adjustment value or allowed-input lineage hash.

## Deterministic Decomposition

Each research adjustment exposes the following versioned deterministic decomposition:

- direction sign from positive/negative; mixed and unknown are zero;
- impact magnitude band from the projected canonical event severity;
- exposure band from direct/value-chain/indirect exposure;
- persistence from one-off/temporary/ongoing lifecycle metadata;
- evidence quality from authority tier, evidence completeness, timestamp quality, and
  mapping quality;
- novelty from novel/revised/repeat/duplicate metadata;
- market reflection from as-of `unreflected`, `partially_reflected`,
  `fully_reflected`, or unknown metadata;
- exponential time decay from as-of date, exposure valid-from date, and declared or
  default half-life metadata.

LLM output is not an adjustment input and cannot directly provide any component.

## Caps And Fail-Closed Rules

The output is split into `sector_event_adjustment_shadow` and
`stock_event_adjustment_shadow`. Default configurable caps are:

- sector: `[-12, +8]`;
- stock: `[-10, +6]`.

Blocked/unknown/conflict events, incomplete evidence, unknown or blocked mapping,
unknown direction, duplicate/unknown novelty, unknown market reflection, and expired
exposure produce zero adjustment with explicit reasons and manual review.

## Deduplication

The builder selects one deterministic enhancement per stable logical event. Within an
event and target, direct exposure is preferred over value-chain and indirect exposure.
Across events sharing the same target and evidence bundle, a direct company event is
preferred over sector/market transmission to prevent double counting. Independent
events without shared evidence are not merged.

## Safety

Outputs are `research_only`; formal ranking, promotion, OOS claims, broker, order, and
live capabilities are false. Protected score/rank/trade fields are recursively rejected.
The only numeric output is the isolated Shadow `adjustment_value` and its explainable
component metadata.
