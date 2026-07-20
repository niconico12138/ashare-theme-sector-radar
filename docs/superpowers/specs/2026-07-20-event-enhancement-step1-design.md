# Event Enhancement Layer Step 1 Design

## Gate

This document covers only Step 1: a versioned structural enhancement contract over
validated canonical risk events. It is paper/shadow/research-only. It does not calculate
an event score, adjustment score, rank, selection output, or formal sector/stock result.
Step 2 is intentionally not started by this delivery.

## Input Boundary

`theme_sector_radar/data/event_enhancement.py` accepts only an event that passes
`validate_risk_event()` and evidence references that are members of that event's
verified evidence set. Announcement, policy/macro, commodity-price, and market-anomaly
events therefore enter through the same validation boundary without changing their fact
providers.

## Four Views

`build_event_enhancement()` emits `event-enhancement-v1` with four versioned views:

- `fact_view`: impact direction, value-chain stage, transmission channel, impact scope,
  and mapping basis. Direction supports positive/negative/mixed/unknown. Stage supports
  upstream/midstream/downstream/mixed/unknown. Missing confirmation stays unknown.
- `lifecycle_view`: duration, effective-until date, expiry/decay metadata, and
  novel/repeat/revised/duplicate metadata. Revision and duplicate identifiers remain
  metadata; they do not change the event fact.
- `evidence_quality_view`: authority tier, evidence completeness, timestamp quality,
  mapping quality, conflict state, and manual-review requirement.
- `market_feedback_view`: `as_of_snapshot` contains pre-event metadata and the event's
  as-of date; `post_event_backtest` separately contains event-after evaluation metadata
  and `evaluation_as_of_date`. The two namespaces cannot be substituted for one another.

The default market feedback state is `post_event_backtest.status=reserved_not_run`.
No post-event return, breadth, propagation, or backtest conclusion is inferred.

## Exposure Mapping

`build_event_exposure_mapping()` emits the independent
`event-exposure-mapping-shadow-v1` contract. It maps an enhancement to individual,
sector, or market entities with exposure type, value-chain stage, direction,
transmission channel, impact scope, evidence, validity, and manual-review metadata.
Unknown or incomplete mappings remain visible as `unknown_mappings`.

The output rejects `event_score`, `quant_score`, `final_score`, `v2_score`,
`selection_score`, confidence, rank, action, trade, order, position, and price fields.
It cannot write formal direction, Linkage, ML, or selection fields.

## LLM Boundary And Fixture

The LLM sub-envelope is fixed at `enabled=false` and `reserved_not_run`; candidates
cannot be emitted in this step. The copper fixture is explicit `research_only` and shows
upstream positive, midstream unknown, downstream negative, and mixed/mixed projections.
It is a structural contract example, not real market evidence.
