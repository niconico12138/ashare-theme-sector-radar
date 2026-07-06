#!/usr/bin/env python3
"""Evaluate selected Agent effectiveness across multiple dates."""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict

if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_ranking(date: str) -> dict | None:
    path = PROJECT_ROOT / "reports" / "agent_bridge" / date / "aihf_stock_ranking.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_daily_report(date: str) -> dict | None:
    path = PROJECT_ROOT / "reports" / "daily_ai_stock_report" / date / "daily_ai_stock_report.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def summarize_agent_effectiveness(rankings: list[dict]) -> list[dict]:
    """Aggregate agent stats across multiple dates."""
    agent_data = defaultdict(lambda: {
        "called": 0, "succeeded": 0, "fallback": 0, "failed": 0,
        "directions": [],
    })

    for ranking in rankings:
        items = ranking.get("items", [])
        meta = ranking.get("run_meta", {})
        requested = meta.get("requested_agents", [])
        succeeded = set(meta.get("succeeded_agents", []))
        fallback = set(meta.get("fallback_agents", []))

        for agent_id in requested:
            agent_data[agent_id]["called"] += 1
            if agent_id in succeeded:
                agent_data[agent_id]["succeeded"] += 1
            elif agent_id in fallback:
                agent_data[agent_id]["fallback"] += 1
            else:
                agent_data[agent_id]["failed"] += 1

        for item in items:
            for fa in item.get("top_positive_agents", []):
                a = fa.get("agent", "")
                if a:
                    agent_data[a]["directions"].append(1)
            for fa in item.get("top_negative_agents", []):
                a = fa.get("agent", "")
                if a:
                    agent_data[a]["directions"].append(-1)

    result = []
    for agent_id, data in sorted(agent_data.items()):
        called = data["called"]
        succ = data["succeeded"]
        fallback = data["fallback"]
        failed = data["failed"]
        dirs = data["directions"]

        avg_dir = sum(dirs) / len(dirs) if dirs else 0
        success_rate = succ / max(called, 1)
        fallback_rate = fallback / max(called, 1)

        if success_rate >= 0.7 and fallback_rate <= 0.3:
            label = "high_value"
        elif success_rate >= 0.3 and fallback_rate < 0.7:
            label = "useful_but_data_limited"
        elif fallback_rate >= 0.7:
            label = "mostly_fallback"
        elif success_rate > 0 and abs(avg_dir) < 0.1:
            label = "no_signal"
        else:
            label = "useful"

        result.append({
            "agent": agent_id,
            "called": called,
            "succeeded": succ,
            "fallback": fallback,
            "failed": failed,
            "success_rate": round(success_rate, 3),
            "fallback_rate": round(fallback_rate, 3),
            "avg_direction": round(avg_dir, 3),
            "effectiveness_label": label,
        })
    return sorted(result, key=lambda x: -x["success_rate"])


def compare_top10_changes(report_72: dict, report_73: dict) -> list[dict]:
    """Compare Top10 stock rankings between two dates."""
    ranking_72 = report_72.get("stock_agent_summary", {}).get("ranking_top10", [])
    ranking_73 = report_73.get("stock_agent_summary", {}).get("ranking_top10", [])

    by_code_72 = {s.get("code"): (i, s) for i, s in enumerate(ranking_72, 1)}
    by_code_73 = {s.get("code"): (i, s) for i, s in enumerate(ranking_73, 1)}

    all_codes = set(by_code_72.keys()) | set(by_code_73.keys())
    result = []
    for code in all_codes:
        in_72 = code in by_code_72
        in_73 = code in by_code_73

        if in_72 and in_73:
            change_type = "stayed"
            rank_72 = by_code_72[code][0]
            rank_73 = by_code_73[code][0]
        elif in_73:
            change_type = "entered"
            rank_72 = None
            rank_73 = by_code_73[code][0]
        else:
            change_type = "exited"
            rank_72 = by_code_72[code][0]
            rank_73 = None

        result.append({
            "code": code,
            "name": by_code_73[code][1].get("name", "") if in_73 else by_code_72[code][1].get("name", ""),
            "change_type": change_type,
            "rank_2026_07_02": rank_72,
            "rank_2026_07_03": rank_73,
        })
    return sorted(result, key=lambda x: x["rank_2026_07_03"] or 999)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate selected Agent effectiveness")
    parser.add_argument("--dates", nargs="+", required=True)
    parser.add_argument("--output-json", default=None)
    parser.add_argument("--output-md", default=None)
    args = parser.parse_args()

    # Load data
    rankings = []
    reports = []
    for date in args.dates:
        ranking = load_ranking(date)
        if ranking:
            rankings.append(ranking)
        report = load_daily_report(date)
        if report:
            reports.append(report)

    if not rankings:
        print("No ranking data found. Run selected preset first.")
        return 1

    # Agent effectiveness
    agent_eff = summarize_agent_effectiveness(rankings)

    # Top10 changes (if 2+ dates)
    top10_changes = []
    if len(reports) >= 2:
        top10_changes = compare_top10_changes(reports[0], reports[1])

    # Output JSON
    output = {
        "dates": args.dates,
        "agent_effectiveness": agent_eff,
        "top10_changes": top10_changes,
    }
    if args.output_json:
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"  JSON: {args.output_json}")

    # Output MD
    if args.output_md:
        lines = []
        lines.append("# Selected Agent Effectiveness Evaluation")
        lines.append(f"")
        lines.append(f"Dates: {', '.join(args.dates)}")
        lines.append(f"Rankings: {len(rankings)}")
        lines.append(f"")

        lines.append("## Agent Effectiveness")
        lines.append("")
        lines.append(f"{'Agent':<25} {'Called':>6} {'Succ':>6} {'Fallb':>6} {'Succ%':>6} {'Fallb%':>6} {'Dir':>5} {'Label':<25}")
        lines.append("-" * 95)
        for a in agent_eff:
            print(f"  {a['agent']:<25} {a['called']:>6} {a['succeeded']:>6} {a['fallback']:>6} {a['success_rate']:>6.1%} {a['fallback_rate']:>6.1%} {a['avg_direction']:>+5.2f} {a['effectiveness_label']:<25}", file=sys.stdout)
            lines.append(f"| {a['agent']:<25} | {a['called']:>6} | {a['succeeded']:>6} | {a['fallback']:>6} | {a['success_rate']:>6.1%} | {a['fallback_rate']:>6.1%} | {a['avg_direction']:>+5.2f} | {a['effectiveness_label']:<25} |")

        if top10_changes:
            lines.append("")
            lines.append("## Top10 Changes")
            lines.append("")
            lines.append("| Code | Name | Change | Rank 7/2 | Rank 7/3 |")
            lines.append("|------|------|--------|----------|----------|")
            for c in top10_changes:
                lines.append(f"| {c['code']} | {c['name']:<10} | {c['change_type']:<8} | {c['rank_2026_07_02'] or '-':<8} | {c['rank_2026_07_03'] or '-':<8} |")

        Path(args.output_md).write_text("\n".join(lines), encoding="utf-8")
        print(f"  MD: {args.output_md}")

    # Print summary
    print(f"\nAgent Effectiveness Summary ({len(rankings)} days):")
    for a in agent_eff:
        print(f"  {a['agent']:<25} succ={a['success_rate']:.1%} fallb={a['fallback_rate']:.1%} {a['effectiveness_label']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
