"""Build a strict paper/shadow stock-ranker dataset from separated sources."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.dataset import build_training_dataset
from theme_sector_radar.ml.source import (
    build_feature_rows_from_source,
    build_label_rows_from_source,
)
from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)
from theme_sector_radar.data.trading_calendar import load_trading_calendar


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-source", required=True, type=Path)
    parser.add_argument("--label-source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--trading-calendar-path", required=True, type=Path)
    parser.add_argument("--expected-calendar-sha256", required=True)
    args = parser.parse_args()

    feature_source, feature_sha = load_strict_json_with_sha256(args.feature_source)
    label_source, label_sha = load_strict_json_with_sha256(args.label_source)
    features = build_feature_rows_from_source(feature_source)
    raw_dates = label_source.get("trading_dates") or (
        (label_source.get("trading_calendar") or {}).get("dates")
    )
    if not isinstance(raw_dates, list) or not raw_dates:
        raise ValueError("label source trading dates are required")
    calendar = load_trading_calendar(
        args.trading_calendar_path,
        as_of=max(str(value) for value in raw_dates),
        include_future=True,
    )
    if calendar["sha256"] != str(args.expected_calendar_sha256).lower():
        raise ValueError("trading calendar SHA mismatch")
    labels = build_label_rows_from_source(
        label_source, trading_calendar=calendar
    )
    if feature_source.get("strict_pit_eligible") or label_source.get(
        "strict_pit_eligible"
    ):
        raise ValueError(
            "self-attested strict PIT is not accepted in ML Shadow Stage 1"
        )
    fixture_only = bool(feature_source.get("fixture_only", False)) or bool(
        label_source.get("fixture_only", False)
    )
    dataset = build_training_dataset(
        features,
        labels,
        strict_pit_eligible=False,
        fixture_only=fixture_only,
        source_manifest={
            "feature_source": {"path": str(args.feature_source), "sha256": feature_sha},
            "label_source": {"path": str(args.label_source), "sha256": label_sha},
            "trading_calendar": {
                "path": str(args.trading_calendar_path.resolve()),
                "sha256": calendar["sha256"],
                "source": calendar["source"],
                "requested_start": calendar["requested_start"],
                "requested_end": calendar["requested_end"],
            },
        },
    )
    validate_no_executable_instructions(dataset, context="ML training dataset")
    write_strict_json_atomic(args.output, dataset)
    print(
        f"status={dataset['status']} dates={dataset['date_range']['date_count']} "
        f"rows={dataset['counts']['joined_rows']} sha256={dataset['dataset_sha256']}"
    )
    return 0 if dataset["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
