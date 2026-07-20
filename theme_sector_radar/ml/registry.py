"""Content-bound model registry for ML stock-ranker shadow bundles."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
from datetime import date, datetime
from types import MappingProxyType
import weakref
from typing import Any, Mapping

from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)

from .ranker import RankerModel
from .contract import canonical_sha256
from .experiment import (
    experiment_config_sha256 as compute_experiment_config_sha256,
    validate_booster_parameter_binding,
    validate_model_parameter_binding,
    validate_experiment_config,
)
from .schema import (
    DISCLAIMER,
    FEATURE_SCHEMA_VERSION,
    LABEL_DEFINITION,
    MODE,
    MODEL_MAX_AGE_DAYS,
    MODEL_REGISTRY_SCHEMA_VERSION,
    V1_FEATURE_NAMES,
    feature_schema_sha256,
)


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_VERIFIED_MODEL_BUNDLES: dict[int, dict[str, Any]] = {}


class _VerifiedBoosterProxy:
    """Expose model metadata operations while blocking raw prediction bypasses."""

    __slots__ = ("__booster",)

    def __init__(self, booster: Any) -> None:
        self.__booster = booster

    @property
    def params(self) -> Mapping[str, Any]:
        return MappingProxyType(dict(self.__booster.params))

    def feature_name(self):
        return self.__booster.feature_name()

    def feature_importance(self, *args, **kwargs):
        return self.__booster.feature_importance(*args, **kwargs)

    def save_model(self, *args, **kwargs):
        return self.__booster.save_model(*args, **kwargs)

    def model_to_string(self) -> str:
        return self.__booster.model_to_string()

    def predict(self, *_args, **_kwargs):
        raise RuntimeError("verified boosters can predict only through predict_shadow")

    def _predict_shadow(self, matrix: Any):
        return self.__booster.predict(matrix)


def _booster_sha256(booster: Any) -> str:
    return hashlib.sha256(booster.model_to_string().encode("utf-8")).hexdigest()


def _register_verified_model_bundle(model: RankerModel) -> None:
    identity = id(model)

    def remove(_reference: weakref.ReferenceType[RankerModel]) -> None:
        _VERIFIED_MODEL_BUNDLES.pop(identity, None)

    _VERIFIED_MODEL_BUNDLES[identity] = {
        "reference": weakref.ref(model, remove),
        "metadata_sha256": canonical_sha256(dict(model.metadata)),
        "booster_sha256": _booster_sha256(model.booster),
    }


def is_verified_model_bundle(model: RankerModel) -> bool:
    """Return whether this exact object came from a verified bundle loader."""

    identity = _VERIFIED_MODEL_BUNDLES.get(id(model))
    if not isinstance(identity, Mapping) or identity["reference"]() is not model:
        return False
    return (
        canonical_sha256(dict(model.metadata)) == identity["metadata_sha256"]
        and _booster_sha256(model.booster) == identity["booster_sha256"]
    )


def predict_verified_booster(model: RankerModel, matrix: Any):
    """Run the hidden booster only after rechecking immutable bundle fingerprints."""

    if not is_verified_model_bundle(model) or not isinstance(
        model.booster, _VerifiedBoosterProxy
    ):
        raise ValueError("model bundle fingerprint changed after verification")
    return model.booster._predict_shadow(matrix)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _registry_now() -> datetime:
    return datetime.now().astimezone()


def _validate_pit_evidence(pit_evidence: Any) -> dict[str, Any]:
    if not isinstance(pit_evidence, dict):
        raise ValueError("strict PIT model bundle requires verifier evidence")
    core = {key: value for key, value in pit_evidence.items() if key != "evidence_sha256"}
    if canonical_sha256(core) != pit_evidence.get("evidence_sha256"):
        raise ValueError("model bundle PIT evidence SHA mismatch")
    if (
        pit_evidence.get("schema_version") != "ml-stock-pit-evidence-v1"
        or pit_evidence.get("mode") != MODE
        or pit_evidence.get("status") != "verified"
        or pit_evidence.get("verifier")
        != "theme_sector_radar.ml.accumulation.verify_accumulation_archive"
        or pit_evidence.get("strict_pit_eligible") is not True
        or pit_evidence.get("minimum_60_dates_satisfied") is not True
    ):
        raise ValueError("model bundle PIT evidence is not strict")
    archive_root = pit_evidence.get("archive_root")
    if not isinstance(archive_root, str) or not archive_root:
        raise ValueError("strict PIT model bundle archive root is missing")
    from .accumulation import load_verified_training_inputs

    loaded = load_verified_training_inputs(archive_root)
    if loaded["evidence"].get("evidence_sha256") != pit_evidence.get(
        "evidence_sha256"
    ):
        raise ValueError("model bundle PIT evidence is not bound to the archive verifier")
    return loaded


def _strict_training_identity(pit_evidence: Any) -> dict[str, str]:
    loaded = _validate_pit_evidence(pit_evidence)
    from .dataset import build_training_dataset

    dataset = build_training_dataset(
        loaded["feature_rows"],
        loaded["label_rows"],
        strict_pit_eligible=False,
        pit_evidence=loaded["evidence"],
    )
    training_dates = set(loaded["evidence"]["verified_training_dates"])
    captured_dates: list[date] = []
    for entry in loaded["evidence"]["labels"]:
        if entry.get("signal_date") not in training_dates:
            continue
        snapshot, _snapshot_sha = load_strict_json_with_sha256(entry["path"])
        captured = datetime.fromisoformat(str(snapshot.get("captured_at") or ""))
        if captured.tzinfo is None or captured.utcoffset() is None:
            raise ValueError("strict label capture timestamp is invalid")
        captured_dates.append(captured.date())
    if not captured_dates:
        raise ValueError("strict model has no captured training labels")
    return {
        "dataset_sha256": str(dataset["dataset_sha256"]),
        "training_records_sha256": canonical_sha256(dataset["records"]),
        "latest_label_capture_date": max(captured_dates).isoformat(),
    }


def save_model_bundle(
    model: RankerModel,
    output_dir: Path | str,
    *,
    model_version: str,
    dataset_sha256: str,
    strict_pit_eligible: bool,
    dataset_classification: str,
    model_available_from: str,
    pit_evidence: Mapping[str, Any] | None = None,
    experiment_config: Mapping[str, Any] | None = None,
    experiment_config_sha256: str | None = None,
) -> dict[str, Any]:
    """Write a new model bundle without overwriting an existing bundle."""

    if not model_version or not _SHA256.fullmatch(dataset_sha256):
        raise ValueError("model_version and a lowercase dataset SHA-256 are required")
    validated_experiment = None
    if (
        dataset_classification == "synthetic_fixture"
        and experiment_config is None
        and experiment_config_sha256 is None
    ):
        from .experiment import build_effective_experiment_config, default_experiment_config

        parameters = model.metadata.get("parameters") or {}
        model_overrides = {
            key: parameters[key]
            for key in (
                "relevance_levels",
                "label_gain",
                "n_estimators",
                "learning_rate",
                "num_leaves",
                "random_state",
            )
            if key in parameters
        }
        validated_experiment = build_effective_experiment_config(
            default_experiment_config(),
            model_overrides=model_overrides,
            allow_fixture=True,
        )
        experiment_config = validated_experiment
        experiment_config_sha256 = compute_experiment_config_sha256(
            validated_experiment, allow_fixture=True
        )
    if experiment_config is not None or experiment_config_sha256 is not None:
        if experiment_config is None or not experiment_config_sha256:
            raise ValueError("experiment config and SHA must be supplied together")
        validated_experiment = validate_experiment_config(
            experiment_config,
            allow_fixture=dataset_classification == "synthetic_fixture",
        )
        if experiment_config_sha256 != compute_experiment_config_sha256(
            validated_experiment,
            allow_fixture=dataset_classification == "synthetic_fixture",
        ):
            raise ValueError("experiment config SHA mismatch")
        validate_model_parameter_binding(
            model.metadata.get("parameters") or {}, validated_experiment
        )
        validate_booster_parameter_binding(model.booster, validated_experiment)
    if tuple(model.feature_names) != V1_FEATURE_NAMES:
        raise ValueError("trained model feature order/schema mismatch")
    strict_identity = None
    if strict_pit_eligible:
        strict_identity = _strict_training_identity(pit_evidence)
        if dataset_sha256 != strict_identity["dataset_sha256"]:
            raise ValueError("strict model dataset does not match the verified archive")
        if model.metadata.get("training_records_sha256") != strict_identity[
            "training_records_sha256"
        ]:
            raise ValueError("strict model training records do not match the dataset")
    if dataset_classification not in {"observed_research", "synthetic_fixture"}:
        raise ValueError("unsupported model dataset classification")
    if dataset_classification == "observed_research" and not strict_pit_eligible:
        raise ValueError(
            "observed research model requires strict PIT eligibility"
        )
    if dataset_classification == "observed_research" and validated_experiment is None:
        raise ValueError(
            "observed research model requires an experiment contract"
        )
    registered_at = _registry_now()
    try:
        available_from = date.fromisoformat(model_available_from)
        maturity_end = date.fromisoformat(
            str(model.metadata["label_maturity_period"]["end"])
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("model availability or label maturity date is invalid") from exc
    if available_from.isoformat() != model_available_from or available_from < maturity_end:
        raise ValueError("model_available_from must not precede label maturity")
    if dataset_classification == "observed_research":
        latest_capture = date.fromisoformat(
            str((strict_identity or {}).get("latest_label_capture_date") or "")
        )
        if available_from <= max(latest_capture, registered_at.date()):
            raise ValueError(
                "observed model_available_from must follow label capture and registration"
            )
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    model_path = destination / "model.txt"
    registry_path = destination / "registry.json"
    if model_path.exists() or registry_path.exists():
        raise FileExistsError(f"model bundle already exists: {destination}")

    temporary_model = destination / ".model.txt.tmp"
    try:
        model.booster.save_model(str(temporary_model))
        os.replace(temporary_model, model_path)
    finally:
        temporary_model.unlink(missing_ok=True)
    model_sha256 = _file_sha256(model_path)
    importances = model.booster.feature_importance(importance_type="gain").tolist()
    registry = {
        "schema_version": MODEL_REGISTRY_SCHEMA_VERSION,
        "mode": MODE,
        "status": "ready",
        "model_version": model_version,
        "registered_at": registered_at.isoformat(),
        "backend": model.metadata["backend"],
        "objective": model.metadata["objective"],
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_schema_sha256": feature_schema_sha256(),
        "feature_names": list(model.feature_names),
        "label_definition": LABEL_DEFINITION,
        "relevance_levels": model.metadata["relevance_levels"],
        "continuous_label_retained_for_evaluation": True,
        "training_period": dict(model.metadata["training_period"]),
        "label_maturity_period": dict(model.metadata["label_maturity_period"]),
        "training_records_sha256": model.metadata["training_records_sha256"],
        "dataset_classification": dataset_classification,
        "model_available_from": model_available_from,
        "model_freshness": {
            "anchor": "model_available_from",
            "max_calendar_age_days": MODEL_MAX_AGE_DAYS,
        },
        "libraries": dict(model.metadata["libraries"]),
        "parameters": dict(model.metadata["parameters"]),
        "dataset_sha256": dataset_sha256,
        "strict_pit_eligible": bool(strict_pit_eligible),
        "pit_evidence_status": (
            "verified_prospective_archive"
            if strict_pit_eligible
            else "unverified_no_trusted_verifier"
        ),
        "pit_evidence": dict(pit_evidence) if strict_pit_eligible else None,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "model_artifact": {
            "path": "model.txt",
            "sha256": model_sha256,
        },
        "feature_importance_gain": {
            name: float(value) for name, value in zip(model.feature_names, importances)
        },
        "disclaimer": DISCLAIMER,
    }
    if validated_experiment is not None:
        registry["experiment"] = {
            "config_sha256": str(experiment_config_sha256),
            "config": validated_experiment,
        }
    validate_no_executable_instructions(registry, context="ML model registry")
    write_strict_json_atomic(registry_path, registry)
    registry_sha256 = _file_sha256(registry_path)
    return {
        "registry": registry,
        "registry_path": str(registry_path),
        "registry_sha256": registry_sha256,
        "model_path": str(model_path),
        "model_sha256": model_sha256,
    }


def load_model_bundle(
    output_dir: Path | str, *, expected_registry_sha256: str
) -> RankerModel:
    """Load and verify a model bundle, rejecting any schema or hash drift."""

    destination = Path(output_dir)
    registry_path = destination / "registry.json"
    registry, registry_sha256 = load_strict_json_with_sha256(registry_path)
    expected_registry_sha256 = str(expected_registry_sha256 or "").lower()
    if (
        not _SHA256.fullmatch(expected_registry_sha256)
        or registry_sha256 != expected_registry_sha256
    ):
        raise ValueError("model registry SHA mismatch")
    if registry.get("schema_version") != MODEL_REGISTRY_SCHEMA_VERSION:
        raise ValueError("model registry schema mismatch")
    if registry.get("mode") != MODE or registry.get("status") != "ready":
        raise ValueError("model registry is not a ready paper/shadow artifact")
    strict_pit_eligible = bool(registry.get("strict_pit_eligible", False))
    safety_envelope = {
        "strict_pit_eligible": strict_pit_eligible,
        "pit_evidence_status": (
            "verified_prospective_archive"
            if strict_pit_eligible
            else "unverified_no_trusted_verifier"
        ),
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
    }
    if any(registry.get(key) != value for key, value in safety_envelope.items()):
        raise ValueError("model registry safety envelope mismatch")
    training_records_sha256 = str(registry.get("training_records_sha256") or "").lower()
    if not _SHA256.fullmatch(training_records_sha256) or set(training_records_sha256) == {"0"}:
        raise ValueError("model registry training records identity is invalid")
    if strict_pit_eligible:
        strict_identity = _strict_training_identity(registry.get("pit_evidence"))
        if registry.get("dataset_sha256") != strict_identity["dataset_sha256"]:
            raise ValueError("model registry dataset does not match the verified archive")
        if registry.get("training_records_sha256") != strict_identity[
            "training_records_sha256"
        ]:
            raise ValueError("model registry training records do not match the dataset")
    if tuple(registry.get("feature_names") or ()) != V1_FEATURE_NAMES:
        raise ValueError("model registry feature order/schema mismatch")
    if registry.get("feature_schema_sha256") != feature_schema_sha256():
        raise ValueError("model registry feature schema SHA mismatch")
    if registry.get("label_definition") != LABEL_DEFINITION:
        raise ValueError("model registry label definition mismatch")
    experiment = registry.get("experiment")
    classification = registry.get("dataset_classification")
    if not isinstance(experiment, dict):
        raise ValueError("model registry experiment contract is required")
    config = validate_experiment_config(
        experiment.get("config") or {},
        allow_fixture=classification == "synthetic_fixture",
    )
    expected_experiment_sha = compute_experiment_config_sha256(
        config,
        allow_fixture=classification == "synthetic_fixture",
    )
    if experiment.get("config_sha256") != expected_experiment_sha:
        raise ValueError("model registry experiment SHA mismatch")
    validate_model_parameter_binding(registry.get("parameters") or {}, config)
    freshness = registry.get("model_freshness")
    if not isinstance(freshness, dict) or freshness != {
        "anchor": "model_available_from",
        "max_calendar_age_days": MODEL_MAX_AGE_DAYS,
    }:
        raise ValueError("model registry freshness contract mismatch")
    if classification not in {
        "observed_research",
        "synthetic_fixture",
    }:
        raise ValueError("model registry dataset classification mismatch")
    if classification == "observed_research":
        if registry.get("strict_pit_eligible") is not True:
            raise ValueError("observed research model requires strict PIT eligibility")
    try:
        available_from = date.fromisoformat(str(registry.get("model_available_from") or ""))
        registered_at = datetime.fromisoformat(str(registry.get("registered_at") or ""))
        maturity_end = date.fromisoformat(
            str((registry.get("label_maturity_period") or {}).get("end") or "")
        )
    except ValueError as exc:
        raise ValueError("model registry availability date is invalid") from exc
    if registered_at.tzinfo is None or registered_at.utcoffset() is None:
        raise ValueError("model registry registration timestamp is invalid")
    if available_from < maturity_end:
        raise ValueError("model registry availability precedes label maturity")
    if classification == "observed_research":
        latest_capture = date.fromisoformat(strict_identity["latest_label_capture_date"])
        if available_from <= max(latest_capture, registered_at.date()):
            raise ValueError("observed model availability was backdated")
    artifact = registry.get("model_artifact")
    if not isinstance(artifact, dict) or artifact.get("path") != "model.txt":
        raise ValueError("model registry artifact path is invalid")
    model_path = destination / "model.txt"
    if _file_sha256(model_path) != artifact.get("sha256"):
        raise ValueError("model artifact SHA mismatch")

    from .contract import import_optional_ml_module, optional_ml_dependency_readiness

    readiness = optional_ml_dependency_readiness()
    if readiness["status"] != "ready":
        missing = ", ".join(readiness["missing_packages"])
        raise RuntimeError(f"optional ML dependencies unavailable: {missing}")
    lgb = import_optional_ml_module("lightgbm")

    booster = lgb.Booster(model_file=str(model_path))
    if tuple(booster.feature_name()) != V1_FEATURE_NAMES:
        raise ValueError("loaded model feature order/schema mismatch")
    validate_booster_parameter_binding(booster, config)
    metadata = dict(registry)
    metadata["registry_sha256"] = registry_sha256
    loaded_model = RankerModel(
        booster=_VerifiedBoosterProxy(booster),
        feature_names=V1_FEATURE_NAMES,
        metadata=metadata,
    )
    _register_verified_model_bundle(loaded_model)
    return loaded_model
