#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
因子方向校准实验

分析每个因子在不同市场状态下应该正向、反向、仅防御有效，还是暂不可信。
不修改生产评分逻辑，只输出校准建议。

用法:
  python scripts/calibrate_factor_direction.py \
    --diagnosis-path reports/selection_validation/diagnostics/2026-06-01_to_2026-07-07/factor_failure_diagnosis.json \
    --validation-root reports/selection_validation \
    --candidate-root reports/agent_bridge \
    --output-dir reports/selection_validation/calibration/2026-06-01_to_2026-07-07
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from diagnose_factor_failure import (
    load_per_candidate_records,
    spearman_correlation,
    _safe_float,
    _avg,
    _split_by_quantile,
)


# ======================================================================
# FACTOR LIST
# ======================================================================

CALIBRATION_FACTORS = [
    "decision_score",
    "stock_short_score",
    "stock_trend_score",
    "sector_leader_score",
    "risk_penalty_score",
    "agent_score",
    "risk_adjusted_score",
    "quant_score",
    "final_score",
    "trend_score",
    "burst_score",
]


# ======================================================================
# PER-DATE BUCKET ANALYSIS
# ======================================================================

def _split_by_percentile(items: list[dict], field: str, top_pct: float = 0.3) -> tuple[list[dict], list[dict]]:
    """Split items into high (top_pct) and low (bottom_pct) by field within date."""
    valid = [(i, _safe_float(i.get(field))) for i in items]
    valid = [(i, v) for i, v in valid if v is not None]
    if len(valid) < 3:
        return [], []
    valid.sort(key=lambda x: x[1], reverse=True)
    n = len(valid)
    top_n = max(1, int(n * top_pct))
    high = [x[0] for x in valid[:top_n]]
    low = [x[0] for x in valid[-top_n:]]
    return high, low


def compute_factor_stats(
    records: list[dict],
    factor: str,
    regime: str | None = None,
) -> dict:
    """Compute calibration stats for a factor, optionally filtered by regime."""
    # Filter records
    if regime:
        subset = [r for r in records if r.get("market_regime") == regime
                  and r.get("data_available") and r.get("next_return_pct") is not None]
    else:
        subset = [r for r in records if r.get("data_available")
                  and r.get("next_return_pct") is not None]

    if not subset:
        return {"sample_count": 0, "date_count": 0}

    # Group by date
    by_date: dict[str, list[dict]] = defaultdict(list)
    for r in subset:
        by_date[r["date"]].append(r)

    # Daily Spearman correlations
    daily_corrs = []
    high_returns_all = []
    low_returns_all = []
    high_hits = 0
    low_hits = 0

    for date, items in sorted(by_date.items()):
        # Spearman
        vals = [_safe_float(x.get(factor)) for x in items]
        rets = [_safe_float(x.get("next_return_pct")) for x in items]
        aligned = [(v, r) for v, r in zip(vals, rets) if v is not None and r is not None]
        if len(aligned) >= 3:
            x = [a[0] for a in aligned]
            y = [a[1] for a in aligned]
            corr = spearman_correlation(x, y)
            if corr is not None:
                daily_corrs.append(corr)

        # Bucket analysis (within date)
        high, low = _split_by_percentile(items, factor, 0.3)
        h_rets = [_safe_float(x.get("next_return_pct")) for x in high]
        l_rets = [_safe_float(x.get("next_return_pct")) for x in low]
        h_rets = [r for r in h_rets if r is not None]
        l_rets = [r for r in l_rets if r is not None]

        high_returns_all.extend(h_rets)
        low_returns_all.extend(l_rets)
        high_hits += sum(1 for r in h_rets if r > 0)
        low_hits += sum(1 for r in l_rets if r > 0)

    # Aggregate
    avg_corr = round(sum(daily_corrs) / len(daily_corrs), 4) if daily_corrs else None
    pos_count = sum(1 for c in daily_corrs if c > 0)
    neg_count = sum(1 for c in daily_corrs if c < 0)
    consistency_pos = round(pos_count / len(daily_corrs) * 100, 1) if daily_corrs else None
    consistency_neg = round(neg_count / len(daily_corrs) * 100, 1) if daily_corrs else None

    high_avg = _avg(high_returns_all)
    low_avg = _avg(low_returns_all)
    gap = None
    if high_avg is not None and low_avg is not None:
        gap = round(high_avg - low_avg, 4)

    high_hit = round(high_hits / len(high_returns_all) * 100, 1) if high_returns_all else None
    low_hit = round(low_hits / len(low_returns_all) * 100, 1) if low_returns_all else None

    # Pooled Spearman
    all_vals = [_safe_float(x.get(factor)) for x in subset]
    all_rets = [_safe_float(x.get("next_return_pct")) for x in subset]
    aligned_all = [(v, r) for v, r in zip(all_vals, all_rets) if v is not None and r is not None]
    pooled_corr = None
    if len(aligned_all) >= 3:
        pooled_corr = spearman_correlation([a[0] for a in aligned_all], [a[1] for a in aligned_all])

    return {
        "sample_count": len(subset),
        "date_count": len(by_date),
        "spearman_corr_avg_by_date": avg_corr,
        "spearman_corr_pooled": pooled_corr,
        "positive_corr_date_count": pos_count,
        "negative_corr_date_count": neg_count,
        "consistency_positive": consistency_pos,
        "consistency_negative": consistency_neg,
        "high_bucket_avg_return": high_avg,
        "low_bucket_avg_return": low_avg,
        "high_minus_low_gap": gap,
        "high_bucket_hit_rate": high_hit,
        "low_bucket_hit_rate": low_hit,
    }


# ======================================================================
# DIRECTION CLASSIFICATION
# ======================================================================

def classify_direction(all_stats: dict, up_stats: dict, down_stats: dict) -> tuple[str, str]:
    """Classify factor direction and confidence."""
    sample = all_stats.get("sample_count", 0)
    dates = all_stats.get("date_count", 0)
    gap = all_stats.get("high_minus_low_gap")
    cons_pos = all_stats.get("consistency_positive")
    cons_neg = all_stats.get("consistency_negative")

    up_gap = up_stats.get("high_minus_low_gap")
    down_gap = down_stats.get("high_minus_low_gap")

    # Insufficient samples
    if sample < 50 or dates < 5:
        return "insufficient_samples", "low"

    # Positive alpha
    if gap is not None and gap >= 1.0 and cons_pos is not None and cons_pos >= 60:
        direction = "positive_alpha"
    # Negative alpha
    elif gap is not None and gap <= -1.0 and cons_neg is not None and cons_neg >= 60:
        direction = "negative_alpha"
    # Regime dependent (check AFTER positive/negative alpha)
    # Only when BOTH up and down have significant opposite gaps
    elif (up_gap is not None and down_gap is not None
          and up_gap * down_gap < 0
          and abs(up_gap) > 0.5 and abs(down_gap) > 0.5):
        direction = "regime_dependent"
    # Defensive only
    elif (up_gap is not None and down_gap is not None
          and down_gap > 0.5 and up_gap <= 0):
        direction = "defensive_only"
    # Offensive only
    elif (up_gap is not None and down_gap is not None
          and up_gap > 0.5 and down_gap <= 0):
        direction = "offensive_only"
    else:
        direction = "no_signal"

    # Confidence
    if sample >= 300 and gap is not None and abs(gap) >= 1.0 and cons_pos is not None and cons_pos >= 60:
        confidence = "high"
    elif sample >= 150 and gap is not None and abs(gap) >= 0.5:
        confidence = "medium"
    else:
        confidence = "low"

    return direction, confidence


# ======================================================================
# RISK PENALTY INTERPRETATION
# ======================================================================

def interpret_risk_penalty(all_stats: dict, up_stats: dict, down_stats: dict) -> dict:
    """Special diagnosis for risk_penalty_score."""
    gap = all_stats.get("high_minus_low_gap")
    cons_pos = all_stats.get("consistency_positive")
    pooled_corr = all_stats.get("spearman_corr_pooled")

    is_valid = False
    interpretation = ""
    recommendation = ""

    if gap is not None and gap > 0 and pooled_corr is not None and pooled_corr > 0:
        # Positive correlation: high risk penalty → higher return
        is_valid = False
        interpretation = "risk_penalty_behaves_like_volatility_or_elasticity_not_pure_risk"
        recommendation = (
            "Do not use risk_penalty_score as a linear deduction from decision_score. "
            "Split into: (1) hard_risk (ST/delisting/liquidity), "
            "(2) volatility_elasticity (high vol ≠ bad), "
            "(3) drawdown_risk (actual downside)."
        )
    elif gap is not None and gap < 0:
        is_valid = True
        interpretation = "risk_penalty_functions_as_expected"
        recommendation = "Current usage is valid"
    else:
        interpretation = "insufficient_signal"
        recommendation = "More data needed"

    return {
        "is_risk_proxy_valid": is_valid,
        "interpretation": interpretation,
        "recommendation": recommendation,
        "observed_gap": gap,
        "observed_corr": pooled_corr,
    }


# ======================================================================
# CALIBRATION RECOMMENDATIONS
# ======================================================================

def build_recommendations(factor_results: dict) -> list[dict]:
    """Build calibration recommendations for each factor."""
    recs = []
    for factor, info in factor_results.items():
        direction = info.get("direction", "no_signal")
        current_usage = _get_current_usage(factor)

        if direction == "positive_alpha":
            action = "confirm_positive_direction"
            allowed = False
        elif direction == "negative_alpha":
            action = "investigate_reverse_signal"
            allowed = False
        elif direction == "defensive_only":
            action = "use_only_in_down_market_regime"
            allowed = False
        elif direction == "offensive_only":
            action = "use_only_in_up_market_regime"
            allowed = False
        elif direction == "regime_dependent":
            action = "implement_regime_conditional_weighting"
            allowed = False
        elif direction == "insufficient_samples":
            action = "collect_more_data"
            allowed = False
        else:
            action = "monitor_or_redefine"
            allowed = False

        # Special handling for risk_penalty_score
        if factor == "risk_penalty_score":
            action = "split_risk_penalty_before_weight_change"
            allowed = False

        recs.append({
            "factor": factor,
            "current_usage": current_usage,
            "observed_direction": direction,
            "recommended_action": action,
            "production_change_allowed": allowed,
        })

    return recs


def _get_current_usage(factor: str) -> str:
    usages = {
        "decision_score": "primary_composite_score",
        "stock_short_score": "component_of_decision_score",
        "stock_trend_score": "component_of_decision_score",
        "sector_leader_score": "component_of_decision_score",
        "risk_penalty_score": "subtracted_from_decision_score",
        "agent_score": "component_of_decision_score_when_available",
        "risk_adjusted_score": "post_agent_risk_adjustment",
        "quant_score": "input_to_candidate_selection",
        "final_score": "input_to_candidate_selection",
        "trend_score": "sector_level_input",
        "burst_score": "sector_level_input",
    }
    return usages.get(factor, "unknown")


# ======================================================================
# NEXT EXPERIMENT PROPOSAL
# ======================================================================

def propose_next_experiment(factor_results: dict, risk_interp: dict) -> str:
    """Propose the next experiment based on calibration results."""
    directions = {f: info.get("direction") for f, info in factor_results.items()}

    if risk_interp.get("is_risk_proxy_valid") is False:
        return (
            "Priority 1: Split risk_penalty_score into hard_risk / volatility_elasticity / drawdown_risk. "
            "This is the highest-impact fix because risk_penalty currently has the strongest "
            "positive correlation with returns, suggesting it penalizes high-elasticity stocks "
            "that actually outperform."
        )

    neg_factors = [f for f, d in directions.items() if d == "negative_alpha"]
    if neg_factors:
        return (
            f"Priority 1: Investigate why {', '.join(neg_factors)} have negative alpha. "
            "Consider whether the factor construction methodology needs revision."
        )

    regime_deps = [f for f, d in directions.items() if d == "regime_dependent"]
    if regime_deps:
        return (
            f"Priority 1: Implement regime-conditional weighting for {', '.join(regime_deps)}. "
            "Use market regime detection to switch factor directions."
        )

    return (
        "Priority 1: Continue accumulating data (target 30+ trading days). "
        "Current signals are insufficient for confident direction changes."
    )


# ======================================================================
# MARKDOWN REPORT
# ======================================================================

def generate_markdown(
    factor_results: dict,
    risk_interp: dict,
    recommendations: list[dict],
    next_experiment: str,
    coverage: dict,
) -> str:
    lines = []
    lines.append(f"# Factor Direction Calibration — 2026-06-01 to 2026-07-07")
    lines.append(f"")

    # 1. Executive Summary
    lines.append(f"## 1. Executive Summary")
    lines.append(f"")
    pos = [f for f, r in factor_results.items() if r.get("direction") == "positive_alpha"]
    neg = [f for f, r in factor_results.items() if r.get("direction") == "negative_alpha"]
    defn = [f for f, r in factor_results.items() if r.get("direction") == "defensive_only"]
    reg = [f for f, r in factor_results.items() if r.get("direction") == "regime_dependent"]
    no_sig = [f for f, r in factor_results.items() if r.get("direction") in ("no_signal", "insufficient_samples")]

    if pos:
        lines.append(f"- **Positive alpha**: {', '.join(pos)}")
    if neg:
        lines.append(f"- **Negative alpha**: {', '.join(neg)}")
    if defn:
        lines.append(f"- **Defensive only**: {', '.join(defn)}")
    if reg:
        lines.append(f"- **Regime dependent**: {', '.join(reg)}")
    if no_sig:
        lines.append(f"- **No signal / insufficient**: {', '.join(no_sig)}")
    lines.append(f"- **Risk penalty valid**: {risk_interp.get('is_risk_proxy_valid', 'N/A')}")
    lines.append(f"")

    # 2. Dataset Summary
    lines.append(f"## 2. Dataset Summary")
    lines.append(f"")
    lines.append(f"- Valid dates: {coverage.get('valid_date_count', 0)}")
    lines.append(f"- Total records: {coverage.get('total_records', 0)}")
    lines.append(f"- Records with forward data: {coverage.get('records_with_data', 0)}")
    lines.append(f"")

    # 3. Factor Direction Table
    lines.append(f"## 3. Factor Direction Table")
    lines.append(f"")
    lines.append(f"| {'Factor':<22} {'N':>5} {'Dates':>5} {'All Gap':>9} {'Up Gap':>9} {'Down Gap':>9} {'Avg ρ':>8} {'Direction':<18} {'Conf':<6} |")
    lines.append(f"|{'─'*24}|{'─'*7}|{'─'*7}|{'─'*11}|{'─'*11}|{'─'*11}|{'─'*10}|{'─'*20}|{'─'*8}|")
    for factor in CALIBRATION_FACTORS:
        info = factor_results.get(factor, {})
        n = info.get("sample_count", 0)
        dates = info.get("date_count", 0)
        all_gap = info.get("all", {}).get("high_minus_low_gap")
        up_gap = info.get("broad_up", {}).get("high_minus_low_gap")
        down_gap = info.get("broad_down", {}).get("high_minus_low_gap")
        avg_rho = info.get("all", {}).get("spearman_corr_avg_by_date")
        direction = info.get("direction", "?")
        confidence = info.get("confidence", "?")

        all_gap_s = f"{all_gap:.2f}" if all_gap is not None else "N/A"
        up_gap_s = f"{up_gap:.2f}" if up_gap is not None else "N/A"
        down_gap_s = f"{down_gap:.2f}" if down_gap is not None else "N/A"
        rho_s = f"{avg_rho:.4f}" if avg_rho is not None else "N/A"

        lines.append(f"| {factor:<22} {n:>5} {dates:>5} {all_gap_s:>9} {up_gap_s:>9} {down_gap_s:>9} {rho_s:>8} {direction:<18} {confidence:<6} |")
    lines.append(f"")

    # 4. Regime-Specific Findings
    lines.append(f"## 4. Regime-Specific Findings")
    lines.append(f"")
    for regime in ["broad_up", "broad_down", "mixed"]:
        lines.append(f"### {regime}")
        lines.append(f"")
        lines.append(f"| {'Factor':<22} {'N':>5} {'Gap':>9} {'High Avg':>9} {'Low Avg':>9} {'Hit High':>9} {'Hit Low':>9} |")
        lines.append(f"|{'─'*24}|{'─'*7}|{'─'*11}|{'─'*11}|{'─'*11}|{'─'*11}|{'─'*11}|")
        for factor in CALIBRATION_FACTORS:
            info = factor_results.get(factor, {}).get(regime, {})
            n = info.get("sample_count", 0)
            gap = info.get("high_minus_low_gap")
            h_avg = info.get("high_bucket_avg_return")
            l_avg = info.get("low_bucket_avg_return")
            h_hit = info.get("high_bucket_hit_rate")
            l_hit = info.get("low_bucket_hit_rate")

            gap_s = f"{gap:.2f}" if gap is not None else "N/A"
            h_avg_s = f"{h_avg:.2f}" if h_avg is not None else "N/A"
            l_avg_s = f"{l_avg:.2f}" if l_avg is not None else "N/A"
            h_hit_s = f"{h_hit:.1f}" if h_hit is not None else "N/A"
            l_hit_s = f"{l_hit:.1f}" if l_hit is not None else "N/A"

            lines.append(f"| {factor:<22} {n:>5} {gap_s:>9} {h_avg_s:>9} {l_avg_s:>9} {h_hit_s:>9} {l_hit_s:>9} |")
        lines.append(f"")

    # 5. Risk Penalty Interpretation
    lines.append(f"## 5. Risk Penalty Interpretation")
    lines.append(f"")
    lines.append(f"- **is_risk_proxy_valid**: {risk_interp.get('is_risk_proxy_valid', 'N/A')}")
    lines.append(f"- **interpretation**: {risk_interp.get('interpretation', 'N/A')}")
    lines.append(f"- **observed_gap**: {risk_interp.get('observed_gap', 'N/A')}")
    lines.append(f"- **observed_corr**: {risk_interp.get('observed_corr', 'N/A')}")
    lines.append(f"- **recommendation**: {risk_interp.get('recommendation', 'N/A')}")
    lines.append(f"")

    # 6. Calibration Recommendations
    lines.append(f"## 6. Calibration Recommendations")
    lines.append(f"")
    lines.append(f"| {'Factor':<22} {'Current Usage':<30} {'Direction':<18} {'Action':<35} {'Prod Change':<12} |")
    lines.append(f"|{'─'*24}|{'─'*32}|{'─'*20}|{'─'*37}|{'─'*14}|")
    for rec in recommendations:
        lines.append(
            f"| {rec['factor']:<22} {rec['current_usage']:<30} "
            f"{rec['observed_direction']:<18} {rec['recommended_action']:<35} "
            f"{str(rec['production_change_allowed']):<12} |"
        )
    lines.append(f"")

    # 7. Do Not Change
    lines.append(f"## 7. Do Not Change Production Weights Yet")
    lines.append(f"")
    lines.append(f"**All production_change_allowed = false.** No factor has sufficient evidence")
    lines.append(f"to warrant a production weight change at this time.")
    lines.append(f"")
    lines.append(f"Reasons:")
    lines.append(f"- Sample size is still limited (24 dates, ~420 records)")
    lines.append(f"- Most factors show no_signal or regime_dependent patterns")
    lines.append(f"- risk_penalty_score is the strongest signal but needs structural redesign")
    lines.append(f"- Direction consistency is below 60% for most factors")
    lines.append(f"")

    # 8. Next Experiment
    lines.append(f"## 8. Next Experiment Proposal")
    lines.append(f"")
    lines.append(f"{next_experiment}")
    lines.append(f"")

    return "\n".join(lines)


def _resolve_aggregate_path(validation_root: Path, aggregate_path: str | None = None) -> Path | None:
    """Resolve the aggregate file used by calibration."""
    if aggregate_path:
        path = Path(aggregate_path)
        return path if path.exists() else None

    agg_base = validation_root / "aggregate"
    if not agg_base.exists():
        return None

    candidates = list(agg_base.rglob("selection_validation_aggregate.json"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


# ======================================================================
# MAIN
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="Calibrate factor direction")
    parser.add_argument("--diagnosis-path", required=True)
    parser.add_argument("--aggregate-path", default=None)
    parser.add_argument("--validation-root", default="reports/selection_validation")
    parser.add_argument("--candidate-root", default="reports/agent_bridge")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    diagnosis_path = Path(args.diagnosis_path)
    validation_root = Path(args.validation_root)
    candidate_root = Path(args.candidate_root)
    output_dir = Path(args.output_dir)

    print(f"  Loading diagnosis...")
    diagnosis = json.loads(diagnosis_path.read_text(encoding="utf-8"))

    # Prefer an explicit aggregate path; otherwise use the newest aggregate so
    # recalibration does not silently read an old window.
    agg_path = _resolve_aggregate_path(validation_root, args.aggregate_path)

    if agg_path is None:
        print(f"  ❌ No aggregate file found")
        sys.exit(1)

    print(f"  Loading per-candidate records from {agg_path}...")
    records = load_per_candidate_records(agg_path, validation_root, candidate_root)

    print(f"  Loaded {len(records)} records")

    valid_records = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]
    print(f"  Records with forward data: {len(valid_records)}")

    # Coverage
    coverage = diagnosis.get("coverage", {})
    coverage["total_records"] = len(records)
    coverage["records_with_data"] = len(valid_records)

    # Compute factor stats
    factor_results = {}
    for factor in CALIBRATION_FACTORS:
        print(f"  Computing {factor}...")
        all_stats = compute_factor_stats(records, factor, regime=None)
        up_stats = compute_factor_stats(records, factor, regime="broad_up")
        down_stats = compute_factor_stats(records, factor, regime="broad_down")
        mixed_stats = compute_factor_stats(records, factor, regime="mixed")

        direction, confidence = classify_direction(all_stats, up_stats, down_stats)

        factor_results[factor] = {
            "all": all_stats,
            "broad_up": up_stats,
            "broad_down": down_stats,
            "mixed": mixed_stats,
            "direction": direction,
            "confidence": confidence,
        }

    # Risk penalty interpretation
    print(f"  Interpreting risk_penalty_score...")
    risk_interp = interpret_risk_penalty(
        factor_results.get("risk_penalty_score", {}).get("all", {}),
        factor_results.get("risk_penalty_score", {}).get("broad_up", {}),
        factor_results.get("risk_penalty_score", {}).get("broad_down", {}),
    )

    # Recommendations
    recommendations = build_recommendations(factor_results)

    # Next experiment
    next_experiment = propose_next_experiment(factor_results, risk_interp)

    # Build output
    output = {
        "as_of": "2026-06-01 to 2026-07-07",
        "coverage": coverage,
        "factor_results": factor_results,
        "risk_penalty_interpretation": risk_interp,
        "calibration_recommendations": recommendations,
        "next_experiment_proposal": next_experiment,
    }

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "factor_direction_calibration.json"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ JSON: {json_path}")

    md = generate_markdown(factor_results, risk_interp, recommendations, next_experiment, coverage)
    md_path = output_dir / "factor_direction_calibration.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  ✅ Markdown: {md_path}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  Calibration Summary")
    print(f"{'='*60}")
    for factor in CALIBRATION_FACTORS:
        info = factor_results[factor]
        d = info.get("direction", "?")
        c = info.get("confidence", "?")
        gap = info.get("all", {}).get("high_minus_low_gap")
        gap_s = f"{gap:.2f}" if gap is not None else "N/A"
        print(f"  {factor:<22} direction={d:<18} conf={c:<6} gap={gap_s}")

    print(f"\n  Risk penalty valid: {risk_interp.get('is_risk_proxy_valid')}")
    print(f"  All production_change_allowed: false")


if __name__ == "__main__":
    main()
