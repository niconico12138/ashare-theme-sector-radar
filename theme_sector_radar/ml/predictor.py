"""Daily cross-sectional prediction for the ML stock-ranker shadow path."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
import math
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)

from .ranker import RankerModel, prepare_prediction_matrix
from .registry import (
    _validate_pit_evidence,
    is_verified_model_bundle,
    predict_verified_booster,
)
from .experiment import (
    experiment_config_sha256,
    validate_booster_parameter_binding,
    validate_experiment_config,
    validate_model_parameter_binding,
)
from .schema import (
    DISCLAIMER,
    FEATURE_SCHEMA_VERSION,
    FUTURE_OR_LABEL_FIELD_NAMES,
    FUTURE_OR_LABEL_FIELD_PREFIXES,
    MODE,
    MODEL_MAX_AGE_DAYS,
    OUTPUT_SCHEMA_VERSION,
    V1_FEATURE_NAMES,
    feature_schema_sha256,
)


def _reject_prediction_leakage(value: Any, *, path: str = "prediction_input") -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key).casefold()
            if (
                key in FUTURE_OR_LABEL_FIELD_NAMES
                or key == "training_label"
                or key.startswith(FUTURE_OR_LABEL_FIELD_PREFIXES)
            ):
                raise ValueError(f"prediction input contains label/future field: {path}.{raw_key}")
            _reject_prediction_leakage(child, path=f"{path}.{raw_key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_prediction_leakage(child, path=f"{path}[{index}]")


def _validate_contract(
    model: RankerModel,
    rows: Sequence[Mapping[str, Any]],
    *,
    allow_fixture: bool,
) -> None:
    if not is_verified_model_bundle(model):
        raise ValueError("model bundle was not loaded through the verified registry")
    metadata = model.metadata
    if tuple(model.feature_names) != V1_FEATURE_NAMES:
        raise ValueError("model feature order/schema mismatch")
    if metadata.get("feature_schema_sha256") != feature_schema_sha256():
        raise ValueError("model feature schema SHA mismatch")
    if not metadata.get("registry_sha256"):
        raise ValueError("model registry SHA is unavailable")
    if metadata.get("mode") != MODE:
        raise ValueError("model mode is not paper/shadow research")
    classification = metadata.get("dataset_classification")
    if classification not in {"observed_research", "synthetic_fixture"}:
        raise ValueError("model dataset classification is unsupported")
    if metadata.get("eligible_for_oos_claim") is not False:
        raise ValueError("model OOS safety flag mismatch")
    if metadata.get("promotion_allowed") is not False:
        raise ValueError("model promotion safety flag mismatch")
    if metadata.get("live_trading_allowed") is not False:
        raise ValueError("model live-trading safety flag mismatch")
    freshness = metadata.get("model_freshness")
    if not isinstance(freshness, Mapping):
        raise ValueError("model freshness metadata is unavailable")
    if freshness.get("max_calendar_age_days") != MODEL_MAX_AGE_DAYS:
        raise ValueError("model freshness contract mismatch")
    try:
        available_from = date.fromisoformat(
            str(metadata.get("model_available_from") or "")
        )
    except ValueError as exc:
        raise ValueError("model available-from date is invalid") from exc
    if (
        classification == "synthetic_fixture"
        and not allow_fixture
    ):
        raise ValueError("synthetic fixture model is not eligible for normal prediction")
    if classification == "synthetic_fixture" and metadata.get(
        "strict_pit_eligible"
    ) is not False:
        raise ValueError("synthetic fixture strict-PIT safety flag mismatch")
    experiment = metadata.get("experiment")
    if not isinstance(experiment, Mapping):
        raise ValueError("model requires an experiment contract")
    config = validate_experiment_config(
        experiment.get("config") or {},
        allow_fixture=classification == "synthetic_fixture",
    )
    if experiment.get("config_sha256") != experiment_config_sha256(
        config, allow_fixture=classification == "synthetic_fixture"
    ):
        raise ValueError("model experiment SHA mismatch")
    validate_model_parameter_binding(metadata.get("parameters") or {}, config)
    validate_booster_parameter_binding(model.booster, config)
    if classification == "observed_research":
        if metadata.get("strict_pit_eligible") is not True:
            raise ValueError("observed research model requires strict PIT eligibility")
        _validate_pit_evidence(metadata.get("pit_evidence"))
    latest_eligible_date = available_from + timedelta(days=MODEL_MAX_AGE_DAYS)
    for row in rows:
        _reject_prediction_leakage(row)
        if row.get("schema_version") != FEATURE_SCHEMA_VERSION:
            raise ValueError("prediction feature schema version mismatch")
        provenance = row.get("provenance")
        if not isinstance(provenance, Mapping):
            raise ValueError("prediction feature provenance is missing")
        if provenance.get("feature_schema_sha256") != feature_schema_sha256():
            raise ValueError("prediction feature schema SHA mismatch")
        if tuple((row.get("features") or {}).keys()) != V1_FEATURE_NAMES:
            raise ValueError("prediction feature order/schema mismatch")
        try:
            prediction_date = date.fromisoformat(str(row.get("as_of_date") or ""))
        except ValueError as exc:
            raise ValueError("prediction as_of_date is invalid") from exc
        if prediction_date < available_from:
            raise ValueError("model is not yet available for prediction as_of_date")
        if prediction_date > latest_eligible_date:
            raise ValueError("model is stale for prediction as_of_date")


def _top_drivers(model: RankerModel, *, limit: int = 5) -> list[dict[str, Any]]:
    importance = model.metadata.get("feature_importance_gain")
    if not isinstance(importance, Mapping):
        return []
    ranked = sorted(
        ((str(name), float(value)) for name, value in importance.items()),
        key=lambda item: (-item[1], item[0]),
    )
    return [
        {"feature": name, "global_gain": value}
        for name, value in ranked[:limit]
        if math.isfinite(value)
    ]


def _unavailable(model: RankerModel, *, error: Exception) -> dict[str, Any]:
    return {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "mode": MODE,
        "status": "unavailable",
        "reason": "feature_or_model_contract_rejected",
        "error_type": type(error).__name__,
        "model_version": model.metadata.get("model_version"),
        "fixture_only": model.metadata.get("dataset_classification") == "synthetic_fixture",
        "predictions": [],
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }


def unavailable_prediction_report(
    *, model_version: str | None, reason: str, error: Exception
) -> dict[str, Any]:
    """Create a strict fail-closed report when no verified model can be loaded."""

    report = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "mode": MODE,
        "status": "unavailable",
        "reason": reason,
        "error_type": type(error).__name__,
        "model_version": model_version,
        "predictions": [],
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(report, context="ML shadow prediction")
    return report


def predict_shadow(
    model: RankerModel,
    feature_rows: Sequence[Mapping[str, Any]],
    *,
    allow_fixture: bool = False,
) -> dict[str, Any]:
    """Predict and map raw scores to a separate 0-100 daily shadow score."""

    try:
        if not feature_rows:
            raise ValueError("prediction feature rows must not be empty")
        _validate_contract(model, feature_rows, allow_fixture=allow_fixture)
        matrix = prepare_prediction_matrix(feature_rows, feature_names=model.feature_names)
        raw = predict_verified_booster(model, matrix["features"])
        values = [float(value) for value in raw]
        if len(values) != len(matrix["records"]) or not all(
            math.isfinite(value) for value in values
        ):
            raise ValueError("model returned invalid predictions")
    except (ValueError, RuntimeError, OSError) as exc:
        report = _unavailable(model, error=exc)
        validate_no_executable_instructions(report, context="ML shadow prediction")
        return report

    by_date: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(matrix["records"]):
        by_date[str(row["as_of_date"])].append(index)
    ranks: dict[int, tuple[int, float]] = {}
    for day in sorted(by_date):
        indices = by_date[day]
        ordered_indices = sorted(
            indices,
            key=lambda index: (-values[index], str(matrix["records"][index]["stock_code"])),
        )
        count = len(ordered_indices)
        for rank, index in enumerate(ordered_indices, start=1):
            percentile = 100.0 if count == 1 else (count - rank) / (count - 1) * 100.0
            ranks[index] = (rank, round(percentile, 6))

    drivers = _top_drivers(model)
    predictions = []
    for index, row in enumerate(matrix["records"]):
        rank, percentile = ranks[index]
        predictions.append(
            {
                "as_of_date": str(row["as_of_date"]),
                "stock_code": str(row["stock_code"]).zfill(6),
                "sector_name": str(row.get("sector_name") or ""),
                "status": "ok",
                "model_version": model.metadata["model_version"],
                "prediction": values[index],
                "ml_quant_score_shadow": percentile,
                "rank": rank,
                "feature_coverage": float(row.get("feature_coverage") or 0.0),
                "top_drivers": drivers,
                "provenance": {
                    "feature_schema_sha256": feature_schema_sha256(),
                    "model_registry_sha256": model.metadata["registry_sha256"],
                    "model_sha256": model.metadata["model_artifact"]["sha256"],
                },
            }
        )
    report = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "mode": MODE,
        "status": "ok",
        "reason": "shadow_prediction_complete",
        "model_version": model.metadata["model_version"],
        "fixture_only": model.metadata.get("dataset_classification") == "synthetic_fixture",
        "strict_pit_eligible": bool(model.metadata.get("strict_pit_eligible", False)),
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "predictions": predictions,
        "provenance": {
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "feature_schema_sha256": feature_schema_sha256(),
            "model_registry_sha256": model.metadata["registry_sha256"],
            "model_sha256": model.metadata["model_artifact"]["sha256"],
        },
        "generated_at": datetime.now().astimezone().isoformat(),
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(report, context="ML shadow prediction")
    return report
