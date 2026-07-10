# Open Source Data Policy

Do include:

- Source code under `theme_sector_radar/`.
- Command scripts under `scripts/`.
- Tests and small fixtures.
- Documentation.
- `config/example.toml`, `config/daily.example.json`, and `.env.example`.
- Small sanitized examples under `examples/`.

Do not include:

- `.env` files or API keys.
- Local StockDB raw data.
- Full `data_cache/`.
- Full `reports/` history.
- Private local paths such as `C:\Users\...`, `E:\...`, or Desktop StockDB paths as required defaults.
- Raw, unsanitized Agent transcripts.
- Any automatic trading modules or buy/sell advice.

Real data dependencies should be configurable through environment variables or config files. Sample mode must remain runnable without external data.
