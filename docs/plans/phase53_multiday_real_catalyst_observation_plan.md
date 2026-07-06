# Phase 53: Multi-day Real Catalyst Observation Plan

**Date**: 2026-07-01  
**Phase**: Phase 53  
**Goal**: expand Catalyst validation from one real day to a small multi-day real observation window.

## Scope

Phase 53 observes real Catalyst event collection over multiple dates. It does not change CatalystEventAgent decision impact.

## Constraints

- Do not modify `E:\Workspace\ai-stock-projects\ai-hedge-fund`.
- Keep CatalystEventAgent report-only.
- Do not modify vote, veto, scoring, or ConsensusDecisionAgent rules.
- Keep the real network symbol set small.
- Record failures honestly if AkShare or network access fails.

## Observation Window

```text
2026-06-25 to 2026-06-29
```

Symbol set:

```text
600519,000001,300750,002594,300059
```

PowerShell note: the comma-separated symbol list must be quoted to preserve leading zeros.

## Commands

```text
python scripts\network_smoke_test.py --symbols "600519,000001,300750,002594,300059"

python -m theme_sector_radar.cli --download-catalyst-events --network --start-date 2026-06-25 --end-date 2026-06-29 --symbols "600519,000001,300750,002594,300059" --refresh --report-root reports

python scripts\check_cache.py 2026-06-25
python scripts\check_cache.py 2026-06-29

python -m theme_sector_radar.cli --backtest-catalyst-events --start-date 2026-06-25 --end-date 2026-06-29 --report-root reports

python -m theme_sector_radar.cli --daily-health-check --as-of 2026-06-29 --report-root reports

python -m pytest tests/theme_sector_radar/ -v
```

## Acceptance Criteria

| Check | Expected |
|-------|----------|
| network smoke | `network_available` |
| generated dates | 5 |
| failed dates | 0 or documented |
| real events | greater than 0 |
| fixture events | 0 for refreshed observation window |
| mapping quality | generated |
| catalyst backtest | nonzero samples |
| daily health check | catalyst status inspected |
| Catalyst decision impact | still report-only |

## Phase 54 Gate

Phase 54 vote calibration should only proceed if real observed samples are large enough to compare `catalyst_observed` with `no_catalyst_observed`. A single observed sample is not enough.
