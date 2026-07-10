#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 41: Candidate Pool Quality Analysis

分析候选池质量：
- 行业/概念分散度
- 板块集中度
- 趋势池/短线池比例
- 重复股票来源
- 主板过滤损耗

用法:
  python scripts/analyze_candidate_pool_quality.py --as-of 2026-07-06
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "reports" / "agent_bridge"


def load_top30_candidates(date: str) -> dict | None:
    """Load top30_candidates.json for a given date."""
    path = OUTPUT_DIR / date / "top30_candidates.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def summarize_filter_losses(funnel: dict) -> dict[str, int]:
    trend_pool = funnel.get("trend_pool", {})
    burst_pool = funnel.get("burst_pool", {})
    return {
        "non_main_board": int(trend_pool.get("filtered_non_main_board", 0) or 0)
        + int(burst_pool.get("filtered_non_main_board", 0) or 0),
        "st_filtered": int(trend_pool.get("filtered_st", 0) or 0)
        + int(burst_pool.get("filtered_st", 0) or 0),
        "invalid_code": int(trend_pool.get("filtered_invalid_code", 0) or 0)
        + int(burst_pool.get("filtered_invalid_code", 0) or 0),
        "empty_name": int(trend_pool.get("filtered_empty_name", 0) or 0)
        + int(burst_pool.get("filtered_empty_name", 0) or 0),
    }


def explain_candidate_shortfall(final_count: int, target_count: int, funnel: dict, filter_losses: dict[str, int]) -> dict:
    shortfall = max(target_count - final_count, 0)
    top_loss_reasons = funnel.get("top_loss_reasons", [])
    dominant = top_loss_reasons[0]["reason"] if top_loss_reasons else ""
    if not dominant:
        positive_losses = [(name, count) for name, count in filter_losses.items() if count > 0]
        dominant = max(positive_losses, key=lambda item: item[1])[0] if positive_losses else ""

    merge = funnel.get("merge", {})
    if shortfall == 0:
        recommendation = "candidate pool reached target"
    elif dominant == "non_main_board":
        recommendation = "main-board constraint is the dominant loss; keep the rule explicit and improve board coverage inside main-board names"
    elif dominant == "st_filtered":
        recommendation = "ST filtering is reducing the pool; keep the safety rule and improve upstream candidate breadth"
    elif dominant in ("invalid_code", "empty_name"):
        recommendation = "data normalization quality is reducing the pool; inspect upstream stock identity fields"
    elif int(merge.get("duplicates_removed", 0) or 0) > 0:
        recommendation = "deduplication reduced the pool; inspect overlapping trend/burst sources and add backfill candidates"
    else:
        recommendation = "raw eligible candidates are below target; expand upstream board constituent coverage"

    return {
        "target_count": target_count,
        "final_count": final_count,
        "shortfall": shortfall,
        "dominant_loss_reason": dominant,
        "recommendation": recommendation,
    }


def analyze_candidate_pool_quality(date: str) -> dict:
    """Analyze candidate pool quality for a given date."""
    data = load_top30_candidates(date)
    if not data:
        return {"error": f"No top30_candidates.json found for {date}"}

    candidates = data.get("candidates", [])
    funnel = data.get("selection_funnel", {})

    # Basic statistics
    final_count = len(candidates)
    trend_count = sum(1 for c in candidates if c.get("source_pool") == "trend")
    burst_count = sum(1 for c in candidates if c.get("source_pool") == "burst")
    both_count = sum(1 for c in candidates if c.get("source_pool") == "both")

    # Board analysis
    board_counts = defaultdict(int)
    stock_boards = defaultdict(list)
    for c in candidates:
        code = c.get("code", "")
        for board in c.get("boards", []):
            board_counts[board] += 1
            stock_boards[code].append(board)

    # Top boards concentration
    sorted_boards = sorted(board_counts.items(), key=lambda x: -x[1])
    top1_board_ratio = sorted_boards[0][1] / final_count if final_count > 0 and sorted_boards else 0
    top3_boards_ratio = sum(c for _, c in sorted_boards[:3]) / final_count if final_count > 0 else 0

    # Duplicate analysis
    stocks_with_multiple_boards = sum(1 for boards in stock_boards.values() if len(boards) > 1)
    duplicate_ratio = stocks_with_multiple_boards / final_count if final_count > 0 else 0

    # Selection funnel analysis
    trend_pool = funnel.get("trend_pool", {})
    burst_pool = funnel.get("burst_pool", {})
    merge = funnel.get("merge", {})
    top_loss_reasons = funnel.get("top_loss_reasons", [])
    selection_policy = data.get("selection_policy", {})
    target_count = int(selection_policy.get("stock_limit", data.get("candidate_count", 30)) or 30)
    filter_loss_totals = summarize_filter_losses(funnel)
    shortfall_analysis = explain_candidate_shortfall(final_count, target_count, funnel, filter_loss_totals)

    # Quality risk tags
    risk_tags = []
    if final_count < target_count:
        risk_tags.append("candidate_count_below_target")
    if final_count < 25:
        risk_tags.append("insufficient_candidates")
    if top1_board_ratio > 0.4:
        risk_tags.append("concentrated_boards")
    if top3_boards_ratio > 0.7:
        risk_tags.append("concentrated_boards")
    if duplicate_ratio > 0.4:
        risk_tags.append("high_duplicate_ratio")

    # Check for concept coverage gap
    # This is a simplified check - full analysis requires concept coverage data
    if not risk_tags:
        risk_tags.append("healthy")

    result = {
        "analysis_date": datetime.now().isoformat(),
        "as_of_date": date,
        "basic_stats": {
            "final_candidate_count": final_count,
            "trend_count": trend_count,
            "burst_count": burst_count,
            "both_count": both_count,
            "unique_board_count": len(board_counts),
            "unique_stock_count": len(stock_boards),
        },
        "source_pool_distribution": {
            "trend_only": trend_count,
            "burst_only": burst_count,
            "both": both_count,
        },
        "board_concentration": {
            "top_boards": [
                {"board": board, "count": count, "ratio": round(count / final_count, 3) if final_count > 0 else 0}
                for board, count in sorted_boards[:10]
            ],
            "top1_board_ratio": round(top1_board_ratio, 3),
            "top3_board_ratio": round(top3_boards_ratio, 3),
        },
        "duplicate_analysis": {
            "stocks_with_multiple_boards": stocks_with_multiple_boards,
            "duplicate_ratio": round(duplicate_ratio, 3),
        },
        "selection_funnel_summary": {
            "trend_eligible": trend_pool.get("eligible", 0),
            "trend_selected": trend_pool.get("selected_final", 0),
            "burst_eligible": burst_pool.get("eligible", 0),
            "burst_selected": burst_pool.get("selected_final", 0),
            "merge_before_dedup": merge.get("before_dedup", 0),
            "merge_after_dedup": merge.get("after_dedup", 0),
            "final_count": merge.get("final_count", 0),
        },
        "filter_loss_totals": filter_loss_totals,
        "shortfall_analysis": shortfall_analysis,
        "top_loss_reasons": top_loss_reasons,
        "quality_risk_tags": risk_tags,
    }

    return result


def generate_markdown_report(result: dict) -> str:
    """Generate markdown report from analysis results."""
    lines = []
    lines.append("# Candidate Pool Quality Report")
    lines.append("")
    lines.append(f"**Analysis Date**: {result.get('analysis_date', '')}")
    lines.append(f"**As Of Date**: {result.get('as_of_date', '')}")
    lines.append("")

    # Basic stats
    stats = result.get("basic_stats", {})
    lines.append("## Basic Statistics")
    lines.append("")
    lines.append(f"- **Final Candidate Count**: {stats.get('final_candidate_count', 0)}")
    lines.append(f"- **Trend Only**: {stats.get('trend_count', 0)}")
    lines.append(f"- **Burst Only**: {stats.get('burst_count', 0)}")
    lines.append(f"- **Both**: {stats.get('both_count', 0)}")
    lines.append(f"- **Unique Board Count**: {stats.get('unique_board_count', 0)}")
    lines.append(f"- **Unique Stock Count**: {stats.get('unique_stock_count', 0)}")
    lines.append("")

    # Board concentration
    concentration = result.get("board_concentration", {})
    lines.append("## Board Concentration")
    lines.append("")
    lines.append(f"- **Top1 Board Ratio**: {concentration.get('top1_board_ratio', 0):.1%}")
    lines.append(f"- **Top3 Board Ratio**: {concentration.get('top3_boards_ratio', 0):.1%}")
    lines.append("")

    top_boards = concentration.get("top_boards", [])
    if top_boards:
        lines.append("### Top Boards")
        lines.append("")
        lines.append("| Board | Count | Ratio |")
        lines.append("|-------|-------|-------|")
        for item in top_boards[:10]:
            lines.append(f"| {item.get('board', '')} | {item.get('count', 0)} | {item.get('ratio', 0):.1%} |")
        lines.append("")

    # Duplicate analysis
    duplicate = result.get("duplicate_analysis", {})
    lines.append("## Duplicate Analysis")
    lines.append("")
    lines.append(f"- **Stocks with Multiple Boards**: {duplicate.get('stocks_with_multiple_boards', 0)}")
    lines.append(f"- **Duplicate Ratio**: {duplicate.get('duplicate_ratio', 0):.1%}")
    lines.append("")

    # Selection funnel summary
    funnel_summary = result.get("selection_funnel_summary", {})
    lines.append("## Selection Funnel Summary")
    lines.append("")
    lines.append(f"- **Trend Eligible**: {funnel_summary.get('trend_eligible', 0)}")
    lines.append(f"- **Trend Selected**: {funnel_summary.get('trend_selected', 0)}")
    lines.append(f"- **Burst Eligible**: {funnel_summary.get('burst_eligible', 0)}")
    lines.append(f"- **Burst Selected**: {funnel_summary.get('burst_selected', 0)}")
    lines.append(f"- **Merge Before Dedup**: {funnel_summary.get('merge_before_dedup', 0)}")
    lines.append(f"- **Merge After Dedup**: {funnel_summary.get('merge_after_dedup', 0)}")
    lines.append(f"- **Final Count**: {funnel_summary.get('final_count', 0)}")
    lines.append("")

    shortfall = result.get("shortfall_analysis", {})
    if shortfall:
        lines.append("## Shortfall Analysis")
        lines.append("")
        lines.append(f"- **Target Count**: {shortfall.get('target_count', 0)}")
        lines.append(f"- **Final Count**: {shortfall.get('final_count', 0)}")
        lines.append(f"- **Shortfall**: {shortfall.get('shortfall', 0)}")
        lines.append(f"- **Dominant Loss Reason**: {shortfall.get('dominant_loss_reason', '-') or '-'}")
        lines.append(f"- **Recommendation**: {shortfall.get('recommendation', '-')}")
        lines.append("")

    filter_losses = result.get("filter_loss_totals", {})
    if filter_losses:
        lines.append("## Filter Loss Totals")
        lines.append("")
        lines.append("| Reason | Count |")
        lines.append("|--------|------:|")
        for reason, count in filter_losses.items():
            lines.append(f"| {reason} | {count} |")
        lines.append("")

    # Top loss reasons
    top_loss = result.get("top_loss_reasons", [])
    if top_loss:
        lines.append("## Top Loss Reasons")
        lines.append("")
        lines.append("| Reason | Count |")
        lines.append("|--------|-------|")
        for item in top_loss:
            lines.append(f"| {item.get('reason', '')} | {item.get('count', 0)} |")
        lines.append("")

    # Quality risk tags
    risk_tags = result.get("quality_risk_tags", [])
    lines.append("## Quality Risk Tags")
    lines.append("")
    for tag in risk_tags:
        if tag == "healthy":
            lines.append(f"- ✅ **{tag}**")
        else:
            lines.append(f"- ⚠️ **{tag}**")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze candidate pool quality")
    parser.add_argument("--as-of", required=True, help="Date YYYY-MM-DD")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    args = parser.parse_args()

    print(f"{'='*70}")
    print(f"  Candidate Pool Quality Analysis")
    print(f"  Date: {args.as_of}")
    print(f"{'='*70}")
    print()

    # Run analysis
    result = analyze_candidate_pool_quality(args.as_of)

    if "error" in result:
        print(f"  ❌ {result['error']}")
        return 1

    # Save JSON
    out_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR / args.as_of
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "candidate_pool_quality.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ JSON: {json_path}")

    # Save Markdown
    md_content = generate_markdown_report(result)
    md_path = out_dir / "candidate_pool_quality.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"  ✅ Markdown: {md_path}")

    # Print summary
    print()
    stats = result.get("basic_stats", {})
    concentration = result.get("board_concentration", {})
    risk_tags = result.get("quality_risk_tags", [])
    print(f"  Summary:")
    print(f"    - Final candidates: {stats.get('final_candidate_count', 0)}")
    print(f"    - Top1 board ratio: {concentration.get('top1_board_ratio', 0):.1%}")
    print(f"    - Top3 board ratio: {concentration.get('top3_boards_ratio', 0):.1%}")
    print(f"    - Risk tags: {', '.join(risk_tags)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
