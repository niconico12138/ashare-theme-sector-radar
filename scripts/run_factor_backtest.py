#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run shadow-only factor value backtests over historical candidates."""

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
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.backtest.factor_value import (  # noqa: E402
    DEFAULT_HORIZONS,
    generate_markdown_report,
    run_factor_backtest,
)

DEFAULT_CANDIDATE_ROOT = PROJECT_ROOT / "reports" / "agent_bridge"
DEFAULT_RETURNS_ROOT = PROJECT_ROOT / "reports" / "forward_returns"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "factor_backtest"


def _default_start(end_date: str, lookback_days: int) -> str:
    end = datetime.strptime(end_date, "%Y-%m-%d")
    return (end - timedelta(days=lookback_days - 1)).strftime("%Y-%m-%d")



def parse_horizons(value: str) -> tuple[str, ...]:
    """Parse comma- or whitespace-separated horizon tokens."""
    horizons = []
    for part in re.split(r"[\s,]+", value.strip()):
        if not part:
            continue
        horizons.append(f"{part}d" if part.isdigit() else part)
    return tuple(horizons)

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Shadow-only factor value backtest")
    parser.add_argument("--start-date", default=None, help="Start date, YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="End date, YYYY-MM-DD")
    parser.add_argument("--lookback-days", type=int, default=120, help="Natural-day lookback when start date is omitted")
    parser.add_argument("--candidate-root", default=str(DEFAULT_CANDIDATE_ROOT), help="Directory containing DATE/top30_candidates.json")
    parser.add_argument("--returns-root", default=str(DEFAULT_RETURNS_ROOT), help="Directory containing DATE/forward_returns.json or DATE.json")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Base output directory")
    parser.add_argument("--horizons", default=",".join(DEFAULT_HORIZONS), help="Comma-separated horizons, e.g. 1d,3d,5d,10d")
    parser.add_argument("--min-samples", type=int, default=30, help="Minimum samples required per horizon")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    start_date = args.start_date or _default_start(args.end_date, args.lookback_days)
    horizons = parse_horizons(args.horizons)
    result = run_factor_backtest(
        start_date=start_date,
        end_date=args.end_date,
        candidate_root=Path(args.candidate_root),
        returns_root=Path(args.returns_root),
        horizons=horizons,
        min_samples=args.min_samples,
    )

    output_dir = Path(args.output_dir) / f"{start_date}_to_{args.end_date}"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "factor_value_backtest.json"
    md_path = output_dir / "factor_value_backtest.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(generate_markdown_report(result), encoding="utf-8")

    coverage = result.get("coverage", {})
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    print(
        "Coverage: "
        f"{coverage.get('usable_sample_count', 0)}/{coverage.get('candidate_count', 0)} "
        f"({coverage.get('coverage_ratio', 0):.1%})"
    )
    top = result.get("ranked_factors", [])[:5]
    if top:
        print("Top factors:")
        for item in top:
            print(
                f"- {item.get('factor_id')}: {item.get('value_label')} "
                f"IC={item.get('best_rank_ic')} horizon={item.get('best_horizon')}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


