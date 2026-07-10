# Phase 6: Regime Router Shadow Score V5 Report

## 1. Modified File List

### New Files Created
| File | Description |
|------|-------------|
| `theme_sector_radar/scoring/defensive_shadow_score.py` | Defensive shadow score for bearish/mixed markets |
| `theme_sector_radar/scoring/regime_router_shadow_score_v5.py` | Regime router that selects appropriate score based on market regime |
| `scripts/evaluate_regime_router_shadow_score_v5.py` | V5 evaluation script |
| `scripts/audit_shadow_v5_promotion_gate.py` | V5 promotion gate audit script |
| `tests/theme_sector_radar/test_defensive_shadow_score.py` | Tests for defensive shadow score |
| `tests/theme_sector_radar/test_regime_router_shadow_score_v5.py` | Tests for regime router V5 |
| `tests/theme_sector_radar/test_regime_router_shadow_score_v5_evaluation.py` | Tests for V5 evaluation |
| `tests/theme_sector_radar/test_shadow_v5_promotion_gate.py` | Tests for V5 promotion gate |
| `docs/phase_6_regime_router_shadow_score_v5_report.md` | This acceptance report |

### Modified Files
| File | Changes |
|------|---------|
| `scripts/export_top30_candidates.py` | Added imports for defensive/regime_router, added V5 field computation and output |

---

## 2. New Field Description

### defensive_shadow_score (shadow-only)
- **Range**: 0-100
- **Purpose**: Specialized for broad_down/mixed markets
- **Design**: Emphasizes defense, drawdown control, close quality, risk filtering
- **Fields**: `defensive_shadow_score`, `defensive_shadow_breakdown`, `defensive_shadow_tags`

### regime_router_shadow_score_v5 (shadow-only)
- **Range**: 0-100
- **Purpose**: Routes to appropriate score based on market regime
- **Profiles**:
  - `broad_up` → bull profile (V4)
  - `broad_down` → defensive profile
  - `mixed` → blended (50% defensive + 30% bull + 20% risk-adjusted)
- **Fields**: `regime_router_shadow_score_v5`, `regime_router_shadow_breakdown_v5`, `regime_router_shadow_tags_v5`, `regime_router_selected_profile`

### Sub-scores (transparency)
- `bull_regime_shadow_score` = V4 score
- `bull_regime_shadow_breakdown` = V4 breakdown
- `defensive_shadow_score` = defensive score
- `defensive_shadow_breakdown` = defensive breakdown

---

## 3. Defensive Shadow Score Design

### Components
1. **Risk Penalty Score** (0-25): Positive use (all_weather_alpha)
2. **Hard Risk Penalty** (0 to -20): Deduction for structural risks
3. **Trade Risk Penalty** (0 to -15): Deduction for execution risks
4. **Drawdown Risk Score** (0 to -15): Deduction for drawdown risks
5. **Close Position Score** (0-20): Bonus for good close quality
6. **Short Score V2** (0-15): Reduced weight to avoid chasing
7. **Volatility Elasticity** (-5 to 0): Penalty for high elasticity (not a bonus in defensive)
8. **Sector Leader Score** (-10 to 0): Penalty for weak leaders
9. **Data Quality Penalty** (0 to -5): Penalty for missing data

### Key Design Decisions
- risk_penalty_score is used positively (all_weather_alpha)
- volatility_elasticity_score is penalized, not rewarded
- close_position_score is rewarded (good close quality = defensive)
- sector_leader_score low values are penalized (prevent following weak stocks)

---

## 4. Regime Router Logic

```
if regime == "broad_up":
    profile = "bull"
    v5_score = bull_score (V4)
elif regime == "broad_down":
    profile = "defensive"
    v5_score = defensive_score
elif regime == "mixed":
    profile = "blended"
    v5_score = 50% defensive + 30% bull + 20% risk_adjusted
else:
    profile = "blended" (default)
```

---

## 5. V5 vs V4 vs Production Comparison (120d)

| Metric | Production | V4 | Defensive | V5 Router |
|--------|------------|-----|-----------|-----------|
| Top-Bottom Gap | -0.17 | +2.29 | +0.25 | **+4.59** |
| Hit Rate Diff | -2.1 | +25.2 | -0.2 | **+56.0** |
| Spearman ρ | -0.02 | +0.28 | +0.02 | **+0.54** |
| Consistency | 42.9% | 46.7% | 61.7% | **55.0%** |

---

## 6. Time Window Results

| Window | Prod Gap | V4 Gap | Defensive Gap | V5 Gap |
|--------|----------|--------|---------------|--------|
| 20d | -0.09 | +3.45 | +0.50 | **+6.16** |
| 40d | -0.45 | +2.45 | -0.01 | **+5.13** |
| 60d | -0.22 | +2.35 | +0.10 | **+4.59** |
| 120d | -0.17 | +2.29 | +0.25 | **+4.59** |

---

## 7. Regime Results

| Regime | Prod Gap | V4 Gap | Defensive Gap | V5 Gap |
|--------|----------|--------|---------------|--------|
| broad_up | -0.31 | +0.07 | +0.01 | **+0.07** |
| broad_down | +0.03 | -0.04 | **+0.78** | **+0.78** |
| mixed | -0.29 | -0.20 | +0.06 | **+0.15** |

**All 3 regimes have positive V5 gap!** This solves V4's regime dependency issue.

---

## 8. Positive Regimes

- broad_up: ✅ positive (gap=+0.07)
- broad_down: ✅ positive (gap=+0.78)
- mixed: ✅ positive (gap=+0.15)

**Positive regimes: 3 (need >= 2)**

---

## 9. Bucket Monotonicity

| Bucket | Count | Avg Return |
|--------|-------|------------|
| 60-80 | 78 | +2.57% |
| 40-60 | 638 | +2.41% |
| <40 | 1337 | -0.98% |

**Monotonicity: positive**

---

## 10. Outlier Contribution (Summary)

- Max single date share: **20.43%** (threshold: 35%)
- Max single stock share: **1.89%** (threshold: 20%)
- Max single sector share: **6.12%** (threshold: 40%)

No concentration risk detected.

---

## 11. Promotion Gate

### Status: `review_ready`

### production_change_allowed: `false`

### Passed Checks (7/7)
- ✅ 120d_v5_gap_positive (4.59 > 1.0)
- ✅ 60d_rolling_positive_share (100% >= 60%)
- ✅ no_single_date_dominance (20.43% <= 35%)
- ✅ no_single_stock_dominance (1.89% <= 20%)
- ✅ no_single_sector_dominance (6.12% <= 40%)
- ✅ multiple_regimes_positive (3 regimes)
- ✅ bucket_monotonicity_ok (positive)

### Failed Checks: None

---

## 12. V5 Improved vs Production

**Value: `true`**

V5 shows significant improvement over production:
- Gap: +4.59 vs -0.17 (production)
- Hit rate diff: +56.0 vs -2.1 (production)
- Spearman ρ: +0.54 vs -0.02 (production)

---

## 13. V5 Improved vs V4

**Value: `true`**

V5 shows significant improvement over V4:
- Gap: +4.59 vs +2.29 (V4)
- Hit rate diff: +56.0 vs +25.2 (V4)
- Spearman ρ: +0.54 vs +0.28 (V4)
- All 3 regimes positive vs only 1 (V4)

---

## 14. production_change_allowed

**Value: `false`**

Despite V5's strong performance and review_ready status:
1. V5 is still a shadow score
2. Production weights must NOT be changed automatically
3. review_ready means进入人工评审，不是自动上线

---

## 15. Production Weight Changes

**Status: NOT changed**

- Production `decision_score` formula: **Unchanged**
- Production `stock_short_score`: **Unchanged**
- Production ranking logic: **Unchanged**
- All V5 fields are **shadow/diagnostic only**

---

## 16. Test Commands and Results

### Test Command
```bash
python -m pytest tests/theme_sector_radar/test_defensive_shadow_score.py \
  tests/theme_sector_radar/test_regime_router_shadow_score_v5.py \
  tests/theme_sector_radar/test_regime_router_shadow_score_v5_evaluation.py \
  tests/theme_sector_radar/test_shadow_v5_promotion_gate.py -q
```

### Test Results
```
46 passed in 0.32s
```

---

## 17. Key Insights

1. **Regime routing solves V4's weakness** — V5 works in all 3 regimes (broad_up, broad_down, mixed)
2. **Defensive score excels in bearish markets** — +0.78 gap in broad_down vs V4's -0.04
3. **Blended approach works** — Mixed regime uses 50% defensive + 30% bull + 20% risk-adjusted
4. **V5 is highly stable** — 100% rolling window success, no concentration risk
5. **Promotion gate: review_ready** — All 7/7 checks passed

---

## 18. Next Steps

### Immediate
1. **Human review** — review_ready means进入人工评审
2. **Validate regime detection** — Ensure regime classification is accurate

### Short-term
3. **Out-of-sample testing** — Test V5 on dates not used for calibration
4. **Production candidate** — If human review approves, consider production adoption

### Medium-term
5. **Shadow V6** — Further refinements based on production feedback
6. **Production adoption** — If V5 consistently outperforms, consider replacing production score

### Do Not Do
- Do not automatically change production weights
- Do not skip human review
- Do not use V5 in production until human review approves

---

## 19. Summary

Phase 6 successfully addressed V4's regime dependency issue by:
1. Creating a defensive shadow score for bearish/mixed markets
2. Implementing a regime router that selects appropriate score based on market conditions
3. Achieving positive gap in all 3 regimes (broad_up, broad_down, mixed)
4. Reaching review_ready status with 7/7 promotion gate checks passed

**V5 is the first shadow score to achieve review_ready status.**
