#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shadow V5 Promotion Gate 审计脚本

验证 Regime Router Shadow Score V5 是否满足 promotion gate 条件。
不做权重调整，只输出审计结论。production_change_allowed = false。

用法:
  python scripts/audit_shadow_v5_promotion_gate.py \
    --aggregate-path reports/selection_validation/aggregate/2026-01-05_to_2026-07-08/selection_validation_aggregate.json \
    --validation-root reports/selection_validation \
    --candidate-root reports/agent_bridge \
    --output-dir reports/selection_validation/shadow_score_v5/audit/2026-01-05_to_2026-07-08
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
from theme_sector_radar.scoring.regime_router_shadow_score_v5 import compute_regime_router_shadow_score_v5
from theme_sector_radar.scoring.risk_decomposition import decompose_trade_risk

REGIMES = ["broad_up", "broad_down", "mixed"]
ROLLING_WINDOWS = [20, 40, 60]


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
    """Load records and compute V5 scores."""
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

            # Compute regime router shadow score V5
            v5_result = compute_regime_router_shadow_score_v5(cand, regime=market_regime)

            boards = cand.get("boards", [])
            sector = boards[0] if boards else "unknown"

            records.append({
                "date": date,
                "code": code,
                "name": ps.get("name", ""),
                "market_regime": market_regime,
                "sector": sector,
                "next_return_pct": ps.get("next_return_pct"),
                "data_available": ps.get("data_available", False),
                "decision_score": ps.get("decision_score") or cand.get("decision_score"),
                "regime_router_shadow_score_v5": v5_result["regime_router_shadow_score_v5"],
            })

    return records, agg


# ======================================================================
# ANALYSIS FUNCTIONS
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


def compute_window_stats(records: list[dict]) -> dict:
    """Compute V5 stats for a set of records."""
    valid = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]
    if len(valid) < 10:
        return {"sample_count": len(valid), "error": "insufficient_samples"}

    groups = _split_by_quantile(valid, "regime_router_shadow_score_v5", 3)
    high_items = groups.get("high", [])
    low_items = groups.get("low", [])

    high_ret = [_safe_float(x.get("next_return_pct")) for x in high_items]
    low_ret = [_safe_float(x.get("next_return_pct")) for x in low_items]

    high_avg = _avg(high_ret)
    low_avg = _avg(low_ret)
    v5_gap = round(high_avg - low_avg, 4) if high_avg is not None and low_avg is not None else None

    # Production gap
    prod_groups = _split_by_quantile(valid, "decision_score", 3)
    prod_high = prod_groups.get("high", [])
    prod_low = prod_groups.get("low", [])
    prod_high_ret = [_safe_float(x.get("next_return_pct")) for x in prod_high]
    prod_low_ret = [_safe_float(x.get("next_return_pct")) for x in prod_low]
    prod_high_avg = _avg(prod_high_ret)
    prod_low_avg = _avg(prod_low_ret)
    prod_gap = round(prod_high_avg - prod_low_avg, 4) if prod_high_avg is not None and prod_low_avg is not None else None

    return {
        "sample_count": len(valid),
        "v5_gap": v5_gap,
        "production_gap": prod_gap,
    }


def compute_rolling_windows(records: list[dict]) -> dict:
    """Compute rolling window statistics."""
    dates = sorted(set(r["date"] for r in records))
    results = {}

    for window in ROLLING_WINDOWS:
        window_results = []
        if len(dates) < window:
            results[f"{window}d_rolling"] = {"available": False}
            continue

        for i in range(window, len(dates) + 1):
            window_dates = dates[i - window:i]
            window_records = [r for r in records if r["date"] in window_dates]
            stats = compute_window_stats(window_records)
            stats["start_date"] = window_dates[0]
            stats["end_date"] = window_dates[-1]
            window_results.append(stats)

        passed_count = sum(1 for w in window_results if w.get("v5_gap") is not None and w["v5_gap"] > 0)
        total_count = len(window_results)

        results[f"{window}d_rolling"] = {
            "available": True,
            "total_windows": total_count,
            "passed_windows": passed_count,
            "positive_window_share": round(passed_count / max(1, total_count) * 100, 1),
        }

    return results


def compute_outlier_contribution(records: list[dict]) -> dict:
    """Analyze outlier contributions."""
    valid = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]
    if len(valid) < 10:
        return {"error": "insufficient_samples"}

    by_date = defaultdict(list)
    for r in valid:
        by_date[r["date"]].append(r)

    date_contributions = {}
    for date, items in by_date.items():
        if len(items) < 3:
            continue
        groups = _split_by_quantile(items, "regime_router_shadow_score_v5", 3)
        high_ret = [_safe_float(x.get("next_return_pct")) for x in groups.get("high", [])]
        low_ret = [_safe_float(x.get("next_return_pct")) for x in groups.get("low", [])]
        high_avg = _avg(high_ret)
        low_avg = _avg(low_ret)
        if high_avg is not None and low_avg is not None:
            date_contributions[date] = round(high_avg - low_avg, 4)

    total_contribution = sum(date_contributions.values())
    max_date_share = 0
    if total_contribution != 0:
        max_date_share = max(abs(c) / abs(total_contribution) * 100 for c in date_contributions.values())

    # Stock contribution
    by_stock = defaultdict(list)
    for r in valid:
        by_stock[r["code"]].append(r)

    stock_returns = {}
    for code, items in by_stock.items():
        rets = [_safe_float(x.get("next_return_pct")) for x in items]
        stock_returns[code] = abs(_avg(rets) or 0)

    total_stock_return = sum(stock_returns.values())
    max_stock_share = 0
    if total_stock_return > 0:
        max_stock_share = max(v / total_stock_return * 100 for v in stock_returns.values())

    # Sector contribution
    by_sector = defaultdict(list)
    for r in valid:
        by_sector[r.get("sector", "unknown")].append(r)

    sector_returns = {}
    for sector, items in by_sector.items():
        rets = [_safe_float(x.get("next_return_pct")) for x in items]
        sector_returns[sector] = abs(_avg(rets) or 0)

    total_sector_return = sum(sector_returns.values())
    max_sector_share = 0
    if total_sector_return > 0:
        max_sector_share = max(v / total_sector_return * 100 for v in sector_returns.values())

    return {
        "max_single_date_contribution_share": round(max_date_share, 2),
        "max_single_stock_contribution_share": round(max_stock_share, 2),
        "max_single_sector_contribution_share": round(max_sector_share, 2),
    }


def compute_regime_stability(records: list[dict]) -> dict:
    """Check V5 stability within each regime."""
    valid = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]

    regime_results = {}
    for regime in REGIMES:
        regime_records = [r for r in valid if r.get("market_regime") == regime]
        if len(regime_records) < 10:
            regime_results[regime] = {"sample_count": len(regime_records), "error": "insufficient_samples"}
            continue

        groups = _split_by_quantile(regime_records, "regime_router_shadow_score_v5", 3)
        high_items = groups.get("high", [])
        low_items = groups.get("low", [])

        high_ret = [_safe_float(x.get("next_return_pct")) for x in high_items]
        low_ret = [_safe_float(x.get("next_return_pct")) for x in low_items]

        high_avg = _avg(high_ret)
        low_avg = _avg(low_ret)
        gap = round(high_avg - low_avg, 4) if high_avg is not None and low_avg is not None else None

        regime_results[regime] = {
            "sample_count": len(regime_records),
            "v5_gap": gap,
            "gap_positive": gap is not None and gap > 0,
        }

    positive_regimes = sum(1 for r in regime_results.values() if r.get("gap_positive"))

    return {
        "regimes": regime_results,
        "positive_regime_count": positive_regimes,
    }


def compute_bucket_monotonicity(records: list[dict]) -> dict:
    """Check bucket monotonicity."""
    valid = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]
    if len(valid) < 20:
        return {"error": "insufficient_samples", "monotonicity": "inconclusive"}

    buckets = {"60-80": [], "40-60": [], "<40": []}
    for r in valid:
        score = _safe_float(r.get("regime_router_shadow_score_v5"))
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
# PROMOTION GATE
# ======================================================================

def evaluate_promotion_gate(
    overall_stats: dict,
    rolling_results: dict,
    outlier_analysis: dict,
    regime_stability: dict,
    bucket_monotonicity: dict,
) -> dict:
    """Evaluate promotion gate for V5."""
    passed_checks = []
    failed_checks = []
    reasons = []

    # Check 1: 120d v5_gap > +1.0pp
    v5_gap = overall_stats.get("v5_gap")
    if v5_gap is not None and v5_gap > 1.0:
        passed_checks.append("120d_v5_gap_positive")
    else:
        failed_checks.append("120d_v5_gap_not_positive")
        reasons.append(f"120d v5_gap={v5_gap} (need > 1.0)")

    # Check 2: 60d rolling positive share >= 60%
    rolling_60d = rolling_results.get("60d_rolling", {})
    positive_share_60d = rolling_60d.get("positive_window_share", 0)
    if positive_share_60d >= 60:
        passed_checks.append("60d_rolling_positive_share")
    else:
        failed_checks.append("60d_rolling_positive_share_low")
        reasons.append(f"60d rolling positive share={positive_share_60d}% (need >= 60%)")

    # Check 3: max_single_date_contribution_share <= 35%
    max_date_share = outlier_analysis.get("max_single_date_contribution_share", 100)
    if max_date_share <= 35:
        passed_checks.append("no_single_date_dominance")
    else:
        failed_checks.append("single_date_dominance")
        reasons.append(f"max single date share={max_date_share}% (need <= 35%)")

    # Check 4: max_single_stock_contribution_share <= 20%
    max_stock_share = outlier_analysis.get("max_single_stock_contribution_share", 100)
    if max_stock_share <= 20:
        passed_checks.append("no_single_stock_dominance")
    else:
        failed_checks.append("single_stock_dominance")
        reasons.append(f"max single stock share={max_stock_share}% (need <= 20%)")

    # Check 5: max_single_sector_contribution_share <= 40%
    max_sector_share = outlier_analysis.get("max_single_sector_contribution_share", 100)
    if max_sector_share <= 40:
        passed_checks.append("no_single_sector_dominance")
    else:
        failed_checks.append("single_sector_dominance")
        reasons.append(f"max single sector share={max_sector_share}% (need <= 40%)")

    # Check 6: at least two regimes have positive v5_gap
    positive_regimes = regime_stability.get("positive_regime_count", 0)
    if positive_regimes >= 2:
        passed_checks.append("multiple_regimes_positive")
    else:
        failed_checks.append("regime_dependency")
        reasons.append(f"only {positive_regimes} regime(s) with positive gap (need >= 2)")

    # Check 7: bucket monotonicity not clearly negative
    monotonicity = bucket_monotonicity.get("monotonicity", "inconclusive")
    if monotonicity != "negative":
        passed_checks.append("bucket_monotonicity_ok")
    else:
        failed_checks.append("bucket_monotonicity_negative")
        reasons.append("bucket monotonicity is clearly negative")

    # Determine status
    if len(failed_checks) == 0:
        status = "review_ready"
    elif len(failed_checks) <= 2:
        status = "watch"
    else:
        status = "blocked"

    return {
        "status": status,
        "production_change_allowed": False,
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "reasons": reasons,
    }


# ======================================================================
# MARKDOWN REPORT
# ======================================================================

def generate_markdown(
    coverage: dict,
    overall_stats: dict,
    rolling_results: dict,
    outlier_analysis: dict,
    regime_stability: dict,
    bucket_monotonicity: dict,
    promotion_gate: dict,
    date_range: str,
) -> str:
    lines = []
    lines.append(f"# Shadow V5 Promotion Gate Audit — {date_range}")
    lines.append("")

    # 1. Coverage
    lines.append("## 1. Data Coverage")
    lines.append("")
    lines.append(f"- Valid dates: {coverage.get('valid_dates', 0)}")
    lines.append(f"- Forward samples: {coverage.get('forward_samples', 0)}")
    lines.append("")

    # 2. Overall Stats
    lines.append("## 2. Overall V5 Performance")
    lines.append("")
    lines.append(f"- V5 gap (120d): {overall_stats.get('v5_gap', 'N/A')}")
    lines.append(f"- Production gap: {overall_stats.get('production_gap', 'N/A')}")
    lines.append("")

    # 3. Rolling Windows
    lines.append("## 3. Rolling Walk-Forward Validation")
    lines.append("")
    for window_key in ["20d_rolling", "40d_rolling", "60d_rolling"]:
        wr = rolling_results.get(window_key, {})
        lines.append(f"### {window_key}")
        lines.append("")
        if not wr.get("available"):
            lines.append("- Not available")
        else:
            lines.append(f"- Total windows: {wr.get('total_windows', 0)}")
            lines.append(f"- Passed windows: {wr.get('passed_windows', 0)}")
            lines.append(f"- Positive window share: {wr.get('positive_window_share', 0)}%")
        lines.append("")

    # 4. Outlier Contribution
    lines.append("## 4. Outlier Contribution")
    lines.append("")
    lines.append(f"- Max single date share: {outlier_analysis.get('max_single_date_contribution_share', 'N/A')}%")
    lines.append(f"- Max single stock share: {outlier_analysis.get('max_single_stock_contribution_share', 'N/A')}%")
    lines.append(f"- Max single sector share: {outlier_analysis.get('max_single_sector_contribution_share', 'N/A')}%")
    lines.append("")

    # 5. Regime Stability
    lines.append("## 5. Regime Stability")
    lines.append("")
    lines.append(f"- Positive regimes: {regime_stability.get('positive_regime_count', 0)}")
    lines.append("")
    for regime in REGIMES:
        rd = regime_stability.get("regimes", {}).get(regime, {})
        gap = rd.get("v5_gap")
        gap_mark = "✅" if rd.get("gap_positive") else "❌"
        lines.append(f"- {regime}: {gap_mark} gap={gap} (n={rd.get('sample_count', 0)})")
    lines.append("")

    # 6. Bucket Monotonicity
    lines.append("## 6. Bucket Monotonicity")
    lines.append("")
    lines.append(f"- Monotonicity: {bucket_monotonicity.get('monotonicity', 'inconclusive')}")
    lines.append("")
    for bucket, stats in bucket_monotonicity.get("bucket_stats", {}).items():
        lines.append(f"- {bucket}: count={stats.get('count', 0)}, avg_return={stats.get('avg_return', 'N/A')}")
    lines.append("")

    # 7. Promotion Gate
    lines.append("## 7. Promotion Gate")
    lines.append("")
    pg = promotion_gate
    lines.append(f"- **Status**: `{pg.get('status', 'unknown')}`")
    lines.append(f"- **production_change_allowed**: `false`")
    lines.append("")
    lines.append("Passed checks:")
    for check in pg.get("passed_checks", []):
        lines.append(f"- ✅ {check}")
    lines.append("")
    lines.append("Failed checks:")
    for check in pg.get("failed_checks", []):
        lines.append(f"- ❌ {check}")
    lines.append("")
    if pg.get("reasons"):
        lines.append("Reasons:")
        for reason in pg["reasons"]:
            lines.append(f"- {reason}")
    lines.append("")

    return "\n".join(lines)


# ======================================================================
# MAIN
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="Audit shadow V5 promotion gate")
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

    print(f"  Loading and computing V5 scores...")
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

    print("  Computing overall stats...")
    overall_stats = compute_window_stats(records)

    print("  Computing rolling windows...")
    rolling_results = compute_rolling_windows(records)

    print("  Computing outlier contributions...")
    outlier_analysis = compute_outlier_contribution(records)

    print("  Computing regime stability...")
    regime_stability = compute_regime_stability(records)

    print("  Computing bucket monotonicity...")
    bucket_monotonicity = compute_bucket_monotonicity(records)

    print("  Evaluating promotion gate...")
    promotion_gate = evaluate_promotion_gate(
        overall_stats, rolling_results, outlier_analysis,
        regime_stability, bucket_monotonicity,
    )

    # Build output
    output = {
        "as_of": date_range,
        "generated_at": datetime.now().isoformat(),
        "coverage": coverage,
        "production_change_allowed": False,
        "overall_stats": overall_stats,
        "rolling_validation": rolling_results,
        "outlier_contribution": outlier_analysis,
        "regime_stability": regime_stability,
        "bucket_monotonicity": bucket_monotonicity,
        "promotion_gate": promotion_gate,
    }

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "shadow_v5_promotion_gate.json"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  JSON: {json_path}")

    md = generate_markdown(
        coverage, overall_stats, rolling_results,
        outlier_analysis, regime_stability, bucket_monotonicity,
        promotion_gate, date_range,
    )
    md_path = output_dir / "shadow_v5_promotion_gate.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  Markdown: {md_path}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  Shadow V5 Promotion Gate Summary")
    print(f"{'='*60}")
    print(f"  Status: {promotion_gate.get('status')}")
    print(f"  production_change_allowed: false")
    print(f"  Positive regimes: {regime_stability.get('positive_regime_count')}")
    print(f"  V5 gap (120d): {overall_stats.get('v5_gap')}")


if __name__ == "__main__":
    main()
