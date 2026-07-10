"""
Regime Router Shadow Score V5 模块 (shadow-only)

根据市场 regime 选择合适的影子评分：
- broad_up 使用 bull_regime_shadow_score (V4)
- broad_down 使用 defensive_shadow_score
- mixed 使用 blended score (50% defensive + 30% bull + 20% risk-adjusted)

不替代生产 decision_score，仅用于历史验证。
不删除 V4，V4 保留为 bull_regime_shadow_score。

设计原则：
1. 全部 shadow-only
2. 不改 production decision_score
3. 不改 production ranking
4. 不改现有 shadow V4
5. candidate 生成时可能没有真实 regime，默认使用 mixed profile
"""

from __future__ import annotations

from typing import Any

from theme_sector_radar.scoring.shadow_decision_score_v4 import compute_shadow_decision_score_v4
from theme_sector_radar.scoring.defensive_shadow_score import compute_defensive_shadow_score


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def compute_regime_router_shadow_score_v5(
    stock: dict,
    regime: str | None = None,
) -> dict:
    """Compute regime router shadow score V5.

    Args:
        stock: Candidate dict with all scoring fields.
        regime: Market regime ("broad_up", "broad_down", "mixed").
                If None, uses "mixed" profile.

    Returns:
        dict with regime_router_shadow_score_v5, regime_router_shadow_breakdown_v5,
        regime_router_shadow_tags_v5, regime_router_selected_profile,
        bull_regime_shadow_score, bull_regime_shadow_breakdown,
        defensive_shadow_score, defensive_shadow_breakdown, defensive_shadow_tags.
    """
    tags: list[str] = []
    breakdown: dict[str, Any] = {}

    # Compute bull score (V4) with broad_up profile
    bull_result = compute_shadow_decision_score_v4(stock, regime="broad_up")
    bull_score = bull_result["shadow_decision_score_v4"]
    bull_breakdown = bull_result["shadow_decision_breakdown_v4"]

    # Compute defensive score
    def_result = compute_defensive_shadow_score(stock)
    def_score = def_result["defensive_shadow_score"]
    def_breakdown = def_result["defensive_shadow_breakdown"]
    def_tags = def_result["defensive_shadow_tags"]

    # Select profile based on regime
    if regime == "broad_up":
        profile = "bull"
        v5_score = bull_score
        tags.append("v5_regime_bull")
    elif regime == "broad_down":
        profile = "defensive"
        v5_score = def_score
        tags.append("v5_regime_defensive")
    elif regime == "mixed":
        profile = "blended"
        # 50% defensive + 30% bull + 20% risk-adjusted
        risk_penalty = _safe_float(stock.get("risk_penalty_score", 50))
        risk_adjusted = _safe_float(stock.get("risk_penalty_score", 50))
        # Risk-adjusted component: neutral baseline with risk penalty bonus
        risk_component = 50.0 + (risk_penalty - 25) * 0.5
        risk_component = max(0.0, min(100.0, risk_component))

        v5_score = def_score * 0.50 + bull_score * 0.30 + risk_component * 0.20
        v5_score = max(0.0, min(100.0, v5_score))
        tags.append("v5_regime_blended")
        breakdown["blended_defensive_weight"] = 0.50
        breakdown["blended_bull_weight"] = 0.30
        breakdown["blended_risk_weight"] = 0.20
        breakdown["blended_risk_component"] = round(risk_component, 2)
    else:
        # Default to mixed profile
        profile = "blended"
        risk_penalty = _safe_float(stock.get("risk_penalty_score", 50))
        risk_component = 50.0 + (risk_penalty - 25) * 0.5
        risk_component = max(0.0, min(100.0, risk_component))

        v5_score = def_score * 0.50 + bull_score * 0.30 + risk_component * 0.20
        v5_score = max(0.0, min(100.0, v5_score))
        tags.append("v5_regime_default")
        breakdown["blended_defensive_weight"] = 0.50
        breakdown["blended_bull_weight"] = 0.30
        breakdown["blended_risk_weight"] = 0.20
        breakdown["blended_risk_component"] = round(risk_component, 2)

    breakdown["regime"] = regime or "default"
    breakdown["selected_profile"] = profile
    breakdown["bull_score"] = round(bull_score, 2)
    breakdown["defensive_score"] = round(def_score, 2)
    breakdown["v5_score"] = round(v5_score, 2)

    # Add def_tags to main tags
    tags.extend(def_tags)

    return {
        "regime_router_shadow_score_v5": round(v5_score, 2),
        "regime_router_shadow_breakdown_v5": breakdown,
        "regime_router_shadow_tags_v5": tags,
        "regime_router_selected_profile": profile,
        # Also return sub-scores for transparency
        "bull_regime_shadow_score": round(bull_score, 2),
        "bull_regime_shadow_breakdown": bull_breakdown,
        "defensive_shadow_score": round(def_score, 2),
        "defensive_shadow_breakdown": def_breakdown,
        "defensive_shadow_tags": def_tags,
    }
