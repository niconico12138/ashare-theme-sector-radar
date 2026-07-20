"""Run independent industry-sector ML shadow research rounds."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.ml.contract import canonical_sha256
from theme_sector_radar.ml.industry_sector_shadow import (
    CLASSIFICATION,
    DISCLAIMER,
    FEATURE_PROFILES,
    ROUND_SPECS,
    MODE,
    PREDICTION_SCHEMA_VERSION,
    build_industry_sector_dataset,
    feature_names_for_profile,
    prepare_round_records,
    run_industry_sector_round,
    validate_shadow_prediction_fields,
    write_industry_sector_model_artifact,
)
from theme_sector_radar.ml.ranker import train_lambdarank
from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)


def _write_json(path: Path, payload: dict) -> dict[str, str]:
    validate_no_executable_instructions(payload, context=f"industry sector shadow artifact {path.name}")
    write_strict_json_atomic(path, payload)
    _loaded, sha256 = load_strict_json_with_sha256(path)
    return {"path": str(path.resolve()), "sha256": sha256}


def _artifact_ref(path: Path) -> dict[str, str]:
    _loaded, sha256 = load_strict_json_with_sha256(path)
    return {"path": str(path.resolve()), "sha256": sha256}


def _load_existing_round(round_output: Path, round_model: Path) -> dict:
    prediction_path = round_output / "predictions.json"
    evaluation_path = round_output / "evaluation.json"
    registry_path = round_model / "registry.json"
    if not all(path.is_file() for path in (prediction_path, evaluation_path, registry_path, round_model / "model.txt")):
        raise FileExistsError(f"incomplete existing industry sector round: {round_output}")
    prediction, _ = load_strict_json_with_sha256(prediction_path)
    _evaluation, _ = load_strict_json_with_sha256(evaluation_path)
    registry, _ = load_strict_json_with_sha256(registry_path)
    validate_shadow_prediction_fields(prediction)
    if prediction.get("dataset_sha256") != registry.get("dataset_sha256"):
        raise ValueError(f"existing round dataset SHA mismatch: {round_output.name}")
    return {
        "prediction": _artifact_ref(prediction_path),
        "evaluation": _artifact_ref(evaluation_path),
        "model": {
            "registry_path": str(registry_path.resolve()),
            "registry_sha256": _artifact_ref(registry_path)["sha256"],
            "model_path": str((round_model / "model.txt").resolve()),
            "model_sha256": _sha256_file(round_model / "model.txt"),
        },
        "prediction_count": len(prediction.get("predictions") or []),
        "fold_count": len(prediction.get("folds") or []),
    }


def _sha256_file(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _round_parameters(spec: dict, args: argparse.Namespace) -> dict:
    return {
        "min_train_dates": spec.get("min_train_dates", args.min_train_dates),
        "test_dates": spec.get("test_dates", args.test_dates),
        "purge_dates": spec.get("purge_dates", args.purge_dates),
        "max_train_dates": spec.get("max_train_dates"),
        "n_estimators": spec.get("n_estimators", args.n_estimators),
        "learning_rate": spec.get("learning_rate", 0.05),
        "num_leaves": spec.get("num_leaves", 15),
        "random_state": spec.get("random_state", 20260720),
        "feature_value_mode": spec.get("feature_value_mode", "raw"),
        "rule_gate_threshold": spec.get("rule_gate_threshold", 50.0),
        "top_k_values": list(spec.get("top_k_values", (3, 5, 7))),
        "evaluation_start": spec.get("evaluation_start"),
        "evaluation_end": spec.get("evaluation_end"),
        "evaluation_regimes": list(spec["evaluation_regimes"]) if spec.get("evaluation_regimes") else None,
        "transaction_cost_bps": spec.get("transaction_cost_bps", 0.0),
    }


def _round_manifest(
    *,
    round_name: str,
    status: str,
    feature_profile: str,
    hypothesis: str,
    parameters: dict,
    dataset_sha256: str,
    artifacts: dict | None = None,
    error: str | None = None,
) -> dict:
    payload = {
        "schema_version": "ml-industry-sector-shadow-round-manifest-v1",
        "mode": MODE,
        "status": status,
        "round_name": round_name,
        "feature_profile": feature_profile,
        "hypothesis": hypothesis,
        "parameters": parameters,
        "dataset_classification": CLASSIFICATION,
        "dataset_sha256": dataset_sha256,
        "artifacts": artifacts or {},
        "strict_pit_eligible": False,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
        "agent_interface": {"enabled": False, "status": "reserved_not_run"},
        "disclaimer": DISCLAIMER,
    }
    if error:
        payload["error"] = error[:1000]
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        default=PROJECT_ROOT / "data_cache" / "sector_history",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "reports" / "paper_shadow" / "industry_sector_ml_shadow",
    )
    parser.add_argument(
        "--model-root",
        type=Path,
        default=PROJECT_ROOT / "models" / "paper_shadow" / "industry_sector_ml_shadow",
    )
    parser.add_argument("--min-train-dates", type=int, default=60)
    parser.add_argument("--test-dates", type=int, default=10)
    parser.add_argument("--purge-dates", type=int, default=5)
    parser.add_argument("--n-estimators", type=int, default=40)
    args = parser.parse_args()
    if min(args.min_train_dates, args.test_dates, args.purge_dates, args.n_estimators) <= 0:
        raise ValueError("industry sector shadow numeric arguments must be positive")

    dataset = build_industry_sector_dataset(args.source_root)
    args.output_root.mkdir(parents=True, exist_ok=True)
    args.model_root.mkdir(parents=True, exist_ok=True)
    dataset_path = args.output_root / "dataset.json"
    if dataset_path.is_file():
        existing_dataset, _ = load_strict_json_with_sha256(dataset_path)
        if existing_dataset.get("dataset_sha256") != dataset.get("dataset_sha256"):
            raise ValueError("existing industry sector dataset is not the current physical-source rebuild")
        dataset_artifact = _artifact_ref(dataset_path)
    else:
        dataset_artifact = _write_json(dataset_path, dataset)
    rounds: dict[str, dict] = {}
    records = dataset["records"]
    for spec in ROUND_SPECS:
        round_name = spec["name"]
        feature_profile = spec["feature_profile"]
        round_output = args.output_root / round_name
        round_model = args.model_root / round_name
        parameters = _round_parameters(spec, args)
        if round_output.is_dir() or round_model.is_dir():
            existing_round_manifest = round_output / "round_manifest.json"
            if existing_round_manifest.is_file():
                existing, _ = load_strict_json_with_sha256(existing_round_manifest)
                if existing.get("status") in {"rejected", "insufficient"}:
                    rounds[round_name] = {
                        "feature_profile": feature_profile,
                        "hypothesis": spec["hypothesis"],
                        "parameters": parameters,
                        "status": existing["status"],
                        "manifest": _artifact_ref(existing_round_manifest),
                    }
                    continue
            rounds[round_name] = {
                **_load_existing_round(round_output, round_model),
                "feature_profile": feature_profile,
                "hypothesis": spec["hypothesis"],
                "parameters": parameters,
                "status": "reused_existing_artifact",
            }
            if existing_round_manifest.is_file():
                rounds[round_name]["manifest"] = _artifact_ref(existing_round_manifest)
            continue
        round_output.mkdir()
        round_model.mkdir()
        try:
            prediction, evaluation = run_industry_sector_round(
                dataset,
                feature_profile=feature_profile,
                hypothesis=spec["hypothesis"],
                **parameters,
            )
            feature_names = feature_names_for_profile(feature_profile)
            model_records = prepare_round_records(
                records,
                feature_names,
                feature_value_mode=parameters["feature_value_mode"],
            )
            model = train_lambdarank(
                model_records,
                feature_names=feature_names,
                relevance_levels=5,
                n_estimators=parameters["n_estimators"],
                learning_rate=parameters["learning_rate"],
                num_leaves=parameters["num_leaves"],
                random_state=parameters["random_state"],
            )
            model_artifact = write_industry_sector_model_artifact(
                model,
                round_model,
                dataset_sha256=dataset["dataset_sha256"],
                feature_profile=feature_profile,
                experiment=parameters,
            )
            prediction_artifact = _write_json(round_output / "predictions.json", prediction)
            evaluation_artifact = _write_json(round_output / "evaluation.json", evaluation)
            round_manifest = _write_json(
                round_output / "round_manifest.json",
                _round_manifest(
                    round_name=round_name,
                    status="completed",
                    feature_profile=feature_profile,
                    hypothesis=spec["hypothesis"],
                    parameters=parameters,
                    dataset_sha256=dataset["dataset_sha256"],
                    artifacts={
                        "prediction": prediction_artifact,
                        "evaluation": evaluation_artifact,
                        "model": model_artifact,
                    },
                ),
            )
            rounds[round_name] = {
                "feature_profile": feature_profile,
                "hypothesis": spec["hypothesis"],
                "parameters": parameters,
                "status": "completed",
                "manifest": round_manifest,
                "prediction": prediction_artifact,
                "evaluation": evaluation_artifact,
                "model": model_artifact,
                "prediction_count": len(prediction["predictions"]),
                "fold_count": len(prediction["folds"]),
            }
        except Exception as exc:
            status = "insufficient" if "insufficient" in str(exc).casefold() else "rejected"
            failed_manifest = _write_json(
                round_output / "round_manifest.json",
                _round_manifest(
                    round_name=round_name,
                    status=status,
                    feature_profile=feature_profile,
                    hypothesis=spec["hypothesis"],
                    parameters=parameters,
                    dataset_sha256=dataset["dataset_sha256"],
                    error=f"{type(exc).__name__}: {exc}",
                ),
            )
            rounds[round_name] = {
                "feature_profile": feature_profile,
                "hypothesis": spec["hypothesis"],
                "parameters": parameters,
                "status": status,
                "manifest": failed_manifest,
            }
    manifest = {
        "schema_version": "ml-industry-sector-shadow-manifest-v1",
        "mode": MODE,
        "status": "research_only",
        "dataset_classification": CLASSIFICATION,
        "dataset": dataset_artifact,
        "source_counts": dataset["counts"],
        "rounds": rounds,
        "feature_profiles": {key: list(value) for key, value in FEATURE_PROFILES.items()},
        "iteration_count": len(rounds),
        "round_plan": [
            {"name": spec["name"], "feature_profile": spec["feature_profile"], "hypothesis": spec["hypothesis"]}
            for spec in ROUND_SPECS
        ],
        "strict_pit_eligible": False,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "formal_predictor_compatible": False,
        "agent_interface": {"enabled": False, "status": "reserved_not_run"},
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    manifest_artifact = _write_json(args.output_root / "manifest.json", manifest)
    print(
        f"status=research_only sectors={dataset['counts']['sector_count']} "
        f"mature_dates={dataset['counts']['mature_dates']} "
        f"rounds={len(rounds)} manifest_sha256={manifest_artifact['sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
