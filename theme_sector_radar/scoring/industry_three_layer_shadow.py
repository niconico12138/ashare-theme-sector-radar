"""Shadow-only decomposition of industry direction into three layers."""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

from ..data.return_validation import trusted_daily_returns
from ..models import SectorSnapshot
from .industry_score import (
    _continuous_breakout_quality,
    _drawdown_control_score,
    _positive_trend_fit,
)


def _clip(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    if not math.isfinite(value):
        raise ValueError("three-layer shadow calculations must remain finite")
    return max(lower, min(upper, value))


def _finite_float(value: Any) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("three-layer shadow inputs must be finite")
    return result


def _percentile(value: Any) -> float:
    result = _finite_float(value)
    if not 0.0 <= result <= 1.0:
        raise ValueError("three-layer shadow percentile must be within [0, 1]")
    return result


def _compound_return(recent_returns: list[float]) -> float:
    wealth = 1.0
    for value in recent_returns:
        factor = 1.0 + float(value) / 100.0
        if not math.isfinite(factor):
            raise ValueError("three-layer shadow calculations must remain finite")
        wealth *= factor
        if not math.isfinite(wealth):
            raise ValueError("three-layer shadow calculations must remain finite")
    return _finite_float((wealth - 1.0) * 100.0)


def _time_series_layer(recent_returns: list[float]) -> Dict[str, Any]:
    if len(recent_returns) < 20:
        return {"score": None, "status": "unavailable", "history_days": len(recent_returns)}

    values = recent_returns[-20:]
    compound_return = _compound_return(values)
    trend_fit = _finite_float(_positive_trend_fit(values))
    breakout_quality = _finite_float(_continuous_breakout_quality(values))
    drawdown_control = _finite_float(_drawdown_control_score(values))
    score = (
        25.0 * trend_fit
        + 20.0 * breakout_quality
        + 15.0 * sum(value > 0 for value in values[-10:]) / 10.0
        + 10.0 * sum(value > 0 for value in values) / 20.0
        + 15.0 * (drawdown_control / 3.0)
        + 15.0 * _clip(compound_return / 10.0)
    )
    return {
        "score": round(_finite_float(score), 2),
        "status": "ok",
        "history_days": 20,
    }


def _cross_section_layer(
    recent_returns: list[float],
    percentiles: Dict[int, float],
) -> Dict[str, Any]:
    score = 0.0
    effective_windows = []
    for window, weight in ((5, 35.0), (10, 35.0), (20, 30.0)):
        if len(recent_returns) >= window and window in percentiles:
            score += _clip(float(percentiles[window])) * weight
            effective_windows.append(window)
    if not effective_windows:
        return {"score": None, "status": "unavailable", "effective_windows": []}
    return {
        "score": round(_finite_float(score), 2),
        "status": "ok" if effective_windows == [5, 10, 20] else "partial",
        "effective_windows": effective_windows,
    }


def _rank_momentum_layer(rank_percentiles: list[Optional[float]]) -> Dict[str, Any]:
    recent = rank_percentiles[-5:]
    missing_endpoint_count = sum(value is None for value in recent)
    if len(recent) < 5 or missing_endpoint_count:
        return {
            "score": None,
            "status": "unavailable",
            "history_days": len(rank_percentiles),
            "missing_endpoint_count": missing_endpoint_count,
        }

    values = [_clip(float(value)) for value in recent if value is not None]
    slope = values[-1] - values[0]
    recent_step = values[-1] - values[-2]
    prior_step = (values[-2] - values[0]) / 3.0
    acceleration = recent_step - prior_step
    residence = sum(value >= 0.75 for value in values) / 5.0
    score = (
        30.0 * values[-1]
        + 35.0 * _clip((slope + 0.5) / 1.0)
        + 15.0 * _clip((acceleration + 0.25) / 0.5)
        + 20.0 * residence
    )
    return {
        "score": round(score, 2),
        "status": "ok",
        "history_days": len(rank_percentiles),
        "current_percentile": round(values[-1], 4),
        "slope_5d": round(slope, 4),
        "acceleration": round(acceleration, 4),
        "top_quartile_residence_5d": round(residence, 4),
    }


def calculate_industry_three_layer_shadow(
    snapshot: SectorSnapshot,
    trend_features: Optional[Dict[str, Any]] = None,
    *,
    risk_flags: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """Return shadow layers without changing any production score."""
    del snapshot
    features = trend_features or {}
    recent_returns = trusted_daily_returns(features.get("recent_returns", []))
    percentiles = {
        int(window): _percentile(value)
        for window, value in features.get("relative_strength_percentiles", {}).items()
    }
    time_series = _time_series_layer(recent_returns)
    cross_section = _cross_section_layer(recent_returns, percentiles)
    rank_momentum = _rank_momentum_layer(
        [
            None if value is None else _percentile(value)
            for value in features.get(
                "daily_rank_percentile_slots",
                features.get("daily_rank_percentiles", []),
            )
        ]
    )
    direction_score = None
    if all(
        layer["status"] == "ok"
        for layer in (time_series, cross_section, rank_momentum)
    ):
        direction_score = round(
            0.5 * float(time_series["score"])
            + 0.3 * float(cross_section["score"])
            + 0.2 * float(rank_momentum["score"]),
            2,
        )
        direction_score = _finite_float(direction_score)
    direction_state = "unavailable"
    if direction_score is not None:
        time_score = float(time_series["score"])
        cross_score = float(cross_section["score"])
        momentum_score = float(rank_momentum["score"])
        slope = float(rank_momentum["slope_5d"])
        if risk_flags and time_score >= 60.0 and cross_score >= 65.0:
            direction_state = "risk_observation"
        elif (
            time_score >= 60.0
            and cross_score >= 70.0
            and momentum_score >= 65.0
            and slope >= 0.2
        ):
            direction_state = "emerging_acceleration"
        elif time_score >= 60.0 and cross_score >= 70.0 and momentum_score >= 55.0:
            direction_state = "stable_core"
        elif time_score < 50.0 and cross_score >= 60.0 and momentum_score >= 65.0:
            direction_state = "pulse_confirmation_required"
        elif time_score >= 55.0 and cross_score >= 60.0 and slope <= -0.15:
            direction_state = "trend_weakening"
        elif time_score < 45.0 and cross_score < 50.0 and momentum_score < 45.0:
            direction_state = "weakening"
        else:
            direction_state = "watch"
    return {
        "mode": "paper_shadow_research_only",
        "weights": {"time_series": 0.5, "cross_section": 0.3, "rank_momentum": 0.2},
        "time_series": time_series,
        "cross_section": cross_section,
        "rank_momentum": rank_momentum,
        "direction_score_shadow": direction_score,
        "direction_state": direction_state,
        "risk_flags_observed": list(risk_flags or []),
    }
