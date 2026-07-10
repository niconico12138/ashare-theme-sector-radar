# Open Source Release Checklist

Use this checklist before creating the public GitHub repository.

## Repository Shape

- [ ] Repository name is `a-share-theme-sector-radar`.
- [ ] Keep this as one complete main project, not split repositories.
- [ ] Include `theme_sector_radar/`, `scripts/`, `tests/`, `docs/`, `examples/`, `config/example.toml`, `.env.example`, `README.md`, `pyproject.toml`, and `LICENSE`.
- [ ] Do not include local StockDB raw data, full `data_cache/`, full `reports/`, `.env`, API keys, tokens, private paths, automatic trading modules, buy/sell advice, or unredacted Agent output.

## Investment Boundary

- [ ] README says the project is research-only.
- [ ] Docs say it is not investment advice, not a stock recommendation service, not an investment advisory service, and not an automated trading system.
- [ ] Sponsorship wording says sponsorship does not include advice, private recommendations, guaranteed support, or return promises.
- [ ] No docs or examples present output as buy/sell/hold instructions.

## Production vs Shadow Boundary

- [ ] `production_change_allowed = false` remains documented.
- [ ] Production `decision_score` weights are not changed.
- [ ] Production ranking behavior is not changed.
- [ ] V5 Regime Router Shadow Score is documented as `review_ready` and `shadow-only`.
- [ ] `review_ready` is not described as `production_enabled`.

## Sample Mode

- [ ] `python scripts/export_top30_candidates.py --sample` runs without StockDB.
- [ ] `python scripts/run_selection_validation_batch.py --mode sample --force` runs without StockDB.
- [ ] `python scripts/evaluate_regime_router_shadow_score_v5.py --sample` runs without StockDB.
- [ ] Sample outputs are clearly marked `sample_mode: true`.
- [ ] Sample outputs include investment-risk disclaimers.

## Configuration

- [ ] `.env.example` contains placeholders only.
- [ ] `config/example.toml` avoids private local paths.
- [ ] StockDB settings are optional and configurable by environment variables.
- [ ] Local defaults remain compatible for existing users but are not required for new open-source users.

## Git Hygiene

- [ ] `.gitignore` ignores `.env`, `.venv/`, `venv/`, `__pycache__/`, `.pytest_cache/`, `*.log`, `data_cache/`, `reports/`, StockDB data, database files, and temporary files.
- [ ] Already tracked `reports/` artifacts are removed from the Git index with `git rm --cached -r reports` before public release.
- [ ] Already tracked `data_cache/` artifacts, if any, are removed from the Git index with `git rm --cached -r data_cache` before public release.
- [ ] Any retained examples live under `examples/`, not `reports/`.

## Security Search

- [ ] Search for `API_KEY`, `token`, `password`, `secret`, `.env`, `C:\Users`, `E:\`, `stockdb`, `openai`, `ollama`, and `langchain api key`.
- [ ] Search for key-like patterns such as `sk-`.
- [ ] Review large files before staging.
- [ ] Rotate any credential that was ever committed or pasted into repo files, even if later redacted.

## Tests

- [ ] Run the required focused test command from `README.md`.
- [ ] Run sample-mode tests after any sample-mode or configuration change.
- [ ] Document failures, skipped checks, and residual risks in the release report.

## Release Decision

- [ ] Private GitHub repository is acceptable once source/docs are staged cleanly.
- [ ] Public release should wait until tracked reports/data are removed from the index, security search is clean, and leaked credentials are rotated.