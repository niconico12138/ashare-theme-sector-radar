"""
影子决策分 V3 模块 (shadow-only)

基于风险拆分和 stock_short_score_v2 计算 shadow_decision_score_v3。
不替代生产 decision_score，仅用于历史验证。

设计原则:
1. 不改 production decision_score
2. 融合 stock_short_score_v2
3. 使用拆分后的风险字段
4. volatility_elasticity_score 不直接作为扣分，可作为机会/弹性项
5. hard_risk_penalty 和 trade_risk_penalty 才是主要风险扣分
6. 输出解释 breakdown

公式:
    alpha_component =
        sector_trend_score  * 0.12
      + sector_burst_score  * 0.12
      + stock_short_score_v2 * 0.25
      + stock_trend_score   * 0.18
      + sector_leader_score * 0.13
      + agent_score         * 0.08
      + quant_score         * 0.07

    elasticity_component = volatility_elasticity_score * 0.08

    risk_component =
        hard_risk_penalty * 0.8
      + trade_risk_penalty * 0.6
      + drawdown_risk_score * 0.4

    shadow_score_v3 = alpha + elasticity - risk, clamped to [0, 100]
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


def compute_shadow_decision_score_v3(stock: dict) -> dict:
    """Compute shadow decision score v3 with decomposed risk and v2 short score.

    Args:
        stock: Candidate dict with all scoring fields PLUS:
            - stock_short_score_v2 (from compute_stock_short_score_v2)
            - hard_risk_penalty (from decompose_trade_risk)
            - trade_risk_penalty (from decompose_trade_risk)
            - volatility_elasticity_score (from decompose_trade_risk)
            - drawdown_risk_score (from decompose_trade_risk)

    Returns:
        dict with shadow_decision_score_v3, shadow_decision_breakdown_v3,
        shadow_decision_v3_tags.
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

    # Use v2 short score if available, fallback to v1
    stock_short_v2 = _safe_float(stock.get("stock_short_score_v2", 0))
    if stock_short_v2 > 0:
        stock_short = stock_short_v2
        breakdown["stock_short_score_source"] = "v2"
        breakdown["stock_short_score_v2"] = round(stock_short_v2, 2)
    else:
        stock_short = _safe_float(stock.get("stock_short_score", 50))
        breakdown["stock_short_score_source"] = "v1_fallback"
        breakdown["stock_short_score_v1"] = round(stock_short, 2)
        tags.append("v3_short_score_v1_fallback")

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
        tags.append("v3_agent_score_missing_neutral")

    # Risk decomposition inputs
    hard_risk = _safe_float(stock.get("hard_risk_penalty", 0))
    trade_risk = _safe_float(stock.get("trade_risk_penalty", 0))
    elasticity = _safe_float(stock.get("volatility_elasticity_score", 50))
    drawdown_risk = _safe_float(stock.get("drawdown_risk_score", 0))

    breakdown["hard_risk_penalty"] = round(hard_risk, 2)
    breakdown["trade_risk_penalty"] = round(trade_risk, 2)
    breakdown["volatility_elasticity_score"] = round(elasticity, 2)
    breakdown["drawdown_risk_score"] = round(drawdown_risk, 2)

    # === Alpha component ===
    alpha = (
        sector_trend * 0.12
        + sector_burst * 0.12
        + stock_short * 0.25
        + stock_trend * 0.18
        + leader_score * 0.13
        + agent_score * 0.08
        + quant * 0.07
    )
    breakdown["alpha_component"] = round(alpha, 2)

    # === Elasticity component (opportunity, not penalty) ===
    # elasticity is 0-100, centered at 50
    # Only add bonus when elasticity > 50 (high elasticity)
    elasticity_bonus = max(0, (elasticity - 50) / 50.0) * 8.0
    breakdown["elasticity_bonus"] = round(elasticity_bonus, 2)
    tags.append("v3_elasticity_as_opportunity")

    # === Risk component ===
    # hard_risk and trade_risk are the main deductions
    # drawdown_risk is secondary
    risk_component = hard_risk * 0.8 + trade_risk * 0.6 + drawdown_risk * 0.4
    breakdown["risk_component"] = round(risk_component, 2)

    # === Final score ===
    shadow_score = alpha + elasticity_bonus - risk_component
    shadow_score = max(0.0, min(100.0, shadow_score))

    breakdown["total"] = round(shadow_score, 2)

    # Diagnostic tags
    if hard_risk > 20:
        tags.append("v3_high_hard_risk")
    if trade_risk > 15:
        tags.append("v3_high_trade_risk")
    if elasticity > 70:
        tags.append("v3_high_elasticity")
    if drawdown_risk > 20:
        tags.append("v3_high_drawdown_risk")

    return {
        "shadow_decision_score_v3": round(shadow_score, 2),
        "shadow_decision_breakdown_v3": breakdown,
        "shadow_decision_v3_tags": tags,
    }
