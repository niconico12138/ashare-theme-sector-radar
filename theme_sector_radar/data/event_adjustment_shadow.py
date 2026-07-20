"""Deterministic numeric research over event enhancements, never formal ranking."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import math
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import validate_no_executable_instructions

from .event_enhancement import (
    build_copper_enhancement_research_case,
    validate_event_enhancement,
    validate_event_exposure_mapping,
)
from .official_announcements import DISCLAIMER, MODE
from .risk_event_schema import canonical_json_bytes, canonical_sha256


EVENT_ADJUSTMENT_SHADOW_SCHEMA_VERSION = "event-adjustment-shadow-v1"
PROTECTED_FIELDS = {
    "quant_score", "final_score", "v2_score", "selection_score", "event_score",
    "confidence", "rank", "action", "trade", "order", "position", "target_price",
}
SEVERITY_BANDS = {
    "unknown": ("none", 0.0),
    "info": ("low", 2.0),
    "watch": ("low", 2.0),
    "elevated": ("medium", 4.0),
    "high": ("high", 6.0),
    "critical": ("extreme", 8.0),
}
EXPOSURE_BANDS = {
    "direct": ("high", 1.0),
    "value_chain": ("medium", 0.75),
    "indirect": ("low", 0.5),
    "unknown": ("none", 0.0),
}
PERSISTENCE_FACTORS = {"one_off": 0.6, "temporary": 0.8, "ongoing": 1.0, "unknown": 0.0}
NOVELTY_FACTORS = {"novel": 1.0, "revised": 0.8, "repeat": 0.5, "duplicate": 0.0, "unknown": 0.0}
REFLECTION_FACTORS = {
    "unreflected": 1.0,
    "partially_reflected": 0.5,
    "fully_reflected": 0.0,
    "unknown": 0.0,
}


@dataclass(frozen=True)
class EventAdjustmentShadowConfig:
    sector_min_adjustment: float = -12.0
    sector_max_adjustment: float = 8.0
    stock_min_adjustment: float = -10.0
    stock_max_adjustment: float = 6.0
    default_half_life_days: int = 30

    def validate(self) -> "EventAdjustmentShadowConfig":
        values = (
            self.sector_min_adjustment,
            self.sector_max_adjustment,
            self.stock_min_adjustment,
            self.stock_max_adjustment,
        )
        if any(isinstance(value, bool) or not math.isfinite(float(value)) for value in values):
            raise ValueError("event adjustment caps must be finite numbers")
        if self.sector_min_adjustment > 0 or self.sector_max_adjustment < 0:
            raise ValueError("sector adjustment caps must contain zero")
        if self.stock_min_adjustment > 0 or self.stock_max_adjustment < 0:
            raise ValueError("stock adjustment caps must contain zero")
        if isinstance(self.default_half_life_days, bool) or self.default_half_life_days <= 0:
            raise ValueError("default_half_life_days must be positive")
        return self


def _reject_protected(value: Any, *, path: str = "event_adjustment_shadow") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).casefold()
            if normalized in PROTECTED_FIELDS or normalized.endswith("_score"):
                raise ValueError(f"event adjustment Shadow contains protected field: {path}.{key}")
            _reject_protected(child, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_protected(child, path=f"{path}[{index}]")


def _contains_numeric(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, Mapping):
        return any(_contains_numeric(child) for child in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_numeric(child) for child in value)
    return False


def _quality_factor(enhancement: Mapping[str, Any], exposure: Mapping[str, Any]) -> float:
    quality = enhancement["evidence_quality_view"]
    authority = {"primary": 1.0, "secondary": 0.75, "research_only": 0.5, "unknown": 0.0}.get(
        str(quality.get("authority_tier")), 0.0
    )
    timestamp = {"timestamp": 1.0, "date_only": 0.8, "timestamp_naive": 0.0, "unknown": 0.0}.get(
        str(quality.get("timestamp_quality")), 0.0
    )
    mapping = {"exact": 1.0, "partial": 0.75}.get(str(exposure.get("mapping_quality")), 0.0)
    completeness = 1.0 if quality.get("evidence_completeness") == "complete" else 0.0
    return authority * timestamp * mapping * completeness


def _time_decay(
    enhancement: Mapping[str, Any], exposure: Mapping[str, Any], config: EventAdjustmentShadowConfig,
) -> tuple[float, int, int]:
    as_of = date.fromisoformat(str(enhancement["as_of_date"]))
    valid_from = date.fromisoformat(str(exposure["valid_from"]))
    elapsed = max(0, (as_of - valid_from).days)
    decay = enhancement["lifecycle_view"].get("decay_metadata") or {}
    raw_half_life = decay.get("half_life_days", config.default_half_life_days)
    half_life = int(raw_half_life) if not isinstance(raw_half_life, bool) else config.default_half_life_days
    if half_life <= 0:
        half_life = config.default_half_life_days
    return 0.5 ** (elapsed / half_life), elapsed, half_life


def _reflection_status(enhancement: Mapping[str, Any]) -> str:
    snapshot = enhancement["market_feedback_view"]["as_of_snapshot"]
    if snapshot.get("status") != "observed":
        return "unknown"
    reaction = snapshot.get("pre_event_reaction") or {}
    value = str(reaction.get("reflection_status") or "unknown")
    return value if value in REFLECTION_FACTORS else "unknown"


def _zero_reasons(enhancement: Mapping[str, Any], exposure: Mapping[str, Any]) -> list[str]:
    quality = enhancement["evidence_quality_view"]
    lifecycle = enhancement["lifecycle_view"]
    reasons = []
    if enhancement.get("event_status") != "observed":
        reasons.append(f"event_status_{enhancement.get('event_status')}")
    if quality.get("evidence_completeness") != "complete":
        reasons.append("evidence_incomplete")
    if quality.get("conflict_status") != "clear":
        reasons.append("event_conflict_or_unknown")
    if exposure.get("mapping_quality") not in {"exact", "partial"}:
        reasons.append("mapping_quality_unknown_or_blocked")
    if exposure.get("impact_direction") not in {"positive", "negative"}:
        reasons.append("impact_direction_not_directional")
    if enhancement.get("severity") not in SEVERITY_BANDS or enhancement.get("severity") == "unknown":
        reasons.append("impact_magnitude_unknown")
    if lifecycle.get("duration_type") == "unknown":
        reasons.append("persistence_unknown")
    novelty = str((lifecycle.get("novelty") or {}).get("status") or "unknown")
    if novelty in {"unknown", "duplicate"}:
        reasons.append(f"novelty_{novelty}")
    if _reflection_status(enhancement) == "unknown":
        reasons.append("market_reflection_unknown")
    if quality.get("authority_tier") == "unknown" or quality.get("timestamp_quality") in {"unknown", "timestamp_naive"}:
        reasons.append("evidence_quality_unknown")
    valid_until = exposure.get("valid_until")
    if valid_until and enhancement["as_of_date"] > valid_until:
        reasons.append("exposure_expired")
    return sorted(set(reasons))


def _adjustment_record(
    enhancement: Mapping[str, Any],
    exposure: Mapping[str, Any],
    config: EventAdjustmentShadowConfig,
) -> dict[str, Any]:
    direction = str(exposure["impact_direction"])
    sign = 1.0 if direction == "positive" else -1.0 if direction == "negative" else 0.0
    magnitude_band, magnitude_value = SEVERITY_BANDS.get(str(enhancement.get("severity")), ("none", 0.0))
    exposure_band, exposure_factor = EXPOSURE_BANDS.get(str(exposure.get("exposure_type")), ("none", 0.0))
    duration = str(enhancement["lifecycle_view"].get("duration_type") or "unknown")
    persistence_factor = PERSISTENCE_FACTORS.get(duration, 0.0)
    novelty = str((enhancement["lifecycle_view"].get("novelty") or {}).get("status") or "unknown")
    novelty_factor = NOVELTY_FACTORS.get(novelty, 0.0)
    reflection = _reflection_status(enhancement)
    reflection_factor = REFLECTION_FACTORS.get(reflection, 0.0)
    evidence_factor = _quality_factor(enhancement, exposure)
    decay_factor, elapsed_days, half_life_days = _time_decay(enhancement, exposure, config)
    reasons = _zero_reasons(enhancement, exposure)
    raw_value = 0.0
    if not reasons:
        raw_value = (
            sign * magnitude_value * exposure_factor * persistence_factor
            * evidence_factor * novelty_factor * reflection_factor * decay_factor
        )
    scope = str(exposure["entity_scope"])
    lower, upper = (
        (config.sector_min_adjustment, config.sector_max_adjustment)
        if scope == "sector"
        else (config.stock_min_adjustment, config.stock_max_adjustment)
    )
    value = min(upper, max(lower, raw_value))
    return {
        "logical_event_id": enhancement["logical_event_id"],
        "event_id": enhancement["event_id"],
        "enhancement_id": enhancement["enhancement_id"],
        "mapping_id": exposure["mapping_id"],
        "entity_scope": scope,
        "entity_id": exposure["entity_id"],
        "source_event_scope": enhancement["scope"],
        "source_event_entity_id": enhancement["entity_id"],
        "exposure_type": exposure["exposure_type"],
        "evidence_bundle_id": "evidence_" + canonical_sha256(enhancement["evidence_refs"])[:24],
        "as_of_date": enhancement["as_of_date"],
        "effective_from": enhancement["effective_from"],
        "pit_status": enhancement["pit_status"],
        "impact_direction": direction,
        "value_chain_stage": exposure["value_chain_stage"],
        "adjustment_value": value,
        "cap": {"minimum": lower, "maximum": upper},
        "decomposition": {
            "direction_sign": sign,
            "impact_magnitude_band": magnitude_band,
            "impact_magnitude_value": magnitude_value,
            "exposure_band": exposure_band,
            "exposure_factor": exposure_factor,
            "persistence_type": duration,
            "persistence_factor": persistence_factor,
            "evidence_quality_factor": evidence_factor,
            "novelty_status": novelty,
            "novelty_factor": novelty_factor,
            "market_reflection_status": reflection,
            "market_reflection_factor": reflection_factor,
            "time_decay_factor": decay_factor,
            "elapsed_days": elapsed_days,
            "half_life_days": half_life_days,
            "uncapped_adjustment": raw_value,
        },
        "zero_adjustment_reasons": reasons,
        "manual_review_required": True,
        "research_only": True,
    }


def _select_events(inputs: Sequence[Mapping[str, Any]]) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], list[dict[str, Any]]]:
    grouped: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for item in inputs:
        enhancement = validate_event_enhancement(item.get("enhancement") or {})
        mapping = validate_event_exposure_mapping(item.get("exposure_mapping") or {})
        if mapping.get("enhancement_id") != enhancement["enhancement_id"] or mapping.get("event_id") != enhancement["event_id"]:
            raise ValueError("event adjustment input enhancement/mapping identity mismatch")
        grouped.setdefault(enhancement["logical_event_id"], []).append((enhancement, mapping))
    selected = []
    deduplicated = []
    novelty_priority = {"revised": 4, "novel": 3, "repeat": 2, "unknown": 1, "duplicate": 0}
    for logical_id, candidates in sorted(grouped.items()):
        ordered = sorted(
            candidates,
            key=lambda pair: (
                novelty_priority.get(str(pair[0]["lifecycle_view"]["novelty"].get("status")), 0),
                pair[0]["enhancement_id"],
            ),
            reverse=True,
        )
        selected.append(ordered[0])
        for skipped, _mapping in ordered[1:]:
            deduplicated.append({
                "logical_event_id": logical_id,
                "excluded_enhancement_id": skipped["enhancement_id"],
                "kept_enhancement_id": ordered[0][0]["enhancement_id"],
                "reason": "logical_event_deduplicated",
            })
    return selected, deduplicated


def _select_exposures(exposures: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for raw in exposures:
        exposure = dict(raw)
        grouped.setdefault((str(exposure["entity_scope"]), str(exposure["entity_id"])), []).append(exposure)
    selected = []
    deduplicated = []
    priority = {"direct": 3, "value_chain": 2, "indirect": 1, "unknown": 0}
    for target, candidates in sorted(grouped.items()):
        ordered = sorted(candidates, key=lambda row: (priority.get(str(row.get("exposure_type")), 0), row["mapping_id"]), reverse=True)
        selected.append(ordered[0])
        for skipped in ordered[1:]:
            deduplicated.append({
                "entity_scope": target[0],
                "entity_id": target[1],
                "excluded_mapping_id": skipped["mapping_id"],
                "kept_mapping_id": ordered[0]["mapping_id"],
                "reason": "direct_exposure_preferred_over_transmission",
            })
    return selected, deduplicated


def _deduplicate_direct_company_transmission(
    records: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for raw in records:
        record = dict(raw)
        grouped.setdefault(
            (
                str(record["entity_scope"]),
                str(record["entity_id"]),
                str(record["evidence_bundle_id"]),
            ),
            [],
        ).append(record)
    selected: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for target, candidates in sorted(grouped.items()):
        direct_company = [
            record
            for record in candidates
            if record["entity_scope"] == "individual"
            and record["source_event_scope"] == "individual"
            and record["source_event_entity_id"] == record["entity_id"]
            and record["exposure_type"] == "direct"
        ]
        if not direct_company:
            selected.extend(candidates)
            continue
        kept = sorted(direct_company, key=lambda record: (record["logical_event_id"], record["mapping_id"]))[0]
        selected.append(kept)
        for record in candidates:
            if record is kept:
                continue
            excluded.append({
                "entity_scope": target[0],
                "entity_id": target[1],
                "evidence_bundle_id": target[2],
                "excluded_event_id": record["event_id"],
                "kept_event_id": kept["event_id"],
                "reason": "direct_company_event_preferred_over_sector_transmission",
            })
    return selected, excluded


def build_event_adjustment_shadow(
    inputs: Sequence[Mapping[str, Any]],
    *,
    config: EventAdjustmentShadowConfig | None = None,
) -> dict[str, Any]:
    cfg = (config or EventAdjustmentShadowConfig()).validate()
    selected, event_deduplication = _select_events(inputs)
    sector_records = []
    stock_records = []
    exposure_deduplication = []
    excluded_scopes = []
    cross_event_deduplication = []
    lineage = []
    excluded_post = []
    for enhancement, mapping in selected:
        exposures, exposure_duplicates = _select_exposures(mapping["exposures"])
        exposure_deduplication.extend(exposure_duplicates)
        allowed_projection = {
            "logical_event_id": enhancement["logical_event_id"],
            "event_id": enhancement["event_id"],
            "event_status": enhancement["event_status"],
            "severity": enhancement["severity"],
            "event_time": enhancement["event_time"],
            "effective_from": enhancement["effective_from"],
            "pit_status": enhancement["pit_status"],
            "as_of_date": enhancement["as_of_date"],
            "fact_view": enhancement["fact_view"],
            "lifecycle_view": enhancement["lifecycle_view"],
            "evidence_quality_view": enhancement["evidence_quality_view"],
            "market_as_of_snapshot": enhancement["market_feedback_view"]["as_of_snapshot"],
            "evidence_refs": enhancement["evidence_refs"],
            "exposures": exposures,
        }
        lineage.append({
            "logical_event_id": enhancement["logical_event_id"],
            "enhancement_id": enhancement["enhancement_id"],
            "exposure_mapping_id": mapping["mapping_id"],
            "as_of_date": enhancement["as_of_date"],
            "effective_from": enhancement["effective_from"],
            "pit_status": enhancement["pit_status"],
            "adjustment_input_sha256": canonical_sha256(allowed_projection),
            "included_views": ["fact_view", "lifecycle_view", "evidence_quality_view", "market_as_of_snapshot", "exposures"],
            "post_event_backtest_included": False,
        })
        post = enhancement["market_feedback_view"]["post_event_backtest"]
        excluded_post.append({
            "enhancement_id": enhancement["enhancement_id"],
            "excluded": True,
            "status": post.get("status"),
            "contained_numeric_metadata": _contains_numeric({
                "post_event_reaction": post.get("post_event_reaction"),
                "breadth_propagation": post.get("breadth_propagation"),
            }),
            "payload_sha256": canonical_sha256(post),
            "reason": "post_event_backtest_never_enters_adjustment_lineage",
        })
        for exposure in exposures:
            if exposure["entity_scope"] not in {"sector", "individual"}:
                excluded_scopes.append({
                    "mapping_id": exposure["mapping_id"],
                    "entity_scope": exposure["entity_scope"],
                    "reason": "only_sector_and_stock_adjustment_views_are_emitted",
                })
                continue
            record = _adjustment_record(enhancement, exposure, cfg)
            if exposure["entity_scope"] == "sector":
                sector_records.append(record)
            else:
                stock_records.append(record)
    stock_records, cross_event_deduplication = _deduplicate_direct_company_transmission(stock_records)
    artifact = {
        "schema_version": EVENT_ADJUSTMENT_SHADOW_SCHEMA_VERSION,
        "mode": MODE,
        "artifact_type": "event_adjustment_shadow",
        "status": "research_complete" if inputs else "unknown_no_inputs",
        "research_only": True,
        "config": asdict(cfg),
        "as_of_dates": sorted({
            str(enhancement["as_of_date"])
            for enhancement, _mapping in selected
        }),
        "effective_from_dates": sorted({
            str(enhancement["effective_from"])
            for enhancement, _mapping in selected
            if enhancement.get("effective_from") is not None
        }),
        "pit_statuses": sorted({
            str(enhancement["pit_status"])
            for enhancement, _mapping in selected
        }),
        "adjustment_lineage": lineage,
        "excluded_post_event_backtests": excluded_post,
        "event_deduplication": event_deduplication,
        "exposure_deduplication": exposure_deduplication,
        "cross_event_deduplication": cross_event_deduplication,
        "excluded_scope_mappings": excluded_scopes,
        "sector_event_adjustment_shadow": sector_records,
        "stock_event_adjustment_shadow": stock_records,
        "manual_review_required": True,
        "formal_ranking_allowed": False,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    return validate_event_adjustment_shadow(artifact)


def validate_event_adjustment_shadow(artifact: Mapping[str, Any]) -> dict[str, Any]:
    if artifact.get("schema_version") != EVENT_ADJUSTMENT_SHADOW_SCHEMA_VERSION or artifact.get("mode") != MODE:
        raise ValueError("event adjustment Shadow schema or mode mismatch")
    if artifact.get("artifact_type") != "event_adjustment_shadow" or artifact.get("research_only") is not True:
        raise ValueError("event adjustment Shadow must remain research_only")
    if any(artifact.get(key) is not False for key in ("formal_ranking_allowed", "eligible_for_oos_claim", "promotion_allowed", "live_trading_allowed")):
        raise ValueError("event adjustment Shadow safety flags must be false")
    config = EventAdjustmentShadowConfig(**dict(artifact.get("config") or {})).validate()
    for key, lower, upper in (
        ("sector_event_adjustment_shadow", config.sector_min_adjustment, config.sector_max_adjustment),
        ("stock_event_adjustment_shadow", config.stock_min_adjustment, config.stock_max_adjustment),
    ):
        records = artifact.get(key)
        if not isinstance(records, list):
            raise ValueError("event adjustment Shadow output views are missing")
        for record in records:
            value = record.get("adjustment_value")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("event adjustment value must be finite")
            if not lower <= value <= upper:
                raise ValueError("event adjustment value exceeds configured cap")
            if record.get("zero_adjustment_reasons") and value != 0:
                raise ValueError("fail-closed adjustment must be zero")
    for row in artifact.get("adjustment_lineage") or []:
        if row.get("post_event_backtest_included") is not False:
            raise ValueError("post-event backtest entered adjustment lineage")
        if "post_event" in canonical_json_bytes(row).decode("utf-8") and "post_event_backtest_included" not in row:
            raise ValueError("post-event values entered adjustment lineage")
    for row in artifact.get("excluded_post_event_backtests") or []:
        if row.get("excluded") is not True:
            raise ValueError("post-event backtest exclusion marker is missing")
    _reject_protected(artifact)
    validate_no_executable_instructions(dict(artifact), context="event adjustment Shadow")
    canonical_json_bytes(dict(artifact))
    return dict(artifact)


def build_copper_adjustment_research_case() -> dict[str, Any]:
    fresh_case = build_copper_enhancement_research_case(as_of_date="2026-07-20")
    decayed_case = build_copper_enhancement_research_case(as_of_date="2026-08-04")
    fresh = build_event_adjustment_shadow([{
        "enhancement": fresh_case["event_enhancement"],
        "exposure_mapping": fresh_case["event_exposure_mapping"],
    }])
    decayed = build_event_adjustment_shadow([{
        "enhancement": decayed_case["event_enhancement"],
        "exposure_mapping": decayed_case["event_exposure_mapping"],
    }])
    return {
        "schema_version": "event-adjustment-copper-research-v1",
        "mode": MODE,
        "status": "fixture_complete",
        "research_only": True,
        "fresh": fresh,
        "decayed": decayed,
        "formal_ranking_allowed": False,
        "promotion_allowed": False,
        "live_trading_allowed": False,
        "disclaimer": DISCLAIMER,
    }


__all__ = [
    "EVENT_ADJUSTMENT_SHADOW_SCHEMA_VERSION",
    "EventAdjustmentShadowConfig",
    "build_copper_adjustment_research_case",
    "build_event_adjustment_shadow",
    "validate_event_adjustment_shadow",
]
