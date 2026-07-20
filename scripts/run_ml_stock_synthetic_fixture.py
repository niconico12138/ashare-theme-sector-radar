"""Generate a deterministic technical fixture for the ML shadow pipeline."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.dataset import build_training_dataset
from theme_sector_radar.ml.evaluation import evaluate_rule_vs_ml_shadow
from theme_sector_radar.ml.predictor import predict_shadow
from theme_sector_radar.ml.ranker import train_lambdarank, walk_forward_ranker_predictions
from theme_sector_radar.ml.registry import load_model_bundle, save_model_bundle
from theme_sector_radar.ml.schema import DISCLAIMER, MODE
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


def _sources(*, anchor_date: date) -> tuple[dict, dict]:
    codes = [f"{index + 1:06d}" for index in range(6)]
    dates = []
    cursor = anchor_date
    while len(dates) < 42:
        if cursor.weekday() < 5:
            dates.append(cursor.isoformat())
        cursor -= timedelta(days=1)
    dates.reverse()
    calendar = {
        "schema_version": "a_share_trading_calendar.v1",
        "market": "CN_A",
        "source": "synthetic_fixture",
        "requested_start": dates[0],
        "requested_end": dates[-1],
        "dates": dates,
        "date_count": len(dates),
    }
    snapshots = []
    for as_of_index in (*range(20, 36), 41):
        candidates = []
        bars_by_code = {}
        for stock_index, code in enumerate(codes):
            slope = 0.02 + stock_index * 0.002
            candidates.append(
                {
                    "code": code,
                    "sector_name": "synthetic_sector",
                    "pe": 10.0 + stock_index,
                    "pb": 1.0 + stock_index * 0.1,
                    "total_mv": 100.0 + stock_index * 20,
                    "sector_trend_score": 60.0,
                    "sector_burst_score": 50.0,
                    "sector_direction_score": 65.0,
                    "data_quality_score": 100.0,
                    "factor_coverage": 1.0,
                }
            )
            bars_by_code[code] = [
                {
                    "date": dates[index],
                    "open": 10.0 + stock_index + index * slope,
                    "high": 10.1 + stock_index + index * slope,
                    "low": 9.9 + stock_index + index * slope,
                    "close": 10.0 + stock_index + index * slope,
                    "volume": 1_000_000 + stock_index * 100_000 + index * 1_000,
                    "amount": 10_000_000 + stock_index * 1_000_000 + index * 10_000,
                }
                for index in range(as_of_index + 1)
            ]
        snapshots.append(
            {
                "as_of_date": dates[as_of_index],
                "candidates": candidates,
                "bars_by_code": bars_by_code,
            }
        )
    stock_rows = []
    sector_rows = []
    for index, day in enumerate(dates):
        sector_rows.append(
            {"date": day, "sector_name": "synthetic_sector", "close": 100.0 + index * 0.1}
        )
        for stock_index, code in enumerate(codes):
            slope = 0.02 + stock_index * 0.002
            stock_rows.append(
                {
                    "date": day,
                    "stock_code": code,
                    "sector_name": "synthetic_sector",
                    "close": 10.0 + stock_index + index * slope,
                }
            )
    return (
        {
            "schema_version": "ml-stock-feature-source-v1",
            "mode": MODE,
            "strict_pit_eligible": False,
            "fixture_only": True,
            "anchor_date": anchor_date.isoformat(),
            "snapshots": snapshots,
        },
        {
            "schema_version": "ml-stock-label-source-v1",
            "mode": MODE,
            "strict_pit_eligible": False,
            "fixture_only": True,
            "anchor_date": anchor_date.isoformat(),
            "trading_dates": dates,
            "trading_calendar": calendar,
            "stock_price_rows": stock_rows,
            "sector_price_rows": sector_rows,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=(
            PROJECT_ROOT
            / "reports"
            / "paper_shadow"
            / "ml_stock_ranker"
            / "synthetic_fixture_calendar_v2_2026-07-18"
        ),
    )
    parser.add_argument("--anchor-date", default="2026-07-18")
    parser.add_argument("--model-version", default=None)
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=(
            PROJECT_ROOT
            / "models"
            / "paper_shadow"
            / "stock_ranker_lgbm_v1_synthetic_fixture_20260718_calendar_v2"
        ),
    )
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    if args.model_dir.exists():
        raise FileExistsError(f"synthetic fixture model already exists: {args.model_dir}")

    anchor_date = date.fromisoformat(args.anchor_date)
    if anchor_date.isoformat() != args.anchor_date:
        raise ValueError("anchor date must be canonical ISO")
    feature_source, label_source = _sources(anchor_date=anchor_date)
    feature_path = args.output_root / "feature_source.json"
    label_path = args.output_root / "label_source.json"
    calendar_path = args.output_root / "trading_calendar.json"
    calendar_payload = dict(label_source["trading_calendar"])
    write_strict_json_atomic(calendar_path, calendar_payload)
    _calendar_doc, calendar_sha = load_strict_json_with_sha256(calendar_path)
    label_source["trading_calendar"] = {
        **calendar_payload,
        "path": str(calendar_path.resolve()),
        "sha256": calendar_sha,
    }
    write_strict_json_atomic(feature_path, feature_source)
    write_strict_json_atomic(label_path, label_source)
    _feature_doc, feature_sha = load_strict_json_with_sha256(feature_path)
    _label_doc, label_sha = load_strict_json_with_sha256(label_path)

    feature_rows = build_feature_rows_from_source(feature_source, allow_fixture=True)
    label_rows = build_label_rows_from_source(label_source, allow_fixture=True)
    dataset = build_training_dataset(
        feature_rows,
        label_rows,
        strict_pit_eligible=False,
        fixture_only=True,
        source_manifest={
            "feature_source": {"path": str(feature_path), "sha256": feature_sha},
            "label_source": {"path": str(label_path), "sha256": label_sha},
            "trading_calendar": {
                "path": str(calendar_path.resolve()),
                "sha256": calendar_sha,
                "source": "synthetic_fixture",
            },
            "fixture_only": True,
        },
    )
    dataset_path = args.output_root / "dataset.json"
    write_strict_json_atomic(dataset_path, dataset)
    _dataset_doc, dataset_file_sha = load_strict_json_with_sha256(dataset_path)

    walk_forward = walk_forward_ranker_predictions(
        dataset["records"],
        prediction_universe_records=dataset["feature_universe_records"],
        min_train_dates=5,
        test_dates=3,
        purge_dates=5,
        n_estimators=5,
    )
    walk_forward_document = {
        "schema_version": "ml-stock-walk-forward-predictions-v1",
        "mode": MODE,
        "status": "ok",
        "fixture_only": True,
        "strict_pit_eligible": False,
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
        "live_trading_allowed": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    walk_forward_path = args.output_root / "walk_forward_predictions.json"
    write_strict_json_atomic(walk_forward_path, walk_forward_document)
    _walk_doc, walk_forward_sha = load_strict_json_with_sha256(walk_forward_path)

    model_version = args.model_version or (
        "stock_ranker_lgbm_v1_synthetic_fixture_"
        f"{anchor_date.strftime('%Y%m%d')}_calendar_v2"
    )
    trained = train_lambdarank(dataset["records"], n_estimators=5)
    bundle = save_model_bundle(
        trained,
        args.model_dir,
        model_version=model_version,
        dataset_sha256=dataset["dataset_sha256"],
        strict_pit_eligible=False,
        dataset_classification="synthetic_fixture",
        model_available_from=str(feature_source["snapshots"][-1]["as_of_date"]),
    )
    loaded = load_model_bundle(
        args.model_dir,
        expected_registry_sha256=bundle["registry_sha256"],
    )
    latest_day = str(feature_source["snapshots"][-1]["as_of_date"])
    latest_rows = build_feature_rows_from_source(
        feature_source, as_of_date=latest_day, allow_fixture=True
    )
    current_prediction = predict_shadow(loaded, latest_rows, allow_fixture=True)
    current_prediction["fixture_only"] = True
    current_prediction_path = args.output_root / "current_prediction.json"
    write_strict_json_atomic(current_prediction_path, current_prediction)
    _current_doc, current_prediction_sha = load_strict_json_with_sha256(
        current_prediction_path
    )

    rule_rows = [
        {
            "as_of_date": row["as_of_date"],
            "stock_code": row["stock_code"],
            "rule_score": 100.0 - int(row["stock_code"]),
            "rule_eligible": True,
        }
        for row in dataset["feature_universe_records"]
    ]
    rule_path = args.output_root / "rule_rows.json"
    write_strict_json_atomic(rule_path, {"mode": MODE, "fixture_only": True, "records": rule_rows})
    _rule_doc, rule_sha = load_strict_json_with_sha256(rule_path)
    evaluation = evaluate_rule_vs_ml_shadow(
        walk_forward_document,
        dataset,
        rule_rows,
        top_ks=(2, 3),
    )
    evaluation["fixture_only"] = True
    evaluation["source_manifest"] = {
        "dataset_sha256": dataset["dataset_sha256"],
        "walk_forward_sha256": walk_forward_sha,
        "rule_rows_sha256": rule_sha,
    }
    evaluation_path = args.output_root / "evaluation.json"
    write_strict_json_atomic(evaluation_path, evaluation)
    _evaluation_doc, evaluation_sha = load_strict_json_with_sha256(evaluation_path)

    training_report = {
        "schema_version": "ml-stock-training-report-v1",
        "mode": MODE,
        "status": "ok",
        "fixture_only": True,
        "model_version": model_version,
        "dataset_sha256": dataset["dataset_sha256"],
        "dataset_file_sha256": dataset_file_sha,
        "model_bundle": {
            "registry_sha256": bundle["registry_sha256"],
            "model_sha256": bundle["model_sha256"],
        },
        "walk_forward": {
            "sha256": walk_forward_sha,
            "fold_count": len(walk_forward["folds"]),
            "prediction_count": len(walk_forward["predictions"]),
        },
        "evaluation_sha256": evaluation_sha,
        "architecture_only_shadow": True,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    training_report_path = args.output_root / "training_report.json"
    write_strict_json_atomic(training_report_path, training_report)
    _training_doc, training_report_sha = load_strict_json_with_sha256(training_report_path)

    manifest = {
        "schema_version": "ml-stock-synthetic-fixture-manifest-v1",
        "mode": MODE,
        "status": "ok",
        "fixture_only": True,
        "artifacts": {
            "feature_source_sha256": feature_sha,
            "label_source_sha256": label_sha,
            "trading_calendar_sha256": calendar_sha,
            "dataset_file_sha256": dataset_file_sha,
            "dataset_sha256": dataset["dataset_sha256"],
            "walk_forward_sha256": walk_forward_sha,
            "registry_sha256": bundle["registry_sha256"],
            "model_sha256": bundle["model_sha256"],
            "current_prediction_sha256": current_prediction_sha,
            "rule_rows_sha256": rule_sha,
            "evaluation_sha256": evaluation_sha,
            "training_report_sha256": training_report_sha,
        },
        "strict_pit_eligible": False,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(manifest, context="ML synthetic fixture")
    manifest_path = args.output_root / "fixture_manifest.json"
    write_strict_json_atomic(manifest_path, manifest)
    _manifest_doc, manifest_sha = load_strict_json_with_sha256(manifest_path)
    print(
        f"status=ok fixture_only=true model={model_version} "
        f"manifest_sha256={manifest_sha}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
