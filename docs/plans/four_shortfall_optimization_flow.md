# Four Shortfall Optimization Flow

## Goal

Turn the current sector-radar stock-candidate system from a runnable research pipeline into a more reliable, explainable, and eventually open-source-ready research platform.

## Flow 1: Data Chain Stability

Objective: make every daily run able to answer whether inputs are fresh, complete, and reproducible.

Steps:

1. Keep `run_daily.py --preflight-only` as the first operator gate.
2. Extend preflight from service availability to data freshness:
   - StockDB reachable.
   - `market_data_service /health` reachable.
   - latest trading date available.
   - required upstream reports exist for `as_of`.
3. Write run-level diagnostics:
   - `reports/daily_run_report_DATE.*`
   - `reports/artifact_manifest/DATE/run_manifest.json`
4. Add hard gates:
   - step failure exit code 1.
   - dependency skip exit code 2.
   - stale/missing artifact exit code 3.
5. Keep all failures actionable with `detail` and `action`.

Acceptance:

- A user can run preflight without launching long jobs.
- A failed daily run says which dependency or artifact failed.
- Existing report files cannot silently masquerade as fresh output.

## Flow 2: Candidate Pool Quality

Objective: explain candidate-pool size and quality before tuning scoring formulas.

Steps:

1. Treat `reports/agent_bridge/DATE/top30_candidates.json` as the source of truth for pool quality.
2. Analyze:
   - final candidate count.
   - trend/burst/both source distribution.
   - board concentration.
   - duplicate and cross-board exposure.
   - selection funnel losses.
   - loss severity and dominant reason.
3. Label root cause when final count is below target:
   - strict main-board rule.
   - ST filter.
   - invalid code or empty name.
   - too few raw candidates.
   - too much deduplication.
   - board concentration.
4. Generate both JSON and Markdown diagnostics:
   - `candidate_pool_quality.json`
   - `candidate_pool_quality.md`
5. Surface summary in daily AI report.

Acceptance:

- When candidate count is below 30, the report explains why.
- The system does not weaken main-board/ST filters silently.
- The user can distinguish data coverage problems from intentional policy constraints.

## Flow 3: Scoring Empirical Calibration

Objective: validate whether board score, quant score, Agent score, risk score, and resonance score actually improve future performance.

Current implementation status:

- Added an offline evaluator: `scripts/evaluate_scoring_calibration.py`.
- It reads `reports/agent_bridge/DATE/top30_candidates.json` plus an external `forward_returns.json`.
- It reports coverage, score buckets, average forward return, hit rate, and sample count.
- It is automatically triggered by `scripts/run_daily_bridge_report.py` when forward-return data exists.
- It intentionally does not change weights yet.

Steps:

1. Build a dated evaluation dataset from generated candidate pools.
2. Evaluate future 1/3/5-day returns and drawdown when data exists.
3. Compare score layers:
   - board-only.
   - quant-only.
   - Agent-only.
   - board + quant.
   - board + quant + Agent.
   - with and without resonance bonus.
4. Produce calibration reports:
   - hit rate by score bucket.
   - average forward return by score bucket.
   - drawdown/risk by risk level.
   - lift versus baseline.
5. Adjust weights only after evidence is available.

Acceptance:

- Weight changes require a before/after evaluation report.
- No LLM black-box scoring becomes the core ranking source.
- Reports can show whether a factor adds signal or just decoration.

Next calibration gaps:

1. Add a forward-return builder from validated StockDB daily bars.
2. Add drawdown and risk-level grouping.
3. Add cross-date aggregation so one thin daily sample does not drive formula changes.
4. Only then tune weights or resonance bonuses.

## Flow 4: Open-Source Readiness

Objective: make the project safe and understandable for GitHub collaboration after core shortfalls are reduced.

Steps:

1. Separate source code, sample data, generated reports, and local-only runtime files.
2. Add or tighten `.gitignore` for generated artifacts.
3. Remove secrets, local absolute paths, and machine-specific assumptions from public paths.
4. Provide demo mode:
   - fixture input data.
   - reproducible command.
   - sample report output.
5. Add project docs:
   - README.
   - architecture diagram text.
   - runbook.
   - disclaimer.
   - contribution guide.

Acceptance:

- A new user can run a demo without StockDB.
- The public repo does not expose personal paths or credentials.
- The project is framed as research tooling, not investment advice.

## Execution Order

1. Candidate Pool Quality.
2. Data Chain Stability extensions.
3. Scoring Empirical Calibration.
4. Open-Source Readiness.

Candidate quality comes first because bad input pools make downstream Agent analysis and scoring calibration misleading.
