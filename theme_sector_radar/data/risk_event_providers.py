"""Provider adapters into the canonical risk-event schema."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .official_announcements import RAW_DOCUMENT_SCHEMA_VERSION, default_source_registry
from .risk_event_schema import (
    build_risk_event,
    normalize_evidence_refs,
    reject_forbidden_fields,
)


LLM_SHADOW_SCHEMA_VERSION = "risk-event-llm-shadow-v1"


def normalize_official_announcement(
    manifest: Mapping[str, Any],
    *,
    event_type: str,
    scope: str,
    entity_id: str,
    severity: str,
    as_of_date: str,
    title: str,
) -> dict[str, Any]:
    if manifest.get("schema_version") != RAW_DOCUMENT_SCHEMA_VERSION:
        raise ValueError("official announcement manifest schema mismatch")
    digest = str(manifest.get("raw_sha256") or "")
    if not manifest.get("document_id") or len(digest) != 64:
        raise ValueError("official announcement evidence identity is incomplete")
    source_id = str(manifest.get("source_id") or "")
    authority_tiers = {
        str(source["source_id"]): str(source["authority_tier"])
        for source in default_source_registry()["sources"]
    }
    if source_id not in authority_tiers:
        raise ValueError("official announcement manifest source is not registered")
    return build_risk_event(
        event_type=event_type,
        scope=scope,
        entity_id=entity_id,
        event_time=manifest.get("published_at"),
        published_at=manifest.get("published_at"),
        effective_from=manifest.get("effective_from"),
        as_of_date=as_of_date,
        observed_at=manifest.get("captured_at"),
        severity=severity,
        status="observed",
        source={
            "source_id": source_id,
            "authority_tier": authority_tiers[source_id],
            "source_kind": "official_announcement",
        },
        evidence_refs=[
            {
                "evidence_id": manifest["document_id"],
                "sha256": digest,
                "kind": "raw_official_announcement",
                "source_id": manifest.get("source_id"),
            }
        ],
        detector=None,
        provider={
            "provider_id": source_id,
            "provider_version": str(manifest.get("source_version") or "unknown"),
        },
        structured_fields={"title": title},
        provenance={"method": "official_announcement_normalization"},
        revision_of=manifest.get("revision_of"),
    )


def llm_extraction_shadow(
    *, evidence_refs: Sequence[Mapping[str, Any]] = (), enabled: bool = False
) -> dict[str, Any]:
    if enabled:
        raise RuntimeError("LLM risk event extraction is reserved and disabled")
    result = {
        "schema_version": LLM_SHADOW_SCHEMA_VERSION,
        "mode": "paper_shadow_research_only",
        "enabled": False,
        "status": "reserved_not_run",
        "candidates": [],
        "evidence_refs": normalize_evidence_refs(evidence_refs),
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": "Research evidence only; no scores, orders, broker connection, or live execution.",
    }
    reject_forbidden_fields(result)
    return result
