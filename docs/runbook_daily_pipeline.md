# Daily Pipeline Runbook

## Sample Run

```bash
python scripts/export_top30_candidates.py --sample
python scripts/run_selection_validation_batch.py --mode sample --force
python scripts/evaluate_regime_router_shadow_score_v5.py --sample
```

## Fixture Board Radar

```bash
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --offline-fixture --fixture-profile full --lookback-days 5 --report-root reports/theme_sector_radar
```

## Real Data Preflight

Before real runs, check:

- `MARKET_DATA_SERVICE_URL` if using the HTTP data service.
- StockDB host/port if using StockDB.
- AkShare network availability.
- `.env` does not get committed.
- `reports/` and `data_cache/` are ignored.

## Real Daily Shape

```bash
python scripts/run_daily_unified_pipeline.py --as-of YYYY-MM-DD
python scripts/export_top30_candidates.py --as-of YYYY-MM-DD --stock-limit 30 --agent-stock-limit 10
```

Review all degradation flags before interpreting output. Reports are research artifacts only.
