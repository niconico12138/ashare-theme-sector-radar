"""Buy timing factor scoring for shadow-only paper entries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class BuyTimingConfig:
    min_amount_reference: float = 200000000.0
    chasing_change_pct: float = 7.0
    weak_liquidity_amount: float = 50000000.0


def evaluate_buy_timing(
    candidate: Mapping[str, Any],
    observation: Mapping[str, Any],
    config: BuyTimingConfig | None = None,
) -> dict[str, Any]:
    config = config or BuyTimingConfig()
    factor_scores = {
        "intraday_momentum": _score_intraday_momentum(observation),
        "amount_strength": _score_amount_strength(observation, config),
        "sector_confirmation": _score_sector_confirmation(candidate),
        "vwap_position": _score_vwap_position(observation),
        "anti_chasing": _score_anti_chasing(observation, config),
    }
    weights = {
        "intraday_momentum": 0.26,
        "amount_strength": 0.22,
        "sector_confirmation": 0.22,
        "vwap_position": 0.16,
        "anti_chasing": 0.14,
    }
    score = sum(factor_scores[name] * weights[name] for name in weights)
    risk_flags = _risk_flags(observation, config)
    if "weak_liquidity" in risk_flags:
        score -= 8.0
    if "chasing_risk" in risk_flags:
        score -= 10.0
    score = _clamp(score)
    return {
        "schema_version": "buy_timing_score.v1",
        "code": str(candidate.get("code") or observation.get("code") or ""),
        "buy_timing_score": score,
        "buy_timing_level": _level(score),
        "factor_scores": factor_scores,
        "risk_flags": risk_flags,
        "config": {
            "min_amount_reference": config.min_amount_reference,
            "chasing_change_pct": config.chasing_change_pct,
            "weak_liquidity_amount": config.weak_liquidity_amount,
        },
        "shadow_only": True,
        "paper_trading_only": True,
        "does_not_modify_official_scores": True,
        "no_execution_signals": True,
    }


def _score_intraday_momentum(observation: Mapping[str, Any]) -> float:
    change_pct = _float(observation.get("change_pct")) or 0.0
    return _clamp(50.0 + change_pct * 10.0)


def _score_amount_strength(observation: Mapping[str, Any], config: BuyTimingConfig) -> float:
    amount = _float(observation.get("amount")) or 0.0
    if config.min_amount_reference <= 0:
        return 50.0
    return _clamp(amount / config.min_amount_reference * 50.0)


def _score_sector_confirmation(candidate: Mapping[str, Any]) -> float:
    values = [
        _float(candidate.get("sector_short_validity_score")),
        _float(candidate.get("sector_intraday_breadth_score")),
        _float(candidate.get("intraday_sector_breadth_score")),
    ]
    values = [value for value in values if value is not None]
    return _clamp(sum(values) / len(values)) if values else 50.0


def _score_vwap_position(observation: Mapping[str, Any]) -> float:
    price = _float(observation.get("latest_price"))
    vwap = _float(observation.get("vwap"))
    if price is None or price <= 0 or vwap is None or vwap <= 0:
        return 50.0
    return _clamp(50.0 + (price - vwap) / vwap * 100.0 * 12.0)


def _score_anti_chasing(observation: Mapping[str, Any], config: BuyTimingConfig) -> float:
    change_pct = _float(observation.get("change_pct")) or 0.0
    price = _float(observation.get("latest_price"))
    high = _float(observation.get("intraday_high"))
    score = 86.0 - max(0.0, change_pct - 4.0) * 8.0
    if price is not None and high is not None and high > 0:
        near_high_pct = price / high * 100.0
        if near_high_pct >= 98.0 and change_pct >= config.chasing_change_pct:
            score -= 18.0
    return _clamp(score)


def _risk_flags(observation: Mapping[str, Any], config: BuyTimingConfig) -> list[str]:
    flags = []
    amount = _float(observation.get("amount")) or 0.0
    change_pct = _float(observation.get("change_pct")) or 0.0
    price = _float(observation.get("latest_price"))
    high = _float(observation.get("intraday_high"))
    if amount < config.weak_liquidity_amount:
        flags.append("weak_liquidity")
    if change_pct >= config.chasing_change_pct:
        if price is None or high is None or high <= 0 or price / high >= 0.98:
            flags.append("chasing_risk")
    return flags


def _level(score: float) -> str:
    if score >= 75.0:
        return "strong_watch"
    if score >= 65.0:
        return "watch"
    return "wait"


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 4)
