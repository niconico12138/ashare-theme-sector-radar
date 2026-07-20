# Event Adjustment Shadow Step 2 Results

## Delivered

- Added `event-adjustment-shadow-v1` with deterministic, versioned decomposition and
  separate sector/stock research outputs.
- Added configurable caps with defaults sector `[-12,+8]` and stock `[-10,+6]`.
- Added explicit post-event backtest exclusion and allowed-input lineage SHA binding.
- Added fail-closed zero adjustment for unknown, blocked, conflict, incomplete evidence,
  unknown mapping/direction, unknown market reflection, and expired exposure.
- Added logical-event, target exposure, and direct-company-versus-sector-transmission
  deduplication.
- Added a copper research fixture: upstream is positive, downstream is negative,
  midstream unknown is zero, mixed direction is zero, and later as-of values decay.

The fresh copper fixture produces `+0.72` upstream and `-0.48` downstream; fifteen days
later the same structural inputs decay to `+0.36` and `-0.24`. These are contract-test
values only, not market claims or formal ranking adjustments.

## Verification

- Step 1 plus Step 2 focused tests: `20 passed`.
- Related event data-layer regression set: `44 passed`.
- `compileall`: passed.
- `git diff --check`: passed.

## Gate Status

Step 2 is implemented only as `event_adjustment_shadow`. No formal sector/stock rank,
quant score, final score, V2 score, selection score, broker, order, or live path consumes
this output. Step 3 remains pending explicit main-conversation review.
