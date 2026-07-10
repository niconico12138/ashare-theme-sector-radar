"""
影子决策分 V4 模块 (shadow-only)

基于 regime-aware 权重计算 shadow_decision_score_v4。
不替代生产 decision_score，仅用于历史验证。

设计原则:
1. 全部 shadow-only
2. 不改 production decision_score
3. 不改 production ranking
4. 不改现有 shadow v3
5. v4 支持 regime-aware 权重，但只在 shadow 输出中体现

Regime-aware 权重:
broad_up:
- 提高 stock_trend_score / volatility_elasticity_score
- 降低防御型 risk_penalty 的主导性
- 保留 hard/trade risk 扣分

broad_down:
- 提高 risk_penalty_score / hard_risk_penalty / trade_risk_penalty
- 提高 close_position / drawdown control
- 降低弹性项权重

mixed:
- 平衡 trend、short_v2、risk
- 更重视回撤控制和成交质量
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


# Regime-specific weight profiles
REGIME_PROFILES = {
    "broad_up": {
        "name": "broad_up",
        "description": "Bullish market: higher trend/elasticity, lower risk dominance",
        "alpha_weights": {
            "sector_trend": 0.15,      # Higher trend weight
            "sector_burst": 0.12,
            "stock_short_v2": 0.22,
            "stock_trend": 0.20,       # Higher trend weight
            "leader_score": 0.10,
            "agent_score": 0.08,
            "quant_score": 0.08,
        },
        "elasticity_weight": 0.12,     # Higher elasticity bonus
        "risk_weights": {
            "hard_risk": 0.6,          # Lower risk dominance
            "trade_risk": 0.5,
            "drawdown_risk": 0.3,
        },
    },
    "broad_down": {
        "name": "broad_down",
        "description": "Bearish market: higher risk/control, lower elasticity",
        "alpha_weights": {
            "sector_trend": 0.08,      # Lower trend weight
            "sector_burst": 0.10,
            "stock_short_v2": 0.25,
            "stock_trend": 0.12,       # Lower trend weight
            "leader_score": 0.15,
            "agent_score": 0.08,
            "quant_score": 0.07,
        },
        "elasticity_weight": 0.04,     # Lower elasticity bonus
        "risk_weights": {
            "hard_risk": 1.0,          # Higher risk dominance
            "trade_risk": 0.8,
            "drawdown_risk": 0.6,
        },
    },
    "mixed": {
        "name": "mixed",
        "description": "Mixed market: balanced weights with drawdown control",
        "alpha_weights": {
            "sector_trend": 0.12,
            "sector_burst": 0.12,
            "stock_short_v2": 0.24,
            "stock_trend": 0.16,
            "leader_score": 0.12,
            "agent_score": 0.08,
            "quant_score": 0.07,
        },
        "elasticity_weight": 0.08,
        "risk_weights": {
            "hard_risk": 0.8,
            "trade_risk": 0.7,
            "drawdown_risk": 0.5,
        },
    },
    "default": {
        "name": "default",
        "description": "Default profile (same as mixed)",
        "alpha_weights": {
            "sector_trend": 0.12,
            "sector_burst": 0.12,
            "stock_short_v2": 0.24,
            "stock_trend": 0.16,
            "leader_score": 0.12,
            "agent_score": 0.08,
            "quant_score": 0.07,
        },
        "elasticity_weight": 0.08,
        "risk_weights": {
            "hard_risk": 0.8,
            "trade_risk": 0.7,
            "drawdown_risk": 0.5,
        },
    },
}


def compute_shadow_decision_score_v4(
    stock: dict,
    regime: str | None = None,
) -> dict:
    """Compute shadow decision score v4 with regime-aware weights.

    Args:
        stock: Candidate dict with all scoring fields PLUS:
            - stock_short_score_v2 (from compute_stock_short_score_v2)
            - hard_risk_penalty (from decompose_trade_risk)
            - trade_risk_penalty (from decompose_trade_risk)
            - volatility_elasticity_score (from decompose_trade_risk)
            - drawdown_risk_score (from decompose_trade_risk)
        regime: Market regime ("broad_up", "broad_down", "mixed").
                If None, uses "default" profile.

    Returns:
        dict with shadow_decision_score_v4, shadow_decision_breakdown_v4,
        shadow_decision_v4_tags, shadow_decision_v4_regime_profile.
    """
    tags: list[str] = []
    breakdown: dict[str, Any] = {}

    # Select regime profile
    if regime and regime in REGIME_PROFILES:
        profile = REGIME_PROFILES[regime]
        tags.append(f"v4_regime_{regime}")
    else:
        profile = REGIME_PROFILES["default"]
        tags.append("v4_regime_default")

    breakdown["regime_profile"] = profile["name"]
    breakdown["regime_description"] = profile["description"]

    # === Extract and normalize scores ===
    raw_trend = _safe_float(
        stock.get("sector_trend_score", stock.get("trend_score", 50))
    )
    sector_trend, trend_was_01 = _normalize_to_100(raw_trend)
    breakdown["sector_trend_score"] = round(sector_trend, 2)

    raw_burst = _safe_float(
        stock.get("sector_burst_score", stock.get("burst_score", 50))
    )
    sector_burst, burst_was_01 = _normalize_to_100(raw_burst)
    breakdown["sector_burst_score"] = round(sector_burst, 2)

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
        tags.append("v4_short_score_v1_fallback")

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
        tags.append("v4_agent_score_missing_neutral")

    # Risk decomposition inputs
    hard_risk = _safe_float(stock.get("hard_risk_penalty", 0))
    trade_risk = _safe_float(stock.get("trade_risk_penalty", 0))
    elasticity = _safe_float(stock.get("volatility_elasticity_score", 50))
    drawdown_risk = _safe_float(stock.get("drawdown_risk_score", 0))

    breakdown["hard_risk_penalty"] = round(hard_risk, 2)
    breakdown["trade_risk_penalty"] = round(trade_risk, 2)
    breakdown["volatility_elasticity_score"] = round(elasticity, 2)
    breakdown["drawdown_risk_score"] = round(drawdown_risk, 2)

    # === Alpha component (regime-aware weights) ===
    aw = profile["alpha_weights"]
    alpha = (
        sector_trend * aw["sector_trend"]
        + sector_burst * aw["sector_burst"]
        + stock_short * aw["stock_short_v2"]
        + stock_trend * aw["stock_trend"]
        + leader_score * aw["leader_score"]
        + agent_score * aw["agent_score"]
        + quant * aw["quant_score"]
    )
    breakdown["alpha_component"] = round(alpha, 2)
    breakdown["alpha_weights"] = aw

    # === Elasticity component (regime-aware) ===
    ew = profile["elasticity_weight"]
    elasticity_bonus = max(0, (elasticity - 50) / 50.0) * (ew * 100)
    breakdown["elasticity_bonus"] = round(elasticity_bonus, 2)
    breakdown["elasticity_weight"] = ew

    # === Risk component (regime-aware) ===
    rw = profile["risk_weights"]
    risk_component = (
        hard_risk * rw["hard_risk"]
        + trade_risk * rw["trade_risk"]
        + drawdown_risk * rw["drawdown_risk"]
    )
    breakdown["risk_component"] = round(risk_component, 2)
    breakdown["risk_weights"] = rw

    # === Final score ===
    shadow_score = alpha + elasticity_bonus - risk_component
    shadow_score = max(0.0, min(100.0, shadow_score))

    breakdown["total"] = round(shadow_score, 2)

    # Diagnostic tags
    if hard_risk > 20:
        tags.append("v4_high_hard_risk")
    if trade_risk > 15:
        tags.append("v4_high_trade_risk")
    if elasticity > 70:
        tags.append("v4_high_elasticity")
    if drawdown_risk > 20:
        tags.append("v4_high_drawdown_risk")

    return {
        "shadow_decision_score_v4": round(shadow_score, 2),
        "shadow_decision_breakdown_v4": breakdown,
        "shadow_decision_v4_tags": tags,
        "shadow_decision_v4_regime_profile": profile["name"],
    }
