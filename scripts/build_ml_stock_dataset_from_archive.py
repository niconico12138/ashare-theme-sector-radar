"""Build a strict PIT ML dataset and independent baselines from the daily archive."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.accumulation import (
    build_archive_readiness_report,
    count_sector_history_dates,
    load_verified_training_inputs,
)
from theme_sector_radar.ml.dataset import build_training_dataset, validate_training_dataset
from theme_sector_radar.ml.schema import DATASET_SCHEMA_VERSION, DISCLAIMER, MODE
from theme_sector_radar.reporting.paper_only_contract import validate_no_executable_instructions
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)


def _write_blocked(args, readiness: dict) -> int:
    baseline = {
        "schema_version": "ml-stock-baseline-source-v1",
        "mode": MODE,
        "status": "blocked",
        "reason": "readiness_gate_blocked_dataset_build",
        "strict_pit_eligible": False,
        "records": [],
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    dataset = {
        "schema_version": DATASET_SCHEMA_VERSION,
        "mode": MODE,
        "status": "blocked",
        "reason": "readiness_gate_blocked_dataset_build",
        "strict_pit_eligible": False,
        "pit_evidence_status": readiness.get("pit_evidence_status"),
        "records": [],
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    report = {
        "schema_version": "ml-stock-archive-dataset-build-v1",
        "mode": MODE,
        "status": "blocked",
        "reason": "readiness_gate_blocked_dataset_build",
        "readiness": readiness,
        "dataset_path": str(args.dataset_output),
        "baseline_path": str(args.baseline_output),
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    for payload, context in (
        (baseline, "ML blocked baseline source"),
        (dataset, "ML blocked archive dataset"),
        (report, "ML blocked archive dataset build"),
    ):
        validate_no_executable_instructions(payload, context=context)
    write_strict_json_atomic(args.readiness_output, readiness)
    write_strict_json_atomic(args.baseline_output, baseline)
    write_strict_json_atomic(args.dataset_output, dataset)
    write_strict_json_atomic(args.report_output, report)
    print("status=blocked reason=readiness_gate_blocked_dataset_build")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", required=True, type=Path)
    parser.add_argument("--dataset-output", required=True, type=Path)
    parser.add_argument("--baseline-output", required=True, type=Path)
    parser.add_argument("--readiness-output", required=True, type=Path)
    parser.add_argument("--report-output", required=True, type=Path)
    parser.add_argument("--sector-history-root", type=Path, default=None)
    args = parser.parse_args()

    sector_history_date_count = (
        count_sector_history_dates(args.sector_history_root)
        if args.sector_history_root is not None
        else 0
    )
    readiness = build_archive_readiness_report(
        args.archive_root,
        sector_history_date_count=sector_history_date_count,
    )
    if not readiness["model_training_ready"]:
        return _write_blocked(args, readiness)

    loaded = load_verified_training_inputs(args.archive_root)
    evidence = loaded["evidence"]
    baseline = {
        "schema_version": "ml-stock-baseline-source-v1",
        "mode": MODE,
        "status": "ok",
        "strict_pit_eligible": True,
        "pit_evidence_sha256": evidence["evidence_sha256"],
        "hybrid_defaults": {
            "quant_weight": 0.65,
            "linkage_v2_weight": 0.35,
            "partial_linkage_v2_weight": 0.20,
        },
        "records": loaded["baseline_rows"],
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(baseline, context="ML baseline source")
    write_strict_json_atomic(args.baseline_output, baseline)
    _baseline_loaded, baseline_sha = load_strict_json_with_sha256(
        args.baseline_output
    )
    dataset = build_training_dataset(
        loaded["feature_rows"],
        loaded["label_rows"],
        strict_pit_eligible=False,
        pit_evidence=evidence,
        source_manifest={
            "archive_root": str(args.archive_root.resolve()),
            "pit_evidence_sha256": evidence["evidence_sha256"],
            "baseline_source": {
                "path": str(args.baseline_output.resolve()),
                "sha256": baseline_sha,
            },
        },
    )
    validate_training_dataset(dataset)
    validate_no_executable_instructions(dataset, context="ML strict archive dataset")
    write_strict_json_atomic(args.dataset_output, dataset)
    _dataset_loaded, dataset_file_sha = load_strict_json_with_sha256(
        args.dataset_output
    )
    report = {
        "schema_version": "ml-stock-archive-dataset-build-v1",
        "mode": MODE,
        "status": "ok",
        "strict_pit_eligible": True,
        "readiness": readiness,
        "dataset": {
            "path": str(args.dataset_output.resolve()),
            "file_sha256": dataset_file_sha,
            "dataset_sha256": dataset["dataset_sha256"],
        },
        "baseline": {
            "path": str(args.baseline_output.resolve()),
            "sha256": baseline_sha,
            "row_count": len(loaded["baseline_rows"]),
        },
        "pit_evidence_sha256": evidence["evidence_sha256"],
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(report, context="ML archive dataset build")
    write_strict_json_atomic(args.readiness_output, readiness)
    write_strict_json_atomic(args.report_output, report)
    print(
        f"status=ok dates={dataset['date_range']['date_count']} "
        f"rows={dataset['counts']['joined_rows']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
