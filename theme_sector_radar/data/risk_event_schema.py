"""Canonical schema and validation for paper-only risk events."""

from __future__ import annotations

from datetime import date, datetime
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import validate_no_executable_instructions
from .official_announcements import DISCLAIMER, MODE


RISK_EVENT_SCHEMA_VERSION = "canonical-risk-event-v1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
SEVERITIES = ("unknown", "info", "watch", "elevated", "high", "critical")
SEVERITY_ORDER = {value: index for index, value in enumerate(SEVERITIES)}
STATUSES = {"observed", "blocked", "unknown", "conflict", "reserved_not_run"}
SCOPES = {"individual", "sector", "market"}
DETECTION_MODES = {"deterministic", "statistical", "source", "llm_shadow"}
FORBIDDEN_KEYS = {
    "action", "confidence", "decision", "event_score", "final_score",
    "impact_score", "order", "position", "price", "rank", "score",
    "signal", "trade", "weight",
}
REQUIRED_FIELDS = {
    "event_id", "event_type", "scope", "entity_id", "event_time",
    "published_at", "effective_from", "as_of_date", "severity", "status",
    "source", "evidence_refs", "detector", "provider", "schema_version",
}


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def canonical_date(value: Any, *, field: str) -> str:
    text = str(value or "")
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date") from exc
    if parsed.isoformat() != text:
        raise ValueError(f"{field} must be a canonical ISO date")
    return text


def canonical_time(value: Any | None, *, field: str) -> tuple[str | None, str]:
    if value is None:
        return None, "unknown"
    text = str(value)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return canonical_date(text, field=field), "date_only"
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp or date") from exc
    return parsed.isoformat(), "timestamp" if parsed.tzinfo is not None else "timestamp_naive"


def require_aware_timestamp(value: Any, *, field: str) -> str:
    text, precision = canonical_time(value, field=field)
    if precision != "timestamp" or text is None:
        raise ValueError(f"{field} must be timezone-aware")
    return text


def reject_forbidden_fields(value: Any, *, path: str = "risk_event") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).casefold()
            if normalized in FORBIDDEN_KEYS or normalized.endswith("_score"):
                raise ValueError(
                    f"risk event contains prohibited score/trade field: {path}.{key}"
                )
            reject_forbidden_fields(child, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            reject_forbidden_fields(child, path=f"{path}[{index}]")


def normalize_evidence_refs(
    references: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw in references:
        if not isinstance(raw, Mapping):
            raise ValueError("risk evidence reference must be an object")
        evidence_id = str(
            raw.get("evidence_id")
            or raw.get("document_id")
            or raw.get("path")
            or ""
        )
        digest = str(raw.get("sha256") or raw.get("raw_sha256") or "").lower()
        if not evidence_id or not _SHA256.fullmatch(digest):
            raise ValueError(
                "risk evidence reference requires evidence_id/path and SHA-256"
            )
        identity = (evidence_id, digest)
        if identity in seen:
            continue
        seen.add(identity)
        item = {"evidence_id": evidence_id, "sha256": digest}
        for field in ("kind", "locator", "source_id"):
            if raw.get(field) is not None:
                item[field] = str(raw[field])
        output.append(item)
    return sorted(output, key=lambda item: (item["evidence_id"], item["sha256"]))


def build_risk_event(
    *,
    event_type: str,
    scope: str,
    entity_id: str,
    event_time: Any | None,
    published_at: Any | None,
    effective_from: str | None,
    as_of_date: str,
    severity: str,
    status: str,
    source: Mapping[str, Any],
    evidence_refs: Sequence[Mapping[str, Any]],
    detector: Mapping[str, Any] | None = None,
    provider: Mapping[str, Any] | None = None,
    observed_at: Any | None = None,
    structured_fields: Mapping[str, Any] | None = None,
    provenance: Mapping[str, Any] | None = None,
    revision_of: str | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    if not event_type or scope not in SCOPES or not entity_id:
        raise ValueError("risk event type, scope, and entity_id are required")
    if severity not in SEVERITY_ORDER or status not in STATUSES:
        raise ValueError("risk event severity or status is invalid")
    if not isinstance(source, Mapping) or not source.get("source_id"):
        raise ValueError("risk event source identity is required")
    detector_value = dict(detector) if detector is not None else None
    provider_value = dict(provider) if provider is not None else None
    if detector_value is None and provider_value is None:
        raise ValueError("risk event detector or provider identity is required")
    if detector_value is not None and detector_value.get("mode") not in DETECTION_MODES:
        raise ValueError("risk event detector mode is invalid")
    event_time_value, event_precision = canonical_time(event_time, field="event_time")
    published_value, published_precision = canonical_time(
        published_at, field="published_at"
    )
    observed_value = (
        require_aware_timestamp(observed_at, field="observed_at")
        if observed_at is not None
        else None
    )
    effective_value = (
        canonical_date(effective_from, field="effective_from")
        if effective_from
        else None
    )
    as_of_value = canonical_date(as_of_date, field="as_of_date")
    refs = normalize_evidence_refs(evidence_refs)
    if status == "observed" and not refs:
        raise ValueError("observed risk event requires evidence references")
    fields = dict(structured_fields or {})
    provenance_value = dict(provenance or {})
    provenance_value.setdefault(
        "input_sha256",
        canonical_sha256(
            {
                "source": dict(source),
                "fields": fields,
                "evidence_refs": refs,
            }
        ),
    )
    reject_forbidden_fields(fields)
    reject_forbidden_fields(provenance_value)
    record = {
        "schema_version": RISK_EVENT_SCHEMA_VERSION,
        "mode": MODE,
        "event_id": event_id or "",
        "event_type": event_type,
        "scope": scope,
        "entity_id": str(entity_id),
        "event_time": event_time_value,
        "event_time_precision": event_precision,
        "published_at": published_value,
        "published_time_precision": published_precision,
        "effective_from": effective_value,
        "effective_time_precision": "date_only" if effective_value else "unknown",
        "as_of_date": as_of_value,
        "observed_at": observed_value,
        "severity": severity,
        "status": status,
        "source": dict(source),
        "evidence_refs": refs,
        "detector": detector_value,
        "provider": provider_value,
        "structured_fields": fields,
        "provenance": provenance_value,
        "revision_of": revision_of,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    if not record["event_id"]:
        record["event_id"] = "risk_" + canonical_sha256(
            {key: value for key, value in record.items() if key != "event_id"}
        )[:32]
    validate_risk_event(record)
    return record


def validate_risk_event(event: Mapping[str, Any]) -> dict[str, Any]:
    missing = sorted(REQUIRED_FIELDS - set(event))
    if missing:
        raise ValueError(f"risk event is missing canonical fields: {missing}")
    if event.get("schema_version") != RISK_EVENT_SCHEMA_VERSION:
        raise ValueError("risk event schema mismatch")
    if event.get("mode") != MODE or not event.get("event_id"):
        raise ValueError("risk event mode or ID mismatch")
    if not event.get("event_type") or event.get("scope") not in SCOPES or not event.get("entity_id"):
        raise ValueError("risk event scope is invalid")
    if event.get("severity") not in SEVERITY_ORDER or event.get("status") not in STATUSES:
        raise ValueError("risk event severity or status is invalid")
    if event.get("status") == "no_event":
        raise ValueError("risk event cannot claim no_event")
    if (
        event.get("eligible_for_oos_claim") is not False
        or event.get("promotion_allowed") is not False
        or event.get("live_trading_allowed") is not False
    ):
        raise ValueError("risk event safety flags must be false")
    canonical_date(event.get("as_of_date"), field="as_of_date")
    event_time, event_precision = canonical_time(event.get("event_time"), field="event_time")
    published_at, published_precision = canonical_time(
        event.get("published_at"), field="published_at"
    )
    if event.get("event_time") != event_time or event.get("event_time_precision") != event_precision:
        raise ValueError("risk event event_time precision mismatch")
    if event.get("published_at") != published_at or event.get("published_time_precision") != published_precision:
        raise ValueError("risk event published_at precision mismatch")
    effective_from = event.get("effective_from")
    if effective_from is not None:
        canonical_date(effective_from, field="effective_from")
        if event.get("effective_time_precision") != "date_only":
            raise ValueError("risk event effective_from precision mismatch")
    elif event.get("effective_time_precision") != "unknown":
        raise ValueError("risk event effective_from precision mismatch")
    observed_at = event.get("observed_at")
    if observed_at is not None:
        require_aware_timestamp(observed_at, field="observed_at")
    source = event.get("source")
    if not isinstance(source, Mapping) or not source.get("source_id"):
        raise ValueError("risk event source identity is missing")
    normalize_evidence_refs(event.get("evidence_refs") or [])
    if event.get("status") == "observed" and not event.get("evidence_refs"):
        raise ValueError("observed risk event has no evidence")
    if event.get("detector") is None and event.get("provider") is None:
        raise ValueError("risk event detector/provider identity is missing")
    reject_forbidden_fields(event)
    canonical_json_bytes(dict(event))
    validate_no_executable_instructions(dict(event), context="canonical risk event")
    return dict(event)
