"""Policy helpers for joint decision classification."""

from __future__ import annotations

from typing import Any

from theme_sector_radar.factors.access import get_factor_value


def safe_float(value: Any, default: float | None = 0.0) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def first_value(row: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None and value != "":
            return value
    return default


def build_agent_lookup(aihf_ranking: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for item in aihf_ranking.get("items", []):
        code = str(item.get("code", "")).strip()
        if code:
            lookup[code] = item
    return lookup


def classify_agent_review(candidate: dict[str, Any], agent_item: dict[str, Any] | None) -> dict[str, Any]:
    if not agent_item:
        return {
            "agent_review_state": "missing",
            "agent_score": None,
            "risk_adjusted_score": None,
            "risk_level": "unknown",
            "contributing_agents": 0,
        }

    agent_score = safe_float(agent_item.get("agent_score"), None)
    risk_adjusted = safe_float(agent_item.get("risk_adjusted_score"), None)
    risk_level = str(agent_item.get("risk_level", "unknown") or "unknown")
    contributing = int(safe_float(agent_item.get("contributing_agents"), 0) or 0)

    if risk_level in {"high", "severe"}:
        state = "risk_flagged"
    elif agent_score is not None and agent_score >= 70:
        state = "confirmed"
    elif agent_score is not None and agent_score < 45:
        state = "conflicted"
    else:
        state = "reviewed"

    return {
        "agent_review_state": state,
        "agent_score": agent_score,
        "risk_adjusted_score": risk_adjusted,
        "risk_level": risk_level,
        "contributing_agents": contributing,
    }


def classify_sector(row: dict[str, Any]) -> dict[str, Any]:
    score = safe_float(first_value(row, "ranking_score", "concept_final_rank_score", "score"), 0.0) or 0.0
    trend = safe_float(first_value(row, "trend_continuation_score", "trend_score", "sector_trend_score"), None)
    burst = safe_float(first_value(row, "short_term_burst_score", "burst_score", "sector_burst_score"), None)
    confidence = safe_float(first_value(row, "confidence_score", "confidence"), 0.0) or 0.0
    label = str(first_value(row, "consensus_label", "agent_consensus_label", "agent_label", "label", default="") or "")

    if label in {"weak_or_avoid", "avoid", "insufficient_data"}:
        bucket = "avoid"
    elif label == "conflicted":
        bucket = "review"
    elif burst is not None and burst >= 70 and (trend is None or trend < 65):
        bucket = "short_burst_watch"
    elif score >= 65 or (trend is not None and trend >= 65) or label in {"strong_consensus", "trend_confirmed"}:
        bucket = "primary_watch"
    else:
        bucket = "review"

    return {
        "sector_name": str(first_value(row, "sector_name", "name", "industry", "concept", default="-")),
        "sector_type": str(first_value(row, "sector_type", default="unknown")),
        "ranking_score": round(score, 2),
        "sector_trend_score": round(trend, 2) if trend is not None else None,
        "sector_burst_score": round(burst, 2) if burst is not None else None,
        "confidence": round(confidence, 4),
        "consensus_label": label or "unknown",
        "decision_bucket": bucket,
        "reason_codes": _sector_reason_codes(score, trend, burst, label),
    }


def _sector_reason_codes(
    score: float,
    trend: float | None,
    burst: float | None,
    label: str,
) -> list[str]:
    reasons: list[str] = []
    if score >= 65:
        reasons.append("sector_score_strong")
    if trend is not None and trend >= 65:
        reasons.append("sector_trend_strong")
    if burst is not None and burst >= 70:
        reasons.append("sector_burst_strong")
    if label:
        reasons.append(f"sector_label_{label}")
    return reasons or ["sector_context_available"]


def normalize_stock(
    candidate: dict[str, Any],
    agent_lookup: dict[str, dict[str, Any]],
    source_pool: str,
) -> dict[str, Any]:
    code = str(first_value(candidate, "code", "stock_code", "symbol", default="") or "")
    final_score = safe_float(candidate.get("final_score"), None)
    v2_score = safe_float(
        first_value(candidate, "v2_score", "factor_composite_shadow_score_v2"),
        None,
    )
    sector_support = get_factor_value(candidate, "sector_support_score", prefer="score")
    selection_score = safe_float(candidate.get("selection_score"), None)
    selection_score_adjusted = safe_float(candidate.get("selection_score_adjusted"), None)
    agent_review = classify_agent_review(candidate, agent_lookup.get(code))

    opportunity_type = infer_opportunity_type(candidate, source_pool, final_score, v2_score)
    bucket = stock_bucket_for(opportunity_type)

    return {
        "code": code,
        "name": str(first_value(candidate, "name", "stock_name", default="") or ""),
        "sector_name": str(first_value(candidate, "sector_name", "industry", "concept_name", "board_name", default="-") or "-"),
        "source_pool": source_pool,
        "opportunity_type": opportunity_type,
        "decision_bucket": bucket,
        "final_score": final_score,
        "v2_score": v2_score,
        "sector_support_score": sector_support,
        "factor_snapshot": candidate.get("factor_snapshot"),
        "scores": {
            "final_score": final_score,
            "v2_score": v2_score,
            "selection_score": selection_score,
            "selection_score_adjusted": selection_score_adjusted,
        },
        "factor_states": build_factor_states(candidate, opportunity_type, sector_support),
        "agent_review_state": agent_review["agent_review_state"],
        "agent_score": agent_review["agent_score"],
        "risk_adjusted_score": agent_review["risk_adjusted_score"],
        "risk_level": agent_review["risk_level"],
        "contributing_agents": agent_review["contributing_agents"],
        "reason_codes": stock_reason_codes(candidate, opportunity_type, sector_support, agent_review),
        "invalidation_flags": build_invalidation_flags(candidate, agent_review),
        "manual_review_reason": build_manual_review_reason(agent_review),
        "action_state": "watch_only",
    }


def build_factor_states(
    candidate: dict[str, Any],
    opportunity_type: str,
    sector_support: float | None,
) -> dict[str, str]:
    return {
        "trend_state": opportunity_type,
        "sector_support": _sector_support_state(sector_support),
        "breakout_structure": _breakout_state(get_factor_value(candidate, "breakout_distance_20", prefer="raw_value")),
        "drawdown_state": _drawdown_state(get_factor_value(candidate, "drawdown_depth_20", prefer="raw_value")),
        "liquidity_state": _liquidity_state(get_factor_value(candidate, "liquidity_score", prefer="raw_value")),
        "overheat_state": _overheat_state(get_factor_value(candidate, "chasing_risk_score", prefer="raw_value")),
    }


def _sector_support_state(score: float | None) -> str:
    if score is None:
        return "unknown"
    if score >= 65:
        return "confirmed"
    if score >= 50:
        return "neutral"
    return "weak"


def _breakout_state(distance: float | None) -> str:
    if distance is None:
        return "unknown"
    if distance <= 0:
        return "breakout"
    if distance <= 3:
        return "near_breakout"
    if distance <= 10:
        return "neutral_distance"
    return "extended_distance"


def _drawdown_state(depth: float | None) -> str:
    if depth is None:
        return "unknown"
    if depth <= 5:
        return "controlled"
    if depth <= 15:
        return "elevated"
    return "deep"


def _liquidity_state(score: float | None) -> str:
    if score is None:
        return "unknown"
    if score >= 50:
        return "available"
    return "thin"


def _overheat_state(score: float | None) -> str:
    if score is None:
        return "unknown"
    if score >= 70:
        return "high"
    if score >= 40:
        return "elevated"
    return "normal"


def build_invalidation_flags(candidate: dict[str, Any], agent_review: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    liquidity = get_factor_value(candidate, "liquidity_score", prefer="raw_value")
    if liquidity is None:
        liquidity = 100.0
    if agent_review["agent_review_state"] == "risk_flagged":
        flags.append("agent_risk_flagged")
    if liquidity is not None and liquidity < 30:
        flags.append("liquidity_thin")
    return flags


def build_manual_review_reason(agent_review: dict[str, Any]) -> list[str]:
    state = agent_review["agent_review_state"]
    if state in {"conflicted", "risk_flagged"}:
        return [f"agent_{state}"]
    return []


def infer_opportunity_type(
    candidate: dict[str, Any],
    source_pool: str,
    final_score: float | None,
    v2_score: float | None,
) -> str:
    explicit = candidate.get("opportunity_type")
    if explicit:
        return str(explicit)
    signal = candidate.get("signal_type") or candidate.get("reason")
    if signal == "low_final_high_v2":
        return "v2_recovery"
    if signal == "high_final_low_v2":
        return "divergence_review"
    if source_pool == "burst_top":
        return "short_burst"
    if final_score is not None and final_score >= 55:
        return "trend_follow"
    if v2_score is not None and v2_score >= 60:
        return "v2_recovery"
    return "blocked"


def stock_bucket_for(opportunity_type: str) -> str:
    mapping = {
        "trend_follow": "core_watch",
        "consensus_confirmed": "core_watch",
        "sector_confirmed": "core_watch",
        "v2_recovery": "v2_opportunity",
        "short_burst": "short_burst",
        "divergence_review": "divergence_review",
        "blocked": "blocked",
    }
    return mapping.get(opportunity_type, "blocked")


def stock_reason_codes(
    candidate: dict[str, Any],
    opportunity_type: str,
    sector_support: float | None,
    agent_review: dict[str, Any],
) -> list[str]:
    reasons = [opportunity_type]
    if sector_support is not None and sector_support >= 65:
        reasons.append("sector_support_confirmed")
    if agent_review["agent_review_state"] == "confirmed":
        reasons.append("agent_confirmed")
    elif agent_review["agent_review_state"] == "conflicted":
        reasons.append("agent_conflicted")
    elif agent_review["agent_review_state"] == "risk_flagged":
        reasons.append("agent_risk_flagged")
    if candidate.get("factor_snapshot"):
        reasons.append("factor_snapshot_available")
    return reasons



