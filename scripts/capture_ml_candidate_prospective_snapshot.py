"""Capture or report the paper-only prospective raw candidate archive."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.prospective_candidate_archive import (
    capture_prospective_daily_snapshot,
    write_prospective_archive_reports,
)
from theme_sector_radar.reporting.strict_json import load_strict_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--report-as-of-date", required=True)
    parser.add_argument(
        "--capture-request",
        type=Path,
        help="Optional same-day capture request. Omit for report-only mode.",
    )
    args = parser.parse_args()

    captured = None
    if args.capture_request is not None:
        request = load_strict_json(args.capture_request)
        captured = capture_prospective_daily_snapshot(
            archive_root=args.archive_root,
            request=request,
        )
    summary = write_prospective_archive_reports(
        args.archive_root,
        args.output_root,
        report_as_of_date=args.report_as_of_date,
    )
    print(
        "status=blocked_raw_capture_only "
        f"captured={captured is not None} "
        f"future_comparison_ready={summary['future_comparison_ready']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
