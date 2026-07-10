# Architecture Overview

Theme Sector Radar is a single-repository research framework.

Main layers:

- `theme_sector_radar/cli.py`: user-facing CLI entry point.
- `theme_sector_radar/pipeline.py`: daily board radar orchestration.
- `theme_sector_radar/models.py`: core report and provider contracts.
- `theme_sector_radar/data/`: AkShare, fixture, HTTP service, StockDB, and cache adapters.
- `theme_sector_radar/scoring/`: production and shadow scoring functions.
- `theme_sector_radar/agents/`: research agents and report helpers.
- `scripts/`: operational and research scripts.
- `tests/`: regression and contract tests.

Data boundaries:

- Public sample mode uses fixtures/synthetic data.
- Real board data can come from AkShare.
- Local K-line and constituent data can come from `market_data_service` or StockDB when configured.

The project should not import downstream trading systems directly. Agent integration is a research handoff layer, not a trading layer.
