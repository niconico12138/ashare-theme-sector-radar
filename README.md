# A-Share Theme Sector Radar

A research-oriented A-share theme/sector rotation and stock-candidate analysis framework.

中文定位：一个面向 A 股主题/板块轮动的研究型选股框架，支持候选股发现、因子评分、Agent 辅助分析、历史验证与 shadow score 研究。

## Disclaimer

This project is for research, education, and workflow automation only. It is not investment advice, not a stock recommendation service, not an investment advisory service, and not an automated trading system. Outputs must not be used as buy, sell, hold, or return-guarantee instructions.

## Core Capabilities

- A-share industry and concept board analysis.
- Candidate stock pool generation for research workflows.
- Rule-based factor scoring and risk decomposition.
- Daily pipeline reports in JSON and Markdown.
- Historical selection validation.
- Shadow score research, including V5 Regime Router Shadow Score.
- Optional Agent-assisted analysis with strict research boundaries.

## Current Research Status

The latest internal validation window covers 2026-01-05 to 2026-07-08 with 120 valid validation days. Production `decision_score` remains unchanged and has ordinary 120d performance. The strongest current research model is V5 Regime Router Shadow Score:

- 120d Top-Bottom Gap: +4.59
- Hit Rate Diff: +56.0
- Spearman rho: +0.54
- Consistency: 55.0%
- broad_up gap: +0.07
- broad_down gap: +0.78
- mixed gap: +0.15
- Promotion Gate: `review_ready`

Important: `review_ready` means ready for human review. It does not mean `production_enabled`.

## Production vs Shadow Boundary

- `production_change_allowed = false`
- V5 is `shadow-only`
- Production weights were not changed
- Production ranking was not changed
- `review_ready` is not automatic production adoption

## Installation

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell users can also activate manually
pip install -e .[dev]
```

Minimal dependency install:

```bash
pip install -r requirements.txt
```

## Quick Start: Sample Mode

Sample mode uses deterministic fixture/synthetic data. It does not require StockDB, market_data_service, API keys, or historical reports.

```bash
python scripts/export_top30_candidates.py --sample
python scripts/run_selection_validation_batch.py --mode sample --force
python scripts/evaluate_regime_router_shadow_score_v5.py --sample
```

Core board radar fixture mode:

```bash
python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --offline-fixture --fixture-profile full --lookback-days 5 --report-root reports/theme_sector_radar
```

See [docs/sample_mode.md](docs/sample_mode.md).

## Real Data Configuration

Real data workflows may use AkShare, a local `market_data_service`, and optionally StockDB.

1. Copy `.env.example` to `.env`.
2. Set `MARKET_DATA_SERVICE_URL` if using the local HTTP service.
3. Set StockDB settings only if you have StockDB installed.
4. Keep `.env`, `data_cache/`, and `reports/` out of Git.

See [docs/open_source_data_policy.md](docs/open_source_data_policy.md).

## Daily Pipeline

```bash
python run_daily.py --as-of 2026-07-08 --mode fixture
python scripts/run_daily_unified_pipeline.py --as-of 2026-07-08
```

For production-like real data runs, confirm data source availability first and review all degradation flags. See [docs/runbook_daily_pipeline.md](docs/runbook_daily_pipeline.md).

## Top30 Candidate Export

```bash
python scripts/export_top30_candidates.py --as-of 2026-07-08 --stock-limit 30 --agent-stock-limit 10
```

Sample export:

```bash
python scripts/export_top30_candidates.py --sample --stock-limit 5 --agent-stock-limit 3
```

The export hides raw rank and is intended for research handoff, not recommendations.

## Historical Validation

```bash
python scripts/run_selection_validation_batch.py --start-date 2026-01-05 --end-date 2026-07-08 --mode existing-artifacts --source stockdb-sdk --force
```

See [docs/validation_methodology.md](docs/validation_methodology.md).

## Shadow Score / V5

V5 Regime Router Shadow Score routes between bull, defensive, and blended profiles by market regime. It is a research score only.

```bash
python scripts/evaluate_regime_router_shadow_score_v5.py --sample
```

For historical artifacts:

```bash
python scripts/evaluate_regime_router_shadow_score_v5.py --aggregate-path reports/selection_validation/aggregate/2026-01-05_to_2026-07-08/selection_validation_aggregate.json --validation-root reports/selection_validation --candidate-root reports/agent_bridge --output-dir reports/selection_validation/shadow_score_v5/2026-01-05_to_2026-07-08
```

## Project Structure

```text
theme_sector_radar/   core package
scripts/              command-line research utilities
tests/                pytest suite
docs/                 architecture, runbooks, methodology, phase reports
config/               example config files
examples/             small sanitized examples only
reports/              generated output, ignored by Git
data_cache/           local cache, ignored by Git
```

## Tests

Focused V5/open-source readiness checks:

```bash
python -m pytest tests/theme_sector_radar/test_defensive_shadow_score.py tests/theme_sector_radar/test_regime_router_shadow_score_v5.py tests/theme_sector_radar/test_shadow_v5_promotion_gate.py tests/theme_sector_radar/test_export_top30_candidates.py -q
```

Sample-mode checks:

```bash
python -m pytest tests/theme_sector_radar/test_export_top30_candidates.py::test_export_sample_top30_writes_demo_artifacts tests/theme_sector_radar/test_selection_validation_batch.py::test_run_sample_batch_writes_validation_artifacts tests/theme_sector_radar/test_regime_router_shadow_score_v5_evaluation.py::test_run_sample_evaluation_writes_shadow_v5_outputs -q
```

## FAQ

**Is this a stock recommendation system?**  
No. It is a research framework.

**Can I run it without StockDB?**  
Yes. Use sample mode and offline fixture mode.

**Does V5 replace production ranking?**  
No. V5 is `review_ready` and `shadow-only`, not `production_enabled`.

**Should I commit reports?**  
No. Full `reports/` and `data_cache/` are generated/local artifacts. Keep only small sanitized examples under `examples/`.

## Sponsorship

If this project helps your research workflow, you can support its maintenance. Sponsorship does not include investment advice, private stock recommendations, guaranteed support, or return promises.

## License

Add a project license before publishing publicly. MIT is assumed in `pyproject.toml` until replaced.
