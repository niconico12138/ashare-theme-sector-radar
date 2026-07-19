# Nonstationary Entry Exit Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement and run a recent-dominant, regime-confirmed, long-history-veto research framework for entry factors, v31/v32, dynamic profit protection, and dynamic stop loss.

**Architecture:** A pure nonstationary validation module produces 60/120-day, observed evaluation tail, regime, perturbation, ablation, and concentration evidence. The internal `holdout` key is retained only for schema compatibility and does not imply blind or out-of-sample status. Existing timing records feed entry and profit audits; local minute archives feed trigger-path stop-loss labels. A report CLI combines evidence into paper-only champion/challenger decisions.

**Tech Stack:** Python 3 standard library, pytest, existing timing research loaders.

---

### Task 1: Multi-Horizon Validation Core

**Files:**
- Create: `theme_sector_radar/timing/nonstationary_validation.py`
- Create: `tests/theme_sector_radar/test_nonstationary_validation.py`

- [ ] Write a failing test for chronological 60/120 windows and a final 20-day `observed_evaluation_tail` (internal schema key: `holdout`).

```python
report = build_nonstationary_windows(records, as_of="2026-07-10", holdout_days=20)
assert report["recent_60"]["date_count"] == 60
assert report["recent_120"]["date_count"] == 120
assert report["holdout"]["date_count"] == 20
assert set(report["recent_60"]["dates"]).isdisjoint(report["holdout"]["dates"])
```

- [ ] Run `python -m pytest tests/theme_sector_radar/test_nonstationary_validation.py -q`; expect import failure.
- [ ] Implement chronological unique-date splitting, regime summaries, concentration, and long-history veto fields. Missing windows return `insufficient_sample`, never pass.
- [ ] Re-run the focused test; expect PASS.

### Task 2: Entry Factor and v31/v32 Audit

**Files:**
- Create: `scripts/audit_timing_nonstationary_entry.py`
- Create: `tests/theme_sector_radar/test_audit_timing_nonstationary_entry.py`
- Read: `theme_sector_radar/timing/combination_experiment.py`

- [ ] Write a failing test that audits v31/v32 by recent windows, the observed evaluation tail, condition ablation, threshold perturbation, regime, and date/board/code concentration.
- [ ] Run the focused test; expect import failure.
- [ ] Implement `audit_nonstationary_entry(...)` using existing strategy conditions without modifying official scores. Perturb numeric thresholds by fixed ±10%; remove one condition at a time; compare against the simpler existing baseline.
- [ ] Generate JSON/Markdown and classify each version as `champion`, `challenger`, `observe`, or `insufficient_evidence`.
- [ ] Run focused and existing overfit tests; expect PASS.

### Task 3: Dynamic Profit Multi-Horizon Audit

**Files:**
- Create: `scripts/audit_timing_nonstationary_profit_exit.py`
- Create: `tests/theme_sector_radar/test_audit_timing_nonstationary_profit_exit.py`
- Reuse: `theme_sector_radar/timing/exit_validation.py`

- [ ] Write a failing test comparing fixed exit and exit_v4 across 60/120/observed-tail windows.
- [ ] Run the focused test; expect import failure.
- [ ] Implement recent-window saved downside, missed upside, tail avoidance, fold stability, and long-history veto summaries.
- [ ] Keep 2% and 3% giveback as the only declared candidates; do not search continuous thresholds.
- [ ] Run the focused test; expect PASS.

### Task 4: Trigger-Path Stop-Loss Labels

**Files:**
- Modify: `theme_sector_radar/data/local_minute_archive.py`
- Modify: `theme_sector_radar/timing/stop_loss_research.py`
- Modify: `tests/theme_sector_radar/test_local_minute_archive.py`
- Modify: `tests/theme_sector_radar/test_stop_loss_research.py`

- [ ] Write failing tests for trigger-bar detection and forward 5/15/30-bar return, post-trigger MAE/MFE, and recovery.
- [ ] Run the focused tests; expect missing fields.
- [ ] Implement path labels using only bars strictly after the trigger bar. A repaired path is one that returns above the entry reference within the declared horizon.
- [ ] Re-test relative weakness, money-flow deterioration, and board weakness under path labels; retain next-day tail only as auxiliary evidence.
- [ ] Run focused tests; expect PASS.

### Task 5: Champion/Challenger Decision Report

**Files:**
- Create: `scripts/audit_timing_nonstationary_entry_exit_decision.py`
- Create: `tests/theme_sector_radar/test_audit_timing_nonstationary_entry_exit_decision.py`
- Create reports under `reports/nonstationary_entry_exit/`

- [ ] Write a failing test that rejects a candidate when recent, observed-tail, perturbation, concentration, or long-history veto evidence fails.
- [ ] Run the focused test; expect import failure.
- [ ] Implement hard-gate decisions and paper-only JSON/Markdown output.
- [ ] Run entry, profit, and stop audits on current 2026 records plus the caller-bound 2024/2025 long-history stress report. The sequence below uses frozen inputs, computes all eight audit SHAs from the files it just wrote, and writes only to a temporary paper-research root.

```powershell
$Reports = "<reports-root>"
$Scratch = Join-Path $env:TEMP "theme-sector-radar-nonstationary-audit"
$Candidate1m = Join-Path $Reports "agent_bridge_mds_1m_complete_sessions_v1"
$Candidate5m = Join-Path $Reports "agent_bridge_mds_5m_from_complete_1m_v1"
$CandidateSource = Join-Path $Reports "agent_bridge_mds_1m_expanded_v2"
$Selection = Join-Path $Reports "selection_validation"
$Calendar = Join-Path $Reports "nonstationary_entry_exit\calendar\a_share_trading_calendar_2026-07-13.json"
$EntryRecords1m = Join-Path $Reports "nonstationary_entry_exit\entry_records_1m\timing_paper_trading_records_2026-07-13_expanded_v2_labeled_entry_causal.json"
$EntryRecords5m = Join-Path $Reports "nonstationary_entry_exit\entry_records_5m\timing_paper_trading_records_2026-07-13_expanded_v2_labeled_entry_causal.json"
$ProfitRecords1m2 = Join-Path $Reports "timing_factor_exit\dual_exit_validation_1m\timing_paper_trading_records_2026-07-13_expanded_v2_labeled.json"
$ProfitRecords1m3 = Join-Path $Reports "nonstationary_entry_exit\profit_1m\records_3pct\timing_paper_trading_records_2026-07-13_expanded_v2_labeled_giveback_3pct.json"
$ProfitRecords5m2 = Join-Path $Reports "timing_factor_exit\dual_exit_validation_5m\timing_paper_trading_records_2026-07-13_expanded_v2_labeled.json"
$ProfitRecords5m3 = Join-Path $Reports "nonstationary_entry_exit\profit_5m\records_3pct\timing_paper_trading_records_2026-07-13_expanded_v2_labeled_giveback_3pct.json"
$LongHistory = Join-Path $Reports "nonstationary_entry_exit\stop_loss_path\local_stop_loss_path_validation_2026-07-13.json"
New-Item -ItemType Directory -Force -Path $Scratch | Out-Null

python scripts/audit_timing_nonstationary_entry.py --candidate-root $Candidate1m --candidate-source-root $CandidateSource --selection-validation-root $Selection --entry-records-path $EntryRecords1m --trading-calendar-path $Calendar --output-dir "$Scratch\entry_1m" --as-of 2026-07-13 --timeframe 1m
python scripts/audit_timing_nonstationary_entry.py --candidate-root $Candidate5m --candidate-source-root $CandidateSource --selection-validation-root $Selection --entry-records-path $EntryRecords5m --trading-calendar-path $Calendar --output-dir "$Scratch\entry_5m" --as-of 2026-07-13 --timeframe 5m
python scripts/audit_timing_nonstationary_profit_exit.py --records-path $ProfitRecords1m2 --candidate-root $Candidate1m --candidate-source-root $CandidateSource --selection-validation-root $Selection --trading-calendar-path $Calendar --output-dir "$Scratch\profit_1m" --as-of 2026-07-13 --snapshot-label expanded_v2_labeled --timeframe 1m --applied-giveback-pct 2
python scripts/audit_timing_nonstationary_profit_exit.py --records-path $ProfitRecords1m3 --candidate-root $Candidate1m --candidate-source-root $CandidateSource --selection-validation-root $Selection --trading-calendar-path $Calendar --output-dir "$Scratch\profit_1m" --as-of 2026-07-13 --snapshot-label expanded_v2_labeled --timeframe 1m --applied-giveback-pct 3
python scripts/audit_timing_nonstationary_profit_exit.py --records-path $ProfitRecords5m2 --candidate-root $Candidate5m --candidate-source-root $CandidateSource --selection-validation-root $Selection --trading-calendar-path $Calendar --output-dir "$Scratch\profit_5m" --as-of 2026-07-13 --snapshot-label expanded_v2_labeled --timeframe 5m --applied-giveback-pct 2
python scripts/audit_timing_nonstationary_profit_exit.py --records-path $ProfitRecords5m3 --candidate-root $Candidate5m --candidate-source-root $CandidateSource --selection-validation-root $Selection --trading-calendar-path $Calendar --output-dir "$Scratch\profit_5m" --as-of 2026-07-13 --snapshot-label expanded_v2_labeled --timeframe 5m --applied-giveback-pct 3
python scripts/audit_timing_nonstationary_stop_exit.py --candidate-root $Candidate1m --candidate-source-root $CandidateSource --selection-validation-root $Selection --entry-records-path $EntryRecords1m --trading-calendar-path $Calendar --output-dir "$Scratch\stop_1m" --as-of 2026-07-13 --timeframe 1m --long-history-report $LongHistory
python scripts/audit_timing_nonstationary_stop_exit.py --candidate-root $Candidate5m --candidate-source-root $CandidateSource --selection-validation-root $Selection --entry-records-path $EntryRecords5m --trading-calendar-path $Calendar --output-dir "$Scratch\stop_5m" --as-of 2026-07-13 --timeframe 5m

$Entry1mReport = "$Scratch\entry_1m\nonstationary_entry_audit_2026-07-13.json"
$Entry5mReport = "$Scratch\entry_5m\nonstationary_entry_audit_2026-07-13.json"
$Profit1m2Report = "$Scratch\profit_1m\nonstationary_profit_exit_audit_2026-07-13_expanded_v2_labeled_giveback_2pct.json"
$Profit1m3Report = "$Scratch\profit_1m\nonstationary_profit_exit_audit_2026-07-13_expanded_v2_labeled_giveback_3pct.json"
$Profit5m2Report = "$Scratch\profit_5m\nonstationary_profit_exit_audit_2026-07-13_expanded_v2_labeled_giveback_2pct.json"
$Profit5m3Report = "$Scratch\profit_5m\nonstationary_profit_exit_audit_2026-07-13_expanded_v2_labeled_giveback_3pct.json"
$Stop1mReport = "$Scratch\stop_1m\nonstationary_stop_exit_audit_2026-07-13.json"
$Stop5mReport = "$Scratch\stop_5m\nonstationary_stop_exit_audit_2026-07-13.json"
$Entry1mSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $Entry1mReport).Hash.ToLowerInvariant()
$Entry5mSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $Entry5mReport).Hash.ToLowerInvariant()
$Profit1m2Sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $Profit1m2Report).Hash.ToLowerInvariant()
$Profit1m3Sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $Profit1m3Report).Hash.ToLowerInvariant()
$Profit5m2Sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $Profit5m2Report).Hash.ToLowerInvariant()
$Profit5m3Sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $Profit5m3Report).Hash.ToLowerInvariant()
$Stop1mSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $Stop1mReport).Hash.ToLowerInvariant()
$Stop5mSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $Stop5mReport).Hash.ToLowerInvariant()
$CalendarSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $Calendar).Hash.ToLowerInvariant()
$RecordsManifest = "$Scratch\expected_records_manifest.json"
$RecordsManifestPayload = [ordered]@{
    schema_version = "timing_final_records_manifest.v1"
    paper_trading_only = $true
    no_execution_signals = $true
    does_not_modify_official_scores = $true
    records = [ordered]@{
        "entry:1m" = [ordered]@{ path = $EntryRecords1m; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $EntryRecords1m).Hash.ToLowerInvariant() }
        "entry:5m" = [ordered]@{ path = $EntryRecords5m; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $EntryRecords5m).Hash.ToLowerInvariant() }
        "profit:1m:2pct" = [ordered]@{ path = $ProfitRecords1m2; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $ProfitRecords1m2).Hash.ToLowerInvariant() }
        "profit:1m:3pct" = [ordered]@{ path = $ProfitRecords1m3; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $ProfitRecords1m3).Hash.ToLowerInvariant() }
        "profit:5m:2pct" = [ordered]@{ path = $ProfitRecords5m2; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $ProfitRecords5m2).Hash.ToLowerInvariant() }
        "profit:5m:3pct" = [ordered]@{ path = $ProfitRecords5m3; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $ProfitRecords5m3).Hash.ToLowerInvariant() }
        "stop:1m" = [ordered]@{ path = $EntryRecords1m; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $EntryRecords1m).Hash.ToLowerInvariant() }
        "stop:5m" = [ordered]@{ path = $EntryRecords5m; sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $EntryRecords5m).Hash.ToLowerInvariant() }
    }
}
$RecordsManifestPayload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $RecordsManifest -Encoding UTF8
$RecordsManifestSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $RecordsManifest).Hash.ToLowerInvariant()

python scripts/audit_timing_nonstationary_entry_exit_decision.py --entry-1m-report $Entry1mReport --entry-5m-report $Entry5mReport --profit-1m-2-report $Profit1m2Report --profit-1m-3-report $Profit1m3Report --profit-5m-2-report $Profit5m2Report --profit-5m-3-report $Profit5m3Report --stop-1m-report $Stop1mReport --stop-5m-report $Stop5mReport --candidate-1m-root $Candidate1m --candidate-5m-root $Candidate5m --candidate-source-root $CandidateSource --selection-validation-root $Selection --expected-entry-1m-sha256 $Entry1mSha --expected-entry-5m-sha256 $Entry5mSha --expected-profit-1m-2-sha256 $Profit1m2Sha --expected-profit-1m-3-sha256 $Profit1m3Sha --expected-profit-5m-2-sha256 $Profit5m2Sha --expected-profit-5m-3-sha256 $Profit5m3Sha --expected-stop-1m-sha256 $Stop1mSha --expected-stop-5m-sha256 $Stop5mSha --expected-calendar-path $Calendar --expected-calendar-sha256 $CalendarSha --expected-records-manifest $RecordsManifest --expected-records-manifest-sha256 $RecordsManifestSha --output-dir "$Scratch\decision" --as-of 2026-07-13
```
- [ ] Run all timing tests, `git diff --check`, and official-score guardrail scan.

## Self-Review

- The plan covers every design section: recent windows, the observed evaluation tail (internal `holdout` schema), regime, long-history veto, entry overfit, profit validation, stop path labels, and champion/challenger decisions.
- Public names are consistent across tasks.
- No new factor or continuous threshold search is introduced.
