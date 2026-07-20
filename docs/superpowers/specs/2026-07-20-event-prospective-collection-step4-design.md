# Event Prospective Collection Step 4 Design

## Scope

Step 4 adds an immutable daily prospective collection chain for event facts and Shadow
projections. It does not run an effect backtest or modify formal ranking. Real and
fixture origins use mutually exclusive archive roots.

## Daily Archive

`event_prospective_collection.py` writes one daily directory containing strict JSON
layers for canonical events, enhancements, exposure mappings, adjustment, source health,
and readiness. Every layer records a file SHA and payload SHA. The final collection
manifest records each path/SHA, collection binding SHA, as-of date, collected-at,
origin, review status, and all safety flags. Existing bytes or manifests cannot be
overwritten with changed content. `load_prospective_event_day()` verifies layer
containment and both SHA forms.

Fixture data is written only below the explicitly separate research archive root. A
research-only event or fixture base snapshot is rejected from a real archive. A blocked
real provider produces source health and unknown/blocked readiness, never fixture success
or `no_event`.

## Runner And A/B Manifests

Each day receives separate sector and individual runner manifests. They bind the
adjustment artifact SHA, adjustment manifest SHA, adjustment file SHA, collection binding,
as-of/effective/PIT metadata, record count, and readiness status for future manual runner
audit. Their approval gate is fixed at `review_status=pending` and
`approved_for_frozen_oos_ab=false`; they do not invoke a runner.

The daily A/B snapshot wraps the existing independent A/B contract. If PIT or coverage
binding fails, it records a blocked snapshot envelope. No post-event field is admitted
into the daily adjustment or B lineage.

## Readiness Gates

The minimum gates cover real event count and source count, duplicate versus explicit
revision, future effective dates, source failure, commodity unit/currency, and unknown
mapping. Real coverage below threshold yields `blocked_insufficient_real_event_coverage`.
Fixture days are `fixture_review_only` even when their structural A/B snapshot is valid.
No returns, Rank IC, drawdown, turnover, costs, or effect claims are computed in Step 4.
