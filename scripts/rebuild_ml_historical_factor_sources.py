"""Rebuild exact historical direction/Linkage sources for paper-only stock ML."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.historical_factor_source_rebuild import (
    write_historical_factor_source_rebuild,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "reports" / "paper_shadow" / "ml_stock_ranker"
        / "historical_research_v9_source_rebuild_bound_20260720" / "dataset.json",
    )
    parser.add_argument(
        "--direction-report",
        type=Path,
        default=PROJECT_ROOT / "reports" / "paper_shadow"
        / "industry_direction_2026-05-01_to_2026-07-16" / "industry_direction_scores.json",
    )
    parser.add_argument(
        "--linkage-report",
        type=Path,
        action="append",
        default=None,
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "reports" / "paper_shadow" / "ml_stock_ranker"
        / "historical_factor_source_rebuild_v2_20260720",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Atomically replace only an exact three-file source-rebuild directory.",
    )
    args = parser.parse_args()
    linkage_reports = args.linkage_report or [
        PROJECT_ROOT / "reports" / "paper_shadow" / "linkage_v2_unified_stockdb"
        / "2026-07-16" / "unified_report.json"
    ]
    report = write_historical_factor_source_rebuild(
        args.dataset,
        args.direction_report,
        linkage_reports,
        args.output_root,
        replace_existing=args.replace_existing,
    )
    counts = report["counts"]
    print(
        "status=blocked_insufficient_strict_pit_coverage "
        f"candidate_rows={counts['candidate_rows']} "
        f"direction_observed={counts['direction_exact_name_observed_rows']} "
        f"direction_eligible={counts['direction_strict_pit_eligible_rows']} "
        f"linkage_eligible={counts['linkage_strict_pit_eligible_rows']} "
        "strict_pit_eligible=false promotion_allowed=false live_trading_allowed=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
