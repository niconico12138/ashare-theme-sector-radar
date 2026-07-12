# Price Momentum Factor Expansion Design

## Objective

Expand the intraday `price_momentum` research category from three to at least eleven factors. Evaluate the full set on 5-minute bars, then independently revalidate only `valuable` and `watchlist` factors on 1-minute bars.

## Scope and Guardrails

- Research artifacts remain paper-only and shadow-only.
- Do not connect a broker, emit executable signals, modify official score fields, or change realtime/paper entry rules.
- Preserve the existing 0-100 factor score convention and missing-data fallback behavior.

## Factor Set

Keep the current factors:

- `opening_drive_score`
- `morning_strength_persist_score`
- `late_return_30m_score`

Add at least eight factors grouped by intent:

- Multi-window return: 5m, 15m, 30m, and 60m return-strength scores.
- Trend persistence: positive-bar ratio and rolling price-slope scores.
- Breakout quality: intraday-high breakout strength and breakout hold score.
- Recovery: pullback-to-reclaim momentum score.

Each factor is a `higher_is_better` price-momentum measure unless its definition requires an explicit opposite direction.

## Data Flow

1. Compute the expanded factor set from candidate 5-minute OHLCV bars.
2. Write factor values to the existing experimental candidate payload fields.
3. Run the existing cross-date research CLI with the current future-return labels and threshold scan.
4. Select only factors rated `valuable` or `watchlist` for 1-minute recalculation.
5. Run the same factor definitions and threshold scan on 1-minute bars.
6. Mark a factor `1m_confirmed` only when it has enough 1-minute labeled coverage, keeps the expected direction, and retains positive separation. A failed or insufficient 1-minute result is reported explicitly, not silently promoted.

## Reporting

The research report will add frequency-aware factor results: 5-minute rating, 1-minute rating where eligible, coverage, direction agreement, and confirmation status. Existing report fields remain compatible.

## Tests

- Unit tests for strong, weak, boundary, and missing-bar inputs for every new factor.
- Catalog test proving every new factor maps only to `price_momentum`.
- Research tests proving 1-minute validation is restricted to 5-minute `valuable` or `watchlist` factors.
- Guardrail test/scan proving official scores and execution behavior are untouched.

## Completion Criteria

- At least eleven price-momentum factors are present in the catalog and research registry.
- 5-minute cross-date report is generated for the expanded set.
- Eligible factors receive a separate 1-minute validation result.
- Focused and regression tests pass with fresh command output.
