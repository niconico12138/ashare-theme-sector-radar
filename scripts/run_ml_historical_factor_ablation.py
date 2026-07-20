"""Run paper-only historical direction/Linkage V2 factor ablations."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.historical_factor_ablation import (
    run_historical_factor_ablation,
    validate_historical_factor_ablation_report,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json,
    write_strict_json_atomic,
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
        "--output-root",
        type=Path,
        default=PROJECT_ROOT
        / "reports"
        / "paper_shadow"
        / "ml_stock_ranker"
        / "historical_factor_ablation_v1_20260720",
    )
    args = parser.parse_args()
    if args.output_root.exists():
        raise FileExistsError(f"historical ablation output already exists: {args.output_root}")
    dataset = load_strict_json(args.dataset)
    report = run_historical_factor_ablation(dataset)
    validate_historical_factor_ablation_report(report)
    args.output_root.mkdir(parents=True)
    write_strict_json_atomic(args.output_root / "ablation_report.json", report)
    print(
        "status=research_only groups=4 candidate_dates="
        f"{report['source_coverage']['candidate_dates']} "
        f"candidate_rows={report['source_coverage']['candidate_rows']} "
        "strict_pit_eligible=false eligible_for_oos_claim=false "
        "promotion_allowed=false live_trading_allowed=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
