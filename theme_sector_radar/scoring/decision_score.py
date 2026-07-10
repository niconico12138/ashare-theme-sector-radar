"""
统一决策分模块

融合板块分、个股分、龙头分、Agent 分、风险扣分，输出统一 decision_score。
自动检测 0-1 量纲并归一化到 0-100。
"""

from __future__ import annotations

from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_to_100(value: float) -> tuple[float, bool]:
    """Normalize a value to 0-100 scale. Returns (normalized, was_0_1)."""
    if value <= 1.5:
        return value * 100.0, True
    return value, False


def compute_decision_score(stock: dict) -> dict:
    """Compute unified decision score for a stock.

    Formula (v1):
        decision_score =
            sector_trend_score  * 0.15
          + sector_burst_score  * 0.15
          + stock_short_score   * 0.25
          + stock_trend_score   * 0.20
          + sector_leader_score * 0.15
          + agent_score         * 0.10
          - risk_penalty_score

    Field name compatibility:
        - sector_trend_score or trend_score
        - sector_burst_score or burst_score
        - agent_score: missing → neutral 50, breakdown marks agent_score_missing_neutral

    Auto-detects 0-1 scale values (<= 1.5) and normalizes to 0-100.

    Args:
        stock: Candidate dict with all scoring fields.

    Returns:
        dict with decision_score, decision_breakdown.
    """
    breakdown: dict[str, Any] = {}

    # === Extract and normalize scores ===
    raw_trend = _safe_float(
        stock.get("sector_trend_score", stock.get("trend_score", 50))
    )
    sector_trend, trend_was_01 = _normalize_to_100(raw_trend)
    breakdown["sector_trend_score"] = round(sector_trend, 2)
    breakdown["sector_trend_score_normalized_from_0_1"] = trend_was_01

    raw_burst = _safe_float(
        stock.get("sector_burst_score", stock.get("burst_score", 50))
    )
    sector_burst, burst_was_01 = _normalize_to_100(raw_burst)
    breakdown["sector_burst_score"] = round(sector_burst, 2)
    breakdown["sector_burst_score_normalized_from_0_1"] = burst_was_01

    stock_short = _safe_float(stock.get("stock_short_score", 50))
    breakdown["stock_short_score"] = round(stock_short, 2)

    stock_trend = _safe_float(stock.get("stock_trend_score", 50))
    breakdown["stock_trend_score"] = round(stock_trend, 2)

    leader_score = _safe_float(stock.get("sector_leader_score", 50))
    breakdown["sector_leader_score"] = round(leader_score, 2)

    # Agent score: neutral 50 if missing
    agent_raw = stock.get("agent_score")
    if agent_raw is not None:
        agent_score = _safe_float(agent_raw, 50)
        breakdown["agent_score"] = round(agent_score, 2)
        breakdown["agent_score_missing_neutral"] = False
    else:
        agent_score = 50.0
        breakdown["agent_score"] = 50.0
        breakdown["agent_score_missing_neutral"] = True

    risk_penalty = _safe_float(stock.get("risk_penalty_score", 0))
    breakdown["risk_penalty_score"] = round(risk_penalty, 2)

    # === Weighted sum ===
    weighted_sum = (
        sector_trend * 0.15
        + sector_burst * 0.15
        + stock_short * 0.25
        + stock_trend * 0.20
        + leader_score * 0.15
        + agent_score * 0.10
    )

    # === Apply risk penalty ===
    decision = weighted_sum - risk_penalty

    # Clamp to 0-100
    decision = max(0.0, min(100.0, decision))

    breakdown["weighted_sum"] = round(weighted_sum, 2)
    breakdown["total"] = round(decision, 2)

    return {
        "decision_score": round(decision, 2),
        "decision_breakdown": breakdown,
    }
