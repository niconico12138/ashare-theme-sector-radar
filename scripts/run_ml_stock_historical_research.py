"""Run a non-promotable historical reconstruction ML research cycle."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.historical_research import (
    HISTORICAL_DATASET_CLASSIFICATION,
    HISTORICAL_FEATURE_NAMES,
    HISTORICAL_FEATURE_PROFILES,
    bind_historical_walk_forward_report,
    build_historical_research_dataset,
    evaluate_historical_walk_forward,
    save_historical_research_bundle,
    validate_historical_research_dataset,
)
from theme_sector_radar.ml.ranker import (
    train_lambdarank,
    walk_forward_ranker_predictions,
)
from theme_sector_radar.ml.schema import DISCLAIMER, MODE
from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)


def _artifact(path: Path) -> dict[str, str]:
    _payload, sha256 = load_strict_json_with_sha256(path)
    return {"path": str(path.resolve()), "sha256": sha256}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-root", required=True, type=Path)
    parser.add_argument("--forward-root", required=True, type=Path)
    parser.add_argument("--calendar", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--model-dir", required=True, type=Path)
    parser.add_argument("--model-version", required=True)
    parser.add_argument("--min-train-dates", type=int, default=60)
    parser.add_argument("--test-dates", type=int, default=5)
    parser.add_argument("--purge-dates", type=int, default=5)
    parser.add_argument("--max-train-dates", type=int, default=None)
    parser.add_argument("--n-estimators", type=int, default=80)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument(
        "--feature-profile",
        choices=sorted(HISTORICAL_FEATURE_PROFILES),
        default="all_v1",
    )
    args = parser.parse_args()

    if args.output_root.exists():
        raise FileExistsError(f"historical research output already exists: {args.output_root}")
    if args.model_dir.exists():
        raise FileExistsError(f"historical research model already exists: {args.model_dir}")
    if min(args.min_train_dates, args.test_dates, args.purge_dates, args.n_estimators, args.top_k) <= 0:
        raise ValueError("historical research numeric arguments must be positive")
    if args.max_train_dates is not None and args.max_train_dates < args.min_train_dates:
        raise ValueError("max_train_dates must be at least min_train_dates")
    feature_names = HISTORICAL_FEATURE_PROFILES[args.feature_profile]

    dataset = build_historical_research_dataset(
        args.candidate_root,
        args.forward_root,
        args.calendar,
    )
    records = validate_historical_research_dataset(dataset)
    model_records = [
        {**row, "features": {name: row["features"][name] for name in feature_names}}
        for row in records
    ]
    model_universe = [
        {**row, "features": {name: row["features"][name] for name in feature_names}}
        for row in dataset["feature_universe_records"]
    ]
    predictions = walk_forward_ranker_predictions(
        model_records,
        prediction_universe_records=model_universe,
        feature_names=feature_names,
        min_train_dates=args.min_train_dates,
        test_dates=args.test_dates,
        purge_dates=args.purge_dates,
        max_train_dates=args.max_train_dates,
        max_label_horizon=5,
        n_estimators=args.n_estimators,
    )
    if predictions.get("status") != "ok":
        raise ValueError(
            "historical research walk-forward is unavailable: "
            f"{predictions.get('reason')}"
        )
    prediction_document = bind_historical_walk_forward_report(
        dataset,
        predictions,
        feature_profile=args.feature_profile,
    )
    evaluation = evaluate_historical_walk_forward(
        dataset,
        prediction_document,
        top_k=args.top_k,
    )
    final_model = train_lambdarank(
        model_records,
        feature_names=feature_names,
        n_estimators=args.n_estimators,
    )

    args.output_root.mkdir(parents=True)
    dataset_path = args.output_root / "dataset.json"
    prediction_path = args.output_root / "walk_forward_predictions.json"
    evaluation_path = args.output_root / "evaluation.json"
    write_strict_json_atomic(dataset_path, dataset)
    write_strict_json_atomic(prediction_path, prediction_document)
    write_strict_json_atomic(evaluation_path, evaluation)
    bundle = save_historical_research_bundle(
        final_model,
        args.model_dir,
        model_version=args.model_version,
        dataset_sha256=dataset["dataset_sha256"],
    )
    report = {
        "schema_version": "ml-stock-historical-research-cycle-v1",
        "mode": MODE,
        "status": "research_only",
        "dataset_classification": HISTORICAL_DATASET_CLASSIFICATION,
        "feature_profile": args.feature_profile,
        "source_counts": dict(dataset["counts"]),
        "split": {
            "min_train_dates": args.min_train_dates,
            "test_dates": args.test_dates,
            "purge_dates": args.purge_dates,
            "max_train_dates": args.max_train_dates,
            "fold_count": len(predictions["folds"]),
        },
        "artifacts": {
            "dataset": _artifact(dataset_path),
            "walk_forward_predictions": _artifact(prediction_path),
            "evaluation": _artifact(evaluation_path),
            "model_registry": {
                "path": str(Path(bundle["registry_path"]).resolve()),
                "sha256": bundle["registry_sha256"],
            },
            "model_binary": {
                "path": str(Path(bundle["model_path"]).resolve()),
                "sha256": bundle["model_sha256"],
            },
        },
        "metrics": dict(evaluation["metrics"]),
        "strict_pit_eligible": False,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(report, context="historical ML research cycle")
    report_path = args.output_root / "cycle_report.json"
    write_strict_json_atomic(report_path, report)
    print(
        "status=research_only "
        f"dates={dataset['counts']['labeled_dates']} "
        f"rows={dataset['counts']['labeled_rows']} "
        f"folds={len(predictions['folds'])} "
        "promotion_allowed=false live_trading_allowed=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
