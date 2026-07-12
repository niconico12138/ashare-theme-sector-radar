# Timing Factor Catalog

This catalog is for paper-only intraday buy and exit timing experiments. It does not emit executable trading signals.

## Categories

| Category | Purpose | Example factors |
|---|---|---|
| `price_momentum` | Detect intraday launch, acceleration, and breakout behavior. | current change %, 5m/15m return, slope, new intraday high |
| `volume_money_flow` | Confirm whether price movement has money behind it. | amount strength, volume ratio, late amount share, volume-price confirmation |
| `vwap_mean_price` | Check whether price has support around intraday average cost. | price vs VWAP, VWAP reclaim, VWAP slope, time above VWAP |
| `intraday_position` | Avoid bad locations and describe where price sits in the day range. | distance to high, distance to low, range position, pullback from high |
| `sector_confirmation` | Confirm that a candidate is moving with a real sector theme. | sector breadth, sector late breadth, leader-follower sync |
| `relative_strength` | Prefer stocks stronger than their sector or market. | stock vs sector alpha, sector rank, stock vs index strength |
| `risk_reversal` | Penalize false breakouts, chasing, and reversal risk. | anti-chasing, spike fade, volume-without-price-progress, high-open failure |
| `time_structure` | Account for when the signal occurs during the day. | open drive, morning persistence, afternoon recovery, late strength |

## Current Implemented Factors

| Factor | Category | Used by |
|---|---|---|
| `intraday_momentum` | `price_momentum` | buy timing |
| `amount_strength` | `volume_money_flow` | buy timing |
| `sector_confirmation` | `sector_confirmation` | buy timing |
| `vwap_position` | `vwap_mean_price` | buy timing |
| `anti_chasing` | `risk_reversal` | buy timing |

## Factor Research V1

`theme_sector_radar.timing.factor_research` evaluates the eight timing categories as paper-only research. It uses candidate-level factor values plus a future return label, then splits each factor into high/low groups and compares adjusted forward-return spread.

### Expanded Price Momentum Set

The `price_momentum` category now contains eleven paper-only research factors:

| Factor | Meaning |
|---|---|
| `opening_drive_score` | Strength of the opening launch. |
| `morning_strength_persist_score` | Ability to retain early-session strength. |
| `late_return_30m_score` | Late 30-minute return strength. |
| `return_5m_strength_score` | Latest 5-minute return strength. |
| `return_15m_strength_score` | Latest 15-minute return strength. |
| `return_60m_strength_score` | Latest 60-minute return strength. |
| `positive_bar_ratio_score` | Share of rising intraday bars. |
| `rolling_price_slope_score` | Slope of the trailing intraday price path. |
| `intraday_breakout_strength_score` | Strength of the latest new-high breakout. |
| `breakout_hold_score` | Ability to hold the breakout above the earlier high. |
| `pullback_reclaim_momentum_score` | Momentum of the latest pullback recovery. |

All eleven use `higher_is_better`. They are research fields only and do not alter official candidate scores.

### Expanded Volume Money Flow Set

The `volume_money_flow` category now contains eleven paper-only research factors:

| Factor | Meaning |
|---|---|
| `amount_acceleration_score` | Second-half amount acceleration versus first half. |
| `late_volume_efficiency_score` | Whether late volume produces price progress without crowding. |
| `volume_spike_exhaustion_score` | Exhaustion risk from abnormal volume spikes and giveback. |
| `early_amount_surge_score` | Early amount surge that still retains price progress. |
| `midday_amount_sustain_score` | Whether amount remains active through the middle of the day. |
| `late_amount_surge_score` | Late-session amount expansion with late price strength. |
| `amount_trend_persistence_score` | Persistence of intraday amount expansion alongside rising prices. |
| `volume_price_alignment_score` | Bar-by-bar alignment between amount changes and price movement. |
| `breakout_volume_confirm_score` | Whether a new intraday high has late volume support. |
| `pullback_volume_dryup_score` | Whether pullbacks happen on reduced amount. |
| `late_money_flow_concentration_score` | Quality of late money-flow concentration. |

All new fields are `higher_is_better` except `volume_spike_exhaustion_score`, which remains `lower_is_better`.

### 5m Then 1m Validation

Run the full price-momentum set on 5-minute bars first. Only a factor rated `valuable` or `watchlist` in that 5-minute report is eligible for 1-minute comparison. A factor is `1m_confirmed` only when its direction agrees, its 1-minute rating is `valuable` or `watchlist`, and its 1-minute adjusted spread is positive. Missing 1-minute coverage is reported as `insufficient_1m_coverage`; it is not treated as a pass.

Direction handling:

- `higher_is_better`: high factor values should have better future returns.
- `lower_is_better`: low risk values should have better future returns.

Ratings:

- `valuable`: positive spread and value score in the current labeled sample.
- `watchlist`: weak positive evidence; keep observing.
- `weak`: no useful separation yet.
- `negative`: current split is directionally harmful.
- `not_enough_split`: enough labels but factor values do not split cleanly.
- `insufficient_labeled_samples`: not enough labeled samples for judgment.

CLI:

```powershell
python scripts\run_timing_factor_research.py `
  --candidate-json reports\agent_bridge\2026-07-07\top30_candidates.intraday_backfilled.json `
  --output-dir reports\timing_factor_research\2026-07-07_codex_v1 `
  --as-of 2026-07-07 `
  --snapshot-label codex_v1 `
  --min-labeled-samples 10
```

The CLI automatically reads `reports/agent_bridge/selection_validation/<date>/next_day_selection_validation.json` when available and uses `next_return_pct` as the forward label.

Single-day exploratory result, `2026-07-07_codex_v1`:

| Category | Current useful factors | Current interpretation |
|---|---|---|
| `price_momentum` | `late_return_30m_score` | Late momentum was more useful than opening drive in this weak next-day sample. |
| `volume_money_flow` | `late_volume_efficiency_score` | Efficient late volume was better than raw amount acceleration. |
| `vwap_mean_price` | `close_vs_vwap_score`, `vwap_slope_score`, `vwap_reclaim_score` | VWAP structure showed the clearest positive separation. |
| `intraday_position` | None yet | Current location factors did not show useful separation in the first sample. |
| `sector_confirmation` | None yet | Values were not split enough to judge; needs more varied samples. |
| `relative_strength` | None yet | Current sector/market relative fields were negative or unsplit. |
| `risk_reversal` | `afternoon_fade_score` | Lower afternoon fade risk was useful as a filter. |
| `time_structure` | `intraday_late_strength_score`, `short_burst_intraday_emotion_score_shadow` | Late-session behavior was more informative than early-session repair/resilience. |

This first run is a small-sample result: 30 candidates, 29 next-day labels, and about 14 labeled rows for most intraday factors. Treat it as a research direction, not a trading rule.

Cross-date labeled result, `2026-01-05_to_2026-07-10_codex_labeled_v1`:

- Candidate files: 185
- Candidate samples: 3239
- Labeled samples: 2055
- Intraday observed samples: 295
- Missing validation dates: 63
- Minimum labeled samples per factor: 50

| Category | Current useful factors | Current interpretation |
|---|---|---|
| `price_momentum` | None yet | Opening drive, morning persistence, and late 30m return did not separate positively across the wider sample. |
| `volume_money_flow` | None as positive entry factor | Raw amount acceleration and late volume efficiency were negative; volume spike exhaustion is weak. |
| `vwap_mean_price` | None yet | VWAP factors were positive in the single day but negative in the wider sample; do not promote yet. |
| `intraday_position` | None yet | Current position factors were mostly negative in the wider sample. |
| `sector_confirmation` | None yet | Sector confirmation fields did not split enough; needs richer and more varied data. |
| `relative_strength` | `market_regime_score` is weak only | Broad market support has mild positive separation but not enough to call valuable. |
| `risk_reversal` | `volume_without_price_progress_risk` watchlist | Lower risk of volume without price progress helped as a filter, not an entry trigger. |
| `time_structure` | `open_to_midday_resilience_score` watchlist | Open-to-midday resilience is the best current candidate for buy-timing research. |

Current promotion status:

- Do not promote any factor to live or paper-entry thresholds yet.
- Keep `open_to_midday_resilience_score` and `volume_without_price_progress_risk` in the next research round.
- Treat single-day VWAP and late-strength positives as unstable until they recover across more dates.
- The next bottleneck is intraday observed coverage: only 295 of 3239 candidate rows currently have the richer intraday fields.

After 5m intraday backfill for `2026-06-01` to `2026-07-10`, report `2026-01-05_to_2026-07-10_after_0601_0710_backfill_thresholds`:

- Matched 5m intraday bars: 496 / 671 requested rows in the backfill window.
- Intraday observed samples improved from 295 to 691.
- Labeled intraday factor samples improved from 273 to 654.
- Valuable factors: 2
- Watchlist factors: 8

Current highest-priority factors:

| Factor | Category | Role | Current threshold insight |
|---|---|---|---|
| `open_to_midday_resilience_score` | `time_structure` | Entry-quality candidate | `>= 80` had the best threshold spread in this run: selected avg return `1.2513%` vs rejected `-0.3669%`. |
| `volume_without_price_progress_risk` | `risk_reversal` | Risk filter | High-risk tail was very weak; use as a block/penalty candidate, not as an entry booster. |
| `opening_drive_score` | `price_momentum` | Watchlist only | High thresholds looked better, but median split is only watchlist; needs stability checks. |
| `late_high_near_close_score` | `intraday_position` | Watchlist only | May help describe good location, but evidence is weaker than midday resilience. |

Research implication:

- Next paper experiment should test `open_to_midday_resilience_score >= 80` as a strict timing-quality filter.
- Next risk experiment should test blocking or penalizing high `volume_without_price_progress_risk`, rather than rewarding low values directly.
- Do not combine all watchlist factors yet; first test the two strongest factors independently.

## Testing Strategy

1. Unit test every factor with strong, weak, and missing-data inputs.
2. Boundary test each factor near thresholds, such as high change %, weak amount, and invalid price.
3. Verify every factor is mapped to exactly one category in `factor_catalog.py`.
4. Keep factor output in a stable 0-100 range unless explicitly documented otherwise.
5. Add buy-timing score tests that prove low-quality candidates move to `pending_candidates`.
6. Run historical paper tests before changing live realtime thresholds.
7. Run realtime smoke with permissive, medium, and strict `min_buy_timing_score` values.
8. Track factor contribution in reports so score changes are explainable.

## Required Test Types

| Test type | What it proves | Current examples |
|---|---|---|
| Single-factor strength | Strong inputs score above weak inputs. | `intraday_momentum` rises with `change_pct`. |
| Boundary behavior | Threshold edges are stable and explainable. | `amount_strength` at 0.5x, 1.0x, and 2.0x reference amount. |
| Directionality | Factor direction does not accidentally invert. | Above VWAP scores higher than equal VWAP, equal scores higher than below VWAP. |
| Missing-data fallback | Bad realtime inputs do not crash the watch loop. | Missing VWAP falls back to neutral 50. |
| Risk flag behavior | Risk tags appear only when their trigger is present. | High change near intraday high sets `chasing_risk`. |
| Threshold experiment | Score thresholds can be compared before changing runtime filters. | `evaluate_buy_timing_thresholds` reports trade count, win rate, average return, and missed winners. |

## Threshold Experiment Metrics

Each candidate should provide a precomputed `buy_timing_score` and a later `forward_return_pct`.
The experiment should compare thresholds such as `55`, `60`, `65`, `70`, `75`, and `80`.

| Metric | Reason |
|---|---|
| `trade_count` | Avoid thresholds that remove too many opportunities. |
| `win_rate` | Check whether higher scores improve hit rate. |
| `avg_forward_return_pct` | Check whether the selected threshold improves expected return. |
| `min_forward_return_pct` | Reveal downside among selected names. |
| `max_forward_return_pct` | Reveal upside among selected names. |
| `missed_winner_count` | Catch thresholds that filter out too many later winners. |

## Expansion Order

1. Add `intraday_position` factors: distance to high, distance to low, range position.
2. Add richer `vwap_mean_price` factors: VWAP reclaim and time above VWAP.
3. Add `relative_strength`: stock versus sector and stock versus index.
4. Add `time_structure`: morning persistence and afternoon recovery.
5. Add exit-timing factors only after buy-timing factors are stable in paper trading.

## Intraday Bar Granularity

Historical paper trading currently uses daily bars for next-day entry and daily high/low exits. For timing research, use minute bars:

| Granularity | Use |
|---|---|
| `5m` | Factor research, threshold experiments, and broad timing comparisons. |
| `1m` | Precise trigger validation, stop-loss/take-profit order sequencing, and live-readiness rehearsal. |
| tick / Level2 | Not required for the current paper-only system. Consider only after stable 1m validation. |

The first trigger module is `theme_sector_radar.timing.intraday_trigger`:

- `evaluate_intraday_buy_trigger` finds the first minute bar that satisfies paper-only buy conditions.
- `evaluate_intraday_exit_sequence` checks whether stop-loss or take-profit is reached first.
- If stop-loss and take-profit are both touched in the same bar, the result is conservative: stop-loss wins.
- `run_intraday_trigger_experiment` applies those checks across a candidate set and summarizes trigger rate, exit reasons, and average return.

Use `5m` first to explore candidate factor quality. Re-run promising rules with `1m` before changing realtime paper thresholds.

## Recommended Research Flow

1. Use daily bars to build the candidate pool.
2. Use `5m` bars to compute timing factors and compare `buy_timing_score` thresholds.
3. Use `1m` bars to validate exact trigger time and stop-loss/take-profit sequence.
4. Promote only paper-tested thresholds into realtime watch configuration.
5. Keep all outputs marked `paper_trading_only` and `no_execution_signals`.
