"""Run one verified model bundle on strictly as-of feature snapshots."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.predictor import (
    predict_shadow,
    unavailable_prediction_report,
)
from theme_sector_radar.ml.registry import load_model_bundle
from theme_sector_radar.ml.source import build_feature_rows_from_source
from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--expected-registry-sha256", required=True)
    parser.add_argument("--feature-source", required=True, type=Path)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--allow-fixture",
        action="store_true",
        help="Allow an explicitly classified synthetic fixture for architecture tests only.",
    )
    args = parser.parse_args()

    try:
        source, source_sha = load_strict_json_with_sha256(args.feature_source)
        rows = build_feature_rows_from_source(source, as_of_date=args.as_of)
        model = load_model_bundle(
            args.model_dir,
            expected_registry_sha256=args.expected_registry_sha256,
        )
        report = predict_shadow(model, rows, allow_fixture=args.allow_fixture)
        report["source"] = {
            "feature_source_path": str(args.feature_source),
            "feature_source_sha256": source_sha,
            "as_of_date": args.as_of,
        }
    except (ValueError, RuntimeError, OSError, FileNotFoundError) as exc:
        report = unavailable_prediction_report(
            model_version=None,
            reason="model_or_feature_source_unavailable",
            error=exc,
        )
    validate_no_executable_instructions(report, context="ML shadow prediction")
    write_strict_json_atomic(args.output, report)
    print(f"status={report['status']} predictions={len(report['predictions'])}")
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
