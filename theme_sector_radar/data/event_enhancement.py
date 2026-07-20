"""Versioned, paper-only structural projections over validated risk events.

This module deliberately describes evidence and exposure. It never calculates a score,
rank, selection adjustment, or trading instruction.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import validate_no_executable_instructions

from .event_impact_shadow import build_copper_increase_research_case
from .official_announcements import DISCLAIMER, MODE
from .risk_event_schema import (
    build_risk_event,
    canonical_date,
    canonical_json_bytes,
    canonical_sha256,
    normalize_evidence_refs,
    reject_forbidden_fields,
    validate_risk_event,
)


EVENT_ENHANCEMENT_SCHEMA_VERSION = "event-enhancement-v1"
EXPOSURE_MAPPING_SCHEMA_VERSION = "event-exposure-mapping-shadow-v1"
ENHANCEMENT_VIEW_VERSION = "event-enhancement-views-v1"
IMPACT_DIRECTIONS = {"positive", "negative", "mixed", "unknown"}
VALUE_CHAIN_STAGES = {"upstream", "midstream", "downstream", "mixed", "unknown"}
DURATION_TYPES = {"one_off", "temporary", "ongoing", "unknown"}
NOVELTY_STATUSES = {"novel", "repeat", "revised", "duplicate", "unknown"}
MAPPING_QUALITIES = {"exact", "partial", "unmapped", "conflict", "unknown"}
FEEDBACK_STATUSES = {"observed", "unknown", "not_available", "reserved_not_run"}
EXPOSURE_SCOPES = {"individual", "sector", "market"}
EXPOSURE_TYPES = {"direct", "indirect", "value_chain", "unknown"}
PROTECTED_FIELDS = {
    "event_score", "quant_score", "final_score", "v2_score", "selection_score",
    "confidence", "rank", "action", "trade", "order", "position", "price",
}


def _reject_protected(value: Any, *, path: str = "event_enhancement") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).casefold()
            if normalized in PROTECTED_FIELDS or normalized.endswith("_score"):
                raise ValueError(f"event enhancement contains protected field: {path}.{key}")
            _reject_protected(child, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_protected(child, path=f"{path}[{index}]")


def _evidence_keys(refs: Sequence[Mapping[str, Any]]) -> set[tuple[str, str]]:
    return {(str(ref["evidence_id"]), str(ref["sha256"])) for ref in refs}


def _event_evidence(
    event: Mapping[str, Any], evidence_refs: Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    event_refs = normalize_evidence_refs(event.get("evidence_refs") or [])
    refs = normalize_evidence_refs(evidence_refs) if evidence_refs is not None else event_refs
    if not _evidence_keys(refs).issubset(_evidence_keys(event_refs)):
        raise ValueError("enhancement evidence refs must be bound to the validated event")
    return refs


def _fact_view(facts: Mapping[str, Any] | None) -> dict[str, Any]:
    facts = dict(facts or {})
    _reject_protected(facts, path="fact_view")
    direction = str(facts.get("impact_direction") or "unknown")
    stage = str(facts.get("value_chain_stage") or "unknown")
    if direction not in IMPACT_DIRECTIONS:
        raise ValueError("enhancement impact_direction is invalid")
    if stage not in VALUE_CHAIN_STAGES:
        raise ValueError("enhancement value_chain_stage is invalid")
    scope = facts.get("impact_scope")
    if isinstance(scope, str):
        scope = [scope]
    if not isinstance(scope, list):
        scope = ["unknown"]
    return {
        "impact_direction": direction,
        "value_chain_stage": stage,
        "transmission_channel": str(facts.get("transmission_channel") or "unknown"),
        "impact_scope": sorted({str(value) for value in scope}) or ["unknown"],
        "mapping_basis": str(facts.get("mapping_basis") or "unconfirmed"),
    }


def _lifecycle_view(event: Mapping[str, Any], lifecycle: Mapping[str, Any] | None) -> dict[str, Any]:
    lifecycle = dict(lifecycle or {})
    _reject_protected(lifecycle, path="lifecycle_view")
    duration = str(lifecycle.get("duration_type") or "unknown")
    if duration not in DURATION_TYPES:
        raise ValueError("enhancement duration_type is invalid")
    effective_until = lifecycle.get("effective_until")
    if effective_until is not None:
        effective_until = canonical_date(effective_until, field="effective_until")
    novelty = dict(lifecycle.get("novelty") or {})
    novelty_status = str(novelty.get("status") or "unknown")
    if novelty_status not in NOVELTY_STATUSES:
        raise ValueError("enhancement novelty status is invalid")
    duplicate_of = novelty.get("duplicate_of")
    revision_of = novelty.get("revision_of") or event.get("revision_of")
    decay = dict(lifecycle.get("decay_metadata") or {})
    _reject_protected(decay, path="lifecycle.decay_metadata")
    canonical_json_bytes(decay)
    return {
        "duration_type": duration,
        "effective_until": effective_until,
        "expiry_metadata": {
            "status": "declared" if effective_until else "unknown",
            "effective_until": effective_until,
        },
        "decay_metadata": decay,
        "novelty": {
            "status": novelty_status,
            "revision_of": revision_of,
            "duplicate_of": duplicate_of,
        },
    }


def _evidence_view(
    event: Mapping[str, Any], refs: Sequence[Mapping[str, Any]], evidence: Mapping[str, Any] | None,
) -> dict[str, Any]:
    evidence = dict(evidence or {})
    _reject_protected(evidence, path="evidence_quality_view")
    mapping_quality = str(evidence.get("mapping_quality") or "unknown")
    if mapping_quality not in MAPPING_QUALITIES:
        raise ValueError("enhancement mapping_quality is invalid")
    authority = str(evidence.get("authority_tier") or event.get("source", {}).get("authority_tier") or "unknown")
    if authority not in {"primary", "secondary", "research_only", "unknown"}:
        raise ValueError("enhancement authority_tier is invalid")
    timestamp_quality = str(
        evidence.get("timestamp_quality")
        or event.get("published_time_precision")
        or "unknown"
    )
    if timestamp_quality not in {"timestamp", "timestamp_naive", "date_only", "unknown"}:
        raise ValueError("enhancement timestamp_quality is invalid")
    conflict_status = str(evidence.get("conflict_status") or ("conflict" if event["status"] == "conflict" else "clear"))
    if conflict_status not in {"clear", "conflict", "unknown"}:
        raise ValueError("enhancement conflict_status is invalid")
    manual_review = bool(evidence.get("manual_review_required", False))
    manual_review = manual_review or event["status"] != "observed" or mapping_quality != "exact"
    return {
        "authority_tier": authority,
        "evidence_completeness": "complete" if refs else "incomplete",
        "evidence_ref_count": len(refs),
        "timestamp_quality": timestamp_quality,
        "mapping_quality": mapping_quality,
        "conflict_status": conflict_status,
        "manual_review_required": manual_review,
    }


def _market_feedback(
    event: Mapping[str, Any], feedback: Mapping[str, Any] | None,
) -> dict[str, Any]:
    feedback = dict(feedback or {})
    _reject_protected(feedback, path="market_feedback")
    snapshot = dict(feedback.get("as_of_snapshot") or {})
    snapshot_date = str(snapshot.get("as_of_date") or event["as_of_date"])
    if canonical_date(snapshot_date, field="market_feedback.as_of_date") != event["as_of_date"]:
        raise ValueError("market feedback as_of_snapshot must match event as_of_date")
    snapshot_status = str(snapshot.get("status") or "unknown")
    if snapshot_status not in FEEDBACK_STATUSES:
        raise ValueError("market as_of_snapshot status is invalid")
    post = dict(feedback.get("post_event_backtest") or {})
    post_status = str(post.get("status") or "reserved_not_run")
    if post_status not in FEEDBACK_STATUSES:
        raise ValueError("market post_event_backtest status is invalid")
    evaluation_date = post.get("evaluation_as_of_date")
    if evaluation_date is not None:
        evaluation_date = canonical_date(evaluation_date, field="evaluation_as_of_date")
        event_day = str(event.get("event_time") or event["as_of_date"])[:10]
        if evaluation_date <= event_day:
            raise ValueError("post_event_backtest evaluation must be after event day")
    pre_reaction = dict(snapshot.get("pre_event_reaction") or {})
    post_reaction = dict(post.get("post_event_reaction") or {})
    breadth = dict(post.get("breadth_propagation") or {})
    canonical_json_bytes({"pre": pre_reaction, "post": post_reaction, "breadth": breadth})
    return {
        "as_of_snapshot": {
            "as_of_date": event["as_of_date"],
            "status": snapshot_status,
            "pre_event_reaction": pre_reaction,
        },
        "post_event_backtest": {
            "status": post_status,
            "evaluation_as_of_date": evaluation_date,
            "post_event_reaction": post_reaction,
            "breadth_propagation": breadth,
            "is_backtest": True,
        },
    }


def _llm_shadow(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {
            "schema_version": "risk-event-llm-shadow-v1",
            "enabled": False,
            "status": "reserved_not_run",
            "candidates": [],
            "evidence_locators": [],
        }
    shadow = dict(value)
    _reject_protected(shadow, path="llm_shadow")
    if shadow.get("enabled") is not False or shadow.get("status") != "reserved_not_run":
        raise ValueError("LLM enhancement shadow must remain disabled/reserved_not_run")
    candidates = shadow.get("candidates") or []
    if candidates:
        raise ValueError("reserved LLM enhancement shadow cannot emit candidates")
    return {
        "schema_version": "risk-event-llm-shadow-v1",
        "enabled": False,
        "status": "reserved_not_run",
        "candidates": [],
        "evidence_locators": list(shadow.get("evidence_locators") or []),
    }


def build_event_enhancement(
    event: Mapping[str, Any],
    *,
    evidence_refs: Sequence[Mapping[str, Any]] | None = None,
    fact_view: Mapping[str, Any] | None = None,
    lifecycle_view: Mapping[str, Any] | None = None,
    evidence_view: Mapping[str, Any] | None = None,
    market_feedback: Mapping[str, Any] | None = None,
    llm_shadow: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    validated = validate_risk_event(event)
    refs = _event_evidence(validated, evidence_refs)
    artifact = {
        "schema_version": EVENT_ENHANCEMENT_SCHEMA_VERSION,
        "view_schema_version": ENHANCEMENT_VIEW_VERSION,
        "mode": MODE,
        "artifact_type": "event_enhancement",
        "enhancement_id": "enh_" + canonical_sha256(
            {"event_id": validated["event_id"], "evidence_refs": refs}
        )[:32],
        "event_id": validated["event_id"],
        "event_schema_version": validated["schema_version"],
        "event_type": validated["event_type"],
        "event_status": validated["status"],
        "severity": validated["severity"],
        "scope": validated["scope"],
        "entity_id": validated["entity_id"],
        "event_time": validated["event_time"],
        "published_at": validated["published_at"],
        "effective_from": validated["effective_from"],
        "pit_status": validated["event_time_precision"],
        "source_id": str(validated["source"].get("source_id") or "unknown"),
        "logical_event_id": "logical_" + canonical_sha256(
            {
                "event_type": validated["event_type"],
                "scope": validated["scope"],
                "entity_id": validated["entity_id"],
                "event_time": validated["event_time"],
                "published_at": validated["published_at"],
                "source_id": validated["source"].get("source_id"),
            }
        )[:32],
        "as_of_date": validated["as_of_date"],
        "evidence_refs": refs,
        "fact_view": _fact_view(fact_view),
        "lifecycle_view": _lifecycle_view(validated, lifecycle_view),
        "evidence_quality_view": _evidence_view(validated, refs, evidence_view),
        "market_feedback_view": _market_feedback(validated, market_feedback),
        "llm_shadow": _llm_shadow(llm_shadow),
        "manual_review_required": True,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    return validate_event_enhancement(artifact)


def validate_event_enhancement(artifact: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version", "view_schema_version", "enhancement_id", "event_id",
        "event_schema_version", "event_status", "severity", "event_time",
        "published_at", "effective_from", "pit_status", "source_id",
        "logical_event_id", "as_of_date",
        "evidence_refs", "fact_view",
        "lifecycle_view", "evidence_quality_view", "market_feedback_view",
        "llm_shadow",
    }
    missing = sorted(required - set(artifact))
    if missing:
        raise ValueError(f"event enhancement missing fields: {missing}")
    if artifact.get("schema_version") != EVENT_ENHANCEMENT_SCHEMA_VERSION:
        raise ValueError("event enhancement schema mismatch")
    if artifact.get("view_schema_version") != ENHANCEMENT_VIEW_VERSION or artifact.get("mode") != MODE:
        raise ValueError("event enhancement view or mode mismatch")
    if artifact.get("event_status") not in {"observed", "blocked", "unknown", "conflict", "reserved_not_run"}:
        raise ValueError("event enhancement event status is invalid")
    if artifact.get("severity") not in {"unknown", "info", "watch", "elevated", "high", "critical"}:
        raise ValueError("event enhancement severity is invalid")
    if artifact.get("pit_status") not in {"timestamp", "timestamp_naive", "date_only", "unknown"}:
        raise ValueError("event enhancement PIT status is invalid")
    if not artifact.get("logical_event_id") or not artifact.get("source_id"):
        raise ValueError("event enhancement logical source identity is missing")
    canonical_date(artifact.get("as_of_date"), field="as_of_date")
    refs = normalize_evidence_refs(artifact.get("evidence_refs") or [])
    fact = artifact.get("fact_view")
    if not isinstance(fact, Mapping) or fact.get("impact_direction") not in IMPACT_DIRECTIONS:
        raise ValueError("event enhancement fact view is invalid")
    if fact.get("value_chain_stage") not in VALUE_CHAIN_STAGES:
        raise ValueError("event enhancement value-chain stage is invalid")
    lifecycle = artifact.get("lifecycle_view")
    if not isinstance(lifecycle, Mapping) or lifecycle.get("duration_type") not in DURATION_TYPES:
        raise ValueError("event enhancement lifecycle view is invalid")
    quality = artifact.get("evidence_quality_view")
    if not isinstance(quality, Mapping) or quality.get("mapping_quality") not in MAPPING_QUALITIES:
        raise ValueError("event enhancement evidence quality view is invalid")
    expected_completeness = "complete" if refs else "incomplete"
    if quality.get("evidence_completeness") != expected_completeness or quality.get("evidence_ref_count") != len(refs):
        raise ValueError("event enhancement evidence completeness mismatch")
    feedback = artifact.get("market_feedback_view")
    if not isinstance(feedback, Mapping) or "as_of_snapshot" not in feedback or "post_event_backtest" not in feedback:
        raise ValueError("event enhancement market feedback separation is missing")
    shadow = artifact.get("llm_shadow")
    if not isinstance(shadow, Mapping) or shadow.get("enabled") is not False or shadow.get("status") != "reserved_not_run":
        raise ValueError("event enhancement LLM shadow is not disabled")
    if any(artifact.get(key) is not False for key in ("eligible_for_oos_claim", "promotion_allowed", "live_trading_allowed")):
        raise ValueError("event enhancement safety flags must be false")
    _reject_protected(artifact)
    reject_forbidden_fields(artifact)
    validate_no_executable_instructions(dict(artifact), context="event enhancement")
    canonical_json_bytes(dict(artifact))
    return dict(artifact)


def build_event_exposure_mapping(
    enhancement: Mapping[str, Any],
    mappings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    checked = validate_event_enhancement(enhancement)
    source_refs = _evidence_keys(checked["evidence_refs"])
    exposures: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []
    for index, raw in enumerate(mappings):
        _reject_protected(raw, path=f"exposure_mapping[{index}]")
        scope = str(raw.get("entity_scope") or "")
        entity_id = str(raw.get("entity_id") or "")
        stage = str(raw.get("value_chain_stage") or "unknown")
        direction = str(raw.get("impact_direction") or "unknown")
        exposure_type = str(raw.get("exposure_type") or "unknown")
        quality = str(raw.get("mapping_quality") or "unknown")
        try:
            refs = normalize_evidence_refs(raw.get("evidence_refs") or checked["evidence_refs"])
        except ValueError:
            refs = []
        missing = []
        if scope not in EXPOSURE_SCOPES:
            missing.append("entity_scope")
        if not entity_id:
            missing.append("entity_id")
        if stage not in VALUE_CHAIN_STAGES:
            missing.append("value_chain_stage")
        if direction not in IMPACT_DIRECTIONS:
            missing.append("impact_direction")
        if exposure_type not in EXPOSURE_TYPES:
            missing.append("exposure_type")
        if quality not in MAPPING_QUALITIES:
            missing.append("mapping_quality")
        if not refs or not _evidence_keys(refs).issubset(source_refs):
            missing.append("evidence_refs_bound_to_event")
        if missing:
            unknown.append({"mapping_index": index, "status": "unknown", "missing_fields": sorted(set(missing))})
            continue
        valid_from = canonical_date(raw.get("valid_from") or checked["as_of_date"], field="valid_from")
        valid_until = canonical_date(raw["valid_until"], field="valid_until") if raw.get("valid_until") else None
        if valid_until is not None and valid_until < valid_from:
            raise ValueError("event exposure mapping validity range is inverted")
        exposures.append({
            "mapping_id": "map_" + hashlib.sha256(f"{checked['event_id']}:{index}".encode("ascii")).hexdigest()[:24],
            "entity_scope": scope,
            "entity_id": entity_id,
            "exposure_type": exposure_type,
            "value_chain_stage": stage,
            "impact_direction": direction,
            "transmission_channel": str(raw.get("transmission_channel") or "unknown"),
            "impact_scope": sorted({str(value) for value in (raw.get("impact_scope") or [scope])}),
            "mapping_quality": quality,
            "evidence_refs": refs,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "requires_human_review": True,
        })
    artifact = {
        "schema_version": EXPOSURE_MAPPING_SCHEMA_VERSION,
        "mode": MODE,
        "artifact_type": "event_exposure_mapping_shadow",
        "mapping_id": "exposure_" + canonical_sha256(
            {"enhancement_id": checked["enhancement_id"], "mappings": list(mappings)}
        )[:32],
        "enhancement_id": checked["enhancement_id"],
        "event_id": checked["event_id"],
        "as_of_date": checked["as_of_date"],
        "status": "observed" if exposures and not unknown else "partial_unknown" if exposures else "unknown",
        "exposures": exposures,
        "unknown_mappings": unknown,
        "manual_review_required": True,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    return validate_event_exposure_mapping(artifact)


def validate_event_exposure_mapping(artifact: Mapping[str, Any]) -> dict[str, Any]:
    if artifact.get("schema_version") != EXPOSURE_MAPPING_SCHEMA_VERSION or artifact.get("mode") != MODE:
        raise ValueError("event exposure mapping schema or mode mismatch")
    if artifact.get("status") not in {"observed", "partial_unknown", "unknown"}:
        raise ValueError("event exposure mapping status is invalid")
    if any(artifact.get(key) is not False for key in ("eligible_for_oos_claim", "promotion_allowed", "live_trading_allowed")):
        raise ValueError("event exposure mapping safety flags must be false")
    _reject_protected(artifact, path="event_exposure_mapping")
    validate_no_executable_instructions(dict(artifact), context="event exposure mapping")
    canonical_json_bytes(dict(artifact))
    return dict(artifact)


def build_copper_enhancement_research_case(
    *, as_of_date: str = "2026-07-20",
) -> dict[str, Any]:
    case = build_copper_increase_research_case()
    event = case["risk_event"]
    as_of = canonical_date(as_of_date, field="as_of_date")
    if as_of != event["as_of_date"]:
        event = build_risk_event(
            event_type=event["event_type"],
            scope=event["scope"],
            entity_id=event["entity_id"],
            event_time=event["event_time"],
            published_at=event["published_at"],
            effective_from=event["effective_from"],
            as_of_date=as_of,
            observed_at=event["observed_at"],
            severity=event["severity"],
            status=event["status"],
            source=event["source"],
            evidence_refs=event["evidence_refs"],
            detector=event["detector"],
            provider=event["provider"],
            structured_fields=event["structured_fields"],
            provenance=event["provenance"],
            revision_of=event["revision_of"],
        )
    enhancement = build_event_enhancement(
        event,
        fact_view={
            "impact_direction": "mixed",
            "value_chain_stage": "mixed",
            "transmission_channel": "commodity_input_output_price",
            "impact_scope": ["upstream", "downstream"],
            "mapping_basis": "research_fixture_only",
        },
        lifecycle_view={
            "duration_type": "temporary",
            "effective_until": "2026-08-19",
            "decay_metadata": {"method": "metadata_only", "half_life_days": 15},
            "novelty": {"status": "novel"},
        },
        evidence_view={"mapping_quality": "partial", "manual_review_required": True},
        market_feedback={
            "as_of_snapshot": {
                "as_of_date": as_of,
                "status": "observed",
                "pre_event_reaction": {
                    "reflection_status": "unreflected",
                    "observation_basis": "research_fixture_only",
                },
            }
        },
    )
    mapping = build_event_exposure_mapping(
        enhancement,
        [
            {
                "entity_scope": "sector",
                "entity_id": "sw_nonferrous_copper",
                "exposure_type": "value_chain",
                "value_chain_stage": "upstream",
                "impact_direction": "positive",
                "transmission_channel": "output_price",
                "impact_scope": ["sector"],
                "mapping_quality": "partial",
                "valid_from": "2026-07-20",
                "valid_until": "2026-08-19",
            },
            {
                "entity_scope": "sector",
                "entity_id": "sw_electrical_cable",
                "exposure_type": "indirect",
                "value_chain_stage": "downstream",
                "impact_direction": "negative",
                "transmission_channel": "input_cost",
                "impact_scope": ["sector"],
                "mapping_quality": "partial",
                "valid_from": "2026-07-20",
                "valid_until": "2026-08-19",
            },
            {
                "entity_scope": "sector",
                "entity_id": "sw_copper_processing",
                "exposure_type": "indirect",
                "value_chain_stage": "midstream",
                "impact_direction": "unknown",
                "transmission_channel": "processing_margin_unknown",
                "impact_scope": ["sector"],
                "mapping_quality": "unknown",
                "valid_from": "2026-07-20",
                "valid_until": "2026-08-19",
            },
            {
                "entity_scope": "sector",
                "entity_id": "sw_integrated_copper_chain",
                "exposure_type": "value_chain",
                "value_chain_stage": "mixed",
                "impact_direction": "mixed",
                "transmission_channel": "output_price_and_input_cost",
                "impact_scope": ["upstream", "downstream"],
                "mapping_quality": "partial",
                "valid_from": "2026-07-20",
                "valid_until": "2026-08-19",
            },
        ],
    )
    return {
        "schema_version": "event-enhancement-copper-fixture-v1",
        "mode": MODE,
        "status": "fixture_complete",
        "research_only": True,
        "event_enhancement": enhancement,
        "event_exposure_mapping": mapping,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }


__all__ = [
    "EVENT_ENHANCEMENT_SCHEMA_VERSION",
    "EXPOSURE_MAPPING_SCHEMA_VERSION",
    "build_copper_enhancement_research_case",
    "build_event_enhancement",
    "build_event_exposure_mapping",
    "validate_event_enhancement",
    "validate_event_exposure_mapping",
]
