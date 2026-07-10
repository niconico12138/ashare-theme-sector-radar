#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
候选因子质量诊断脚本

分析 top30_candidates.json 中各评分因子的分布、区分度和量纲问题。
同步检查 aihf_request.json 的 trend/burst 分布。
含 spread 警告、bucket 分布、top/bottom 分离度诊断。

用法:
  python scripts/analyze_candidate_factor_quality.py \
    --candidate-path reports/agent_bridge/2026-07-07/top30_candidates.json \
    --request-path reports/agent_bridge/2026-07-07/aihf_request.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NUMERIC_FIELDS = [
    "trend_score",
    "burst_score",
    "stock_short_score",
    "stock_trend_score",
    "sector_leader_score",
    "risk_penalty_score",
    "decision_score",
]

# Spread warning thresholds per field
SPREAD_THRESHOLDS = {
    "stock_short_score": 20,
    "risk_penalty_score": 15,
    "decision_score": 25,
    "stock_trend_score": 20,
    "sector_leader_score": 30,
}


def _compute_stats(values: list[float]) -> dict:
    """Compute min/max/mean/std/unique_count/missing_count for a list of values."""
    missing = sum(1 for v in values if v is None)
    clean = [v for v in values if v is not None]
    if not clean:
        return {
            "min": None, "max": None, "mean": None, "std": None,
            "spread": None, "unique_count": 0, "missing_count": missing, "count": 0,
        }
    n = len(clean)
    mn = min(clean)
    mx = max(clean)
    mean = sum(clean) / n
    variance = sum((v - mean) ** 2 for v in clean) / max(1, n - 1)
    std = math.sqrt(variance)
    unique = len(set(round(v, 4) for v in clean))
    spread = round(mx - mn, 4)
    return {
        "min": round(mn, 4),
        "max": round(mx, 4),
        "mean": round(mean, 4),
        "std": round(std, 4),
        "spread": spread,
        "unique_count": unique,
        "missing_count": missing,
        "count": n,
    }


def _bucket_distribution(values: list[float]) -> dict:
    """Compute bucket distribution: <40, 40-60, 60-80, >=80."""
    buckets = {"<40": 0, "40-60": 0, "60-80": 0, ">=80": 0}
    for v in values:
        if v < 40:
            buckets["<40"] += 1
        elif v < 60:
            buckets["40-60"] += 1
        elif v < 80:
            buckets["60-80"] += 1
        else:
            buckets[">=80"] += 1
    return buckets


def _top_bottom_separation(candidates: list[dict], field: str = "decision_score") -> dict:
    """Compute top5 vs bottom10 mean separation for a field."""
    vals = [(c.get(field, 0), c.get("code", "?")) for c in candidates]
    vals.sort(key=lambda x: x[0], reverse=True)

    top5 = [v[0] for v in vals[:5]] if len(vals) >= 5 else [v[0] for v in vals]
    bottom10 = [v[0] for v in vals[-10:]] if len(vals) >= 10 else [v[0] for v in vals]

    top5_mean = sum(top5) / len(top5) if top5 else 0
    bottom10_mean = sum(bottom10) / len(bottom10) if bottom10 else 0

    return {
        "field": field,
        "top5_mean": round(top5_mean, 4),
        "top5_codes": [v[1] for v in vals[:5]],
        "bottom10_mean": round(bottom10_mean, 4),
        "bottom10_codes": [v[1] for v in vals[-10:]],
        "separation": round(top5_mean - bottom10_mean, 4),
    }


def analyze_candidates(candidates: list[dict]) -> dict:
    """Analyze factor quality for a list of candidates."""
    report = {"fields": {}, "warnings": []}

    for field in NUMERIC_FIELDS:
        values = [c.get(field) for c in candidates]
        stats = _compute_stats([v for v in values if v is not None])

        # Detect issues
        issues = []
        if stats["unique_count"] is not None and stats["unique_count"] <= 2:
            issues.append("low_discrimination")
            report["warnings"].append(f"{field}: unique_count={stats['unique_count']} (low discrimination)")

        if stats["max"] is not None and stats["max"] <= 1.5 and stats["max"] > 0:
            issues.append("scale_suspect_0_1")
            report["warnings"].append(f"{field}: max={stats['max']} (suspected 0-1 scale)")

        # Spread warning
        spread_threshold = SPREAD_THRESHOLDS.get(field)
        if spread_threshold is not None and stats["spread"] is not None:
            if stats["spread"] < spread_threshold:
                issues.append("low_spread")
                report["warnings"].append(
                    f"{field}: spread={stats['spread']:.2f} < {spread_threshold} (narrow distribution)"
                )

        stats["issues"] = issues
        stats["bucket_distribution"] = _bucket_distribution(
            [v for v in values if v is not None]
        )
        report["fields"][field] = stats

    # Check trade_eligibility distribution
    elig_values = [c.get("trade_eligibility", "unknown") for c in candidates]
    elig_dist = {}
    for v in elig_values:
        elig_dist[v] = elig_dist.get(v, 0) + 1

    report["trade_eligibility"] = {
        "distribution": elig_dist,
        "unique_count": len(elig_dist),
    }
    if len(elig_dist) <= 1:
        report["warnings"].append(
            f"trade_eligibility: only {list(elig_dist.keys())} (no risk stratification)"
        )

    # Check risk_tags distribution
    all_tags = []
    for c in candidates:
        all_tags.extend(c.get("risk_tags", []))
    tag_dist = {}
    for t in all_tags:
        tag_dist[t] = tag_dist.get(t, 0) + 1
    report["risk_tags_distribution"] = dict(sorted(tag_dist.items(), key=lambda x: -x[1]))

    # Top/bottom separation for key fields
    report["separations"] = {}
    for field in ["decision_score", "stock_short_score", "stock_trend_score"]:
        sep = _top_bottom_separation(candidates, field)
        report["separations"][field] = sep
        if sep["separation"] < 10 and field == "decision_score":
            report["warnings"].append(
                f"decision_score: top5_mean={sep['top5_mean']:.1f} - bottom10_mean={sep['bottom10_mean']:.1f} "
                f"= {sep['separation']:.1f} (separation < 10)"
            )

    return report


def analyze_aihf_request(request: dict) -> dict:
    """Analyze aihf_request.json for trend/burst split."""
    stocks = request.get("stocks", [])
    trend_count = sum(1 for s in stocks if s.get("source_pool") in ("trend", "both"))
    burst_count = sum(1 for s in stocks if s.get("source_pool") == "burst")

    result = {
        "total_stocks": len(stocks),
        "trend_count": trend_count,
        "burst_count": burst_count,
        "balanced": trend_count == burst_count,
    }

    if not result["balanced"]:
        result["warning"] = f"trend={trend_count}, burst={burst_count} (not 5/5)"

    # Check new fields present
    required_fields = [
        "stock_short_score", "stock_trend_score", "sector_leader_score",
        "decision_score", "trade_eligibility", "risk_tags",
    ]
    missing_fields = []
    for f in required_fields:
        present = sum(1 for s in stocks if f in s)
        if present < len(stocks):
            missing_fields.append(f)

    result["new_fields_present"] = len(missing_fields) == 0
    result["missing_new_fields"] = missing_fields

    return result


def generate_markdown(candidate_report: dict, aihf_report: dict, date: str) -> str:
    """Generate markdown report."""
    lines = []
    lines.append(f"# 候选因子质量诊断报告")
    lines.append(f"")
    lines.append(f"**日期**: {date}")
    lines.append(f"")

    # Warnings
    warnings = candidate_report.get("warnings", [])
    if warnings:
        lines.append(f"## ⚠️ 警告")
        lines.append(f"")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append(f"")
    else:
        lines.append(f"## ✅ 无警告")
        lines.append(f"")

    # Numeric field stats with spread and buckets
    lines.append(f"## 数值因子统计")
    lines.append(f"")
    lines.append(f"| {'字段':<25} {'min':>8} {'max':>8} {'spread':>8} {'mean':>8} {'std':>8} {'unique':>7} {'问题'} |")
    lines.append(f"|{'─'*27}|{'─'*10}|{'─'*10}|{'─'*10}|{'─'*10}|{'─'*10}|{'─'*9}|{'─'*20}|")

    for field in NUMERIC_FIELDS:
        stats = candidate_report.get("fields", {}).get(field, {})
        issues = stats.get("issues", [])
        issue_str = ", ".join(issues) if issues else "—"
        min_v = f"{stats['min']:.2f}" if stats.get("min") is not None else "N/A"
        max_v = f"{stats['max']:.2f}" if stats.get("max") is not None else "N/A"
        spread_v = f"{stats['spread']:.2f}" if stats.get("spread") is not None else "N/A"
        mean_v = f"{stats['mean']:.2f}" if stats.get("mean") is not None else "N/A"
        std_v = f"{stats['std']:.2f}" if stats.get("std") is not None else "N/A"
        unique_v = str(stats.get("unique_count", "N/A"))
        lines.append(f"| {field:<25} {min_v:>8} {max_v:>8} {spread_v:>8} {mean_v:>8} {std_v:>8} {unique_v:>7} {issue_str} |")
    lines.append(f"")

    # Bucket distributions
    lines.append(f"## Bucket 分布")
    lines.append(f"")
    lines.append(f"| {'字段':<25} {'<40':>6} {'40-60':>6} {'60-80':>6} {'>=80':>6} |")
    lines.append(f"|{'─'*27}|{'─'*8}|{'─'*8}|{'─'*8}|{'─'*8}|")
    for field in ["stock_short_score", "stock_trend_score", "sector_leader_score", "decision_score"]:
        stats = candidate_report.get("fields", {}).get(field, {})
        buckets = stats.get("bucket_distribution", {})
        lines.append(f"| {field:<25} {buckets.get('<40',0):>6} {buckets.get('40-60',0):>6} {buckets.get('60-80',0):>6} {buckets.get('>=80',0):>6} |")
    lines.append(f"")

    # Top/bottom separation
    seps = candidate_report.get("separations", {})
    if seps:
        lines.append(f"## Top/Bottom 分离度")
        lines.append(f"")
        for field, sep in seps.items():
            lines.append(f"- **{field}**: top5_mean={sep['top5_mean']:.1f}, bottom10_mean={sep['bottom10_mean']:.1f}, separation={sep['separation']:.1f}")
        lines.append(f"")

    # Trade eligibility
    elig = candidate_report.get("trade_eligibility", {})
    lines.append(f"## 交易分类分布")
    lines.append(f"")
    for k, v in sorted(elig.get("distribution", {}).items()):
        lines.append(f"- **{k}**: {v} 只")
    lines.append(f"")

    # Risk tags
    tags = candidate_report.get("risk_tags_distribution", {})
    if tags:
        lines.append(f"## 风险标签分布")
        lines.append(f"")
        for tag, count in sorted(tags.items(), key=lambda x: -x[1]):
            lines.append(f"- {tag}: {count}")
        lines.append(f"")

    # AIHF request
    lines.append(f"## AIHF Request 分析")
    lines.append(f"")
    lines.append(f"- 总数: {aihf_report.get('total_stocks', 0)}")
    lines.append(f"- trend: {aihf_report.get('trend_count', 0)}")
    lines.append(f"- burst: {aihf_report.get('burst_count', 0)}")
    lines.append(f"- balanced: {aihf_report.get('balanced', False)}")
    lines.append(f"- new fields present: {aihf_report.get('new_fields_present', False)}")
    if aihf_report.get("missing_new_fields"):
        lines.append(f"- missing fields: {aihf_report['missing_new_fields']}")
    lines.append(f"")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze candidate factor quality")
    parser.add_argument("--candidate-path", required=True, help="Path to top30_candidates.json")
    parser.add_argument("--request-path", required=True, help="Path to aihf_request.json")
    args = parser.parse_args()

    candidate_path = Path(args.candidate_path)
    request_path = Path(args.request_path)

    if not candidate_path.exists():
        print(f"❌ Candidate file not found: {candidate_path}")
        sys.exit(1)
    if not request_path.exists():
        print(f"❌ Request file not found: {request_path}")
        sys.exit(1)

    # Load data
    candidate_data = json.loads(candidate_path.read_text(encoding="utf-8"))
    request_data = json.loads(request_path.read_text(encoding="utf-8"))

    candidates = candidate_data.get("candidates", [])
    date = candidate_data.get("as_of", "unknown")

    # Analyze
    candidate_report = analyze_candidates(candidates)
    aihf_report = analyze_aihf_request(request_data)

    # Save JSON
    full_report = {
        "as_of": date,
        "candidate_count": len(candidates),
        "candidate_analysis": candidate_report,
        "aihf_analysis": aihf_report,
    }
    out_dir = candidate_path.parent
    json_path = out_dir / "candidate_factor_quality.json"
    json_path.write_text(json.dumps(full_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ JSON report saved: {json_path}")

    # Save Markdown
    md = generate_markdown(candidate_report, aihf_report, date)
    md_path = out_dir / "candidate_factor_quality.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"✅ Markdown report saved: {md_path}")

    # Print summary
    print(f"\n=== 因子质量摘要 ({date}) ===")
    print(f"候选数: {len(candidates)}")
    for field in NUMERIC_FIELDS:
        stats = candidate_report["fields"].get(field, {})
        issues = stats.get("issues", [])
        issue_str = f" [{', '.join(issues)}]" if issues else ""
        spread = stats.get("spread", "N/A")
        spread_v = f"{spread:.2f}" if isinstance(spread, (int, float)) else spread
        print(f"  {field}: min={stats.get('min', 'N/A')} max={stats.get('max', 'N/A')} spread={spread_v} unique={stats.get('unique_count', 'N/A')}{issue_str}")

    elig_dist = candidate_report["trade_eligibility"]["distribution"]
    print(f"  trade_eligibility: {elig_dist}")
    print(f"  aihf trend/burst: {aihf_report['trend_count']}/{aihf_report['burst_count']}")

    # Print separations
    seps = candidate_report.get("separations", {})
    for field, sep in seps.items():
        print(f"  {field} separation: top5={sep['top5_mean']:.1f} bottom10={sep['bottom10_mean']:.1f} gap={sep['separation']:.1f}")

    # Print warnings count
    warnings = candidate_report.get("warnings", [])
    print(f"  warnings: {len(warnings)}")
    for w in warnings:
        print(f"    - {w}")


if __name__ == "__main__":
    main()
