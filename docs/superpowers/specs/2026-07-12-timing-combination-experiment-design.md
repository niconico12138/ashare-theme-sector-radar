# Timing Combination Experiment Design

## Goal

Build a paper-only experiment layer that iterates multiple intraday factor-combination versions and selects the best current version from historical labeled samples.

## Scope

- Use already backfilled timing factors and `forward_return_pct` labels.
- Keep output paper-only and shadow-only.
- Do not modify official scoring fields.
- Do not emit executable buy or sell instructions.

## Strategy Families

The first iteration should test these families:

- Time core: `open_to_midday_resilience_score`, `midday_hold_score`.
- VWAP confirmation: add `vwap_above_ratio_score`, `midday_vwap_support_score`.
- Position confirmation: add `late_high_near_close_score`, `high_area_acceptance_score`.
- Risk filtered: add low `high_to_close_drawdown_score`, `late_breakdown_risk`, `lower_low_sequence_risk`, `volume_without_price_progress_risk`.
- Relative strength add-on: add `stock_vs_market_intraday_alpha_score`, `relative_resilience_score`.
- Strict high-conviction: combine the strongest time, VWAP, position, and risk thresholds.

## Ranking

Rank versions by a research score that rewards positive selected average return, positive spread versus rejected candidates, positive win-rate spread, and enough selected samples. Penalize very tiny sample counts. The report must include all versions, the selected best version, and guardrails.

## Outputs

- JSON report with all version metrics and selected best version.
- Markdown report summarizing best version, ranked versions, and guardrails.
