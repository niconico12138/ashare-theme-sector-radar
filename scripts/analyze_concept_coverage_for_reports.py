#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 41: Concept Coverage Analysis for Reports

扫描多个日期的 concept_unified_rank.csv，与 market_data_service 的 concept_members_history.csv 对照。

用法:
  python scripts/analyze_concept_coverage_for_reports.py \
    --dates 2026-07-01,2026-07-02,2026-07-03,2026-07-06 \
    --top-n 20 \
    --market-data-root E:\liaohua\01_projects\market_data_service
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONCEPT_RANK_DIR = PROJECT_ROOT / "reports" / "full_concept" / "unified_rank"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "concept_coverage"


def load_concept_unified_rank(date: str, top_n: int = 20) -> list[dict]:
    """Load concept_unified_rank.csv for a given date."""
    path = CONCEPT_RANK_DIR / date / "concept_unified_rank.csv"
    if not path.exists():
        return []

    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            concepts = []
            for row in reader:
                concepts.append({
                    "concept_name": row.get("sector_name", ""),
                    "rank": int(row.get("rank", 0) or 0),
                    "composite_score": float(row.get("concept_final_rank_score", 0) or 0),
                    "trend_score": float(row.get("trend_continuation_score", 0) or 0),
                    "burst_score": float(row.get("short_term_burst_score", 0) or 0),
                })
            # Sort by rank and take top_n
            concepts.sort(key=lambda x: x["rank"])
            return concepts[:top_n]
    except Exception:
        return []


def load_local_concept_members(market_data_root: str) -> dict[str, dict]:
    """Load concept_members_history.csv from market_data_service."""
    # Normalize path separators
    root = Path(market_data_root.replace("\\", "/"))
    csv_path = root / "market_data_service" / "data" / "concept_members_history.csv"
    if not csv_path.exists():
        return {}

    try:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            concepts = {}
            for row in reader:
                concept = row.get("concept", "")
                if concept not in concepts:
                    concepts[concept] = {
                        "stock_count": 0,
                        "as_of_dates": set(),
                        "sources": set(),
                    }
                concepts[concept]["stock_count"] += 1
                concepts[concept]["as_of_dates"].add(row.get("as_of", ""))
                concepts[concept]["sources"].add(row.get("source", ""))
            return concepts
    except Exception:
        return {}


def analyze_concept_coverage(
    dates: list[str],
    top_n: int,
    market_data_root: str,
) -> dict:
    """Analyze concept coverage across multiple dates."""
    # Load local concept members
    local_members = load_local_concept_members(market_data_root)

    # Aggregate concept data across dates
    concept_data = defaultdict(lambda: {
        "appearances": 0,
        "best_rank": 999,
        "latest_rank": 999,
        "latest_composite_score": 0,
        "latest_trend_score": 0,
        "latest_burst_score": 0,
        "dates": [],
    })

    for date in dates:
        concepts = load_concept_unified_rank(date, top_n)
        for c in concepts:
            name = c["concept_name"]
            data = concept_data[name]
            data["appearances"] += 1
            data["best_rank"] = min(data["best_rank"], c["rank"])
            data["latest_rank"] = c["rank"]
            data["latest_composite_score"] = c["composite_score"]
            data["latest_trend_score"] = c["trend_score"]
            data["latest_burst_score"] = c["burst_score"]
            data["dates"].append(date)

    # Build coverage analysis
    coverage_results = []
    for name, data in concept_data.items():
        local_info = local_members.get(name, {})
        has_local = name in local_members
        local_stock_count = local_info.get("stock_count", 0)
        as_of_dates = local_info.get("as_of_dates", set())
        sources = local_info.get("sources", set())

        # Determine coverage status
        if not has_local:
            coverage_status = "missing"
        elif local_stock_count == 0:
            coverage_status = "missing"
        elif local_stock_count < 10:
            coverage_status = "covered_thin"
        else:
            coverage_status = "covered_good"

        # Calculate priority score
        priority_score = 0
        priority_score += data["appearances"] * 2
        priority_score += max(0, 21 - data["best_rank"])
        priority_score += data["latest_composite_score"] / 10

        # Coverage penalty
        coverage_penalty = 0
        if coverage_status == "missing":
            coverage_penalty = 20
        elif coverage_status == "covered_thin":
            coverage_penalty = 8
        priority_score += coverage_penalty

        coverage_results.append({
            "concept_name": name,
            "appearances": data["appearances"],
            "best_rank": data["best_rank"],
            "latest_rank": data["latest_rank"],
            "latest_composite_score": data["latest_composite_score"],
            "latest_trend_score": data["latest_trend_score"],
            "latest_burst_score": data["latest_burst_score"],
            "has_local_concept_members": has_local,
            "local_stock_count": local_stock_count,
            "latest_snapshot_as_of": max(as_of_dates) if as_of_dates else None,
            "source_distribution": list(sources),
            "coverage_status": coverage_status,
            "priority_score": round(priority_score, 2),
            "dates_affected": data["dates"],
        })

    # Sort by priority score
    coverage_results.sort(key=lambda x: -x["priority_score"])

    # Build priority list for concept members to add
    priority_list = []
    for item in coverage_results:
        if item["coverage_status"] in ("missing", "covered_thin"):
            reason = "missing" if item["coverage_status"] == "missing" else "thin_coverage"
            priority_list.append({
                "priority": len(priority_list) + 1,
                "concept_name": item["concept_name"],
                "reason": reason,
                "suggested_min_stock_count": 10,
                "dates_affected": item["dates_affected"],
                "current_status": item["coverage_status"],
                "local_stock_count": item["local_stock_count"],
                "priority_score": item["priority_score"],
            })

    result = {
        "analysis_date": datetime.now().isoformat(),
        "dates_analyzed": dates,
        "top_n": top_n,
        "total_concepts": len(coverage_results),
        "coverage_summary": {
            "covered_good": sum(1 for c in coverage_results if c["coverage_status"] == "covered_good"),
            "covered_thin": sum(1 for c in coverage_results if c["coverage_status"] == "covered_thin"),
            "missing": sum(1 for c in coverage_results if c["coverage_status"] == "missing"),
        },
        "concept_coverage": coverage_results,
        "priority_list": priority_list,
    }

    return result


def generate_markdown_report(result: dict) -> str:
    """Generate markdown report from analysis results."""
    lines = []
    lines.append("# Concept Coverage Analysis Report")
    lines.append("")
    lines.append(f"**Analysis Date**: {result.get('analysis_date', '')}")
    lines.append(f"**Dates Analyzed**: {', '.join(result.get('dates_analyzed', []))}")
    lines.append(f"**Top N**: {result.get('top_n', 0)}")
    lines.append(f"**Total Concepts**: {result.get('total_concepts', 0)}")
    lines.append("")

    # Coverage summary
    summary = result.get("coverage_summary", {})
    lines.append("## Coverage Summary")
    lines.append("")
    lines.append(f"- **Covered Good (>=10 stocks)**: {summary.get('covered_good', 0)}")
    lines.append(f"- **Covered Thin (1-9 stocks)**: {summary.get('covered_thin', 0)}")
    lines.append(f"- **Missing**: {summary.get('missing', 0)}")
    lines.append("")

    # Concept coverage table
    coverage = result.get("concept_coverage", [])
    if coverage:
        lines.append("## Concept Coverage Details")
        lines.append("")
        lines.append("| Concept | Appearances | Best Rank | Latest Rank | Composite Score | Local Stocks | Status | Priority |")
        lines.append("|---------|-------------|-----------|-------------|-----------------|--------------|--------|----------|")
        for item in coverage[:30]:
            status_icon = "✅" if item["coverage_status"] == "covered_good" else "⚠️" if item["coverage_status"] == "covered_thin" else "❌"
            lines.append(
                f"| {item['concept_name']} | {item['appearances']} | "
                f"{item['best_rank']} | {item['latest_rank']} | "
                f"{item['latest_composite_score']:.2f} | "
                f"{item['local_stock_count']} | {status_icon} {item['coverage_status']} | "
                f"{item['priority_score']:.1f} |"
            )
        lines.append("")

    # Priority list
    priority_list = result.get("priority_list", [])
    if priority_list:
        lines.append("## Priority List for Concept Members Enhancement")
        lines.append("")
        lines.append("| Priority | Concept | Reason | Local Stocks | Dates Affected | Priority Score |")
        lines.append("|----------|---------|--------|--------------|----------------|----------------|")
        for item in priority_list[:20]:
            dates_str = ", ".join(item["dates_affected"][:3])
            lines.append(
                f"| {item['priority']} | {item['concept_name']} | "
                f"{item['reason']} | {item['local_stock_count']} | "
                f"{dates_str} | {item['priority_score']:.1f} |"
            )
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze concept coverage for reports")
    parser.add_argument("--dates", required=True, help="Comma-separated dates (YYYY-MM-DD)")
    parser.add_argument("--top-n", type=int, default=20, help="Top N concepts to analyze")
    parser.add_argument("--market-data-root", required=True, help="Path to market_data_service root")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    args = parser.parse_args()

    dates = [d.strip() for d in args.dates.split(",") if d.strip()]
    if not dates:
        print("  ❌ No dates provided")
        return 1

    print(f"{'='*70}")
    print(f"  Concept Coverage Analysis")
    print(f"  Dates: {', '.join(dates)}")
    print(f"  Top N: {args.top_n}")
    print(f"{'='*70}")
    print()

    # Run analysis
    result = analyze_concept_coverage(dates, args.top_n, args.market_data_root)

    # Save JSON
    out_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "concept_coverage_summary.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ JSON: {json_path}")

    # Save Markdown
    md_content = generate_markdown_report(result)
    md_path = out_dir / "concept_coverage_summary.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"  ✅ Markdown: {md_path}")

    # Print summary
    print()
    summary = result.get("coverage_summary", {})
    priority_list = result.get("priority_list", [])
    print(f"  Summary:")
    print(f"    - Total concepts: {result.get('total_concepts', 0)}")
    print(f"    - Covered good: {summary.get('covered_good', 0)}")
    print(f"    - Covered thin: {summary.get('covered_thin', 0)}")
    print(f"    - Missing: {summary.get('missing', 0)}")
    print(f"    - Priority list: {len(priority_list)} concepts")
    if priority_list:
        print(f"    - Top 5 priorities:")
        for item in priority_list[:5]:
            print(f"      {item['priority']}. {item['concept_name']} ({item['reason']})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
