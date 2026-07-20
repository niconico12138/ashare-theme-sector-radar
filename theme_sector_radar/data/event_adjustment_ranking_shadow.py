"""A/B ranking Shadow adapter over immutable base and event-adjustment evidence."""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import validate_no_executable_instructions

from .event_adjustment_shadow import (
    build_copper_adjustment_research_case,
    validate_event_adjustment_shadow,
)
from .official_announcements import DISCLAIMER, MODE
from .risk_event_schema import canonical_date, canonical_json_bytes, canonical_sha256


BASE_RANKING_SNAPSHOT_SCHEMA_VERSION = "event-ab-base-ranking-snapshot-v1"
EVENT_ADJUSTMENT_MANIFEST_SCHEMA_VERSION = "event-adjustment-shadow-manifest-v1"
EVENT_AB_RANKING_SCHEMA_VERSION = "event-adjustment-ranking-ab-shadow-v1"
EVENT_AB_METRICS_SCHEMA_VERSION = "event-adjustment-ranking-metrics-preregistration-v1"
EVENT_AB_EVALUATION_SCHEMA_VERSION = "event-adjustment-ranking-evaluation-shadow-v1"
PROTECTED_FIELDS = {
    "score", "quant_score", "final_score", "v2_score", "selection_score",
    "event_score", "confidence", "rank", "action", "trade", "order", "position",
    "target_price",
}
PIT_STATUSES = {"verified", "fixture_verified", "timestamp", "date_only"}


def _reject_protected(value: Any, *, path: str = "event_ab_shadow") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).casefold()
            if normalized in PROTECTED_FIELDS or normalized.endswith("_score"):
                raise ValueError(f"event A/B Shadow contains protected field: {path}.{key}")
            _reject_protected(child, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_protected(child, path=f"{path}[{index}]")


def build_base_ranking_snapshot(
    *,
    entity_scope: str,
    as_of_date: str,
    effective_from: str,
    pit_status: str,
    source_id: str,
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if entity_scope not in {"sector", "individual"}:
        raise ValueError("base ranking snapshot scope must be sector or individual")
    normalized_rows = []
    for raw in rows:
        entity_id = str(raw.get("entity_id") or "")
        base_rank = raw.get("base_rank")
        base_value = raw.get("base_value")
        if not entity_id or isinstance(base_rank, bool) or not isinstance(base_rank, int) or base_rank <= 0:
            raise ValueError("base ranking row identity or base_rank is invalid")
        if isinstance(base_value, bool) or not isinstance(base_value, (int, float)) or not math.isfinite(base_value):
            raise ValueError("base ranking row base_value must be finite")
        normalized_rows.append({
            "entity_scope": entity_scope,
            "entity_id": entity_id,
            "base_rank": base_rank,
            "base_value": float(base_value),
        })
    snapshot = {
        "schema_version": BASE_RANKING_SNAPSHOT_SCHEMA_VERSION,
        "mode": MODE,
        "artifact_type": "event_ab_base_ranking_snapshot",
        "entity_scope": entity_scope,
        "as_of_date": canonical_date(as_of_date, field="as_of_date"),
        "effective_from": canonical_date(effective_from, field="effective_from"),
        "pit_status": pit_status,
        "source_id": source_id,
        "rows": sorted(normalized_rows, key=lambda row: row["base_rank"]),
        "research_only": True,
        "formal_ranking_allowed": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    snapshot["snapshot_sha256"] = canonical_sha256(snapshot)
    return validate_base_ranking_snapshot(snapshot)


def validate_base_ranking_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if snapshot.get("schema_version") != BASE_RANKING_SNAPSHOT_SCHEMA_VERSION or snapshot.get("mode") != MODE:
        raise ValueError("base ranking snapshot schema or mode mismatch")
    if snapshot.get("entity_scope") not in {"sector", "individual"} or snapshot.get("pit_status") not in PIT_STATUSES:
        raise ValueError("base ranking snapshot scope or PIT status is invalid")
    as_of = canonical_date(snapshot.get("as_of_date"), field="as_of_date")
    effective = canonical_date(snapshot.get("effective_from"), field="effective_from")
    if effective > as_of:
        raise ValueError("base ranking snapshot effective_from is after as_of_date")
    rows = snapshot.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("base ranking snapshot rows are missing")
    ids = [str(row.get("entity_id") or "") for row in rows]
    ranks = [row.get("base_rank") for row in rows]
    if len(set(ids)) != len(ids) or sorted(ranks) != list(range(1, len(rows) + 1)):
        raise ValueError("base ranking snapshot identities or ranks are not unique/contiguous")
    for row in rows:
        if row.get("entity_scope") != snapshot["entity_scope"]:
            raise ValueError("base ranking row scope mismatch")
        value = row.get("base_value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("base ranking value is invalid")
    expected = canonical_sha256({key: value for key, value in snapshot.items() if key != "snapshot_sha256"})
    if snapshot.get("snapshot_sha256") != expected:
        raise ValueError("base ranking snapshot SHA mismatch")
    if any(snapshot.get(key) is not False for key in ("formal_ranking_allowed", "promotion_allowed", "live_trading_allowed")):
        raise ValueError("base ranking snapshot safety flags must be false")
    _reject_protected(snapshot)
    canonical_json_bytes(dict(snapshot))
    return dict(snapshot)


def build_event_adjustment_manifest(adjustment: Mapping[str, Any]) -> dict[str, Any]:
    checked = validate_event_adjustment_shadow(adjustment)
    manifest = {
        "schema_version": EVENT_ADJUSTMENT_MANIFEST_SCHEMA_VERSION,
        "mode": MODE,
        "artifact_schema_version": checked["schema_version"],
        "artifact_sha256": canonical_sha256(checked),
        "as_of_dates": list(checked.get("as_of_dates") or []),
        "effective_from_dates": list(checked.get("effective_from_dates") or []),
        "pit_statuses": list(checked.get("pit_statuses") or []),
        "post_event_backtest_included": False,
        "research_only": True,
        "formal_ranking_allowed": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    return validate_event_adjustment_manifest(manifest, checked)


def validate_event_adjustment_manifest(
    manifest: Mapping[str, Any], adjustment: Mapping[str, Any],
) -> dict[str, Any]:
    checked = validate_event_adjustment_shadow(adjustment)
    if manifest.get("schema_version") != EVENT_ADJUSTMENT_MANIFEST_SCHEMA_VERSION or manifest.get("mode") != MODE:
        raise ValueError("event adjustment manifest schema or mode mismatch")
    if manifest.get("artifact_sha256") != canonical_sha256(checked):
        raise ValueError("event adjustment artifact SHA mismatch")
    expected = canonical_sha256({key: value for key, value in manifest.items() if key != "manifest_sha256"})
    if manifest.get("manifest_sha256") != expected:
        raise ValueError("event adjustment manifest SHA mismatch")
    for key in ("as_of_dates", "effective_from_dates", "pit_statuses"):
        if list(manifest.get(key) or []) != list(checked.get(key) or []):
            raise ValueError(f"event adjustment manifest {key} mismatch")
    if manifest.get("post_event_backtest_included") is not False:
        raise ValueError("post-event data entered adjustment manifest")
    if any(manifest.get(key) is not False for key in ("formal_ranking_allowed", "promotion_allowed", "live_trading_allowed")):
        raise ValueError("event adjustment manifest safety flags must be false")
    _reject_protected(manifest)
    return dict(manifest)


def build_event_adjustment_ranking_ab_shadow(
    base_snapshot: Mapping[str, Any],
    adjustment: Mapping[str, Any],
    adjustment_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    base = validate_base_ranking_snapshot(base_snapshot)
    adjusted = validate_event_adjustment_shadow(adjustment)
    manifest = validate_event_adjustment_manifest(adjustment_manifest, adjusted)
    if list(manifest["as_of_dates"]) != [base["as_of_date"]]:
        raise ValueError("A/B Shadow base and adjustment as_of_date mismatch")
    if any(day > base["as_of_date"] for day in manifest["effective_from_dates"]):
        raise ValueError("A/B Shadow adjustment contains future effective_from")
    if not manifest["pit_statuses"] or any(status not in PIT_STATUSES for status in manifest["pit_statuses"]):
        raise ValueError("A/B Shadow adjustment PIT status is not eligible")
    view_key = (
        "sector_event_adjustment_shadow"
        if base["entity_scope"] == "sector"
        else "stock_event_adjustment_shadow"
    )
    records = list(adjusted[view_key])
    seen_event_targets: set[tuple[str, str]] = set()
    by_entity: dict[str, list[dict[str, Any]]] = {}
    for raw in records:
        record = dict(raw)
        if record.get("as_of_date") != base["as_of_date"]:
            raise ValueError("A/B Shadow adjustment row as_of_date mismatch")
        if record.get("effective_from") and record["effective_from"] > base["as_of_date"]:
            raise ValueError("A/B Shadow adjustment row is not yet effective")
        identity = (str(record.get("logical_event_id") or ""), str(record.get("entity_id") or ""))
        if identity in seen_event_targets:
            raise ValueError("A/B Shadow contains duplicate logical event/target adjustment")
        seen_event_targets.add(identity)
        by_entity.setdefault(str(record["entity_id"]), []).append(record)
    base_ids = {str(row["entity_id"]) for row in base["rows"]}
    unmatched = sorted(set(by_entity) - base_ids)
    b_rows = []
    for row in base["rows"]:
        entity_id = str(row["entity_id"])
        target_records = by_entity.get(entity_id, [])
        adjustment_value = sum(float(record["adjustment_value"]) for record in target_records)
        zero_reasons = sorted({reason for record in target_records for reason in record.get("zero_adjustment_reasons") or []})
        b_rows.append({
            "entity_scope": base["entity_scope"],
            "entity_id": entity_id,
            "base_rank": int(row["base_rank"]),
            "base_value": float(row["base_value"]),
            "adjustment": adjustment_value,
            "research_adjusted_value": float(row["base_value"]) + adjustment_value,
            "research_rank": 0,
            "research_rank_change": 0,
            "logical_event_ids": sorted({str(record["logical_event_id"]) for record in target_records}),
            "manual_review_required": any(record.get("manual_review_required") is True for record in target_records),
            "zero_adjustment_reasons": zero_reasons,
        })
    ranked = sorted(b_rows, key=lambda row: (-row["research_adjusted_value"], row["base_rank"], row["entity_id"]))
    for research_rank, row in enumerate(ranked, start=1):
        row["research_rank"] = research_rank
        row["research_rank_change"] = row["base_rank"] - research_rank
    artifact = {
        "schema_version": EVENT_AB_RANKING_SCHEMA_VERSION,
        "mode": MODE,
        "artifact_type": "event_adjustment_ranking_ab_shadow",
        "status": "fixture_only" if base["pit_status"] == "fixture_verified" else "research_only",
        "research_only": True,
        "entity_scope": base["entity_scope"],
        "as_of_date": base["as_of_date"],
        "effective_from": base["effective_from"],
        "pit_binding": {
            "base_pit_status": base["pit_status"],
            "adjustment_pit_statuses": manifest["pit_statuses"],
            "post_event_backtest_included": False,
        },
        "base_snapshot_sha256": base["snapshot_sha256"],
        "event_adjustment_artifact_sha256": manifest["artifact_sha256"],
        "event_adjustment_manifest_sha256": manifest["manifest_sha256"],
        "a_original_snapshot": {"rows": list(base["rows"])},
        "b_event_adjusted_shadow": {"rows": sorted(ranked, key=lambda row: row["research_rank"])},
        "unmatched_adjustment_entities": unmatched,
        "manual_review_required": any(row["manual_review_required"] for row in b_rows),
        "effect_claim_allowed": False,
        "formal_ranking_allowed": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    return validate_event_adjustment_ranking_ab_shadow(artifact)


def validate_event_adjustment_ranking_ab_shadow(artifact: Mapping[str, Any]) -> dict[str, Any]:
    if artifact.get("schema_version") != EVENT_AB_RANKING_SCHEMA_VERSION or artifact.get("mode") != MODE:
        raise ValueError("event A/B ranking Shadow schema or mode mismatch")
    if artifact.get("research_only") is not True or artifact.get("effect_claim_allowed") is not False:
        raise ValueError("event A/B ranking Shadow cannot claim effect")
    if any(artifact.get(key) is not False for key in ("formal_ranking_allowed", "promotion_allowed", "live_trading_allowed")):
        raise ValueError("event A/B ranking Shadow safety flags must be false")
    if artifact.get("pit_binding", {}).get("post_event_backtest_included") is not False:
        raise ValueError("post-event data entered B ranking")
    a_rows = artifact.get("a_original_snapshot", {}).get("rows")
    b_rows = artifact.get("b_event_adjusted_shadow", {}).get("rows")
    if not isinstance(a_rows, list) or not isinstance(b_rows, list) or len(a_rows) != len(b_rows):
        raise ValueError("event A/B ranking rows are missing or misaligned")
    for row in b_rows:
        required = {"base_rank", "base_value", "adjustment", "research_adjusted_value", "research_rank_change"}
        if not required.issubset(row):
            raise ValueError("event B ranking row fields are incomplete")
        if not math.isclose(row["research_adjusted_value"], row["base_value"] + row["adjustment"], abs_tol=1e-12):
            raise ValueError("event B ranking arithmetic mismatch")
    _reject_protected(artifact)
    validate_no_executable_instructions(dict(artifact), context="event A/B ranking Shadow")
    canonical_json_bytes(dict(artifact))
    return dict(artifact)


def build_event_ab_metric_preregistration() -> dict[str, Any]:
    registrations = []
    for scope, cutoffs in (("sector", (3, 5, 7)), ("individual", (1, 3, 5))):
        for top_n in cutoffs:
            registrations.append({
                "entity_scope": scope,
                "top_n": top_n,
                "forward_horizons_days": [1, 5, 20],
                "metric_names": [
                    "forward_return",
                    "rank_ic",
                    "max_drawdown",
                    "turnover",
                    "transaction_cost",
                    "event_coverage",
                ],
                "status": "pre_registered_not_run",
            })
    artifact = {
        "schema_version": EVENT_AB_METRICS_SCHEMA_VERSION,
        "mode": MODE,
        "status": "pre_registered_not_run",
        "registrations": registrations,
        "post_event_metrics_excluded_from_ranking": True,
        "effect_claim_allowed": False,
        "formal_ranking_allowed": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    artifact["registration_sha256"] = canonical_sha256(artifact)
    _reject_protected(artifact)
    return artifact


def build_event_ab_evaluation_contract(
    *, real_event_count: int, fixture_event_count: int = 0,
) -> dict[str, Any]:
    if isinstance(real_event_count, bool) or real_event_count < 0:
        raise ValueError("real_event_count must be a non-negative integer")
    if isinstance(fixture_event_count, bool) or fixture_event_count < 0:
        raise ValueError("fixture_event_count must be a non-negative integer")
    registration = build_event_ab_metric_preregistration()
    status = "blocked_insufficient_real_event_coverage" if real_event_count == 0 else "pre_registered_not_run"
    return {
        "schema_version": EVENT_AB_EVALUATION_SCHEMA_VERSION,
        "mode": MODE,
        "status": status,
        "metric_registration_sha256": registration["registration_sha256"],
        "real_event_count": real_event_count,
        "fixture_event_count": fixture_event_count,
        "metric_results": [],
        "effect_claim_allowed": False,
        "formal_ranking_allowed": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }


def build_copper_ranking_ab_research_case() -> dict[str, Any]:
    adjustment_case = build_copper_adjustment_research_case()
    adjustment = adjustment_case["fresh"]
    base = build_base_ranking_snapshot(
        entity_scope="sector",
        as_of_date="2026-07-20",
        effective_from="2026-07-20",
        pit_status="fixture_verified",
        source_id="copper_ranking_research_fixture",
        rows=[
            {"entity_id": "sw_copper_processing", "base_rank": 1, "base_value": 90.4},
            {"entity_id": "sw_nonferrous_copper", "base_rank": 2, "base_value": 90.0},
            {"entity_id": "sw_electrical_cable", "base_rank": 3, "base_value": 89.9},
            {"entity_id": "sw_integrated_copper_chain", "base_rank": 4, "base_value": 80.0},
        ],
    )
    manifest = build_event_adjustment_manifest(adjustment)
    ab = build_event_adjustment_ranking_ab_shadow(base, adjustment, manifest)
    return {
        "schema_version": "copper-event-ranking-ab-research-fixture-v1",
        "mode": MODE,
        "status": "fixture_contract_only",
        "research_only": True,
        "base_snapshot": base,
        "adjustment": adjustment,
        "adjustment_manifest": manifest,
        "ab_shadow": ab,
        "metric_preregistration": build_event_ab_metric_preregistration(),
        "evaluation_contract": build_event_ab_evaluation_contract(real_event_count=0, fixture_event_count=1),
        "effect_claim_allowed": False,
        "formal_ranking_allowed": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }


__all__ = [
    "build_base_ranking_snapshot",
    "build_copper_ranking_ab_research_case",
    "build_event_ab_evaluation_contract",
    "build_event_ab_metric_preregistration",
    "build_event_adjustment_manifest",
    "build_event_adjustment_ranking_ab_shadow",
    "validate_base_ranking_snapshot",
    "validate_event_adjustment_manifest",
    "validate_event_adjustment_ranking_ab_shadow",
]
