#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 39: Agent Effectiveness Evaluation

评估 selected 7 个 Agent 的有效性：
- 成功率、fallback 率、信号分布
- 跨日期 Top10 变化
- Agent 差异化程度

用法:
  python scripts/evaluate_agent_effectiveness.py --dates 2026-07-01,2026-07-02,2026-07-03,2026-07-06
  python scripts/evaluate_agent_effectiveness.py --dates 2026-07-06 --agent-preset selected
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

# Selected 7 agents
SELECTED_AGENTS = [
    "technical_analyst",
    "fundamentals_analyst",
    "valuation_analyst",
    "sentiment_analyst",
    "china_youzi",
    "industry_rotation",
    "news_sentiment_analyst",
]


def load_bridge_report(date: str, preset: str = "selected") -> dict | None:
    """Load daily_bridge_report.json for a given date."""
    report_path = OUTPUT_DIR / date / "daily_bridge_report.json"
    if not report_path.exists():
        return None
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_stock_ranking(date: str) -> dict | None:
    """Load aihf_stock_ranking.json for a given date."""
    ranking_path = OUTPUT_DIR / date / "aihf_stock_ranking.json"
    if not ranking_path.exists():
        return None
    try:
        return json.loads(ranking_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def evaluate_agent_effectiveness(dates: list[str], preset: str = "selected") -> dict:
    """Evaluate agent effectiveness across multiple dates."""
    result = {
        "evaluation_date": datetime.now().isoformat(),
        "dates_evaluated": dates,
        "preset": preset,
        "per_agent_stats": {},
        "daily_top10": {},
        "cross_date_analysis": {},
        "conclusions": {},
    }

    # Per-agent stats
    agent_stats = defaultdict(lambda: {
        "total_calls": 0,
        "success_count": 0,
        "fallback_count": 0,
        "failed_count": 0,
        "buy_count": 0,
        "hold_count": 0,
        "sell_count": 0,
        "confidence_sum": 0.0,
        "confidence_count": 0,
        "weighted_contribution_sum": 0.0,
        "weighted_contribution_count": 0,
    })

    # Daily top10 tracking
    daily_top10 = {}
    all_top10_codes = defaultdict(int)  # code -> count of dates in top10

    for date in dates:
        ranking = load_stock_ranking(date)
        if not ranking:
            continue

        items = ranking.get("items", [])
        run_meta = ranking.get("run_meta", {})
        per_agent_status = run_meta.get("per_agent_status", {})

        # Track daily top10
        top10_items = items[:10]
        daily_top10[date] = [
            {
                "code": item.get("code", ""),
                "name": item.get("name", ""),
                "source_pool": item.get("source_pool", ""),
                "boards": item.get("boards", []),
                "trend_score": item.get("trend_score", 0),
                "burst_score": item.get("burst_score", 0),
                "agent_score": item.get("agent_score", 0),
                "risk_adjusted_score": item.get("risk_adjusted_score", 0),
                "top_positive_agents": [
                    {"agent": a.get("agent", ""), "signal": a.get("signal", ""), "confidence": a.get("confidence", 0), "weight": a.get("weight", 0)}
                    for a in item.get("top_positive_agents", [])[:3]
                ],
                "top_negative_agents": [
                    {"agent": a.get("agent", ""), "signal": a.get("signal", ""), "confidence": a.get("confidence", 0), "weight": a.get("weight", 0)}
                    for a in item.get("top_negative_agents", [])[:3]
                ],
            }
            for item in top10_items
        ]

        for item in top10_items:
            all_top10_codes[item.get("code", "")] += 1

        # Aggregate per-agent stats
        for agent_key in SELECTED_AGENTS:
            agent_status = per_agent_status.get(agent_key, {})
            stats = agent_stats[agent_key]

            succeeded = agent_status.get("succeeded", 0)
            failed = agent_status.get("failed", 0)
            fallback = agent_status.get("fallback", 0)

            stats["total_calls"] += succeeded + failed + fallback
            stats["success_count"] += succeeded
            stats["fallback_count"] += fallback
            stats["failed_count"] += failed

        # Aggregate agent signals from all items
        for item in items:
            # Check top_positive_agents
            for pa in item.get("top_positive_agents", []):
                agent_key = pa.get("agent", "")
                if agent_key in SELECTED_AGENTS:
                    stats = agent_stats[agent_key]
                    signal = pa.get("signal", "neutral")
                    if signal in ("bullish", "buy"):
                        stats["buy_count"] += 1
                    elif signal in ("bearish", "sell"):
                        stats["sell_count"] += 1
                    else:
                        stats["hold_count"] += 1
                    stats["confidence_sum"] += pa.get("confidence", 0) * 100
                    stats["confidence_count"] += 1
                    stats["weighted_contribution_sum"] += pa.get("confidence", 0) * pa.get("weight", 0)
                    stats["weighted_contribution_count"] += 1

            # Check top_negative_agents
            for na in item.get("top_negative_agents", []):
                agent_key = na.get("agent", "")
                if agent_key in SELECTED_AGENTS:
                    stats = agent_stats[agent_key]
                    signal = na.get("signal", "neutral")
                    if signal in ("bullish", "buy"):
                        stats["buy_count"] += 1
                    elif signal in ("bearish", "sell"):
                        stats["sell_count"] += 1
                    else:
                        stats["hold_count"] += 1
                    stats["confidence_sum"] += na.get("confidence", 0) * 100
                    stats["confidence_count"] += 1
                    stats["weighted_contribution_sum"] += na.get("confidence", 0) * na.get("weight", 0)
                    stats["weighted_contribution_count"] += 1

    # Calculate per-agent effectiveness metrics
    for agent_key in SELECTED_AGENTS:
        stats = agent_stats[agent_key]
        total = stats["total_calls"]
        if total == 0:
            result["per_agent_stats"][agent_key] = {
                "total_calls": 0,
                "success_rate": 0,
                "fallback_rate": 0,
                "failed_rate": 0,
                "buy_count": 0,
                "hold_count": 0,
                "sell_count": 0,
                "avg_confidence": 0,
                "avg_weighted_contribution": 0,
                "effectiveness_rating": "no_data",
            }
            continue

        success_rate = stats["success_count"] / total
        fallback_rate = stats["fallback_count"] / total
        failed_rate = stats["failed_count"] / total

        avg_confidence = stats["confidence_sum"] / stats["confidence_count"] if stats["confidence_count"] > 0 else 0
        avg_weighted_contribution = stats["weighted_contribution_sum"] / stats["weighted_contribution_count"] if stats["weighted_contribution_count"] > 0 else 0

        # Determine effectiveness rating
        if success_rate >= 0.8:
            rating = "high_value"
        elif success_rate >= 0.5:
            rating = "moderate"
        elif fallback_rate >= 0.8:
            rating = "mostly_fallback"
        else:
            rating = "weak"

        result["per_agent_stats"][agent_key] = {
            "total_calls": total,
            "success_count": stats["success_count"],
            "fallback_count": stats["fallback_count"],
            "failed_count": stats["failed_count"],
            "success_rate": round(success_rate, 3),
            "fallback_rate": round(fallback_rate, 3),
            "failed_rate": round(failed_rate, 3),
            "buy_count": stats["buy_count"],
            "hold_count": stats["hold_count"],
            "sell_count": stats["sell_count"],
            "avg_confidence": round(avg_confidence, 3),
            "avg_weighted_contribution": round(avg_weighted_contribution, 4),
            "effectiveness_rating": rating,
        }

    # Cross-date analysis
    repeated_codes = {code: count for code, count in all_top10_codes.items() if count > 1}
    new_entries = {code: count for code, count in all_top10_codes.items() if count == 1}

    result["cross_date_analysis"] = {
        "dates_count": len(dates),
        "repeated_in_top10": [
            {"code": code, "appearances": count}
            for code, count in sorted(repeated_codes.items(), key=lambda x: -x[1])[:10]
        ],
        "new_entries_count": len(new_entries),
        "total_unique_stocks": len(all_top10_codes),
    }

    # Conclusions
    high_value_agents = [k for k, v in result["per_agent_stats"].items() if v.get("effectiveness_rating") == "high_value"]
    weak_agents = [k for k, v in result["per_agent_stats"].items() if v.get("effectiveness_rating") == "weak"]
    mostly_fallback_agents = [k for k, v in result["per_agent_stats"].items() if v.get("effectiveness_rating") == "mostly_fallback"]
    no_data_agents = [k for k, v in result["per_agent_stats"].items() if v.get("effectiveness_rating") == "no_data"]

    result["conclusions"] = {
        "high_value_agents": high_value_agents,
        "weak_agents": weak_agents,
        "mostly_fallback_agents": mostly_fallback_agents,
        "no_data_agents": no_data_agents,
        "recommended_selected_preset": SELECTED_AGENTS.copy(),
        "candidate_for_disable": [],
    }

    # Identify candidates for disable
    for agent_key in mostly_fallback_agents:
        stats = result["per_agent_stats"][agent_key]
        if stats.get("fallback_rate", 0) >= 0.9:
            result["conclusions"]["candidate_for_disable"].append({
                "agent": agent_key,
                "reason": f"fallback_rate={stats['fallback_rate']:.1%}",
            })

    return result


def generate_markdown_report(result: dict) -> str:
    """Generate markdown report from evaluation results."""
    lines = []
    lines.append("# Agent Effectiveness Evaluation Report")
    lines.append("")
    lines.append(f"**Evaluation Date**: {result.get('evaluation_date', '')}")
    lines.append(f"**Dates Evaluated**: {', '.join(result.get('dates_evaluated', []))}")
    lines.append(f"**Preset**: {result.get('preset', '')}")
    lines.append("")

    # Per-agent stats
    lines.append("## Per-Agent Effectiveness")
    lines.append("")
    lines.append("| Agent | Total | Success | Fallback | Failed | Success Rate | Buy | Hold | Sell | Avg Confidence | Rating |")
    lines.append("|-------|-------|---------|----------|--------|--------------|-----|------|------|----------------|--------|")

    for agent_key, stats in result.get("per_agent_stats", {}).items():
        lines.append(
            f"| {agent_key} | {stats.get('total_calls', 0)} | "
            f"{stats.get('success_count', 0)} | {stats.get('fallback_count', 0)} | "
            f"{stats.get('failed_count', 0)} | {stats.get('success_rate', 0):.1%} | "
            f"{stats.get('buy_count', 0)} | {stats.get('hold_count', 0)} | "
            f"{stats.get('sell_count', 0)} | {stats.get('avg_confidence', 0):.1f} | "
            f"{stats.get('effectiveness_rating', '?')} |"
        )
    lines.append("")

    # Daily Top10
    lines.append("## Daily Top10")
    lines.append("")
    for date, items in result.get("daily_top10", {}).items():
        lines.append(f"### {date}")
        lines.append("")
        lines.append("| Rank | Code | Name | Source | Boards | Agent Score | Risk Adjusted |")
        lines.append("|------|------|------|--------|--------|-------------|---------------|")
        for i, item in enumerate(items[:10], 1):
            boards = ", ".join(item.get("boards", [])[:2])
            lines.append(
                f"| {i} | {item.get('code', '')} | {item.get('name', '')} | "
                f"{item.get('source_pool', '')} | {boards} | "
                f"{item.get('agent_score', 0):.1f} | {item.get('risk_adjusted_score', 0):.1f} |"
            )
        lines.append("")

    # Cross-date analysis
    cross = result.get("cross_date_analysis", {})
    lines.append("## Cross-Date Analysis")
    lines.append("")
    lines.append(f"- **Dates evaluated**: {cross.get('dates_count', 0)}")
    lines.append(f"- **Total unique stocks in Top10**: {cross.get('total_unique_stocks', 0)}")
    lines.append(f"- **New entries**: {cross.get('new_entries_count', 0)}")
    lines.append("")

    repeated = cross.get("repeated_in_top10", [])
    if repeated:
        lines.append("### Repeated in Top10")
        lines.append("")
        lines.append("| Code | Appearances |")
        lines.append("|------|-------------|")
        for item in repeated:
            lines.append(f"| {item.get('code', '')} | {item.get('appearances', 0)} |")
        lines.append("")

    # Conclusions
    conclusions = result.get("conclusions", {})
    lines.append("## Conclusions")
    lines.append("")
    lines.append(f"- **High value agents**: {', '.join(conclusions.get('high_value_agents', [])) or 'None'}")
    lines.append(f"- **Weak agents**: {', '.join(conclusions.get('weak_agents', [])) or 'None'}")
    lines.append(f"- **Mostly fallback agents**: {', '.join(conclusions.get('mostly_fallback_agents', [])) or 'None'}")
    lines.append(f"- **No data agents**: {', '.join(conclusions.get('no_data_agents', [])) or 'None'}")
    lines.append("")

    candidate_disable = conclusions.get("candidate_for_disable", [])
    if candidate_disable:
        lines.append("### Candidate for Disable")
        lines.append("")
        for item in candidate_disable:
            lines.append(f"- **{item.get('agent', '')}**: {item.get('reason', '')}")
        lines.append("")

    recommended = conclusions.get("recommended_selected_preset", [])
    lines.append(f"### Recommended Selected Preset")
    lines.append("")
    lines.append(f"Keep all 7 agents: {', '.join(recommended)}")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Evaluate agent effectiveness")
    parser.add_argument("--dates", required=True, help="Comma-separated dates (YYYY-MM-DD)")
    parser.add_argument("--agent-preset", default="selected", help="Agent preset to evaluate")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    args = parser.parse_args()

    dates = [d.strip() for d in args.dates.split(",") if d.strip()]
    if not dates:
        print("  ❌ No dates provided")
        return 1

    print(f"{'='*70}")
    print(f"  Agent Effectiveness Evaluation")
    print(f"  Dates: {', '.join(dates)}")
    print(f"  Preset: {args.agent_preset}")
    print(f"{'='*70}")
    print()

    # Run evaluation
    result = evaluate_agent_effectiveness(dates, args.agent_preset)

    # Save JSON
    out_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR / "agent_effectiveness"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"{args.agent_preset}_agent_effectiveness.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ JSON: {json_path}")

    # Save Markdown
    md_content = generate_markdown_report(result)
    md_path = out_dir / f"{args.agent_preset}_agent_effectiveness.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"  ✅ Markdown: {md_path}")

    # Print summary
    print()
    print(f"  Summary:")
    for agent_key, stats in result.get("per_agent_stats", {}).items():
        print(f"    {agent_key}: {stats.get('effectiveness_rating', '?')} "
              f"(success={stats.get('success_rate', 0):.1%}, "
              f"fallback={stats.get('fallback_rate', 0):.1%})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
