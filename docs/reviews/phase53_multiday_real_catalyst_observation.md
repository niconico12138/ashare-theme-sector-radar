# Phase 53: Multi-day Real Catalyst Observation

**Date**: 2026-07-01  
**Phase**: Phase 53  
**Status**: completed

Phase 53 expanded Catalyst validation from a single real day to a five-day real observation window. CatalystEventAgent remains report-only.

## Commands Run

```text
python scripts\network_smoke_test.py --symbols "600519,000001,300750,002594,300059"

python -m theme_sector_radar.cli --download-catalyst-events --network --start-date 2026-06-25 --end-date 2026-06-29 --symbols "600519,000001,300750,002594,300059" --refresh --report-root reports

python scripts\check_cache.py 2026-06-25
python scripts\check_cache.py 2026-06-29

python -m theme_sector_radar.cli --backtest-catalyst-events --start-date 2026-06-25 --end-date 2026-06-29 --report-root reports

python -m theme_sector_radar.cli --daily-health-check --as-of 2026-06-29 --report-root reports
```

## Network Smoke Result

| Check | Result |
|-------|--------|
| AkShare import | ok |
| AkShare version | 1.18.64 |
| tested symbols | 600519, 000001, 300750, 002594, 300059 |
| `stock_news_em` | ok for all symbols |
| overall status | `network_available` |

PowerShell command quoting matters. Without quotes around the comma-separated symbol list, leading zeros can be lost. The successful command used quotes.

## Real Catalyst Collection Result

Output:

```text
reports/data_downloads/catalyst_events/2026-06-25_to_2026-06-29/
```

| Metric | Value |
|--------|-------|
| generated_dates | 5 |
| skipped_dates | 0 |
| failed_dates | 0 |
| total_events | 116 |
| real_event_count | 116 |
| fixture_event_count | 0 |
| mapped_events | 116 |
| unmapped_events | 0 |

## Mapping Quality

| Metric | Value |
|--------|-------|
| event_count | 116 |
| mapped_count | 116 |
| unmapped_count | 0 |
| mapping_rate | 100% |
| status_counts | `mapped_by_symbol: 116` |

Mapping report:

```text
reports/data_downloads/catalyst_events/2026-06-25_to_2026-06-29/catalyst_mapping_quality.json
reports/data_downloads/catalyst_events/2026-06-25_to_2026-06-29/catalyst_mapping_quality.md
```

## Cache Spot Checks

| Date | Event Count | Source | Mapped | Unmapped | Source Status |
|------|-------------|--------|--------|----------|---------------|
| 2026-06-25 | 25 | `akshare_stock_news_em` | 25 | 0 | ok |
| 2026-06-29 | 22 | `akshare_stock_news_em` | 22 | 0 | ok |

The terminal may display mojibake for Chinese titles, but JSON strings are valid Unicode.

## Catalyst Backtest Result

Command:

```text
python -m theme_sector_radar.cli --backtest-catalyst-events --start-date 2026-06-25 --end-date 2026-06-29 --report-root reports
```

Output:

```text
reports/backtests/catalyst_events/2026-06-25_to_2026-06-29/
```

| Metric | Value |
|--------|-------|
| total_samples | 50 |
| cache_coverage | 100% |
| data_status_counts.real | 50 |
| data_status_counts.fixture | 0 |
| catalyst_observed | 1 |
| no_catalyst_observed | 49 |
| recommend_vote_calibration | false |

Forward-return fields are not yet informative for this narrow late-June window because there is not enough future data after the signal dates.

## Daily Health Check

Command:

```text
python -m theme_sector_radar.cli --daily-health-check --as-of 2026-06-29 --report-root reports
```

Result:

| Check | Status |
|-------|--------|
| overall | ok |
| radar | ok |
| research | ok |
| catalyst | ok |
| data_source_mode | sector_history_replay |

Output:

```text
reports/daily_health/2026-06-29/daily_health_check.json
reports/daily_health/2026-06-29/daily_health_check.md
```

## Decision Logic Safety

| Area | Changed? | Notes |
|------|----------|-------|
| CatalystEventAgent vote | no | still neutral |
| CatalystEventAgent veto | no | still false |
| Catalyst decision impact | no | still report-only |
| ConsensusDecisionAgent | no | unchanged |
| scoring formulas | no | unchanged |
| final label rules | no | unchanged |

## Conclusion

Real multi-day Catalyst collection is operational. The cache now contains a five-day real observation window with 116 real events and 100% symbol-based mapping in this controlled symbol set.

However, Phase 54 vote calibration is not justified yet:

- only 1 backtest sample is `catalyst_observed`;
- the window is too short;
- forward-return validation is not informative for late-window dates;
- all evidence supports continuing observation rather than changing decision rules.

## Next Step

Phase 54 should not calibrate Catalyst vote yet. The better next phase is to extend real observation over more trading days, preferably using daily production runs, and only revisit Catalyst vote calibration after enough real `catalyst_observed` samples accumulate.
