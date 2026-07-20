"""Paper-only aggregation and human-review alert payloads."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from theme_sector_radar.reporting.paper_only_contract import validate_no_executable_instructions
from .official_announcements import DISCLAIMER, MODE
from .risk_event_ledger import build_unified_event_ledger
from .risk_event_schema import (
    SEVERITY_ORDER,
    canonical_date,
    canonical_json_bytes,
    canonical_sha256,
    reject_forbidden_fields,
    validate_risk_event,
)


RISK_REPORT_SCHEMA_VERSION = "unified-risk-monitor-report-v1"


def aggregate_risk_events(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    validated = [validate_risk_event(event) for event in events]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for event in validated:
        grouped.setdefault((event["scope"], event["entity_id"]), []).append(event)
    result: dict[str, list[dict[str, Any]]] = {
        "individual": [],
        "sector": [],
        "market": [],
    }
    for (scope, entity_id), members in sorted(grouped.items()):
        result[scope].append(
            {
                "scope": scope,
                "entity_id": entity_id,
                "event_count": len(members),
                "event_types": sorted({event["event_type"] for event in members}),
                "max_severity": max(
                    (event["severity"] for event in members),
                    key=lambda value: SEVERITY_ORDER[value],
                ),
                "evidence_status": "complete"
                if all(event["evidence_refs"] for event in members)
                else "incomplete",
                "requires_human_review": True,
            }
        )
    return result


def build_risk_monitor_report(
    events: Iterable[Mapping[str, Any]],
    *,
    as_of_date: str,
    source_health: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    report_date = canonical_date(as_of_date, field="as_of_date")
    ledger = build_unified_event_ledger(events)
    accepted = ledger["events"]
    alerts = []
    for event in accepted:
        if (
            event["severity"] not in {"elevated", "high", "critical"}
            and event["status"] not in {"blocked", "unknown", "conflict"}
        ):
            continue
        alerts.append(
            {
                "alert_id": "alert_" + canonical_sha256(event)[:24],
                "event_id": event["event_id"],
                "event_type": event["event_type"],
                "scope": event["scope"],
                "entity_id": event["entity_id"],
                "severity": event["severity"],
                "status": event["status"],
                "effective_from": event["effective_from"],
                "evidence_refs": event["evidence_refs"],
                "requires_human_review": True,
                "message_code": "risk_fact_review_required",
            }
        )
    report = {
        "schema_version": RISK_REPORT_SCHEMA_VERSION,
        "mode": MODE,
        "status": "ok",
        "as_of_date": report_date,
        "events": accepted,
        "ledger_summary": {
            "duplicate_count": ledger["duplicate_count"],
            "revision_count": ledger["revision_count"],
            "conflict_count": ledger["conflict_count"],
        },
        "aggregation": aggregate_risk_events(accepted),
        "source_health": dict(source_health) if source_health is not None else None,
        "alerts": alerts,
        "reminder_payload": {
            "delivery_status": "paper_shadow_only",
            "requires_human_review": True,
            "alerts": alerts,
        },
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    reject_forbidden_fields(report)
    validate_no_executable_instructions(report, context="unified risk monitoring")
    canonical_json_bytes(report)
    return report

