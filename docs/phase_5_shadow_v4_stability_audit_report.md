# Phase 5: Shadow V4 Stability Audit Report

## 1. Modified File List

### New Files Created
| File | Description |
|------|-------------|
| `scripts/audit_shadow_v4_stability.py` | V4 stability audit script with rolling validation, outlier analysis, regime stability, bucket monotonicity, and promotion gate |
| `tests/theme_sector_radar/test_shadow_v4_stability_audit.py` | Tests for V4 stability audit |
| `docs/phase_5_shadow_v4_stability_audit_report.md` | This acceptance report |

---

## 2. New Script Usage

### V4 Stability Audit
```bash
python scripts/audit_shadow_v4_stability.py \
  --aggregate-path reports/selection_validation/aggregate/2026-01-05_to_2026-07-08/selection_validation_aggregate.json \
  --validation-root reports/selection_validation \
  --candidate-root reports/agent_bridge \
  --output-dir reports/selection_validation/shadow_score_v4/audit/2026-01-05_to_2026-07-08
```

---

## 3. Report Output Paths

| Report | Path |
|--------|------|
| Audit JSON | `reports/selection_validation/shadow_score_v4/audit/2026-01-05_to_2026-07-08/shadow_v4_stability_audit.json` |
| Audit Markdown | `reports/selection_validation/shadow_score_v4/audit/2026-01-05_to_2026-07-08/shadow_v4_stability_audit.md` |

---

## 4. Test Commands and Results

### Test Command
```bash
python -m pytest tests/theme_sector_radar/test_shadow_v4_stability_audit.py \
  tests/theme_sector_radar/test_shadow_decision_score_v4_evaluation.py \
  tests/theme_sector_radar/test_shadow_decision_score_v4.py \
  tests/theme_sector_radar/test_stock_short_score_v2_quality.py -q
```

### Test Results
```
58 passed in 0.29s
```

---

## 5. Rolling Walk-Forward Results

### 20d Rolling
- Total windows: 101
- Passed windows: 101
- **Positive window share: 100.0%**

### 40d Rolling
- Total windows: 81
- Passed windows: 81
- **Positive window share: 100.0%**

### 60d Rolling
- Total windows: 61
- Passed windows: 61
- **Positive window share: 100.0%**

**Summary**: V4 shows 100% positive rolling window share across all three windows. This indicates very strong stability.

---

## 6. Outlier Contribution Results

### Date Contribution
- Max single date share: **21.53%**
- Single date dominance: **False** (threshold: 35%)
- Top positive dates: 2026-03-24 (20.16%), 2026-06-23 (19.87%), 2026-02-27 (19.11%)

### Stock Contribution
- Max single stock share: **5.88%**
- Single stock dominance: **False** (threshold: 20%)

### Sector Contribution
- Max single sector share: **7.97%**
- Single sector dominance: **False** (threshold: 40%)

**Summary**: No single date, stock, or sector dominates V4 performance. This indicates good diversification.

---

## 7. Regime Stability Results

| Regime | Sample Count | V4 Gap | HR Diff | Consistency | Gap Positive |
|--------|--------------|--------|---------|-------------|--------------|
| broad_up | 803 | +0.07 | -2.4 | 45.7% | ✅ |
| broad_down | 567 | -0.04 | -0.5 | 50.0% | ❌ |
| mixed | 683 | -0.20 | -1.8 | 45.2% | ❌ |

- Positive regimes: **1** (broad_up only)
- Regime dependency warning: **True**

**Summary**: V4 only shows positive gap in broad_up regime. In broad_down and mixed regimes, the gap is slightly negative. This is the main concern for promotion.

---

## 8. Bucket Monotonicity Results

| Bucket | Count | Avg Return | Hit Rate |
|--------|-------|------------|----------|
| 80+ | 0 | N/A | N/A |
| 60-80 | 82 | +2.68% | 74.4% |
| 40-60 | 1465 | +0.55% | 53.3% |
| <40 | 506 | -1.17% | 31.8% |

- Monotonicity: **positive**
- Valid buckets: 3

**Summary**: Higher V4 score buckets show clearly higher returns. The monotonicity is positive, indicating V4 has predictive value.

---

## 9. Promotion Gate

### Status: `watch`

### production_change_allowed: `false`

### Passed Checks (6/7)
- ✅ 120d_v4_gap_positive (2.29 > 1.0)
- ✅ 60d_rolling_positive_share (100% >= 60%)
- ✅ no_single_date_dominance (21.53% <= 35%)
- ✅ no_single_stock_dominance (5.88% <= 20%)
- ✅ no_single_sector_dominance (7.97% <= 40%)
- ✅ bucket_monotonicity_ok (positive)

### Failed Checks (1/7)
- ❌ regime_dependency (only 1 regime with positive gap, need >= 2)

### Reasons
- Only 1 regime (broad_up) has positive gap
- V4 does not work in broad_down or mixed regimes

---

## 10. Is V4 Robust?

**Partially robust.** V4 shows:
- ✅ Strong rolling window stability (100% positive across all windows)
- ✅ No outlier dominance (date, stock, sector)
- ✅ Positive bucket monotonicity
- ❌ Regime dependency (only works in broad_up)

V4 is robust within the broad_up regime but does not generalize well to other market conditions.

---

## 11. Does V4 Have Concentrated Contributions?

**No.** Contributions are well-diversified:
- No single date contributes > 35%
- No single stock contributes > 20%
- No single sector contributes > 40%

---

## 12. Should We Change Production Weights?

**No.** Despite V4's strong performance in broad_up:
1. V4 only works in 1 of 3 regimes
2. Promotion gate status is "watch", not "review_ready"
3. production_change_allowed remains false

---

## 13. Production Weight Changes

**Status: NOT changed**

- Production `decision_score` formula: **Unchanged**
- Production `stock_short_score`: **Unchanged**
- Production ranking logic: **Unchanged**
- All V4 fields remain **shadow/diagnostic only**

---

## 14. Next Steps

### Immediate
1. **Investigate regime dependency** — Understand why V4 doesn't work in broad_down/mixed
2. **Consider regime-specific V4 variants** — Different formulas for different regimes

### Short-term
3. **Accumulate more data** — Validate over 200+ dates
4. **Test regime detection accuracy** — Ensure regime classification is correct
5. **Consider hybrid approach** — Use V4 only when regime is broad_up, use production otherwise

### Medium-term
6. **Shadow V5** — Address regime dependency issue
7. **Production candidate** — If regime dependency is resolved, consider production adoption

### Do Not Do
- Do not change production weights based on current audit
- Do not use V4 in production until regime dependency is resolved
- Do not make production ranking regime-dependent until validated over 200+ dates

---

## 15. Key Insights

1. **V4 is highly stable in broad_up** — 100% rolling window success, strong bucket monotonicity
2. **V4 has regime dependency issue** — Only works in bullish markets
3. **No concentration risk** — Contributions are well-diversified across dates, stocks, and sectors
4. **Promotion gate: watch** — Need to resolve regime dependency before review_ready
5. **Production change: not allowed** — V4 is not ready for production adoption
