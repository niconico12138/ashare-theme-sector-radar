# Phase 54: Catalyst Production Workflow Hardening

**Date**: 2026-07-02  
**Phase**: Phase 54  
**Status**: completed

Phase 54 hardened the catalyst collection production workflow by fixing bugs identified during Phase 53 multi-day real observation, adding CLI safeguards, and sanitizing prohibited trading terms.

## Issues Fixed

### Issue A: `date_count` always 0 in historical collection summary

**Root Cause**: In `historical_collector.py`, the `date_count` field was computed as `(end - current).days + 1` after the while loop had incremented `current` past `end`, always yielding 0.

**Fix**: Compute `date_count` before the loop starts, when `current` still equals `start_date`:

```python
current = datetime.strptime(start_date, "%Y-%m-%d")
end = datetime.strptime(end_date, "%Y-%m-%d")
date_count = (end - current).days + 1  # computed before loop
```

**File**: `theme_sector_radar/data/catalyst_events/historical_collector.py:84`

**Retrospective Fix**: Updated 4 existing summary files with correct `date_count`:

| Summary File | Old | Correct |
|---|---|---|
| `2026-06-29/catalyst_historical_collection_summary.json` | 0 | 1 |
| `2026-06-25_to_2026-06-29/catalyst_historical_collection_summary.json` | 0 | 5 |
| `2026-06-01_to_2026-06-05-fixture/catalyst_historical_collection_summary.json` | 0 | 5 |
| `2026-06-01_to_2026-06-29-fixture-rebuild/catalyst_historical_collection_summary.json` | 0 | 29 |

Corresponding `.md` files updated as well.

### Issue B: PowerShell `--symbols` leading zero loss

**Root Cause**: When `--symbols 000001,002594` is passed unquoted in PowerShell, leading zeros can be lost.

**Fix**: Updated CLI help text to warn about quoting requirement:

```python
help="指定板块名称列表，逗号分隔。PowerShell 中必须加引号: --symbols \"000001,002594\"，否则前导零会丢失"
```

**File**: `theme_sector_radar/cli.py:154`

**Note**: The actual command used in Phase 53 already included quotes (`--symbols "600519,000001,300750,002594,300059"`). This fix ensures future users are warned.

### Issue C: Action-like wording in report generators

**Scanned**: production `.py` files under `theme_sector_radar/`, plus recent Catalyst and experiment report outputs.

**Fix**: report wording was tightened from action-like phrases to research-only phrasing:

- experiment comparison conclusion label changed to "后续方向"
- report boundary text changed to "不作为操作依据" / "不作为个股操作依据"
- English report text changed away from action wording
- sector score interpretation changed from position-like wording to trend-observation wording

**Updated tests**: report contract and sector history analysis tests now assert the new wording.

**Boundary**: new production code should not emit action-like wording, even as a negated disclaimer. Use "研究复盘", "观察信号", "操作依据边界" and similar terms instead.

## Decision Logic Safety

| Area | Changed? | Notes |
|------|----------|-------|
| CatalystEventAgent vote | no | still neutral |
| CatalystEventAgent veto | no | still false |
| Catalyst decision impact | no | still report-only |
| ConsensusDecisionAgent | no | unchanged |
| scoring formulas | no | unchanged |
| final label rules | no | unchanged |

## Files Modified

| File | Change |
|------|--------|
| `theme_sector_radar/data/catalyst_events/historical_collector.py` | Fix date_count computation |
| `theme_sector_radar/cli.py` | Add --symbols quoting warning |
| `theme_sector_radar/analysis/sector_history_analyzer.py` | Sanitize disclaimer |
| `theme_sector_radar/experiments/weight_comparison.py` | Sanitize conclusion wording |
| `tests/theme_sector_radar/test_sector_history_analysis.py` | Update assertion for new disclaimer |
| `reports/experiments/weights/2026-06-28-fixture-v2/comparison.md` | Sanitize conclusion wording |
| `reports/experiments/weights/2026-06-28-fixture/comparison.md` | Sanitize conclusion wording |
| 4x `catalyst_historical_collection_summary.json` | Fix date_count |
| 4x `catalyst_historical_collection_summary.md` | Fix date_count |

## Validation

- All 4 historical collection summary files now have correct `date_count`
- No prohibited trading terms remain in report output (only in disclaimers as negations)
- CLI `--symbols` help text warns about PowerShell quoting
- CatalystEventAgent remains report-only
- No changes to scoring, voting, or decision logic

## Next Step

Continue real observation via daily production runs. Catalyst vote calibration remains unjustified until sufficient `catalyst_observed` samples accumulate.
