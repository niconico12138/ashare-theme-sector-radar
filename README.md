# A-Share Theme Sector Radar

> A research framework for A-share theme/sector rotation and stock-candidate analysis.

中文定位：面向 A 股主题与行业板块轮动的研究型分析框架。它将行情、板块成分、基准和因子数据组织为可审计的研究流水线，输出板块强弱、个股研究候选、数据质量标记和历史验证结果。

## Important boundary

This project is for research, education, and workflow automation only. It is **not** investment advice, a stock recommendation service, an investment advisory service, or an automated trading system. It does not connect to brokers, place orders, generate position instructions, or promise returns. All outputs require independent human review.

本项目仅用于研究、学习和工作流自动化；不构成投资建议，不生成买卖指令，不接入券商。候选股是后续研究对象，不是交易清单。

## What it does

- Scores A-share industry and concept boards to identify research directions.
- Builds a board-aware stock candidate pool instead of ranking the whole market indiscriminately.
- Evaluates momentum, trend, liquidity, valuation, volatility, drawdown, data quality and other factors.
- Produces structured JSON/Markdown reports for reproducible daily research runs.
- Validates candidate-selection methods against historical data and diagnoses failure modes.
- Runs experimental Shadow Score models separately from the protected baseline ranking.
- Supports optional agent-assisted diagnostics while preserving the research-only boundary.

## Architecture

```mermaid
flowchart TB
    subgraph Sources["1. 数据来源"]
        S1["AkShare / 公开市场数据"]
        S2["本地 StockDB（可选）"]
        S3["本地行情数据服务（可选）"]
        S4["离线测试夹具 / 脱敏示例"]
    end

    subgraph Data["2. 数据与溯源层"]
        D1["数据源路由与重试"]
        D2["快照、K线、基准与板块成分股"]
        D3["标准化与数据血缘校验"]
        D4["本地缓存（不纳入 Git）"]
    end

    subgraph Research["3. 研究与评分层"]
        R1["板块评分\n趋势 · 动量 · 截面强度"]
        R2["风险与数据质量诊断"]
        R3["板块轮动 / 方向候选"]
        R4["个股因子与板块-个股关联度"]
        R5["候选筛选\n排序 · 配额 · 集中度控制"]
    end

    subgraph Validation["4. 验证与 Shadow 层"]
        V1["前瞻收益标签"]
        V2["历史选股验证"]
        V3["校准、归因与稳定性诊断"]
        V4["影子评分\n仅限研究"]
    end

    subgraph Outputs["5. 输出层"]
        O1["每日 JSON / Markdown 报告"]
        O2["Top-N 研究候选"]
        O3["运行日志、降级标记与审计产物"]
    end

    S1 --> D1
    S2 --> D1
    S3 --> D1
    S4 --> D1
    D1 --> D2 --> D3 --> D4
    D3 --> R1
    D3 --> R2
    R1 --> R3 --> R4 --> R5
    R2 --> R1
    R2 --> R5
    R5 --> O1
    R5 --> O2
    R5 --> V1 --> V2 --> V3 --> V4
    V2 --> O3
    V3 --> O3
    V4 --> O3
```

### Research data flow

```mermaid
flowchart LR
    A["研究日期"] --> B["加载行情与板块输入"]
    B --> C["校验时效性、身份与覆盖率"]
    C -->|"可用"| D["计算板块评分"]
    C -->|"降级"| X["记录标记 / 使用允许的后备数据"]
    D --> E["筛选合格研究方向"]
    E --> F["获取板块成分股与个股因子"]
    F --> G["计算个股分与板块-个股关联度"]
    G --> H["应用去重与集中度约束"]
    H --> I["输出研究候选和报告"]
    I --> J["后续：构建历史标签与验证"]
```

The pipeline is intentionally fail-aware: unavailable, stale, incomplete, or fallback data is recorded in outputs rather than silently treated as fully reliable.

## Repository map

| Path | Responsibility |
|---|---|
| `theme_sector_radar/` | Core package: data access, models, scoring, agents, history, backtests and reports. |
| `scripts/` | Command-line workflows for daily runs, exports, validation, calibration and diagnostics. |
| `tests/` | Pytest coverage for data contracts, scoring, pipelines and report schemas. |
| `config/` | Public configuration examples. |
| `docs/` | Runbooks, methodology, architecture notes and research documentation. |
| `examples/` | Small sanitized examples that are safe to share. |
| `reports/`, `data_cache/` | Generated/local artifacts; ignored by Git and not part of the public source distribution. |

## Current research snapshot

The following figures are a historical research snapshot, not a promise of future performance. The validation window covered 2026-01-05 to 2026-07-08 with 120 valid validation days. The strongest evaluated experimental model was V5 Regime Router Shadow Score:

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
python run_daily.py --as-of 2026-07-08 --provider akshare
python scripts/run_daily_unified_pipeline.py --as-of 2026-07-08
```

For production-like real data runs, confirm data source availability first and review all degradation flags. See [docs/runbook_daily_pipeline.md](docs/runbook_daily_pipeline.md).

Daily outputs are written under `reports/theme_sector_radar/<date>/`, including `run_log.json` when the daily runner records execution metadata.

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
