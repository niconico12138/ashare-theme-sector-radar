# Volume Money Flow Expansion Design

## Goal

Expand the paper-only intraday `volume_money_flow` research category from three factors to at least eleven factors, then evaluate it with the same 5-minute first, 1-minute confirmation workflow used for price momentum.

## Scope

- Keep all new fields shadow-only and research-only.
- Do not modify `final_score`, `v2_score`, `selection_score`, or `selection_score_adjusted`.
- Do not emit executable trading signals or broker instructions.
- Use the existing intraday backfill and timing research pipeline.

## Factor Set

The category will retain:

- `amount_acceleration_score`
- `late_volume_efficiency_score`
- `volume_spike_exhaustion_score`

It will add these experimental factors:

- `early_amount_surge_score`
- `midday_amount_sustain_score`
- `late_amount_surge_score`
- `amount_trend_persistence_score`
- `volume_price_alignment_score`
- `breakout_volume_confirm_score`
- `pullback_volume_dryup_score`
- `late_money_flow_concentration_score`

These cover short-window amount expansion, sustained money flow, late-session concentration, volume-price alignment, breakout confirmation, and pullback dry-up support.

## Workflow

Add a generic category frequency-validation CLI so `volume_money_flow` can reuse the same 5m-to-1m validation path without cloning price-momentum logic. The 1m comparison must only include factors in the requested category that were rated `valuable` or `watchlist` on 5m.

## Tests

- Calculator tests prove the new volume-money-flow fields reward supported money flow over exhausted flow.
- Missing intraday bars return `None` for all new fields.
- Research spec tests prove `volume_money_flow` has at least eleven registered factors.
- Frequency-comparison tests prove category filtering works for both `price_momentum` and `volume_money_flow`.
- CLI tests prove the new category validation report is paper-only and writes JSON/Markdown.
