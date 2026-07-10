#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stock_short_score_v2 质量诊断脚本

诊断校准后的 stock_short_score_v2 分布质量。
不做权重调整，只输出诊断结论。

用法:
  python scripts/diagnose_stock_short_score_v2_quality.py \
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
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.scoring.stock_short_score_v2 import compute_stock_short_score_v2
from theme_sector_radar.scoring.stock_short_score import compute_stock_short_score

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

def load_and_compute_v2(
    aggregate_path: Path,
    validation_root: Path,
    candidate_root: Path,
) -> tuple[list[dict], dict]:
    """Load records and compute stock_short_score_v2 for each."""
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

            # Also compute v1 for comparison
            short_v1_result = compute_stock_short_score(cand)

            records.append({
                "date": date,
                "code": code,
                "name": ps.get("name", ""),
                "market_regime": market_regime,
                "next_return_pct": ps.get("next_return_pct"),
                "data_available": ps.get("data_available", False),
                "stock_short_score_v1": short_v1_result.get("stock_short_score", 0),
                "stock_short_score_v2": short_v2_result.get("stock_short_score_v2", 0),
                "stock_short_breakdown_v2": short_v2_result.get("stock_short_breakdown_v2", {}),
                "stock_short_v2_tags": short_v2_result.get("stock_short_v2_tags", []),
            })

    return records, agg


# ======================================================================
# DISTRIBUTION ANALYSIS
# ======================================================================

def compute_distribution(scores: list[float]) -> dict:
    clean = [s for s in scores if s is not None]
    if not clean:
        return {"sample_count": 0, "min": None, "max": None, "mean": None,
                "spread": None, "unique_count": 0, "std": None,
                "bucket_distribution": {}, "quality_flags": ["excessive_missing"]}

    n = len(clean)
    mn, mx = min(clean), max(clean)
    mean = sum(clean) / n
    var = sum((v - mean) ** 2 for v in clean) / max(1, n - 1)
    std = math.sqrt(var)
    unique = len(set(round(s, 0) for s in clean))
    spread = round(mx - mn, 2)

    # Buckets: 0-20, 20-40, 40-60, 60-80, 80-100
    buckets = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
    for s in clean:
        if s < 20:
            buckets["0-20"] += 1
        elif s < 40:
            buckets["20-40"] += 1
        elif s < 60:
            buckets["40-60"] += 1
        elif s < 80:
            buckets["60-80"] += 1
        else:
            buckets["80-100"] += 1

    flags = []
    if unique <= 1:
        flags.append("constant_value")
    if spread < 10:
        flags.append("low_spread")
    if unique <= 3 and n > 10:
        flags.append("low_unique_count")
    if spread >= 30:
        flags.append("spread_target_met")

    return {
        "sample_count": n, "min": round(mn, 2), "max": round(mx, 2),
        "mean": round(mean, 2), "std": round(std, 2),
        "unique_count": unique, "spread": spread,
        "bucket_distribution": buckets, "quality_flags": flags,
    }


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


def compute_factor_performance(records: list[dict], field: str, label: str = "all") -> dict:
    """Compute top-bottom gap for a factor."""
    valid = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]
    if len(valid) < 10:
        return {"label": label, "sample_count": len(valid), "error": "insufficient_samples"}

    groups = _split_by_quantile(valid, field, 3)
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
        for x in valid
    ]
    aligned = [(v, r) for v, r in aligned if v is not None and r is not None]
    corr = None
    if len(aligned) >= 5:
        corr = spearman_correlation([a[0] for a in aligned], [a[1] for a in aligned])

    return {
        "label": label,
        "sample_count": len(valid),
        "top5_count": len(high_items),
        "bottom10_count": len(low_items),
        "top5_avg_return": high_avg,
        "bottom10_avg_return": low_avg,
        "gap": gap,
        "top5_hit_rate": high_hr,
        "bottom10_hit_rate": low_hr,
        "hit_rate_diff": hr_diff,
        "spearman_corr": corr,
    }


def compute_regime_performance(records: list[dict], field: str) -> dict:
    """Compute performance per regime."""
    results = {}
    for regime in REGIMES:
        regime_records = [r for r in records if r.get("market_regime") == regime]
        results[regime] = compute_factor_performance(regime_records, field, regime)
    return results


# ======================================================================
# COMPARISON
# ======================================================================

def compute_v1_v2_comparison(records: list[dict]) -> dict:
    """Compare v1 and v2 scores."""
    v1_perf = compute_factor_performance(records, "stock_short_score_v1", "v1")
    v2_perf = compute_factor_performance(records, "stock_short_score_v2", "v2")

    v1_regime = compute_regime_performance(records, "stock_short_score_v1")
    v2_regime = compute_regime_performance(records, "stock_short_score_v2")

    return {
        "v1": {"overall": v1_perf, "regime": v1_regime},
        "v2": {"overall": v2_perf, "regime": v2_regime},
    }


# ======================================================================
# MARKDOWN REPORT
# ======================================================================

def generate_markdown(
    coverage: dict,
    v2_dist: dict,
    v1_dist: dict,
    v2_perf: dict,
    comparison: dict,
    date_range: str,
) -> str:
    lines = []
    lines.append(f"# Stock Short Score V2 Quality — {date_range}")
    lines.append("")

    # 1. Coverage
    lines.append("## 1. Data Coverage")
    lines.append("")
    lines.append(f"- Valid dates: {coverage.get('valid_dates', 0)}")
    lines.append(f"- Forward samples: {coverage.get('forward_samples', 0)}")
    lines.append("")

    # 2. V2 Distribution
    lines.append("## 2. Stock Short Score V2 Distribution")
    lines.append("")
    lines.append(f"- Min: {v2_dist.get('min', 'N/A')}")
    lines.append(f"- Max: {v2_dist.get('max', 'N/A')}")
    lines.append(f"- Mean: {v2_dist.get('mean', 'N/A')}")
    lines.append(f"- Std: {v2_dist.get('std', 'N/A')}")
    lines.append(f"- Spread: {v2_dist.get('spread', 'N/A')}")
    lines.append(f"- Unique count: {v2_dist.get('unique_count', 'N/A')}")
    lines.append(f"- Quality flags: {', '.join(v2_dist.get('quality_flags', [])) or 'none'}")
    lines.append("")

    lines.append("### Bucket Distribution")
    lines.append("")
    lines.append("| Bucket | Count | Pct |")
    lines.append("|--------|-------|-----|")
    buckets = v2_dist.get("bucket_distribution", {})
    total = v2_dist.get("sample_count", 1)
    for bucket, count in buckets.items():
        pct = round(count / total * 100, 1) if total > 0 else 0
        lines.append(f"| {bucket} | {count} | {pct}% |")
    lines.append("")

    # 3. V1 Distribution (comparison)
    lines.append("## 3. Stock Short Score V1 Distribution (Comparison)")
    lines.append("")
    lines.append(f"- Min: {v1_dist.get('min', 'N/A')}")
    lines.append(f"- Max: {v1_dist.get('max', 'N/A')}")
    lines.append(f"- Mean: {v1_dist.get('mean', 'N/A')}")
    lines.append(f"- Spread: {v1_dist.get('spread', 'N/A')}")
    lines.append(f"- Unique count: {v1_dist.get('unique_count', 'N/A')}")
    lines.append("")

    # 4. V2 Performance
    lines.append("## 4. V2 Factor Performance")
    lines.append("")
    lines.append(_performance_table(v2_perf))

    # 5. Regime Performance
    lines.append("## 5. V2 Regime Performance")
    lines.append("")
    for regime in REGIMES:
        regime_data = v2_perf.get("regime", {}).get(regime, {})
        lines.append(f"### {regime}")
        lines.append("")
        lines.append(_performance_table(regime_data))
        lines.append("")

    # 6. V1 vs V2 Comparison
    lines.append("## 6. V1 vs V2 Comparison")
    lines.append("")
    lines.append("| Metric | V1 | V2 |")
    lines.append("|--------|----|----|")
    v1_overall = comparison.get("v1", {}).get("overall", {})
    v2_overall = comparison.get("v2", {}).get("overall", {})
    lines.append(f"| Gap | {v1_overall.get('gap', 'N/A')} | {v2_overall.get('gap', 'N/A')} |")
    lines.append(f"| Hit Rate Diff | {v1_overall.get('hit_rate_diff', 'N/A')} | {v2_overall.get('hit_rate_diff', 'N/A')} |")
    lines.append(f"| Spearman ρ | {v1_overall.get('spearman_corr', 'N/A')} | {v2_overall.get('spearman_corr', 'N/A')} |")
    lines.append("")

    # 7. Spread Target
    lines.append("## 7. Spread Target Assessment")
    lines.append("")
    spread = v2_dist.get("spread", 0)
    target_met = spread >= 30
    lines.append(f"- Current spread: {spread}")
    lines.append(f"- Target: >= 30")
    lines.append(f"- **Target met**: `{str(target_met).lower()}`")
    lines.append("")

    return "\n".join(lines)


def _performance_table(data: dict) -> str:
    lines = []
    n = data.get("sample_count", 0)
    lines.append(f"Sample count: {n}")
    lines.append("")
    if "error" in data:
        lines.append(f"- {data['error']}")
        return "\n".join(lines)
    lines.append(f"- Top5 avg return: {data.get('top5_avg_return', 'N/A')}")
    lines.append(f"- Bottom10 avg return: {data.get('bottom10_avg_return', 'N/A')}")
    lines.append(f"- Gap: {data.get('gap', 'N/A')}")
    lines.append(f"- Hit rate diff: {data.get('hit_rate_diff', 'N/A')}")
    lines.append(f"- Spearman ρ: {data.get('spearman_corr', 'N/A')}")
    return "\n".join(lines)


# ======================================================================
# MAIN
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="Diagnose stock_short_score_v2 quality")
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

    print(f"  Loading and computing v2 scores...")
    records, agg = load_and_compute_v2(aggregate_path, validation_root, candidate_root)
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

    # Compute distributions
    print("  Computing distributions...")
    v2_scores = [r.get("stock_short_score_v2") for r in valid]
    v1_scores = [r.get("stock_short_score_v1") for r in valid]
    v2_dist = compute_distribution(v2_scores)
    v1_dist = compute_distribution(v1_scores)

    # Compute performance
    print("  Computing v2 performance...")
    v2_perf = compute_factor_performance(valid, "stock_short_score_v2", "v2")
    v2_perf["regime"] = compute_regime_performance(valid, "stock_short_score_v2")

    # V1 vs V2 comparison
    print("  Computing v1 vs v2 comparison...")
    comparison = compute_v1_v2_comparison(valid)

    # Build output
    output = {
        "as_of": date_range,
        "generated_at": datetime.now().isoformat(),
        "coverage": coverage,
        "v2_distribution": v2_dist,
        "v1_distribution": v1_dist,
        "v2_performance": v2_perf,
        "comparison": comparison,
        "spread_target_met": v2_dist.get("spread", 0) >= 30,
    }

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "stock_short_score_v2_quality.json"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  JSON: {json_path}")

    md = generate_markdown(coverage, v2_dist, v1_dist, v2_perf, comparison, date_range)
    md_path = output_dir / "stock_short_score_v2_quality.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  Markdown: {md_path}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  Stock Short Score V2 Quality Summary")
    print(f"{'='*60}")
    print(f"  V2: min={v2_dist.get('min')}, max={v2_dist.get('max')}, spread={v2_dist.get('spread')}, unique={v2_dist.get('unique_count')}")
    print(f"  V1: min={v1_dist.get('min')}, max={v1_dist.get('max')}, spread={v1_dist.get('spread')}, unique={v1_dist.get('unique_count')}")
    print(f"  Spread target (>=30): {v2_dist.get('spread', 0) >= 30}")
    print(f"  V2 gap: {v2_perf.get('gap', 'N/A')}")


if __name__ == "__main__":
    main()
