#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史数据可用性审计脚本

扫描指定日期范围内各数据源的可用性，确定可验证日期数量。

用法:
  python scripts/audit_historical_data_availability.py \
    --start-date 2026-01-01 --end-date 2026-07-08

  python scripts/audit_historical_data_availability.py \
    --start-date 2026-06-01 --end-date 2026-07-08 --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATE_RE = re.compile(r"^2026-\d{2}-\d{2}$")


def _scan_dir_dates(dir_path: Path) -> set[str]:
    """Scan a directory for YYYY-MM-DD subdirectories."""
    dates = set()
    if not dir_path.exists():
        return dates
    for item in dir_path.iterdir():
        if item.is_dir() and DATE_RE.match(item.name):
            dates.add(item.name)
    return dates


def _is_trading_day(date_str: str) -> bool:
    """Heuristic: skip Sundays (weekday 6)."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.weekday() != 6  # Sunday


def _next_trading_date(date_str: str) -> str | None:
    """Find the next trading day after date_str."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    for offset in range(1, 5):
        next_dt = dt + timedelta(days=offset)
        if next_dt.weekday() != 6:  # skip Sunday
            return next_dt.strftime("%Y-%m-%d")
    return None


def audit_availability(start_date: str, end_date: str) -> dict:
    """Audit data availability for each date in range."""
    # Scan all source directories
    sector_scores_dates = _scan_dir_dates(PROJECT_ROOT / "reports" / "sector_scores")
    sector_research_dates = _scan_dir_dates(PROJECT_ROOT / "reports" / "full90" / "sector_research")
    concept_rank_dates = _scan_dir_dates(PROJECT_ROOT / "reports" / "full_concept" / "unified_rank")
    unified_dates = _scan_dir_dates(PROJECT_ROOT / "reports" / "unified")
    agent_bridge_dates = _scan_dir_dates(PROJECT_ROOT / "reports" / "agent_bridge")
    validation_dates = _scan_dir_dates(PROJECT_ROOT / "reports" / "selection_validation")

    # Generate date range
    dt_start = datetime.strptime(start_date, "%Y-%m-%d")
    dt_end = datetime.strptime(end_date, "%Y-%m-%d")
    all_dates = []
    current = dt_start
    while current <= dt_end:
        d = current.strftime("%Y-%m-%d")
        all_dates.append(d)
        current += timedelta(days=1)

    # Classify each date
    direct_verify = []  # has validation data
    backfillable = []   # has unified + top30 but no validation
    needs_unified = []  # has sector_research but no unified
    needs_sector_inputs = []  # has sector_scores but no sector_research
    missing_sector_scores = []  # no sector_scores at all
    no_next_day_bars = []  # no forward data possible
    non_trading = []

    for d in all_dates:
        if not _is_trading_day(d):
            non_trading.append(d)
            continue

        has_sector_scores = d in sector_scores_dates
        has_sector_research = d in sector_research_dates
        has_concept = d in concept_rank_dates
        has_unified = d in unified_dates
        has_agent_bridge = d in agent_bridge_dates
        has_validation = d in validation_dates

        # Check if next day has bars
        next_d = _next_trading_date(d)
        has_next_day_bars = False
        if next_d:
            # Check if next day has any data source
            has_next_day_bars = (next_d in sector_scores_dates or
                                next_d in unified_dates or
                                next_d in agent_bridge_dates)

        if has_validation:
            direct_verify.append(d)
        elif has_agent_bridge and has_unified:
            backfillable.append(d)
        elif has_unified:
            backfillable.append(d)
        elif has_sector_research:
            needs_unified.append(d)
        elif has_sector_scores:
            needs_sector_inputs.append(d)
        else:
            missing_sector_scores.append(d)

        if not has_next_day_bars:
            no_next_day_bars.append(d)

    # Summary
    total_dates = len(all_dates)
    trading_days = total_dates - len(non_trading)

    # Project forward: how many more can we validate?
    # We need: sector_scores → sector_research → unified → agent_bridge → validation
    # Plus next-day bars for forward returns
    can_validate = len(direct_verify) + len(backfillable) + len(needs_unified) + len(needs_sector_inputs)

    return {
        "scan_range": f"{start_date} to {end_date}",
        "total_calendar_days": total_dates,
        "trading_days": trading_days,
        "non_trading_days": len(non_trading),
        "data_source_counts": {
            "sector_scores": len(sector_scores_dates),
            "sector_research": len(sector_research_dates),
            "concept_rank": len(concept_rank_dates),
            "unified": len(unified_dates),
            "agent_bridge": len(agent_bridge_dates),
            "validation": len(validation_dates),
        },
        "classification": {
            "direct_verify": {"count": len(direct_verify), "dates": direct_verify},
            "backfillable": {"count": len(backfillable), "dates": backfillable},
            "needs_unified": {"count": len(needs_unified), "dates": needs_unified},
            "needs_sector_inputs": {"count": len(needs_sector_inputs), "dates": needs_sector_inputs},
            "missing_sector_scores": {"count": len(missing_sector_scores), "dates": missing_sector_scores},
            "non_trading": {"count": len(non_trading), "dates": non_trading},
            "no_next_day_bars": {"count": len(no_next_day_bars), "dates": no_next_day_bars},
        },
        "projected_validatable": can_validate,
        "current_validated": len(direct_verify),
        "blocking_reasons": [],
    }


def generate_markdown(report: dict) -> str:
    lines = []
    lines.append(f"# Historical Data Availability Audit")
    lines.append(f"")
    lines.append(f"**Scan range**: {report['scan_range']}")
    lines.append(f"**Generated**: {datetime.now().isoformat()}")
    lines.append(f"")

    lines.append(f"## Summary")
    lines.append(f"")
    lines.append(f"- Calendar days: {report['total_calendar_days']}")
    lines.append(f"- Trading days: {report['trading_days']}")
    lines.append(f"- Non-trading days: {report['non_trading_days']}")
    lines.append(f"")

    lines.append(f"## Data Source Counts")
    lines.append(f"")
    for src, count in report['data_source_counts'].items():
        lines.append(f"- {src}: {count} dates")
    lines.append(f"")

    lines.append(f"## Date Classification")
    lines.append(f"")
    cls = report['classification']
    for key in ['direct_verify', 'backfillable', 'needs_unified', 'needs_sector_inputs', 'missing_sector_scores', 'non_trading']:
        info = cls[key]
        lines.append(f"### {key} ({info['count']} dates)")
        if info['dates']:
            lines.append(f"  {', '.join(info['dates'][:10])}{'...' if len(info['dates']) > 10 else ''}")
        lines.append(f"")

    lines.append(f"## Projection")
    lines.append(f"")
    lines.append(f"- Currently validated: {report['current_validated']}")
    lines.append(f"- Projected validatable after backfill: {report['projected_validatable']}")
    lines.append(f"- Target: 60 valid trading days")
    target_met = report['projected_validatable'] >= 60
    lines.append(f"- **Target met**: {'YES' if target_met else 'NO'}")
    if not target_met:
        lines.append(f"- **Gap**: {60 - report['projected_validatable']} more dates needed")
    lines.append(f"")

    if report.get('blocking_reasons'):
        lines.append(f"## Blocking Reasons")
        lines.append(f"")
        for reason in report['blocking_reasons']:
            lines.append(f"- {reason}")
        lines.append(f"")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Audit historical data availability")
    parser.add_argument("--start-date", default="2026-01-01")
    parser.add_argument("--end-date", default="2026-07-08")
    parser.add_argument("--output-dir", default="reports/selection_validation/data_availability")
    args = parser.parse_args()

    print(f"  Scanning {args.start_date} to {args.end_date}...")
    report = audit_availability(args.start_date, args.end_date)

    # Save
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "historical_data_availability.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ JSON: {json_path}")

    md_path = out_dir / "historical_data_availability.md"
    md_path.write_text(generate_markdown(report), encoding="utf-8")
    print(f"  ✅ Markdown: {md_path}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"  Data Availability Summary")
    print(f"{'='*60}")
    print(f"  Calendar days: {report['total_calendar_days']}")
    print(f"  Trading days: {report['trading_days']}")
    print(f"  Currently validated: {report['current_validated']}")
    print(f"  Projected validatable: {report['projected_validatable']}")
    cls = report['classification']
    print(f"  Direct verify: {cls['direct_verify']['count']}")
    print(f"  Backfillable: {cls['backfillable']['count']}")
    print(f"  Needs unified: {cls['needs_unified']['count']}")
    print(f"  Needs sector inputs: {cls['needs_sector_inputs']['count']}")
    print(f"  Missing sector_scores: {cls['missing_sector_scores']['count']}")
    print(f"  No next-day bars: {cls['no_next_day_bars']['count']}")
    target_met = report['projected_validatable'] >= 60
    gap = 60 - report["projected_validatable"]
    print(f"  Target 60 met: {'YES' if target_met else f'NO (gap={gap})'}")


if __name__ == "__main__":
    main()
