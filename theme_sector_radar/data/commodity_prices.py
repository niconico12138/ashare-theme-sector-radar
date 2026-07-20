"""Paper-only commodity price evidence and observation contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping, Protocol, Sequence

from theme_sector_radar.reporting.paper_only_contract import validate_no_executable_instructions
from theme_sector_radar.reporting.strict_json import load_strict_json_with_sha256, write_strict_json_atomic

from .official_announcements import DISCLAIMER, MODE
from .risk_event_schema import (
    canonical_date,
    canonical_sha256,
    canonical_time,
    normalize_evidence_refs,
    require_aware_timestamp,
)


COMMODITY_SOURCE_REGISTRY_VERSION = "commodity-price-source-registry-v1"
COMMODITY_EVIDENCE_SCHEMA_VERSION = "commodity-price-raw-evidence-v1"
COMMODITY_OBSERVATION_SCHEMA_VERSION = "commodity-price-observation-v1"
COMMODITY_LEDGER_SCHEMA_VERSION = "commodity-price-ledger-v1"
COMMODITY_PROVIDER_VERSION = "commodity-price-provider-v1"
MARKET_TYPES = {"spot", "futures"}
STATUSES = {"observed", "blocked", "unknown", "conflict"}
FIXTURE_SOURCE_ID = "commodity_price_research_fixture"


def commodity_price_source_registry() -> dict[str, Any]:
    sources = [
        {
            "source_id": "ndrc_price_monitoring",
            "display_name": "NDRC price monitoring",
            "authority_tier": "primary",
            "official_url": "https://www.ndrc.gov.cn/fggz/jgjdyfld/jjszhdt/",
            "market_types": ["spot"],
            "adapter_status": "blocked",
            "block_reason": "machine-readable format, terms, cadence, and units not verified",
        },
        {
            "source_id": "shfe_official_market_data",
            "display_name": "Shanghai Futures Exchange market data",
            "authority_tier": "primary",
            "official_url": "https://www.shfe.com.cn/statements/dataview.html?paramid=kx",
            "market_types": ["futures"],
            "adapter_status": "blocked",
            "block_reason": "terms, contract metadata, settlement semantics, and cadence not verified",
        },
        {
            "source_id": "akshare_commodity_discovery",
            "display_name": "AkShare commodity discovery",
            "authority_tier": "secondary",
            "official_url": None,
            "market_types": ["spot", "futures"],
            "adapter_status": "blocked",
            "block_reason": "secondary discovery only; upstream official evidence is required",
        },
        {
            "source_id": FIXTURE_SOURCE_ID,
            "display_name": "Commodity price research fixture",
            "authority_tier": "research_only",
            "official_url": None,
            "market_types": ["spot", "futures"],
            "adapter_status": "fixture",
            "block_reason": None,
        },
    ]
    registry = {
        "schema_version": COMMODITY_SOURCE_REGISTRY_VERSION,
        "mode": MODE,
        "status": "ok",
        "sources": sources,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    validate_commodity_source_registry(registry)
    return registry


def validate_commodity_source_registry(registry: Mapping[str, Any]) -> dict[str, Any]:
    if registry.get("schema_version") != COMMODITY_SOURCE_REGISTRY_VERSION or registry.get("mode") != MODE:
        raise ValueError("commodity source registry schema or mode mismatch")
    if registry.get("promotion_allowed") is not False or registry.get("live_trading_allowed") is not False:
        raise ValueError("commodity source registry safety flags must be false")
    sources = registry.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("commodity source registry is empty")
    seen: set[str] = set()
    for source in sources:
        source_id = str(source.get("source_id") or "") if isinstance(source, Mapping) else ""
        if not source_id or source_id in seen:
            raise ValueError("commodity source registry has duplicate or empty source_id")
        seen.add(source_id)
        if source.get("authority_tier") not in {"primary", "secondary", "research_only"}:
            raise ValueError("commodity source authority tier is invalid")
        if source.get("adapter_status") not in {"blocked", "ready", "fixture"}:
            raise ValueError("commodity source adapter status is invalid")
        if not set(source.get("market_types") or []).issubset(MARKET_TYPES):
            raise ValueError("commodity source market types are invalid")
    validate_no_executable_instructions(dict(registry), context="commodity source registry")
    return dict(registry)


def _write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"immutable commodity evidence changed: {path}")
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


def archive_commodity_price_evidence(
    archive_root: Path | str,
    *,
    source_id: str,
    source_url_or_path: str,
    retrieved_at: Any,
    raw_content: bytes | str,
    provider_version: str,
    document_version: str = "v1",
    revision_of: str | None = None,
) -> dict[str, Any]:
    sources = {row["source_id"]: row for row in commodity_price_source_registry()["sources"]}
    if source_id not in sources or not source_url_or_path or not provider_version:
        raise ValueError("commodity evidence source identity is incomplete")
    retrieved = require_aware_timestamp(retrieved_at, field="retrieved_at")
    payload = raw_content.encode("utf-8") if isinstance(raw_content, str) else bytes(raw_content)
    if not payload:
        raise ValueError("commodity evidence raw content is empty")
    digest = hashlib.sha256(payload).hexdigest()
    evidence_id = canonical_sha256(
        {"source_id": source_id, "sha256": digest, "document_version": document_version}
    )
    root = Path(archive_root).resolve()
    raw_relative = Path("raw") / source_id / f"{digest}.bin"
    manifest_relative = Path("manifests") / f"{evidence_id}.json"
    manifest = {
        "schema_version": COMMODITY_EVIDENCE_SCHEMA_VERSION,
        "mode": MODE,
        "status": "archived",
        "evidence_id": evidence_id,
        "source_id": source_id,
        "authority_tier": sources[source_id]["authority_tier"],
        "source_url_or_path": source_url_or_path,
        "retrieved_at": retrieved,
        "raw_relative_path": raw_relative.as_posix(),
        "raw_sha256": digest,
        "raw_size_bytes": len(payload),
        "provider_version": provider_version,
        "document_version": document_version,
        "revision_of": revision_of,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    _write_once(root / raw_relative, payload)
    manifest_path = root / manifest_relative
    if manifest_path.exists():
        existing, _ = load_strict_json_with_sha256(manifest_path)
        if existing != manifest:
            raise ValueError("immutable commodity evidence manifest changed")
    else:
        write_strict_json_atomic(manifest_path, manifest)
    return {**manifest, "raw_path": str(root / raw_relative), "manifest_path": str(manifest_path)}


def build_commodity_observation(
    *,
    price_date: str,
    as_of_date: str,
    observed_at: Any,
    commodity_id: str,
    commodity_name: str,
    unit: str | None,
    currency: str | None,
    market_type: str,
    price: float | None,
    source: Mapping[str, Any],
    source_url_or_path: str,
    evidence_refs: Sequence[Mapping[str, Any]],
    provider: Mapping[str, Any],
    published_at: Any | None = None,
    effective_from: str | None = None,
    status: str = "observed",
    quality_issues: Sequence[str] = (),
    contract_code: str | None = None,
    revision_of: str | None = None,
    observation_id: str | None = None,
) -> dict[str, Any]:
    if status not in STATUSES or market_type not in MARKET_TYPES:
        raise ValueError("commodity observation status or market type is invalid")
    if not commodity_id or not commodity_name or not source.get("source_id") or not provider.get("provider_id"):
        raise ValueError("commodity observation identity is incomplete")
    date_value = canonical_date(price_date, field="price_date")
    as_of_value = canonical_date(as_of_date, field="as_of_date")
    observed_value = require_aware_timestamp(observed_at, field="observed_at")
    published_value, published_precision = canonical_time(published_at, field="published_at")
    effective_value = canonical_date(effective_from, field="effective_from") if effective_from else None
    refs = normalize_evidence_refs(evidence_refs)
    numeric = None if price is None else float(price)
    if numeric is not None and not math.isfinite(numeric):
        raise ValueError("commodity observation price must be finite")
    issues = sorted({str(issue) for issue in quality_issues})
    if status == "observed" and (numeric is None or numeric <= 0 or not unit or not currency or not refs):
        raise ValueError("observed commodity price requires positive price, unit, currency, and evidence")
    record = {
        "schema_version": COMMODITY_OBSERVATION_SCHEMA_VERSION,
        "mode": MODE,
        "observation_id": observation_id or "",
        "status": status,
        "quality_status": "complete" if not issues and status == "observed" else "degraded",
        "quality_issues": issues,
        "price_date": date_value,
        "as_of_date": as_of_value,
        "observed_at": observed_value,
        "commodity_id": commodity_id,
        "commodity_name": commodity_name,
        "unit": unit,
        "currency": currency,
        "market_type": market_type,
        "price": numeric,
        "contract_code": contract_code,
        "published_at": published_value,
        "published_time_precision": published_precision,
        "effective_from": effective_value,
        "effective_time_precision": "date_only" if effective_value else "unknown",
        "source": dict(source),
        "source_url_or_path": source_url_or_path,
        "evidence_refs": refs,
        "provider": dict(provider),
        "revision_of": revision_of,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    if not record["observation_id"]:
        record["observation_id"] = "commodity_" + canonical_sha256(
            {key: value for key, value in record.items() if key != "observation_id"}
        )[:32]
    return validate_commodity_observation(record)


def validate_commodity_observation(record: Mapping[str, Any]) -> dict[str, Any]:
    if record.get("schema_version") != COMMODITY_OBSERVATION_SCHEMA_VERSION or record.get("mode") != MODE:
        raise ValueError("commodity observation schema or mode mismatch")
    if not record.get("observation_id") or record.get("status") not in STATUSES:
        raise ValueError("commodity observation identity or status is invalid")
    if any(record.get(key) is not False for key in ("eligible_for_oos_claim", "promotion_allowed", "live_trading_allowed")):
        raise ValueError("commodity observation safety flags must be false")
    canonical_date(record.get("price_date"), field="price_date")
    canonical_date(record.get("as_of_date"), field="as_of_date")
    require_aware_timestamp(record.get("observed_at"), field="observed_at")
    published, precision = canonical_time(record.get("published_at"), field="published_at")
    if published != record.get("published_at") or precision != record.get("published_time_precision"):
        raise ValueError("commodity observation publication precision mismatch")
    if record.get("market_type") not in MARKET_TYPES:
        raise ValueError("commodity observation market type is invalid")
    normalize_evidence_refs(record.get("evidence_refs") or [])
    if record.get("status") == "observed":
        value = record.get("price")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError("observed commodity price is invalid")
        if not record.get("unit") or not record.get("currency") or not record.get("evidence_refs"):
            raise ValueError("observed commodity price metadata is incomplete")
    validate_no_executable_instructions(dict(record), context="commodity price observation")
    return dict(record)


def normalize_commodity_fixture(payload: Mapping[str, Any], *, stale_after_days: int = 7) -> dict[str, Any]:
    source_id = str(payload.get("source_id") or FIXTURE_SOURCE_ID)
    price_date = str(payload.get("price_date") or payload.get("as_of_date") or "")
    as_of_date = str(payload.get("as_of_date") or price_date)
    issues: list[str] = []
    try:
        numeric = float(payload.get("price"))
        if not math.isfinite(numeric) or numeric <= 0:
            raise ValueError
    except (TypeError, ValueError):
        numeric = None
        issues.append("abnormal_price")
    if not payload.get("unit"):
        issues.append("missing_unit")
    if not payload.get("currency"):
        issues.append("missing_currency")
    try:
        refs = normalize_evidence_refs(payload.get("evidence_refs") or [])
    except ValueError:
        refs = []
    if not refs:
        issues.append("missing_evidence_sha")
    if source_id != FIXTURE_SOURCE_ID:
        issues.append("untrusted_fixture_source")
    if price_date and as_of_date:
        price_date = canonical_date(price_date, field="price_date")
        as_of_date = canonical_date(as_of_date, field="as_of_date")
        age = (date.fromisoformat(as_of_date) - date.fromisoformat(price_date)).days
        if age < 0:
            issues.append("future_dated_price")
        elif age > stale_after_days:
            issues.append("stale_data")
    blocking = {"abnormal_price", "missing_evidence_sha", "untrusted_fixture_source"} & set(issues)
    status = "blocked" if blocking else "unknown" if issues else "observed"
    return build_commodity_observation(
        price_date=price_date,
        as_of_date=as_of_date,
        observed_at=payload.get("observed_at"),
        commodity_id=str(payload.get("commodity_id") or "unknown"),
        commodity_name=str(payload.get("commodity_name") or "unknown"),
        unit=str(payload.get("unit")) if payload.get("unit") else None,
        currency=str(payload.get("currency")) if payload.get("currency") else None,
        market_type=str(payload.get("market_type") or "spot"),
        price=numeric,
        source={
            "source_id": FIXTURE_SOURCE_ID,
            "authority_tier": "research_only",
            "source_kind": "commodity_price_fixture",
        },
        source_url_or_path=str(payload.get("source_url_or_path") or "fixture://commodity-price"),
        evidence_refs=refs,
        provider={"provider_id": FIXTURE_SOURCE_ID, "provider_version": COMMODITY_PROVIDER_VERSION},
        published_at=payload.get("published_at") or price_date,
        effective_from=payload.get("effective_from"),
        status=status,
        quality_issues=issues,
        contract_code=payload.get("contract_code"),
        revision_of=payload.get("revision_of"),
        observation_id=payload.get("observation_id"),
    )


class CommodityPriceProvider(Protocol):
    provider_id: str
    provider_version: str

    def fetch(self, *, as_of_date: str) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class BlockedCommodityPriceProvider:
    provider_id: str
    reason: str
    provider_version: str = COMMODITY_PROVIDER_VERSION

    def fetch(self, *, as_of_date: str) -> Mapping[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "as_of_date": canonical_date(as_of_date, field="as_of_date"),
            "status": "blocked",
            "event_state": "unknown_not_no_event",
            "observations": [],
            "reason": self.reason,
            "promotion_allowed": False,
            "live_trading_allowed": False,
        }


@dataclass(frozen=True)
class OfflineCommodityPriceProvider:
    records: Sequence[Mapping[str, Any]]
    provider_id: str = FIXTURE_SOURCE_ID
    provider_version: str = COMMODITY_PROVIDER_VERSION

    def fetch(self, *, as_of_date: str) -> Mapping[str, Any]:
        day = canonical_date(as_of_date, field="as_of_date")
        selected = [normalize_commodity_fixture(row) for row in self.records if row.get("as_of_date") == day]
        return {
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "as_of_date": day,
            "status": "fixture" if selected else "unknown",
            "event_state": "observed" if selected else "unknown_not_no_event",
            "observations": selected,
            "promotion_allowed": False,
            "live_trading_allowed": False,
        }


def build_commodity_observation_ledger(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    validated = [validate_commodity_observation(record) for record in records]
    events: list[dict[str, Any]] = []
    duplicates: list[dict[str, str]] = []
    revisions: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    exact: dict[str, dict[str, Any]] = {}
    logical: dict[str, dict[str, Any]] = {}
    ids: set[str] = set()
    for raw in validated:
        record = dict(raw)
        if record["observation_id"] in ids:
            raise ValueError("commodity ledger contains duplicate observation_id")
        ids.add(record["observation_id"])
        fingerprint = canonical_sha256({key: value for key, value in record.items() if key != "observation_id"})
        if fingerprint in exact:
            duplicates.append({"observation_id": record["observation_id"], "duplicate_of": exact[fingerprint]["observation_id"]})
            continue
        logical_key = canonical_sha256(
            {key: record.get(key) for key in ("price_date", "commodity_id", "market_type", "contract_code")}
            | {"source_id": record["source"].get("source_id")}
        )
        prior = logical.get(logical_key)
        if prior is not None:
            if record.get("revision_of") == prior["observation_id"]:
                revisions.append({"observation_id": record["observation_id"], "revision_of": prior["observation_id"]})
            else:
                record["status"] = "conflict"
                record["conflict_with"] = prior["observation_id"]
                conflicts.append({"observation_id": record["observation_id"], "conflict_with": prior["observation_id"]})
        exact[fingerprint] = record
        logical[logical_key] = record
        events.append(record)
    return {
        "schema_version": COMMODITY_LEDGER_SCHEMA_VERSION,
        "mode": MODE,
        "status": "conflicts_present" if conflicts else "ok",
        "observations": events,
        "duplicates": duplicates,
        "revisions": revisions,
        "conflicts": conflicts,
        "observation_count": len(events),
        "duplicate_count": len(duplicates),
        "revision_count": len(revisions),
        "conflict_count": len(conflicts),
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }


def build_commodity_source_health(results: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = []
    seen: set[str] = set()
    for result in results:
        source_id = str(result.get("provider_id") or "")
        if not source_id or source_id in seen:
            raise ValueError("commodity health requires unique provider identities")
        seen.add(source_id)
        if result.get("event_state") == "no_event":
            raise ValueError("commodity provider failure cannot claim no_event")
        rows.append(
            {
                "source_id": source_id,
                "status": str(result.get("status") or "unknown"),
                "event_state": str(result.get("event_state") or "unknown_not_no_event"),
                "reason": result.get("reason"),
            }
        )
    return {
        "schema_version": "commodity-price-source-health-v1",
        "mode": MODE,
        "status": "blocked_sources_present" if any(row["status"] == "blocked" for row in rows) else "ok",
        "sources": rows,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }


__all__ = [
    "BlockedCommodityPriceProvider",
    "CommodityPriceProvider",
    "OfflineCommodityPriceProvider",
    "archive_commodity_price_evidence",
    "build_commodity_observation",
    "build_commodity_observation_ledger",
    "build_commodity_source_health",
    "commodity_price_source_registry",
    "normalize_commodity_fixture",
    "validate_commodity_observation",
]
