"""Run ten independent paper-only historical ML shadow iterations."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.historical_iteration import (
    write_historical_iteration_suite,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT
        / "reports"
        / "paper_shadow"
        / "ml_stock_ranker"
        / "historical_research_v9_source_rebuild_bound_20260720"
        / "dataset.json",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=PROJECT_ROOT
        / "reports"
        / "paper_shadow"
        / "ml_stock_ranker"
        / "historical_factor_ablation_v1_20260720"
        / "ablation_report.json",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT
        / "reports"
        / "paper_shadow"
        / "ml_stock_ranker"
        / "historical_iterations_v2_20260720",
    )
    args = parser.parse_args()
    report = write_historical_iteration_suite(
        args.dataset,
        args.baseline,
        args.output_root,
    )
    print(
        "status=research_only iterations="
        f"{report['iteration_count']} candidate_dates="
        f"{report['source_coverage']['candidate_dates']} candidate_rows="
        f"{report['source_coverage']['candidate_rows']} "
        "strict_pit_eligible=false eligible_for_oos_claim=false "
        "promotion_allowed=false live_trading_allowed=false"
    )
    for item in report["iterations"]:
        print(
            f"iteration={item['iteration']} id={item['id']} "
            f"status={item['status']} decision={item['decision']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
