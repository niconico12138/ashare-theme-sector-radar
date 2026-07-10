# Contributing

Thanks for helping improve A-Share Theme Sector Radar.

## Project Boundary

This project is a research-oriented A-share theme/sector rotation and stock-candidate analysis framework. Contributions must preserve these boundaries:

- No investment advice, stock recommendations, buy/sell/hold instructions, or return promises.
- No automatic trading module or brokerage execution integration.
- No promotion of shadow models into production ranking without explicit review and separate approval.
- V5 Regime Router Shadow Score must remain described as `review_ready` and `shadow-only`, not `production_enabled`.
- Production `decision_score` weights and ranking behavior should not be changed unless a change is explicitly requested and reviewed.

## Data Policy

Do not commit local data or generated artifacts:

- `.env` or secrets
- StockDB raw data
- `data_cache/`
- full `reports/`
- private path configuration
- unredacted Agent outputs

Use small sanitized examples under `examples/` when a sample artifact is useful.

## Development

Run focused tests before opening a change:

```bash
python -m pytest tests/theme_sector_radar/test_defensive_shadow_score.py tests/theme_sector_radar/test_regime_router_shadow_score_v5.py tests/theme_sector_radar/test_shadow_v5_promotion_gate.py tests/theme_sector_radar/test_export_top30_candidates.py -q
```

For sample-mode changes, also run the sample-mode tests documented in `README.md`.