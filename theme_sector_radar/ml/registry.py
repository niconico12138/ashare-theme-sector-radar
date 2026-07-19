"""Content-bound model registry for ML stock-ranker shadow bundles."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
from datetime import date
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


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    return {
        "dataset_sha256": str(dataset["dataset_sha256"]),
        "training_records_sha256": canonical_sha256(dataset["records"]),
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
) -> dict[str, Any]:
    """Write a new model bundle without overwriting an existing bundle."""

    if not model_version or not _SHA256.fullmatch(dataset_sha256):
        raise ValueError("model_version and a lowercase dataset SHA-256 are required")
    if tuple(model.feature_names) != V1_FEATURE_NAMES:
        raise ValueError("trained model feature order/schema mismatch")
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
    try:
        available_from = date.fromisoformat(model_available_from)
        maturity_end = date.fromisoformat(
            str(model.metadata["label_maturity_period"]["end"])
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("model availability or label maturity date is invalid") from exc
    if available_from.isoformat() != model_available_from or available_from < maturity_end:
        raise ValueError("model_available_from must not precede label maturity")
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
        "model_artifact": {
            "path": "model.txt",
            "sha256": model_sha256,
        },
        "feature_importance_gain": {
            name: float(value) for name, value in zip(model.feature_names, importances)
        },
        "disclaimer": DISCLAIMER,
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
    freshness = registry.get("model_freshness")
    if not isinstance(freshness, dict) or freshness != {
        "anchor": "model_available_from",
        "max_calendar_age_days": MODEL_MAX_AGE_DAYS,
    }:
        raise ValueError("model registry freshness contract mismatch")
    if registry.get("dataset_classification") not in {
        "observed_research",
        "synthetic_fixture",
    }:
        raise ValueError("model registry dataset classification mismatch")
    try:
        available_from = date.fromisoformat(str(registry.get("model_available_from") or ""))
        maturity_end = date.fromisoformat(
            str((registry.get("label_maturity_period") or {}).get("end") or "")
        )
    except ValueError as exc:
        raise ValueError("model registry availability date is invalid") from exc
    if available_from < maturity_end:
        raise ValueError("model registry availability precedes label maturity")
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
    metadata = dict(registry)
    metadata["registry_sha256"] = registry_sha256
    return RankerModel(
        booster=booster,
        feature_names=V1_FEATURE_NAMES,
        metadata=metadata,
    )
