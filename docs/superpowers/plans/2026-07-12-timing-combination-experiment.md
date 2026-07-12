# Timing Combination Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evaluate multiple paper-only intraday factor-combination versions and report the best current version.

**Architecture:** Add a focused timing combination research module, a CLI wrapper, and tests. The module operates on candidate dictionaries with factor values and `forward_return_pct`, while the CLI loads historical candidate files and selection-validation labels.

**Tech Stack:** Python, pytest, JSON/Markdown reports.

---

### Task 1: Combination Evaluator

**Files:**
- Create: `theme_sector_radar/timing/combination_experiment.py`
- Test: `tests/theme_sector_radar/test_timing_combination_experiment.py`

- [ ] Write failing tests for condition filtering, version ranking, guardrails, and best-version selection.
- [ ] Implement `FactorCondition`, `StrategyVersion`, `evaluate_strategy_versions`, and default strategy builders.
- [ ] Run focused tests until green.

### Task 2: CLI Report

**Files:**
- Create: `scripts/run_timing_combination_experiment.py`
- Test: `tests/theme_sector_radar/test_run_timing_combination_experiment.py`

- [ ] Write failing CLI test that loads candidate files and writes JSON/Markdown.
- [ ] Implement candidate loading, selection-validation label merge, JSON output, and Markdown output.
- [ ] Run focused tests until green.

### Task 3: Historical Run

**Outputs:**
- `reports/timing_combination_experiment/confirmed_factor_combo_v1/...`

- [ ] Run against `reports/agent_bridge_remaining_timing_5m`.
- [ ] Inspect ranked versions and choose the best version.
- [ ] Run verification tests and guardrail scan.
