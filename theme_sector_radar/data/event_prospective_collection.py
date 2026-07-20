"""Immutable prospective event collection and A/B Shadow daily manifests."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import math
import os
import tempfile
from typing import Any, Iterable, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import validate_no_executable_instructions
from theme_sector_radar.reporting.strict_json import load_strict_json_with_sha256, write_strict_json_atomic

from .event_adjustment_ranking_shadow import (
    build_event_adjustment_manifest,
    build_event_adjustment_ranking_ab_shadow,
    build_event_ab_metric_preregistration,
    validate_base_ranking_snapshot,
)
from .event_adjustment_shadow import validate_event_adjustment_shadow
from .event_enhancement import validate_event_enhancement, validate_event_exposure_mapping
from .official_announcements import DISCLAIMER, MODE
from .risk_event_schema import canonical_date, canonical_json_bytes, canonical_sha256, validate_risk_event


PROSPECTIVE_COLLECTION_SCHEMA_VERSION = "event-prospective-collection-v1"
DAILY_READINESS_SCHEMA_VERSION = "event-prospective-readiness-v1"
DAILY_AB_SNAPSHOT_SCHEMA_VERSION = "event-prospective-ab-daily-snapshot-v1"
RUNNER_MANIFEST_SCHEMA_VERSION = "event-adjustment-runner-manifest-v1"
COLLECTION_ORIGINS = {"real", "fixture"}
_SAFE_STATUSES = {"ok", "observed", "blocked", "unknown", "unavailable", "parse_failed", "fixture"}


@dataclass(frozen=True)
class ProspectiveReadinessConfig:
    minimum_real_event_count: int = 1
    minimum_distinct_real_sources: int = 1
    maximum_unknown_mapping_count: int = 0
    require_commodity_units_currency: bool = True

    def validate(self) -> "ProspectiveReadinessConfig":
        if isinstance(self.minimum_real_event_count, bool) or self.minimum_real_event_count < 0:
            raise ValueError("minimum_real_event_count must be non-negative")
        if isinstance(self.minimum_distinct_real_sources, bool) or self.minimum_distinct_real_sources < 0:
            raise ValueError("minimum_distinct_real_sources must be non-negative")
        if isinstance(self.maximum_unknown_mapping_count, bool) or self.maximum_unknown_mapping_count < 0:
            raise ValueError("maximum_unknown_mapping_count must be non-negative")
        if not isinstance(self.require_commodity_units_currency, bool):
            raise ValueError("require_commodity_units_currency must be boolean")
        return self


def _write_json_once(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing, _ = load_strict_json_with_sha256(path)
        if existing != dict(payload):
            raise ValueError(f"immutable prospective artifact changed: {path}")
    else:
        write_strict_json_atomic(path, dict(payload))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("prospective artifact escaped daily archive root") from exc


def _source_health_rows(source_health: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    seen: set[str] = set()
    for raw in source_health:
        source_id = str(raw.get("source_id") or raw.get("provider_id") or "")
        status = str(raw.get("status") or raw.get("health_status") or "unknown")
        if not source_id or source_id in seen:
            raise ValueError("prospective source health requires unique source IDs")
        if status not in _SAFE_STATUSES:
            status = "unknown"
        if raw.get("event_state") == "no_event":
            raise ValueError("prospective source health cannot claim no_event")
        seen.add(source_id)
        rows.append({
            "source_id": source_id,
            "status": status,
            "event_state": str(raw.get("event_state") or "unknown_not_no_event"),
            "reason": raw.get("reason") or raw.get("error_code"),
            "authority_tier": raw.get("authority_tier"),
        })
    return sorted(rows, key=lambda row: row["source_id"])


def _logical_event_key(event: Mapping[str, Any]) -> str:
    return canonical_sha256({
        "event_type": event["event_type"],
        "scope": event["scope"],
        "entity_id": event["entity_id"],
        "event_time": event["event_time"],
        "published_at": event["published_at"],
        "source_id": event["source"].get("source_id"),
    })


def _event_gates(
    events: Sequence[Mapping[str, Any]],
    enhancements: Sequence[Mapping[str, Any]],
    exposures: Sequence[Mapping[str, Any]],
    source_health: Sequence[Mapping[str, Any]],
    *,
    as_of_date: str,
    origin: str,
    config: ProspectiveReadinessConfig,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    real_events = [event for event in events if event["source"].get("authority_tier") != "research_only"]
    real_sources = {str(event["source"].get("source_id")) for event in real_events}
    logical: dict[str, list[Mapping[str, Any]]] = {}
    for event in events:
        logical.setdefault(_logical_event_key(event), []).append(event)
    duplicate_groups = [rows for rows in logical.values() if len(rows) > 1 and not any(row.get("revision_of") for row in rows[1:])]
    revision_count = sum(1 for rows in logical.values() for row in rows[1:] if row.get("revision_of"))
    future_effective = [event["event_id"] for event in events if event.get("effective_from") and event["effective_from"] > as_of_date]
    source_failures = [row["source_id"] for row in source_health if row["status"] in {"blocked", "unavailable", "parse_failed"}]
    commodity_quality = []
    if config.require_commodity_units_currency:
        for event in events:
            if str(event.get("event_type", "")).startswith("commodity_"):
                fields = event.get("structured_fields") or {}
                if not fields.get("unit") or not fields.get("currency"):
                    commodity_quality.append(event["event_id"])
    unknown_mappings = sum(
        len(mapping.get("unknown_mappings") or [])
        for mapping in exposures
        if mapping.get("status") in {"unknown", "partial_unknown"}
    )
    checks = [
        ("minimum_real_event_coverage", origin == "fixture" or len(real_events) >= config.minimum_real_event_count, {"real_event_count": len(real_events), "required": config.minimum_real_event_count}),
        ("minimum_distinct_real_sources", origin == "fixture" or len(real_sources) >= config.minimum_distinct_real_sources, {"distinct_real_sources": len(real_sources), "required": config.minimum_distinct_real_sources}),
        ("duplicate_event_gate", not duplicate_groups, {"duplicate_group_count": len(duplicate_groups), "revision_count": revision_count}),
        ("cross_day_effective_gate", not future_effective, {"future_effective_event_ids": future_effective}),
        ("source_health_gate", not source_failures or origin == "fixture", {"failed_sources": source_failures}),
        ("commodity_unit_currency_gate", not commodity_quality, {"invalid_event_ids": commodity_quality}),
        ("mapping_unknown_gate", unknown_mappings <= config.maximum_unknown_mapping_count, {"unknown_mapping_count": unknown_mappings, "maximum": config.maximum_unknown_mapping_count}),
    ]
    for name, passed, details in checks:
        gates.append({"gate": name, "status": "pass" if passed else "blocked", "details": details})
    if origin == "fixture":
        review_status = "fixture_review_only"
    elif all(gate["status"] == "pass" for gate in gates):
        review_status = "ready_for_manual_shadow_review"
    else:
        review_status = "blocked_insufficient_real_event_coverage"
    readiness = {
        "schema_version": DAILY_READINESS_SCHEMA_VERSION,
        "mode": MODE,
        "as_of_date": as_of_date,
        "data_origin": origin,
        "review_status": review_status,
        "approved_for_frozen_oos_ab": False,
        "real_event_count": len(real_events),
        "real_source_count": len(real_sources),
        "fixture_event_count": len(events) - len(real_events),
        "revision_count": revision_count,
        "source_failure_count": len(source_failures),
        "unknown_mapping_count": unknown_mappings,
        "gates": gates,
        "effect_claim_allowed": False,
        "formal_ranking_allowed": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    return gates, readiness


def _ab_daily_snapshot(
    base_snapshots: Mapping[str, Mapping[str, Any]],
    adjustment: Mapping[str, Any],
    adjustment_manifest: Mapping[str, Any],
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    outputs = {}
    for scope, base in base_snapshots.items():
        key = "sector" if scope == "sector" else "individual"
        try:
            outputs[key] = build_event_adjustment_ranking_ab_shadow(base, adjustment, adjustment_manifest)
        except ValueError as exc:
            outputs[key] = {
                "schema_version": EVENT_AB_DAILY_SNAPSHOT_SCHEMA_VERSION,
                "mode": MODE,
                "status": "blocked",
                "entity_scope": key,
                "reason": str(exc),
                "a_original_snapshot": None,
                "b_event_adjusted_shadow": None,
                "effect_claim_allowed": False,
                "formal_ranking_allowed": False,
                "promotion_allowed": False,
                "live_trading_allowed": False,
                "disclaimer": DISCLAIMER,
            }
    return {
        "schema_version": DAILY_AB_SNAPSHOT_SCHEMA_VERSION,
        "mode": MODE,
        "status": "fixture_only" if readiness["data_origin"] == "fixture" else readiness["review_status"],
        "as_of_date": readiness["as_of_date"],
        "review_status": readiness["review_status"],
        "approved_for_frozen_oos_ab": False,
        "snapshots": outputs,
        "metric_registration": build_event_ab_metric_preregistration(),
        "effect_claim_allowed": False,
        "formal_ranking_allowed": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }


def _runner_manifest(
    *,
    entity_scope: str,
    as_of_date: str,
    adjustment: Mapping[str, Any],
    adjustment_manifest: Mapping[str, Any],
    adjustment_file_sha256: str,
    collection_binding_sha256: str,
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    view_key = "sector_event_adjustment_shadow" if entity_scope == "sector" else "stock_event_adjustment_shadow"
    records = adjustment.get(view_key) or []
    manifest = {
        "schema_version": RUNNER_MANIFEST_SCHEMA_VERSION,
        "mode": MODE,
        "artifact_type": "event_adjustment_runner_manifest",
        "entity_scope": entity_scope,
        "as_of_date": as_of_date,
        "effective_from_dates": adjustment.get("effective_from_dates") or [],
        "pit_statuses": adjustment.get("pit_statuses") or [],
        "adjustment_artifact_sha256": adjustment_manifest["artifact_sha256"],
        "adjustment_manifest_sha256": adjustment_manifest["manifest_sha256"],
        "adjustment_file_sha256": adjustment_file_sha256,
        "collection_binding_sha256": collection_binding_sha256,
        "record_count": len(records),
        "review_status": "pending",
        "readiness_status": readiness["review_status"],
        "approved_for_frozen_oos_ab": False,
        "manual_review_required": True,
        "formal_ranking_allowed": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    return manifest


def archive_prospective_event_day(
    archive_root: Path | str,
    research_archive_root: Path | str,
    *,
    as_of_date: str,
    collected_at: str,
    data_origin: str,
    events: Sequence[Mapping[str, Any]],
    enhancements: Sequence[Mapping[str, Any]],
    exposure_mappings: Sequence[Mapping[str, Any]],
    adjustment: Mapping[str, Any],
    source_health: Sequence[Mapping[str, Any]],
    base_snapshots: Mapping[str, Mapping[str, Any]] | None = None,
    readiness_config: ProspectiveReadinessConfig | None = None,
) -> dict[str, Any]:
    day = canonical_date(as_of_date, field="as_of_date")
    if data_origin not in COLLECTION_ORIGINS:
        raise ValueError("prospective data_origin is invalid")
    real_root = Path(archive_root).resolve()
    research_root = Path(research_archive_root).resolve()
    if real_root == research_root:
        raise ValueError("real and research prospective roots must be separate")
    target_root = real_root if data_origin == "real" else research_root
    day_root = target_root / day
    collected = str(collected_at)
    if not collected.endswith("+08:00") and "+" not in collected and not collected.endswith("Z"):
        raise ValueError("collected_at must be timezone-aware")
    validated_events = [validate_risk_event(event) for event in events]
    validated_enhancements = [validate_event_enhancement(item) for item in enhancements]
    validated_exposures = [validate_event_exposure_mapping(item) for item in exposure_mappings]
    validated_adjustment = validate_event_adjustment_shadow(adjustment)
    health_rows = _source_health_rows(source_health)
    if data_origin == "real":
        if any(event["source"].get("authority_tier") == "research_only" for event in validated_events):
            raise ValueError("research-only event cannot enter real prospective root")
        if any(snapshot.get("pit_status") == "fixture_verified" for snapshot in (base_snapshots or {}).values()):
            raise ValueError("fixture base snapshot cannot enter real prospective root")
    event_ids = {event["event_id"] for event in validated_events}
    enhancement_ids = {item["enhancement_id"] for item in validated_enhancements}
    for item in validated_enhancements:
        if item["event_id"] not in event_ids:
            raise ValueError("enhancement references an event outside daily collection")
    for mapping in validated_exposures:
        if mapping["enhancement_id"] not in enhancement_ids:
            raise ValueError("exposure mapping references an enhancement outside daily collection")
    if any(row.get("post_event_backtest_included") is not False for row in validated_adjustment.get("adjustment_lineage") or []):
        raise ValueError("post-event data cannot enter prospective adjustment archive")
    config = (readiness_config or ProspectiveReadinessConfig()).validate()
    _gates, readiness = _event_gates(
        validated_events,
        validated_enhancements,
        validated_exposures,
        health_rows,
        as_of_date=day,
        origin=data_origin,
        config=config,
    )
    adjustment_manifest = build_event_adjustment_manifest(validated_adjustment)
    layers = {
        "canonical_events": {"schema_version": "prospective-canonical-events-v1", "mode": MODE, "as_of_date": day, "data_origin": data_origin, "records": validated_events},
        "enhancements": {"schema_version": "prospective-event-enhancements-v1", "mode": MODE, "as_of_date": day, "data_origin": data_origin, "records": validated_enhancements},
        "exposure_mappings": {"schema_version": "prospective-exposure-mappings-v1", "mode": MODE, "as_of_date": day, "data_origin": data_origin, "records": validated_exposures},
        "adjustment": {"schema_version": "prospective-event-adjustment-v1", "mode": MODE, "as_of_date": day, "data_origin": data_origin, "artifact": validated_adjustment, "manifest": adjustment_manifest},
        "source_health": {"schema_version": "prospective-source-health-v1", "mode": MODE, "as_of_date": day, "data_origin": data_origin, "sources": health_rows},
        "readiness": readiness,
    }
    layer_manifest_rows: dict[str, Any] = {}
    for name, payload in layers.items():
        path = day_root / "layers" / f"{name}.json"
        file_sha = _write_json_once(path, payload)
        layer_manifest_rows[name] = {
            "relative_path": _safe_relative(path, day_root),
            "file_sha256": file_sha,
            "payload_sha256": canonical_sha256(payload),
        }
    collection_binding = canonical_sha256({"as_of_date": day, "data_origin": data_origin, "layers": layer_manifest_rows})
    runner_manifests = {}
    for scope in ("sector", "individual"):
        runner = _runner_manifest(
            entity_scope=scope,
            as_of_date=day,
            adjustment=validated_adjustment,
            adjustment_manifest=adjustment_manifest,
            adjustment_file_sha256=layer_manifest_rows["adjustment"]["file_sha256"],
            collection_binding_sha256=collection_binding,
            readiness=readiness,
        )
        path = day_root / "runner_manifests" / f"{scope}_event_adjustment_manifest.json"
        file_sha = _write_json_once(path, runner)
        runner_manifests[scope] = {
            "relative_path": _safe_relative(path, day_root),
            "file_sha256": file_sha,
            "manifest_sha256": runner["manifest_sha256"],
        }
    ab_snapshot = _ab_daily_snapshot(
        {key: validate_base_ranking_snapshot(value) for key, value in (base_snapshots or {}).items()},
        validated_adjustment,
        adjustment_manifest,
        readiness,
    )
    ab_path = day_root / "ab_shadow" / "daily_snapshot.json"
    ab_file_sha = _write_json_once(ab_path, ab_snapshot)
    readiness_path = day_root / "readiness" / "coverage_readiness.json"
    readiness_file_sha = _write_json_once(readiness_path, readiness)
    manifest = {
        "schema_version": PROSPECTIVE_COLLECTION_SCHEMA_VERSION,
        "mode": MODE,
        "artifact_type": "prospective_event_day_manifest",
        "as_of_date": day,
        "collected_at": collected,
        "data_origin": data_origin,
        "review_status": readiness["review_status"],
        "readiness_status": readiness["review_status"],
        "approved_for_frozen_oos_ab": False,
        "layer_manifests": layer_manifest_rows,
        "runner_manifests": runner_manifests,
        "ab_shadow_daily_snapshot": {"relative_path": _safe_relative(ab_path, day_root), "file_sha256": ab_file_sha},
        "readiness": {"relative_path": _safe_relative(readiness_path, day_root), "file_sha256": readiness_file_sha},
        "collection_binding_sha256": collection_binding,
        "effect_claim_allowed": False,
        "formal_ranking_allowed": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    manifest_path = day_root / "collection_manifest.json"
    manifest_file_sha = _write_json_once(manifest_path, manifest)
    return {
        **manifest,
        "manifest_path": str(manifest_path),
        "manifest_file_sha256": manifest_file_sha,
        "archive_root": str(day_root),
    }


def load_prospective_event_day(manifest_path: Path | str) -> dict[str, Any]:
    path = Path(manifest_path).resolve()
    manifest, file_sha = load_strict_json_with_sha256(path)
    if manifest.get("schema_version") != PROSPECTIVE_COLLECTION_SCHEMA_VERSION:
        raise ValueError("prospective collection manifest schema mismatch")
    root = path.parent
    for entry in manifest.get("layer_manifests", {}).values():
        layer_path = (root / str(entry["relative_path"])).resolve()
        if _safe_relative(layer_path, root) != str(entry["relative_path"]):
            raise ValueError("prospective layer path escapes daily root")
        payload, actual_sha = load_strict_json_with_sha256(layer_path)
        if actual_sha != entry["file_sha256"] or canonical_sha256(payload) != entry["payload_sha256"]:
            raise ValueError("prospective layer SHA mismatch")
    if file_sha != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError("prospective manifest SHA changed while reading")
    return dict(manifest)


__all__ = [
    "DAILY_AB_SNAPSHOT_SCHEMA_VERSION",
    "DAILY_READINESS_SCHEMA_VERSION",
    "ProspectiveReadinessConfig",
    "archive_prospective_event_day",
    "load_prospective_event_day",
]
