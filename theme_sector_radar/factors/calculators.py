"""
Bars 因子计算器

基于日线 bars 数据计算各类因子值。
所有计算异常必须降级，不允许中断 pipeline。
bars 不足时返回 None，并标记 quality="missing"。
"""

from __future__ import annotations

from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为 float。"""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_bars(bars: list[dict]) -> list[dict]:
    """规整 bars 数据方向，确保从新到旧排列。

    通过比较第一条和最后一条的日期来判断方向。
    如果已经是新到旧，直接返回；如果是旧到新，则反转。
    """
    if not bars or len(bars) < 2:
        return bars

    # 尝试从日期字段判断方向
    first_date = bars[0].get("date", "")
    last_date = bars[-1].get("date", "")

    if first_date and last_date:
        # 如果第一条日期比最后一条日期早，说明是旧到新，需要反转
        if first_date < last_date:
            return list(reversed(bars))
        else:
            # 已经是新到旧或同一天
            return bars

    # 如果没有日期字段，假设已经是新到旧
    return bars


def _calc_ma(values: list[float], period: int) -> float | None:
    """计算移动平均值（使用最后 N 个值）。"""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _calc_atr(bars: list[dict], period: int) -> float | None:
    """计算 ATR (Average True Range)。"""
    if len(bars) < period + 1:
        return None

    true_ranges: list[float] = []
    for i in range(period):
        high = _safe_float(bars[i].get("high", 0))
        low = _safe_float(bars[i].get("low", 0))
        prev_close = _safe_float(bars[i + 1].get("close", 0))

        if prev_close <= 0:
            true_ranges.append(high - low)
        else:
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            true_ranges.append(tr)

    if not true_ranges:
        return None
    return sum(true_ranges) / len(true_ranges)


def _calc_range_pct(bars: list[dict], period: int) -> float | None:
    """计算振幅百分比（最高价-最低价）/ 收盘价。"""
    if len(bars) < period:
        return None

    ranges: list[float] = []
    for i in range(period):
        high = _safe_float(bars[i].get("high", 0))
        low = _safe_float(bars[i].get("low", 0))
        close = _safe_float(bars[i].get("close", 0))
        if close > 0:
            ranges.append((high - low) / close * 100)

    if not ranges:
        return None
    return sum(ranges) / len(ranges)


def _calc_amount_avg(bars: list[dict], period: int) -> float | None:
    """计算平均成交额。"""
    if len(bars) < period:
        return None

    amounts: list[float] = []
    for i in range(period):
        amount = _safe_float(bars[i].get("amount", 0))
        if amount > 0:
            amounts.append(amount)

    if not amounts:
        return None
    return sum(amounts) / len(amounts)


def calculate_bar_factors(
    candidate: dict,
    bars: list[dict] | None,
) -> dict[str, float | None]:
    """基于 bars 数据计算各类因子值。

    Args:
        candidate: 候选股字典（用于 fallback）
        bars: 日线数据列表，可以是新到旧或旧到新

    Returns:
        dict: factor_id -> value (可以是 None)
    """
    result: dict[str, float | None] = {}

    # bars 不足时返回全部 None
    if not bars or len(bars) < 5:
        return {
            "ma20_slope_5": None,
            "near_high_250": None,
            "contraction_score": None,
            "atr10_atr50": None,
            "range10_range20": None,
            "range20_range60": None,
            "amount_ratio_20": None,
        }

    # 规整 bars 方向：确保从新到旧
    bars = _normalize_bars(bars)

    # 提取数据
    closes: list[float] = [_safe_float(b.get("close", 0)) for b in bars]
    highs: list[float] = [_safe_float(b.get("high", 0)) for b in bars]
    lows: list[float] = [_safe_float(b.get("low", 0)) for b in bars]

    # ============================================================
    # ma20_slope_5: MA20 斜率（5日）
    # ============================================================
    try:
        if len(closes) >= 25:
            ma20_now = sum(closes[:20]) / 20
            ma20_prev = sum(closes[5:25]) / 20
            if ma20_prev > 0:
                slope_pct = (ma20_now - ma20_prev) / ma20_prev * 100
                result["ma20_slope_5"] = round(slope_pct, 4)
            else:
                result["ma20_slope_5"] = None
        else:
            result["ma20_slope_5"] = None
    except Exception:
        result["ma20_slope_5"] = None

    # ============================================================
    # near_high_250: 距250日新高百分比
    # ============================================================
    try:
        lookback_250 = min(250, len(highs))
        if lookback_250 >= 20:  # 至少需要一些数据
            high_250 = max(highs[:lookback_250])
            current_close = closes[0] if closes else 0
            if high_250 > 0:
                # 计算距离新高的百分比，范围 [-100, 0]
                # 0 表示在新高，-50 表示距离新高 50%
                near_high = (current_close / high_250 - 1) * 100
                result["near_high_250"] = round(near_high, 4)
            else:
                result["near_high_250"] = None
        else:
            result["near_high_250"] = None
    except Exception:
        result["near_high_250"] = None

    # ============================================================
    # atr10_atr50: ATR10/ATR50 比值
    # ============================================================
    try:
        atr10 = _calc_atr(bars, 10)
        atr50 = _calc_atr(bars, 50)
        if atr10 is not None and atr50 is not None and atr50 > 0:
            result["atr10_atr50"] = round(atr10 / atr50, 4)
        else:
            result["atr10_atr50"] = None
    except Exception:
        result["atr10_atr50"] = None

    # ============================================================
    # range10_range20: 振幅10/振幅20 比值
    # ============================================================
    try:
        range10 = _calc_range_pct(bars, 10)
        range20 = _calc_range_pct(bars, 20)
        if range10 is not None and range20 is not None and range20 > 0:
            result["range10_range20"] = round(range10 / range20, 4)
        else:
            result["range10_range20"] = None
    except Exception:
        result["range10_range20"] = None

    # ============================================================
    # range20_range60: 振幅20/振幅60 比值
    # ============================================================
    try:
        range20 = _calc_range_pct(bars, 20)
        range60 = _calc_range_pct(bars, 60)
        if range20 is not None and range60 is not None and range60 > 0:
            result["range20_range60"] = round(range20 / range60, 4)
        else:
            result["range20_range60"] = None
    except Exception:
        result["range20_range60"] = None

    # ============================================================
    # amount_ratio_20: 成交额比(5日均/20日均)
    # ============================================================
    try:
        amount_avg_5 = _calc_amount_avg(bars, 5)
        amount_avg_20 = _calc_amount_avg(bars, 20)
        if amount_avg_5 is not None and amount_avg_20 is not None and amount_avg_20 > 0:
            result["amount_ratio_20"] = round(amount_avg_5 / amount_avg_20, 4)
        else:
            result["amount_ratio_20"] = None
    except Exception:
        result["amount_ratio_20"] = None

    # ============================================================
    # contraction_score: 收缩评分 (0-100)
    # 综合 ATR 收缩和振幅收缩，收缩越明显分数越高
    # ============================================================
    try:
        score = 50.0  # 基准分

        # ATR 收缩：atr10_atr50 < 1 表示短期波动收缩
        atr_ratio = result.get("atr10_atr50")
        if atr_ratio is not None:
            if atr_ratio < 0.7:
                score += 25.0  # 显著收缩
            elif atr_ratio < 0.85:
                score += 15.0  # 中等收缩
            elif atr_ratio < 1.0:
                score += 5.0   # 轻微收缩
            elif atr_ratio > 1.3:
                score -= 15.0  # 波动扩大
            elif atr_ratio > 1.1:
                score -= 5.0   # 轻微扩大

        # 振幅收缩：range10_range20 < 1 表示短期振幅收缩
        range_ratio = result.get("range10_range20")
        if range_ratio is not None:
            if range_ratio < 0.7:
                score += 20.0
            elif range_ratio < 0.85:
                score += 10.0
            elif range_ratio < 1.0:
                score += 5.0
            elif range_ratio > 1.3:
                score -= 10.0
            elif range_ratio > 1.1:
                score -= 5.0

        score = max(0.0, min(100.0, score))
        result["contraction_score"] = round(score, 2)
    except Exception:
        result["contraction_score"] = None

    # ============================================================
    # liquidity_score: 流动性评分 (0-100)
    # 基于近20日平均成交额
    # ============================================================
    try:
        avg_amount = _calc_amount_avg(bars, 20)
        if avg_amount is not None:
            if avg_amount >= 1_000_000_000:
                result["liquidity_score"] = 90.0
            elif avg_amount >= 500_000_000:
                result["liquidity_score"] = 80.0
            elif avg_amount >= 200_000_000:
                result["liquidity_score"] = 70.0
            elif avg_amount >= 100_000_000:
                result["liquidity_score"] = 60.0
            elif avg_amount >= 50_000_000:
                result["liquidity_score"] = 50.0
            elif avg_amount >= 20_000_000:
                result["liquidity_score"] = 40.0
            else:
                result["liquidity_score"] = 30.0
        else:
            result["liquidity_score"] = None
    except Exception:
        result["liquidity_score"] = None

    # ============================================================
    # chasing_risk_score: 追高风险评分 (0-100)
    # 基于短期涨幅和价格位置
    # ============================================================
    try:
        if len(closes) >= 10 and len(highs) >= 20:
            close_t = closes[0]
            close_t_minus_5 = closes[5] if len(closes) > 5 else closes[-1]
            high_20 = max(highs[:20])

            # 计算 5日涨幅
            return_5d = (close_t / close_t_minus_5 - 1) if close_t_minus_5 > 0 else 0

            # 计算距20日高点位置
            near_20_high = close_t / high_20 if high_20 > 0 else 0

            # 计算当天涨幅（如果有前一日 close）
            daily_return = 0
            if len(closes) >= 2:
                prev_close = closes[1]
                if prev_close > 0:
                    daily_return = (close_t / prev_close - 1)

            # 评分
            base = 50
            if return_5d > 0.15:
                base += 25
            elif return_5d > 0.08:
                base += 15

            if near_20_high > 0.98:
                base += 20
            elif near_20_high > 0.95:
                base += 10

            if daily_return > 0.07:
                base += 15

            # 限制在 0-100
            base = max(0, min(100, base))
            result["chasing_risk_score"] = round(base, 2)
        else:
            result["chasing_risk_score"] = None
    except Exception:
        result["chasing_risk_score"] = None

    # ============================================================
    # drawdown_depth_20: 20日最大回撤深度 (%)
    # 在最近 20 日窗口内，从任一阶段高点到后续低点的最大跌幅
    # ============================================================
    try:
        if len(highs) >= 20 and len(lows) >= 20:
            # 取最近 20 日的数据
            window_highs = highs[:20]
            window_lows = lows[:20]
            window_closes = closes[:20]

            # 计算最大回撤
            max_drawdown = 0.0
            peak = window_closes[0] if window_closes else 0

            for i in range(len(window_highs)):
                current_high = window_highs[i]
                current_low = window_lows[i]
                current_close = window_closes[i] if i < len(window_closes) else current_high

                # 更新峰值
                if current_high > peak:
                    peak = current_high

                # 计算回撤
                if peak > 0:
                    drawdown = (peak - current_low) / peak * 100
                    max_drawdown = max(max_drawdown, drawdown)

            if max_drawdown > 0:
                result["drawdown_depth_20"] = round(max_drawdown, 2)
            else:
                result["drawdown_depth_20"] = None
        else:
            result["drawdown_depth_20"] = None
    except Exception:
        result["drawdown_depth_20"] = None

    # ============================================================
    # breakout_distance_20: 距20日突破距离 (%)
    # 表示当前价格距离 20 日高点的百分比距离
    # ============================================================
    try:
        if len(highs) >= 20 and len(closes) > 0:
            high_20 = max(highs[:20])
            close_t = closes[0]
            if high_20 > 0:
                distance = (high_20 - close_t) / high_20 * 100
                result["breakout_distance_20"] = round(max(0, distance), 2)
            else:
                result["breakout_distance_20"] = None
        else:
            result["breakout_distance_20"] = None
    except Exception:
        result["breakout_distance_20"] = None

    return result
