"""
防御型影子评分模块 (shadow-only)

专门服务 broad_down / mixed 市场状态。
降低追涨弹性，强调防守、回撤、收盘质量、风险过滤。
不替代生产 decision_score，仅用于历史验证和 regime_router_shadow_score_v5。

设计目标：
1. risk_penalty_score 正向使用（all_weather_alpha）
2. hard_risk_penalty / trade_risk_penalty / drawdown_risk_score 扣分
3. close_position_score 加分（收盘质量）
4. stock_short_score_v2 中防御性组件加分
5. volatility_elasticity_score 不加分，必要时轻微扣分
6. sector_leader_score 低分扣分
7. data_quality_penalty

分数范围 0-100，缺少字段时降级不崩。
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


def _scale_to_range(value: float, in_min: float, in_max: float,
                    out_min: float, out_max: float) -> float:
    """Linearly scale value from [in_min, in_max] to [out_min, out_max]."""
    if in_max <= in_min:
        return (out_min + out_max) / 2.0
    clamped = max(in_min, min(in_max, value))
    return out_min + (clamped - in_min) / (in_max - in_min) * (out_max - out_min)


def compute_defensive_shadow_score(stock: dict) -> dict:
    """Compute defensive shadow score for bearish/mixed markets.

    Args:
        stock: Candidate dict with scoring fields.

    Returns:
        dict with defensive_shadow_score, defensive_shadow_breakdown, defensive_shadow_tags.
    """
    tags: list[str] = []
    breakdown: dict[str, Any] = {}

    # === Extract fields ===
    risk_penalty = _safe_float(stock.get("risk_penalty_score", 50))
    hard_risk = _safe_float(stock.get("hard_risk_penalty", 0))
    trade_risk = _safe_float(stock.get("trade_risk_penalty", 0))
    drawdown_risk = _safe_float(stock.get("drawdown_risk_score", 0))
    elasticity = _safe_float(stock.get("volatility_elasticity_score", 50))
    leader_score = _safe_float(stock.get("sector_leader_score", 50))
    stock_short_v2 = _safe_float(stock.get("stock_short_score_v2", 0))
    stock_short_v1 = _safe_float(stock.get("stock_short_score", 50))
    quant_score = _safe_float(stock.get("quant_score", 50))
    final_score = _safe_float(stock.get("final_score", 0))

    # OHLC for close position
    high = _safe_float(stock.get("high", 0))
    low = _safe_float(stock.get("low", 0))
    close = _safe_float(stock.get("close", 0))
    change_pct = _safe_float(stock.get("change_pct", stock.get("pct_change", 0)))
    amount = _safe_float(stock.get("amount", 0))
    volume = _safe_float(stock.get("volume", 0))

    # ================================================================
    # Component 1: Risk Penalty Score (正向使用, 0-25)
    # risk_penalty_score 是 all_weather_alpha，正向使用
    # ================================================================
    risk_bonus = _scale_to_range(risk_penalty, 0, 50, 0, 25)
    breakdown["risk_penalty_bonus"] = round(risk_bonus, 2)
    breakdown["risk_penalty_score_raw"] = round(risk_penalty, 2)

    # ================================================================
    # Component 2: Hard Risk Penalty (扣分, 0 to -20)
    # ================================================================
    hard_risk_deduction = -_scale_to_range(hard_risk, 0, 50, 0, 20)
    breakdown["hard_risk_deduction"] = round(hard_risk_deduction, 2)
    if hard_risk > 20:
        tags.append("defensive_high_hard_risk")

    # ================================================================
    # Component 3: Trade Risk Penalty (扣分, 0 to -15)
    # ================================================================
    trade_risk_deduction = -_scale_to_range(trade_risk, 0, 40, 0, 15)
    breakdown["trade_risk_deduction"] = round(trade_risk_deduction, 2)
    if trade_risk > 15:
        tags.append("defensive_high_trade_risk")

    # ================================================================
    # Component 4: Drawdown Risk Score (扣分, 0 to -15)
    # ================================================================
    drawdown_deduction = -_scale_to_range(drawdown_risk, 0, 50, 0, 15)
    breakdown["drawdown_deduction"] = round(drawdown_deduction, 2)
    if drawdown_risk > 20:
        tags.append("defensive_high_drawdown_risk")

    # ================================================================
    # Component 5: Close Position Score (加分, 0-20)
    # 收盘质量高 = 防御性强
    # ================================================================
    if high > 0 and low > 0 and high > low:
        close_pos = max(0.0, min(1.0, (close - low) / (high - low)))
        close_position_score = close_pos * 20.0
        breakdown["close_position_raw"] = round(close_pos, 4)
    else:
        # Fallback: use change_pct
        if change_pct > 3:
            close_position_score = 15.0
        elif change_pct > 0:
            close_position_score = 10.0
        elif change_pct > -2:
            close_position_score = 6.0
        else:
            close_position_score = 2.0
        tags.append("defensive_close_position_fallback")
    breakdown["close_position_score"] = round(close_position_score, 2)

    # ================================================================
    # Component 6: Short Score V2 (防御性组件, 0-15)
    # 使用 V2 但降低权重，避免追涨
    # ================================================================
    if stock_short_v2 > 0:
        # 降低权重，避免追涨
        short_component = _scale_to_range(stock_short_v2, 0, 100, 0, 15)
    elif stock_short_v1 > 0:
        short_component = _scale_to_range(stock_short_v1, 0, 100, 0, 15)
        tags.append("defensive_short_v1_fallback")
    else:
        short_component = _scale_to_range(quant_score, 0, 100, 0, 12)
        tags.append("defensive_short_fallback")
    breakdown["short_score_component"] = round(short_component, 2)

    # ================================================================
    # Component 7: Volatility Elasticity (不加分，轻微扣分, -5 to 0)
    # 在防御型评分中，高弹性不是优势
    # ================================================================
    if elasticity > 70:
        elasticity_penalty = -3.0
        tags.append("defensive_high_elasticity_penalty")
    elif elasticity > 60:
        elasticity_penalty = -1.0
    else:
        elasticity_penalty = 0.0
    breakdown["elasticity_penalty"] = round(elasticity_penalty, 2)

    # ================================================================
    # Component 8: Sector Leader Score (低分扣分, -10 to 0)
    # 防止跟风弱股
    # ================================================================
    if leader_score < 30:
        leader_penalty = -10.0
        tags.append("defensive_weak_leader")
    elif leader_score < 50:
        leader_penalty = -5.0
    elif leader_score < 70:
        leader_penalty = -2.0
    else:
        leader_penalty = 0.0
    breakdown["leader_penalty"] = round(leader_penalty, 2)

    # ================================================================
    # Component 9: Data Quality Penalty (0 to -5)
    # ================================================================
    data_quality_penalty = 0.0
    if amount <= 0 and volume <= 0:
        data_quality_penalty -= 3.0
        tags.append("defensive_missing_volume_amount")
    if change_pct == 0:
        data_quality_penalty -= 2.0
        tags.append("defensive_no_change_data")
    data_quality_penalty = max(-5.0, data_quality_penalty)
    breakdown["data_quality_penalty"] = round(data_quality_penalty, 2)

    # ================================================================
    # Total Score
    # ================================================================
    raw_total = (
        risk_bonus
        + hard_risk_deduction
        + trade_risk_deduction
        + drawdown_deduction
        + close_position_score
        + short_component
        + elasticity_penalty
        + leader_penalty
        + data_quality_penalty
    )
    total = max(0.0, min(100.0, raw_total))

    breakdown["total_raw"] = round(raw_total, 2)
    breakdown["total"] = round(total, 2)

    return {
        "defensive_shadow_score": round(total, 2),
        "defensive_shadow_breakdown": breakdown,
        "defensive_shadow_tags": tags,
    }
