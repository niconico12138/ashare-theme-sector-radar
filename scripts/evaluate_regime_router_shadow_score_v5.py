#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regime Router Shadow Score V5 评估脚本

比较 production decision_score vs shadow_decision_score_v4 vs defensive_shadow_score vs regime_router_shadow_score_v5。
不做权重调整，只输出评估结论。production_change_allowed = false。

用法:
  python scripts/evaluate_regime_router_shadow_score_v5.py \
    --aggregate-path reports/selection_validation/aggregate/2026-01-05_to_2026-07-08/selection_validation_aggregate.json \
    --validation-root reports/selection_validation \
    --candidate-root reports/agent_bridge \
    --output-dir reports/selection_validation/shadow_score_v5/2026-01-05_to_2026-07-08
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.scoring.stock_short_score_v2 import compute_stock_short_score_v2
from theme_sector_radar.scoring.shadow_decision_score_v4 import compute_shadow_decision_score_v4
from theme_sector_radar.scoring.defensive_shadow_score import compute_defensive_shadow_score
from theme_sector_radar.scoring.regime_router_shadow_score_v5 import compute_regime_router_shadow_score_v5
from theme_sector_radar.scoring.risk_decomposition import decompose_trade_risk

REGIMES = ["broad_up", "broad_down", "mixed"]
WINDOWS = [20, 40, 60, 120]


# ======================================================================
# HELPERS
# ======================================================================

def _safe_float(v, default=None):
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _avg(values: list) -> float | None:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), 4)


def _pct(values: list) -> float | None:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return round(sum(1 for v in clean if v > 0) / len(clean) * 100, 1)


def _rank(values: list[float]) -> list[float]:
    n = len(values)
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


def spearman_correlation(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3 or len(y) < 3:
        return None
    n = len(x)
    rx = _rank(x)
    ry = _rank(y)
    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n
    cov = sum((rx[i] - mean_rx) * (ry[i] - mean_ry) for i in range(n))
    std_x = math.sqrt(sum((rx[i] - mean_rx) ** 2 for i in range(n)))
    std_y = math.sqrt(sum((ry[i] - mean_ry) ** 2 for i in range(n)))
    if std_x == 0 or std_y == 0:
        return 0.0
    return round(cov / (std_x * std_y), 4)


# ======================================================================
# DATA LOADING
# ======================================================================

def load_and_compute(
    aggregate_path: Path,
    validation_root: Path,
    candidate_root: Path,
) -> tuple[list[dict], dict]:
    """Load records and compute all scores."""
    agg = json.loads(aggregate_path.read_text(encoding="utf-8"))
    ok_dates = [
        row["date"] for row in agg.get("date_status_table", [])
        if row.get("status") == "ok"
    ]

    regime_lookup = {}
    for row in agg.get("date_status_table", []):
        regime_lookup[row["date"]] = row.get("market_regime")

    records = []
    for date in ok_dates:
        val_path = validation_root / date / "next_day_selection_validation.json"
        if not val_path.exists():
            continue
        val = json.loads(val_path.read_text(encoding="utf-8"))
        per_stock = val.get("per_stock", [])
        market_regime = regime_lookup.get(date)

        t30_path = candidate_root / date / "top30_candidates.json"
        candidate_lookup = {}
        if t30_path.exists():
            try:
                t30 = json.loads(t30_path.read_text(encoding="utf-8"))
                for c in t30.get("candidates", []):
                    candidate_lookup[str(c.get("code", ""))] = c
            except Exception:
                pass

        for ps in per_stock:
            code = str(ps.get("code", ""))
            cand = candidate_lookup.get(code, {})

            # Compute stock_short_score_v2
            short_v2_result = compute_stock_short_score_v2(cand)
            cand["stock_short_score_v2"] = short_v2_result["stock_short_score_v2"]

            # Compute risk decomposition if not present
            if "hard_risk_penalty" not in cand:
                decomp = decompose_trade_risk(cand)
                cand["hard_risk_penalty"] = decomp["hard_risk_penalty"]
                cand["trade_risk_penalty"] = decomp["trade_risk_penalty"]
                cand["volatility_elasticity_score"] = decomp["volatility_elasticity_score"]
                cand["drawdown_risk_score"] = decomp["drawdown_risk_score"]

            # Compute shadow_decision_score_v4 with regime
            v4_result = compute_shadow_decision_score_v4(cand, regime=market_regime)

            # Compute defensive shadow score
            def_result = compute_defensive_shadow_score(cand)

            # Compute regime router shadow score V5
            v5_result = compute_regime_router_shadow_score_v5(cand, regime=market_regime)

            records.append({
                "date": date,
                "code": code,
                "name": ps.get("name", ""),
                "market_regime": market_regime,
                "next_return_pct": ps.get("next_return_pct"),
                "next_low_return_pct": ps.get("next_low_return_pct"),
                "max_intraday_drawdown_pct": ps.get("max_intraday_drawdown_pct"),
                "data_available": ps.get("data_available", False),
                "decision_score": ps.get("decision_score") or cand.get("decision_score"),
                "shadow_decision_score_v4": v4_result["shadow_decision_score_v4"],
                "defensive_shadow_score": def_result["defensive_shadow_score"],
                "regime_router_shadow_score_v5": v5_result["regime_router_shadow_score_v5"],
                "regime_router_selected_profile": v5_result["regime_router_selected_profile"],
                "stock_short_score": ps.get("stock_short_score") or cand.get("stock_short_score"),
                "stock_short_score_v2": short_v2_result["stock_short_score_v2"],
            })

    return records, agg


# ======================================================================
# SCORE COMPARISON
# ======================================================================

def _split_by_quantile(items: list[dict], field: str, n: int = 3) -> dict[str, list[dict]]:
    valid = [(i, _safe_float(i.get(field))) for i in items]
    valid = [(i, v) for i, v in valid if v is not None]
    valid.sort(key=lambda x: x[1], reverse=True)
    total = len(valid)
    if total == 0:
        return {}
    group_size = max(1, total // n)
    labels = ["high", "mid", "low"][:n]
    groups: dict[str, list[dict]] = {lb: [] for lb in labels}
    for idx, (item, _) in enumerate(valid):
        g = min(idx // group_size, n - 1)
        groups[labels[g]].append(item)
    return groups


def compute_score_comparison(records: list[dict], label: str = "all") -> dict:
    """Compare production vs v4 vs defensive vs v5."""
    valid = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]
    if len(valid) < 10:
        return {"label": label, "sample_count": len(valid), "error": "insufficient_samples"}

    results = {}
    for score_field, score_label in [
        ("decision_score", "production"),
        ("shadow_decision_score_v4", "shadow_v4"),
        ("defensive_shadow_score", "defensive"),
        ("regime_router_shadow_score_v5", "regime_router_v5"),
    ]:
        groups = _split_by_quantile(valid, score_field, 3)
        high_items = groups.get("high", [])
        low_items = groups.get("low", [])

        high_ret = [_safe_float(x.get("next_return_pct")) for x in high_items]
        low_ret = [_safe_float(x.get("next_return_pct")) for x in low_items]

        high_avg = _avg(high_ret)
        low_avg = _avg(low_ret)
        gap = round(high_avg - low_avg, 4) if high_avg is not None and low_avg is not None else None

        high_hr = _pct(high_ret)
        low_hr = _pct(low_ret)
        hr_diff = round(high_hr - low_hr, 1) if high_hr is not None and low_hr is not None else None

        # Spearman correlation
        aligned = [
            (_safe_float(x.get(score_field)), _safe_float(x.get("next_return_pct")))
            for x in valid
        ]
        aligned = [(v, r) for v, r in aligned if v is not None and r is not None]
        corr = None
        if len(aligned) >= 5:
            corr = spearman_correlation([a[0] for a in aligned], [a[1] for a in aligned])

        # Consistency
        by_date = defaultdict(list)
        for r in valid:
            score = _safe_float(r.get(score_field))
            ret = _safe_float(r.get("next_return_pct"))
            if score is not None and ret is not None:
                by_date[r["date"]].append((score, ret))

        pos_dates, neg_dates = 0, 0
        for date_items in by_date.values():
            if len(date_items) < 3:
                continue
            dc = spearman_correlation([x[0] for x in date_items], [x[1] for x in date_items])
            if dc is not None:
                if dc > 0:
                    pos_dates += 1
                elif dc < 0:
                    neg_dates += 1

        consistency = round(pos_dates / max(1, pos_dates + neg_dates) * 100, 1)

        results[score_label] = {
            "top_bottom_gap": gap,
            "hit_rate_diff": hr_diff,
            "top_avg_return": high_avg,
            "bottom_avg_return": low_avg,
            "spearman_corr": corr,
            "consistency": consistency,
            "positive_dates": pos_dates,
            "negative_dates": neg_dates,
        }

    return {
        "label": label,
        "sample_count": len(valid),
        **results,
    }


def compute_window_comparisons(records: list[dict]) -> dict:
    """Compute comparisons for different time windows."""
    dates = sorted(set(r["date"] for r in records))
    results = {}

    for window in WINDOWS:
        if len(dates) < window:
            results[f"{window}d"] = {"error": f"insufficient dates ({len(dates)} < {window})"}
            continue
        window_dates = dates[-window:]
        window_records = [r for r in records if r["date"] in window_dates]
        results[f"{window}d"] = compute_score_comparison(window_records, f"last_{window}d")

    return results


def compute_regime_comparisons(records: list[dict]) -> dict:
    """Compute comparisons per market regime."""
    results = {}
    for regime in REGIMES:
        regime_records = [r for r in records if r.get("market_regime") == regime]
        results[regime] = compute_score_comparison(regime_records, regime)
    return results


def check_improvement(overall: dict, baseline: str, target: str) -> bool:
    """Check if target score is better than baseline."""
    base_data = overall.get(baseline, {})
    target_data = overall.get(target, {})

    base_gap = base_data.get("top_bottom_gap")
    target_gap = target_data.get("top_bottom_gap")
    base_cons = base_data.get("consistency")
    target_cons = target_data.get("consistency")

    if base_gap is None or target_gap is None:
        return False

    gap_improved = target_gap > base_gap
    cons_improved = (target_cons or 0) > (base_cons or 0)

    return gap_improved or cons_improved


def compute_bucket_monotonicity(records: list[dict], field: str) -> dict:
    """Check bucket monotonicity for a score field."""
    valid = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]
    if len(valid) < 20:
        return {"error": "insufficient_samples", "monotonicity": "inconclusive"}

    buckets = {"60-80": [], "40-60": [], "<40": []}
    for r in valid:
        score = _safe_float(r.get(field))
        if score is None:
            continue
        if score >= 60:
            buckets["60-80"].append(r)
        elif score >= 40:
            buckets["40-60"].append(r)
        else:
            buckets["<40"].append(r)

    bucket_stats = {}
    for bucket_name, items in buckets.items():
        rets = [_safe_float(x.get("next_return_pct")) for x in items]
        avg_ret = _avg(rets)
        bucket_stats[bucket_name] = {"count": len(items), "avg_return": avg_ret}

    ordered = ["60-80", "40-60", "<40"]
    returns = [bucket_stats[b]["avg_return"] for b in ordered if bucket_stats[b]["avg_return"] is not None]

    monotonicity = "inconclusive"
    if len(returns) >= 3:
        if all(returns[i] >= returns[i+1] for i in range(len(returns)-1)):
            monotonicity = "positive"
        elif all(returns[i] <= returns[i+1] for i in range(len(returns)-1)):
            monotonicity = "negative"

    return {"bucket_stats": bucket_stats, "monotonicity": monotonicity}


# ======================================================================
# MARKDOWN REPORT
# ======================================================================

def generate_markdown(
    coverage: dict,
    overall: dict,
    windows: dict,
    regimes: dict,
    v5_dist: dict,
    bucket_mono: dict,
    date_range: str,
) -> str:
    lines = []
    lines.append(f"# Regime Router Shadow Score V5 Evaluation — {date_range}")
    lines.append("")

    # 1. Coverage
    lines.append("## 1. Data Coverage")
    lines.append("")
    lines.append(f"- Valid dates: {coverage.get('valid_dates', 0)}")
    lines.append(f"- Forward samples: {coverage.get('forward_samples', 0)}")
    lines.append("")

    # 2. V5 Distribution
    lines.append("## 2. V5 Score Distribution")
    lines.append("")
    lines.append(f"- Min: {v5_dist.get('min', 'N/A')}")
    lines.append(f"- Max: {v5_dist.get('max', 'N/A')}")
    lines.append(f"- Mean: {v5_dist.get('mean', 'N/A')}")
    lines.append(f"- Spread: {v5_dist.get('spread', 'N/A')}")
    lines.append(f"- Unique count: {v5_dist.get('unique_count', 'N/A')}")
    lines.append("")

    # 3. Overall comparison
    lines.append("## 3. Overall Comparison (All Dates)")
    lines.append("")
    lines.append(_comparison_table(overall))

    # 4. Window comparisons
    lines.append("## 4. Time Window Comparisons")
    lines.append("")
    for window_key, window_data in windows.items():
        lines.append(f"### {window_key}")
        lines.append("")
        if "error" in window_data:
            lines.append(f"- {window_data['error']}")
        else:
            lines.append(_comparison_table(window_data))
        lines.append("")

    # 5. Regime comparisons
    lines.append("## 5. Regime Comparisons")
    lines.append("")
    for regime in REGIMES:
        regime_data = regimes.get(regime, {})
        lines.append(f"### {regime}")
        lines.append("")
        if "error" in regime_data:
            lines.append(f"- {regime_data.get('error', 'no data')}")
        else:
            lines.append(_comparison_table(regime_data))
        lines.append("")

    # 6. Positive regimes
    lines.append("## 6. Positive Regimes")
    lines.append("")
    positive_count = 0
    for regime in REGIMES:
        v5_gap = regimes.get(regime, {}).get("regime_router_v5", {}).get("top_bottom_gap")
        if v5_gap is not None and v5_gap > 0:
            positive_count += 1
            lines.append(f"- {regime}: ✅ positive (gap={v5_gap})")
        else:
            lines.append(f"- {regime}: ❌ negative (gap={v5_gap})")
    lines.append(f"\nPositive regimes: {positive_count} (need >= 2)")
    lines.append("")

    # 7. Bucket monotonicity
    lines.append("## 7. Bucket Monotonicity")
    lines.append("")
    lines.append(f"- Monotonicity: {bucket_mono.get('monotonicity', 'inconclusive')}")
    lines.append("")
    for bucket, stats in bucket_mono.get("bucket_stats", {}).items():
        lines.append(f"- {bucket}: count={stats.get('count', 0)}, avg_return={stats.get('avg_return', 'N/A')}")
    lines.append("")

    # 8. Verdict
    lines.append("## 8. Verdict")
    lines.append("")
    v5_vs_prod = check_improvement(overall, "production", "regime_router_v5")
    v5_vs_v4 = check_improvement(overall, "shadow_v4", "regime_router_v5")
    lines.append(f"- **v5_improved_vs_production**: `{str(v5_vs_prod).lower()}`")
    lines.append(f"- **v5_improved_vs_v4**: `{str(v5_vs_v4).lower()}`")
    lines.append(f"- **production_change_allowed**: `false`")
    lines.append("")

    # 9. Production change
    lines.append("## 9. Production Change Assessment")
    lines.append("")
    lines.append("- **production_change_allowed**: `false`")
    lines.append("- Do not change production weights based on this evaluation.")
    lines.append("- All shadow scores are diagnostic only.")
    lines.append("")

    return "\n".join(lines)


def _comparison_table(data: dict) -> str:
    """Generate a comparison table."""
    lines = []
    n = data.get("sample_count", 0)
    lines.append(f"Sample count: {n}")
    lines.append("")
    lines.append("| Metric | Production | V4 | Defensive | V5 Router |")
    lines.append("|--------|------------|-----|-----------|-----------|")

    for metric in ["top_bottom_gap", "hit_rate_diff", "spearman_corr", "consistency"]:
        prod_val = data.get("production", {}).get(metric, "N/A")
        v4_val = data.get("shadow_v4", {}).get(metric, "N/A")
        def_val = data.get("defensive", {}).get(metric, "N/A")
        v5_val = data.get("regime_router_v5", {}).get(metric, "N/A")

        if isinstance(prod_val, float): prod_val = f"{prod_val:.4f}"
        if isinstance(v4_val, float): v4_val = f"{v4_val:.4f}"
        if isinstance(def_val, float): def_val = f"{def_val:.4f}"
        if isinstance(v5_val, float): v5_val = f"{v5_val:.4f}"

        lines.append(f"| {metric} | {prod_val} | {v4_val} | {def_val} | {v5_val} |")

    return "\n".join(lines)


# ======================================================================
# MAIN
# ======================================================================


def _sample_records() -> list[dict]:
    """Build deterministic records for open-source V5 sample mode."""
    records = []
    regimes = ["broad_up", "broad_down", "mixed"]
    for i in range(30):
        regime = regimes[i % len(regimes)]
        strength = 30 - i
        records.append({
            "date": f"2026-06-{(i % 10) + 1:02d}",
            "code": f"600{i + 1:03d}",
            "name": f"Sample Stock {i + 1}",
            "market_regime": regime,
            "data_available": True,
            "next_return_pct": round(-1.0 + strength * 0.12, 4),
            "next_low_return_pct": round(-1.6 + strength * 0.08, 4),
            "max_intraday_drawdown_pct": round(1.5 - strength * 0.02, 4),
            "decision_score": 40 + strength * 0.4,
            "shadow_decision_score_v4": 38 + strength * 0.8,
            "defensive_shadow_score": 36 + strength * 0.7,
            "regime_router_shadow_score_v5": 35 + strength * 1.0,
            "regime_router_selected_profile": "bull" if regime == "broad_up" else ("defensive" if regime == "broad_down" else "blended"),
            "stock_short_score": 35 + strength * 0.5,
            "stock_short_score_v2": 35 + strength * 0.7,
        })
    return records


def run_sample_evaluation(output_dir: Path | str) -> dict:
    """Run V5 evaluation on synthetic records without historical artifacts."""
    output_dir = Path(output_dir)
    records = _sample_records()
    valid = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]
    coverage = {"total_dates": len(sorted(set(r["date"] for r in records))), "valid_dates": len(sorted(set(r["date"] for r in valid))), "total_candidates": len(records), "forward_samples": len(valid), "date_range": "sample"}
    v5_scores = [_safe_float(r.get("regime_router_shadow_score_v5")) for r in valid]
    v5_scores = [score for score in v5_scores if score is not None]
    v5_dist = {"min": round(min(v5_scores), 2), "max": round(max(v5_scores), 2), "mean": round(sum(v5_scores) / len(v5_scores), 2), "spread": round(max(v5_scores) - min(v5_scores), 2), "unique_count": len(set(round(s, 0) for s in v5_scores)), "sample_count": len(v5_scores)}
    overall = compute_score_comparison(records, "sample")
    windows = compute_window_comparisons(records)
    regimes = compute_regime_comparisons(records)
    bucket_mono = compute_bucket_monotonicity(records, "regime_router_shadow_score_v5")
    output = {"as_of": "sample", "sample_mode": True, "generated_at": datetime.now().isoformat(), "coverage": coverage, "production_change_allowed": False, "promotion_gate": "review_ready_shadow_only", "v5_improved_vs_production": check_improvement(overall, "production", "regime_router_v5"), "v5_improved_vs_v4": check_improvement(overall, "shadow_v4", "regime_router_v5"), "v5_score_distribution": v5_dist, "overall_comparison": overall, "window_comparisons": windows, "regime_comparisons": regimes, "bucket_monotonicity": bucket_mono, "disclaimer": "Research sample only. Not investment advice or stock recommendation."}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "regime_router_shadow_score_v5_evaluation.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    md = generate_markdown(coverage, overall, windows, regimes, v5_dist, bucket_mono, "sample")
    md += "\n\n> Sample mode uses synthetic fixture data. V5 remains review_ready shadow-only, not production_enabled.\n"
    (output_dir / "regime_router_shadow_score_v5_evaluation.md").write_text(md, encoding="utf-8")
    print(f"  Sample V5 evaluation: {output_dir}")
    return output
def main():
    parser = argparse.ArgumentParser(description="Evaluate regime router shadow score V5")
    parser.add_argument("--sample", action="store_true", help="Run deterministic sample mode without historical artifacts")
    parser.add_argument("--aggregate-path", default=None)
    parser.add_argument("--validation-root", default="reports/selection_validation")
    parser.add_argument("--candidate-root", default="reports/agent_bridge")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    if args.sample:
        run_sample_evaluation(Path(args.output_dir or "reports/selection_validation/shadow_score_v5/sample"))
        return

    if not args.aggregate_path or not args.output_dir:
        parser.error("--aggregate-path and --output-dir are required unless --sample is used")

    aggregate_path = Path(args.aggregate_path)
    validation_root = Path(args.validation_root)
    candidate_root = Path(args.candidate_root)
    output_dir = Path(args.output_dir)

    date_range = aggregate_path.parent.name

    print(f"  Loading and computing scores...")
    records, agg = load_and_compute(aggregate_path, validation_root, candidate_root)
    valid = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]
    print(f"  Total: {len(records)}, with forward data: {len(valid)}")

    ok_dates = [row for row in agg.get("date_status_table", []) if row.get("status") == "ok"]
    coverage = {
        "total_dates": len(agg.get("date_status_table", [])),
        "valid_dates": len(ok_dates),
        "total_candidates": len(records),
        "forward_samples": len(valid),
        "date_range": date_range,
    }

    # V5 score distribution
    v5_scores = [_safe_float(r.get("regime_router_shadow_score_v5")) for r in valid]
    v5_scores = [s for s in v5_scores if s is not None]
    v5_dist = {}
    if v5_scores:
        mn, mx = min(v5_scores), max(v5_scores)
        mean = sum(v5_scores) / len(v5_scores)
        unique = len(set(round(s, 0) for s in v5_scores))
        v5_dist = {
            "min": round(mn, 2), "max": round(mx, 2),
            "mean": round(mean, 2), "spread": round(mx - mn, 2),
            "unique_count": unique, "sample_count": len(v5_scores),
        }

    print("  Computing overall comparison...")
    overall = compute_score_comparison(records, "all")

    print("  Computing window comparisons...")
    windows = compute_window_comparisons(records)

    print("  Computing regime comparisons...")
    regimes = compute_regime_comparisons(records)

    print("  Computing bucket monotonicity...")
    bucket_mono = compute_bucket_monotonicity(records, "regime_router_shadow_score_v5")

    # Check improvements
    v5_vs_prod = check_improvement(overall, "production", "regime_router_v5")
    v5_vs_v4 = check_improvement(overall, "shadow_v4", "regime_router_v5")

    # Build output
    output = {
        "as_of": date_range,
        "generated_at": datetime.now().isoformat(),
        "coverage": coverage,
        "production_change_allowed": False,
        "v5_improved_vs_production": v5_vs_prod,
        "v5_improved_vs_v4": v5_vs_v4,
        "v5_score_distribution": v5_dist,
        "overall_comparison": overall,
        "window_comparisons": windows,
        "regime_comparisons": regimes,
        "bucket_monotonicity": bucket_mono,
    }

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "regime_router_shadow_score_v5_evaluation.json"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  JSON: {json_path}")

    md = generate_markdown(coverage, overall, windows, regimes, v5_dist, bucket_mono, date_range)
    md_path = output_dir / "regime_router_shadow_score_v5_evaluation.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  Markdown: {md_path}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  Regime Router V5 Evaluation Summary")
    print(f"{'='*60}")
    print(f"  v5_improved_vs_production: {v5_vs_prod}")
    print(f"  v5_improved_vs_v4: {v5_vs_v4}")
    print(f"  production_change_allowed: false")
    print()
    prod_gap = overall.get("production", {}).get("top_bottom_gap")
    v4_gap = overall.get("shadow_v4", {}).get("top_bottom_gap")
    v5_gap = overall.get("regime_router_v5", {}).get("top_bottom_gap")
    print(f"  Production gap: {prod_gap}")
    print(f"  V4 gap: {v4_gap}")
    print(f"  V5 gap: {v5_gap}")


if __name__ == "__main__":
    main()


