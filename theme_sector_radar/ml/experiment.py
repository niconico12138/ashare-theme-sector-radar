"""Versioned, paper-only experiment settings for the ML stock shadow path."""

from __future__ import annotations

import copy
from typing import Any, Mapping

from .contract import canonical_sha256
from .schema import FEATURE_SCHEMA_VERSION, LABEL_DEFINITION, MODE, feature_schema_sha256


EXPERIMENT_CONFIG_SCHEMA_VERSION = "ml-stock-experiment-config-v1"


def default_experiment_config() -> dict[str, Any]:
    """Return the registered observed-data V1 settings without timestamps."""

    return {
        "schema_version": EXPERIMENT_CONFIG_SCHEMA_VERSION,
        "mode": MODE,
        "experiment_id": "stock_ranker_lgbm_v1_direction_candidate_shadow",
        "feature_contract": {
            "schema_version": FEATURE_SCHEMA_VERSION,
            "feature_schema_sha256": feature_schema_sha256(),
            "legacy_relevance_included": False,
        },
        "label_contract": {
            "definition": LABEL_DEFINITION,
            "training_horizon": 5,
            "maximum_horizon": 5,
        },
        "split": {
            "type": "expanding_date_grouped_walk_forward",
            "min_train_dates": 60,
            "test_dates": 20,
            "purge_dates": 5,
        },
        "model": {
            "backend": "lightgbm_lambdarank",
            "objective": "lambdarank",
            "metric": ["ndcg"],
            "relevance_levels": 5,
            "label_gain": [0, 1, 3, 7, 15],
            "n_estimators": 80,
            "learning_rate": 0.05,
            "num_leaves": 15,
            "random_state": 20260718,
            "min_child_samples": 2,
            "subsample": 1.0,
            "colsample_bytree": 1.0,
            "reg_lambda": 1.0,
            "deterministic": True,
            "force_col_wise": True,
            "n_jobs": 1,
            "verbosity": -1,
        },
        "baseline": {
            "hybrid_quant_weight": 0.65,
            "hybrid_linkage_weight": 0.35,
            "hybrid_partial_linkage_weight": 0.20,
        },
        "safety": {
            "strict_pit_eligible": False,
            "eligible_for_oos_claim": False,
            "promotion_allowed": False,
            "live_trading_allowed": False,
        },
    }


def validate_experiment_config(
    config: Mapping[str, Any], *, allow_fixture: bool = False
) -> dict[str, Any]:
    """Validate and return a detached config suitable for an artifact manifest."""

    if not isinstance(config, Mapping):
        raise ValueError("ML experiment config must be an object")
    normalized = {str(key): value for key, value in config.items()}
    expected = default_experiment_config()
    if normalized.get("schema_version") != EXPERIMENT_CONFIG_SCHEMA_VERSION:
        raise ValueError("ML experiment config schema mismatch")
    if normalized.get("mode") != MODE:
        raise ValueError("ML experiment config mode mismatch")
    if not str(normalized.get("experiment_id") or ""):
        raise ValueError("ML experiment id is required")

    feature_contract = normalized.get("feature_contract")
    if not isinstance(feature_contract, Mapping):
        raise ValueError("ML experiment feature contract is missing")
    if feature_contract.get("schema_version") != FEATURE_SCHEMA_VERSION:
        raise ValueError("ML experiment feature schema mismatch")
    if feature_contract.get("feature_schema_sha256") != feature_schema_sha256():
        raise ValueError("ML experiment feature schema SHA mismatch")
    if feature_contract.get("legacy_relevance_included") is not False:
        raise ValueError("legacy relevance must be excluded from ML features")

    label_contract = normalized.get("label_contract")
    if not isinstance(label_contract, Mapping):
        raise ValueError("ML experiment label contract is missing")
    if label_contract.get("definition") != LABEL_DEFINITION:
        raise ValueError("ML experiment label definition mismatch")
    if int(label_contract.get("training_horizon") or 0) != 5:
        raise ValueError("ML experiment training horizon must be 5")
    if int(label_contract.get("maximum_horizon") or 0) != 5:
        raise ValueError("ML experiment maximum horizon must be 5")

    split = normalized.get("split")
    if not isinstance(split, Mapping) or split.get("type") != expected["split"]["type"]:
        raise ValueError("ML experiment split contract mismatch")
    min_train_dates = int(split.get("min_train_dates") or 0)
    test_dates = int(split.get("test_dates") or 0)
    purge_dates = int(split.get("purge_dates") or 0)
    if (
        (min_train_dates < 60 and not allow_fixture)
        or test_dates <= 0
        or purge_dates < 5
    ):
        raise ValueError("ML experiment split does not meet the research minimums")

    model = normalized.get("model")
    if not isinstance(model, Mapping) or model.get("backend") != "lightgbm_lambdarank":
        raise ValueError("ML experiment model backend mismatch")
    relevance_levels = int(model.get("relevance_levels") or 0)
    n_estimators = int(model.get("n_estimators") or 0)
    learning_rate = float(model.get("learning_rate") or 0.0)
    num_leaves = int(model.get("num_leaves") or 0)
    if relevance_levels < 2 or n_estimators <= 0 or not 0.0 < learning_rate <= 1.0 or num_leaves < 2:
        raise ValueError("ML experiment model parameters are invalid")
    expected_label_gain = [(2**index) - 1 for index in range(relevance_levels)]
    if model.get("objective") != "lambdarank":
        raise ValueError("ML experiment model objective mismatch")
    if model.get("metric") != ["ndcg"]:
        raise ValueError("ML experiment model metric mismatch")
    if model.get("label_gain") != expected_label_gain:
        raise ValueError("ML experiment model label_gain mismatch")
    fixed_parameters = {
        "min_child_samples": 2,
        "subsample": 1.0,
        "colsample_bytree": 1.0,
        "reg_lambda": 1.0,
        "deterministic": True,
        "force_col_wise": True,
        "n_jobs": 1,
        "verbosity": -1,
    }
    if any(model.get(key) != value for key, value in fixed_parameters.items()):
        raise ValueError("ML experiment fixed model parameter mismatch")

    baseline = normalized.get("baseline")
    if not isinstance(baseline, Mapping):
        raise ValueError("ML experiment baseline contract is missing")
    for key in (
        "hybrid_quant_weight",
        "hybrid_linkage_weight",
        "hybrid_partial_linkage_weight",
    ):
        value = float(baseline.get(key) or -1.0)
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"ML experiment baseline value is invalid: {key}")

    safety = normalized.get("safety")
    if not isinstance(safety, Mapping):
        raise ValueError("ML experiment safety contract is missing")
    for key in ("strict_pit_eligible", "eligible_for_oos_claim", "promotion_allowed", "live_trading_allowed"):
        if safety.get(key) is not False:
            raise ValueError(f"ML experiment safety flag must be false: {key}")
    return normalized


def build_effective_experiment_config(
    config: Mapping[str, Any],
    *,
    split_overrides: Mapping[str, Any] | None = None,
    model_overrides: Mapping[str, Any] | None = None,
    baseline_overrides: Mapping[str, Any] | None = None,
    allow_fixture: bool = False,
) -> dict[str, Any]:
    """Apply controlled overrides and validate the resulting effective settings."""

    effective = copy.deepcopy(dict(config))
    for section, overrides in (
        ("split", split_overrides),
        ("model", model_overrides),
        ("baseline", baseline_overrides),
    ):
        if overrides:
            target = effective.get(section)
            if not isinstance(target, dict):
                raise ValueError(f"ML experiment section is missing: {section}")
            target.update(dict(overrides))
    return validate_experiment_config(effective, allow_fixture=allow_fixture)


def validate_model_parameter_binding(
    model_parameters: Mapping[str, Any], config: Mapping[str, Any]
) -> None:
    """Require the trained model parameters to match the registered experiment."""

    if not isinstance(model_parameters, Mapping):
        raise ValueError("ML model parameters are missing")
    model_config = config.get("model")
    if not isinstance(model_config, Mapping):
        raise ValueError("ML experiment model contract is missing")
    for key in (
        "backend",
        "objective",
        "metric",
        "relevance_levels",
        "label_gain",
        "n_estimators",
        "learning_rate",
        "num_leaves",
        "random_state",
        "min_child_samples",
        "subsample",
        "colsample_bytree",
        "reg_lambda",
        "deterministic",
        "force_col_wise",
        "n_jobs",
        "verbosity",
    ):
        if model_parameters.get(key) != model_config.get(key):
            raise ValueError(f"ML model parameter mismatch: {key}")


def validate_booster_parameter_binding(booster: Any, config: Mapping[str, Any]) -> None:
    """Bind the serialized LightGBM booster settings to the experiment contract."""

    params = getattr(booster, "params", None)
    model = config.get("model") if isinstance(config, Mapping) else None
    if not isinstance(params, Mapping) or not isinstance(model, Mapping):
        raise ValueError("ML booster parameter contract is missing")
    checks = (
        ("num_iterations", "n_estimators", int),
        ("learning_rate", "learning_rate", float),
        ("num_leaves", "num_leaves", int),
    )
    for booster_key, config_key, converter in checks:
        try:
            observed = converter(params.get(booster_key))
            expected = converter(model.get(config_key))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"ML serialized booster parameter is invalid: {booster_key}"
            ) from exc
        if observed != expected:
            raise ValueError(
                f"ML serialized booster parameter mismatch: {booster_key}"
            )
    seed_key = "seed" if params.get("seed") is not None else "random_state"
    try:
        observed_seed = int(params.get(seed_key))
        expected_seed = int(model.get("random_state"))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"ML serialized booster parameter is invalid: {seed_key}"
        ) from exc
    if observed_seed != expected_seed:
        raise ValueError(
            f"ML serialized booster parameter mismatch: {seed_key}"
        )
    if params.get("objective") != model.get("objective"):
        raise ValueError("ML serialized booster parameter mismatch: objective")
    observed_metric = params.get("metric")
    if isinstance(observed_metric, str):
        observed_metric = [observed_metric]
    if observed_metric != model.get("metric"):
        raise ValueError("ML serialized booster parameter mismatch: metric")
    if params.get("label_gain") != model.get("label_gain"):
        raise ValueError("ML serialized booster parameter mismatch: label_gain")
    fixed_checks = (
        (("min_data_in_leaf", "min_child_samples"), "min_child_samples"),
        (("bagging_fraction", "subsample"), "subsample"),
        (("feature_fraction", "colsample_bytree"), "colsample_bytree"),
        (("lambda_l2", "reg_lambda"), "reg_lambda"),
        (("deterministic",), "deterministic"),
        (("force_col_wise",), "force_col_wise"),
        (("num_threads", "n_jobs"), "n_jobs"),
        (("verbosity",), "verbosity"),
    )
    for booster_keys, config_key in fixed_checks:
        booster_key = next((key for key in booster_keys if key in params), booster_keys[0])
        if params.get(booster_key) != model.get(config_key):
            raise ValueError(
                f"ML serialized booster parameter mismatch: {booster_key}"
            )


def experiment_config_sha256(
    config: Mapping[str, Any], *, allow_fixture: bool = False
) -> str:
    """Hash only a validated, timestamp-free experiment configuration."""

    return canonical_sha256(
        validate_experiment_config(config, allow_fixture=allow_fixture)
    )
