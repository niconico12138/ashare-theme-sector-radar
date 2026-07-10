"""
个股趋势评分模块

基于个股维度计算中长线趋势分，使用 MA 均线体系、突破前高、回撤控制、量价配合等。
bars 不足时 fallback 到 change_pct、quant_score、sector_trend_score/trend_score。
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
    if close_prev <= 0:
        return 0.0
    return (close_now - close_prev) / close_prev * 100


def _calc_ma(closes: list[float], period: int) -> float:
    if len(closes) < period:
        return 0.0
    return sum(closes[-period:]) / period


def compute_stock_trend_score(
    stock: dict,
    bars: list[dict] | None = None,
) -> dict:
    """Compute individual stock trend score (0-100).

    Args:
        stock: Stock dict with optional fields: change_pct, quant_score,
               sector_trend_score/trend_score, close.
        bars: Optional list of daily bar dicts sorted newest-first.
              Each bar should have: date, open, high, low, close, volume, amount.

    Returns:
        dict with stock_trend_score, stock_trend_breakdown, stock_trend_tags.
    """
    tags: list[str] = []
    breakdown: dict[str, float] = {}
    has_bars = bars and len(bars) >= 5

    # Extract basic fields
    change_pct = _safe_float(stock.get("change_pct", stock.get("pct_change", 0)))
    quant_score = _safe_float(stock.get("quant_score", 0))
    sector_trend = _safe_float(
        stock.get("sector_trend_score", stock.get("trend_score", 0))
    )

    # Collect bar data (newest-first)
    closes: list[float] = []
    volumes: list[float] = []
    if has_bars:
        for bar in bars:
            closes.append(_safe_float(bar.get("close", 0)))
            volumes.append(_safe_float(bar.get("volume", 0)))

    if not has_bars:
        tags.append("trend_score_degraded_missing_bars")
        return _fallback_score(stock, change_pct, quant_score, sector_trend, tags)

    # === Component 1: MA Alignment (0-25) ===
    ma5 = _calc_ma(closes, 5)
    ma10 = _calc_ma(closes, 10)
    ma20 = _calc_ma(closes, 20)
    ma60 = _calc_ma(closes, 60) if len(closes) >= 60 else 0.0
    latest_close = closes[0]

    # Check MA alignment: price > MA5 > MA10 > MA20 > MA60 is ideal
    alignment_score = 0.0
    above_count = 0
    if latest_close > 0:
        if ma5 > 0 and latest_close > ma5:
            above_count += 1
        if ma10 > 0 and latest_close > ma10:
            above_count += 1
        if ma20 > 0 and latest_close > ma20:
            above_count += 1
        if ma60 > 0 and latest_close > ma60:
            above_count += 1

    # MA ordering bonus
    ma_order_bonus = 0.0
    if ma5 > 0 and ma10 > 0 and ma5 > ma10:
        ma_order_bonus += 3.0
    if ma10 > 0 and ma20 > 0 and ma10 > ma20:
        ma_order_bonus += 3.0
    if ma20 > 0 and ma60 > 0 and ma20 > ma60:
        ma_order_bonus += 2.0

    alignment_score = min(25.0, above_count * 5.0 + ma_order_bonus)
    breakdown["ma_alignment"] = round(alignment_score, 2)
    breakdown["above_ma_count"] = above_count

    # === Component 2: MA20 Slope (0-20) ===
    # Calculate MA20 slope by comparing current MA20 vs MA20 5 bars ago
    if len(closes) >= 25:
        ma20_prev = sum(closes[6:26]) / 20  # 5 bars ago
        if ma20_prev > 0:
            ma20_slope_pct = (ma20 - ma20_prev) / ma20_prev * 100
        else:
            ma20_slope_pct = 0.0

        if ma20_slope_pct > 3:
            slope_score = 20.0
        elif ma20_slope_pct > 1.5:
            slope_score = 16.0
        elif ma20_slope_pct > 0.5:
            slope_score = 12.0
        elif ma20_slope_pct > -0.5:
            slope_score = 8.0
        elif ma20_slope_pct > -1.5:
            slope_score = 4.0
        else:
            slope_score = 0.0
        breakdown["ma20_slope_pct"] = round(ma20_slope_pct, 2)
    else:
        slope_score = 10.0  # neutral
        ma20_slope_pct = 0.0
    breakdown["ma20_slope"] = round(slope_score, 2)

    # === Component 3: Price vs MA20 (0-15) ===
    if ma20 > 0:
        price_vs_ma20 = (latest_close - ma20) / ma20 * 100
        if price_vs_ma20 > 10:
            price_ma20_score = 12.0  # too far above, possible pullback
            tags.append("overextended_above_ma20")
        elif price_vs_ma20 > 5:
            price_ma20_score = 15.0  # strong but not overextended
        elif price_vs_ma20 > 0:
            price_ma20_score = 12.0  # above, healthy
        elif price_vs_ma20 > -5:
            price_ma20_score = 8.0  # slightly below
        else:
            price_ma20_score = 3.0  # well below
        breakdown["price_vs_ma20_pct"] = round(price_vs_ma20, 2)
    else:
        price_ma20_score = 7.5
    breakdown["price_vs_ma20"] = round(price_ma20_score, 2)

    # === Component 4: Breakout High (0-15) ===
    # Check if price is near or above 20-day high
    highs = [(_safe_float(bars[i].get("high", 0))) for i in range(min(20, len(bars)))]
    if highs:
        recent_high = max(highs)
        if recent_high > 0:
            high_proximity = (latest_close / recent_high - 1) * 100
            if high_proximity >= 0:
                breakout_score = 15.0  # at or above 20d high
                tags.append("near_20d_high")
            elif high_proximity > -2:
                breakout_score = 12.0
            elif high_proximity > -5:
                breakout_score = 8.0
            else:
                breakout_score = 4.0
            breakdown["high_proximity_pct"] = round(high_proximity, 2)
        else:
            breakout_score = 7.5
    else:
        breakout_score = 7.5
    breakdown["breakout_high"] = round(breakout_score, 2)

    # === Component 5: Drawdown Control (0-15) ===
    # Calculate max drawdown from recent peak
    if len(closes) >= 10:
        peak = closes[-1]  # oldest in the window
        max_dd = 0.0
        for c in reversed(closes):  # from oldest to newest
            if c > peak:
                peak = c
            dd = (peak - c) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        if max_dd < 3:
            drawdown_score = 15.0
        elif max_dd < 5:
            drawdown_score = 12.0
        elif max_dd < 10:
            drawdown_score = 8.0
        elif max_dd < 15:
            drawdown_score = 4.0
        else:
            drawdown_score = 0.0
            tags.append("large_drawdown")
        breakdown["max_drawdown_pct"] = round(max_dd, 2)
    else:
        drawdown_score = 7.5
    breakdown["drawdown_control"] = round(drawdown_score, 2)

    # === Component 6: Volume-Price Confirmation (0-10) ===
    if len(volumes) >= 10:
        avg_vol = sum(volumes[:10]) / 10
        recent_vol = volumes[0] if volumes[0] > 0 else 1
        vol_change = recent_vol / avg_vol if avg_vol > 0 else 1.0

        # Price up + volume up = confirmation
        if change_pct > 0 and vol_change > 1.5:
            vp_score = 10.0
        elif change_pct > 0 and vol_change > 1:
            vp_score = 8.0
        elif change_pct < 0 and vol_change < 0.8:
            vp_score = 7.0  # shrinking volume on decline is ok
        elif change_pct < 0 and vol_change > 1.5:
            vp_score = 2.0  # distribution
            tags.append("distribution_volume")
        else:
            vp_score = 5.0
        breakdown["vol_change_ratio"] = round(vol_change, 2)
    else:
        vp_score = 5.0
    breakdown["volume_price_confirm"] = round(vp_score, 2)

    # === Component 7: Data Quality (0-10) ===
    data_quality = 10.0
    data_quality -= max(0, 20 - len(closes)) * 0.3
    data_quality = max(0.0, min(10.0, data_quality))
    breakdown["data_quality"] = round(data_quality, 2)

    # === Total Score ===
    total = (
        alignment_score
        + slope_score
        + price_ma20_score
        + breakout_score
        + drawdown_score
        + vp_score
        + data_quality
    )
    total = max(0.0, min(100.0, total))
    breakdown["total_raw"] = round(total, 2)

    return {
        "stock_trend_score": round(total, 2),
        "stock_trend_breakdown": breakdown,
        "stock_trend_tags": tags,
    }


def _fallback_score(
    stock: dict,
    change_pct: float,
    quant_score: float,
    sector_trend: float,
    tags: list[str],
) -> dict:
    """Fallback scoring when bars are insufficient.

    Uses change_pct, quant_score, and sector_trend_score as proxies.
    """
    breakdown: dict[str, float] = {}

    # Weight available proxies
    if sector_trend > 0:
        trend_base = sector_trend * 0.4
    else:
        trend_base = 50.0 * 0.4

    if quant_score > 0:
        quant_base = quant_score * 0.4
    else:
        quant_base = 50.0 * 0.4
        tags.append("quant_score_missing_neutral")

    # Change_pct as momentum proxy (normalize to 0-100 range)
    momentum = max(0.0, min(100.0, 50.0 + change_pct * 5)) * 0.2

    total = trend_base + quant_base + momentum
    total = max(0.0, min(100.0, total))

    breakdown["fallback_trend_component"] = round(trend_base, 2)
    breakdown["fallback_quant_component"] = round(quant_base, 2)
    breakdown["fallback_momentum_component"] = round(momentum, 2)
    breakdown["total_raw"] = round(total, 2)

    return {
        "stock_trend_score": round(total, 2),
        "stock_trend_breakdown": breakdown,
        "stock_trend_tags": tags,
    }
