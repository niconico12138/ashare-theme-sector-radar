"""
个股短线评分模块

基于个股维度计算短线动量分，区别于板块级 burst_score。
支持无 bars 降级打分，fallback 模式使用 quant_score/final_score/relevance_score
进行分位数风格拉伸以保证区分度。
"""

from __future__ import annotations

from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pct_change(close_now: float, close_prev: float) -> float:
    """Calculate percentage change."""
    if close_prev <= 0:
        return 0.0
    return (close_now - close_prev) / close_prev * 100


def _calc_ma(closes: list[float], period: int) -> float:
    """Calculate moving average for given period."""
    if len(closes) < period:
        return 0.0
    return sum(closes[-period:]) / period


def _scale_to_range(value: float, in_min: float, in_max: float,
                    out_min: float, out_max: float) -> float:
    """Linearly scale value from [in_min, in_max] to [out_min, out_max]."""
    if in_max <= in_min:
        return (out_min + out_max) / 2.0
    clamped = max(in_min, min(in_max, value))
    return out_min + (clamped - in_min) / (in_max - in_min) * (out_max - out_min)


def compute_stock_short_score(
    stock: dict,
    bars: list[dict] | None = None,
    sector_context: dict | None = None,
) -> dict:
    """Compute individual stock short-term score (0-100).

    Args:
        stock: Stock dict with fields like change_pct, amount, volume,
               turnover_rate, volume_ratio, sector_burst_score/burst_score,
               quant_score, final_score, relevance_score, source_pool.
        bars: Optional list of daily bar dicts sorted newest-first.
              Each bar should have: date, open, high, low, close, volume, amount.
        sector_context: Optional sector-level context (burst_score, trend_score).

    Returns:
        dict with stock_short_score, stock_short_breakdown, stock_short_tags.
    """
    tags: list[str] = []
    breakdown: dict[str, float] = {}
    has_bars = bars and len(bars) >= 2

    # Extract basic fields from stock dict
    change_pct = _safe_float(stock.get("change_pct", stock.get("pct_change", 0)))
    amount = _safe_float(stock.get("amount", 0))
    volume = _safe_float(stock.get("volume", 0))
    turnover_rate = _safe_float(stock.get("turnover_rate", 0))
    volume_ratio = _safe_float(stock.get("volume_ratio", 0))

    # Additional fields for fallback discrimination
    quant_score = _safe_float(stock.get("quant_score", 0))
    final_score = _safe_float(stock.get("final_score", 0))
    relevance_score = _safe_float(stock.get("relevance_score", 0))
    source_pool = stock.get("source_pool", "")
    sector_burst_raw = _safe_float(
        stock.get("sector_burst_score", stock.get("burst_score", 0))
    )
    sector_burst = sector_burst_raw

    # Collect raw bar data for trend calculations
    closes: list[float] = []
    volumes: list[float] = []
    highs: list[float] = []
    if has_bars:
        for bar in bars:
            closes.append(_safe_float(bar.get("close", 0)))
            volumes.append(_safe_float(bar.get("volume", 0)))
            highs.append(_safe_float(bar.get("high", 0)))

    # === Component 1: Intraday Momentum (0-25) ===
    if change_pct != 0:
        if change_pct > 7:
            intraday_momentum = 25.0
        elif change_pct > 4:
            intraday_momentum = 20.0
        elif change_pct > 2:
            intraday_momentum = 15.0
        elif change_pct > 0:
            intraday_momentum = 10.0
        elif change_pct > -2:
            intraday_momentum = 5.0
        else:
            intraday_momentum = 0.0
    elif final_score > 0:
        # Scale final_score (typically 50-75) to 0-25 range with wider spread
        intraday_momentum = _scale_to_range(final_score, 40.0, 80.0, 5.0, 22.0)
        breakdown["fallback_source"] = "final_score"
    elif quant_score > 0:
        intraday_momentum = _scale_to_range(quant_score, 40.0, 80.0, 5.0, 22.0)
        breakdown["fallback_source"] = "quant_score"
    else:
        intraday_momentum = 10.0
    breakdown["intraday_momentum"] = round(intraday_momentum, 2)

    # === Component 2: 5-day Momentum (0-20) ===
    if has_bars and len(closes) >= 6:
        close_5d_ago = closes[5] if len(closes) > 5 else closes[-1]
        day5_change = _pct_change(closes[0], close_5d_ago)
        if day5_change > 15:
            momentum_5d = 20.0
        elif day5_change > 10:
            momentum_5d = 16.0
        elif day5_change > 5:
            momentum_5d = 12.0
        elif day5_change > 0:
            momentum_5d = 8.0
        elif day5_change > -5:
            momentum_5d = 4.0
        else:
            momentum_5d = 0.0
        breakdown["momentum_5d"] = round(momentum_5d, 2)
        breakdown["day5_change_pct"] = round(day5_change, 2)
    else:
        # Fallback: use quant_score to simulate momentum spread
        if quant_score > 0:
            momentum_5d = _scale_to_range(quant_score, 40.0, 80.0, 3.0, 18.0)
        else:
            momentum_5d = min(20.0, max(0.0, change_pct * 1.5))
        breakdown["momentum_5d"] = round(momentum_5d, 2)
        if not has_bars:
            tags.append("short_score_degraded_missing_bars")

    # === Component 3: Volume Expansion (0-20) ===
    if has_bars and len(volumes) >= 5:
        avg_vol_5 = sum(volumes[1:6]) / min(5, len(volumes) - 1) if len(volumes) > 1 else volumes[0]
        vol_ratio_calc = volumes[0] / avg_vol_5 if avg_vol_5 > 0 else 1.0
        if vol_ratio_calc > 3:
            volume_expansion = 20.0
        elif vol_ratio_calc > 2:
            volume_expansion = 16.0
        elif vol_ratio_calc > 1.5:
            volume_expansion = 12.0
        elif vol_ratio_calc > 1:
            volume_expansion = 8.0
        else:
            volume_expansion = 4.0
        breakdown["volume_expansion"] = round(volume_expansion, 2)
        breakdown["volume_ratio_calc"] = round(vol_ratio_calc, 2)
    else:
        # Fallback: use relevance_score as proxy for activity level
        if relevance_score > 0:
            volume_expansion = _scale_to_range(relevance_score, 0.6, 0.9, 4.0, 16.0)
        elif quant_score > 0:
            volume_expansion = _scale_to_range(quant_score, 40.0, 80.0, 4.0, 14.0)
        else:
            volume_expansion = 10.0
        breakdown["volume_expansion"] = round(volume_expansion, 2)

    # === Component 4: High Rejection (冲高回落) (0-15) ===
    if has_bars and len(highs) >= 2:
        latest_bar = bars[0]
        today_high = _safe_float(latest_bar.get("high", 0))
        today_close = _safe_float(latest_bar.get("close", 0))
        today_open = _safe_float(latest_bar.get("open", 0))
        if today_high > 0 and today_open > 0:
            upper_shadow_pct = (today_high - max(today_close, today_open)) / today_open * 100
            if upper_shadow_pct > 5:
                high_rejection = 0.0
                tags.append("high_rejection")
            elif upper_shadow_pct > 3:
                high_rejection = 4.0
            elif upper_shadow_pct > 1:
                high_rejection = 10.0
            else:
                high_rejection = 15.0
            breakdown["high_rejection"] = round(high_rejection, 2)
            breakdown["upper_shadow_pct"] = round(upper_shadow_pct, 2)
        else:
            high_rejection = 8.0
            breakdown["high_rejection"] = 8.0
    else:
        # Fallback: final_score proxy for closing strength
        if final_score > 0:
            high_rejection = _scale_to_range(final_score, 40.0, 80.0, 4.0, 13.0)
        else:
            high_rejection = 8.0
        breakdown["high_rejection"] = round(high_rejection, 2)

    # === Component 5: Relative Strength (0-20) ===
    if sector_burst > 1.5:
        relative = change_pct - (sector_burst / 10)
    elif sector_burst > 0:
        relative = change_pct - (sector_burst * 10)
    else:
        relative = change_pct

    if relative != 0 or change_pct != 0:
        if relative > 3:
            relative_strength = 20.0
        elif relative > 1:
            relative_strength = 15.0
        elif relative > -1:
            relative_strength = 10.0
        elif relative > -3:
            relative_strength = 5.0
        else:
            relative_strength = 0.0
    elif relevance_score > 0:
        relative_strength = _scale_to_range(relevance_score, 0.6, 0.9, 4.0, 18.0)
    else:
        relative_strength = 8.0
    breakdown["relative_strength"] = round(relative_strength, 2)

    # === Component 6: Source Pool Bonus (0-10) ===
    if source_pool == "burst":
        source_bonus = 10.0
    elif source_pool == "both":
        source_bonus = 7.0
    elif source_pool == "trend":
        source_bonus = 4.0
    else:
        source_bonus = 5.0
    breakdown["source_pool_bonus"] = round(source_bonus, 2)

    # === Component 7: Quant Score Component (0-10) ===
    # Direct quant_score contribution for fallback discrimination
    if quant_score > 0:
        quant_component = _scale_to_range(quant_score, 40.0, 85.0, 0.0, 10.0)
    else:
        quant_component = 5.0
    breakdown["quant_component"] = round(quant_component, 2)

    # === Component 8: Data Quality (0-10) ===
    data_quality = 10.0
    if not has_bars:
        data_quality -= 5.0
    if amount <= 0 and volume <= 0:
        data_quality -= 3.0
    if turnover_rate <= 0:
        data_quality -= 2.0
    data_quality = max(0.0, data_quality)
    breakdown["data_quality"] = round(data_quality, 2)

    # === Total Score ===
    total = (
        intraday_momentum
        + momentum_5d
        + volume_expansion
        + high_rejection
        + relative_strength
        + source_bonus
        + quant_component
        + data_quality
    )
    total = max(0.0, min(100.0, total))

    breakdown["total_raw"] = round(total, 2)
    breakdown["fallback_used"] = 1 if breakdown.get("fallback_source") else 0
    breakdown["distribution_stretch_applied"] = 1 if (not has_bars and quant_score > 0) else 0

    if breakdown.get("fallback_source"):
        tags.append("short_score_fallback_used")

    return {
        "stock_short_score": round(total, 2),
        "stock_short_breakdown": breakdown,
        "stock_short_tags": tags,
    }
