#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regime-aware 因子行为诊断脚本

分析各因子在 broad_up / broad_down / mixed 不同市场状态下的表现。
识别哪些因子适合哪些市场状态，哪些因子属于 defensive_not_alpha。
不做权重调整，只输出诊断结论。production_change_allowed = false。

用法:
  python scripts/diagnose_regime_aware_factor_behavior.py \
    --aggregate-path reports/selection_validation/aggregate/2026-01-05_to_2026-07-08/selection_validation_aggregate.json \
    --validation-root reports/selection_validation \
    --candidate-root reports/agent_bridge \
    --output-dir reports/selection_validation/diagnostics/2026-01-05_to_2026-07-08
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

# Factors to analyze
FACTOR_FIELDS = [
    "decision_score",
    "stock_short_score",
    "stock_trend_score",
    "sector_leader_score",
    "risk_penalty_score",
    "agent_score",
]

REGIMES = ["broad_up", "broad_down", "mixed"]


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
    """Compute percentage of positive values."""
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return round(sum(1 for v in clean if v > 0) / len(clean) * 100, 1)


def _rank(values: list[float]) -> list[float]:
    """Assign ranks to values. Ties get average rank."""
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

def load_per_candidate_records(
    aggregate_path: Path,
    validation_root: Path,
    candidate_root: Path,
) -> tuple[list[dict], dict]:
    """Load and merge per-candidate records from all valid dates."""
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
                "stock_short_score": ps.get("stock_short_score") or cand.get("stock_short_score"),
                "stock_trend_score": cand.get("stock_trend_score"),
                "sector_leader_score": cand.get("sector_leader_score"),
                "risk_penalty_score": cand.get("risk_penalty_score"),
                "agent_score": cand.get("agent_score"),
                "source_pool": ps.get("source_pool") or cand.get("source_pool"),
                "trade_eligibility": ps.get("trade_eligibility") or cand.get("trade_eligibility"),
            })

    return records, agg


# ======================================================================
# REGIME-FACTOR ANALYSIS
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


def compute_regime_factor_gaps(records: list[dict]) -> dict:
    """Compute per-factor top-bottom gap for each regime."""
    valid = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]

    # Group by regime
    regime_records: dict[str, list[dict]] = defaultdict(list)
    for r in valid:
        regime_records[r.get("market_regime", "unknown")].append(r)

    result = {}
    for regime in REGIMES:
        items = regime_records.get(regime, [])
        if len(items) < 10:
            result[regime] = {"sample_count": len(items), "factors": {}, "error": "insufficient_samples"}
            continue

        factors = {}
        for field in FACTOR_FIELDS:
            groups = _split_by_quantile(items, field, 3)
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
                (_safe_float(x.get(field)), _safe_float(x.get("next_return_pct")))
                for x in items
            ]
            aligned = [(v, r) for v, r in aligned if v is not None and r is not None]
            corr = None
            if len(aligned) >= 5:
                xs = [a[0] for a in aligned]
                ys = [a[1] for a in aligned]
                corr = spearman_correlation(xs, ys)

            # Drawdown comparison
            high_dd = [_safe_float(x.get("max_intraday_drawdown_pct")) for x in high_items]
            low_dd = [_safe_float(x.get("max_intraday_drawdown_pct")) for x in low_items]
            high_dd_avg = _avg(high_dd)
            low_dd_avg = _avg(low_dd)
            dd_diff = round(high_dd_avg - low_dd_avg, 4) if high_dd_avg is not None and low_dd_avg is not None else None

            factors[field] = {
                "high_count": len(high_items),
                "low_count": len(low_items),
                "high_avg_return": high_avg,
                "low_avg_return": low_avg,
                "gap": gap,
                "high_hit_rate": high_hr,
                "low_hit_rate": low_hr,
                "hit_rate_diff": hr_diff,
                "spearman_corr": corr,
                "high_avg_drawdown": high_dd_avg,
                "low_avg_drawdown": low_dd_avg,
                "drawdown_diff": dd_diff,
            }

        result[regime] = {
            "sample_count": len(items),
            "factors": factors,
        }

    return result


def classify_regime_behavior(regime_gaps: dict) -> dict:
    """Classify each factor's behavior across regimes.

    Categories:
    - up_only_alpha: positive gap only in broad_up, negative/zero in broad_down
    - down_only_alpha: positive gap only in broad_down, negative/zero in broad_up
    - all_weather_alpha: positive gap in both broad_up and broad_down
    - defensive_not_alpha: reduces drawdown but doesn't improve return
    - regime_dependent: sign flips, no consistent pattern
    - inconclusive: insufficient data or no clear pattern
    """
    classifications = {}

    for field in FACTOR_FIELDS:
        up_data = regime_gaps.get("broad_up", {}).get("factors", {}).get(field, {})
        down_data = regime_gaps.get("broad_down", {}).get("factors", {}).get(field, {})
        mixed_data = regime_gaps.get("mixed", {}).get("factors", {}).get(field, {})

        up_gap = up_data.get("gap")
        down_gap = down_data.get("gap")
        mixed_gap = mixed_data.get("gap")

        up_dd = up_data.get("drawdown_diff")
        down_dd = down_data.get("drawdown_diff")

        up_corr = up_data.get("spearman_corr")
        down_corr = down_data.get("spearman_corr")

        # Check if data is sufficient
        if up_gap is None or down_gap is None:
            classifications[field] = {
                "classification": "inconclusive",
                "explanation": "Insufficient data in broad_up or broad_down regime.",
                "up_gap": up_gap,
                "down_gap": down_gap,
                "mixed_gap": mixed_gap,
            }
            continue

        # Check for defensive_not_alpha: negative gap but lower drawdown
        if up_gap <= 0 and down_gap <= 0:
            if (up_dd is not None and up_dd < 0) or (down_dd is not None and down_dd < 0):
                classifications[field] = {
                    "classification": "defensive_not_alpha",
                    "explanation": (
                        f"Factor shows negative gap in both regimes (up={up_gap:.4f}, down={down_gap:.4f}) "
                        f"but reduces drawdown. Defensive value, not alpha."
                    ),
                    "up_gap": up_gap,
                    "down_gap": down_gap,
                    "mixed_gap": mixed_gap,
                }
                continue

        # Check for all_weather_alpha: positive in both
        if up_gap > 0 and down_gap > 0:
            classifications[field] = {
                "classification": "all_weather_alpha",
                "explanation": (
                    f"Factor shows positive gap in both broad_up ({up_gap:.4f}) "
                    f"and broad_down ({down_gap:.4f}). Consistent alpha across regimes."
                ),
                "up_gap": up_gap,
                "down_gap": down_gap,
                "mixed_gap": mixed_gap,
            }
            continue

        # Check for up_only_alpha
        if up_gap > 0 and down_gap <= 0:
            classifications[field] = {
                "classification": "up_only_alpha",
                "explanation": (
                    f"Factor works in broad_up (gap={up_gap:.4f}) but fails in broad_down "
                    f"(gap={down_gap:.4f}). Offensive factor, use only in bullish markets."
                ),
                "up_gap": up_gap,
                "down_gap": down_gap,
                "mixed_gap": mixed_gap,
            }
            continue

        # Check for down_only_alpha
        if down_gap > 0 and up_gap <= 0:
            classifications[field] = {
                "classification": "down_only_alpha",
                "explanation": (
                    f"Factor works in broad_down (gap={down_gap:.4f}) but fails in broad_up "
                    f"(gap={up_gap:.4f}). Defensive factor, use only in bearish markets."
                ),
                "up_gap": up_gap,
                "down_gap": down_gap,
                "mixed_gap": mixed_gap,
            }
            continue

        # Default: regime_dependent
        classifications[field] = {
            "classification": "regime_dependent",
            "explanation": (
                f"Factor sign flips between regimes: broad_up={up_gap:.4f}, "
                f"broad_down={down_gap:.4f}. No consistent pattern."
            ),
            "up_gap": up_gap,
            "down_gap": down_gap,
            "mixed_gap": mixed_gap,
        }

    return classifications


def generate_regime_recommendations(classifications: dict) -> list[dict]:
    """Generate regime-conditional recommendations. Read-only, no production changes."""
    recs = []

    for field, info in classifications.items():
        cls = info.get("classification")
        if cls == "up_only_alpha":
            recs.append({
                "factor": field,
                "recommendation": f"Consider increasing weight of {field} in broad_up regime.",
                "regime": "broad_up",
                "action": "increase_weight",
                "production_change_allowed": False,
            })
            recs.append({
                "factor": field,
                "recommendation": f"Consider decreasing weight of {field} in broad_down regime.",
                "regime": "broad_down",
                "action": "decrease_weight",
                "production_change_allowed": False,
            })
        elif cls == "down_only_alpha":
            recs.append({
                "factor": field,
                "recommendation": f"Consider increasing weight of {field} in broad_down regime.",
                "regime": "broad_down",
                "action": "increase_weight",
                "production_change_allowed": False,
            })
            recs.append({
                "factor": field,
                "recommendation": f"Consider decreasing weight of {field} in broad_up regime.",
                "regime": "broad_up",
                "action": "decrease_weight",
                "production_change_allowed": False,
            })
        elif cls == "all_weather_alpha":
            recs.append({
                "factor": field,
                "recommendation": f"{field} shows consistent alpha across all regimes. Consider stable weight.",
                "regime": "all",
                "action": "stable_weight",
                "production_change_allowed": False,
            })
        elif cls == "defensive_not_alpha":
            recs.append({
                "factor": field,
                "recommendation": f"{field} provides defensive value (reduces drawdown) but not alpha. Keep as risk filter.",
                "regime": "all",
                "action": "keep_as_risk_filter",
                "production_change_allowed": False,
            })

    # Always add this
    recs.append({
        "factor": "all",
        "recommendation": "Do not change production weights. All recommendations are diagnostic only.",
        "regime": "all",
        "action": "no_production_change",
        "production_change_allowed": False,
    })

    return recs


# ======================================================================
# MARKDOWN REPORT
# ======================================================================

def generate_markdown(
    coverage: dict,
    regime_gaps: dict,
    classifications: dict,
    recommendations: list[dict],
    date_range: str,
) -> str:
    lines = []
    lines.append(f"# Regime-Aware Factor Behavior — {date_range}")
    lines.append("")

    # 1. Coverage
    lines.append("## 1. Data Coverage")
    lines.append("")
    lines.append(f"- Valid dates: {coverage.get('valid_dates', 0)}")
    lines.append(f"- Forward samples: {coverage.get('forward_samples', 0)}")
    lines.append("")
    for regime in REGIMES:
        rg = regime_gaps.get(regime, {})
        lines.append(f"- {regime}: n={rg.get('sample_count', 0)}")
    lines.append("")

    # 2. Per-regime factor gaps
    lines.append("## 2. Per-Regime Factor Top-Bottom Gaps")
    lines.append("")
    lines.append("| Factor | broad_up gap | broad_down gap | mixed gap | Sign Flip? |")
    lines.append("|--------|-------------|----------------|-----------|------------|")
    for field in FACTOR_FIELDS:
        up_gap = regime_gaps.get("broad_up", {}).get("factors", {}).get(field, {}).get("gap")
        down_gap = regime_gaps.get("broad_down", {}).get("factors", {}).get(field, {}).get("gap")
        mixed_gap = regime_gaps.get("mixed", {}).get("factors", {}).get(field, {}).get("gap")
        up_s = f"{up_gap:.4f}" if up_gap is not None else "N/A"
        down_s = f"{down_gap:.4f}" if down_gap is not None else "N/A"
        mixed_s = f"{mixed_gap:.4f}" if mixed_gap is not None else "N/A"
        flip = "Yes" if (up_gap is not None and down_gap is not None and
                         ((up_gap > 0 and down_gap < 0) or (up_gap < 0 and down_gap > 0))) else "No"
        lines.append(f"| {field} | {up_s} | {down_s} | {mixed_s} | {flip} |")
    lines.append("")

    # 3. Detailed per-regime analysis
    lines.append("## 3. Detailed Per-Regime Analysis")
    lines.append("")
    for regime in REGIMES:
        rg = regime_gaps.get(regime, {})
        lines.append(f"### {regime} (n={rg.get('sample_count', 0)})")
        lines.append("")
        lines.append("| Factor | High Avg | Low Avg | Gap | HR Diff | ρ | DD Diff |")
        lines.append("|--------|----------|---------|-----|---------|---|---------|")
        for field in FACTOR_FIELDS:
            f = rg.get("factors", {}).get(field, {})
            ha = f.get("high_avg_return")
            la = f.get("low_avg_return")
            g = f.get("gap")
            hr = f.get("hit_rate_diff")
            c = f.get("spearman_corr")
            dd = f.get("drawdown_diff")
            ha_s = f"{ha:.4f}" if ha is not None else "N/A"
            la_s = f"{la:.4f}" if la is not None else "N/A"
            g_s = f"{g:.4f}" if g is not None else "N/A"
            hr_s = f"{hr:.1f}" if hr is not None else "N/A"
            c_s = f"{c:.4f}" if c is not None else "N/A"
            dd_s = f"{dd:.4f}" if dd is not None else "N/A"
            lines.append(f"| {field} | {ha_s} | {la_s} | {g_s} | {hr_s} | {c_s} | {dd_s} |")
        lines.append("")

    # 4. Classification
    lines.append("## 4. Factor Regime Classification")
    lines.append("")
    lines.append("| Factor | Classification | Up Gap | Down Gap | Explanation |")
    lines.append("|--------|---------------|--------|----------|-------------|")
    for field in FACTOR_FIELDS:
        c = classifications.get(field, {})
        cls = c.get("classification", "unknown")
        ug = c.get("up_gap")
        dg = c.get("down_gap")
        ug_s = f"{ug:.4f}" if ug is not None else "N/A"
        dg_s = f"{dg:.4f}" if dg is not None else "N/A"
        expl = c.get("explanation", "")
        if len(expl) > 60:
            expl = expl[:57] + "..."
        lines.append(f"| {field} | {cls} | {ug_s} | {dg_s} | {expl} |")
    lines.append("")

    # Detailed explanations
    lines.append("### Detailed Explanations")
    lines.append("")
    for field in FACTOR_FIELDS:
        c = classifications.get(field, {})
        lines.append(f"**{field}**: {c.get('classification', 'unknown')}")
        lines.append(f"- {c.get('explanation', '')}")
        lines.append("")

    # 5. Recommendations
    lines.append("## 5. Regime-Conditional Recommendations")
    lines.append("")
    lines.append("**All recommendations are diagnostic only. production_change_allowed = false.**")
    lines.append("")
    for rec in recommendations:
        lines.append(f"- **{rec['factor']}** [{rec['regime']}]: {rec['recommendation']}")
    lines.append("")

    # 6. Production change
    lines.append("## 6. Production Change Assessment")
    lines.append("")
    lines.append("- **production_change_allowed**: `false`")
    lines.append("- All recommendations are diagnostic only.")
    lines.append("- Do not modify production weights based on this analysis.")
    lines.append("")

    return "\n".join(lines)


# ======================================================================
# MAIN
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="Regime-aware factor behavior diagnosis")
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

    print(f"  Loading records...")
    records, agg = load_per_candidate_records(aggregate_path, validation_root, candidate_root)
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

    print("  Computing regime-factor gaps...")
    regime_gaps = compute_regime_factor_gaps(records)

    print("  Classifying regime behavior...")
    classifications = classify_regime_behavior(regime_gaps)

    print("  Generating recommendations...")
    recommendations = generate_regime_recommendations(classifications)

    # Build output
    output = {
        "as_of": date_range,
        "generated_at": datetime.now().isoformat(),
        "coverage": coverage,
        "production_change_allowed": False,
        "regime_gaps": regime_gaps,
        "classifications": classifications,
        "recommendations": recommendations,
    }

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "regime_aware_factor_behavior.json"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  JSON: {json_path}")

    md = generate_markdown(coverage, regime_gaps, classifications, recommendations, date_range)
    md_path = output_dir / "regime_aware_factor_behavior.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  Markdown: {md_path}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  Regime-Aware Factor Behavior Summary")
    print(f"{'='*60}")
    print(f"  production_change_allowed: false")
    print()
    for field in FACTOR_FIELDS:
        c = classifications.get(field, {})
        print(f"  {field}: {c.get('classification', 'unknown')}")
        print(f"    up_gap={c.get('up_gap', 'N/A')}, down_gap={c.get('down_gap', 'N/A')}")


if __name__ == "__main__":
    main()
