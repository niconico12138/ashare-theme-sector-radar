"""Audit local candidate feature sources without training a model."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.candidate_data_preparation import write_candidate_data_preparation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    root = PROJECT_ROOT / "reports" / "paper_shadow" / "ml_stock_ranker"
    parser.add_argument("--dataset", type=Path, default=root / "historical_research_v9_source_rebuild_bound_20260720" / "dataset.json")
    parser.add_argument("--feature-inventory", type=Path, default=root / "historical_iterations_round11_20_v2_20260720" / "feature_inventory.json")
    parser.add_argument("--direction-report", type=Path, default=PROJECT_ROOT / "reports" / "paper_shadow" / "industry_direction_2026-05-01_to_2026-07-16" / "industry_direction_scores.json")
    parser.add_argument("--output-root", type=Path, default=root / "candidate_data_preparation_v2_20260720")
    args = parser.parse_args()
    report = write_candidate_data_preparation(
        args.dataset, args.feature_inventory, args.direction_report, PROJECT_ROOT, args.output_root
    )
    summary = report["coverage_summary"]
    print(
        "status=planning_only_no_model_training "
        f"v9_dates={summary['v9_candidate_dates']} v9_rows={summary['v9_candidate_rows']} "
        f"physical_dates={summary['physical_candidate_source_dates']} "
        f"extra_dates={summary['extra_candidate_source_dates']} "
        "strict_direction_rows=0 strict_linkage_rows=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
