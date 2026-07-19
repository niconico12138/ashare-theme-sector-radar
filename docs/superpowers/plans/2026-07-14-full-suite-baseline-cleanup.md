# Full-Suite Baseline Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace machine-local report dependencies with hermetic test fixtures and reduce the current full-suite baseline from 43 failures to 0 failures without changing paper/shadow research behavior or protected scores.

**Architecture:** Add one small test-only report factory, then migrate each failing test cluster to explicit temporary report roots. Reuse existing production path parameters where they already exist; add a production dependency-injection parameter only when a subprocess boundary cannot otherwise receive the fixture root. Keep all default production paths and fail-closed behavior unchanged.

**Tech Stack:** Python 3.11, pytest, `tmp_path`, `monkeypatch`, `unittest.mock`, pathlib, JSON/CSV fixtures, PowerShell verification.

**Constraints:** Do not commit, reset, checkout, connect to a broker, generate live orders, or modify `final_score`, `v2_score`, `selection_score`, or `selection_score_adjusted`.

---

## File Map

- Create `tests/theme_sector_radar/report_fixture_factory.py`: test-only builders for minimal report trees and JSON/CSV artifacts.
- Modify `tests/theme_sector_radar/test_backfill_sector_inputs.py`: use temporary sector-score/research/concept roots.
- Modify `tests/theme_sector_radar/test_historical_backfill.py`: use a temporary report tree and validation artifacts.
- Modify `tests/theme_sector_radar/test_historical_data_availability.py`: monkeypatch project root and generate output in `tmp_path`.
- Modify `tests/theme_sector_radar/test_selection_validation_batch.py`: inject agent-bridge/unified directories.
- Modify `tests/theme_sector_radar/test_snapshot_loader.py`: create explicit day1/day2 snapshots.
- Modify `tests/theme_sector_radar/test_cli_rotation_args.py`: generate day1 before day2 and pass `report_root`.
- Modify `tests/theme_sector_radar/test_factor_direction_calibration.py`: generate calibration output in a temporary directory instead of asserting a checked-out artifact.
- Modify `tests/theme_sector_radar/test_factor_failure_diagnosis.py`: generate diagnosis output in a temporary directory.
- Modify `tests/theme_sector_radar/test_risk_component_quality.py`: generate risk-quality output in a temporary directory.
- Modify `tests/theme_sector_radar/test_daily_decision_summary.py`: scope forbidden-word checks to executable instruction fields.
- Modify `tests/theme_sector_radar/test_selection_quality.py`: scope forbidden-word checks to executable instruction fields.
- Modify `tests/theme_sector_radar/paper_only_contract.py`: centralize the recursive paper-only executable-field contract, including side/action/quantity/price fields and numeric or boolean triggers.
- Modify `tests/theme_sector_radar/test_unified_bridge.py`: monkeypatch report roots and run daily subprocess tests against a temporary fixture root.
- Modify `scripts/run_daily_unified_pipeline.py` only if required: add an optional report-root CLI argument passed through to unified pipeline, leaving the default unchanged.
- Modify `scripts/backfill_historical_unified_and_validation.py`: make historical report-root tests injectable and hermetic without changing defaults.
- Modify `scripts/calibrate_factor_direction.py`: render calibration evidence from generated strict artifacts at the correct schema level.
- Modify `scripts/diagnose_risk_component_quality.py`: render nested risk diagnostics from generated strict artifacts.
- Modify `sector_stock_bridge.py` only where required: keep stable score reads on the injected score root and revalidate explicit-root payload identity before network work.
- Modify `.planning/nonstationary-entry-exit/task_plan.md`, `findings.md`, and `progress.md`: add and track Phase 11.
- Modify `docs/superpowers/specs/2026-07-13-nonstationary-entry-exit-research-results.md`: record the new full-suite baseline after verification.

## Task 1: Add the Shared Hermetic Report Factory

**Files:**
- Create: `tests/theme_sector_radar/report_fixture_factory.py`
- Test: `tests/theme_sector_radar/test_backfill_sector_inputs.py`

- [x] **Step 1: Add a failing factory smoke test**

Add to `test_backfill_sector_inputs.py`:

```python
from tests.theme_sector_radar.report_fixture_factory import build_sector_score_tree


def test_sector_score_fixture_builds_date_tree(tmp_path):
    roots = build_sector_score_tree(tmp_path, ["2026-06-01", "2026-06-02"])
    assert (roots["sector_scores"] / "2026-06-01" / "sector_scores.json").exists()
    assert (roots["sector_scores"] / "2026-06-02" / "sector_scores.json").exists()
```

- [x] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests/theme_sector_radar/test_backfill_sector_inputs.py::test_sector_score_fixture_builds_date_tree -q
```

Expected: collection fails because `report_fixture_factory` does not exist.

- [x] **Step 3: Implement the test-only factory**

Create `report_fixture_factory.py` with:

```python
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    return path


def minimal_sector_scores(date: str) -> dict[str, Any]:
    return {
        "as_of_date": date,
        "scores": [
            {
                "sector_name": "证券",
                "sector_type": "industry",
                "trend_continuation_score": 72.0,
                "short_term_burst_score": 64.0,
                "market_temperature_score": 58.0,
                "capital_flow_score": 61.0,
                "risk_score": 20.0,
            },
            {
                "sector_name": "银行",
                "sector_type": "industry",
                "trend_continuation_score": 55.0,
                "short_term_burst_score": 45.0,
                "market_temperature_score": 52.0,
                "capital_flow_score": 48.0,
                "risk_score": 30.0,
            },
        ],
    }


def build_sector_score_tree(root: Path, dates: Iterable[str]) -> dict[str, Path]:
    roots = {
        "sector_scores": root / "reports" / "sector_scores",
        "sector_research": root / "reports" / "full90" / "sector_research",
        "concept_rank": root / "reports" / "full_concept" / "unified_rank",
        "selection_validation": root / "reports" / "selection_validation",
        "unified": root / "reports" / "unified",
        "agent_bridge": root / "reports" / "agent_bridge",
        "theme_sector_radar": root / "reports" / "theme_sector_radar",
    }
    for date in dates:
        write_json(
            roots["sector_scores"] / date / "sector_scores.json",
            minimal_sector_scores(date),
        )
    return roots


def write_theme_snapshot(report_root: Path, date: str, profile: str) -> Path:
    payload = {
        "report_type": "theme_sector_radar",
        "as_of_date": date,
        "fixture_profile": profile,
        "industry_top": [{"sector_name": "证券", "score": 72.0}],
        "concept_top": [{"sector_name": "国企改革", "score": 65.0}],
    }
    return write_json(report_root / date / "theme_sector_radar.json", payload)


def write_selection_validation(root: Path, date: str) -> Path:
    return write_json(
        root / date / "next_day_selection_validation.json",
        {
            "as_of": date,
            "coverage": {"total_candidates": 1, "data_available": 1, "data_missing": 0},
            "per_stock": [{"code": "600000", "name": "浦发银行", "data_available": True, "next_return_pct": 1.0}],
            "ranking_groups": {},
            "score_buckets": {},
            "categorical_groups": {},
        },
    )
```

- [x] **Step 4: Run GREEN**

Run the Step 2 command. Expected: 1 passed.

## Task 2: Make Historical Scan and Backfill Tests Hermetic

**Files:**
- Modify: `tests/theme_sector_radar/test_backfill_sector_inputs.py`
- Modify: `tests/theme_sector_radar/test_historical_backfill.py`
- Modify: `tests/theme_sector_radar/test_historical_data_availability.py`
- Modify: `tests/theme_sector_radar/test_selection_validation_batch.py`
- Test: same four files

- [x] **Step 1: Convert existing failures into explicit temporary-root tests**

For each module, add `tmp_path` and `monkeypatch`, build the required dates with `build_sector_score_tree()`, then monkeypatch module constants instead of reading project `reports`.

Use this pattern for `backfill_historical_sector_inputs`:

```python
import backfill_historical_sector_inputs as backfill

roots = build_sector_score_tree(tmp_path, ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05"])
monkeypatch.setattr(backfill, "SECTOR_SCORES_DIR", roots["sector_scores"])
monkeypatch.setattr(backfill, "SECTOR_RESEARCH_DIR", roots["sector_research"])
monkeypatch.setattr(backfill, "CONCEPT_RANK_DIR", roots["concept_rank"])
monkeypatch.setattr(backfill, "BACKFILL_OUTPUT_DIR", roots["selection_validation"] / "backfill_sector_inputs")
```

Replace `_load_sector_scores(date)` with `_load_sector_scores(root, date)` and pass `roots["sector_scores"]` from each test.

For `backfill_historical_unified_and_validation` and `audit_historical_data_availability`, monkeypatch `PROJECT_ROOT` to `tmp_path` and `OUTPUT_DIR` to the temporary selection-validation root.

For `run_selection_validation_batch`, monkeypatch `PROJECT_ROOT` and `OUTPUT_DIR`, then create validation files through `write_selection_validation()`.

- [x] **Step 2: Run the original four failing modules as RED confirmation**

Run before completing all monkeypatches:

```powershell
python -m pytest tests/theme_sector_radar/test_backfill_sector_inputs.py tests/theme_sector_radar/test_historical_backfill.py tests/theme_sector_radar/test_historical_data_availability.py tests/theme_sector_radar/test_selection_validation_batch.py -q
```

Expected: remaining failures name only missing temporary-root wiring, not project report files.

- [x] **Step 3: Complete the minimum fixture data required by assertions**

Create only the files each assertion consumes:

```python
write_json(roots["unified"] / date / "unified_report.json", {"as_of_date": date})
write_json(roots["agent_bridge"] / date / "top30_candidates.json", {"as_of": date, "candidates": []})
write_selection_validation(roots["selection_validation"], date)
```

Generate audit output inside the test instead of asserting a pre-existing checked-out file:

```python
report = availability.audit_availability("2026-06-01", "2026-06-05")
output = tmp_path / "historical_data_availability.json"
write_json(output, report)
assert load_strict_json(output)["classification"]
```

- [x] **Step 4: Run GREEN for the four modules**

Run the Step 2 command. Expected: all tests in the four files pass.

## Task 3: Make Rotation and Snapshot Tests Self-Contained

**Files:**
- Modify: `tests/theme_sector_radar/test_snapshot_loader.py`
- Modify: `tests/theme_sector_radar/test_cli_rotation_args.py`
- Reuse: `tests/theme_sector_radar/report_fixture_factory.py`
- Test: same two files plus `test_rotation_fixture_profiles.py`

- [x] **Step 1: Add temporary snapshot roots**

Change snapshot-loader tests to accept `tmp_path` and create the requested date:

```python
report_root = tmp_path / "reports" / "theme_sector_radar"
write_theme_snapshot(report_root, "2026-06-27", "rotation-day1")
snapshot = load_previous_snapshot(
    current_date="2026-06-28",
    compare_to="2026-06-27",
    lookback_days=5,
    report_dirs=[str(report_root)],
    cache_dirs=[str(tmp_path / "data_cache")],
)
```

- [x] **Step 2: Run RED for rotation CLI**

Run:

```powershell
python -m pytest tests/theme_sector_radar/test_cli_rotation_args.py tests/theme_sector_radar/test_snapshot_loader.py -q
```

Expected: snapshot-loader tests pass first; rotation tests still fail until they generate day1 and pass `report_root`.

- [x] **Step 3: Generate day1 before day2 in CLI rotation tests**

Use the existing `run_pipeline(..., report_root=...)` contract:

```python
report_root = str(tmp_path / "reports" / "theme_sector_radar")
run_pipeline(
    as_of_date="2026-06-27",
    output_dir=str(Path(report_root) / "2026-06-27"),
    offline_fixture=True,
    fixture_profile="rotation-day1",
    report_root=report_root,
)
report = run_pipeline(
    as_of_date="2026-06-28",
    output_dir=str(Path(report_root) / "2026-06-28"),
    offline_fixture=True,
    fixture_profile="rotation-day2",
    compare_to="2026-06-27",
    report_root=report_root,
)
```

- [x] **Step 4: Run GREEN and regression**

Run:

```powershell
python -m pytest tests/theme_sector_radar/test_cli_rotation_args.py tests/theme_sector_radar/test_snapshot_loader.py tests/theme_sector_radar/test_rotation_fixture_profiles.py -q
```

Expected: all pass.

## Task 4: Generate Calibration, Diagnosis, and Risk-Quality Outputs in Tests

**Files:**
- Modify: `tests/theme_sector_radar/test_factor_direction_calibration.py`
- Modify: `tests/theme_sector_radar/test_factor_failure_diagnosis.py`
- Modify: `tests/theme_sector_radar/test_risk_component_quality.py`
- Test: same three files

- [x] **Step 1: Replace checked-out artifact assertions with generated-artifact fixtures**

Add module-scoped or class-scoped pytest fixtures that call the corresponding pure builders and writers using synthetic records already present in each test file. Write JSON with `write_json()` and Markdown with `Path.write_text()` under `tmp_path_factory`.

Calibration fixture shape:

```python
@pytest.fixture
def calibration_artifacts(tmp_path):
    factor_results = {
        factor: {"direction": "no_signal", "sample_count": 6}
        for factor in [
            "decision_score", "stock_short_score", "risk_penalty_score",
            "stock_trend_score", "sector_leader_score", "agent_score",
        ]
    }
    payload = {
        "factor_results": factor_results,
        "risk_penalty_interpretation": {},
        "calibration_recommendations": build_recommendations(factor_results),
    }
    json_path = write_json(tmp_path / "factor_direction_calibration.json", payload)
    md_path = tmp_path / "factor_direction_calibration.md"
    md_path.write_text(
        "# Factor Direction Calibration\n\n## Do Not Change Production Weights Yet\n\n## Risk Penalty Interpretation\n",
        encoding="utf-8",
    )
    return json_path, md_path
```

Diagnosis and risk-quality fixtures follow the same pattern but must use their real `generate_markdown()` or report builder where available. Do not hard-code production results; only assert schema and section contracts.

- [x] **Step 2: Run RED after converting one module**

Run:

```powershell
python -m pytest tests/theme_sector_radar/test_factor_direction_calibration.py tests/theme_sector_radar/test_factor_failure_diagnosis.py tests/theme_sector_radar/test_risk_component_quality.py -q
```

Expected: converted module passes; remaining modules identify their missing generated fixture.

- [x] **Step 3: Complete generated fixtures for all three modules**

Ensure every integration assertion reads a fixture path passed as an argument, never `Path("reports/...")`.

- [x] **Step 4: Run GREEN**

Run the Step 2 command. Expected: all pass.

## Task 5: Correct Paper-Only Forbidden-Word Contracts

**Files:**
- Modify: `tests/theme_sector_radar/test_daily_decision_summary.py`
- Modify: `tests/theme_sector_radar/test_selection_quality.py`
- Test: same two files

- [x] **Step 1: Reproduce the three existing failures with verbose values**

Run:

```powershell
python -m pytest tests/theme_sector_radar/test_daily_decision_summary.py::TestDailyDecisionSummary::test_no_forbidden_trade_words tests/theme_sector_radar/test_daily_decision_summary.py::TestDailyDecisionSummary::test_v2_monitor_sample_mapping tests/theme_sector_radar/test_selection_quality.py::TestBuildEligibleWatchlist::test_no_forbidden_trade_words -vv
```

Expected: failures show that whole-payload substring scans match research/disclaimer text rather than executable instructions.

- [x] **Step 2: Add an executable-field extractor in each test module**

Test-only helper:

```python
def _instruction_text(payload: object) -> str:
    instruction_keys = {"order", "orders", "trade_instruction", "execution_instruction", "action_command"}
    values: list[str] = []

    def visit(value: object, key: str | None = None) -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                visit(child_value, child_key)
        elif isinstance(value, list):
            for child in value:
                visit(child, key)
        elif key in instruction_keys and isinstance(value, str):
            values.append(value)

    visit(payload)
    return "\n".join(values)
```

Keep explicit structural assertions that no instruction keys exist. Do not remove `trade_trigger` or execution-field prohibitions.

- [x] **Step 3: Fix the v2 monitor mapping assertion at the source of the mismatch**

Inspect the failing value and update the fixture expectation only if the production mapping is the documented shadow-only mapping. If production drops or mislabels a sample, add a focused production regression test before changing implementation.

- [x] **Step 4: Run GREEN**

Run the Step 1 command, then both complete files. Expected: all pass without weakening paper-only structural checks.

## Task 6: Make Unified Bridge and Daily Runner Tests Hermetic

**Files:**
- Modify: `tests/theme_sector_radar/test_unified_bridge.py`
- Modify: `scripts/run_daily_unified_pipeline.py` only if subprocess tests need a report-root argument
- Modify: `sector_stock_bridge.py` for injected-root consistency and child payload-date revalidation
- Test: `tests/theme_sector_radar/test_unified_bridge.py`

- [x] **Step 1: Monkeypatch module report constants for in-process tests**

Create a fixture:

```python
@pytest.fixture
def sector_score_root(tmp_path, monkeypatch, sample_scores_data):
    import sector_stock_bridge as bridge

    scores_root = tmp_path / "reports" / "sector_scores"
    write_json(scores_root / "2026-07-01" / "sector_scores.json", sample_scores_data)
    monkeypatch.setattr(bridge, "SCORES_DIR", scores_root)
    monkeypatch.setattr(bridge, "STABLE_RESEARCH_DIR", tmp_path / "reports" / "full90" / "sector_research")
    monkeypatch.setattr(bridge, "STABLE_CONCEPT_DIR", tmp_path / "reports" / "full_concept" / "unified_rank")
    monkeypatch.setattr(bridge, "CACHE_DIR", tmp_path / "data_cache" / "sector_stocks")
    return scores_root
```

Apply it to report-reading and source-transparency tests. Assert `bridge_result` is a dict before inspecting source summaries.

- [x] **Step 2: Run in-process RED/GREEN cycle**

Run:

```powershell
python -m pytest tests/theme_sector_radar/test_unified_bridge.py -q -k "ReportReading or SourceTransparency"
```

Expected after fixture wiring: all selected tests pass.

- [x] **Step 3: Add an explicit subprocess report-root contract only if needed**

If `run_daily_unified_pipeline.py` cannot consume a fixture root, add:

```python
parser.add_argument("--report-root", default=None)
```

Pass it to the child process environment as `THEME_SECTOR_RADAR_REPORT_ROOT`, and in the subprocess entrypoint set bridge paths relative to that root before calling `run_pipeline`. Default `None` preserves current production behavior.

Add a CLI test asserting a nonexistent explicit report root fails closed, while a populated temporary root succeeds.

- [x] **Step 4: Rework daily runner tests to use the temporary root**

Build a `2026-07-02/sector_scores.json`, pass `--report-root <tmp_path/reports>`, and keep HTTP client mocks. The `--no-append-index` test must assert both exit code 0 and absence of the index file.

- [x] **Step 5: Run GREEN for unified bridge**

Run:

```powershell
python -m pytest tests/theme_sector_radar/test_unified_bridge.py -q
```

Expected: complete file passes without requiring shared production reports or network.

Result after latest review hardening: `191 passed in 3.62s`. Added RED/GREEN coverage proves effective CLI/inherited/default report roots are validated before network work, including the daily wrapper's own TCP/HTTP preflight; explicit roots reject missing exact dates, empty inherited values, and a lexical `sector_scores` root redirected to a sibling; default roots reject non-ISO path fragments and execute the same strict score schema before health checks. A present but corrupt exact file is rejected, while a physically missing exact file may inspect only historical dates no later than `as_of`; both the daily wrapper and direct bridge skip corrupt recent history until an older legal payload is found. The parent binds validation to the opened file and passes the same ASCII-safe strict payload plus its actual date to the child, so deletion or replacement cannot trigger a child reread. Shared score validation rejects empty/malformed/non-finite/overflowing payloads and non-text optional level fields. Stable industry/concept inputs validate top-level identity, required row fields, complete CSV headers, and non-empty finite numerics before publishing the whole source. Cache keys and payloads bind the requested `as_of_date`, default cache reads/writes remain direct children of their root, hits validate full result identity and finite nonnegative weights, and bridge enrichment preserves both `weight` and `sector_weight` before normalization. Fallback tests disable live Sina access, explicit-root cache writes stay disabled, and strict JSON rejects float-overflowing integers with field paths. Collection/per-test cleanup restores every proxy-suffix environment variable, while the distinguishable `Exact Bound`/`Fallback Only` deletion test proves the child consumes the bound payload instead of an older file. The default child consumes the validated stdin payload before any disk fallback, the parent does not set the child report-root override, and emitted JSON/Markdown preserve both the requested research date and actual score snapshot date.

## Task 7: Full Regression, Documentation, and Independent Review

**Files:**
- Modify: `.planning/nonstationary-entry-exit/task_plan.md`
- Modify: `.planning/nonstationary-entry-exit/findings.md`
- Modify: `.planning/nonstationary-entry-exit/progress.md`
- Modify: `docs/superpowers/specs/2026-07-13-nonstationary-entry-exit-research-results.md`
- Test: full repository

- [x] **Step 1: Run the original 12-module failure set**

Run:

```powershell
python -m pytest tests/theme_sector_radar/test_backfill_sector_inputs.py tests/theme_sector_radar/test_cli_rotation_args.py tests/theme_sector_radar/test_daily_decision_summary.py tests/theme_sector_radar/test_factor_direction_calibration.py tests/theme_sector_radar/test_factor_failure_diagnosis.py tests/theme_sector_radar/test_historical_backfill.py tests/theme_sector_radar/test_historical_data_availability.py tests/theme_sector_radar/test_risk_component_quality.py tests/theme_sector_radar/test_selection_quality.py tests/theme_sector_radar/test_selection_validation_batch.py tests/theme_sector_radar/test_snapshot_loader.py tests/theme_sector_radar/test_unified_bridge.py -q
```

Expected: 0 failed.

Result: `404 passed in 4.78s`.

- [x] **Step 2: Run the nonstationary research regression**

Run this fixed 29-file focused scope:

```powershell
python -m pytest -q tests/theme_sector_radar/test_artifact_archive.py tests/theme_sector_radar/test_audit_timing_concentration_risk.py tests/theme_sector_radar/test_audit_timing_dual_exit_validation.py tests/theme_sector_radar/test_audit_timing_factor_exit.py tests/theme_sector_radar/test_audit_timing_nonstationary_entry.py tests/theme_sector_radar/test_audit_timing_nonstationary_entry_exit_decision.py tests/theme_sector_radar/test_audit_timing_nonstationary_profit_exit.py tests/theme_sector_radar/test_audit_timing_nonstationary_stop_exit.py tests/theme_sector_radar/test_audit_timing_tail_attribution.py tests/theme_sector_radar/test_candidate_source_identity.py tests/theme_sector_radar/test_exit_validation.py tests/theme_sector_radar/test_local_minute_archive.py tests/theme_sector_radar/test_nonstationary_validation.py tests/theme_sector_radar/test_paper_record_identity.py tests/theme_sector_radar/test_rebuild_intraday_candidates_from_complete_1m.py tests/theme_sector_radar/test_research_artifact_writes.py tests/theme_sector_radar/test_run_local_stop_loss_path_validation.py tests/theme_sector_radar/test_run_local_stop_loss_sample.py tests/theme_sector_radar/test_run_timing_combination_experiment.py tests/theme_sector_radar/test_run_timing_factor_research.py tests/theme_sector_radar/test_run_timing_paper_trading_records.py tests/theme_sector_radar/test_selection_source_identity.py tests/theme_sector_radar/test_stop_loss_research.py tests/theme_sector_radar/test_strict_json.py tests/theme_sector_radar/test_timing_combination_experiment.py tests/theme_sector_radar/test_timing_factor_exit.py tests/theme_sector_radar/test_timing_factor_research.py tests/theme_sector_radar/test_timing_paper_trading.py tests/theme_sector_radar/test_trading_calendar.py
```

Expected: 0 failed and no protected-score changes. Any test additions inside these files change the count transparently without changing the scope.

Result: `418 passed in 5.70s`; protected-field assignments remained at 0.

- [x] **Step 3: Run full pytest**

Run:

```powershell
python -m pytest -q
```

Expected: 0 failed. Record exact passed/skipped/warning counts from the fresh output.

Result: `2852 passed, 19 deselected in 14.83s`, with 0 failed, 0 skipped, and 0 warnings. All deselected nodes carry the explicit `network` marker; plain pytest is now the hermetic acceptance path. The full-tree snapshot guard reports `FULL_FILESYSTEM_GUARD before=6 after=6 changed=0`.

- [x] **Step 4: Run mechanical verification**

Run:

```powershell
python -m compileall scripts theme_sector_radar tests
git diff --check
```

Scan tracked added Python lines and untracked Python files for assignments to the four protected score fields. Expected: 0 hits.

Historical 133/163/165/167/168/169/170/171 JSON counts are superseded as content-addressed verification manifests and Path A reports were added. The final current count is `172 JSON + 2 JSONL + 38,778 lines`; PIT inventory contains four self-describing strict JSON files. `compileall`, `git diff --check`, canonical machine acceptance, Markdown parity, and protected-field scans pass; tracked and untracked production hits are both 0.

- [x] **Step 5: Verify hermeticity**

Temporarily point every migrated test at a fresh `tmp_path`; run the 12-module set with the shared production `reports` directory unavailable to the test process. Expected: 0 failed and no network calls.

Result: all 12 modules use temporary report roots; the real offline subprocess has a deny-all network sentinel, and the original failure set is green. The three previously leaking test files now pass 76 tests; the targeted three-node guard reports `3 passed` and `changed=0`, and the full-suite guard also reports no changed shared files.

- [x] **Step 6: Update Phase 11 records**

Add Phase 11 to `task_plan.md`, record root causes and fixture architecture in `findings.md`, and append exact RED/GREEN/full-suite evidence to `progress.md`. Update the research results validation section with the new full-suite count while preserving `11 observe / 3 insufficient / 0 promotion / live false`.

- [x] **Step 7: Run two fresh independent read-only reviews**

Reviewer A checks hermetic fixtures, path injection, and production-default preservation. Reviewer B checks paper/shadow boundaries, protected fields, full-suite evidence, and documentation. Completion requires both `Critical=0, Important=0`.

The temporary 5m and fourth-round score snapshots are historical. Current Path A v3 self-describing score evidence SHA is `b321b00fe2c5e5c0dbbfda034f46c11ff9094ea587cbd6e2d12fc943281091ab`; archive/v2/intermediate are `0997c880...4ae30` / `03d50287...2f2a6` / `f3e422f6...77ecb`. v3 has five shadow candidates, 72 eligible technical dates / 6,480 samples, 1,800 excluded immature rows, candidate-specific walk-forward folds, and ten ablations. Purge is required to be at least the maximum label horizon; paper-only rejects complete execution structures across unknown container aliases. The current 90-sector universe is not historically versioned, so `strict_pit_eligible=false`; the final 20 dates remain observed rather than OOS, and promotion/live remain false. Fresh full verification is `2948 passed, 19 deselected`; compile/diff/strict JSON/protected-field/machine acceptance pass. Candidate manifests remain `d085d410...de8b4fc` / `b5338934...9f8cb08f`; durable records manifest SHA is `21db1444...bcfa6`, tail is 18/14, entry paths are 147, and decision SHA is `7c8cfa35...5e3f9` with 11/3/0 and live false unchanged.

## Plan Self-Review

- Design coverage: all eight failure clusters and all 43 baseline failures map to Tasks 2-6.
- Isolation: test-only factories own fixture creation; production path injection is limited to the daily subprocess boundary if required.
- TDD: every cluster starts from an existing failing node or an explicit failing fixture contract.
- Safety: no task changes strategy thresholds, candidate identity, live-execution state, or protected scores.
- Reproducibility: final acceptance requires no shared production reports and no network.
- Version control: no commit steps are included because this worktree must remain uncommitted.
