"""Selection quality watchlist classification."""


from __future__ import annotations

from typing import Any

from theme_sector_radar.factors.access import get_factor_value
from theme_sector_radar.factors.calculators import calculate_intraday_factors


INTRADAY_ATOMIC_FACTOR_IDS = [
    "late_return_30m_score",
    "late_vwap_support_score",
    "late_volume_share_score",
    "late_high_near_close_score",
    "high_to_close_drawdown_score",
    "morning_spike_fade_score",
    "afternoon_fade_score",
    "max_gain_giveback_ratio",
    "close_vs_vwap_score",
    "late_price_above_vwap_ratio",
    "vwap_slope_score",
    "vwap_reclaim_score",
    "volume_without_price_progress_risk",
    "late_volume_efficiency_score",
    "amount_acceleration_score",
    "volume_spike_exhaustion_score",
    "opening_drive_score",
    "morning_strength_persist_score",
    "morning_pullback_repair_score",
    "open_to_midday_resilience_score",
    "sector_intraday_breadth_change",
    "sector_late_breadth_score",
    "leader_follower_sync_score",
    "stock_vs_sector_intraday_alpha",
]

SHORT_BURST_NEWS_EMOTION_FACTOR_IDS = [
    "market_short_emotion_score",
    "limit_up_breadth_score",
    "limit_up_failure_risk",
    "leader_continuation_score",
    "short_burst_environment_score",
    "crowding_heat_score",
    "news_heat_score",
    "policy_catalyst_score",
    "earnings_catalyst_score",
    "event_freshness_score",
    "event_continuation_score",
    "negative_news_risk_score",
    "rumor_hype_risk_score",
    "short_burst_news_emotion_score_shadow",
]


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert to float with a default fallback."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ============================================================
# Sector Support Adjustment Policy (缁楊兛绨╅崡浣风闂冭埖顔?
# ============================================================

SECTOR_SUPPORT_ADJUSTMENT_POLICY = {
    "trend_follow": "enable_adjustment",
    "short_burst": "disable_adjustment",
    "blocked": "disable_adjustment",
    "divergence_review": "display_only",
    "v2_recovery": "display_only",
    "consensus_confirmed": "display_only",
    "unknown": "display_only",
}


def _infer_opportunity_type(candidate: dict, source_pool_override: str | None = None) -> str:
    """Infer opportunity type from candidate fields."""
    # 娴兼ê鍘涙禒?candidate 閻╁瓨甯寸拠璇插絿
    opportunity_type = candidate.get("opportunity_type")
    if opportunity_type:
        return opportunity_type

    # 娴?selection_bucket 閹恒劍鏌?
    selection_bucket = candidate.get("selection_bucket", "")
    if selection_bucket == "v2_opportunity":
        return "v2_recovery"
    elif selection_bucket == "divergence_review":
        return "divergence_review"
    elif selection_bucket == "blocked":
        return "blocked"
    elif selection_bucket == "core_watch":
        return "trend_follow"

    # 娴?source_pool 閹恒劍鏌?
    source_pool = source_pool_override or candidate.get("source_pool", "")
    if source_pool == "v2_potential":
        return "v2_recovery"
    elif source_pool in ("burst_top", "burst"):
        return "short_burst"
    elif source_pool in ("trend_top", "trend"):
        return "trend_follow"

    # 娴?signal_type 閹恒劍鏌?
    signal_type = candidate.get("signal_type", "")
    if signal_type == "low_final_high_v2":
        return "v2_recovery"
    elif signal_type == "high_final_low_v2":
        return "divergence_review"

    return "unknown"


def _calculate_sector_support_delta(
    sector_support_score: float | None,
    policy: str,
) -> tuple[float, bool, str]:
    """Calculate sector-support adjustment delta."""
    if policy == "enable_adjustment":
        if sector_support_score is None:
            return 0.0, False, "sector_support_score missing"

        sector_support_val = _safe_float(sector_support_score)
        if sector_support_val >= 75:
            return 5.0, True, "trend_follow sector_support strong"
        elif sector_support_val >= 65:
            return 3.0, True, "trend_follow sector_support moderate"
        elif sector_support_val < 40:
            return -5.0, True, "trend_follow sector_support very_weak"
        elif sector_support_val < 50:
            return -3.0, True, "trend_follow sector_support weak"
        else:
            return 0.0, False, "trend_follow sector_support neutral"

    elif policy == "disable_adjustment":
        return 0.0, False, f"disabled for {policy}"

    elif policy == "display_only":
        return 0.0, False, f"display_only for {policy}"

    else:
        return 0.0, False, "policy unknown"


def _factor_score(candidate: dict, factor_id: str, *, prefer: str = "score") -> float | None:
    value = get_factor_value(candidate, factor_id, prefer=prefer)
    if value is None:
        return None
    return _safe_float(value)


def _neutral_if_missing(value: float | None) -> float:
    return 50.0 if value is None else value


def _sector_key(candidate: dict) -> str:
    for key in ("sector_name", "sector", "industry_name", "industry"):
        value = candidate.get(key)
        if value:
            return str(value)
    return "__unknown__"


def _peer_rank_basis(candidate: dict) -> float:
    trend = _factor_score(candidate, "stock_trend_score")
    final = _factor_score(candidate, "final_score")
    if trend is not None and final is not None:
        return trend * 0.7 + final * 0.3
    if trend is not None:
        return trend
    if final is not None:
        return final
    return 50.0


def annotate_sector_peer_rank_scores(candidates: list[dict]) -> list[dict]:
    """Add same-sector peer rank scores without changing official scores."""
    groups: dict[str, list[dict]] = {}
    for candidate in candidates:
        groups.setdefault(_sector_key(candidate), []).append(candidate)

    for group in groups.values():
        if len(group) == 1:
            group[0]["sector_peer_rank_score"] = 50.0
            continue

        ranked = sorted(group, key=_peer_rank_basis, reverse=True)
        denominator = max(1, len(ranked) - 1)
        for rank, candidate in enumerate(ranked):
            candidate["sector_peer_rank_score"] = round(100.0 * (denominator - rank) / denominator, 2)
    return candidates


def _mean_factor(candidates: list[dict], factor_id: str) -> float | None:
    values = []
    for candidate in candidates:
        value = _factor_score(candidate, factor_id, prefer="score")
        if value is None:
            value = _factor_score(candidate, factor_id, prefer="raw_value")
        if value is not None:
            values.append(value)
    if not values:
        return None
    return sum(values) / len(values)


def annotate_market_regime_scores(candidates: list[dict]) -> list[dict]:
    """Add same-day market regime scores derived from the candidate pool."""
    if not candidates:
        return candidates

    stock_trend = _mean_factor(candidates, "stock_trend_score")
    sector_support = _mean_factor(candidates, "sector_support_score")
    trend_persistence = _mean_factor(candidates, "trend_persistence_score")
    risk_adjusted_return = _mean_factor(candidates, "risk_adjusted_return_20")

    score = (
        0.40 * _neutral_if_missing(stock_trend)
        + 0.30 * _neutral_if_missing(sector_support)
        + 0.20 * _neutral_if_missing(trend_persistence)
        + 0.10 * _neutral_if_missing(risk_adjusted_return)
    )
    diagnostics = {
        "stock_trend_score_avg": None if stock_trend is None else round(stock_trend, 2),
        "sector_support_score_avg": None if sector_support is None else round(sector_support, 2),
        "trend_persistence_score_avg": None if trend_persistence is None else round(trend_persistence, 2),
        "risk_adjusted_return_20_avg": None if risk_adjusted_return is None else round(risk_adjusted_return, 2),
    }
    for candidate in candidates:
        candidate["market_regime_score"] = round(score, 2)
        candidate["market_regime_components"] = diagnostics
    return candidates


def _average_present(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    if not present:
        return None
    return sum(present) / len(present)


def _regime_from_score(score: float, *, weak_cutoff: float = 52.0, fading_cutoff: float = 58.0) -> str:
    if score < weak_cutoff:
        return "risk_off"
    if score < fading_cutoff:
        return "neutral"
    return "risk_on"


def _sector_regime_from_score(score: float) -> str:
    if score < 45:
        return "weak"
    if score < 55:
        return "fading"
    if score < 68:
        return "stable"
    return "leading"


def _calculate_market_gate(candidate: dict) -> dict:
    explicit_score = _factor_score(candidate, "market_regime_score")
    components = {
        "market_regime_score": explicit_score,
        "trend_persistence_score": _factor_score(candidate, "trend_persistence_score"),
        "risk_adjusted_return_20": _factor_score(candidate, "risk_adjusted_return_20"),
        "relative_strength_20": _factor_score(candidate, "relative_strength_20"),
        "volume_stability_score": _factor_score(candidate, "volume_stability_score"),
    }
    score = explicit_score
    if score is None:
        score = _average_present(list(components.values()))
    if score is None:
        score = 55.0

    regime = _regime_from_score(score)
    penalty = 0.0
    if any(value is not None for value in components.values()) or explicit_score is not None:
        if regime == "risk_off":
            penalty = 8.0
        elif regime == "neutral":
            penalty = 3.0

    return {
        "regime": regime,
        "score": round(score, 2),
        "penalty": round(penalty, 2),
        "components": {key: None if value is None else round(value, 2) for key, value in components.items()},
    }


def _calculate_sector_gate(candidate: dict) -> dict:
    explicit_score = _factor_score(candidate, "sector_regime_score")
    components = {
        "sector_support_score": _factor_score(candidate, "sector_support_score"),
        "sector_trend_score": _factor_score(candidate, "sector_trend_score"),
        "sector_peer_rank_score": _factor_score(candidate, "sector_peer_rank_score"),
        "relative_strength_60": _factor_score(candidate, "relative_strength_60"),
    }
    score = explicit_score
    if score is None:
        weighted_values = []
        sector_support = components["sector_support_score"]
        sector_trend = components["sector_trend_score"]
        peer_rank = components["sector_peer_rank_score"]
        relative_strength = components["relative_strength_60"]
        if sector_support is not None:
            weighted_values.append((sector_support, 0.60))
        if sector_trend is not None:
            weighted_values.append((sector_trend, 0.20))
        if peer_rank is not None:
            weighted_values.append((peer_rank, 0.10))
        if relative_strength is not None:
            weighted_values.append((relative_strength, 0.10))
        if weighted_values:
            total_weight = sum(weight for _, weight in weighted_values)
            score = sum(value * weight for value, weight in weighted_values) / total_weight
        else:
            score = None
    if score is None:
        score = 55.0

    regime = _sector_regime_from_score(score)
    penalty = 0.0
    has_sector_signal = explicit_score is not None or any(
        components[key] is not None
        for key in ("sector_support_score", "sector_trend_score", "relative_strength_60")
    )
    if has_sector_signal:
        if regime == "weak":
            penalty = 7.0
        elif regime == "fading":
            penalty = 4.0

    return {
        "regime": regime,
        "score": round(score, 2),
        "penalty": round(penalty, 2),
        "components": {key: None if value is None else round(value, 2) for key, value in components.items()},
    }


def _calculate_trend_health_gate(candidate: dict) -> dict:
    components = {
        "trend_persistence_score": _factor_score(candidate, "trend_persistence_score"),
        "risk_adjusted_return_20": _factor_score(candidate, "risk_adjusted_return_20"),
        "volume_stability_score": _factor_score(candidate, "volume_stability_score"),
        "relative_strength_20": _factor_score(candidate, "relative_strength_20"),
    }
    if not any(value is not None for value in components.values()):
        return {
            "state": "unknown",
            "score": 55.0,
            "penalty": 0.0,
            "checks": {},
            "components": {key: None for key in components},
        }

    checks = {
        "trend_persistence": _neutral_if_missing(components["trend_persistence_score"]) >= 55,
        "risk_adjusted_return": _neutral_if_missing(components["risk_adjusted_return_20"]) >= 50,
        "volume_stability": _neutral_if_missing(components["volume_stability_score"]) >= 45,
        "relative_strength": _neutral_if_missing(components["relative_strength_20"]) >= 50,
    }
    passed = sum(1 for value in checks.values() if value)
    if passed >= 4:
        state = "healthy"
        penalty = 0.0
    elif passed >= 2:
        state = "mixed"
        penalty = 3.0
    else:
        state = "weak"
        penalty = 6.0

    score = _average_present(list(components.values()))
    if score is None:
        score = 50.0

    return {
        "state": state,
        "score": round(score, 2),
        "penalty": round(penalty, 2),
        "checks": checks,
        "components": {key: None if value is None else round(value, 2) for key, value in components.items()},
    }


def _calculate_risk_gate_decision(candidate: dict, optimized_watch_score: float) -> dict:
    market_gate = _calculate_market_gate(candidate)
    sector_gate = _calculate_sector_gate(candidate)
    trend_health_gate = _calculate_trend_health_gate(candidate)
    total_penalty = (
        market_gate["penalty"]
        + sector_gate["penalty"]
        + trend_health_gate["penalty"]
    )
    risk_adjusted_score = max(0.0, min(100.0, optimized_watch_score - total_penalty))

    active_gates = []
    if market_gate["penalty"] > 0:
        active_gates.append(f"market_{market_gate['regime']}")
    if sector_gate["penalty"] > 0:
        active_gates.append(f"sector_{sector_gate['regime']}")
    if trend_health_gate["penalty"] > 0:
        active_gates.append(f"trend_{trend_health_gate['state']}")

    if market_gate["regime"] == "risk_off" or total_penalty >= 12.0:
        observation_mode = "risk_limited_observation"
        observation_priority = 0
    elif market_gate["regime"] == "neutral" or sector_gate["regime"] == "fading" or trend_health_gate["state"] == "mixed":
        observation_mode = "cautious_observation"
        observation_priority = 1
    else:
        observation_mode = "normal_observation"
        observation_priority = 2

    return {
        "schema_version": "risk_gate_decision.v1",
        "policy": "watch_ranking_shadow_only",
        "observation_mode": observation_mode,
        "observation_priority": observation_priority,
        "base_score_source": "optimized_watch_score",
        "base_score": round(optimized_watch_score, 2),
        "risk_adjusted_watch_score_shadow": round(risk_adjusted_score, 2),
        "total_penalty": round(total_penalty, 2),
        "active_gates": active_gates,
        "market_gate": market_gate,
        "sector_gate": sector_gate,
        "trend_health_gate": trend_health_gate,
        "does_not_modify_official_scores": True,
        "no_execution_signals": True,
    }


def _calculate_short_burst_risk_gate(candidate: dict, optimized_watch_score: float) -> dict:
    """Calculate short-burst specific risk controls for watch ranking only."""
    components = {
        "stock_short_score_v2": _factor_score(candidate, "stock_short_score_v2"),
        "sector_burst_score": _factor_score(candidate, "sector_burst_score"),
        "sector_support_score": _factor_score(candidate, "sector_support_score"),
        "chasing_risk_score": _factor_score(candidate, "chasing_risk_score", prefer="raw_value"),
        "amount_ratio_20": _factor_score(candidate, "amount_ratio_20", prefer="raw_value"),
        "breakout_distance_20": _factor_score(candidate, "breakout_distance_20", prefer="raw_value"),
        "relative_strength_20": _factor_score(candidate, "relative_strength_20"),
        "volume_stability_score": _factor_score(candidate, "volume_stability_score"),
    }

    penalties: list[tuple[str, float]] = []
    confirmations: list[str] = []

    sector_burst = components["sector_burst_score"]
    sector_support = components["sector_support_score"]
    if sector_burst is not None:
        if sector_burst < 50:
            penalties.append(("sector_burst_weak", 5.0))
        elif sector_burst >= 70:
            confirmations.append("sector_burst_confirmed")
    if sector_support is not None:
        if sector_support < 45:
            penalties.append(("sector_support_weak", 4.0))
        elif sector_support >= 65:
            confirmations.append("sector_support_confirmed")

    chasing_risk = components["chasing_risk_score"]
    if chasing_risk is not None:
        if chasing_risk >= 80:
            penalties.append(("burst_overheat_high", 6.0))
        elif chasing_risk >= 70:
            penalties.append(("burst_overheat_watch", 3.0))

    amount_ratio = components["amount_ratio_20"]
    if amount_ratio is not None:
        if amount_ratio >= 2.5:
            penalties.append(("volume_extreme_expansion", 4.0))
        elif amount_ratio >= 1.8:
            penalties.append(("volume_fast_expansion", 2.0))
        elif 1.0 <= amount_ratio <= 1.7:
            confirmations.append("volume_expansion_balanced")

    breakout_distance = components["breakout_distance_20"]
    if breakout_distance is not None:
        if breakout_distance > 20:
            penalties.append(("burst_position_extended", 4.0))
        elif breakout_distance <= 10:
            confirmations.append("burst_position_acceptable")

    relative_strength = components["relative_strength_20"]
    volume_stability = components["volume_stability_score"]
    if relative_strength is not None and relative_strength >= 85 and (sector_burst is None or sector_burst < 55):
        penalties.append(("single_name_strength_without_sector_spread", 3.0))
    if volume_stability is not None:
        if volume_stability < 45:
            penalties.append(("volume_stability_weak", 3.0))
        elif volume_stability >= 60:
            confirmations.append("volume_stability_confirmed")

    total_penalty = min(18.0, sum(value for _, value in penalties))
    short_score = max(0.0, min(100.0, optimized_watch_score - total_penalty))
    if total_penalty >= 12.0:
        observation_mode = "burst_risk_limited_observation"
        observation_priority = 0
    elif total_penalty >= 6.0:
        observation_mode = "burst_cautious_observation"
        observation_priority = 1
    else:
        observation_mode = "burst_normal_observation"
        observation_priority = 2

    return {
        "schema_version": "short_burst_risk_gate.v1",
        "policy": "short_burst_watch_ranking_shadow_only",
        "base_score_source": "optimized_watch_score",
        "base_score": round(optimized_watch_score, 2),
        "short_burst_risk_adjusted_score_shadow": round(short_score, 2),
        "total_penalty": round(total_penalty, 2),
        "penalties": [{"reason": reason, "value": value} for reason, value in penalties],
        "confirmations": confirmations,
        "components": {key: None if value is None else round(value, 2) for key, value in components.items()},
        "observation_mode": observation_mode,
        "observation_priority": observation_priority,
        "does_not_modify_official_scores": True,
        "no_execution_signals": True,
    }


def _calculate_factor_value_overlay(candidate: dict, base_score: float) -> dict:
    """Calculate a watch-only factor overlay from validated factor value signals."""
    delta = 0.0
    positive_factors: list[str] = []
    risk_factors: list[str] = []
    neutral_factors: list[str] = []

    sector_support = _factor_score(candidate, "sector_support_score", prefer="score")
    if sector_support is not None:
        if sector_support >= 75:
            delta += 4.0
            positive_factors.append("sector_support_positive")
        elif sector_support >= 65:
            delta += 2.0
            positive_factors.append("sector_support_watch")
        elif sector_support < 50:
            delta -= 2.0
            risk_factors.append("sector_support_weak_penalty")
        else:
            neutral_factors.append("sector_support_neutral")

    trend_scores = [
        _factor_score(candidate, "trend_score"),
        _factor_score(candidate, "stock_trend_score"),
        _factor_score(candidate, "sector_trend_score"),
    ]
    trend_scores = [value for value in trend_scores if value is not None]
    if trend_scores:
        trend_score = max(trend_scores)
        if trend_score >= 70:
            delta += 3.0
            positive_factors.append("trend_positive")
        elif trend_score >= 60:
            delta += 1.5
            positive_factors.append("trend_watch")
        else:
            neutral_factors.append("trend_neutral")

    composite_scores = [
        _factor_score(candidate, "factor_composite_shadow_score"),
        _factor_score(candidate, "factor_composite_shadow_score_v2"),
    ]
    composite_scores = [value for value in composite_scores if value is not None]
    if composite_scores and max(composite_scores) >= 60:
        delta += 2.0
        positive_factors.append("factor_composite_positive")

    contraction = _factor_score(candidate, "contraction_score")
    if contraction is not None:
        if contraction >= 70:
            delta += 1.5
            positive_factors.append("contraction_positive")
        else:
            neutral_factors.append("contraction_neutral")

    burst = _factor_score(candidate, "burst_score")
    if burst is not None:
        if burst >= 70:
            delta += 1.5
            positive_factors.append("burst_positive")
        else:
            neutral_factors.append("burst_neutral")

    chasing_risk = _factor_score(candidate, "chasing_risk_score", prefer="raw_value")
    if chasing_risk is not None:
        if chasing_risk >= 70:
            delta -= 4.0
            risk_factors.append("overheat_risk_penalty")
        elif chasing_risk >= 60:
            delta -= 2.0
            risk_factors.append("overheat_watch_penalty")
        else:
            neutral_factors.append("overheat_normal")

    drawdown_depth = _factor_score(candidate, "drawdown_depth_20", prefer="raw_value")
    if drawdown_depth is not None:
        if drawdown_depth > 15:
            delta -= 3.0
            risk_factors.append("deep_drawdown_penalty")
        elif drawdown_depth > 10:
            delta -= 1.5
            risk_factors.append("drawdown_watch_penalty")
        else:
            neutral_factors.append("drawdown_controlled")

    breakout_distance = _factor_score(candidate, "breakout_distance_20", prefer="raw_value")
    if breakout_distance is not None:
        if breakout_distance > 20:
            delta -= 3.0
            risk_factors.append("breakout_distance_far_penalty")
        elif breakout_distance > 10:
            delta -= 2.0
            risk_factors.append("breakout_distance_extended_penalty")
        else:
            neutral_factors.append("breakout_distance_acceptable")

    amount_ratio = _factor_score(candidate, "amount_ratio_20", prefer="raw_value")
    if amount_ratio is not None:
        if amount_ratio >= 2.5:
            delta -= 2.0
            risk_factors.append("volume_spike_penalty")
        elif amount_ratio >= 1.8:
            delta -= 1.0
            risk_factors.append("volume_expansion_watch_penalty")
        else:
            neutral_factors.append("volume_normal")

    def neutral_if_missing(value: float | None) -> float:
        return 50.0 if value is None else value

    trend_model_scores = [
        _factor_score(candidate, "trend_score"),
        _factor_score(candidate, "stock_trend_score"),
        _factor_score(candidate, "sector_trend_score"),
    ]
    trend_model_scores = [value for value in trend_model_scores if value is not None]
    trend_model_score = max(trend_model_scores) if trend_model_scores else None

    model_score = 50.0
    model_score += 0.35 * neutral_if_missing(_factor_score(candidate, "sector_support_score"))
    model_score += 0.25 * neutral_if_missing(trend_model_score)
    model_score += 0.15 * neutral_if_missing(_factor_score(candidate, "contraction_score"))
    model_score += 0.10 * neutral_if_missing(_factor_score(candidate, "final_score"))
    model_score -= 0.12 * neutral_if_missing(_factor_score(candidate, "chasing_risk_score"))
    model_score -= 0.10 * neutral_if_missing(_factor_score(candidate, "drawdown_depth_20"))
    model_score -= 0.10 * neutral_if_missing(_factor_score(candidate, "breakout_distance_20"))
    model_score -= 0.05 * neutral_if_missing(_factor_score(candidate, "amount_ratio_20"))
    rule_delta = max(-10.0, min(8.0, delta))
    raw_risk_guardrail = min(0.0, rule_delta) * 1.5
    optimized_watch_score = max(0.0, min(100.0, model_score + raw_risk_guardrail))
    model_delta = optimized_watch_score - base_score

    return {
        "schema_version": "factor_value_overlay.v1",
        "policy": "watch_ranking_only",
        "model": "backtest_weighted_score_v1",
        "base_score_source": "selection_score_adjusted",
        "base_score": round(base_score, 2),
        "delta": round(model_delta, 2),
        "model_score": round(model_score, 2),
        "raw_risk_guardrail": round(raw_risk_guardrail, 2),
        "optimized_watch_score": round(optimized_watch_score, 2),
        "rule_delta": round(rule_delta, 2),
        "positive_factors": positive_factors,
        "risk_factors": risk_factors,
        "neutral_factors": neutral_factors,
        "does_not_change_official_scores": True,
        "backtest_window": "2026-03-13_to_2026-07-10",
    }


def _calculate_factor_value_overlay_v2_shadow(candidate: dict, base_score: float) -> dict:
    trend_scores = [
        _factor_score(candidate, "trend_score"),
        _factor_score(candidate, "stock_trend_score"),
        _factor_score(candidate, "sector_trend_score"),
    ]
    trend_scores = [value for value in trend_scores if value is not None]
    trend_score = max(trend_scores) if trend_scores else None

    model_score = 50.0
    model_score += 0.32 * _neutral_if_missing(_factor_score(candidate, "sector_support_score"))
    model_score += 0.24 * _neutral_if_missing(trend_score)
    model_score += 0.14 * _neutral_if_missing(_factor_score(candidate, "contraction_score"))
    model_score += 0.10 * _neutral_if_missing(_factor_score(candidate, "final_score"))
    model_score -= 0.08 * _neutral_if_missing(_factor_score(candidate, "drawdown_depth_20"))
    model_score -= 0.08 * _neutral_if_missing(_factor_score(candidate, "breakout_distance_20"))
    model_score -= 0.06 * _neutral_if_missing(_factor_score(candidate, "relative_strength_20"))
    model_score -= 0.04 * _neutral_if_missing(_factor_score(candidate, "risk_adjusted_return_20"))
    model_score -= 0.04 * _neutral_if_missing(_factor_score(candidate, "amount_ratio_20"))

    optimized = max(0.0, min(100.0, model_score))
    return {
        "schema_version": "factor_value_overlay.v2_shadow",
        "policy": "shadow_watch_ranking_only",
        "model": "factor_value_shadow_v2",
        "base_score_source": "selection_score_adjusted",
        "base_score": round(base_score, 2),
        "delta": round(optimized - base_score, 2),
        "optimized_watch_score_v2_shadow": round(optimized, 2),
        "does_not_change_official_scores": True,
        "does_not_drive_current_sort": True,
    }


def _calculate_short_burst_emotion_overlay_shadow(candidate: dict) -> dict:
    """Expose short-burst emotion factors as a shadow-only ranking input."""
    score_v2 = _factor_score(candidate, "short_burst_emotion_score_v2")
    score_v1 = _factor_score(candidate, "short_burst_emotion_score_v1")
    if score_v2 is not None:
        score = score_v2
        score_source = "short_burst_emotion_score_v2"
        model = "short_burst_emotion_v2_shadow"
    elif score_v1 is not None:
        score = score_v1
        score_source = "short_burst_emotion_score_v1"
        model = "short_burst_emotion_v1_shadow"
    else:
        score = None
        score_source = "missing"
        model = "short_burst_emotion_missing"

    components = {
        "short_burst_emotion_score_v2": score_v2,
        "short_burst_emotion_score_v1": score_v1,
        "volume_burst_quality_score": _factor_score(candidate, "volume_burst_quality_score"),
        "close_strength_score": _factor_score(candidate, "close_strength_score"),
        "limit_attention_score": _factor_score(candidate, "limit_attention_score"),
        "next_day_cashout_risk_score": _factor_score(candidate, "next_day_cashout_risk_score"),
        "single_name_overheat_score": _factor_score(candidate, "single_name_overheat_score"),
    }
    return {
        "schema_version": "short_burst_emotion_overlay.v1",
        "policy": "shadow_observation_only",
        "model": model,
        "score_source": score_source,
        "short_burst_emotion_score_shadow": None if score is None else round(score, 2),
        "components": {key: None if value is None else round(value, 2) for key, value in components.items()},
        "requires_rolling_validation": True,
        "does_not_modify_official_scores": True,
        "does_not_drive_current_sort": True,
        "no_execution_signals": True,
    }


def _calculate_intraday_factor_snapshot(candidate: dict) -> dict:
    intraday_factors = calculate_intraday_factors(candidate)
    factors = [
        {
            "factor_id": factor_id,
            "value": None if value is None else round(value, 2),
            "quality": "missing" if value is None else "observed",
            "tags": ["intraday_shadow", "no_execution_signal"],
        }
        for factor_id, value in intraday_factors.items()
    ]
    observed = [item["factor_id"] for item in factors if item["quality"] == "observed"]
    return {
        "schema_version": "intraday_factor_snapshot.v1",
        "policy": "shadow_observation_only",
        "intraday_available": bool(observed),
        "factors": factors,
        "summary": {
            "factor_count": len(factors),
            "observed_count": len(observed),
            "observed_factors": observed,
        },
        "does_not_modify_official_scores": True,
        "no_execution_signals": True,
    }


def _calculate_short_burst_intraday_emotion_overlay_shadow(
    candidate: dict,
    intraday_factor_snapshot: dict,
) -> dict | None:
    values = {
        item.get("factor_id"): item.get("value")
        for item in intraday_factor_snapshot.get("factors", [])
        if isinstance(item, dict)
    }
    score = values.get("short_burst_intraday_emotion_score_shadow")
    if score is None:
        return None
    return {
        "schema_version": "short_burst_intraday_emotion_overlay.v1",
        "policy": "shadow_observation_only",
        "score_source": "short_burst_intraday_emotion_score_shadow",
        "short_burst_intraday_emotion_score_shadow": round(_safe_float(score), 2),
        "components": {
            "intraday_close_position_score": values.get("intraday_close_position_score"),
            "intraday_high_pullback_risk_score": values.get("intraday_high_pullback_risk_score"),
            "intraday_volume_price_confirm_score": values.get("intraday_volume_price_confirm_score"),
            "intraday_sector_breadth_score": values.get("intraday_sector_breadth_score"),
            "intraday_late_strength_score": values.get("intraday_late_strength_score"),
        },
        "requires_forward_return_validation": True,
        "does_not_modify_official_scores": True,
        "does_not_drive_current_sort": True,
        "no_execution_signals": True,
    }


def _calculate_short_burst_news_emotion_overlay_shadow(candidate: dict) -> dict | None:
    score = _factor_score(candidate, "short_burst_news_emotion_score_shadow")
    if score is None:
        return None
    components = {
        factor_id: _factor_score(candidate, factor_id)
        for factor_id in SHORT_BURST_NEWS_EMOTION_FACTOR_IDS
        if factor_id != "short_burst_news_emotion_score_shadow"
    }
    return {
        "schema_version": "short_burst_news_emotion_overlay.v1",
        "policy": "shadow_observation_only",
        "score_source": "short_burst_news_emotion_score_shadow",
        "short_burst_news_emotion_score_shadow": round(_safe_float(score), 2),
        "components": {key: None if value is None else round(value, 2) for key, value in components.items()},
        "requires_forward_return_validation": True,
        "does_not_modify_official_scores": True,
        "does_not_drive_current_sort": True,
        "no_execution_signals": True,
    }


def _calculate_short_burst_observation_rank_shadow(
    short_burst_emotion_overlay_shadow: dict | None,
    short_burst_intraday_emotion_overlay_shadow: dict | None,
    short_burst_news_emotion_overlay_shadow: dict | None = None,
) -> dict | None:
    daily_score = None
    intraday_score = None
    news_score = None
    if short_burst_emotion_overlay_shadow is not None:
        daily_score = short_burst_emotion_overlay_shadow.get("short_burst_emotion_score_shadow")
    if short_burst_intraday_emotion_overlay_shadow is not None:
        intraday_score = short_burst_intraday_emotion_overlay_shadow.get("short_burst_intraday_emotion_score_shadow")
    if short_burst_news_emotion_overlay_shadow is not None:
        news_score = short_burst_news_emotion_overlay_shadow.get("short_burst_news_emotion_score_shadow")
    if daily_score is None and intraday_score is None and news_score is None:
        return None
    if daily_score is None and news_score is None:
        rank_score = _safe_float(intraday_score)
        model = "short_burst_intraday_shadow_only"
    elif intraday_score is None and news_score is None:
        rank_score = _safe_float(daily_score)
        model = "short_burst_daily_shadow_only"
    elif daily_score is None and intraday_score is None:
        rank_score = _safe_float(news_score)
        model = "short_burst_news_emotion_shadow_only"
    else:
        parts = []
        if daily_score is not None:
            parts.append((_safe_float(daily_score), 0.42))
        if intraday_score is not None:
            parts.append((_safe_float(intraday_score), 0.33))
        if news_score is not None:
            parts.append((_safe_float(news_score), 0.25))
        total_weight = sum(weight for _, weight in parts)
        rank_score = sum(value * weight for value, weight in parts) / total_weight
        model = "short_burst_daily_intraday_news_shadow_blend"
    return {
        "schema_version": "short_burst_observation_rank_shadow.v1",
        "policy": "shadow_observation_only",
        "model": model,
        "short_burst_observation_rank_shadow": round(rank_score, 2),
        "daily_shadow_score": None if daily_score is None else round(_safe_float(daily_score), 2),
        "intraday_shadow_score": None if intraday_score is None else round(_safe_float(intraday_score), 2),
        "news_emotion_shadow_score": None if news_score is None else round(_safe_float(news_score), 2),
        "requires_forward_return_validation": True,
        "does_not_modify_official_scores": True,
        "does_not_drive_current_sort": True,
        "no_execution_signals": True,
    }


def classify_stock_candidate(candidate: dict, source_pool: str) -> dict:
    """鐎电懓宕熸稉顏勨偓娆撯偓澶庡亗鏉╂稖顢戦崚鍡欒閵?
    Args:
        candidate: 閸婃瑩鈧鍋傜€涙鍚€
        source_pool: 閺夈儲绨Ч?(trend_top/burst_top/v2_potential/divergence_review)

    Returns:
        閸掑棛琚紒鎾寸亯鐎涙鍚€
    """
    code = candidate.get("code", "")
    name = candidate.get("name", "")
    signal_type = candidate.get("signal_type", "unknown")
    data_quality = candidate.get("data_quality", "ok")
    risk_flags = candidate.get("risk_flags", [])

    # 鐠囪褰?final_score - 娣囨繃瀵旈崢鐔奉潗閸婄》绱濇稉宥堟祮娑?0
    final_score_raw = candidate.get("final_score")
    final_score = _safe_float(final_score_raw) if final_score_raw is not None else None

    # 鐠囪褰?v2_score - 娴兼ê鍘涙担璺ㄦ暏 v2_score閿涘畺allback 閸?factor_composite_shadow_score_v2
    v2_score_raw = candidate.get("v2_score")
    if v2_score_raw is None:
        v2_score_raw = candidate.get("factor_composite_shadow_score_v2")
    v2_score = _safe_float(v2_score_raw) if v2_score_raw is not None else None

    # 閻劋绨拋锛勭暬閻ㄥ嫬鍨庨弫甯礄娑擃厽鈧冣偓纭风礆
    final_score_for_calc = final_score if final_score is not None else 50.0
    v2_score_for_calc = v2_score if v2_score is not None else 50.0

    # 濡偓閺?hard blockers
    hard_blockers = []

    if not code:
        hard_blockers.append("missing_code")
    if not name:
        hard_blockers.append("missing_name")
    if data_quality == "missing":
        hard_blockers.append("data_missing")
    # 閸欘亝婀?final_score 閸?v2_score 閸氬本妞傜紓鍝勩亼閺冭埖澧犵憴锕€褰?scores_missing
    if final_score is None and v2_score is None:
        hard_blockers.append("scores_missing")

    # 濡偓閺?severe risk flags
    severe_flags = {"severe", "data_missing", "suspended", "st", "liquidity_missing"}
    for flag in risk_flags:
        if flag in severe_flags:
            hard_blockers.append(f"risk_{flag}")

    # 閸掑棛琚?
    selection_bucket = "blocked"
    selection_score = 0.0

    if hard_blockers:
        selection_bucket = "blocked"
        selection_score = 0.0
    elif source_pool == "v2_potential" and signal_type == "low_final_high_v2":
        selection_bucket = "v2_opportunity"
        selection_score = v2_score_for_calc * 0.7 + final_score_for_calc * 0.3
    elif source_pool == "divergence_review" and signal_type == "high_final_low_v2":
        selection_bucket = "divergence_review"
        selection_score = final_score_for_calc * 0.5 + v2_score_for_calc * 0.5
    elif source_pool in ("trend_top", "burst_top") and final_score is not None and final_score >= 55:
        selection_bucket = "core_watch"
        selection_score = final_score_for_calc * 0.7 + v2_score_for_calc * 0.3
    else:
        selection_bucket = "blocked"
        selection_score = 0.0

    # 闂勬劕鍩楅崚鍡樻殶閼煎啫娲?
    selection_score = max(0.0, min(100.0, selection_score))

    soft_warnings = []

    if data_quality == "partial":
        soft_warnings.append("partial_data")
    if final_score is not None and final_score < 55 and selection_bucket == "core_watch":
        soft_warnings.append("low_final_score")

    # 閺傛澘顤冩潪顖濐劅閸?(缁楊兛绨╅崡浣风闂冭埖顔?B + 缁楊剙娲撻崡浣风安闂冭埖顔岄弽鈥冲櫙 + 缁楊剙娲撻崡浣稿彋闂冭埖顔岀拠顓濈疅娣囶喗顒?
    liquidity_score = get_factor_value(candidate, "liquidity_score", prefer="raw_value")
    if liquidity_score is not None and _safe_float(liquidity_score) < 40:
        soft_warnings.append("liquidity_weak")

    chasing_risk_score = get_factor_value(candidate, "chasing_risk_score", prefer="raw_value")
    if chasing_risk_score is not None and _safe_float(chasing_risk_score) >= 70:
        soft_warnings.append("chasing_risk_high")

    # drawdown_depth_20 deep 娑撳秴鍟€娴ｆ粈璐?soft_warning閿涘本鏁兼稉?repair_context (shadow-only)

    # 鐠愩劑鍣虹涵顔款吇 (缁楊兛绨╅崡浣告磽闂冭埖顔? sector_support_score)
    quality_confirmations = []
    sector_support_score = get_factor_value(candidate, "sector_support_score", prefer="score")
    if sector_support_score is not None:
        sector_support_val = _safe_float(sector_support_score)
        if sector_support_val >= 65:
            quality_confirmations.append("sector_support_confirmed")
        elif sector_support_val < 50:
            soft_warnings.append("sector_support_weak")
            if sector_support_val < 40:
                soft_warnings.append("sector_support_very_weak")

    # selection_score_adjusted (缁楊兛绨╅崡浣风闂冭埖顔? 閹?opportunity_type 閸氼垳鏁?
    opportunity_type = _infer_opportunity_type(candidate, source_pool)
    adjustment_policy = SECTOR_SUPPORT_ADJUSTMENT_POLICY.get(opportunity_type, "display_only")

    sector_support_score = get_factor_value(candidate, "sector_support_score", prefer="score")
    factor_snapshot = candidate.get("factor_snapshot")

    adjustment_delta, adjustment_applied, adjustment_reason = _calculate_sector_support_delta(
        sector_support_score, adjustment_policy
    )

    selection_score_adjusted = selection_score + adjustment_delta if adjustment_applied else selection_score
    selection_score_adjusted = max(0.0, min(100.0, selection_score_adjusted))

    # 绾喖鐣?quality_level
    if hard_blockers:
        quality_level = "blocked"
    elif soft_warnings:
        quality_level = "warn"
    else:
        quality_level = "ok"

    # ============================================================
    # bars_factor_policy (缁楊兛绗侀崡浣风癌闂冭埖顔?+ 缁楊剙娲撻崡浣风安闂冭埖顔岄弽鈥冲櫙 + 缁楊剙娲撻崡浣稿彋闂冭埖顔岀拠顓濈疅娣囶喗顒?
    # ============================================================
    bars_factor_policy = {}

    # breakout_distance_20: raw_value = (high_20 - close_t) / high_20 * 100
    # near(raw<=3) -> structure_candidate (闂?trigger), neutral/far -> profile_only
    # 閸樺棗褰舵径宥囨磸閺勫墽銇?near 娑撳秳绔寸€规矮绱禍?far閿涘奔绮庢担婊€璐熺紒鎾寸€担宥囩枂閺嶅洨顒?
    breakout_distance = get_factor_value(candidate, "breakout_distance_20", prefer="raw_value")
    if breakout_distance is not None:
        breakout_val = _safe_float(breakout_distance)
        if breakout_val <= 3:
            bars_factor_policy["breakout_distance_20"] = {
                "policy": "structure_candidate",
                "applied": False,
                "reason": "near 20d high position; historical validation does not support standalone trigger",
            }
            if "structure_position_candidate" not in quality_confirmations:
                quality_confirmations.append("structure_position_candidate")
        elif breakout_val <= 10:
            bars_factor_policy["breakout_distance_20"] = {
                "policy": "profile_only",
                "applied": False,
                "reason": "neutral position from 20d high",
            }
        else:
            bars_factor_policy["breakout_distance_20"] = {
                "policy": "profile_only",
                "applied": False,
                "reason": "far from 20d high",
            }
    else:
        bars_factor_policy["breakout_distance_20"] = {
            "policy": "calibration_needed",
            "applied": False,
            "reason": "breakout_distance_20 missing",
        }

    # drawdown_depth_20: raw_value = 閸ョ偞鎸欓惂鎯у瀻濮?    # deep(raw>15) -> repair_context (闂?soft_warning), normal/healthy -> profile_only
    # deep 娑撳秶鐡戞禍搴棑闂勨晜浼撻崠鏍电礉閸欘垵鍏橀弰顖欐叏婢跺秵婧€娴?    drawdown_depth = get_factor_value(candidate, "drawdown_depth_20", prefer="raw_value")
    drawdown_depth = get_factor_value(candidate, "drawdown_depth_20", prefer="raw_value")
    if drawdown_depth is not None:
        drawdown_val = _safe_float(drawdown_depth)
        if drawdown_val > 15:
            bars_factor_policy["drawdown_depth_20"] = {
                "policy": "repair_context",
                "applied": False,
                "reason": "deep pullback context; not a hard risk blocker",
            }
        else:
            bars_factor_policy["drawdown_depth_20"] = {
                "policy": "profile_only",
                "applied": False,
                "reason": "shallow/normal pullback",
            }
    else:
        bars_factor_policy["drawdown_depth_20"] = {
            "policy": "calibration_needed",
            "applied": False,
            "reason": "drawdown_depth_20 missing",
        }

    # liquidity_score: 娣囨繃瀵?profile_only, weak 娴ｆ粈璐?soft_warning (applied false)
    liquidity_score = get_factor_value(candidate, "liquidity_score", prefer="raw_value")
    if factor_snapshot is not None and liquidity_score is None:
        liquidity_score = factor_snapshot.get("liquidity_score")
    if liquidity_score is not None:
        liquidity_val = _safe_float(liquidity_score)
        if liquidity_val < 40:
            bars_factor_policy["liquidity_score"] = {
                "policy": "soft_warning",
                "applied": False,
                "reason": "liquidity weak",
            }
            if "liquidity_weak" not in soft_warnings:
                soft_warnings.append("liquidity_weak")
        else:
            bars_factor_policy["liquidity_score"] = {
                "policy": "profile_only",
                "applied": False,
                "reason": "liquidity acceptable",
            }
    else:
        bars_factor_policy["liquidity_score"] = {
            "policy": "calibration_needed",
            "applied": False,
            "reason": "liquidity_score missing",
        }

    # chasing_risk_score: raw_value 閸楁娊顥撻梽鈺勭槑閸?0-100)
    # high(>=70) -> soft_warning(applied=true), watch(>=60) -> display_only, normal(<60) -> profile_only
    chasing_risk = get_factor_value(candidate, "chasing_risk_score", prefer="raw_value")
    if chasing_risk is not None:
        chasing_val = _safe_float(chasing_risk)
        if chasing_val >= 70:
            bars_factor_policy["chasing_risk_score"] = {
                "policy": "soft_warning",
                "applied": True,
                "reason": "overheat risk high",
            }
            if "overheat_risk_high" not in soft_warnings:
                soft_warnings.append("overheat_risk_high")
        elif chasing_val >= 60:
            bars_factor_policy["chasing_risk_score"] = {
                "policy": "display_only",
                "applied": False,
                "reason": "overheat risk watch",
            }
        else:
            bars_factor_policy["chasing_risk_score"] = {
                "policy": "profile_only",
                "applied": False,
                "reason": "chasing risk normal",
            }
    else:
        bars_factor_policy["chasing_risk_score"] = {
            "policy": "calibration_needed",
            "applied": False,
            "reason": "chasing_risk_score missing",
        }

    factor_value_overlay = _calculate_factor_value_overlay(candidate, selection_score_adjusted)
    factor_value_overlay_v2_shadow = _calculate_factor_value_overlay_v2_shadow(candidate, selection_score_adjusted)
    risk_gate_decision = _calculate_risk_gate_decision(candidate, factor_value_overlay["optimized_watch_score"])
    intraday_factor_snapshot = _calculate_intraday_factor_snapshot(candidate)
    intraday_values = {
        item.get("factor_id"): item.get("value")
        for item in intraday_factor_snapshot.get("factors", [])
        if isinstance(item, dict)
    }
    short_burst_risk_gate = None
    short_burst_risk_adjusted_score_shadow = None
    short_burst_emotion_overlay_shadow = None
    short_burst_intraday_emotion_overlay_shadow = None
    short_burst_news_emotion_overlay_shadow = None
    short_burst_observation_rank_shadow = None
    if opportunity_type == "short_burst":
        short_burst_risk_gate = _calculate_short_burst_risk_gate(
            candidate,
            factor_value_overlay["optimized_watch_score"],
        )
        short_burst_risk_adjusted_score_shadow = short_burst_risk_gate[
            "short_burst_risk_adjusted_score_shadow"
        ]
        short_burst_emotion_overlay_shadow = _calculate_short_burst_emotion_overlay_shadow(candidate)
        short_burst_intraday_emotion_overlay_shadow = _calculate_short_burst_intraday_emotion_overlay_shadow(
            candidate,
            intraday_factor_snapshot,
        )
        short_burst_news_emotion_overlay_shadow = _calculate_short_burst_news_emotion_overlay_shadow(candidate)
        short_burst_observation_rank_shadow = _calculate_short_burst_observation_rank_shadow(
            short_burst_emotion_overlay_shadow,
            short_burst_intraday_emotion_overlay_shadow,
            short_burst_news_emotion_overlay_shadow,
        )
    watch_ranking_decision = {
        "schema_version": "watch_ranking_decision.v1",
        "status": "shadow_observation",
        "current_sort_model": (
            "short_burst_risk_adjusted_score_shadow"
            if short_burst_risk_adjusted_score_shadow is not None
            else "risk_adjusted_watch_score_shadow"
        ),
        "current_sort_score": (
            short_burst_risk_adjusted_score_shadow
            if short_burst_risk_adjusted_score_shadow is not None
            else risk_gate_decision["risk_adjusted_watch_score_shadow"]
        ),
        "base_sort_model": "optimized_watch_score",
        "base_sort_score": factor_value_overlay["optimized_watch_score"],
        "shadow_model": "optimized_watch_score_v2_shadow",
        "shadow_score": factor_value_overlay_v2_shadow["optimized_watch_score_v2_shadow"],
        "short_burst_shadow_model": (
            short_burst_emotion_overlay_shadow["score_source"]
            if short_burst_emotion_overlay_shadow is not None
            else None
        ),
        "short_burst_shadow_score": (
            short_burst_emotion_overlay_shadow["short_burst_emotion_score_shadow"]
            if short_burst_emotion_overlay_shadow is not None
            else None
        ),
        "intraday_shadow_model": (
            short_burst_intraday_emotion_overlay_shadow["score_source"]
            if short_burst_intraday_emotion_overlay_shadow is not None
            else None
        ),
        "intraday_shadow_score": (
            short_burst_intraday_emotion_overlay_shadow["short_burst_intraday_emotion_score_shadow"]
            if short_burst_intraday_emotion_overlay_shadow is not None
            else None
        ),
        "news_emotion_shadow_model": (
            short_burst_news_emotion_overlay_shadow["score_source"]
            if short_burst_news_emotion_overlay_shadow is not None
            else None
        ),
        "news_emotion_shadow_score": (
            short_burst_news_emotion_overlay_shadow["short_burst_news_emotion_score_shadow"]
            if short_burst_news_emotion_overlay_shadow is not None
            else None
        ),
        "observation_rank_shadow_score": (
            short_burst_observation_rank_shadow["short_burst_observation_rank_shadow"]
            if short_burst_observation_rank_shadow is not None
            else None
        ),
        "shadow_delta": round(
            factor_value_overlay_v2_shadow["optimized_watch_score_v2_shadow"]
            - factor_value_overlay["optimized_watch_score"],
            2,
        ),
        "requires_rolling_validation": True,
        "does_not_modify_official_scores": True,
        "no_execution_signals": True,
    }

    return {
        "code": code,
        "name": name,
        "source_pool": source_pool,
        "sector_peer_rank_score": _factor_score(candidate, "sector_peer_rank_score"),
        "selection_bucket": selection_bucket,
        "selection_score": round(selection_score, 2),
        "selection_score_adjusted": round(selection_score_adjusted, 2),
        "optimized_watch_score": factor_value_overlay["optimized_watch_score"],
        "factor_value_overlay": factor_value_overlay,
        "risk_adjusted_watch_score_shadow": risk_gate_decision["risk_adjusted_watch_score_shadow"],
        "risk_gate_decision": risk_gate_decision,
        "short_burst_risk_adjusted_score_shadow": short_burst_risk_adjusted_score_shadow,
        "short_burst_risk_gate": short_burst_risk_gate,
        "short_burst_emotion_overlay_shadow": short_burst_emotion_overlay_shadow,
        "short_burst_news_emotion_overlay_shadow": short_burst_news_emotion_overlay_shadow,
        **{
            factor_id: _factor_score(candidate, factor_id)
            for factor_id in SHORT_BURST_NEWS_EMOTION_FACTOR_IDS
        },
        "intraday_factor_snapshot": intraday_factor_snapshot,
        "intraday_close_position_score": intraday_values.get("intraday_close_position_score"),
        "intraday_high_pullback_risk_score": intraday_values.get("intraday_high_pullback_risk_score"),
        "intraday_volume_price_confirm_score": intraday_values.get("intraday_volume_price_confirm_score"),
        "intraday_sector_breadth_score": intraday_values.get("intraday_sector_breadth_score"),
        "intraday_late_strength_score": intraday_values.get("intraday_late_strength_score"),
        "short_burst_intraday_emotion_score_shadow": intraday_values.get("short_burst_intraday_emotion_score_shadow"),
        **{factor_id: intraday_values.get(factor_id) for factor_id in INTRADAY_ATOMIC_FACTOR_IDS},
        "short_burst_intraday_emotion_overlay_shadow": short_burst_intraday_emotion_overlay_shadow,
        "short_burst_observation_rank_shadow": short_burst_observation_rank_shadow,
        "optimized_watch_score_v2_shadow": factor_value_overlay_v2_shadow["optimized_watch_score_v2_shadow"],
        "factor_value_overlay_v2_shadow": factor_value_overlay_v2_shadow,
        "watch_ranking_decision": watch_ranking_decision,
        "sector_support_adjustment_policy": adjustment_policy,
        "sector_support_adjustment_applied": adjustment_applied,
        "sector_support_adjustment_delta": round(adjustment_delta, 2),
        "sector_support_adjustment_reason": adjustment_reason,
        "bars_factor_policy": bars_factor_policy,
        "quality_level": quality_level,
        "hard_blockers": hard_blockers,
        "soft_warnings": soft_warnings,
        "quality_confirmations": quality_confirmations,
        "risk_flags": risk_flags,
        "action_state": "watch_only",
    }


def build_eligible_watchlist(stock_pools: dict, top_n: int = 10) -> dict:
    """閺嬪嫬缂撶划鍓х暆鐟欏倸鐧傚Ч鐘偓?
    Args:
        stock_pools: daily_decision_summary 娑擃厾娈?stock_pools
        top_n: 濮ｅ繋閲?bucket 閺堚偓婢舵矮绻氶悾娆戞畱閼诧紕銈ㄩ弫浼村櫤

    Returns:
        閸掑棛琚崥搴ｆ畱閸婃瑩鈧鐫滈崪?selection_quality
    """
    # 閺€鍫曟肠閹碘偓閺堝鈧瑩鈧鍋?
    all_candidates: list[dict] = []

    # 閹稿绱崗鍫㈤獓婢跺嫮鎮婇崥鍕潨
    pool_priority = {
        "v2_potential": 1,
        "core_watch": 2,
        "divergence_review": 3,
        "blocked": 4,
    }

    raw_candidates: list[tuple[str, dict]] = []
    for pool_name in ["trend_top", "burst_top", "v2_potential", "divergence_review"]:
        for candidate in stock_pools.get(pool_name, []):
            raw_candidates.append((pool_name, dict(candidate)))

    raw_candidate_items = [candidate for _, candidate in raw_candidates]
    annotate_sector_peer_rank_scores(raw_candidate_items)
    annotate_market_regime_scores(raw_candidate_items)
    for pool_name, candidate in raw_candidates:
        classified = classify_stock_candidate(candidate, pool_name)
        all_candidates.append(classified)

    # 閸樺鍣搁敍姘倱娑撯偓 code 閸欘亙绻氶悾娆庣喘閸忓牏楠囬張鈧妯兼畱
    seen_codes: dict[str, dict] = {}
    for candidate in all_candidates:
        code = candidate.get("code", "")
        if not code:
            continue

        bucket = candidate.get("selection_bucket", "blocked")
        priority = pool_priority.get(bucket, 5)

        if code not in seen_codes:
            seen_codes[code] = candidate
            seen_codes[code]["_priority"] = priority
        else:
            # 婵″倹鐏夐弬鏉库偓娆撯偓澶夌喘閸忓牏楠囬弴鎾彯閿涘本娴涢幑?            existing_priority = seen_codes[code].get("_priority", 5)
            if priority < existing_priority:
                # 鐠佹澘缍嶉弶銉︾爱閸樺棗褰?
                old_source = seen_codes[code].get("source_pool", "")
                candidate["source_pool_history"] = [old_source, candidate.get("source_pool", "")]
                seen_codes[code] = candidate
                seen_codes[code]["_priority"] = priority
            else:
                # 鐠佹澘缍嶉弶銉︾爱閸樺棗褰?
                if "source_pool_history" not in seen_codes[code]:
                    seen_codes[code]["source_pool_history"] = []
                seen_codes[code]["source_pool_history"].append(candidate.get("source_pool", ""))

    # 閹?bucket 閸掑棛绮?
    result = {
        "eligible_watchlist": [],
        "core_watch": [],
        "v2_opportunity": [],
        "divergence_review": [],
        "blocked": [],
    }

    all_hard_blockers: list[str] = []
    all_soft_warnings: list[str] = []

    for code, candidate in seen_codes.items():
        bucket = candidate.get("selection_bucket", "blocked")

        # 濞撳懐鎮婇崘鍛村劥鐎涙顔?
        clean_candidate = {k: v for k, v in candidate.items() if not k.startswith("_")}

        if bucket == "core_watch":
            result["core_watch"].append(clean_candidate)
        elif bucket == "v2_opportunity":
            result["v2_opportunity"].append(clean_candidate)
        elif bucket == "divergence_review":
            result["divergence_review"].append(clean_candidate)
        elif bucket == "blocked":
            result["blocked"].append(clean_candidate)

        # 閺€鍫曟肠 blockers 閸?warnings
        all_hard_blockers.extend(candidate.get("hard_blockers", []))
        all_soft_warnings.extend(candidate.get("soft_warnings", []))

    # 閺嬪嫬缂?eligible_watchlist閿涙碍甯撻梽?blocked閿涘本瀵?selection_score 閹烘帒绨?
    eligible = []
    for bucket in ["v2_opportunity", "core_watch", "divergence_review"]:
        for candidate in result[bucket]:
            eligible.append(candidate)

    # Sort by risk-adjusted watch-only score, falling back to legacy scores for old records.
    eligible.sort(
        key=lambda x: (
            (
                (x.get("short_burst_risk_gate") or {}).get("observation_priority")
                if x.get("short_burst_risk_gate")
                else (x.get("risk_gate_decision") or {}).get("observation_priority", 1)
            ),
            x.get(
                "short_burst_risk_adjusted_score_shadow",
                x.get("risk_adjusted_watch_score_shadow", x.get("optimized_watch_score", x.get("selection_score_adjusted", x.get("selection_score", 0)))),
            ),
            x.get("risk_adjusted_watch_score_shadow", x.get("optimized_watch_score", x.get("selection_score_adjusted", x.get("selection_score", 0)))),
            x.get("optimized_watch_score", x.get("selection_score_adjusted", x.get("selection_score", 0))),
            x.get("selection_score_adjusted", x.get("selection_score", 0)),
            x.get("selection_score", 0),
        ),
        reverse=True,
    )
    result["eligible_watchlist"] = eligible[:top_n * 2]  # 娣囨繄鏆€閺囨潙顦块悽銊ょ艾鐏炴洜銇?

    # 闂勬劕鍩楅崥鍕潨婢堆冪毈
    for bucket in ["core_watch", "v2_opportunity", "divergence_review", "blocked"]:
        result[bucket] = result[bucket][:top_n]

    # 鐠侊紕鐣?selection_quality
    eligible_count = len(result["eligible_watchlist"])
    blocked_count = len(result["blocked"])

    # 閸掋倖鏌?pool_quality
    if eligible_count == 0 or len(all_hard_blockers) >= 5:
        pool_quality = "fail"
    elif blocked_count > eligible_count or all_soft_warnings:
        pool_quality = "warn"
    else:
        pool_quality = "ok"

    selection_quality = {
        "eligible_count": eligible_count,
        "blocked_count": blocked_count,
        "pool_quality": pool_quality,
        "hard_blockers": list(set(all_hard_blockers)),
        "soft_warnings": list(set(all_soft_warnings)),
    }

    return {
        "eligible_watchlist": result["eligible_watchlist"],
        "core_watch": result["core_watch"],
        "v2_opportunity": result["v2_opportunity"],
        "divergence_review": result["divergence_review"],
        "blocked": result["blocked"],
        "selection_quality": selection_quality,
    }
