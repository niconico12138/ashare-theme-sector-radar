"""Inventory ML shadow artifacts without mutating content-addressed history."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from theme_sector_radar.ml.schema import DISCLAIMER, MODE
from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)


INVENTORY_SCHEMA_VERSION = "ml-artifact-inventory-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CURRENT_STATUSES = frozenset(
    {
        "active",
        "blocked",
        "captured",
        "insufficient_data",
        "ok",
        "pending_label_maturity",
        "ready",
        "trained_shadow",
        "unavailable",
        "verified",
    }
)


def _common_anchor(roots: list[Path]) -> Path:
    try:
        return Path(os.path.commonpath([str(root) for root in roots]))
    except ValueError as exc:
        raise ValueError("ML artifact roots must share a filesystem anchor") from exc


def _relative_path(path: Path, anchor: Path) -> str:
    return path.relative_to(anchor).as_posix()


def _iter_artifact_files(roots: Iterable[Path], output_path: Path) -> list[Path]:
    files: set[Path] = set()
    output_resolved = output_path.resolve()
    for raw_root in roots:
        root = raw_root.resolve()
        if not root.exists():
            raise ValueError(f"ML artifact root is missing: {root}")
        candidates = [root] if root.is_file() else list(root.rglob("*"))
        for path in candidates:
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved == output_resolved:
                continue
            if resolved.suffix.casefold() == ".json" or resolved.name == "model.txt":
                files.add(resolved)
    return sorted(files, key=lambda path: str(path).casefold())


def _require_registry_model_pairs(files: Iterable[Path]) -> None:
    """Reject model registries or binaries that cannot be bound as a pair."""

    file_set = {path.resolve() for path in files}
    for path in file_set:
        if path.name == "registry.json":
            model_path = (path.parent / "model.txt").resolve()
            if model_path not in file_set:
                raise ValueError(f"ML registry/model pair is incomplete: {path}")
            registry, _registry_sha = load_strict_json_with_sha256(path)
            artifact = registry.get("model_artifact") if isinstance(registry, Mapping) else None
            if (
                not isinstance(artifact, Mapping)
                or artifact.get("path") != "model.txt"
                or artifact.get("sha256")
                != hashlib.sha256(model_path.read_bytes()).hexdigest()
            ):
                raise ValueError(f"ML registry model SHA mismatch: {path}")
        if path.name == "model.txt" and (path.parent / "registry.json").resolve() not in file_set:
            raise ValueError(f"ML registry/model pair is incomplete: {path}")


def _validate_live_flags(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in {
                "live_trading_allowed",
                "promotion_allowed",
                "eligible_for_oos_claim",
            } and child is not False:
                raise ValueError(
                    f"ML artifact {key} must be false: {child_path}"
                )
            _validate_live_flags(child, path=child_path)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_live_flags(child, path=f"{path}[{index}]")


def _json_entry(path: Path, *, relative: str) -> dict[str, Any]:
    try:
        payload, sha256 = load_strict_json_with_sha256(path)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"ML artifact is not strict JSON: {relative}: {exc}") from exc
    validate_no_executable_instructions(payload, context=f"ML artifact {relative}")
    _validate_live_flags(payload, path=relative)
    complete_current_contract = (
        isinstance(payload, Mapping)
        and isinstance(payload.get("schema_version"), str)
        and str(payload["schema_version"]).startswith("ml-")
        and payload.get("mode") == MODE
        and payload.get("status") in _CURRENT_STATUSES
        and payload.get("eligible_for_oos_claim") is False
        and payload.get("promotion_allowed") is False
        and payload.get("live_trading_allowed") is False
    )
    return {
        "path": relative,
        "artifact_type": "strict_json",
        "sha256": sha256,
        "artifact_status": (
            "current_or_compatible" if complete_current_contract else "superseded_legacy"
        ),
        "eligible_as_current_evidence": complete_current_contract,
        "inline_live_flag_present": (
            isinstance(payload, Mapping) and "live_trading_allowed" in payload
        ),
        "inline_safety_envelope_complete": complete_current_contract,
        "live_trading_allowed": False,
    }


def _model_entry(path: Path, *, relative: str) -> dict[str, Any]:
    return {
        "path": relative,
        "artifact_type": "model_binary",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "artifact_status": "bound_model_binary",
        "eligible_as_current_evidence": False,
        "inline_live_flag_present": False,
        "live_trading_allowed": False,
    }


def _resolved_roots(roots: Iterable[Path]) -> list[Path]:
    resolved = sorted(
        {Path(root).resolve() for root in roots},
        key=lambda path: str(path).casefold(),
    )
    if not resolved:
        raise ValueError("at least one ML artifact root is required")
    return resolved


def build_artifact_inventory(
    roots: Iterable[Path], *, output_path: Path
) -> dict[str, Any]:
    """Build a strict identity map for current and superseded ML artifacts."""

    resolved_roots = _resolved_roots(roots)
    anchor = _common_anchor(resolved_roots)
    artifacts: list[dict[str, Any]] = []
    physical_files = _iter_artifact_files(resolved_roots, output_path)
    _require_registry_model_pairs(physical_files)
    for path in physical_files:
        relative = _relative_path(path, anchor)
        artifacts.append(
            _model_entry(path, relative=relative)
            if path.name == "model.txt"
            else _json_entry(path, relative=relative)
        )

    legacy_count = sum(
        entry["artifact_status"] == "superseded_legacy" for entry in artifacts
    )
    compatible_count = sum(
        entry["artifact_status"] == "current_or_compatible" for entry in artifacts
    )
    model_count = sum(entry["artifact_type"] == "model_binary" for entry in artifacts)
    inventory = {
        "schema_version": INVENTORY_SCHEMA_VERSION,
        "mode": MODE,
        "status": "ok",
        "source_anchor": str(anchor),
        "source_roots": [_relative_path(root, anchor) for root in resolved_roots],
        "artifact_count": len(artifacts),
        "json_artifact_count": len(artifacts) - model_count,
        "model_binary_count": model_count,
        "current_or_compatible_count": compatible_count,
        "legacy_missing_live_flag_count": legacy_count,
        "legacy_policy": (
            "Historical JSON without an explicit false live flag is immutable evidence "
            "only and is ineligible as current evidence."
        ),
        "artifacts": artifacts,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(inventory, context="ML artifact inventory")
    write_strict_json_atomic(output_path, inventory)
    return inventory


def verify_artifact_inventory(
    inventory_path: Path | str, *, expected_sha256: str
) -> dict[str, Any]:
    """Verify an existing inventory and every bound file without writing."""

    path = Path(inventory_path)
    inventory, inventory_sha = load_strict_json_with_sha256(path)
    expected_sha = str(expected_sha256 or "").lower()
    if not _SHA256.fullmatch(expected_sha) or inventory_sha != expected_sha:
        raise ValueError("ML artifact inventory SHA mismatch")
    if (
        not isinstance(inventory, Mapping)
        or inventory.get("schema_version") != INVENTORY_SCHEMA_VERSION
        or inventory.get("mode") != MODE
        or inventory.get("status") != "ok"
        or inventory.get("promotion_allowed") is not False
        or inventory.get("live_trading_allowed") is not False
    ):
        raise ValueError("ML artifact inventory contract mismatch")
    validate_no_executable_instructions(inventory, context="ML artifact inventory")

    anchor = Path(str(inventory.get("source_anchor") or "")).resolve()
    raw_roots = inventory.get("source_roots")
    raw_entries = inventory.get("artifacts")
    if not anchor.is_absolute() or not isinstance(raw_roots, list) or not isinstance(
        raw_entries, list
    ):
        raise ValueError("ML artifact inventory roots or entries are invalid")
    roots = [(anchor / str(relative)).resolve() for relative in raw_roots]
    physical = _iter_artifact_files(roots, path)
    physical_by_relative = {
        _relative_path(item, anchor): item for item in physical
    }
    entries: dict[str, Mapping[str, Any]] = {}
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, Mapping):
            raise ValueError("ML artifact inventory entry must be an object")
        relative = str(raw_entry.get("path") or "")
        if relative in entries:
            raise ValueError("ML artifact inventory contains duplicate paths")
        entries[relative] = raw_entry
    if set(entries) != set(physical_by_relative):
        raise ValueError("ML artifact inventory does not cover the physical roots")
    _require_registry_model_pairs(physical_by_relative.values())

    for relative, entry in entries.items():
        bound_path = physical_by_relative[relative]
        resolved = bound_path.resolve()
        try:
            resolved.relative_to(anchor)
        except ValueError as exc:
            raise ValueError("ML artifact inventory path escapes its anchor") from exc
        actual_sha = hashlib.sha256(resolved.read_bytes()).hexdigest()
        if entry.get("sha256") != actual_sha:
            raise ValueError(f"ML artifact SHA mismatch: {relative}")
        if entry.get("live_trading_allowed") is not False:
            raise ValueError(f"ML artifact inventory live flag mismatch: {relative}")
        if resolved.name == "model.txt":
            if (
                entry.get("artifact_type") != "model_binary"
                or entry.get("artifact_status") != "bound_model_binary"
                or entry.get("eligible_as_current_evidence") is not False
            ):
                raise ValueError(f"ML model binary inventory mismatch: {relative}")
            continue
        expected = _json_entry(resolved, relative=relative)
        if dict(entry) != expected:
            raise ValueError(f"ML JSON artifact inventory mismatch: {relative}")

    json_count = sum(entry.get("artifact_type") == "strict_json" for entry in entries.values())
    model_count = len(entries) - json_count
    legacy_count = sum(
        entry.get("artifact_status") == "superseded_legacy"
        for entry in entries.values()
    )
    compatible_count = sum(
        entry.get("artifact_status") == "current_or_compatible"
        for entry in entries.values()
    )
    expected_counts = {
        "artifact_count": len(entries),
        "json_artifact_count": json_count,
        "model_binary_count": model_count,
        "legacy_missing_live_flag_count": legacy_count,
        "current_or_compatible_count": compatible_count,
    }
    if any(inventory.get(key) != value for key, value in expected_counts.items()):
        raise ValueError("ML artifact inventory count mismatch")
    return dict(inventory)
