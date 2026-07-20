"""Run the pre-registered paper-only prospective stock comparison."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.prospective_comparison import (
    run_prospective_comparison,
)
from theme_sector_radar.reporting.strict_json import load_strict_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--report-as-of-date", required=True)
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--labels-sha256")
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--predictions-sha256")
    parser.add_argument("--event-manifest", type=Path)
    args = parser.parse_args()

    event_manifest = (
        load_strict_json(args.event_manifest) if args.event_manifest else None
    )
    result = run_prospective_comparison(
        archive_root=args.archive_root,
        output_root=args.output_root,
        report_as_of_date=args.report_as_of_date,
        labels_path=args.labels,
        labels_sha256=args.labels_sha256,
        predictions_path=args.predictions,
        predictions_sha256=args.predictions_sha256,
        event_manifest=event_manifest,
    )
    report = result["report"]
    print(
        f"status={report['status']} "
        f"snapshot_dates={report['counts']['snapshot_dates']} "
        f"metrics_available={report['metrics_available']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
