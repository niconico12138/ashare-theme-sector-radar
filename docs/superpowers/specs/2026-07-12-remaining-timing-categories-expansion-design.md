# Remaining Timing Categories Expansion Design

## Goal

Expand the remaining six intraday timing research categories one category at a time, then run the same paper-only 5m-first and 1m-confirmed validation flow used for `price_momentum` and `volume_money_flow`.

## Categories

The remaining categories are:

- `vwap_mean_price`
- `intraday_position`
- `sector_confirmation`
- `relative_strength`
- `risk_reversal`
- `time_structure`

Each category will receive six new factors, taking each from four registered factors to ten. Every factor must be registered in exactly one category.

## Factor Additions

`vwap_mean_price`:

- `open_vwap_reclaim_score`
- `midday_vwap_support_score`
- `vwap_distance_stability_score`
- `vwap_pullback_support_score`
- `vwap_breakout_confirm_score`
- `vwap_above_ratio_score`

`intraday_position`:

- `open_to_high_progress_score`
- `close_above_midrange_score`
- `low_reclaim_position_score`
- `late_range_expansion_score`
- `high_area_acceptance_score`
- `close_location_stability_score`

`sector_confirmation`:

- `sector_breadth_persistence_score`
- `sector_late_acceleration_score`
- `leader_sync_persistence_score`
- `sector_alpha_confirmation_score`
- `sector_breadth_quality_score`
- `theme_confirmation_composite_score`

`relative_strength`:

- `stock_intraday_rank_proxy_score`
- `stock_vs_market_intraday_alpha_score`
- `relative_late_strength_score`
- `relative_vwap_strength_score`
- `relative_breakout_leadership_score`
- `relative_resilience_score`

`risk_reversal`:

- `open_high_reversal_risk`
- `late_breakdown_risk`
- `failed_breakout_risk`
- `lower_low_sequence_risk`
- `volatility_expansion_reversal_risk`
- `weak_close_after_volume_risk`

All six risk factors are `lower_is_better`.

`time_structure`:

- `first_hour_follow_through_score`
- `midday_hold_score`
- `afternoon_recovery_score`
- `late_session_acceleration_score`
- `session_consistency_score`
- `close_auction_strength_proxy_score`

## Validation

Use the existing `scripts/run_timing_category_frequency_validation.py` CLI for each category. The comparison must include only factors in the requested category that are rated `valuable` or `watchlist` on 5m. The final result should list confirmed factors, watchlist-only factors, negative factors, and next research direction.

## Guardrails

- Paper-only and shadow-only.
- Do not change official scoring fields.
- Do not connect to brokers or create executable trading instructions.
- Do not move a factor across categories after test registration unless a test is updated deliberately.
