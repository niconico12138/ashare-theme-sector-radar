# Phase 1 + Phase 2 Acceptance Report

## 1. Modified File List

### New Files Created
| File | Description |
|------|-------------|
| `scripts/diagnose_factor_signal_120d.py` | 120-day factor signal diagnosis script |
| `tests/theme_sector_radar/test_factor_signal_diagnosis_120d.py` | Tests for 120d diagnosis |
| `docs/phase_1_2_acceptance_report.md` | This acceptance report |

### Modified Files
| File | Changes |
|------|---------|
| `theme_sector_radar/scoring/risk_decomposition.py` | Added `trade_risk_penalty`, `risk_quality_tags` to `decompose_trade_risk()` |
| `scripts/export_top30_candidates.py` | Added new shadow fields to top30 output |
| `scripts/diagnose_risk_component_quality.py` | Added `trade_risk_penalty` and `risk_quality_tags` to data loading, distribution, and return relationship analysis |
| `tests/theme_sector_radar/test_risk_component_quality.py` | Added tests for `trade_risk_penalty`, `risk_quality_tags`, `hard_risk` variation, production decision_score unchanged |
| `tests/theme_sector_radar/test_selection_validation_batch.py` | Added tests for shadow risk fields in top30_candidates |

---

## 2. New Script Usage

### Factor Signal 120d Diagnosis
```bash
python scripts/diagnose_factor_signal_120d.py \
  --aggregate-path reports/selection_validation/aggregate/2026-01-05_to_2026-07-08/selection_validation_aggregate.json \
  --validation-root reports/selection_validation \
  --candidate-root reports/agent_bridge \
  --output-dir reports/selection_validation/diagnostics/2026-01-05_to_2026-07-08
```

**Parameters:**
- `--aggregate-path`: Path to `selection_validation_aggregate.json`
- `--validation-root`: Root directory for per-date validation JSONs (default: `reports/selection_validation`)
- `--candidate-root`: Root directory for per-date `top30_candidates.json` (default: `reports/agent_bridge`)
- `--output-dir`: Output directory for diagnosis reports

---

## 3. New Report Paths

| Report | Path |
|--------|------|
| Factor Diagnosis JSON | `reports/selection_validation/diagnostics/2026-01-05_to_2026-07-08/factor_diagnosis_120d.json` |
| Factor Diagnosis Markdown | `reports/selection_validation/diagnostics/2026-01-05_to_2026-07-08/factor_diagnosis_120d.md` |

---

## 4. Test Commands and Results

### Test Command
```bash
python -m pytest tests/theme_sector_radar/test_factor_failure_diagnosis.py \
  tests/theme_sector_radar/test_factor_direction_calibration.py \
  tests/theme_sector_radar/test_risk_component_quality.py \
  tests/theme_sector_radar/test_selection_validation_batch.py \
  tests/theme_sector_radar/test_factor_signal_diagnosis_120d.py -q
```

### Test Results
```
114 passed in 0.46s
```

All tests pass, including:
- 32 tests for 120d factor signal diagnosis
- 28 tests for risk component quality (including new `trade_risk_penalty` and `risk_quality_tags` tests)
- Remaining tests for factor failure diagnosis, direction calibration, and selection validation batch

---

## 5. 120-Day Sample Statistics

| Metric | Value |
|--------|-------|
| Total dates scanned | 184 |
| Valid dates (forward-return available) | 120 |
| Total candidate entries | 2,100 |
| Forward-return samples | 2,053 |
| Date range | 2026-01-05 to 2026-07-08 |

---

## 6. Factor Diagnosis Conclusions

### Signal Classification

| Factor | Signal | Gap (pp) | Consistency | Explanation |
|--------|--------|----------|-------------|-------------|
| `decision_score` | regime_dependent | -0.1657 | 42.5% | Sign flips: broad_up=-0.31, broad_down=+0.03 |
| `stock_short_score` | regime_dependent | +0.0187 | 48.3% | Sign flips: broad_up=-0.45, broad_down=+0.74 |
| `stock_trend_score` | regime_dependent | +0.0674 | 50.0% | Sign flips: broad_up=+0.16, broad_down=-0.19 |
| `sector_leader_score` | regime_dependent | -0.2446 | 44.2% | Sign flips: broad_up=-0.48, broad_down=+0.08 |
| `risk_penalty_score` | **positive_signal** | +0.2574 | 58.3% | High-risk-penalty group outperforms with 58.3% consistency |
| `agent_score` | regime_dependent | -0.6116 | 40.0% | Sign flips: broad_up=+1.63, broad_down=-0.61 |

### Key Findings

1. **risk_penalty_score is the only factor with positive_signal** (gap=+0.26pp, consistency=58.3%). This means stocks with higher risk penalty scores actually outperform — the risk filter is working defensively, not as alpha.

2. **All other factors are regime_dependent** — they flip sign between broad_up and broad_down markets. This explains why aggregate validation showed "inconclusive" signals.

3. **Strongest positive factor**: `risk_penalty_score` (gap=+0.26pp, consistency=58.3%)
4. **Strongest negative factor**: `agent_score` (gap=-0.61pp, consistency=40.0%)

5. **Trend vs Burst**: Overall gap=-0.16pp (trend underperforms burst slightly). In broad_up: burst outperforms (+2.38% vs +1.55%). In broad_down: trend outperforms (-2.00% vs -2.40%).

6. **Agent analyzed vs skipped**: Analyzed stocks underperform skipped by -0.26pp. Agent selection adds negative value in current form.

### Spearman Rank Correlation

| Factor | Avg ρ | Consistency |
|--------|-------|-------------|
| decision_score | -0.0248 | 42.5% |
| stock_short_score | -0.0205 | 48.3% |
| stock_trend_score | -0.0082 | 50.0% |
| sector_leader_score | -0.0145 | 44.2% |
| risk_penalty_score | +0.0502 | 58.3% |
| agent_score | -0.0035 | 40.0% |

---

## 7. Risk Split: Before vs After

### Before (existing `risk_decomposition.py`)
- `hard_risk_penalty` (0-50): ST, delisted, liquidity, data quality
- `volatility_elasticity_score` (0-100): High volatility/elasticity features
- `drawdown_risk_score` (0-50): Drawdown risk from overheated patterns
- `risk_decomposition_tags`: Raw tags without category prefix

### After (updated `risk_decomposition.py`)
- `hard_risk_penalty` (0-50): **Unchanged** — structural exclusions
- **`trade_risk_penalty` (0-40)**: **NEW** — short-term execution risk (near limit-up, high rejection, overextended, consecutive poor close, abnormal turnover)
- `volatility_elasticity_score` (0-100): **Unchanged** — high volatility features
- `drawdown_risk_score` (0-50): **Unchanged** — drawdown risk
- **`risk_quality_tags`**: **NEW** — human-readable category-prefixed tags (`hard:`, `trade:`, `elast:`, `drawdown:`)
- `risk_decomposition_tags`: **Kept** for backward compatibility

### New `trade_risk_penalty` Components

| Trigger | Points | Tag |
|---------|--------|-----|
| Near limit-up (change > 9.5%) | +15 | `trade:near_limit_up` |
| Strong change (change > 8%) | +10 | `trade:strong_change` |
| High rejection (short high, trend low) | +8 | `trade:high_rejection` |
| Overextended (short > 80, trend < 50) | +5 | `trade:overextended` |
| Consecutive poor close | +5 | `trade:consecutive_poor_close` |
| Abnormal turnover, weak close | +5 | `trade:abnormal_turnover_weak_close` |
| Laggard momentum | +3 | `trade:laggard_momentum` |
| Original risk_tags trade signals | +2 each | `trade:from_<tag>` |

**Max cap**: 40.0

### `risk_quality_tags` Format
Each tag is prefixed with its category:
- `hard:st_stock`, `hard:low_liquidity`, `hard:partial_data_risk`
- `trade:near_limit_up`, `trade:high_rejection`
- `elast:high_change`, `elast:burst_pool`
- `drawdown:near_limit_up`, `drawdown:short_overheated`

---

## 8. production_change_allowed

**Value: `false`**

Reason: No factor shows consistent positive signal with >= 55% daily consistency that would justify production weight changes. The only positive_signal (`risk_penalty_score`) indicates defensive value, not alpha generation.

---

## 9. Production Weight Changes

**Status: NOT changed**

- Production `decision_score` formula: **Unchanged** (sector_trend*0.15 + sector_burst*0.15 + stock_short*0.25 + stock_trend*0.20 + sector_leader*0.15 + agent*0.10 - risk_penalty)
- Production `risk_penalty_score`: **Unchanged** (computed by `trade_risk.py`)
- Production ranking logic: **Unchanged**
- All new fields (`trade_risk_penalty`, `risk_quality_tags`) are **shadow/diagnostic only**

---

## 10. Next Steps

### Immediate
1. **Re-run `export_top30_candidates.py`** for historical dates to populate `trade_risk_penalty` and `risk_quality_tags` in existing reports
2. **Run risk component quality diagnosis** on 120d data with new fields to compare old vs new risk decomposition

### Short-term
3. **Regime-aware analysis**: Since most factors are regime_dependent, build regime-specific factor models (Phase 3 of the plan)
4. **Agent score rebuild**: Agent_score shows strongest negative signal — investigate why agent-analyzed stocks underperform (Phase 4)
5. **Short score rebuild**: stock_short_score is inconclusive with near-zero gap — rebuild as shadow feature (Phase 3)

### Medium-term
6. **Shadow decision_score v3**: Combine positive_signal risk_penalty with regime-aware factors
7. **Backtest regime-switching strategy**: Test if switching factor weights by market regime improves returns
8. **Agent output reframing**: Convert agent_score to structured catalyst type/strength/sustainability fields

### Do Not Do
- Do not change production weights based on current diagnosis
- Do not increase agent analysis count to fix factor failure
- Do not judge based on single-day top5 performance
- Do not make production ranking regime-dependent until validated over 200+ dates
