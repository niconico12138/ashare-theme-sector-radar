"""Build an OOS-readiness report without reading event outputs or training models."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.industry_sector_oos_readiness import build_oos_readiness_report
from theme_sector_radar.reporting.paper_only_contract import validate_no_executable_instructions
from theme_sector_radar.reporting.strict_json import load_strict_json_with_sha256, write_strict_json_atomic


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=PROJECT_ROOT / "data_cache" / "sector_history")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "reports" / "paper_shadow" / "industry_sector_ml_shadow" / "dataset.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "paper_shadow" / "industry_sector_ml_shadow" / "oos_readiness.json",
    )
    args = parser.parse_args()
    dataset, dataset_sha = load_strict_json_with_sha256(args.dataset)
    report = build_oos_readiness_report(args.source_root, dataset_counts=dataset["counts"])
    report["dataset_sha256"] = dataset["dataset_sha256"]
    report["dataset_artifact_sha256"] = dataset_sha
    report["event_enhancement_ab"]["event_source_read"] = False
    validate_no_executable_instructions(report, context="industry sector OOS readiness")
    write_strict_json_atomic(args.output, report)
    _loaded, output_sha = load_strict_json_with_sha256(args.output)
    print(
        f"status={report['status']} source_end={report['latest_source_record_date']} "
        f"mature_label_end={report['latest_mature_label_date']} sha256={output_sha}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
