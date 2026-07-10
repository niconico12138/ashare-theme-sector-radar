"""
影子决策分模块 (实验性)

基于风险拆分结果计算 shadow_decision_score_v2。
不替代生产 decision_score，仅用于历史验证。

公式:
    alpha_component =
        sector_trend_score  * 0.10
      + sector_burst_score  * 0.10
      + stock_short_score   * 0.25
      + stock_trend_score   * 0.15
      + sector_leader_score * 0.15
      + quant_score         * 0.10
      + agent_score         * 0.05

    elasticity_component = volatility_elasticity_score * 0.10

    risk_component =
        hard_risk_penalty * 1.0
      + drawdown_risk_score * 0.5

    shadow_score = alpha + elasticity - risk, clamped to [0, 100]
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


def compute_shadow_decision_score_v2(stock: dict) -> dict:
    """Compute shadow decision score v2 with decomposed risk.

    Args:
        stock: Candidate dict with all scoring fields PLUS:
            - hard_risk_penalty (from decompose_trade_risk)
            - volatility_elasticity_score (from decompose_trade_risk)
            - drawdown_risk_score (from decompose_trade_risk)

    Returns:
        dict with shadow_decision_score_v2, shadow_decision_breakdown_v2,
        shadow_decision_tags_v2.
    """
    tags: list[str] = []
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

    quant = _safe_float(stock.get("quant_score", 50))
    breakdown["quant_score"] = round(quant, 2)

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
        tags.append("agent_score_missing_neutral")

    # Risk decomposition inputs
    hard_risk = _safe_float(stock.get("hard_risk_penalty", 0))
    elasticity = _safe_float(stock.get("volatility_elasticity_score", 50))
    drawdown_risk = _safe_float(stock.get("drawdown_risk_score", 0))

    breakdown["hard_risk_penalty"] = round(hard_risk, 2)
    breakdown["volatility_elasticity_score"] = round(elasticity, 2)
    breakdown["drawdown_risk_score"] = round(drawdown_risk, 2)

    # === Alpha component ===
    alpha = (
        sector_trend * 0.10
        + sector_burst * 0.10
        + stock_short * 0.25
        + stock_trend * 0.15
        + leader_score * 0.15
        + quant * 0.10
        + agent_score * 0.05
    )
    breakdown["alpha_component"] = round(alpha, 2)

    # === Elasticity component ===
    elasticity_component = elasticity * 0.10
    breakdown["elasticity_component"] = round(elasticity_component, 2)

    # === Risk component ===
    risk_component = hard_risk * 1.0 + drawdown_risk * 0.5
    breakdown["risk_component"] = round(risk_component, 2)

    # === Final score ===
    shadow_score = alpha + elasticity_component - risk_component
    shadow_score = max(0.0, min(100.0, shadow_score))

    breakdown["total"] = round(shadow_score, 2)

    return {
        "shadow_decision_score_v2": round(shadow_score, 2),
        "shadow_decision_breakdown_v2": breakdown,
        "shadow_decision_tags_v2": tags,
    }
