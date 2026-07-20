"""Independent policy and macro event providers and fixture evidence adapter."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from .official_announcements import (
    archive_raw_announcement,
    default_source_registry,
    infer_effective_from,
    validate_source_registry,
)
from .risk_event_schema import build_risk_event


PROVIDER_CONTRACT_VERSION = "policy-macro-provider-v1"
FIXTURE_SOURCE_ID = "policy_macro_offline_fixture"
_REAL_SOURCE_IDS = {
    "csrc_notices",
    "mof_notices",
    "sta_notices",
    "ndrc_notices",
    "miit_notices",
}


class PolicyMacroProvider(Protocol):
    provider_id: str
    provider_version: str

    def fetch(self, *, as_of_date: str) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class BlockedPolicyMacroProvider:
    provider_id: str
    provider_version: str = PROVIDER_CONTRACT_VERSION

    def fetch(self, *, as_of_date: str) -> Mapping[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "as_of_date": as_of_date,
            "status": "blocked",
            "records": [],
            "reason": "network, terms, cadence, cost, or credentials not verified",
            "event_state": "unknown_not_no_event",
        }


@dataclass(frozen=True)
class OfflinePolicyMacroProvider:
    records: Sequence[Mapping[str, Any]]
    provider_id: str = FIXTURE_SOURCE_ID
    provider_version: str = PROVIDER_CONTRACT_VERSION

    def fetch(self, *, as_of_date: str) -> Mapping[str, Any]:
        selected = [dict(record) for record in self.records if record.get("as_of_date") == as_of_date]
        return {
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "as_of_date": as_of_date,
            "status": "fixture",
            "records": selected,
            "event_state": "observed" if selected else "unknown_not_no_event",
        }


def _fixture_source_entry() -> dict[str, Any]:
    return {
        "source_id": FIXTURE_SOURCE_ID,
        "display_name": "Policy and macro offline fixture",
        "authority_tier": "research_only",
        "source_kind": "policy_macro_fixture",
        "official_url": None,
        "historical_coverage": {"status": "fixture_only", "start": None, "end": None},
        "time_precision": {"status": "fixture_declared", "supported": ["timestamp", "date_only"]},
        "source_version": "fixture-v1",
        "original_content": {"status": "fixture_only", "policy": "not_real_world_evidence"},
        "sha256": {"status": "computed_per_document", "algorithm": "sha256"},
        "retrieval_frequency": {"status": "not_applicable", "value": None},
        "cost": {"status": "not_applicable", "value": None},
        "availability_status": "available_offline_fixture",
        "adapter_status": "fixture",
        "requires_credentials": False,
        "notes": "Contract fixture only; never factual production evidence.",
    }


def policy_macro_source_registry() -> dict[str, Any]:
    base = default_source_registry()
    sources = [
        dict(source)
        for source in base["sources"]
        if source["source_id"] in _REAL_SOURCE_IDS
    ]
    sources.append(_fixture_source_entry())
    registry = {
        **base,
        "registry_version": "policy-macro-registry-2026-07-20-v1",
        "sources": sources,
    }
    validate_source_registry(registry)
    return registry


def provider_registry() -> dict[str, Any]:
    registry = policy_macro_source_registry()
    return {
        "schema_version": PROVIDER_CONTRACT_VERSION,
        "mode": registry["mode"],
        "status": "ok",
        "providers": [
            {
                "provider_id": source["source_id"],
                "provider_version": PROVIDER_CONTRACT_VERSION,
                "adapter_status": source["adapter_status"],
                "event_state": "unknown_not_no_event",
            }
            for source in registry["sources"]
        ],
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": registry["disclaimer"],
    }


def archive_policy_macro_fixture(
    archive_root: Path | str,
    *,
    source_url_or_path: str,
    published_at: Any,
    captured_at: Any,
    raw_content: bytes | str,
    effective_from: str | None = None,
    document_version: str = "v1",
    revision_of: str | None = None,
) -> dict[str, Any]:
    return archive_raw_announcement(
        archive_root,
        source_id=FIXTURE_SOURCE_ID,
        source_url_or_path=source_url_or_path,
        published_at=published_at,
        captured_at=captured_at,
        raw_content=raw_content,
        effective_from=effective_from,
        document_version=document_version,
        revision_of=revision_of,
        registry=policy_macro_source_registry(),
    )


def normalize_policy_macro_event(
    manifest: Mapping[str, Any],
    *,
    event_type: str,
    scope: str,
    entity_id: str,
    severity: str,
    as_of_date: str,
    title: str,
    impact_scope: Sequence[str] = (),
) -> dict[str, Any]:
    source_id = str(manifest.get("source_id") or "")
    if source_id not in _REAL_SOURCE_IDS | {FIXTURE_SOURCE_ID}:
        raise ValueError("policy/macro manifest source is not registered")
    digest = str(manifest.get("raw_sha256") or "")
    if not manifest.get("document_id") or len(digest) != 64:
        raise ValueError("policy/macro manifest evidence identity is incomplete")
    published_at = manifest.get("published_at")
    effective = manifest.get("effective_from")
    if effective is None and published_at is not None:
        effective = infer_effective_from(published_at)["effective_from"]
    return build_risk_event(
        event_type=event_type,
        scope=scope,
        entity_id=entity_id,
        event_time=published_at,
        published_at=published_at,
        effective_from=effective,
        as_of_date=as_of_date,
        observed_at=manifest.get("captured_at"),
        severity=severity,
        status="observed",
        source={
            "source_id": source_id,
            "authority_tier": "research_only"
            if source_id == FIXTURE_SOURCE_ID
            else "primary",
            "source_kind": "policy_macro",
        },
        evidence_refs=[
            {
                "evidence_id": manifest["document_id"],
                "sha256": digest,
                "kind": "raw_policy_macro_document",
                "source_id": source_id,
            }
        ],
        detector=None,
        provider={
            "provider_id": source_id,
            "provider_version": PROVIDER_CONTRACT_VERSION,
        },
        structured_fields={
            "title": title,
            "impact_scope": sorted({str(value) for value in impact_scope}),
        },
        provenance={"method": "policy_macro_provider_normalization"},
        revision_of=manifest.get("revision_of"),
    )


def normalize_provider_result(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    if result.get("event_state") == "no_event":
        raise ValueError("policy/macro provider cannot claim no_event")
    status = str(result.get("status") or "")
    if status == "blocked":
        return [
            build_risk_event(
                event_type="policy_macro_provider_status",
                scope="market",
                entity_id="market",
                event_time=None,
                published_at=None,
                effective_from=None,
                as_of_date=str(result.get("as_of_date") or "1970-01-01"),
                observed_at=None,
                severity="unknown",
                status="blocked",
                source={
                    "source_id": str(result.get("provider_id") or "unknown"),
                    "authority_tier": "primary",
                    "source_kind": "policy_macro",
                },
                evidence_refs=[],
                detector=None,
                provider={
                    "provider_id": str(result.get("provider_id") or "unknown"),
                    "provider_version": str(result.get("provider_version") or "unknown"),
                },
                structured_fields={"reason": str(result.get("reason") or "provider_blocked")},
                provenance={"method": "blocked_policy_macro_provider"},
            )
        ]
    return []

