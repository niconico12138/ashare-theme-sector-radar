# Factor Usage Policy

This document defines how factors may be used in the three-project joint system.
It connects:

- `docs/runbooks/factor_catalog.md`
- `docs/runbooks/sector_factor_catalog.md`
- `docs/runbooks/stock_factor_catalog.md`
- `docs/runbooks/factor_semantics_contract.md`

The goal is to prevent factor semantics from drifting across scoring,
reporting, backfill, diagnostics, and future automation.

## Canonical Usage Layers

| Layer | Allowed behavior | Disallowed behavior |
|---|---|---|
| `official_score` | Rank or sort official candidates. | Hidden formula changes without tests. |
| `pool_signal` | Build watch-only candidate pools. | Produce price levels or execution actions. |
| `selection_quality` | Re-rank or annotate the compact observation pool. | Change `final_score`. |
| `shadow_score` | Run parallel validation and disagreement review. | Affect official ranking. |
| `stock_profile` | Explain stock state. | Force inclusion or exclusion by itself. |
| `risk_review` | Add review flags and soft warnings. | Automatic removal without explicit policy. |
| `explanation_only` | Improve report wording and reason codes. | Affect ranking or pool membership. |
| `research_only` | Offline tests and diagnostics. | Production use. |

## Current Production Policy

| Area | Factors | Policy |
|---|---|---|
| Official ranking | `final_score` | Only official ranking score. |
| Trend pool | `stock_trend_score`, sector context | Watch-only candidate pool. |
| Short pool | `stock_short_score_v2`, burst context | Watch-only candidate pool. |
| Sector support | `sector_support_score` | May adjust observation quality for `trend_follow`; does not change official order. |
| V2 discovery | `factor_composite_shadow_score_v2` | Shadow-only independent opportunity discovery. |
| Bars profile | `liquidity_score`, `breakout_distance_20`, `drawdown_depth_20`, `chasing_risk_score` | Profile, review, and shadow policy only. |
| Agent scores | `agent_score`, `trend_agent_score`, `short_agent_score` | Pass-through and explanation context. |

## Strategy-Level Use

### Trend-follow watch-only

Use sector trend and stock trend factors to form a trend observation pool.
`sector_support_score` may improve observation quality only when the candidate
is classified as `trend_follow`.

### V2 opportunity watch-only

Use `factor_composite_shadow_score_v2` to find low-final-score but high-v2
disagreement candidates. These are observation candidates only and remain
outside official ranking.

### Short-burst watch-only

Use short score and burst context to form a short-term observation pool. Sector
support is display-only for this type unless future validation changes the
policy.

## Promotion Gate

A factor cannot move into a stronger usage layer unless all checks pass:

1. Schema metadata exists.
2. Calculation is deterministic and tested.
3. Coverage is sufficient.
4. Historical evaluation is documented.
5. Opportunity-type slice analysis is documented when relevant.
6. The factor has a documented downgrade or invalidation meaning.
7. The factor remains consistent with `factor_semantics_contract.md`.

## Demotion Rules

A factor should be demoted when:

1. Coverage collapses.
2. Score distribution becomes constant or nearly constant.
3. It becomes redundant with `final_score` without incremental value.
4. It has unstable sign across months.
5. Its wording creates action-like semantics.

## Non-Negotiable Guardrails

1. `profile_only` does not trigger selection, removal, or actions.
2. `structure_candidate` is structure position, not an execution trigger.
3. `repair_context` is pullback context, not automatic deterioration.
4. `soft_warning` is review context, not automatic removal.
5. No factor may directly produce price levels or execution actions.
6. All current candidate outputs remain `watch_only`.
