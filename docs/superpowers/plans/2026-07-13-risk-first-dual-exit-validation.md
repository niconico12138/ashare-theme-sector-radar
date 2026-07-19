# Risk-First Dual Exit Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build paper-only, separately auditable dynamic-profit-protection and dynamic-loss-reduction candidates, then validate the existing exit factors with point-in-time and walk-forward risk gates.

**Architecture:** Keep factor generation in `factor_exit.py`; enrich each paper record with two named candidate outcomes and execution-quality flags in `paper_trading.py`. A focused validation module summarizes folds and concentration, while a CLI consumes historical paper records and writes JSON/Markdown research reports. No component may emit executable trading instructions or modify official scores.

**Tech Stack:** Python 3, standard library JSON/argparse/pathlib, pytest.

---

## File Structure

- Modify: `theme_sector_radar/timing/factor_exit.py` for a distinct `exit_v5_factor_risk_confirmed` stop-loss candidate without changing v1-v4.
- Modify: `theme_sector_radar/timing/paper_trading.py` for two paper candidate fields, data-quality annotations, and declared execution assumptions.
- Create: `theme_sector_radar/timing/exit_validation.py` for point-in-time, walk-forward, group, and concentration summaries.
- Create: `scripts/audit_timing_dual_exit_validation.py` as the report CLI.
- Modify: `scripts/run_timing_paper_trading_records.py` to declare simulation assumptions.
- Create: `tests/theme_sector_radar/test_exit_validation.py` and `tests/theme_sector_radar/test_audit_timing_dual_exit_validation.py`.
- Modify: `tests/theme_sector_radar/test_timing_factor_exit.py`, `tests/theme_sector_radar/test_timing_paper_trading.py`, and `tests/theme_sector_radar/test_run_timing_paper_trading_records.py`.

### Task 1: Add independently named paper candidates

**Files:**
- Modify: `tests/theme_sector_radar/test_timing_factor_exit.py`
- Modify: `theme_sector_radar/timing/factor_exit.py`

- [ ] **Step 1: Write failing tests**

```python
def test_factor_exit_exposes_paper_profit_and_loss_candidates():
    report = evaluate_factor_exit_triggers(bars, entry_price=10.0)
    strategies = report["strategies"]
    assert strategies["exit_v4_confirmed_factor_protect"]["paper_candidate_kind"] == "take_profit_protect"
    assert strategies["exit_v5_factor_risk_confirmed"]["paper_candidate_kind"] == "stop_loss_risk"
```

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/theme_sector_radar/test_timing_factor_exit.py -q`

Expected: failure because `paper_candidate_kind` and `exit_v5_factor_risk_confirmed` do not exist.

- [ ] **Step 3: Implement the minimum behavior**

```python
strategies["exit_v5_factor_risk_confirmed"] = _evaluate_confirmed_factor_risk(
    rows, entry_price, risk_stop_pct, close_return
)
```

Add explicit `paper_candidate_kind` to the strategy report. The v5 evaluator must require the configured loss threshold plus at least two risk confirmations; do not alter existing v1-v4 outcomes.

- [ ] **Step 4: Verify success**

Run: `python -m pytest tests/theme_sector_radar/test_timing_factor_exit.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add theme_sector_radar/timing/factor_exit.py tests/theme_sector_radar/test_timing_factor_exit.py
git commit -m "feat: add confirmed paper stop-loss candidate"
```

### Task 2: Record point-in-time and execution-quality evidence

**Files:**
- Modify: `tests/theme_sector_radar/test_timing_paper_trading.py`
- Modify: `tests/theme_sector_radar/test_run_timing_paper_trading_records.py`
- Modify: `theme_sector_radar/timing/paper_trading.py`
- Modify: `scripts/run_timing_paper_trading_records.py`

- [ ] **Step 1: Write failing record-schema tests**

```python
record = report["records"][0]
assert record["paper_exit_candidates"]["paper_take_profit_protect_candidate"]["strategy_id"] == "exit_v4_confirmed_factor_protect"
assert record["paper_exit_candidates"]["paper_stop_loss_risk_candidate"]["strategy_id"] == "exit_v5_factor_risk_confirmed"
assert record["exit_data_quality"]["bar_count"] == 3
assert record["execution_assumptions"]["fill_model"] == "next_bar_open_when_available"
assert record["paper_exit_candidates"]["paper_take_profit_protect_candidate"]["simulated_exit_price"] == 10.2
```

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/theme_sector_radar/test_timing_paper_trading.py tests/theme_sector_radar/test_run_timing_paper_trading_records.py -q`

Expected: failure because candidate, data-quality, and execution fields do not exist.

- [ ] **Step 3: Implement only auditable paper fields**

```python
"paper_exit_candidates": {
    "paper_take_profit_protect_candidate": _candidate(strategies, "exit_v4_confirmed_factor_protect"),
    "paper_stop_loss_risk_candidate": _candidate(strategies, "exit_v5_factor_risk_confirmed"),
},
"execution_assumptions": {
    "fill_model": "next_bar_open_when_available",
    "paper_research_only": True,
},
```

Add `exit_data_quality` with bar count, chronological ordering, and missing-price status. Preserve raw trigger values as observations; do not retrospectively rewrite a trigger into a fill when next-bar data is missing.
For a triggered candidate, locate the first bar strictly after `trigger_time` and use only its `open`; a missing or invalid next-bar open must not fall back to price/close. Record `simulated_exit_price`, `simulated_exit_return_pct`, and `fill_available`. A missing next bar or open must produce `fill_available=False` and exclude the observation from fill-based effectiveness metrics.

- [ ] **Step 4: Verify success**

Run: `python -m pytest tests/theme_sector_radar/test_timing_paper_trading.py tests/theme_sector_radar/test_run_timing_paper_trading_records.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add theme_sector_radar/timing/paper_trading.py scripts/run_timing_paper_trading_records.py tests/theme_sector_radar/test_timing_paper_trading.py tests/theme_sector_radar/test_run_timing_paper_trading_records.py
git commit -m "feat: record paper dual-exit evidence"
```

### Task 3: Build risk-first validation summaries

**Files:**
- Create: `tests/theme_sector_radar/test_exit_validation.py`
- Create: `theme_sector_radar/timing/exit_validation.py`

- [ ] **Step 1: Write failing tests**

```python
def test_validate_dual_exit_records_reports_walk_forward_and_concentration():
    report = validate_dual_exit_records(records, fold_count=3, tail_loss_pct=-5.0)
    assert report["candidates"]["paper_take_profit_protect_candidate"]["walk_forward"]["fold_count"] == 3
    assert report["candidates"]["paper_stop_loss_risk_candidate"]["concentration"]["top_board_share"] == 0.5
    assert report["paper_trading_only"] is True
```

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/theme_sector_radar/test_exit_validation.py -q`

Expected: failure because `exit_validation` does not exist.

- [ ] **Step 3: Implement a pure validation module**

```python
def validate_dual_exit_records(records, *, fold_count=3, tail_loss_pct=-5.0):
    return {
        "candidates": {
            candidate_id: _candidate_validation(records, candidate_id, fold_count, tail_loss_pct)
            for candidate_id in CANDIDATE_IDS
        },
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }
```

Sort by `as_of`, form contiguous chronological folds without shuffling, and summarize triggered/labeled counts, post-trigger tails, saved-vs-forward return, missed upside, MAE/MFE where available, plus date/board/version groups. Calculate top date, board, and code shares among triggered observations. Folds below the declared minimum labeled trigger count must report `insufficient_sample`, never a pass.

- [ ] **Step 4: Verify success**

Run: `python -m pytest tests/theme_sector_radar/test_exit_validation.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add theme_sector_radar/timing/exit_validation.py tests/theme_sector_radar/test_exit_validation.py
git commit -m "feat: add dual-exit risk validation summaries"
```

### Task 4: Expose a reproducible validation CLI

**Files:**
- Create: `tests/theme_sector_radar/test_audit_timing_dual_exit_validation.py`
- Create: `scripts/audit_timing_dual_exit_validation.py`

- [ ] **Step 1: Write a failing report test**

```python
result = audit_dual_exit_validation(
    records_path=records_path, output_dir=tmp_path / "out", as_of="2026-07-13", snapshot_label="unit"
)
assert result["json_path"].exists()
assert "Walk-Forward" in result["markdown_path"].read_text(encoding="utf-8")
assert result["report"]["paper_trading_only"] is True
```

- [ ] **Step 2: Verify failure**

Run: `python -m pytest tests/theme_sector_radar/test_audit_timing_dual_exit_validation.py -q`

Expected: failure because the CLI module does not exist.

- [ ] **Step 3: Implement JSON/Markdown reporting with non-promotion status**

```python
report = validate_dual_exit_records(records, fold_count=fold_count, tail_loss_pct=tail_loss_pct)
report["promotion_status"] = "paper_research_only"
json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
```

Accept `--records-path`, `--output-dir`, `--as-of`, `--snapshot-label`, `--fold-count`, `--tail-loss-pct`, and `--min-labeled-triggers`. Markdown must show data quality, baseline comparison, folds, factor attribution, and date/board/code concentration. Do not include buy/sell recommendations.

- [ ] **Step 4: Verify success**

Run: `python -m pytest tests/theme_sector_radar/test_audit_timing_dual_exit_validation.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add scripts/audit_timing_dual_exit_validation.py tests/theme_sector_radar/test_audit_timing_dual_exit_validation.py
git commit -m "feat: add dual-exit validation audit"
```

### Task 5: Run existing-factor validation before adding any new factor

**Files:**
- Create only under: `$env:TEMP\theme-sector-radar-dual-exit-paper\<run-label>\`

- [ ] **Step 1: Generate fresh 1m and 5m records for the expanded samples**

Run:
```powershell
$Reports = "<reports-root>"
$PaperRoot = Join-Path $env:TEMP "theme-sector-radar-dual-exit-paper"
$EntryBarsManifest = Join-Path $env:TEMP "theme-sector-radar-entry-bars-manifest.json"
if (-not (Test-Path -LiteralPath $EntryBarsManifest -PathType Leaf)) { throw "stage the caller-approved local entry-bars manifest first" }
$EntryBarsManifestSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $EntryBarsManifest).Hash.ToLowerInvariant()
New-Item -ItemType Directory -Force -Path $PaperRoot | Out-Null

python scripts/run_timing_paper_trading_records.py --candidate-root "$Reports\agent_bridge_mds_1m_complete_sessions_v1" --candidate-source-root "$Reports\agent_bridge_mds_1m_expanded_v2" --output-dir "$PaperRoot\dual_exit_validation_1m" --as-of 2026-07-13 --snapshot-label expanded_v2 --selection-validation-root "$Reports\selection_validation" --bar-interval 1m --trading-calendar-path "$Reports\nonstationary_entry_exit\calendar\a_share_trading_calendar_2026-07-13.json" --entry-bars-manifest $EntryBarsManifest --expected-entry-bars-manifest-sha256 $EntryBarsManifestSha
python scripts/run_timing_paper_trading_records.py --candidate-root "$Reports\agent_bridge_mds_5m_from_complete_1m_v1" --candidate-source-root "$Reports\agent_bridge_mds_1m_expanded_v2" --output-dir "$PaperRoot\dual_exit_validation_5m" --as-of 2026-07-13 --snapshot-label expanded_v2 --selection-validation-root "$Reports\selection_validation" --bar-interval 5m --trading-calendar-path "$Reports\nonstationary_entry_exit\calendar\a_share_trading_calendar_2026-07-13.json" --entry-bars-manifest $EntryBarsManifest --expected-entry-bars-manifest-sha256 $EntryBarsManifestSha
```

- [ ] **Step 2: Audit 3-fold and 5-fold results for both timeframes**

Run:
```powershell
python scripts/audit_timing_dual_exit_validation.py --records-path "$PaperRoot\dual_exit_validation_1m\timing_paper_trading_records_2026-07-13_expanded_v2.json" --output-dir "$PaperRoot\audit_1m" --as-of 2026-07-13 --snapshot-label expanded_v2_f3 --fold-count 3
python scripts/audit_timing_dual_exit_validation.py --records-path "$PaperRoot\dual_exit_validation_5m\timing_paper_trading_records_2026-07-13_expanded_v2.json" --output-dir "$PaperRoot\audit_5m" --as-of 2026-07-13 --snapshot-label expanded_v2_f5 --fold-count 5
```

- [ ] **Step 3: Verify code and guardrails**

Run: `python -m pytest tests/theme_sector_radar/test_timing_factor_exit.py tests/theme_sector_radar/test_timing_paper_trading.py tests/theme_sector_radar/test_run_timing_paper_trading_records.py tests/theme_sector_radar/test_exit_validation.py tests/theme_sector_radar/test_audit_timing_dual_exit_validation.py tests/theme_sector_radar/test_audit_timing_factor_exit.py -q`

Run: `git diff --check`

Run: `git diff -U0 -- theme_sector_radar scripts tests docs | Select-String -Pattern '^\+.*(final_score|v2_score|selection_score|selection_score_adjusted)'`

Expected: tests pass and both guardrail commands have no output.

- [ ] **Step 4: Select the next research target strictly from evidence**

Choose sector/relative-strength factors only if profit protection has concentrated missed-upside or repair outcomes. Choose market-regime/funding-deterioration factors only if loss reduction fails to reduce post-trigger tails. If a candidate lacks minimum labeled triggers or has concentrated improvement, report `insufficient_evidence` and expand history instead of adding factors.

- [ ] **Step 5: Commit plan metadata only**

```powershell
git add docs/superpowers/plans/2026-07-13-risk-first-dual-exit-validation.md
git commit -m "docs: plan dual-exit validation"
```

## Plan Self-Review

- Spec coverage: Tasks 1-2 create separate candidates and point-in-time evidence; Task 3 enforces walk-forward, group, and concentration checks; Task 4 makes validation reproducible; Task 5 runs existing factors before any new factor is considered.
- Placeholder scan: all modules, public functions, test targets, CLI arguments, and promotion constraints are named.
- Type consistency: all record consumers use `paper_exit_candidates`; candidate ids remain `paper_take_profit_protect_candidate` and `paper_stop_loss_risk_candidate`; reports stay paper-only and preserve official scores.
