# Phase 3 Acceptance Report

## 1. Modified File List

### New Files Created
| File | Description |
|------|-------------|
| `scripts/diagnose_regime_aware_factor_behavior.py` | Regime-aware factor behavior diagnosis script |
| `theme_sector_radar/scoring/stock_short_score_v2.py` | Shadow stock short score v2 module |
| `theme_sector_radar/scoring/shadow_decision_score_v3.py` | Shadow decision score v3 module |
| `scripts/evaluate_shadow_decision_score_v3.py` | V3 evaluation script |
| `tests/theme_sector_radar/test_regime_aware_factor_behavior.py` | Tests for regime-aware diagnosis |
| `tests/theme_sector_radar/test_stock_short_score_v2.py` | Tests for stock short score v2 |
| `tests/theme_sector_radar/test_shadow_decision_score_v3.py` | Tests for shadow decision score v3 |
| `tests/theme_sector_radar/test_shadow_decision_score_v3_evaluation.py` | Tests for v3 evaluation |
| `docs/phase_3_acceptance_report.md` | This acceptance report |

### Modified Files
| File | Changes |
|------|---------|
| `scripts/export_top30_candidates.py` | Added imports for v2/v3, added v2/v3 field computation and output |

---

## 2. New Field Description

### stock_short_score_v2 (shadow-only)
- **Range**: 0-100
- **Components**:
  - `close_position_score` (0-20): (close - low) / (high - low)
  - `three_day_rs_score` (0-15): 3-day relative strength
  - `five_day_rs_score` (0-15): 5-day relative strength
  - `volume_expansion_score` (0-15): Volume expansion quality
  - `sector_rs_score` (0-15): Sector relative strength
  - `rejection_penalty` (0 to -10): High rejection penalty
  - `overheat_penalty` (0 to -10): Overheat penalty
  - `data_quality_penalty` (0 to -5): Data quality penalty
- **Degradation**: Missing bars/OHLC gracefully falls back to available data
- **Fields**: `stock_short_score_v2`, `stock_short_breakdown_v2`, `stock_short_v2_tags`

### shadow_decision_score_v3 (shadow-only)
- **Range**: 0-100
- **Formula**:
  - alpha = sector_trend*0.12 + sector_burst*0.12 + stock_short_v2*0.25 + stock_trend*0.18 + leader*0.13 + agent*0.08 + quant*0.07
  - elasticity_bonus = max(0, (elasticity - 50) / 50) * 8 (opportunity, not penalty)
  - risk = hard_risk*0.8 + trade_risk*0.6 + drawdown_risk*0.4
  - final = alpha + elasticity_bonus - risk, clamped [0, 100]
- **Fields**: `shadow_decision_score_v3`, `shadow_decision_breakdown_v3`, `shadow_decision_v3_tags`

---

## 3. New Script Usage

### Regime-Aware Diagnosis
```bash
python scripts/diagnose_regime_aware_factor_behavior.py \
  --aggregate-path reports/selection_validation/aggregate/2026-01-05_to_2026-07-08/selection_validation_aggregate.json \
  --validation-root reports/selection_validation \
  --candidate-root reports/agent_bridge \
  --output-dir reports/selection_validation/diagnostics/2026-01-05_to_2026-07-08
```

### V3 Evaluation
```bash
python scripts/evaluate_shadow_decision_score_v3.py \
  --aggregate-path reports/selection_validation/aggregate/2026-01-05_to_2026-07-08/selection_validation_aggregate.json \
  --validation-root reports/selection_validation \
  --candidate-root reports/agent_bridge \
  --output-dir reports/selection_validation/shadow_score_v3/2026-01-05_to_2026-07-08
```

---

## 4. Report Output Paths

| Report | Path |
|--------|------|
| Regime-Aware JSON | `reports/selection_validation/diagnostics/2026-01-05_to_2026-07-08/regime_aware_factor_behavior.json` |
| Regime-Aware Markdown | `reports/selection_validation/diagnostics/2026-01-05_to_2026-07-08/regime_aware_factor_behavior.md` |
| V3 Evaluation JSON | `reports/selection_validation/shadow_score_v3/2026-01-05_to_2026-07-08/shadow_decision_score_v3_evaluation.json` |
| V3 Evaluation Markdown | `reports/selection_validation/shadow_score_v3/2026-01-05_to_2026-07-08/shadow_decision_score_v3_evaluation.md` |

---

## 5. Test Commands and Results

### Test Command
```bash
python -m pytest tests/theme_sector_radar/test_regime_aware_factor_behavior.py \
  tests/theme_sector_radar/test_stock_short_score_v2.py \
  tests/theme_sector_radar/test_shadow_decision_score_v3.py \
  tests/theme_sector_radar/test_shadow_decision_score_v3_evaluation.py \
  tests/theme_sector_radar/test_factor_signal_diagnosis_120d.py \
  tests/theme_sector_radar/test_risk_component_quality.py -q
```

### Test Results
```
117 passed in 0.41s
```

---

## 6. Regime-Aware Diagnosis Conclusions

### Factor Classifications

| Factor | Classification | Up Gap | Down Gap | Explanation |
|--------|---------------|--------|----------|-------------|
| `decision_score` | down_only_alpha | -0.3146 | +0.0250 | Works in bearish, fails in bullish |
| `stock_short_score` | down_only_alpha | -0.4524 | +0.7440 | Works in bearish, fails in bullish |
| `stock_trend_score` | up_only_alpha | +0.1571 | -0.1897 | Works in bullish, fails in bearish |
| `sector_leader_score` | down_only_alpha | -0.4775 | +0.0775 | Works in bearish, fails in bullish |
| `risk_penalty_score` | **all_weather_alpha** | +0.4164 | +0.3029 | Positive in ALL regimes |
| `agent_score` | inconclusive | N/A | N/A | Insufficient data |

### Key Insights
1. **risk_penalty_score is all_weather_alpha** — consistent positive gap across all regimes. This confirms the Phase 1/2 finding that risk filtering provides defensive value.
2. **Most factors are regime_dependent** — they work in one regime but fail in another.
3. **stock_short_score works best in broad_down** (gap +0.74) — defensive factor.
4. **stock_trend_score works best in broad_up** (gap +0.16) — offensive factor.

---

## 7. stock_short_score_v2 Distribution

| Metric | Value |
|--------|-------|
| Sample count | 105 (recent dates) |
| Min | 13.13 |
| Max | 30.07 |
| Mean | 22.21 |
| Spread | 16.94 |
| Unique count | 18 |

Score has reasonable spread and does not collapse to fixed values.

---

## 8. Shadow V3 vs Production Comparison

### Overall (120 days)

| Metric | Production | Shadow V3 |
|--------|------------|-----------|
| Top-Bottom Gap | -0.1657 | -0.2064 |
| Hit Rate Diff | -2.1 | -2.5 |
| Spearman ρ | -0.0199 | -0.0175 |
| Consistency | 42.9% | 42.9% |

---

## 9. Time Window Results

| Window | Prod Gap | V3 Gap | Prod Consistency | V3 Consistency |
|--------|----------|--------|------------------|----------------|
| 20d | -0.0926 | +0.3505 | 26.3% | 31.6% |
| 40d | -0.4526 | -0.2648 | 35.9% | 38.5% |
| 60d | -0.2152 | -0.3317 | 35.6% | 39.0% |
| 120d | -0.1657 | -0.2064 | 42.9% | 42.9% |

**Note**: V3 shows improvement in 20d window (gap +0.35 vs -0.09) but not in longer windows.

---

## 10. Regime Results

| Regime | Prod Gap | V3 Gap | Prod Consistency | V3 Consistency |
|--------|----------|--------|------------------|----------------|
| broad_up | -0.3146 | -0.0529 | 43.5% | 39.1% |
| broad_down | +0.0250 | -0.1162 | 43.8% | 50.0% |
| mixed | -0.2929 | -0.1300 | 41.5% | 41.5% |

**Note**: V3 reduces the negative gap in broad_up (-0.05 vs -0.31), showing improvement in bullish markets.

---

## 11. shadow_score_v3_improved

**Value: `false`**

V3 does not show consistent improvement across all windows and regimes. The 20d window shows promise, but longer windows do not show clear improvement.

---

## 12. production_change_allowed

**Value: `false`**

---

## 13. Production Weight Changes

**Status: NOT changed**

- Production `decision_score` formula: **Unchanged**
- Production `stock_short_score`: **Unchanged**
- Production ranking logic: **Unchanged**
- All new fields are **shadow/diagnostic only**

---

## 14. Next Steps

### Immediate
1. **Accumulate more data** — 120 days may not be enough for statistical significance
2. **Investigate 20d window improvement** — V3 shows promise in recent 20 days

### Short-term
3. **Regime-aware weighting** — Use regime classification to adjust factor weights dynamically
4. **Agent score rebuild** — Agent_score has insufficient data for classification
5. **Refine v3 formula** — Adjust risk weights based on regime-specific performance

### Medium-term
6. **Backtest regime-switching strategy** — Test if switching weights by regime improves returns
7. **Shadow v4** — Combine all_weather_alpha risk_penalty with regime-specific factors

### Do Not Do
- Do not change production weights based on current evaluation
- Do not make production ranking regime-dependent until validated over 200+ dates
- Do not use v3 in production until it consistently outperforms in 60d+ windows
