# Sample Mode

Sample mode is the public demo path. It must run without StockDB, market_data_service, network access, or API keys.

Commands:

```bash
python scripts/export_top30_candidates.py --sample
python scripts/run_selection_validation_batch.py --mode sample --force
python scripts/evaluate_regime_router_shadow_score_v5.py --sample
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --offline-fixture --fixture-profile full --lookback-days 5 --report-root reports/theme_sector_radar
```

Sample outputs are synthetic or fixture-based. They demonstrate file formats and workflow shape. They are not market conclusions and not investment advice.
