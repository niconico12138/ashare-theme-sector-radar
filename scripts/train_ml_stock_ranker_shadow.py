"""Train and register the optional LightGBM stock ranker in shadow mode."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.contract import optional_ml_dependency_readiness
from theme_sector_radar.ml.dataset import validate_training_dataset
from theme_sector_radar.ml.ranker import (
    train_lambdarank,
    walk_forward_ranker_predictions,
)
from theme_sector_radar.ml.registry import save_model_bundle
from theme_sector_radar.ml.schema import DISCLAIMER, MODE
from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)


def _write_blocked(args, dataset_sha: str, *, reason: str, readiness=None) -> int:
    report = {
        "schema_version": "ml-stock-training-report-v1",
        "mode": MODE,
        "status": "blocked",
        "reason": reason,
        "dependency_readiness": readiness,
        "dataset_file_sha256": dataset_sha,
        "strict_pit_eligible": False,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(report, context="ML training readiness")
    write_strict_json_atomic(args.report, report)
    write_strict_json_atomic(
        args.walk_forward_output,
        {
            "schema_version": "ml-stock-walk-forward-predictions-v1",
            "mode": MODE,
            "status": "blocked",
            "reason": reason,
            "predictions": [],
            "promotion_allowed": False,
            "generated_at": datetime.now().astimezone().isoformat(),
            "disclaimer": DISCLAIMER,
        },
    )
    return 2


def _write_unavailable(args, dataset_sha: str, readiness, *, reason: str) -> int:
    return _write_blocked(
        args,
        dataset_sha,
        readiness=readiness,
        reason=reason,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--expected-dataset-file-sha256", required=True)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--walk-forward-output", required=True, type=Path)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--model-available-from", default=None)
    parser.add_argument("--min-train-dates", type=int, default=60)
    parser.add_argument("--test-dates", type=int, default=20)
    parser.add_argument("--purge-dates", type=int, default=5)
    parser.add_argument("--n-estimators", type=int, default=80)
    args = parser.parse_args()

    dataset, dataset_file_sha = load_strict_json_with_sha256(args.dataset)
    if dataset_file_sha != str(args.expected_dataset_file_sha256).lower():
        raise ValueError("dataset file SHA mismatch")
    if dataset.get("status") != "ok":
        return _write_blocked(
            args, dataset_file_sha, reason="training_dataset_not_ready"
        )
    if (
        not bool(dataset.get("fixture_only", False))
        and dataset.get("strict_pit_eligible") is not True
    ):
        return _write_blocked(
            args,
            dataset_file_sha,
            reason="strict_pit_evidence_required_for_observed_training",
        )
    records = validate_training_dataset(dataset)
    readiness = optional_ml_dependency_readiness()
    if readiness["status"] != "ready":
        return _write_unavailable(
            args, dataset_file_sha, readiness, reason="optional_ml_dependencies_missing"
        )
    walk_forward = walk_forward_ranker_predictions(
        records,
        prediction_universe_records=list(dataset["feature_universe_records"]),
        min_train_dates=args.min_train_dates,
        test_dates=args.test_dates,
        purge_dates=args.purge_dates,
        max_label_horizon=5,
        n_estimators=args.n_estimators,
    )
    if walk_forward["status"] != "ok":
        return _write_unavailable(
            args, dataset_file_sha, readiness, reason="insufficient_walk_forward_dates"
        )
    walk_forward_document = {
        "schema_version": "ml-stock-walk-forward-predictions-v1",
        "mode": MODE,
        "status": "ok",
        "fixture_only": bool(dataset.get("fixture_only", False)),
        "strict_pit_eligible": bool(dataset.get("strict_pit_eligible", False)),
        "eligible_for_oos_claim": False,
        "split": {
            "type": walk_forward["split_type"],
            "purge_dates": walk_forward["purge_dates"],
            "max_label_horizon": walk_forward["max_label_horizon"],
            "folds": walk_forward["folds"],
        },
        "predictions": [
            {
                key: row[key]
                for key in (
                    "fold", "as_of_date", "stock_code", "sector_name",
                    "prediction", "ml_quant_score_shadow", "rank"
                )
            }
            for row in walk_forward["predictions"]
        ],
        "promotion_allowed": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(
        walk_forward_document, context="ML walk-forward predictions"
    )
    write_strict_json_atomic(args.walk_forward_output, walk_forward_document)
    _walk_forward_loaded, walk_forward_sha = load_strict_json_with_sha256(
        args.walk_forward_output
    )

    trained = train_lambdarank(records, n_estimators=args.n_estimators)
    source_manifest = dataset.get("source_manifest")
    fixture_only = bool(dataset.get("fixture_only", False))
    if isinstance(source_manifest, dict) and "fixture_only" in source_manifest:
        if bool(source_manifest["fixture_only"]) != fixture_only:
            raise ValueError("dataset fixture classification mismatch")
        fixture_only = bool(source_manifest["fixture_only"])
    bundle = save_model_bundle(
        trained,
        args.model_dir,
        model_version=args.model_version,
        dataset_sha256=dataset["dataset_sha256"],
        strict_pit_eligible=bool(dataset.get("strict_pit_eligible", False)),
        dataset_classification=(
            "synthetic_fixture"
            if fixture_only
            else "observed_research"
        ),
        model_available_from=(
            args.model_available_from
            or datetime.now().astimezone().date().isoformat()
        ),
        pit_evidence=(
            dataset.get("pit_evidence")
            if bool(dataset.get("strict_pit_eligible", False))
            else None
        ),
    )
    report = {
        "schema_version": "ml-stock-training-report-v1",
        "mode": MODE,
        "status": "ok",
        "model_version": args.model_version,
        "dependency_readiness": readiness,
        "dataset": {
            "path": str(args.dataset),
            "file_sha256": dataset_file_sha,
            "dataset_sha256": dataset["dataset_sha256"],
            "strict_pit_eligible": bool(dataset.get("strict_pit_eligible", False)),
        },
        "model_bundle": {
            "registry_path": bundle["registry_path"],
            "registry_sha256": bundle["registry_sha256"],
            "model_path": bundle["model_path"],
            "model_sha256": bundle["model_sha256"],
        },
        "walk_forward": {
            "path": str(args.walk_forward_output),
            "sha256": walk_forward_sha,
            "fold_count": len(walk_forward["folds"]),
            "prediction_count": len(walk_forward["predictions"]),
            "purge_dates": args.purge_dates,
        },
        "strict_pit_eligible": bool(dataset.get("strict_pit_eligible", False)),
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(report, context="ML training report")
    write_strict_json_atomic(args.report, report)
    print(
        f"status=ok model={args.model_version} registry_sha256={bundle['registry_sha256']} "
        f"walk_forward_predictions={len(walk_forward['predictions'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
