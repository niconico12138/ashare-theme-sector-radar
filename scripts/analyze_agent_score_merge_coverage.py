#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diagnostic & backfill tool for agent_score merge coverage.

Scans reports/agent_bridge/<DATE>/ for each date and reports:
- How many candidates match ranking items
- How many agent_score fields are already present
- What would change with --apply

Usage:
  python scripts/analyze_agent_score_merge_coverage.py --dates 2026-06-29,2026-07-01
  python scripts/analyze_agent_score_merge_coverage.py --dates 2026-06-29 --apply
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_BRIDGE_DIR = PROJECT_ROOT / "reports" / "agent_bridge"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "agent_bridge" / "agent_score_merge_coverage"

from scripts.export_top30_candidates import merge_agent_scores_into_candidates  # noqa: E402


def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def analyze_date(date: str, bridge_dir: Path) -> dict:
    """Analyze a single date's merge coverage without modifying files."""
    top30_path = bridge_dir / date / "top30_candidates.json"
    ranking_path = bridge_dir / date / "aihf_stock_ranking.json"

    result = {
        "date": date,
        "candidate_count": 0,
        "ranking_item_count": 0,
        "merged_count": 0,
        "missing_from_ranking_count": 0,
        "missing_from_ranking_codes": [],
        "ranking_extra_count": 0,
        "ranking_extra_codes": [],
        "agent_score_merged": False,
        "agent_score_merge_count": None,
        "rank_hidden": None,
        "raw_rank_leaked": False,
        "merge_status": "none",
    }

    # Load top30
    top30 = _load_json(top30_path)
    if top30 is None:
        result["merge_status"] = "missing_top30"
        return result

    candidates = top30.get("candidates", [])
    result["candidate_count"] = len(candidates)
    result["rank_hidden"] = top30.get("rank_hidden")
    result["agent_score_merged"] = top30.get("agent_score_merged", False)
    result["agent_score_merge_count"] = top30.get("agent_score_merge_count")

    # Check raw rank leak
    for c in candidates:
        if "rank" in c:
            result["raw_rank_leaked"] = True
            break

    # Count existing agent_score
    result["merged_count"] = sum(1 for c in candidates if "agent_score" in c)

    # Load ranking
    ranking = _load_json(ranking_path)
    if ranking is None:
        result["merge_status"] = "missing_ranking"
        return result

    items = ranking.get("items", [])
    result["ranking_item_count"] = len(items)

    # Code sets
    cand_codes = {str(c.get("code", "")).strip() for c in candidates if c.get("code")}
    rank_codes = {str(i.get("code", "")).strip() for i in items if i.get("code")}

    missing_codes = sorted(cand_codes - rank_codes)
    extra_codes = sorted(rank_codes - cand_codes)

    result["missing_from_ranking_count"] = len(missing_codes)
    result["missing_from_ranking_codes"] = missing_codes
    result["ranking_extra_count"] = len(extra_codes)
    result["ranking_extra_codes"] = extra_codes

    # Determine merge_status
    if result["merged_count"] == len(candidates) and len(candidates) > 0:
        result["merge_status"] = "full"
    elif result["merged_count"] > 0:
        result["merge_status"] = "partial"
    elif len(cand_codes & rank_codes) > 0:
        result["merge_status"] = "pending"
    else:
        result["merge_status"] = "no_overlap"

    return result


def generate_markdown(results: list[dict]) -> str:
    """Generate a markdown report from analysis results."""
    lines = [
        "# Agent Score Merge Coverage Report",
        "",
        f"**Generated At**: {datetime.now().isoformat()}",
        f"**Dates Analyzed**: {len(results)}",
        "",
        "## Summary Table",
        "",
        "| Date | Candidates | Ranking | Merged | Missing | Extra | Status | rank_hidden | raw_rank_leak |",
        "|------|-----------|---------|--------|---------|-------|--------|-------------|---------------|",
    ]

    for r in results:
        lines.append(
            f"| {r['date']} | {r['candidate_count']} | {r['ranking_item_count']} "
            f"| {r['merged_count']} | {r['missing_from_ranking_count']} "
            f"| {r['ranking_extra_count']} | {r['merge_status']} "
            f"| {r['rank_hidden']} | {r['raw_rank_leaked']} |"
        )

    lines.append("")

    # Per-date details
    lines.append("## Per-Date Details")
    lines.append("")

    for r in results:
        lines.append(f"### {r['date']}")
        lines.append("")
        lines.append(f"- **merge_status**: {r['merge_status']}")
        lines.append(f"- **candidate_count**: {r['candidate_count']}")
        lines.append(f"- **ranking_item_count**: {r['ranking_item_count']}")
        lines.append(f"- **merged_count**: {r['merged_count']}")
        lines.append(f"- **agent_score_merged**: {r['agent_score_merged']}")
        lines.append(f"- **agent_score_merge_count**: {r['agent_score_merge_count']}")
        lines.append(f"- **rank_hidden**: {r['rank_hidden']}")
        lines.append(f"- **raw_rank_leaked**: {r['raw_rank_leaked']}")

        if r["missing_from_ranking_codes"]:
            lines.append(f"- **missing_from_ranking** ({r['missing_from_ranking_count']}): {', '.join(r['missing_from_ranking_codes'])}")
        if r["ranking_extra_codes"]:
            lines.append(f"- **ranking_extra** ({r['ranking_extra_count']}): {', '.join(r['ranking_extra_codes'])}")

        # Diagnosis
        if r["merge_status"] == "missing_top30":
            lines.append("- **diagnosis**: top30_candidates.json not found")
        elif r["merge_status"] == "missing_ranking":
            lines.append("- **diagnosis**: aihf_stock_ranking.json not found")
        elif r["merge_status"] == "full":
            lines.append("- **diagnosis**: All candidates already have agent_score")
        elif r["merge_status"] == "pending":
            lines.append(f"- **diagnosis**: Merge not yet performed. {len(set(str(c.get('code','')) for c in []) & set(r['missing_from_ranking_codes']))} candidates match ranking but agent_score not written.")
        elif r["merge_status"] == "no_overlap":
            lines.append("- **diagnosis**: No code overlap between candidates and ranking — ranking was generated for a different candidate pool")
        elif r["merge_status"] == "partial":
            lines.append(f"- **diagnosis**: Partially merged. {r['missing_from_ranking_count']} candidates have no matching ranking item.")
        else:
            lines.append(f"- **diagnosis**: Status={r['merge_status']}")

        lines.append("")

    # Aggregate
    total_cands = sum(r["candidate_count"] for r in results)
    total_merged = sum(r["merged_count"] for r in results)
    total_missing = sum(r["missing_from_ranking_count"] for r in results)
    lines.append("## Aggregate")
    lines.append("")
    lines.append(f"- **Total candidates**: {total_cands}")
    lines.append(f"- **Already merged**: {total_merged}")
    lines.append(f"- **Missing from ranking**: {total_missing}")
    lines.append(f"- **Mergeable (pending)**: {sum(1 for r in results if r['merge_status'] == 'pending')}")
    lines.append(f"- **No overlap**: {sum(1 for r in results if r['merge_status'] == 'no_overlap')}")
    lines.append("")

    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose and backfill agent_score merge coverage"
    )
    parser.add_argument(
        "--dates",
        required=True,
        help="Comma-separated dates, e.g. 2026-06-29,2026-07-01",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually perform merges (default: dry-run诊断 only)",
    )
    parser.add_argument(
        "--bridge-dir",
        default=str(DEFAULT_BRIDGE_DIR),
        help="Base directory for agent_bridge",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for coverage report",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    dates = [d.strip() for d in args.dates.split(",") if d.strip()]
    if not dates:
        print("ERROR: no dates provided", file=sys.stderr)
        return 2

    bridge_dir = Path(args.bridge_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for date in sorted(dates):
        info = analyze_date(date, bridge_dir)

        # Apply merge if requested
        if args.apply and info["merge_status"] in ("pending", "partial", "no_overlap"):
            top30_path = bridge_dir / date / "top30_candidates.json"
            ranking_path = bridge_dir / date / "aihf_stock_ranking.json"
            if top30_path.exists() and ranking_path.exists():
                ok = merge_agent_scores_into_candidates(top30_path, ranking_path)
                if ok:
                    # Re-analyze after merge
                    info = analyze_date(date, bridge_dir)
                    info["applyPerformed"] = True
                else:
                    info["applyPerformed"] = False
                    info["applyError"] = "merge_agent_scores_into_candidates returned False"

        results.append(info)

    # Write JSON
    json_path = output_dir / "agent_score_merge_coverage.json"
    json_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Write Markdown
    md_path = output_dir / "agent_score_merge_coverage.md"
    md_path.write_text(generate_markdown(results), encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    print()

    # Summary
    for r in results:
        status_icon = {"full": "✅", "partial": "⚠️", "pending": "🔄",
                       "no_overlap": "❌", "missing_top30": "🚫",
                       "missing_ranking": "🚫"}.get(r["merge_status"], "?")
        print(f"  {status_icon} {r['date']}: {r['merge_status']} "
              f"({r['merged_count']}/{r['candidate_count']} merged, "
              f"{r['missing_from_ranking_count']} missing from ranking)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
