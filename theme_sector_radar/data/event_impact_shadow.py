"""Evidence-bound event-to-sector impact mapping for paper Shadow research."""

from __future__ import annotations

from datetime import date
import hashlib
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import validate_no_executable_instructions

from .commodity_prices import normalize_commodity_fixture, validate_commodity_observation
from .official_announcements import DISCLAIMER, MODE
from .risk_event_schema import (
    build_risk_event,
    canonical_date,
    canonical_sha256,
    normalize_evidence_refs,
    validate_risk_event,
)


EVENT_IMPACT_SHADOW_SCHEMA_VERSION = "event-impact-shadow-v1"
EVENT_IMPACT_PROVIDER_VERSION = "manual-evidence-mapping-v1"
STAGES = {"upstream", "midstream", "downstream"}
DIRECTIONS = {"positive", "negative", "mixed", "unknown"}
PROTECTED_FIELDS = {
    "quant_score",
    "final_score",
    "v2_score",
    "selection_score",
    "direction_score",
    "score",
    "rank",
    "confidence",
    "action",
    "trade",
    "order",
    "position",
    "target_price",
}


def _reject_protected_fields(value: Any, *, path: str = "event_impact_shadow") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).casefold()
            if normalized in PROTECTED_FIELDS or normalized.endswith("_score"):
                raise ValueError(f"event impact Shadow contains protected field: {path}.{key}")
            _reject_protected_fields(child, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_protected_fields(child, path=f"{path}[{index}]")


def build_commodity_price_change_event(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    *,
    threshold_pct: float = 0.05,
) -> dict[str, Any]:
    left = validate_commodity_observation(previous)
    right = validate_commodity_observation(current)
    if left["status"] != "observed" or right["status"] != "observed":
        raise ValueError("commodity change requires two observed price records")
    identity_fields = ("commodity_id", "unit", "currency", "market_type", "contract_code")
    if any(left.get(field) != right.get(field) for field in identity_fields):
        raise ValueError("commodity change inputs have incompatible identities")
    if left["price_date"] >= right["price_date"]:
        raise ValueError("commodity change dates are not chronological")
    prior_value = float(left["price"])
    current_value = float(right["price"])
    change_pct = current_value / prior_value - 1.0
    if change_pct >= threshold_pct:
        event_type, severity = "commodity_price_increase", "elevated"
    elif change_pct <= -threshold_pct:
        event_type, severity = "commodity_price_decrease", "elevated"
    else:
        event_type, severity = "commodity_price_change_below_threshold", "info"
    return build_risk_event(
        event_type=event_type,
        scope="market",
        entity_id=right["commodity_id"],
        event_time=right["price_date"],
        published_at=right["published_at"],
        effective_from=right["effective_from"],
        as_of_date=right["as_of_date"],
        observed_at=right["observed_at"],
        severity=severity,
        status="observed",
        source=right["source"],
        evidence_refs=normalize_evidence_refs([*left["evidence_refs"], *right["evidence_refs"]]),
        detector={
            "detector_id": "commodity_price_change_detector",
            "detector_version": "commodity-price-change-v1",
            "mode": "deterministic",
        },
        provider=None,
        structured_fields={
            "commodity_id": right["commodity_id"],
            "commodity_name": right["commodity_name"],
            "prior_value": prior_value,
            "current_value": current_value,
            "change_pct": change_pct,
            "threshold_pct": threshold_pct,
            "unit": right["unit"],
            "currency": right["currency"],
            "market_type": right["market_type"],
        },
        provenance={
            "method": "two_observation_deterministic_change",
            "previous_observation_id": left["observation_id"],
            "current_observation_id": right["observation_id"],
        },
    )


def map_event_impact_shadow(
    event: Mapping[str, Any],
    mapping_rules: Sequence[Mapping[str, Any]],
    *,
    as_of_date: str,
    valid_from: str,
    valid_to: str | None = None,
    half_life_days: int = 30,
) -> dict[str, Any]:
    source_event = validate_risk_event(event)
    as_of = canonical_date(as_of_date, field="as_of_date")
    start = canonical_date(valid_from, field="valid_from")
    end = canonical_date(valid_to, field="valid_to") if valid_to else None
    if end is not None and end < start:
        raise ValueError("event impact validity range is inverted")
    if isinstance(half_life_days, bool) or half_life_days <= 0:
        raise ValueError("event impact half_life_days must be positive")
    impacts: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for index, raw in enumerate(mapping_rules):
        stage = str(raw.get("industry_stage") or "")
        direction = str(raw.get("impact_direction") or "")
        sector_id = str(raw.get("sector_id") or "")
        sector_name = str(raw.get("sector_name") or "")
        evidence = normalize_evidence_refs(raw.get("evidence_refs") or source_event["evidence_refs"])
        missing = [
            name
            for name, value in (
                ("sector_id", sector_id),
                ("sector_name", sector_name),
                ("industry_stage", stage if stage in STAGES else ""),
                ("impact_direction", direction if direction in DIRECTIONS else ""),
                ("evidence_refs", evidence),
            )
            if not value
        ]
        if missing:
            blocked.append({"mapping_index": index, "status": "unknown", "missing_fields": missing})
            continue
        impacts.append(
            {
                "sector_id": sector_id,
                "sector_name": sector_name,
                "industry_stage": stage,
                "impact_direction": direction,
                "rationale_code": str(raw.get("rationale_code") or "manual_evidence_mapping"),
                "evidence_refs": evidence,
                "valid_from": start,
                "valid_to": end,
                "decay_metadata": {
                    "method": "exponential_metadata_only",
                    "half_life_days": int(half_life_days),
                    "starts_at": start,
                    "computed_value": None,
                },
                "requires_human_review": True,
            }
        )
    status = "observed" if impacts and not blocked else "partial_unknown" if impacts else "unknown"
    artifact = {
        "schema_version": EVENT_IMPACT_SHADOW_SCHEMA_VERSION,
        "mode": MODE,
        "artifact_type": "event_impact_shadow",
        "impact_id": "impact_" + canonical_sha256(
            {"event_id": source_event["event_id"], "as_of_date": as_of, "rules": list(mapping_rules)}
        )[:32],
        "status": status,
        "source_event_id": source_event["event_id"],
        "source_event_schema_version": source_event["schema_version"],
        "as_of_date": as_of,
        "mapping_provider": {
            "provider_id": "manual_evidence_mapping_shadow",
            "provider_version": EVENT_IMPACT_PROVIDER_VERSION,
        },
        "impacts": impacts,
        "blocked_mappings": blocked,
        "requires_human_review": True,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    return validate_event_impact_shadow(artifact)


def validate_event_impact_shadow(artifact: Mapping[str, Any]) -> dict[str, Any]:
    if artifact.get("schema_version") != EVENT_IMPACT_SHADOW_SCHEMA_VERSION or artifact.get("mode") != MODE:
        raise ValueError("event impact Shadow schema or mode mismatch")
    if artifact.get("artifact_type") != "event_impact_shadow" or not artifact.get("impact_id"):
        raise ValueError("event impact Shadow identity is missing")
    if artifact.get("status") not in {"observed", "partial_unknown", "unknown"}:
        raise ValueError("event impact Shadow status is invalid")
    if any(artifact.get(key) is not False for key in ("eligible_for_oos_claim", "promotion_allowed", "live_trading_allowed")):
        raise ValueError("event impact Shadow safety flags must be false")
    _reject_protected_fields(artifact)
    validate_no_executable_instructions(dict(artifact), context="event impact Shadow")
    return dict(artifact)


def build_copper_increase_research_case() -> dict[str, Any]:
    """Explicit research-only fixture showing opposite value-chain directions."""

    def evidence(label: str) -> list[dict[str, str]]:
        return [{
            "evidence_id": label,
            "sha256": hashlib.sha256(label.encode("ascii")).hexdigest(),
            "kind": "research_fixture",
            "source_id": "commodity_price_research_fixture",
        }]

    common = {
        "as_of_date": "2026-07-20",
        "observed_at": "2026-07-20T16:00:00+08:00",
        "commodity_id": "copper_cathode",
        "commodity_name": "Copper cathode",
        "unit": "CNY/metric_ton",
        "currency": "CNY",
        "market_type": "spot",
        "effective_from": "2026-07-20",
    }
    previous = normalize_commodity_fixture({
        **common,
        "price_date": "2026-07-13",
        "published_at": "2026-07-13",
        "price": 100.0,
        "evidence_refs": evidence("copper-fixture-previous"),
    }, stale_after_days=30)
    current = normalize_commodity_fixture({
        **common,
        "price_date": "2026-07-20",
        "published_at": "2026-07-20",
        "price": 110.0,
        "evidence_refs": evidence("copper-fixture-current"),
    }, stale_after_days=30)
    event = build_commodity_price_change_event(previous, current)
    impact = map_event_impact_shadow(
        event,
        [
            {
                "sector_id": "sw_nonferrous_copper",
                "sector_name": "Copper producers",
                "industry_stage": "upstream",
                "impact_direction": "positive",
                "rationale_code": "output_price_increase",
            },
            {
                "sector_id": "sw_electrical_cable",
                "sector_name": "Cable consumers",
                "industry_stage": "downstream",
                "impact_direction": "negative",
                "rationale_code": "input_cost_increase",
            },
        ],
        as_of_date="2026-07-20",
        valid_from="2026-07-20",
        valid_to="2026-08-19",
        half_life_days=15,
    )
    return {
        "schema_version": "commodity-increase-research-case-v1",
        "mode": MODE,
        "status": "fixture_complete",
        "research_only": True,
        "observations": [previous, current],
        "risk_event": event,
        "event_impact_shadow": impact,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }


__all__ = [
    "build_commodity_price_change_event",
    "build_copper_increase_research_case",
    "map_event_impact_shadow",
    "validate_event_impact_shadow",
]
