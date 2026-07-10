# 120-Day Selection Validation: Factor Diagnosis and Risk Rebuild Plan

## Background

The selection validation aggregate for `2026-01-05_to_2026-07-08` completed with 120 valid forward-return dates.

Current aggregate output:

- JSON: `reports/selection_validation/aggregate/2026-01-05_to_2026-07-08/selection_validation_aggregate.json`
- Markdown: `reports/selection_validation/aggregate/2026-01-05_to_2026-07-08/selection_validation_aggregate.md`

Current headline signals:

- `decision_score_signal`: inconclusive, gap about `-0.05pp`
- `stock_short_score_signal`: inconclusive, gap about `-0.23pp`
- `trade_eligibility_signal`: inconclusive
- `agent_incremental_signal`: inconclusive, gap about `-0.37pp`
- `trend_vs_burst_signal`: inconclusive, gap about `-0.22pp`

The sample size is now large enough for a more reliable diagnostic pass, but the evidence does not support production weight changes yet.

## Goal

Find why the current selection factors do not produce stable next-day alpha, then redesign the weak components as shadow-only features.

The near-term goal is not to change production ranking weights. The near-term goal is to create a stronger evidence layer for later changes.

## Non-Goals

- Do not change production `decision_score` weights.
- Do not expose raw rank fields.
- Do not remove existing filters for ST, delisted stocks, or non-main-board stocks.
- Do not make buy/sell recommendations.
- Do not make Agent LLM output directly decide production ranking.

## Phase 1: Full Factor Diagnostic

Create or extend a diagnostic script that reads all existing validation artifacts under:

`reports/selection_validation/2026-*/next_day_selection_validation.json`

The script should generate a report for `2026-01-05_to_2026-07-08`.

Required outputs:

- `reports/selection_validation/diagnostics/2026-01-05_to_2026-07-08/factor_diagnosis_120d.json`
- `reports/selection_validation/diagnostics/2026-01-05_to_2026-07-08/factor_diagnosis_120d.md`

Required analysis:

- Overall factor rank correlation with next-day return.
- Per-regime factor performance: `broad_up`, `broad_down`, `mixed`.
- Top/bottom group gaps for:
  - `decision_score`
  - `stock_short_score`
  - `stock_trend_score`
  - `sector_leader_score`
  - `risk_penalty_score`
  - `agent_score`
  - `shadow_decision_score_v2` if present
- Signal consistency by date.
- Hit rate difference between high-score and low-score groups.
- Top/bottom drawdown comparison using `next_low_return_pct` or `max_intraday_drawdown_pct`.
- Source pool comparison: `trend` vs `burst`.
- Agent comparison: analyzed vs skipped.

Interpretation rules:

- Mark a factor as `positive_signal` only if average gap is positive and consistency is at least 55%.
- Mark a factor as `negative_signal` only if average gap is negative and consistency is at least 55%.
- Otherwise mark it as `inconclusive`.
- If the sign flips between regimes, mark as `regime_dependent`.
- If high score reduces drawdown but does not improve return, mark as `defensive_not_alpha`.

Acceptance:

- Report must include total dates, valid dates, total candidates, and forward-return sample count.
- Report must list the strongest positive and strongest negative factors.
- Report must state whether production weight changes are allowed. Expected answer: `false`.
- Tests must cover empty data, regime split, sign flip, consistency threshold, and markdown generation.

## Phase 2: Risk Factor Rebuild

Current evidence suggests `risk_penalty_score` may mix real risk with volatility or elasticity. Split it into separate components.

Add or revise shadow-only fields:

- `hard_risk_penalty`: irreversible or structural exclusions.
- `trade_risk_penalty`: short-term execution risk.
- `volatility_elasticity_score`: opportunity-like volatility, not a penalty by default.
- `drawdown_risk_score`: actual next-day downside proxy, used only for diagnostics until validated.
- `risk_quality_tags`: explain which rules fired.

Suggested definitions:

`hard_risk_penalty`

- ST stock.
- Delisted or delisting risk.
- Non-main-board if the system scope excludes it.
- Very low liquidity.
- Missing critical data.

`trade_risk_penalty`

- Near limit-up.
- Large high rejection.
- Overextended above short moving average.
- Consecutive strong days with poor close position.
- Abnormal turnover without close strength.

`volatility_elasticity_score`

- Large true range.
- Volume expansion.
- Strong intraday range with positive close.
- Strong sector-relative movement.

`drawdown_risk_score`

- Close far below intraday high.
- Weak close position.
- Large recent run-up.
- Poor next-day low-return behavior in historical validation.

Acceptance:

- Existing production `risk_penalty_score` remains unchanged unless tests explicitly prove behavior is shadow-only.
- New fields appear in `top30_candidates.json`.
- New fields appear in factor quality reports.
- At least one diagnostic report compares old risk score vs rebuilt components.
- Tests verify that hard risk is not constant for all candidates unless data truly lacks risk variation.

## Phase 3: Short Score Rebuild

The current short score is still inconclusive. Rebuild it as a shadow feature first.

Add `stock_short_score_v2` and `stock_short_breakdown_v2`.

Candidate components:

- Close position: `(close - low) / (high - low)`.
- 3-day relative strength.
- 5-day relative strength.
- Volume expansion with positive close.
- Sector-relative strength.
- Rejection penalty.
- Overheat penalty.
- Data quality penalty.

Acceptance:

- `stock_short_score_v2` must have useful spread across candidates.
- `stock_short_score_v2` must not collapse to a few repeated values.
- Historical validation must compare v1 vs v2.
- Production ranking must not use v2 yet.

## Phase 4: Agent Output Reframing

Agent score should not directly change production weights until validated.

Add structured agent interpretation fields if available:

- `agent_catalyst_type`
- `agent_catalyst_strength`
- `agent_sustainability`
- `agent_risk_flags`
- `agent_reason_tags`

Use these as diagnostic features, not direct ranking weights.

Acceptance:

- Existing `agent_score` remains backward compatible.
- Missing agent fields do not break the pipeline.
- Diagnostic reports can compare candidates by catalyst type and risk tags.

## Phase 5: Shadow Decision Score V3

Create `shadow_decision_score_v3` after Phase 1-3 diagnostics.

Expected principles:

- Use production-safe base fields.
- Use rebuilt risk components.
- Treat volatility elasticity as separate from risk penalty.
- Apply regime-aware reporting, but do not make production ranking regime-dependent yet.

Acceptance:

- Current production score and shadow v3 are reported side by side.
- Historical validation compares current vs v3 over 20/40/60/120 day windows.
- `production_change_allowed` remains `false` until v3 beats current score consistently.

## Suggested Test Commands

Run focused tests first:

```bash
python -m pytest tests/theme_sector_radar/test_factor_failure_diagnosis.py \
  tests/theme_sector_radar/test_factor_direction_calibration.py \
  tests/theme_sector_radar/test_risk_component_quality.py \
  tests/theme_sector_radar/test_selection_validation_batch.py -q
```

Then run relevant new tests added for the phase.

## Delivery Checklist

Each implementation pass should report:

- Modified file list.
- New report paths.
- Test commands and results.
- Number of valid dates and forward-return samples used.
- Factor conclusions.
- Whether production weight changes are allowed.
- Any remaining data quality caveats.

## Recommended Next Step

Start with Phase 1 and Phase 2 only.

Reason:

- Phase 1 tells us which factors are truly weak versus regime-dependent.
- Phase 2 addresses the highest-risk design issue: risk score may be penalizing volatility/elasticity instead of actual risk.
- Production weights should stay frozen until these two are complete.
