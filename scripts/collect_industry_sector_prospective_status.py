"""Collect immutable industry OOS source snapshots and monitor 5-day maturity."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.industry_sector_prospective_collection import collect_prospective_collection_status
from theme_sector_radar.reporting.strict_json import load_strict_json_with_sha256


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=PROJECT_ROOT / "data_cache" / "sector_history")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "reports" / "paper_shadow" / "industry_sector_ml_shadow" / "prospective_collection",
    )
    args = parser.parse_args()
    report = collect_prospective_collection_status(args.source_root, args.output_root)
    _loaded, sha256 = load_strict_json_with_sha256(args.output_root / "prospective_collection_status.json")
    print(
        f"status={report['status']} complete_end={report['complete_trading_date_end']} "
        f"all_mature={report['all_test_labels_mature']} sha256={sha256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
