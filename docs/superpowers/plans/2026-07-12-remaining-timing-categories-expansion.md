# Remaining Timing Categories Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand and validate the remaining six paper-only intraday timing factor categories.

**Architecture:** Add six new calculated fields per category in `calculate_intraday_factors`, register each field once in `INTRADAY_FACTOR_RESEARCH_SPECS`, and reuse the generic category frequency-validation CLI. Historical research runs are stored under category-specific report folders.

**Tech Stack:** Python, pytest, JSON/Markdown reports.

---

### Task 1: Lock Category Boundaries With Tests

**Files:**
- Modify: `tests/theme_sector_radar/test_factor_calculators.py`
- Modify: `tests/theme_sector_radar/test_timing_factor_research.py`

- [ ] Write failing tests proving each remaining category has at least ten factors.
- [ ] Write failing tests proving healthy intraday examples score above weak examples for new higher-is-better factors.
- [ ] Write failing tests proving new `risk_reversal` fields are lower for healthy examples.
- [ ] Write missing-data tests proving new fields return `None` without intraday bars.

### Task 2: Implement One Category At A Time

**Files:**
- Modify: `theme_sector_radar/factors/calculators.py`
- Modify: `theme_sector_radar/timing/factor_research.py`

- [ ] Add `vwap_mean_price` fields and specs, then run focused tests.
- [ ] Add `intraday_position` fields and specs, then run focused tests.
- [ ] Add `sector_confirmation` fields and specs, then run focused tests.
- [ ] Add `relative_strength` fields and specs, then run focused tests.
- [ ] Add `risk_reversal` fields and specs, then run focused tests.
- [ ] Add `time_structure` fields and specs, then run focused tests.

### Task 3: Refresh Documentation

**Files:**
- Modify: `docs/runbooks/timing_factor_catalog.md`

- [ ] Add expanded factor tables for all six categories.
- [ ] Keep direction metadata explicit for lower-is-better risk factors.

### Task 4: Historical Research

**Outputs:**
- `reports/timing_factor_research/<category>_5m_then_1m/...`

- [ ] Backfill 5m and 1m candidates once with the expanded factor set.
- [ ] Run category frequency validation for `vwap_mean_price`.
- [ ] Run category frequency validation for `intraday_position`.
- [ ] Run category frequency validation for `sector_confirmation`.
- [ ] Run category frequency validation for `relative_strength`.
- [ ] Run category frequency validation for `risk_reversal`.
- [ ] Run category frequency validation for `time_structure`.
- [ ] Summarize confirmed, watchlist, weak, and negative factors per category.
