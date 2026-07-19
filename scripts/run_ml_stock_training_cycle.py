"""Run the verified ML stock-ranker shadow training/evaluation cycle."""

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
from theme_sector_radar.ml.evaluation import evaluate_rule_vs_ml_shadow
from theme_sector_radar.ml.ranker import train_lambdarank, walk_forward_ranker_predictions
from theme_sector_radar.ml.registry import save_model_bundle
from theme_sector_radar.ml.contract import canonical_sha256, optional_ml_dependency_readiness
from theme_sector_radar.ml.schema import DISCLAIMER, MODE
from theme_sector_radar.reporting.paper_only_contract import validate_no_executable_instructions
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)


def _write_blocked(output_root: Path, readiness: dict, *, reason: str) -> int:
    output_root.mkdir(parents=True, exist_ok=True)
    write_strict_json_atomic(
        output_root / "readiness.json",
        readiness,
    )
    cycle = {
        "schema_version": "ml-stock-training-cycle-v1",
        "mode": MODE,
        "status": "blocked",
        "reason": reason,
        "readiness": readiness,
        "promotion_allowed": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(cycle, context="ML training cycle")
    write_strict_json_atomic(output_root / "cycle_report.json", cycle)
    print(f"status=blocked reason={reason}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--min-train-dates", type=int, default=60)
    parser.add_argument("--test-dates", type=int, default=20)
    parser.add_argument("--purge-dates", type=int, default=5)
    parser.add_argument("--n-estimators", type=int, default=80)
    parser.add_argument("--hybrid-quant-weight", type=float, default=0.65)
    parser.add_argument("--hybrid-linkage-weight", type=float, default=0.35)
    parser.add_argument("--hybrid-partial-linkage-weight", type=float, default=0.20)
    parser.add_argument("--sector-history-root", type=Path, default=None)
    args = parser.parse_args()

    try:
        readiness = build_archive_readiness_report(
            args.archive_root,
            sector_history_date_count=(
                count_sector_history_dates(args.sector_history_root)
                if args.sector_history_root is not None
                else 0
            ),
        )
        if not readiness["model_training_ready"]:
            return _write_blocked(
                args.output_root,
                readiness,
                reason="readiness_gate_blocked_training",
            )
        dependencies = optional_ml_dependency_readiness()
        if dependencies["status"] != "ready":
            readiness["blocking_reasons"] = list(readiness.get("blocking_reasons") or []) + [
                "optional_ml_dependencies_missing"
            ]
            return _write_blocked(
                args.output_root,
                readiness,
                reason="optional_ml_dependencies_missing",
            )

        loaded = load_verified_training_inputs(args.archive_root)
        evidence = loaded["evidence"]
        args.output_root.mkdir(parents=True, exist_ok=True)
        baseline_path = args.output_root / "baseline_rows.json"
        baseline_document = {
            "schema_version": "ml-stock-baseline-source-v1",
            "mode": MODE,
            "status": "ok",
            "strict_pit_eligible": True,
            "pit_evidence_sha256": evidence["evidence_sha256"],
            "hybrid_defaults": {
                "quant_weight": args.hybrid_quant_weight,
                "linkage_v2_weight": args.hybrid_linkage_weight,
                "partial_linkage_v2_weight": args.hybrid_partial_linkage_weight,
            },
            "records": loaded["baseline_rows"],
            "promotion_allowed": False,
            "generated_at": datetime.now().astimezone().isoformat(),
            "disclaimer": DISCLAIMER,
        }
        validate_no_executable_instructions(
            baseline_document, context="ML training baseline source"
        )
        write_strict_json_atomic(baseline_path, baseline_document)
        _baseline_loaded, baseline_sha = load_strict_json_with_sha256(
            baseline_path
        )
        dataset = build_training_dataset(
            loaded["feature_rows"],
            loaded["label_rows"],
            strict_pit_eligible=False,
            source_manifest={
                "archive_root": str(Path(args.archive_root).resolve()),
                "pit_evidence_sha256": evidence["evidence_sha256"],
                "baseline_source": {
                    "path": str(baseline_path.resolve()),
                    "sha256": baseline_sha,
                },
            },
            pit_evidence=evidence,
        )
        dataset_path = args.output_root / "dataset.json"
        write_strict_json_atomic(dataset_path, dataset)
        dataset_loaded, dataset_file_sha = load_strict_json_with_sha256(dataset_path)
        records = validate_training_dataset(dataset_loaded)
        walk_forward = walk_forward_ranker_predictions(
            records,
            prediction_universe_records=list(dataset_loaded["feature_universe_records"]),
            min_train_dates=args.min_train_dates,
            test_dates=args.test_dates,
            purge_dates=args.purge_dates,
            max_label_horizon=5,
            n_estimators=args.n_estimators,
        )
        if walk_forward.get("status") != "ok":
            return _write_blocked(
                args.output_root,
                readiness,
                reason=str(walk_forward.get("reason") or "walk_forward_blocked"),
            )
        prediction_rows = list(walk_forward["predictions"])
        prediction_identities = {
            (str(row["as_of_date"]), str(row["stock_code"]))
            for row in prediction_rows
        }
        prediction_universe_rows = [
            row
            for row in dataset_loaded["feature_universe_records"]
            if (str(row["as_of_date"]), str(row["stock_code"]))
            in prediction_identities
        ]
        walk_forward_document = {
            "schema_version": "ml-stock-walk-forward-predictions-v1",
            "mode": MODE,
            "status": "ok",
            "fixture_only": False,
            "strict_pit_eligible": True,
            "eligible_for_oos_claim": False,
            "dataset_sha256": dataset_loaded["dataset_sha256"],
            "dataset_file_sha256": dataset_file_sha,
            "split": {
                "type": walk_forward["split_type"],
                "min_train_dates": walk_forward["min_train_dates"],
                "test_dates": walk_forward["test_dates"],
                "purge_dates": walk_forward["purge_dates"],
                "max_label_horizon": walk_forward["max_label_horizon"],
                "folds": walk_forward["folds"],
            },
            "prediction_rows_sha256": canonical_sha256(prediction_rows),
            "prediction_universe_sha256": canonical_sha256(
                prediction_universe_rows
            ),
            "predictions": prediction_rows,
            "promotion_allowed": False,
            "generated_at": datetime.now().astimezone().isoformat(),
            "disclaimer": DISCLAIMER,
        }
        walk_forward_path = args.output_root / "walk_forward_predictions.json"
        validate_no_executable_instructions(
            walk_forward_document, context="ML training walk-forward"
        )
        write_strict_json_atomic(walk_forward_path, walk_forward_document)
        _walk_forward_loaded, walk_forward_sha = load_strict_json_with_sha256(
            walk_forward_path
        )
        prediction_report = walk_forward_document
        evaluation = evaluate_rule_vs_ml_shadow(
            prediction_report,
            dataset_loaded,
            loaded["baseline_rows"],
            top_ks=(10, 20, 30),
            horizons=(1, 3, 5),
            baseline_strict_pit_eligible=True,
            hybrid_quant_weight=args.hybrid_quant_weight,
            hybrid_linkage_weight=args.hybrid_linkage_weight,
            hybrid_partial_linkage_weight=args.hybrid_partial_linkage_weight,
        )
        evaluation_path = args.output_root / "evaluation.json"
        write_strict_json_atomic(evaluation_path, evaluation)
        trained = train_lambdarank(records, n_estimators=args.n_estimators)
        bundle = save_model_bundle(
            trained,
            args.model_dir,
            model_version=args.model_version,
            dataset_sha256=dataset_loaded["dataset_sha256"],
            strict_pit_eligible=True,
            dataset_classification="observed_research",
            model_available_from=max(
                str(row["training_label_end_date"]) for row in records
            ),
            pit_evidence=evidence,
        )
        training_report = {
            "schema_version": "ml-stock-training-report-v1",
            "mode": MODE,
            "status": "ok",
            "model_version": args.model_version,
            "dependency_readiness": dependencies,
            "dataset": {
                "path": str(dataset_path),
                "file_sha256": dataset_file_sha,
                "dataset_sha256": dataset_loaded["dataset_sha256"],
                "strict_pit_eligible": True,
            },
            "model_bundle": {
                "registry_path": bundle["registry_path"],
                "registry_sha256": bundle["registry_sha256"],
                "model_path": bundle["model_path"],
                "model_sha256": bundle["model_sha256"],
            },
            "walk_forward": {
                "path": str(walk_forward_path),
                "sha256": walk_forward_sha,
                "fold_count": len(walk_forward["folds"]),
                "prediction_count": len(walk_forward["predictions"]),
                "purge_dates": args.purge_dates,
            },
            "evaluation": {"path": str(evaluation_path)},
            "strict_pit_eligible": True,
            "eligible_for_oos_claim": False,
            "promotion_allowed": False,
            "generated_at": datetime.now().astimezone().isoformat(),
            "disclaimer": DISCLAIMER,
        }
        validate_no_executable_instructions(training_report, context="ML training report")
        write_strict_json_atomic(args.output_root / "training_report.json", training_report)
        cycle = {
            "schema_version": "ml-stock-training-cycle-v1",
            "mode": MODE,
            "status": "trained_shadow",
            "readiness": readiness,
            "training_report": str(args.output_root / "training_report.json"),
            "evaluation_report": str(evaluation_path),
            "promotion_allowed": False,
            "generated_at": datetime.now().astimezone().isoformat(),
            "disclaimer": DISCLAIMER,
        }
        validate_no_executable_instructions(cycle, context="ML training cycle")
        write_strict_json_atomic(args.output_root / "cycle_report.json", cycle)
        print(f"status=trained_shadow model={args.model_version}")
        return 0
    except (ValueError, RuntimeError, OSError, FileNotFoundError) as exc:
        return _write_blocked(
            args.output_root,
            {
                "schema_version": "ml-stock-data-readiness-v1",
                "mode": MODE,
                "status": "blocked",
                "model_training_ready": False,
                "strict_pit_eligible": False,
                "blocking_reasons": ["training_cycle_exception_fail_closed"],
                "promotion_allowed": False,
                "disclaimer": DISCLAIMER,
            },
            reason="training_cycle_exception_fail_closed",
        )


if __name__ == "__main__":
    raise SystemExit(main())
