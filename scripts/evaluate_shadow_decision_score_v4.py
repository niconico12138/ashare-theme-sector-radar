#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shadow Decision Score V4 评估脚本

比较 production decision_score vs shadow_decision_score_v3 vs shadow_decision_score_v4 的历史表现。
不做权重调整，只输出评估结论。production_change_allowed = false。

用法:
  python scripts/evaluate_shadow_decision_score_v4.py \
    --aggregate-path reports/selection_validation/aggregate/2026-01-05_to_2026-07-08/selection_validation_aggregate.json \
    --validation-root reports/selection_validation \
    --candidate-root reports/agent_bridge \
    --output-dir reports/selection_validation/shadow_score_v4/2026-01-05_to_2026-07-08
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
from theme_sector_radar.scoring.shadow_decision_score_v3 import compute_shadow_decision_score_v3
from theme_sector_radar.scoring.shadow_decision_score_v4 import compute_shadow_decision_score_v4
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

            # Compute shadow_decision_score_v3
            v3_result = compute_shadow_decision_score_v3(cand)

            # Compute shadow_decision_score_v4 with regime
            v4_result = compute_shadow_decision_score_v4(cand, regime=market_regime)

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
                "shadow_decision_score_v3": v3_result["shadow_decision_score_v3"],
                "shadow_decision_score_v4": v4_result["shadow_decision_score_v4"],
                "shadow_decision_v4_regime_profile": v4_result["shadow_decision_v4_regime_profile"],
                "stock_short_score": ps.get("stock_short_score") or cand.get("stock_short_score"),
                "stock_short_score_v2": short_v2_result["stock_short_score_v2"],
                "source_pool": ps.get("source_pool") or cand.get("source_pool"),
                "trade_eligibility": ps.get("trade_eligibility") or cand.get("trade_eligibility"),
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
    """Compare production vs v3 vs v4."""
    valid = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]
    if len(valid) < 10:
        return {"label": label, "sample_count": len(valid), "error": "insufficient_samples"}

    results = {}
    for score_field, score_label in [
        ("decision_score", "production"),
        ("shadow_decision_score_v3", "shadow_v3"),
        ("shadow_decision_score_v4", "shadow_v4"),
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

        # Drawdown
        high_dd = [_safe_float(x.get("max_intraday_drawdown_pct")) for x in high_items]
        low_dd = [_safe_float(x.get("max_intraday_drawdown_pct")) for x in low_items]

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
            "top_avg_drawdown": _avg([v for v in high_dd if v is not None]),
            "bottom_avg_drawdown": _avg([v for v in low_dd if v is not None]),
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


# ======================================================================
# MARKDOWN REPORT
# ======================================================================

def generate_markdown(
    coverage: dict,
    overall: dict,
    windows: dict,
    regimes: dict,
    v4_score_dist: dict,
    date_range: str,
) -> str:
    lines = []
    lines.append(f"# Shadow Decision Score V4 Evaluation — {date_range}")
    lines.append("")

    # 1. Coverage
    lines.append("## 1. Data Coverage")
    lines.append("")
    lines.append(f"- Valid dates: {coverage.get('valid_dates', 0)}")
    lines.append(f"- Forward samples: {coverage.get('forward_samples', 0)}")
    lines.append("")

    # 2. V4 Score Distribution
    lines.append("## 2. Shadow Decision Score V4 Distribution")
    lines.append("")
    lines.append(f"- Min: {v4_score_dist.get('min', 'N/A')}")
    lines.append(f"- Max: {v4_score_dist.get('max', 'N/A')}")
    lines.append(f"- Mean: {v4_score_dist.get('mean', 'N/A')}")
    lines.append(f"- Spread: {v4_score_dist.get('spread', 'N/A')}")
    lines.append(f"- Unique count: {v4_score_dist.get('unique_count', 'N/A')}")
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

    # 6. Verdict
    lines.append("## 6. Verdict")
    lines.append("")
    v4_vs_prod = check_improvement(overall, "production", "shadow_v4")
    v4_vs_v3 = check_improvement(overall, "shadow_v3", "shadow_v4")
    lines.append(f"- **v4_improved_vs_production**: `{str(v4_vs_prod).lower()}`")
    lines.append(f"- **v4_improved_vs_v3**: `{str(v4_vs_v3).lower()}`")
    lines.append(f"- **production_change_allowed**: `false`")
    lines.append("")

    # 7. Production change
    lines.append("## 7. Production Change Assessment")
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
    lines.append("| Metric | Production | Shadow V3 | Shadow V4 |")
    lines.append("|--------|------------|-----------|-----------|")

    for metric in ["top_bottom_gap", "hit_rate_diff", "top_avg_return", "bottom_avg_return",
                    "spearman_corr", "consistency"]:
        prod_val = data.get("production", {}).get(metric, "N/A")
        v3_val = data.get("shadow_v3", {}).get(metric, "N/A")
        v4_val = data.get("shadow_v4", {}).get(metric, "N/A")

        if isinstance(prod_val, float):
            prod_val = f"{prod_val:.4f}"
        if isinstance(v3_val, float):
            v3_val = f"{v3_val:.4f}"
        if isinstance(v4_val, float):
            v4_val = f"{v4_val:.4f}"

        lines.append(f"| {metric} | {prod_val} | {v3_val} | {v4_val} |")

    # Pos/Neg dates
    prod_pos = data.get("production", {}).get("positive_dates", 0)
    prod_neg = data.get("production", {}).get("negative_dates", 0)
    v3_pos = data.get("shadow_v3", {}).get("positive_dates", 0)
    v3_neg = data.get("shadow_v3", {}).get("negative_dates", 0)
    v4_pos = data.get("shadow_v4", {}).get("positive_dates", 0)
    v4_neg = data.get("shadow_v4", {}).get("negative_dates", 0)
    lines.append(f"| Pos/Neg Dates | {prod_pos}/{prod_neg} | {v3_pos}/{v3_neg} | {v4_pos}/{v4_neg} |")

    return "\n".join(lines)


# ======================================================================
# MAIN
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="Evaluate shadow decision score v4")
    parser.add_argument("--aggregate-path", required=True)
    parser.add_argument("--validation-root", default="reports/selection_validation")
    parser.add_argument("--candidate-root", default="reports/agent_bridge")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

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

    # V4 score distribution
    v4_scores = [_safe_float(r.get("shadow_decision_score_v4")) for r in valid]
    v4_scores = [s for s in v4_scores if s is not None]
    v4_dist = {}
    if v4_scores:
        mn, mx = min(v4_scores), max(v4_scores)
        mean = sum(v4_scores) / len(v4_scores)
        unique = len(set(round(s, 0) for s in v4_scores))
        v4_dist = {
            "min": round(mn, 2), "max": round(mx, 2),
            "mean": round(mean, 2), "spread": round(mx - mn, 2),
            "unique_count": unique, "sample_count": len(v4_scores),
        }

    print("  Computing overall comparison...")
    overall = compute_score_comparison(records, "all")

    print("  Computing window comparisons...")
    windows = compute_window_comparisons(records)

    print("  Computing regime comparisons...")
    regimes = compute_regime_comparisons(records)

    # Check improvements
    v4_vs_prod = check_improvement(overall, "production", "shadow_v4")
    v4_vs_v3 = check_improvement(overall, "shadow_v3", "shadow_v4")

    # Build output
    output = {
        "as_of": date_range,
        "generated_at": datetime.now().isoformat(),
        "coverage": coverage,
        "production_change_allowed": False,
        "v4_improved_vs_production": v4_vs_prod,
        "v4_improved_vs_v3": v4_vs_v3,
        "v4_score_distribution": v4_dist,
        "overall_comparison": overall,
        "window_comparisons": windows,
        "regime_comparisons": regimes,
    }

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "shadow_decision_score_v4_evaluation.json"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  JSON: {json_path}")

    md = generate_markdown(coverage, overall, windows, regimes, v4_dist, date_range)
    md_path = output_dir / "shadow_decision_score_v4_evaluation.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  Markdown: {md_path}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  Shadow Decision Score V4 Evaluation Summary")
    print(f"{'='*60}")
    print(f"  v4_improved_vs_production: {v4_vs_prod}")
    print(f"  v4_improved_vs_v3: {v4_vs_v3}")
    print(f"  production_change_allowed: false")
    print()
    prod_gap = overall.get("production", {}).get("top_bottom_gap")
    v3_gap = overall.get("shadow_v3", {}).get("top_bottom_gap")
    v4_gap = overall.get("shadow_v4", {}).get("top_bottom_gap")
    print(f"  Production gap: {prod_gap}")
    print(f"  Shadow V3 gap: {v3_gap}")
    print(f"  Shadow V4 gap: {v4_gap}")


if __name__ == "__main__":
    main()
