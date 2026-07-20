"""Facade for the unified paper-only risk event data layer."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .market_anomalies import MarketAnomalyThresholds, detect_market_anomalies
from .policy_macro_events import (
    BlockedPolicyMacroProvider,
    OfflinePolicyMacroProvider,
    PolicyMacroProvider,
    archive_policy_macro_fixture,
    normalize_policy_macro_event,
    normalize_provider_result,
    policy_macro_source_registry,
    provider_registry,
)
from .risk_event_ledger import build_unified_event_ledger, fuse_risk_events
from .risk_event_providers import llm_extraction_shadow, normalize_official_announcement
from .risk_event_schema import (
    RISK_EVENT_SCHEMA_VERSION,
    build_risk_event,
    normalize_evidence_refs,
    validate_risk_event,
)
from .risk_monitoring import aggregate_risk_events, build_risk_monitor_report


def normalize_risk_event(
    source_type: str, payload: Mapping[str, Any], **kwargs: Any
) -> Any:
    """Normalize one provider type through a single explicit facade."""

    if source_type == "official_announcement":
        return normalize_official_announcement(payload, **kwargs)
    if source_type == "policy_macro":
        return normalize_policy_macro_event(payload, **kwargs)
    if source_type == "market_anomaly":
        return detect_market_anomalies(payload, **kwargs)
    raise ValueError(f"unsupported risk event source_type: {source_type}")


def adapt_policy_macro_fixture(
    records: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Adapt offline policy/macro fixture rows into canonical risk events.

    Fixture rows are research evidence, never production facts. Incomplete rows emit a
    blocked event so fixture or mapping failures cannot be mistaken for ``no_event``.
    """

    if not records:
        raise ValueError("empty policy/macro fixture cannot establish no_event")
    output: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ValueError("policy/macro fixture row must be an object")
        as_of_date = str(record.get("as_of_date") or "")
        if not as_of_date:
            raise ValueError("policy/macro fixture row requires as_of_date")
        source_id = str(record.get("source_id") or "policy_macro_offline_fixture")
        required = {
            "event_type": record.get("event_type"),
            "scope": record.get("scope") or "market",
            "entity_id": record.get("entity_id") or "market",
            "severity": record.get("severity"),
            "title": record.get("title"),
        }
        try:
            references = normalize_evidence_refs(record.get("evidence_refs") or [])
        except ValueError:
            references = []
        missing = sorted(
            [key for key, value in required.items() if not value]
            + ([] if references else ["evidence_refs"])
        )
        if source_id != "policy_macro_offline_fixture":
            missing.append("registered_fixture_source")
        if missing:
            event = build_risk_event(
                event_type="policy_macro_fixture_status",
                scope=str(required["scope"]),
                entity_id=str(required["entity_id"]),
                event_time=record.get("published_at"),
                published_at=record.get("published_at"),
                effective_from=record.get("effective_from"),
                as_of_date=as_of_date,
                observed_at=record.get("observed_at"),
                severity="unknown",
                status="blocked",
                source={
                    "source_id": "policy_macro_offline_fixture",
                    "authority_tier": "research_only",
                    "source_kind": "policy_macro_fixture",
                },
                evidence_refs=references,
                detector=None,
                provider={
                    "provider_id": "policy_macro_offline_fixture",
                    "provider_version": "policy-macro-provider-v1",
                },
                structured_fields={
                    "reason": "incomplete_or_untrusted_policy_macro_fixture",
                    "missing_fields": sorted(set(missing)),
                    "fixture_row": index,
                },
                provenance={"method": "policy_macro_fixture_adapter_blocked"},
            )
        else:
            event = build_risk_event(
                event_type=str(required["event_type"]),
                scope=str(required["scope"]),
                entity_id=str(required["entity_id"]),
                event_time=record.get("event_time") or record.get("published_at"),
                published_at=record.get("published_at"),
                effective_from=record.get("effective_from"),
                as_of_date=as_of_date,
                observed_at=record.get("observed_at"),
                severity=str(required["severity"]),
                status="observed",
                source={
                    "source_id": source_id,
                    "authority_tier": "research_only",
                    "source_kind": "policy_macro_fixture",
                },
                evidence_refs=references,
                detector=None,
                provider={
                    "provider_id": source_id,
                    "provider_version": "policy-macro-provider-v1",
                },
                structured_fields={
                    "title": str(required["title"]),
                    "impact_scope": sorted(
                        {str(value) for value in record.get("impact_scope") or []}
                    ),
                },
                provenance={"method": "policy_macro_fixture_adapter"},
                revision_of=record.get("revision_of"),
                event_id=record.get("event_id"),
            )
        output.append(validate_risk_event(event))
    return output


def validate_unified_risk_event(event: Mapping[str, Any]) -> dict[str, Any]:
    return validate_risk_event(event)


extract_llm_shadow = llm_extraction_shadow


__all__ = [
    "BlockedPolicyMacroProvider",
    "MarketAnomalyThresholds",
    "OfflinePolicyMacroProvider",
    "PolicyMacroProvider",
    "RISK_EVENT_SCHEMA_VERSION",
    "adapt_policy_macro_fixture",
    "aggregate_risk_events",
    "archive_policy_macro_fixture",
    "build_risk_event",
    "build_risk_monitor_report",
    "build_unified_event_ledger",
    "detect_market_anomalies",
    "extract_llm_shadow",
    "fuse_risk_events",
    "normalize_official_announcement",
    "normalize_policy_macro_event",
    "normalize_provider_result",
    "normalize_risk_event",
    "policy_macro_source_registry",
    "provider_registry",
    "validate_risk_event",
    "validate_unified_risk_event",
]
