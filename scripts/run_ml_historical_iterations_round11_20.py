"""Run only rounds 11-20 of paper-only historical stock-ML research."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.historical_iteration_extension import (
    write_historical_iteration_extension,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    root = PROJECT_ROOT / "reports" / "paper_shadow" / "ml_stock_ranker"
    parser.add_argument(
        "--dataset", type=Path,
        default=root / "historical_research_v9_source_rebuild_bound_20260720" / "dataset.json",
    )
    parser.add_argument(
        "--baseline", type=Path,
        default=root / "historical_factor_ablation_v1_20260720" / "ablation_report.json",
    )
    parser.add_argument(
        "--previous-suite", type=Path,
        default=root / "historical_iterations_v2_20260720" / "suite_report.json",
    )
    parser.add_argument(
        "--source-report", type=Path,
        default=root / "historical_factor_source_rebuild_v2_20260720" / "rebuild_report.json",
    )
    parser.add_argument(
        "--output-root", type=Path,
        default=root / "historical_iterations_round11_20_v2_20260720",
    )
    args = parser.parse_args()
    report = write_historical_iteration_extension(
        args.dataset,
        args.baseline,
        args.previous_suite,
        args.source_report,
        args.output_root,
    )
    completed = sum(item["status"] == "completed" for item in report["rounds"])
    print(
        f"status=research_only rounds=10 completed={completed} total_iterations=20 "
        f"feature_inventory_sha256={report['feature_inventory']['inventory_sha256']} "
        "direction_linkage_validated=false strict_pit_eligible=false "
        "promotion_allowed=false live_trading_allowed=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
