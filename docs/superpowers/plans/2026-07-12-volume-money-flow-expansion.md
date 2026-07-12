# Volume Money Flow Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand paper-only intraday `volume_money_flow` factors and validate them with 5m-first, 1m-confirmed research.

**Architecture:** Extend `calculate_intraday_factors` with eight new shadow-only score fields, register those fields in `INTRADAY_FACTOR_RESEARCH_SPECS`, and add a reusable category frequency-validation CLI. The existing timing research runner remains the source of factor ratings.

**Tech Stack:** Python, pytest, existing JSON/Markdown report writers.

---

### Task 1: Calculator And Research Registration

**Files:**
- Modify: `theme_sector_radar/factors/calculators.py`
- Modify: `theme_sector_radar/timing/factor_research.py`
- Test: `tests/theme_sector_radar/test_factor_calculators.py`
- Test: `tests/theme_sector_radar/test_timing_factor_research.py`

- [ ] **Step 1: Write failing calculator tests**

Add tests asserting the eight new `volume_money_flow` fields are higher for supported flow than exhausted flow, and `None` without intraday bars.

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest tests\theme_sector_radar\test_factor_calculators.py::TestCalculateBarFactors::test_intraday_volume_money_flow_expansion_rewards_supported_flow tests\theme_sector_radar\test_factor_calculators.py::TestCalculateBarFactors::test_intraday_volume_money_flow_expansion_is_missing_without_bars -q`

Expected: FAIL because the new fields are missing.

- [ ] **Step 3: Implement minimal calculator fields**

Add the eight new fields to the empty result, compute them from existing intraday `prices` and `amounts`, and return them.

- [ ] **Step 4: Register research specs and test count**

Add the eight specs under `volume_money_flow`, then add a test asserting the category has at least eleven factors.

- [ ] **Step 5: Run focused tests**

Run: `python -m pytest tests\theme_sector_radar\test_factor_calculators.py tests\theme_sector_radar\test_timing_factor_research.py -q`

Expected: PASS.

### Task 2: Generic Category Frequency Validation

**Files:**
- Modify: `theme_sector_radar/timing/factor_research.py`
- Create: `scripts/run_timing_category_frequency_validation.py`
- Test: `tests/theme_sector_radar/test_timing_factor_research.py`
- Test: `tests/theme_sector_radar/test_run_timing_category_frequency_validation.py`

- [ ] **Step 1: Write failing tests**

Add tests proving comparison can filter `volume_money_flow`, and the CLI writes a paper-only report for that category.

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest tests\theme_sector_radar\test_timing_factor_research.py::test_frequency_validation_filters_requested_category tests\theme_sector_radar\test_run_timing_category_frequency_validation.py -q`

Expected: FAIL because the generic function and script do not exist.

- [ ] **Step 3: Implement generic comparison and CLI**

Add `compare_frequency_factor_reports(..., category="price_momentum")` and a new script that passes a user-selected category.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests\theme_sector_radar\test_timing_factor_research.py tests\theme_sector_radar\test_run_timing_category_frequency_validation.py -q`

Expected: PASS.

### Task 3: Run Historical Study

**Files:**
- Output: `reports/timing_factor_research/volume_money_flow_5m_then_1m/...`

- [ ] **Step 1: Backfill 5m and 1m candidate roots if needed**

Use the same historical roots and date range as price momentum: `2026-06-01` to `2026-07-10`.

- [ ] **Step 2: Run category validation**

Run the new CLI for `volume_money_flow`.

- [ ] **Step 3: Summarize promoted and rejected factors**

Report 5m `valuable`/`watchlist`, 1m-confirmed, not confirmed, and negative factors.
