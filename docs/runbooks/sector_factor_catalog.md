# Sector Factor Catalog

This document defines sector-level factors for the three-project joint system.
Sector factors answer one question: which industry or theme direction is worth
observing today?

Sector factors do not select individual stocks by themselves. They provide
context for routing, confidence, and review.

## Factor Groups

| Group | Factor ids | Current usage | Notes |
|---|---|---|---|
| Sector trend | `sector_trend_score`, `trend_score`, `persistence_score`, `multi_window_consensus_score` | `pool_signal`, `stock_profile` | Used to identify durable sector strength. |
| Sector burst | `sector_burst_score`, `burst_score`, `short_term_heat_score` | `pool_signal`, `stock_profile` | Used to identify short-term heat. |
| Breadth | `RS_Breadth`, `advance_decline_ratio`, `leader_count`, `participation_rate`, `breadth_score` | `research_only` | Measures whether sector strength is broad or concentrated. |
| Relative strength | `RS_Return`, `excess_return`, `relative_rank`, `rank_change`, `RotationBonus` | `research_only` | Measures sector performance relative to market or other sectors. |
| Capital and volume | `RS_Flow`, `amount_ratio`, `volume_ratio`, `capital_volume_score`, `turnover_activity_score` | `research_only` | Measures money flow and activity confirmation. |
| Catalyst and semantics | `catalyst_strength_score`, `theme_persistence_score`, `policy_theme_match_score` | `research_only` | Measures whether a sector move has a durable narrative or event driver. |
| Risk and conflict | `conflict_score`, `data_quality_score`, `sector_score_semantic_audit` | `risk_review`, `explanation_only` | Used for review and data-quality warnings. |
| Stock bridge | `sector_support_score`, `sector_trend_score`, `sector_burst_score` | `selection_quality`, `stock_profile` | Connects sector context to stock observation quality. |

## Registered Sector Factors

| Factor id | Layer | Status | Rule |
|---|---|---|---|
| `sector_trend_score` | `stock_profile` | active | Can support `trend_follow` explanations. |
| `sector_burst_score` | `stock_profile` | active | Can support `short_burst` explanations. |
| `sector_support_score` | `selection_quality` | active | Can adjust observation quality for `trend_follow`; does not change official ranking. |
| `trend_score` | `stock_profile` | fallback | Alternative field name for `sector_trend_score`. |
| `burst_score` | `stock_profile` | fallback | Alternative field name for `sector_burst_score`. |

## Research Reserve

These factors are valid research candidates, but they are not production
selection inputs until they pass backtest, attribution, and shadow validation.

| Factor id | Intended group | Required validation |
|---|---|---|
| `RS_Return` | Relative strength | IC, sector rotation stability, market-regime slice. |
| `RS_Breadth` | Breadth | Breadth monotonicity and leader concentration test. |
| `RS_Flow` | Capital and volume | Turnover robustness and lag test. |
| `RotationBonus` | Relative strength | Lag and redundancy check against price momentum. |
| `MKT`, `IND` | Risk neutralization | Exposure attribution and residual test. |
| `catalyst_strength_score` | Catalyst and semantics | Catalyst persistence and false-positive review. |
| `multi_window_consensus_score` | Sector trend | Multi-horizon stability test. |
| `conflict_score` | Risk and conflict | Data-quality and explanation audit. |

## Sector-to-Stock Routing Rules

1. Strong sector trend may support `trend_follow` observation.
2. Strong sector burst may support `short_burst` observation, with stricter risk review.
3. Strong `sector_support_score` may improve observation quality for `trend_follow`.
4. Weak or conflicted sector context should be displayed as review context, not as automatic removal.
5. Sector factors must not produce price levels, execution instructions, or non-watch actions.

## Promotion Rules

A sector factor may move from `research_only` to active use only when all of the
following are true:

1. It has a stable definition in the factor schema.
2. It has enough historical samples across multiple months.
3. It improves forward-return diagnostics or explanation quality.
4. It is not mostly redundant with `final_score`.
5. Its allowed usage layer is documented before production use.
