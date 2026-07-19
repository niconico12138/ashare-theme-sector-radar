# Stop-Loss Negative Sample Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a paper-only negative-event dataset with matched controls and test sector weakness, relative weakness, and money-flow deterioration for stop-loss confirmation.

**Architecture:** A new pure module labels intraday records and deterministically matches controls. A CLI loads historical candidate files and selection labels, writes the expanded dataset, and produces JSON/Markdown factor audits. Existing exit rules remain observational until the audit provides sufficient evidence.

**Tech Stack:** Python 3 standard library, pytest.

---

### Task 1: Label negative events and controls

**Files:**
- Create: `theme_sector_radar/timing/stop_loss_research.py`
- Create: `tests/theme_sector_radar/test_stop_loss_research.py`

- [ ] Write a failing test asserting a -3% MAE record receives `intraday_drawdown`, a next-day -5% label receives `next_day_tail_loss`, and a same-date normal record is selected as its control.
- [ ] Run `python -m pytest tests/theme_sector_radar/test_stop_loss_research.py -q`; expect import failure.
- [ ] Implement `build_stop_loss_negative_sample(records, drawdown_pct=-3.0, tail_loss_pct=-5.0)` with deterministic date, board, and early-return matching; unmatched rows use `control_unavailable=True`.
- [ ] Re-run the focused test; expect PASS.

### Task 2: Measure three factor groups without scoring changes

**Files:**
- Modify: `theme_sector_radar/timing/stop_loss_research.py`
- Modify: `tests/theme_sector_radar/test_stop_loss_research.py`

- [ ] Write failing tests for `sector_weakness`, `relative_weakness`, and `money_flow_deterioration` evidence fields and factor-level summaries.
- [ ] Run the focused test; expect failure due to absent factor fields.
- [ ] Derive fields only from existing candidate data: sector support/breadth, relative resilience/market alpha, and late breakdown/volume-price/money-flow fields. Return missing data as unavailable, never as a positive signal.
- [ ] Re-run the focused test; expect PASS.

### Task 3: Add reproducible sample and audit CLI

**Files:**
- Create: `scripts/run_local_stop_loss_sample.py`
- Create: `tests/theme_sector_radar/test_run_local_stop_loss_sample.py`

- [ ] Write a failing CLI test that writes JSON/Markdown with negative count, matched-control count, and per-factor tail summaries.
- [ ] Run the test; expect import failure.
- [ ] Implement CLI arguments `--stock-archive`, `--codes-json`, `--output-dir`, `--as-of`; read the caller-bound local archive and write only paper-research artifacts.
- [ ] Re-run the test; expect PASS.

Run:
```powershell
python scripts/run_local_stop_loss_sample.py --stock-archive <local-1m-archive.zip> --codes-json <codes.json> --output-dir <paper-report-dir> --as-of 2026-07-13
```

### Task 4: Run caller-bound archive research and decide promotion

**Files:**
- Create: `reports/timing_stop_loss/<run-label>/*.json`
- Create: `reports/timing_stop_loss/<run-label>/*.md`

- [ ] Run the archive-bound CLI separately for the declared 2024 and 2025 local 1m archives. Each run consumes an explicit code manifest and writes only to a paper research directory; candidate roots and selection reports are not inputs to this CLI.

```powershell
$CodesJson = Join-Path $env:TEMP "theme-sector-radar-stop-codes.json"
'{"codes":["000001","600000"]}' | Set-Content -LiteralPath $CodesJson -Encoding utf8
python scripts/run_local_stop_loss_sample.py --stock-archive "<local-archive-root>/2024_1min.zip" --codes-json $CodesJson --output-dir "$env:TEMP\theme-sector-radar-stop-sample-2024" --as-of 2026-07-13
python scripts/run_local_stop_loss_sample.py --stock-archive "<local-archive-root>/2025_1min.zip" --codes-json $CodesJson --output-dir "$env:TEMP\theme-sector-radar-stop-sample-2025" --as-of 2026-07-13
```
- [ ] Audit factor coverage, negative/control balance, tail reduction, false-positive proxy, and date/board/code concentration.
- [ ] Run all focused tests plus `git diff --check` and official-score guardrail scan.
- [ ] Classify each factor as `insufficient_evidence`, `observe`, or `paper_candidate`; no live promotion is permitted.

## Plan Self-Review

- Tasks cover the confirmed sample labels, matching, three factor families, reproducible outputs, and evidence-only decisions.
- All names and CLI inputs are fixed; no continuous parameter search is introduced.
