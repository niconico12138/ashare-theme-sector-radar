"""Unified immutable-style in-memory ledger for canonical risk events."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from theme_sector_radar.reporting.paper_only_contract import validate_no_executable_instructions
from .official_announcements import DISCLAIMER, MODE
from .risk_event_schema import (
    SEVERITY_ORDER,
    canonical_json_bytes,
    canonical_sha256,
    normalize_evidence_refs,
    reject_forbidden_fields,
    validate_risk_event,
)


RISK_LEDGER_SCHEMA_VERSION = "unified-risk-event-ledger-v1"


def build_unified_event_ledger(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    validated = [validate_risk_event(event) for event in events]
    accepted: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    revisions: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    exact: dict[str, dict[str, Any]] = {}
    logical: dict[str, dict[str, Any]] = {}
    known_ids: set[str] = set()
    for raw in validated:
        event = dict(raw)
        if event["event_id"] in known_ids:
            raise ValueError("risk event ledger contains duplicate event_id")
        known_ids.add(event["event_id"])
        exact_key = canonical_sha256(
            {key: value for key, value in event.items() if key != "event_id"}
        )
        if exact_key in exact:
            duplicates.append(
                {
                    "event_id": event["event_id"],
                    "duplicate_of": exact[exact_key]["event_id"],
                }
            )
            continue
        logical_key = canonical_sha256(
            {
                "event_type": event["event_type"],
                "scope": event["scope"],
                "entity_id": event["entity_id"],
                "event_time": event["event_time"],
                "published_at": event["published_at"],
                "effective_from": event["effective_from"],
                "source_id": event["source"].get("source_id"),
            }
        )
        prior = logical.get(logical_key)
        if prior is not None:
            if event.get("revision_of") == prior["event_id"]:
                revisions.append(
                    {"event_id": event["event_id"], "revision_of": prior["event_id"]}
                )
            else:
                event["status"] = "conflict"
                event["conflict_with"] = prior["event_id"]
                conflicts.append(
                    {
                        "event_id": event["event_id"],
                        "conflict_with": prior["event_id"],
                    }
                )
        event["evidence_refs"] = normalize_evidence_refs(event["evidence_refs"])
        event["evidence_completeness"] = (
            "complete" if event["evidence_refs"] else "incomplete"
        )
        exact[exact_key] = event
        logical[logical_key] = event
        accepted.append(event)
    ledger = {
        "schema_version": RISK_LEDGER_SCHEMA_VERSION,
        "mode": MODE,
        "status": "conflicts_present" if conflicts else "ok",
        "events": accepted,
        "duplicates": duplicates,
        "revisions": revisions,
        "conflicts": conflicts,
        "event_count": len(accepted),
        "duplicate_count": len(duplicates),
        "revision_count": len(revisions),
        "conflict_count": len(conflicts),
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    reject_forbidden_fields(ledger)
    validate_no_executable_instructions(ledger, context="unified risk event ledger")
    canonical_json_bytes(ledger)
    return ledger


def fuse_risk_events(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Compatibility name for the canonical ledger entry point."""

    return build_unified_event_ledger(events)

