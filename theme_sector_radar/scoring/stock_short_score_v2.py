"""
个股短线评分 V2 模块 (shadow-only) — 校准版

基于更细粒度的组件计算短线动量分。
不替代生产 stock_short_score，仅用于历史验证和 shadow_decision_score_v3/v4。

校准目标：spread >= 30，避免分数塌缩。

组件:
1. close_position_score (0-25): (close - low) / (high - low) — 收盘位置
2. three_day_relative_strength (0-20): 3日相对强度
3. five_day_relative_strength (0-15): 5日相对强度
4. volume_expansion_quality (0-15): 量能扩张质量
5. sector_relative_strength (0-10): 板块相对强度
6. high_rejection_penalty (0 to -15): 冲高回落惩罚
7. overheat_penalty (0 to -15): 过热惩罚
8. data_quality_penalty (0 to -3): 数据质量惩罚

总分 0-100，缺少字段时降级但不崩溃。
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


def _calc_close_position(high: float, low: float, close: float) -> float:
    """Calculate close position: (close - low) / (high - low).
    Returns 0.5 if range is zero."""
    if high <= low or high <= 0:
        return 0.5
    return max(0.0, min(1.0, (close - low) / (high - low)))


def _continuous_momentum(value: float, neg_scale: float = -15, pos_scale: float = 25,
                         midpoint: float = 0.0, steepness: float = 0.3) -> float:
    """Continuous sigmoid-style scaling for momentum components.
    Returns value in [0, pos_scale] range."""
    import math
    x = (value - midpoint) * steepness
    sigmoid = 1.0 / (1.0 + math.exp(-x))
    return neg_scale + (pos_scale - neg_scale) * sigmoid


def compute_stock_short_score_v2(
    stock: dict,
    bars: list[dict] | None = None,
    sector_context: dict | None = None,
) -> dict:
    """Compute stock short score v2 (0-100) — calibrated version.

    Args:
        stock: Stock dict with fields like change_pct, amount, volume,
               turnover_rate, volume_ratio, high, low, close,
               stock_short_score, sector_burst_score, etc.
        bars: Optional list of daily bar dicts sorted newest-first.
              Each bar: date, open, high, low, close, volume, amount.
        sector_context: Optional sector-level context.

    Returns:
        dict with stock_short_score_v2, stock_short_breakdown_v2, stock_short_v2_tags.
    """
    tags: list[str] = []
    breakdown: dict[str, Any] = {}
    has_bars = bars and len(bars) >= 2

    # Extract fields
    change_pct = _safe_float(stock.get("change_pct", stock.get("pct_change", 0)))
    amount = _safe_float(stock.get("amount", 0))
    volume = _safe_float(stock.get("volume", 0))
    turnover_rate = _safe_float(stock.get("turnover_rate", 0))
    volume_ratio = _safe_float(stock.get("volume_ratio", 0))
    quant_score = _safe_float(stock.get("quant_score", 0))
    final_score = _safe_float(stock.get("final_score", 0))
    relevance_score = _safe_float(stock.get("relevance_score", 0))
    source_pool = stock.get("source_pool", "")

    # Get OHLC from stock or bars
    today_high = _safe_float(stock.get("high", 0))
    today_low = _safe_float(stock.get("low", 0))
    today_close = _safe_float(stock.get("close", 0))
    today_open = _safe_float(stock.get("open", 0))

    if has_bars and (today_high <= 0 or today_low <= 0):
        bar = bars[0]
        today_high = _safe_float(bar.get("high", today_high))
        today_low = _safe_float(bar.get("low", today_low))
        today_close = _safe_float(bar.get("close", today_close))
        today_open = _safe_float(bar.get("open", today_open))

    # Collect bar data
    closes: list[float] = []
    volumes: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    if has_bars:
        for bar in bars:
            closes.append(_safe_float(bar.get("close", 0)))
            volumes.append(_safe_float(bar.get("volume", 0)))
            highs.append(_safe_float(bar.get("high", 0)))
            lows.append(_safe_float(bar.get("low", 0)))

    # Sector context
    sector_burst = _safe_float(sector_context.get("burst_score", stock.get("burst_score", 0))) if sector_context else _safe_float(stock.get("burst_score", 0))
    sector_trend = _safe_float(sector_context.get("trend_score", stock.get("trend_score", 0))) if sector_context else _safe_float(stock.get("trend_score", 0))

    # Existing v1 score for fallback reference
    v1_score = _safe_float(stock.get("stock_short_score", 0))

    # ================================================================
    # Component 1: Close Position Score (0-25)
    # (close - low) / (high - low) — 收盘在日内的位置
    # 使用连续缩放而非阶梯
    # ================================================================
    if today_high > 0 and today_low > 0 and today_high > today_low:
        close_pos = _calc_close_position(today_high, today_low, today_close)
        # Continuous scaling: 0->0, 0.5->10, 1.0->25
        close_position_score = close_pos * 25.0
        breakdown["close_position_raw"] = round(close_pos, 4)
    elif has_bars and len(highs) >= 1 and len(lows) >= 1:
        close_pos = _calc_close_position(highs[0], lows[0], closes[0])
        close_position_score = close_pos * 25.0
        breakdown["close_position_raw"] = round(close_pos, 4)
        tags.append("v2_close_position_from_bars")
    else:
        # Fallback: use v1_score or quant_score for better differentiation
        if v1_score > 0:
            close_position_score = _scale_to_range(v1_score, 20, 90, 5, 23)
        elif quant_score > 0:
            close_position_score = _scale_to_range(quant_score, 30, 90, 5, 22)
        elif final_score > 0:
            close_position_score = _scale_to_range(final_score, 40, 85, 5, 20)
        else:
            close_position_score = _scale_to_range(change_pct, -5, 8, 3, 22)
        tags.append("v2_close_position_fallback")
    breakdown["close_position_score"] = round(close_position_score, 2)

    # ================================================================
    # Component 2: 3-Day Relative Strength (0-20)
    # 使用连续缩放
    # ================================================================
    if has_bars and len(closes) >= 4:
        close_3d_ago = closes[3] if len(closes) > 3 else closes[-1]
        if close_3d_ago > 0:
            rs_3d = (closes[0] - close_3d_ago) / close_3d_ago * 100
        else:
            rs_3d = 0.0
        # Continuous scaling: -10% -> 0, 0% -> 8, +20% -> 20
        three_day_rs = _scale_to_range(rs_3d, -10, 20, 0, 20)
        breakdown["three_day_rs_raw"] = round(rs_3d, 4)
    else:
        # Fallback: use v1_score or other available fields
        if v1_score > 0:
            three_day_rs = _scale_to_range(v1_score, 20, 90, 3, 18)
        elif quant_score > 0:
            three_day_rs = _scale_to_range(quant_score, 30, 90, 3, 17)
        else:
            three_day_rs = _scale_to_range(change_pct, -5, 8, 2, 18)
        tags.append("v2_three_day_rs_fallback")
    breakdown["three_day_rs_score"] = round(three_day_rs, 2)

    # ================================================================
    # Component 3: 5-Day Relative Strength (0-15)
    # ================================================================
    if has_bars and len(closes) >= 6:
        close_5d_ago = closes[5] if len(closes) > 5 else closes[-1]
        if close_5d_ago > 0:
            rs_5d = (closes[0] - close_5d_ago) / close_5d_ago * 100
        else:
            rs_5d = 0.0
        # Continuous scaling: -15% -> 0, 0% -> 5, +30% -> 15
        five_day_rs = _scale_to_range(rs_5d, -15, 30, 0, 15)
        breakdown["five_day_rs_raw"] = round(rs_5d, 4)
    else:
        # Fallback: use v1_score or other available fields
        if v1_score > 0:
            five_day_rs = _scale_to_range(v1_score, 20, 90, 2, 14)
        elif quant_score > 0:
            five_day_rs = _scale_to_range(quant_score, 35, 85, 2, 14)
        else:
            five_day_rs = _scale_to_range(change_pct, -5, 8, 1, 13)
        tags.append("v2_five_day_rs_fallback")
    breakdown["five_day_rs_score"] = round(five_day_rs, 2)

    # ================================================================
    # Component 4: Volume Expansion Quality (0-15)
    # 不只看放量，还看收盘强度
    # ================================================================
    if has_bars and len(volumes) >= 5:
        avg_vol_5 = sum(volumes[1:6]) / min(5, len(volumes) - 1) if len(volumes) > 1 else volumes[0]
        vol_ratio_calc = volumes[0] / avg_vol_5 if avg_vol_5 > 0 else 1.0
        # Volume expansion with positive close = good
        vol_quality = _scale_to_range(vol_ratio_calc, 0.3, 5.0, 2, 15)
        # Bonus for volume expansion with positive close
        if change_pct > 0 and vol_ratio_calc > 1.2:
            vol_quality = min(15, vol_quality + 2)
        # Penalty for volume expansion with negative close
        if change_pct < -1 and vol_ratio_calc > 1.5:
            vol_quality *= 0.6
        breakdown["volume_expansion_raw"] = round(vol_ratio_calc, 4)
    elif volume_ratio > 0:
        vol_quality = _scale_to_range(volume_ratio, 0.3, 5.0, 2, 15)
        if change_pct > 0 and volume_ratio > 1.2:
            vol_quality = min(15, vol_quality + 2)
        if change_pct < -1 and volume_ratio > 1.5:
            vol_quality *= 0.6
        breakdown["volume_expansion_raw"] = round(volume_ratio, 4)
        tags.append("v2_volume_from_ratio")
    else:
        if v1_score > 0:
            vol_quality = _scale_to_range(v1_score, 20, 90, 3, 14)
        elif relevance_score > 0:
            vol_quality = _scale_to_range(relevance_score, 0.5, 0.95, 3, 12)
        elif quant_score > 0:
            vol_quality = _scale_to_range(quant_score, 35, 85, 2, 11)
        else:
            vol_quality = 6.0
        tags.append("v2_volume_fallback")
    breakdown["volume_expansion_score"] = round(vol_quality, 2)

    # ================================================================
    # Component 5: Sector Relative Strength (0-10)
    # ================================================================
    if sector_burst > 0 or sector_trend > 0:
        sector_avg = (sector_burst + sector_trend) / 2.0
        relative = change_pct - sector_avg / 10.0
        sector_rs = _scale_to_range(relative, -8, 12, 0, 10)
        breakdown["sector_relative_raw"] = round(relative, 4)
    else:
        # Fallback: use v1_score or source_pool
        if v1_score > 0:
            sector_rs = _scale_to_range(v1_score, 20, 90, 1, 9)
        elif source_pool == "burst":
            sector_rs = 7.0
        elif source_pool == "both":
            sector_rs = 5.5
        elif source_pool == "trend":
            sector_rs = 4.0
        else:
            sector_rs = 5.0
        tags.append("v2_sector_rs_fallback")
    breakdown["sector_rs_score"] = round(sector_rs, 2)

    # ================================================================
    # Component 6: High Rejection Penalty (0 to -15)
    # 对冲高回落更敏感
    # ================================================================
    if today_high > 0 and today_close > 0 and today_open > 0:
        upper_shadow = (today_high - max(today_close, today_open)) / today_open * 100
        # More sensitive: continuous scaling
        if upper_shadow > 5:
            rejection_penalty = -15.0
            tags.append("v2_high_rejection_severe")
        elif upper_shadow > 3:
            rejection_penalty = -10.0
            tags.append("v2_high_rejection_moderate")
        elif upper_shadow > 1.5:
            rejection_penalty = -5.0
            tags.append("v2_high_rejection_mild")
        elif upper_shadow > 0.5:
            rejection_penalty = -2.0
        else:
            rejection_penalty = 0.0
        breakdown["upper_shadow_pct"] = round(upper_shadow, 4)
    else:
        rejection_penalty = 0.0
        tags.append("v2_rejection_no_data")
    breakdown["rejection_penalty"] = round(rejection_penalty, 2)

    # ================================================================
    # Component 7: Overheat Penalty (0 to -15)
    # 避免极端超涨误判为强势
    # ================================================================
    overheat_penalty = 0.0
    # Near limit-up = overheat risk
    if change_pct > 9.5:
        overheat_penalty = -15.0
        tags.append("v2_overheat_near_limit")
    elif change_pct > 7:
        overheat_penalty = -8.0
        tags.append("v2_overheat_high_change")
    elif change_pct > 5:
        overheat_penalty = -3.0
    # Very high volume with weak close
    if volume_ratio > 5 and change_pct < 1:
        overheat_penalty -= 5.0
        tags.append("v2_overheat_volume_weak_close")
    elif volume_ratio > 3 and change_pct < 0:
        overheat_penalty -= 3.0
    overheat_penalty = max(-15.0, overheat_penalty)
    breakdown["overheat_penalty"] = round(overheat_penalty, 2)

    # ================================================================
    # Component 8: Data Quality Penalty (0 to -3)
    # 不要把所有历史样本压到低分
    # ================================================================
    data_quality_penalty = 0.0
    if not has_bars:
        data_quality_penalty -= 2.0  # Reduced from -3
        tags.append("v2_missing_bars")
    if amount <= 0 and volume <= 0:
        data_quality_penalty -= 1.0  # Reduced from -2
        tags.append("v2_missing_volume_amount")
    data_quality_penalty = max(-3.0, data_quality_penalty)  # Reduced cap
    breakdown["data_quality_penalty"] = round(data_quality_penalty, 2)

    # ================================================================
    # Total Score
    # ================================================================
    raw_total = (
        close_position_score
        + three_day_rs
        + five_day_rs
        + vol_quality
        + sector_rs
        + rejection_penalty
        + overheat_penalty
        + data_quality_penalty
    )
    total = max(0.0, min(100.0, raw_total))

    breakdown["total_raw"] = round(raw_total, 2)
    breakdown["total"] = round(total, 2)

    # Check for score collapse
    unique_approx = round(total, 0)
    breakdown["unique_approx"] = unique_approx

    return {
        "stock_short_score_v2": round(total, 2),
        "stock_short_breakdown_v2": breakdown,
        "stock_short_v2_tags": tags,
    }
