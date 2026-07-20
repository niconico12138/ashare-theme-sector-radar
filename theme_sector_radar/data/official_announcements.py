"""Paper-only official announcement data contracts and immutable evidence storage.

This module deliberately stops at source metadata, raw documents, structured event
records, and health evidence. It does not calculate event scores or trading actions.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)


MODE = "paper_shadow_research_only"
DISCLAIMER = "Research evidence only; no scores, orders, broker connection, or live execution."
SOURCE_REGISTRY_SCHEMA_VERSION = "official-announcement-source-registry-v1"
RAW_DOCUMENT_SCHEMA_VERSION = "official-announcement-raw-document-v1"
EVENT_LEDGER_SCHEMA_VERSION = "official-announcement-event-ledger-v1"
SOURCE_HEALTH_SCHEMA_VERSION = "official-announcement-source-health-v1"
REGISTRY_VERSION = "official-announcement-registry-2026-07-20-v1"
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PUBLISHED_PRECISIONS = {"timestamp", "timestamp_naive", "date_only", "unknown"}
_RETRIEVAL_STATUSES = {
    "retrieved",
    "retrieval_failed",
    "parse_failed",
    "mapping_uncertain",
    "not_attempted",
    "blocked",
}
_AUTHORITY_TIERS = {"primary", "secondary", "research_only"}
_FORBIDDEN_EVENT_FIELDS = {
    "action",
    "confidence",
    "decision",
    "event_score",
    "final_score",
    "impact_score",
    "rank",
    "score",
    "signal",
    "trade",
    "weight",
}


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _finite_json(value: Any, *, context: str) -> None:
    try:
        _canonical_json(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{context} must be strict JSON") from exc


def _iso_date(value: Any, *, field: str) -> str:
    text = str(value or "")
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date") from exc
    if parsed.isoformat() != text:
        raise ValueError(f"{field} must be a canonical ISO date")
    return text


def _iso_datetime(value: Any, *, field: str, allow_date: bool = True) -> tuple[str, str]:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat(), "date_only"
    text = str(value or "")
    if allow_date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return _iso_date(text, field=field), "date_only"
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp or date") from exc
    precision = "timestamp" if parsed.tzinfo is not None else "timestamp_naive"
    return parsed.isoformat(), precision


def _require_aware_datetime(value: Any, *, field: str) -> str:
    text, precision = _iso_datetime(value, field=field, allow_date=False)
    if precision != "timestamp":
        raise ValueError(f"{field} must be timezone-aware")
    return text


def _next_trading_date(day: date, trading_dates: Sequence[str] | None) -> str | None:
    if trading_dates is None:
        return None
    normalized = [_iso_date(value, field="trading_dates") for value in trading_dates]
    for candidate in normalized:
        if candidate > day.isoformat():
            return candidate
    return None


def infer_effective_from(
    published_at: Any,
    *,
    trading_dates: Sequence[str] | None = None,
    market_close: time = time(15, 0),
) -> dict[str, Any]:
    """Infer only what the timestamp can prove; date-only stays unresolved."""

    text, precision = _iso_datetime(published_at, field="published_at")
    if precision == "date_only":
        return {
            "effective_from": None,
            "effective_time_precision": "unknown",
            "inference_status": "date_only_unresolved",
        }
    if precision != "timestamp":
        return {
            "effective_from": None,
            "effective_time_precision": "unknown",
            "inference_status": "naive_timestamp_blocked",
        }
    parsed = datetime.fromisoformat(text).astimezone(SHANGHAI_TZ)
    if parsed.time() > market_close:
        next_day = _next_trading_date(parsed.date(), trading_dates)
        return {
            "effective_from": next_day,
            "effective_time_precision": "date_only" if next_day else "unknown",
            "inference_status": "after_close_next_trading_day"
            if next_day
            else "after_close_calendar_required",
        }
    return {
        "effective_from": parsed.date().isoformat(),
        "effective_time_precision": "date_only",
        "inference_status": "same_trading_date_before_close",
    }


def _source_specs() -> list[dict[str, Any]]:
    official = [
        ("sse_announcements", "Shanghai Stock Exchange announcements", "https://www.sse.com.cn/disclosure/listedinfo/announcement/", "stock_exchange"),
        ("szse_announcements", "Shenzhen Stock Exchange announcements", "https://www.szse.cn/disclosure/listed/notice/", "stock_exchange"),
        ("bse_announcements", "Beijing Stock Exchange announcements", "https://www.bse.cn/disclosure/announcement.html", "stock_exchange"),
        ("csrc_notices", "China Securities Regulatory Commission notices", "https://www.csrc.gov.cn/csrc/c100028/common_list.shtml", "regulator"),
        ("mof_notices", "Ministry of Finance notices", "https://www.mof.gov.cn/zhengwuxinxi/zhengcefabu/", "policy"),
        ("sta_notices", "State Taxation Administration notices", "https://www.chinatax.gov.cn/chinatax/n810214/index.html", "policy"),
        ("ndrc_notices", "National Development and Reform Commission notices", "https://www.ndrc.gov.cn/xxgk/zcfb/", "policy"),
        ("miit_notices", "Ministry of Industry and Information Technology notices", "https://www.miit.gov.cn/zwgk/zcwj/wjfb/index.html", "policy"),
        ("issuer_official_announcements", "Listed company official announcements", "", "issuer_official"),
        ("fund_official_disclosures", "Fund manager and fund disclosure notices", "", "fund_disclosure"),
    ]
    records = []
    for source_id, name, url, source_kind in official:
        record = {
                "source_id": source_id,
                "display_name": name,
                "authority_tier": "primary",
                "source_kind": source_kind,
                "official_url": url or None,
                "historical_coverage": {"status": "pending_verification", "start": None, "end": None},
                "time_precision": {"status": "pending_verification", "supported": ["timestamp", "date_only"]},
                "source_version": "entry-v1",
                "original_content": {"status": "required", "policy": "archive_raw_bytes"},
                "sha256": {"status": "computed_per_document", "algorithm": "sha256"},
                "retrieval_frequency": {"status": "pending_verification", "value": None},
                "cost": {"status": "pending_verification", "value": None},
                "availability_status": "blocked_no_network_or_terms_review",
                "adapter_status": "blocked",
                "requires_credentials": False,
                "notes": "Official endpoint metadata only; no live adapter is enabled in this layer.",
            }
        if source_id == "csrc_notices":
            record.update(
                {
                    "historical_coverage": {
                        "status": "document_pages_verified_sample_only",
                        "start": "2021-12-10",
                        "end": "2021-12-10",
                    },
                    "time_precision": {
                        "status": "verified_document_date_only",
                        "supported": ["date_only"],
                    },
                    "source_version": "csrc-html-document-v1",
                    "retrieval_frequency": {
                        "status": "manual_read_only_only",
                        "value": "explicit_document_url",
                    },
                    "availability_status": "adapter_ready_runtime_terms_gate",
                    "adapter_status": "ready",
                    "notes": (
                        "Read-only explicit-document adapter implemented; runtime remains "
                        "blocked unless terms are explicitly verified."
                    ),
                }
            )
        records.append(record)
    records.extend(
        [
            {
                "source_id": "akshare_announcement_adapter",
                "display_name": "AkShare announcement adapter",
                "authority_tier": "secondary",
                "source_kind": "aggregator_adapter",
                "official_url": None,
                "historical_coverage": {"status": "pending_verification", "start": None, "end": None},
                "time_precision": {"status": "pending_verification", "supported": ["timestamp", "date_only"]},
                "source_version": "entry-v1",
                "original_content": {"status": "derived_only", "policy": "must_retain_upstream_reference"},
                "sha256": {"status": "computed_per_document", "algorithm": "sha256"},
                "retrieval_frequency": {"status": "pending_verification", "value": None},
                "cost": {"status": "pending_verification", "value": None},
                "availability_status": "blocked_no_network_or_terms_review",
                "adapter_status": "blocked",
                "requires_credentials": False,
                "notes": "Secondary discovery only; never authoritative when primary evidence is absent.",
            },
            {
                "source_id": "announcement_research_fixture",
                "display_name": "Offline announcement fixture",
                "authority_tier": "research_only",
                "source_kind": "offline_fixture",
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
                "notes": "Software-contract fixture; cannot support PIT or performance claims.",
            },
        ]
    )
    return records


def default_source_registry() -> dict[str, Any]:
    sources = _source_specs()
    registry = {
        "schema_version": SOURCE_REGISTRY_SCHEMA_VERSION,
        "mode": MODE,
        "status": "ok",
        "registry_version": REGISTRY_VERSION,
        "sources": sources,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    validate_source_registry(registry)
    return registry


def validate_source_registry(registry: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(registry, Mapping):
        raise ValueError("announcement source registry must be an object")
    if registry.get("schema_version") != SOURCE_REGISTRY_SCHEMA_VERSION:
        raise ValueError("announcement source registry schema mismatch")
    if registry.get("mode") != MODE or registry.get("status") != "ok":
        raise ValueError("announcement source registry is not paper-only")
    if registry.get("promotion_allowed") is not False or registry.get("live_trading_allowed") is not False:
        raise ValueError("announcement source registry safety flags must be false")
    sources = registry.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("announcement source registry sources are missing")
    seen: set[str] = set()
    for source in sources:
        if not isinstance(source, Mapping):
            raise ValueError("announcement source registry entry must be an object")
        source_id = str(source.get("source_id") or "")
        if not source_id or source_id in seen:
            raise ValueError("announcement source registry contains duplicate source_id")
        seen.add(source_id)
        if source.get("authority_tier") not in _AUTHORITY_TIERS:
            raise ValueError(f"announcement source authority tier is invalid: {source_id}")
        if source.get("adapter_status") not in {"blocked", "fixture", "ready"}:
            raise ValueError(f"announcement source adapter status is invalid: {source_id}")
        for key in ("historical_coverage", "time_precision", "original_content", "sha256", "retrieval_frequency", "cost"):
            if not isinstance(source.get(key), Mapping):
                raise ValueError(f"announcement source capability is missing: {source_id}.{key}")
    validate_no_executable_instructions(dict(registry), context="announcement source registry")
    _finite_json(dict(registry), context="announcement source registry")
    return dict(registry)


def probe_source_registry(registry: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Probe metadata only; this function never performs network I/O."""

    checked = validate_source_registry(registry or default_source_registry())
    results = []
    for source in checked["sources"]:
        if source["adapter_status"] == "fixture":
            status = "fixture_ready"
            reason = "offline fixture only"
        elif source["adapter_status"] == "ready":
            status = "blocked"
            reason = "adapter implemented; runtime terms verification is required"
        else:
            status = "blocked"
            reason = "network disabled; terms, cadence, cost, and credentials require verification"
        results.append({"source_id": source["source_id"], "probe_status": status, "reason": reason})
    return {
        "schema_version": SOURCE_HEALTH_SCHEMA_VERSION,
        "mode": MODE,
        "status": "metadata_only",
        "probe_mode": "no_network",
        "registry_version": checked["registry_version"],
        "sources": results,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }


def _write_bytes_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"immutable raw document changed: {path}")
        return
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def archive_raw_announcement(
    archive_root: Path | str,
    *,
    source_id: str,
    source_url_or_path: str,
    published_at: Any,
    captured_at: Any,
    raw_content: bytes | str,
    effective_from: str | None = None,
    document_version: str = "v1",
    revision_of: str | None = None,
    retrieval_status: str = "retrieved",
    provider_version: str | None = None,
    registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Archive one raw document without overwriting a prior byte identity."""

    checked_registry = validate_source_registry(registry or default_source_registry())
    known = {str(row["source_id"]): row for row in checked_registry["sources"]}
    if source_id not in known:
        raise ValueError(f"unknown announcement source: {source_id}")
    if not source_url_or_path:
        raise ValueError("source_url_or_path is required")
    if retrieval_status != "retrieved":
        raise ValueError("only retrieved content can be written to raw archive")
    if not document_version:
        raise ValueError("document_version is required")
    if published_at is None:
        published_text, published_precision = None, "unknown"
    else:
        published_text, published_precision = _iso_datetime(published_at, field="published_at")
    captured_text = _require_aware_datetime(captured_at, field="captured_at")
    effective_text = _iso_date(effective_from, field="effective_from") if effective_from else None
    payload = raw_content.encode("utf-8") if isinstance(raw_content, str) else bytes(raw_content)
    if not payload:
        raise ValueError("raw_content must not be empty")
    raw_sha256 = hashlib.sha256(payload).hexdigest()
    document_id = _canonical_sha256(
        {"source_id": source_id, "raw_sha256": raw_sha256, "document_version": document_version}
    )
    root = Path(archive_root).resolve()
    raw_relative = Path("raw") / source_id / f"{raw_sha256}.bin"
    manifest_relative = Path("manifests") / f"{document_id}.json"
    raw_path = root / raw_relative
    manifest_path = root / manifest_relative
    manifest = {
        "schema_version": RAW_DOCUMENT_SCHEMA_VERSION,
        "mode": MODE,
        "status": "archived",
        "document_id": document_id,
        "source_id": source_id,
        "source_version": known[source_id]["source_version"],
        "provider_version": provider_version,
        "source_url_or_path": source_url_or_path,
        "published_at": published_text,
        "published_time_precision": published_precision,
        "captured_at": captured_text,
        "retrieved_at": captured_text,
        "effective_from": effective_text,
        "effective_time_precision": "date_only" if effective_text else "unknown",
        "raw_relative_path": raw_relative.as_posix(),
        "raw_sha256": raw_sha256,
        "raw_size_bytes": len(payload),
        "document_version": document_version,
        "revision_of": revision_of,
        "retrieval_status": retrieval_status,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(manifest, context="raw announcement manifest")
    _finite_json(manifest, context="raw announcement manifest")
    _write_bytes_once(raw_path, payload)
    if manifest_path.exists():
        existing, _ = load_strict_json_with_sha256(manifest_path)
        if existing != manifest:
            raise ValueError(f"immutable announcement manifest changed: {manifest_path}")
    else:
        write_strict_json_atomic(manifest_path, manifest)
    return {**manifest, "raw_path": str(raw_path), "manifest_path": str(manifest_path)}


def load_archived_announcement(manifest_path: Path | str, *, archive_root: Path | str | None = None) -> tuple[dict[str, Any], bytes]:
    manifest, _ = load_strict_json_with_sha256(Path(manifest_path))
    if manifest.get("schema_version") != RAW_DOCUMENT_SCHEMA_VERSION or manifest.get("mode") != MODE:
        raise ValueError("raw announcement manifest schema mismatch")
    root = Path(archive_root).resolve() if archive_root else Path(manifest_path).resolve().parents[1]
    raw_path = (root / str(manifest.get("raw_relative_path") or "")).resolve()
    try:
        raw_path.relative_to(root)
    except ValueError as exc:
        raise ValueError("raw announcement path escapes archive root") from exc
    payload = raw_path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != manifest.get("raw_sha256"):
        raise ValueError("raw announcement SHA mismatch")
    return dict(manifest), payload


def build_event_record(
    *,
    source_id: str,
    event_type: str,
    title: str,
    issuer: str | None = None,
    published_at: Any | None = None,
    effective_from: str | None = None,
    evidence_refs: Sequence[Mapping[str, Any]] = (),
    affected_symbols: Sequence[str] = (),
    affected_entities: Sequence[str] = (),
    structured_fields: Mapping[str, Any] | None = None,
    event_status: str = "observed",
    retrieval_status: str = "retrieved",
    mapping_status: str = "not_attempted",
    revision_of: str | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    if event_status not in {"observed", "unavailable", "parse_failed", "mapping_uncertain", "conflict"}:
        raise ValueError("event_status must represent evidence state, not no_event")
    if retrieval_status not in _RETRIEVAL_STATUSES:
        raise ValueError("event retrieval_status is invalid")
    if event_status == "observed" and not evidence_refs:
        raise ValueError("observed event requires raw evidence references")
    published_text = None
    published_precision = "unknown"
    if published_at is not None:
        published_text, published_precision = _iso_datetime(published_at, field="published_at")
    effective_text = _iso_date(effective_from, field="effective_from") if effective_from else None
    if mapping_status not in {"not_attempted", "resolved", "uncertain", "unmapped"}:
        raise ValueError("event mapping_status is invalid")
    fields = dict(structured_fields or {})
    _reject_event_score_fields(fields)
    refs = [dict(ref) for ref in evidence_refs]
    for ref in refs:
        if not ref.get("document_id") or not _SHA256.fullmatch(str(ref.get("raw_sha256") or "")):
            raise ValueError("event evidence reference must bind document_id and raw_sha256")
    record = {
        "schema_version": EVENT_LEDGER_SCHEMA_VERSION,
        "mode": MODE,
        "event_id": event_id or "",
        "event_status": event_status,
        "retrieval_status": retrieval_status,
        "mapping_status": mapping_status,
        "source_id": source_id,
        "event_type": event_type,
        "issuer": issuer,
        "title": str(title),
        "published_at": published_text,
        "published_time_precision": published_precision,
        "effective_from": effective_text,
        "effective_time_precision": "date_only" if effective_text else "unknown",
        "affected_symbols": sorted({str(value) for value in affected_symbols}),
        "affected_entities": sorted({str(value) for value in affected_entities}),
        "structured_fields": fields,
        "evidence_refs": refs,
        "revision_of": revision_of,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    if not record["event_id"]:
        identity = {key: value for key, value in record.items() if key != "event_id"}
        record["event_id"] = "event_" + _canonical_sha256(identity)[:32]
    validate_event_record(record)
    return record


def _reject_event_score_fields(value: Any, *, path: str = "event") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).casefold()
            if normalized in _FORBIDDEN_EVENT_FIELDS or normalized.endswith("_score"):
                raise ValueError(f"event record contains prohibited score/action field: {path}.{key}")
            _reject_event_score_fields(child, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_event_score_fields(child, path=f"{path}[{index}]")


def validate_event_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if record.get("schema_version") != EVENT_LEDGER_SCHEMA_VERSION or record.get("mode") != MODE:
        raise ValueError("event record schema or mode mismatch")
    if not record.get("event_id") or record.get("event_status") == "no_event":
        raise ValueError("event record cannot claim no_event")
    if record.get("promotion_allowed") is not False or record.get("live_trading_allowed") is not False:
        raise ValueError("event record safety flags must be false")
    if record.get("published_time_precision") not in _PUBLISHED_PRECISIONS:
        raise ValueError("event published time precision is invalid")
    _reject_event_score_fields(record)
    _finite_json(dict(record), context="event record")
    validate_no_executable_instructions(dict(record), context="event record")
    return dict(record)


def build_event_ledger(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Deduplicate exact evidence, preserve revisions, and surface conflicts."""

    validated = [validate_event_record(record) for record in records]
    unique: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    by_fingerprint: dict[str, dict[str, Any]] = {}
    by_logical_key: dict[str, dict[str, Any]] = {}
    for record in validated:
        fingerprint = _canonical_sha256({key: value for key, value in record.items() if key != "event_id"})
        if fingerprint in by_fingerprint:
            duplicates.append({"event_id": record["event_id"], "duplicate_of": by_fingerprint[fingerprint]["event_id"]})
            continue
        logical_key = _canonical_sha256(
            {
                "source_id": record["source_id"],
                "issuer": record["issuer"],
                "published_at": record["published_at"],
                "title": " ".join(str(record["title"]).split()).casefold(),
            }
        )
        prior = by_logical_key.get(logical_key)
        revision_ref = record.get("revision_of")
        is_declared_revision = bool(revision_ref) and revision_ref in {
            prior.get("event_id") if prior else None,
            prior.get("revision_of") if prior else None,
        }
        if prior and not is_declared_revision:
            conflicted = dict(record)
            conflicted["event_status"] = "conflict"
            conflicted["conflict_with"] = prior["event_id"]
            conflicts.append({"event_id": record["event_id"], "conflict_with": prior["event_id"]})
            record = conflicted
        by_fingerprint[fingerprint] = record
        by_logical_key[logical_key] = record
        unique.append(record)
    ledger = {
        "schema_version": EVENT_LEDGER_SCHEMA_VERSION,
        "mode": MODE,
        "status": "ok" if not conflicts else "conflicts_present",
        "events": unique,
        "duplicates": duplicates,
        "conflicts": conflicts,
        "event_count": len(unique),
        "duplicate_count": len(duplicates),
        "conflict_count": len(conflicts),
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(ledger, context="event ledger")
    _finite_json(ledger, context="event ledger")
    return ledger


def build_source_health_report(
    observations: Iterable[Mapping[str, Any]],
    *,
    registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    checked = validate_source_registry(registry or default_source_registry())
    by_source = {str(row["source_id"]): row for row in checked["sources"]}
    seen: set[str] = set()
    reports: list[dict[str, Any]] = []
    for raw in observations:
        source_id = str(raw.get("source_id") or "")
        if source_id not in by_source or source_id in seen:
            raise ValueError("source health observations must use unique registry source IDs")
        seen.add(source_id)
        retrieval_status = str(raw.get("retrieval_status") or "not_attempted")
        if retrieval_status not in _RETRIEVAL_STATUSES:
            raise ValueError("source health retrieval_status is invalid")
        if raw.get("event_state") == "no_event":
            raise ValueError("source health cannot convert incomplete retrieval into no_event")
        parse_status = str(raw.get("parse_status") or "not_attempted")
        mapping_status = str(raw.get("mapping_status") or "not_attempted")
        health_status = "ok"
        if retrieval_status in {"blocked", "not_attempted", "retrieval_failed"}:
            health_status = "blocked" if retrieval_status == "blocked" else "unavailable"
        elif retrieval_status == "parse_failed" or parse_status == "parse_failed":
            health_status = "parse_failed"
        elif retrieval_status == "mapping_uncertain" or mapping_status == "uncertain":
            health_status = "degraded"
        reports.append(
            {
                "source_id": source_id,
                "authority_tier": by_source[source_id]["authority_tier"],
                "health_status": health_status,
                "retrieval_status": retrieval_status,
                "parse_status": parse_status,
                "mapping_status": mapping_status,
                "event_count": int(raw.get("event_count") or 0),
                "event_state": "observed" if int(raw.get("event_count") or 0) > 0 else "unknown_not_no_event",
                "error_code": raw.get("error_code"),
                "captured_at": raw.get("captured_at"),
            }
        )
    for source_id, source in by_source.items():
        if source_id not in seen:
            reports.append(
                {
                    "source_id": source_id,
                    "authority_tier": source["authority_tier"],
                    "health_status": "unobserved",
                    "retrieval_status": "not_attempted",
                    "parse_status": "not_attempted",
                    "mapping_status": "not_attempted",
                    "event_count": 0,
                    "event_state": "unknown_not_no_event",
                    "error_code": "source_not_observed",
                    "captured_at": None,
                }
            )
    report = {
        "schema_version": SOURCE_HEALTH_SCHEMA_VERSION,
        "mode": MODE,
        "status": "ok",
        "registry_version": checked["registry_version"],
        "sources": sorted(reports, key=lambda row: row["source_id"]),
        "summary": {
            "source_count": len(reports),
            "ok_count": sum(row["health_status"] == "ok" for row in reports),
            "blocked_or_unavailable_count": sum(row["health_status"] in {"blocked", "unavailable", "unobserved"} for row in reports),
            "parse_failed_count": sum(row["health_status"] == "parse_failed" for row in reports),
            "mapping_uncertain_count": sum(row["health_status"] == "degraded" for row in reports),
        },
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(report, context="announcement source health")
    _finite_json(report, context="announcement source health")
    return report
