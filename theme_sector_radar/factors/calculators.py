"""
Bars 因子计算器

基于日线 bars 数据计算各类因子值。
所有计算异常必须降级，不允许中断 pipeline。
bars 不足时返回 None，并标记 quality="missing"。
"""

from __future__ import annotations

import math
from typing import Any


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为 float。"""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _coerce_candidate_score(candidate: dict, field: str) -> float | None:
    value = candidate.get(field)
    if value is None:
        return None
    try:
        return _clamp_score(float(value))
    except (TypeError, ValueError):
        return None


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


def _extract_intraday_price(point: dict) -> float:
    for key in ("price", "close", "current", "last"):
        value = _safe_float(point.get(key))
        if value > 0:
            return value
    return 0.0


PRICE_MOMENTUM_EXPANSION_IDS = (
    "return_5m_strength_score",
    "return_15m_strength_score",
    "return_60m_strength_score",
    "positive_bar_ratio_score",
    "rolling_price_slope_score",
    "intraday_breakout_strength_score",
    "breakout_hold_score",
    "pullback_reclaim_momentum_score",
)


def _intraday_return_strength(prices: list[float], bars: int) -> float:
    if len(prices) <= bars:
        return 50.0
    anchor = prices[-bars - 1]
    if anchor <= 0:
        return 50.0
    return _clamp_score(50.0 + (prices[-1] / anchor - 1.0) * 1200.0)


def calculate_intraday_factors(candidate: dict) -> dict[str, float | None]:
    """Calculate shadow-only intraday factors when intraday bars are available."""
    empty = {
        "intraday_close_position_score": None,
        "intraday_high_pullback_risk_score": None,
        "intraday_volume_price_confirm_score": None,
        "intraday_sector_breadth_score": None,
        "intraday_late_strength_score": None,
        "short_burst_intraday_emotion_score_shadow": None,
        "late_return_30m_score": None,
        "late_vwap_support_score": None,
        "late_volume_share_score": None,
        "late_high_near_close_score": None,
        "high_to_close_drawdown_score": None,
        "morning_spike_fade_score": None,
        "afternoon_fade_score": None,
        "max_gain_giveback_ratio": None,
        "close_vs_vwap_score": None,
        "late_price_above_vwap_ratio": None,
        "vwap_slope_score": None,
        "vwap_reclaim_score": None,
        "open_vwap_reclaim_score": None,
        "midday_vwap_support_score": None,
        "vwap_distance_stability_score": None,
        "vwap_pullback_support_score": None,
        "vwap_breakout_confirm_score": None,
        "vwap_above_ratio_score": None,
        "volume_without_price_progress_risk": None,
        "late_volume_efficiency_score": None,
        "amount_acceleration_score": None,
        "volume_spike_exhaustion_score": None,
        "early_amount_surge_score": None,
        "midday_amount_sustain_score": None,
        "late_amount_surge_score": None,
        "amount_trend_persistence_score": None,
        "volume_price_alignment_score": None,
        "breakout_volume_confirm_score": None,
        "pullback_volume_dryup_score": None,
        "late_money_flow_concentration_score": None,
        "opening_drive_score": None,
        "morning_strength_persist_score": None,
        "morning_pullback_repair_score": None,
        "open_to_midday_resilience_score": None,
        "sector_intraday_breadth_change": None,
        "sector_late_breadth_score": None,
        "leader_follower_sync_score": None,
        "stock_vs_sector_intraday_alpha": None,
        "sector_peer_rank_score": None,
        "market_regime_score": None,
        "sector_leader_score": None,
        "open_to_high_progress_score": None,
        "close_above_midrange_score": None,
        "low_reclaim_position_score": None,
        "late_range_expansion_score": None,
        "high_area_acceptance_score": None,
        "close_location_stability_score": None,
        "sector_breadth_persistence_score": None,
        "sector_late_acceleration_score": None,
        "leader_sync_persistence_score": None,
        "sector_alpha_confirmation_score": None,
        "sector_breadth_quality_score": None,
        "theme_confirmation_composite_score": None,
        "stock_intraday_rank_proxy_score": None,
        "stock_vs_market_intraday_alpha_score": None,
        "relative_late_strength_score": None,
        "relative_vwap_strength_score": None,
        "relative_breakout_leadership_score": None,
        "relative_resilience_score": None,
        "open_high_reversal_risk": None,
        "late_breakdown_risk": None,
        "failed_breakout_risk": None,
        "lower_low_sequence_risk": None,
        "volatility_expansion_reversal_risk": None,
        "weak_close_after_volume_risk": None,
        "first_hour_follow_through_score": None,
        "midday_hold_score": None,
        "afternoon_recovery_score": None,
        "late_session_acceleration_score": None,
        "session_consistency_score": None,
        "close_auction_strength_proxy_score": None,
        "return_5m_strength_score": None,
        "return_15m_strength_score": None,
        "return_60m_strength_score": None,
        "positive_bar_ratio_score": None,
        "rolling_price_slope_score": None,
        "intraday_breakout_strength_score": None,
        "breakout_hold_score": None,
        "pullback_reclaim_momentum_score": None,
        "execution_liquidity_amount_score": None,
        "execution_amount_continuity_score": None,
        "execution_price_impact_risk": None,
        "execution_vwap_slippage_risk": None,
        "execution_spread_proxy_score": None,
        "execution_turnover_depth_score": None,
        "execution_tradeability_score": None,
        "execution_gap_to_limit_up_score": None,
        "execution_gap_to_limit_down_risk": None,
        "execution_microstructure_quality_score": None,
        "cashout_late_surge_risk": None,
        "cashout_late_fade_risk": None,
        "cashout_high_volume_stall_risk": None,
        "cashout_close_giveback_risk": None,
        "cashout_tail_amount_concentration_risk": None,
        "cashout_overheat_without_breadth_risk": None,
        "cashout_vwap_extension_risk": None,
        "cashout_failed_late_breakout_risk": None,
        "cashout_auction_weakness_risk": None,
        "cashout_next_day_pressure_proxy": None,
        "sector_continuation_breadth_score": None,
        "sector_continuation_late_breadth_score": None,
        "sector_continuation_leader_sync_score": None,
        "sector_continuation_alpha_support_score": None,
        "sector_continuation_peer_rank_score": None,
        "sector_continuation_theme_quality_score": None,
        "sector_continuation_market_alignment_score": None,
        "sector_continuation_breadth_acceleration_score": None,
        "sector_continuation_concentration_balance_score": None,
        "sector_continuation_composite_score": None,
        "market_environment_index_trend_score": None,
        "market_environment_vwap_support_score": None,
        "market_environment_breadth_score": None,
        "market_environment_limit_up_breadth_score": None,
        "market_environment_limit_down_risk": None,
        "market_environment_failure_risk": None,
        "market_environment_leader_continuation_score": None,
        "market_environment_crowding_risk": None,
        "market_environment_risk_appetite_score": None,
        "market_environment_composite_score": None,
    }
    intraday_bars = candidate.get("intraday_bars") or candidate.get("minute_bars") or candidate.get("ticks")
    if not isinstance(intraday_bars, list) or len(intraday_bars) < 3:
        return empty

    try:
        prices = [_extract_intraday_price(point) for point in intraday_bars if isinstance(point, dict)]
        amounts = [_safe_float(point.get("amount")) for point in intraday_bars if isinstance(point, dict)]
        prices = [price for price in prices if price > 0]
        amounts = [amount for amount in amounts if amount >= 0]
        if len(prices) < 3:
            return empty

        low = min(prices)
        high = max(prices)
        current = prices[-1]
        open_price = prices[0]
        prev_close = _safe_float(candidate.get("prev_close") or candidate.get("previous_close") or open_price)
        total_amount = sum(amounts) if amounts else 0.0
        vwap = (
            sum(price * amount for price, amount in zip(prices, amounts)) / total_amount
            if total_amount > 0 and len(amounts) == len(prices)
            else sum(prices) / len(prices)
        )
        late_window = max(2, min(6, len(prices) // 4 or 2))
        late_prices = prices[-late_window:]
        late_amounts = amounts[-late_window:] if amounts and len(amounts) == len(prices) else []
        late_anchor = prices[-late_window - 1] if len(prices) > late_window else open_price
        morning_end = max(1, len(prices) // 3)
        midday_idx = max(1, len(prices) // 2)
        morning_prices = prices[:morning_end]
        afternoon_prices = prices[midday_idx:]
        first_half_prices = prices[:midday_idx]
        second_half_prices = prices[midday_idx:]
        first_half_amounts = amounts[:midday_idx] if amounts and len(amounts) == len(prices) else []
        second_half_amounts = amounts[midday_idx:] if amounts and len(amounts) == len(prices) else []
        intraday_range = high - low
        if intraday_range > 0:
            close_position = (current - low) / intraday_range * 100.0
        else:
            close_position = 50.0
        pullback_risk = 0.0 if high <= 0 else (high - current) / high * 100.0 * 12.0

        split = max(1, len(prices) // 3)
        early_price = prices[split - 1]
        late_return = (current - late_anchor) / late_anchor * 100.0 if late_anchor > 0 else 0.0
        day_return = (current - prev_close) / prev_close * 100.0 if prev_close > 0 else (current - open_price) / open_price * 100.0
        early_return = (early_price - open_price) / open_price * 100.0 if open_price > 0 else 0.0
        late_strength = _clamp_score(50.0 + late_return * 10.0 + (current - sum(late_prices) / len(late_prices)) * 2.0)

        if amounts and len(amounts) == len(prices):
            half = max(1, len(amounts) // 2)
            first_amount = sum(amounts[:half])
            second_amount = sum(amounts[half:])
            volume_shift = second_amount / first_amount if first_amount > 0 else 1.0
        else:
            volume_shift = 1.0
        price_holds = 1.0 if current >= early_price else max(0.0, current / early_price) if early_price > 0 else 0.0
        volume_price_confirm = _clamp_score(45.0 + min(volume_shift, 2.5) * 16.0 + day_return * 4.0 + (price_holds - 1.0) * 80.0)

        sector_breadth = candidate.get("sector_intraday_breadth_score")
        if sector_breadth is None:
            sector_breadth = candidate.get("intraday_sector_breadth_score")
        sector_breadth_score = _clamp_score(_safe_float(sector_breadth, 50.0))
        sector_breadth_change = _clamp_score(_safe_float(candidate.get("sector_intraday_breadth_change"), 50.0))
        sector_late_breadth = _clamp_score(_safe_float(candidate.get("sector_late_breadth_score"), sector_breadth_score))
        leader_follower_sync = _clamp_score(_safe_float(candidate.get("leader_follower_sync_score"), 50.0))
        stock_sector_alpha = _clamp_score(50.0 + _safe_float(candidate.get("stock_vs_sector_intraday_alpha"), 0.0) * 5.0)
        sector_peer_rank = _clamp_score(_safe_float(candidate.get("sector_peer_rank_score"), 50.0))
        market_regime = _clamp_score(_safe_float(candidate.get("market_regime_score"), 50.0))
        sector_leader = _clamp_score(_safe_float(candidate.get("sector_leader_score"), 50.0))

        late_amount = sum(late_amounts) if late_amounts else 0.0
        late_volume_share = late_amount / total_amount if total_amount > 0 else 0.0
        late_volume_share_score = _clamp_score(late_volume_share / 0.35 * 100.0 if late_volume_share > 0 else 50.0)
        late_return_score = _clamp_score(50.0 + late_return * 12.0)
        late_above_vwap_ratio = (
            sum(1 for price in late_prices if price >= vwap) / len(late_prices) * 100.0
            if late_prices
            else 50.0
        )
        close_vs_vwap = (current - vwap) / vwap * 100.0 if vwap > 0 else 0.0
        close_vs_vwap_score = _clamp_score(50.0 + close_vs_vwap * 12.0)
        late_vwap_support_score = _clamp_score(close_vs_vwap_score * 0.6 + late_above_vwap_ratio * 0.4)
        late_high_near_close_score = _clamp_score(100.0 - pullback_risk)
        high_to_close_drawdown_score = _clamp_score(pullback_risk)

        morning_high = max(morning_prices)
        morning_low = min(morning_prices)
        morning_gain = (morning_high - prev_close) / prev_close * 100.0 if prev_close > 0 else 0.0
        morning_giveback = (morning_high - current) / morning_high * 100.0 if morning_high > 0 else 0.0
        morning_spike_fade_score = _clamp_score(morning_gain * 18.0 + morning_giveback * 16.0)
        afternoon_high = max(afternoon_prices) if afternoon_prices else high
        afternoon_fade_score = _clamp_score((afternoon_high - current) / afternoon_high * 100.0 * 18.0 if afternoon_high > 0 else 0.0)
        max_gain = (high - prev_close) / prev_close * 100.0 if prev_close > 0 else 0.0
        giveback = (high - current) / high * 100.0 if high > 0 else 0.0
        max_gain_giveback_ratio = _clamp_score(giveback / max_gain * 100.0 if max_gain > 0 else 0.0)

        first_half_amount = sum(first_half_amounts) if first_half_amounts else 0.0
        second_half_amount = sum(second_half_amounts) if second_half_amounts else 0.0
        first_vwap = (
            sum(price * amount for price, amount in zip(first_half_prices, first_half_amounts)) / first_half_amount
            if first_half_amount > 0
            else sum(first_half_prices) / len(first_half_prices)
        )
        second_vwap = (
            sum(price * amount for price, amount in zip(second_half_prices, second_half_amounts)) / second_half_amount
            if second_half_amount > 0 and second_half_prices
            else sum(second_half_prices) / len(second_half_prices) if second_half_prices else first_vwap
        )
        vwap_slope_score = _clamp_score(50.0 + ((second_vwap - first_vwap) / first_vwap * 100.0 * 12.0 if first_vwap > 0 else 0.0))
        was_below_vwap = any(price < vwap for price in prices[:midday_idx])
        vwap_reclaim_score = _clamp_score(close_vs_vwap_score + (18.0 if was_below_vwap and current >= vwap else 0.0))
        prices_above_vwap_ratio = sum(1 for price in prices if price >= vwap) / len(prices) * 100.0 if prices else 50.0
        first_third_above_vwap = sum(1 for price in prices[:morning_end] if price >= vwap) / len(morning_prices) * 100.0
        midday_prices = prices[morning_end:midday_idx + 1] if midday_idx + 1 > morning_end else prices[:midday_idx + 1]
        midday_above_vwap_ratio = (
            sum(1 for price in midday_prices if price >= vwap) / len(midday_prices) * 100.0
            if midday_prices else 50.0
        )
        avg_vwap_distance = (
            sum(abs(price - vwap) / vwap * 100.0 for price in prices) / len(prices)
            if vwap > 0 else 0.0
        )
        late_vwap_reclaim = any(price < vwap for price in prices[:morning_end]) and current >= vwap
        below_vwap_pullback = min(prices[morning_end:]) if len(prices) > morning_end else low
        pullback_vs_vwap = (below_vwap_pullback - vwap) / vwap * 100.0 if vwap > 0 else 0.0
        open_vwap_reclaim_score = _clamp_score(50.0 + close_vs_vwap * 12.0 + (18.0 if late_vwap_reclaim else 0.0) - max(0.0, 45.0 - first_third_above_vwap) * 0.25)
        midday_vwap_support_score = _clamp_score(midday_above_vwap_ratio * 0.55 + close_vs_vwap_score * 0.45)
        vwap_distance_stability_score = _clamp_score(82.0 - avg_vwap_distance * 10.0 + max(0.0, close_vs_vwap) * 6.0 - max_gain_giveback_ratio * 0.25)
        vwap_pullback_support_score = _clamp_score(50.0 + max(-2.0, pullback_vs_vwap) * 7.0 + close_vs_vwap * 10.0 + late_above_vwap_ratio * 0.25)
        vwap_breakout_confirm_score = _clamp_score(50.0 + close_vs_vwap * 12.0 + max(0.0, (current - max(prices[:-1])) / max(prices[:-1]) * 100.0 if max(prices[:-1]) > 0 else 0.0) * 24.0)
        vwap_above_ratio_score = _clamp_score(prices_above_vwap_ratio)

        price_progress = max(0.0, day_return)
        amount_acceleration = second_half_amount / first_half_amount if first_half_amount > 0 else 1.0
        amount_acceleration_score = _clamp_score(50.0 + (amount_acceleration - 1.0) * 30.0)
        volume_without_price_progress_risk = _clamp_score(max(0.0, amount_acceleration - 1.0) * 30.0 + max(0.0, 2.0 - price_progress) * 12.0)
        late_volume_efficiency_score = _clamp_score(50.0 + late_return * 15.0 - max(0.0, late_volume_share - 0.35) * 40.0)
        max_amount = max(amounts) if amounts else 0.0
        avg_amount = total_amount / len(amounts) if amounts else 0.0
        spike_ratio = max_amount / avg_amount if avg_amount > 0 else 1.0
        volume_spike_exhaustion_score = _clamp_score(max(0.0, spike_ratio - 1.8) * 25.0 + max_gain_giveback_ratio * 0.45)
        early_amount_surge_score = 50.0
        midday_amount_sustain_score = 50.0
        late_amount_surge_score = 50.0
        amount_trend_persistence_score = 50.0
        volume_price_alignment_score = 50.0
        breakout_volume_confirm_score = 50.0
        pullback_volume_dryup_score = 50.0
        late_money_flow_concentration_score = 50.0
        if amounts and len(amounts) == len(prices) and avg_amount > 0:
            early_window = max(2, min(4, len(amounts) // 3 or 2))
            early_avg_amount = sum(amounts[:early_window]) / early_window
            late_avg_amount = sum(late_amounts) / len(late_amounts) if late_amounts else avg_amount
            first_half_avg_amount = first_half_amount / len(first_half_amounts) if first_half_amounts else avg_amount
            second_half_avg_amount = second_half_amount / len(second_half_amounts) if second_half_amounts else avg_amount
            prior_late_amount = sum(amounts[:-late_window]) / len(amounts[:-late_window]) if len(amounts) > late_window else avg_amount
            early_return_for_flow = (prices[early_window - 1] / open_price - 1.0) * 100.0 if open_price > 0 else 0.0
            late_amount_ratio = late_avg_amount / prior_late_amount if prior_late_amount > 0 else 1.0
            early_amount_ratio = early_avg_amount / amounts[0] if amounts[0] > 0 else 1.0
            sustain_ratio = second_half_avg_amount / first_half_avg_amount if first_half_avg_amount > 0 else 1.0

            amount_up_count = sum(1 for previous, current_amount in zip(amounts, amounts[1:]) if current_amount >= previous)
            price_up_count = sum(1 for previous, current_price in zip(prices, prices[1:]) if current_price >= previous)
            aligned_count = sum(
                1
                for previous_price, current_price, previous_amount, current_amount
                in zip(prices, prices[1:], amounts, amounts[1:])
                if (current_price >= previous_price and current_amount >= previous_amount)
                or (current_price < previous_price and current_amount <= previous_amount)
            )
            down_amounts = [
                current_amount
                for previous_price, current_price, current_amount in zip(prices, prices[1:], amounts[1:])
                if current_price < previous_price
            ]
            down_avg_amount = sum(down_amounts) / len(down_amounts) if down_amounts else 0.0
            down_amount_ratio = down_avg_amount / avg_amount if avg_amount > 0 else 0.0
            prior_high_for_volume = max(prices[:-1])
            breakout_pct_for_volume = (current / prior_high_for_volume - 1.0) * 100.0 if prior_high_for_volume > 0 else 0.0

            early_amount_surge_score = _clamp_score(
                50.0 + (early_amount_ratio - 1.0) * 16.0 + early_return_for_flow * 8.0 - max_gain_giveback_ratio * 0.6
            )
            midday_amount_sustain_score = _clamp_score(
                50.0 + (sustain_ratio - 1.0) * 28.0 + max(0.0, day_return) * 4.0 - max_gain_giveback_ratio * 0.45
            )
            late_amount_surge_score = _clamp_score(
                50.0 + (late_amount_ratio - 1.0) * 24.0 + late_return * 10.0 - max_gain_giveback_ratio * 0.55
            )
            amount_trend_persistence_score = _clamp_score(
                (amount_up_count / max(1, len(amounts) - 1) * 45.0)
                + (price_up_count / max(1, len(prices) - 1) * 35.0)
                + max(0.0, day_return) * 3.0
                - max_gain_giveback_ratio * 0.25
            )
            volume_price_alignment_score = _clamp_score(
                aligned_count / max(1, len(prices) - 1) * 100.0
                + max(0.0, day_return) * 2.0
                - max_gain_giveback_ratio * 0.35
            )
            breakout_volume_confirm_score = _clamp_score(
                50.0 + breakout_pct_for_volume * 22.0 + (late_amount_ratio - 1.0) * 22.0 - max_gain_giveback_ratio * 0.5
            )
            pullback_volume_dryup_score = _clamp_score(
                78.0 - down_amount_ratio * 28.0 + max(0.0, day_return) * 2.0 - max_gain_giveback_ratio * 0.45
            )
            late_money_flow_concentration_score = _clamp_score(
                late_volume_share_score * 0.45 + late_amount_surge_score * 0.35 + late_volume_efficiency_score * 0.20
            )

        opening_drive = (prices[min(1, len(prices) - 1)] - prev_close) / prev_close * 100.0 if prev_close > 0 else 0.0
        opening_drive_score = _clamp_score(50.0 + opening_drive * 12.0)
        morning_strength_persist_score = _clamp_score(100.0 - (morning_giveback / max(morning_gain, 0.1) * 100.0 if morning_gain > 0 else 50.0))
        post_morning_low = min(prices[morning_end:]) if len(prices) > morning_end else morning_low
        repair_span = current - post_morning_low
        morning_pullback_repair_score = _clamp_score(50.0 + (repair_span / prev_close * 100.0 * 18.0 if prev_close > 0 else 0.0) - max(0.0, morning_giveback) * 3.0)
        midday_price = prices[midday_idx]
        open_to_midday_return = (midday_price - open_price) / open_price * 100.0 if open_price > 0 else 0.0
        open_to_midday_resilience_score = _clamp_score(50.0 + open_to_midday_return * 12.0 - max(0.0, (open_price - morning_low) / open_price * 100.0 if open_price > 0 else 0.0) * 8.0)

        positive_bar_ratio_score = _clamp_score(
            sum(1 for previous, current_price in zip(prices, prices[1:]) if current_price > previous)
            / max(1, len(prices) - 1)
            * 100.0
        )
        slope_window = prices[-min(6, len(prices)):]
        slope_anchor = slope_window[0]
        rolling_price_slope_score = _clamp_score(
            50.0 + ((slope_window[-1] / slope_anchor - 1.0) * 1200.0 if slope_anchor > 0 else 0.0)
        )
        prior_high = max(prices[:-1])
        breakout_pct = (current - prior_high) / prior_high * 100.0 if prior_high > 0 else 0.0
        intraday_breakout_strength_score = _clamp_score(50.0 + breakout_pct * 12.0)
        breakout_hold_score = _clamp_score(50.0 + breakout_pct * 18.0)
        reclaim_low = min(prices[-min(4, len(prices)):])
        reclaim_pct = (current - reclaim_low) / reclaim_low * 100.0 if reclaim_low > 0 else 0.0
        pullback_reclaim_momentum_score = _clamp_score(50.0 + reclaim_pct * 18.0)

        close_above_midrange_score = _clamp_score(50.0 + (close_position - 50.0) * 1.1 + day_return * 2.0)
        low_reclaim_position_score = _clamp_score(50.0 + ((current - low) / low * 100.0 * 7.0 if low > 0 else 0.0) - max_gain_giveback_ratio * 0.35)
        open_to_high_progress_score = _clamp_score(50.0 + max(0.0, day_return) * 5.0 + close_position * 0.35 - max_gain_giveback_ratio * 0.45)
        late_range = max(late_prices) - min(late_prices) if late_prices else 0.0
        full_range = intraday_range if intraday_range > 0 else 1.0
        late_range_expansion_score = _clamp_score(50.0 + late_return * 8.0 + late_range / full_range * 35.0 - max_gain_giveback_ratio * 0.35)
        high_area_acceptance_score = _clamp_score(late_high_near_close_score * 0.65 + close_position * 0.35)
        close_location_stability_score = _clamp_score(close_position * 0.55 + positive_bar_ratio_score * 0.25 + (100.0 - max_gain_giveback_ratio) * 0.20)

        sector_breadth_persistence_score = _clamp_score(sector_breadth_score * 0.45 + sector_breadth_change * 0.25 + sector_late_breadth * 0.30)
        sector_late_acceleration_score = _clamp_score(sector_late_breadth * 0.55 + sector_breadth_change * 0.25 + late_strength * 0.20)
        leader_sync_persistence_score = _clamp_score(leader_follower_sync * 0.65 + sector_leader * 0.20 + sector_breadth_score * 0.15)
        sector_alpha_confirmation_score = _clamp_score(stock_sector_alpha * 0.45 + sector_breadth_score * 0.25 + sector_late_breadth * 0.30)
        sector_breadth_quality_score = _clamp_score(sector_breadth_score * 0.35 + sector_late_breadth * 0.35 + market_regime * 0.15 + leader_follower_sync * 0.15)
        theme_confirmation_composite_score = _clamp_score(
            sector_breadth_persistence_score * 0.28
            + sector_late_acceleration_score * 0.22
            + leader_sync_persistence_score * 0.20
            + sector_alpha_confirmation_score * 0.18
            + sector_breadth_quality_score * 0.12
        )

        market_intraday_return = _safe_float(candidate.get("market_intraday_return_pct"), 0.0)
        sector_intraday_return = _safe_float(candidate.get("sector_intraday_return_pct"), 0.0)
        stock_vs_market_alpha = day_return - market_intraday_return
        stock_vs_sector_alpha_pct = day_return - sector_intraday_return
        stock_intraday_rank_proxy_score = _clamp_score(sector_peer_rank * 0.45 + stock_sector_alpha * 0.35 + close_position * 0.20)
        stock_vs_market_intraday_alpha_score = _clamp_score(50.0 + stock_vs_market_alpha * 7.0)
        relative_late_strength_score = _clamp_score(50.0 + (late_return - sector_intraday_return * 0.35) * 9.0 + stock_sector_alpha * 0.15)
        relative_vwap_strength_score = _clamp_score(close_vs_vwap_score * 0.55 + stock_sector_alpha * 0.25 + sector_peer_rank * 0.20)
        relative_breakout_leadership_score = _clamp_score(intraday_breakout_strength_score * 0.35 + stock_sector_alpha * 0.30 + sector_leader * 0.20 + sector_peer_rank * 0.15)
        relative_resilience_score = _clamp_score(close_position * 0.35 + stock_vs_market_intraday_alpha_score * 0.30 + stock_sector_alpha * 0.20 + (100.0 - max_gain_giveback_ratio) * 0.15)

        lower_low_count = sum(1 for previous, current_price in zip(prices, prices[1:]) if current_price < previous)
        late_breakdown_pct = (late_anchor - current) / late_anchor * 100.0 if late_anchor > 0 and current < late_anchor else 0.0
        open_high_reversal_risk = _clamp_score(max_gain_giveback_ratio * 0.55 + max(0.0, morning_giveback) * 8.0 + max(0.0, -day_return) * 10.0)
        late_breakdown_risk = _clamp_score(late_breakdown_pct * 18.0 + max(0.0, 50.0 - close_position) * 0.65 + max(0.0, -close_vs_vwap) * 8.0)
        failed_breakout_risk = _clamp_score(max_gain_giveback_ratio * 0.70 + max(0.0, -breakout_pct) * 10.0 + max(0.0, 55.0 - close_position) * 0.25)
        lower_low_sequence_risk = _clamp_score(lower_low_count / max(1, len(prices) - 1) * 75.0 + max(0.0, -day_return) * 8.0)
        volatility_expansion_reversal_risk = _clamp_score((intraday_range / open_price * 100.0 if open_price > 0 else 0.0) * 7.0 + max_gain_giveback_ratio * 0.55)
        weak_close_after_volume_risk = _clamp_score(max(0.0, spike_ratio - 1.0) * 18.0 + max(0.0, 50.0 - close_position) * 0.8 + max(0.0, -day_return) * 7.0)

        first_hour_follow_through_score = _clamp_score(
            50.0 + early_return * 8.0 + morning_strength_persist_score * 0.25 - max_gain_giveback_ratio * 0.70
        )
        midday_hold_score = _clamp_score(open_to_midday_resilience_score * 0.55 + close_position * 0.25 + vwap_slope_score * 0.20)
        afternoon_low = min(afternoon_prices) if afternoon_prices else low
        afternoon_recovery_pct = (current - afternoon_low) / afternoon_low * 100.0 if afternoon_low > 0 else 0.0
        afternoon_recovery_score = _clamp_score(50.0 + afternoon_recovery_pct * 12.0 + late_return * 5.0 - max_gain_giveback_ratio * 0.25)
        late_session_acceleration_score = _clamp_score(late_return_score * 0.45 + rolling_price_slope_score * 0.35 + late_strength * 0.20)
        session_consistency_score = _clamp_score(positive_bar_ratio_score * 0.45 + (100.0 - max_gain_giveback_ratio) * 0.30 + close_position * 0.25)
        close_auction_strength_proxy_score = _clamp_score(late_high_near_close_score * 0.45 + late_strength * 0.35 + close_position * 0.20)

        spread_bps = _safe_float(candidate.get("bid_ask_spread_bps"), None)
        turnover_rate_pct = _safe_float(candidate.get("turnover_rate_pct"), None)
        limit_up_price = _safe_float(candidate.get("limit_up_price"), None)
        limit_down_price = _safe_float(candidate.get("limit_down_price"), None)
        amount_continuity = amount_trend_persistence_score
        execution_liquidity_amount_score = _clamp_score(math.log10(max(total_amount, 1.0)) * 20.0 - 90.0)
        execution_amount_continuity_score = _clamp_score(amount_continuity * 0.65 + volume_price_alignment_score * 0.35)
        execution_price_impact_risk = _clamp_score(max(0.0, spike_ratio - 1.4) * 24.0 + max(0.0, avg_vwap_distance - 1.2) * 12.0 + max(0.0, 60.0 - execution_liquidity_amount_score) * 0.45)
        execution_vwap_slippage_risk = _clamp_score(
            avg_vwap_distance * 10.0
            + max(0.0, 65.0 - vwap_distance_stability_score) * 0.35
            + max(0.0, 60.0 - volume_price_alignment_score) * 0.25
            + max(0.0, 50.0 - close_position) * 0.20
        )
        execution_spread_proxy_score = (
            _clamp_score(100.0 - spread_bps * 1.8)
            if spread_bps is not None
            else _clamp_score(70.0 - execution_price_impact_risk * 0.35)
        )
        execution_turnover_depth_score = (
            _clamp_score(turnover_rate_pct * 18.0)
            if turnover_rate_pct is not None
            else _clamp_score(execution_liquidity_amount_score * 0.70 + amount_continuity * 0.30)
        )
        execution_gap_to_limit_up_score = (
            _clamp_score((limit_up_price - current) / current * 600.0 if current > 0 and limit_up_price and limit_up_price > current else 20.0)
            if limit_up_price is not None
            else _clamp_score(100.0 - max(0.0, day_return - 7.0) * 12.0)
        )
        execution_gap_to_limit_down_risk = (
            _clamp_score((current - limit_down_price) / current * -350.0 + 80.0 if current > 0 and limit_down_price and limit_down_price < current else 70.0)
            if limit_down_price is not None
            else _clamp_score(max(0.0, -day_return) * 12.0 + late_breakdown_risk * 0.4)
        )
        execution_tradeability_score = _clamp_score(
            execution_liquidity_amount_score * 0.26
            + execution_amount_continuity_score * 0.20
            + execution_spread_proxy_score * 0.18
            + execution_turnover_depth_score * 0.16
            + execution_gap_to_limit_up_score * 0.10
            + (100.0 - execution_price_impact_risk) * 0.10
        )
        execution_microstructure_quality_score = _clamp_score(
            execution_tradeability_score * 0.45
            + (100.0 - execution_vwap_slippage_risk) * 0.20
            + (100.0 - execution_gap_to_limit_down_risk) * 0.15
            + volume_price_alignment_score * 0.20
        )

        cashout_late_surge_risk = _clamp_score(max(0.0, late_amount_surge_score - 55.0) * 1.1 + max(0.0, late_volume_share_score - 70.0) * 0.75)
        cashout_late_fade_risk = _clamp_score(late_breakdown_risk * 0.60 + max(0.0, 50.0 - late_return_score) * 0.55)
        cashout_high_volume_stall_risk = _clamp_score(max(0.0, late_amount_surge_score - 55.0) * 0.65 + max(0.0, 55.0 - late_return_score) * 0.85 + volume_without_price_progress_risk * 0.35)
        cashout_close_giveback_risk = _clamp_score(high_to_close_drawdown_score * 0.75 + max_gain_giveback_ratio * 0.35)
        cashout_tail_amount_concentration_risk = _clamp_score(max(0.0, late_volume_share_score - 55.0) * 0.95 + max(0.0, spike_ratio - 1.8) * 18.0)
        cashout_overheat_without_breadth_risk = _clamp_score(max(0.0, day_return - 4.0) * 10.0 + max(0.0, 55.0 - sector_breadth_quality_score) * 0.75)
        cashout_vwap_extension_risk = _clamp_score(
            avg_vwap_distance * 8.0
            + max(0.0, 65.0 - late_vwap_support_score) * 0.45
            + max(0.0, 60.0 - sector_breadth_quality_score) * 0.25
        )
        cashout_failed_late_breakout_risk = _clamp_score(failed_breakout_risk * 0.65 + max(0.0, 60.0 - breakout_hold_score) * 0.55)
        cashout_auction_weakness_risk = _clamp_score(max(0.0, 60.0 - close_auction_strength_proxy_score) * 1.1 + max(0.0, -late_return) * 12.0)
        cashout_next_day_pressure_proxy = _clamp_score(
            cashout_late_surge_risk * 0.16
            + cashout_late_fade_risk * 0.14
            + cashout_high_volume_stall_risk * 0.12
            + cashout_close_giveback_risk * 0.12
            + cashout_tail_amount_concentration_risk * 0.10
            + cashout_overheat_without_breadth_risk * 0.12
            + cashout_vwap_extension_risk * 0.10
            + cashout_failed_late_breakout_risk * 0.08
            + cashout_auction_weakness_risk * 0.06
        )

        hot_sector_concentration = _safe_float(candidate.get("market_hot_sector_concentration"), None)
        concentration_balance = (
            _clamp_score(100.0 - abs(hot_sector_concentration - 0.45) * 140.0)
            if hot_sector_concentration is not None
            else _clamp_score(100.0 - max(0.0, sector_late_breadth - sector_breadth_score) * 0.15)
        )
        sector_continuation_breadth_score = sector_breadth_persistence_score
        sector_continuation_late_breadth_score = sector_late_acceleration_score
        sector_continuation_leader_sync_score = leader_sync_persistence_score
        sector_continuation_alpha_support_score = sector_alpha_confirmation_score
        sector_continuation_peer_rank_score = _clamp_score(sector_peer_rank * 0.70 + stock_sector_alpha * 0.30)
        sector_continuation_theme_quality_score = theme_confirmation_composite_score
        sector_continuation_market_alignment_score = _clamp_score(sector_breadth_quality_score * 0.65 + market_regime * 0.35)
        sector_continuation_breadth_acceleration_score = _clamp_score(sector_breadth_change * 0.55 + sector_late_breadth * 0.45)
        sector_continuation_concentration_balance_score = concentration_balance
        sector_continuation_composite_score = _clamp_score(
            sector_continuation_breadth_score * 0.14
            + sector_continuation_late_breadth_score * 0.13
            + sector_continuation_leader_sync_score * 0.12
            + sector_continuation_alpha_support_score * 0.12
            + sector_continuation_peer_rank_score * 0.10
            + sector_continuation_theme_quality_score * 0.13
            + sector_continuation_market_alignment_score * 0.10
            + sector_continuation_breadth_acceleration_score * 0.09
            + sector_continuation_concentration_balance_score * 0.07
        )

        market_vwap_position_score = _clamp_score(_safe_float(candidate.get("market_vwap_position_score"), 50.0))
        market_breadth_score = _clamp_score(_safe_float(candidate.get("market_breadth_score"), market_regime))
        market_limit_up_count = _safe_float(candidate.get("market_limit_up_count"), None)
        market_limit_down_count = _safe_float(candidate.get("market_limit_down_count"), None)
        market_limit_failure_rate = _safe_float(candidate.get("market_limit_up_failure_rate"), None)
        leader_continuation_rate = _safe_float(candidate.get("leader_continuation_rate"), None)
        market_environment_index_trend_score = _clamp_score(50.0 + market_intraday_return * 12.0 + market_regime * 0.35)
        market_environment_vwap_support_score = market_vwap_position_score
        market_environment_breadth_score = market_breadth_score
        market_environment_limit_up_breadth_score = (
            _clamp_score(market_limit_up_count / 80.0 * 100.0)
            if market_limit_up_count is not None
            else _clamp_score(market_regime * 0.6 + sector_breadth_score * 0.4)
        )
        market_environment_limit_down_risk = (
            _clamp_score(market_limit_down_count / 30.0 * 100.0)
            if market_limit_down_count is not None
            else _clamp_score(max(0.0, -market_intraday_return) * 18.0)
        )
        market_environment_failure_risk = (
            _clamp_score(market_limit_failure_rate * 100.0)
            if market_limit_failure_rate is not None
            else _clamp_score(max(0.0, 55.0 - market_breadth_score) * 0.8)
        )
        market_environment_leader_continuation_score = (
            _clamp_score(leader_continuation_rate * 100.0)
            if leader_continuation_rate is not None
            else _clamp_score(leader_follower_sync * 0.60 + sector_leader * 0.40)
        )
        market_environment_crowding_risk = (
            _clamp_score(hot_sector_concentration * 100.0)
            if hot_sector_concentration is not None
            else _clamp_score(max(0.0, market_environment_limit_up_breadth_score - 80.0) * 0.8)
        )
        market_environment_risk_appetite_score = _clamp_score(
            market_environment_index_trend_score * 0.28
            + market_environment_breadth_score * 0.24
            + market_environment_limit_up_breadth_score * 0.18
            + market_environment_leader_continuation_score * 0.18
            + (100.0 - market_environment_limit_down_risk) * 0.12
        )
        market_environment_composite_score = _clamp_score(
            market_environment_risk_appetite_score * 0.45
            + market_environment_vwap_support_score * 0.18
            + (100.0 - market_environment_failure_risk) * 0.16
            + (100.0 - market_environment_crowding_risk) * 0.10
            + market_environment_leader_continuation_score * 0.11
        )

        close_position_score = _clamp_score(close_position)
        pullback_risk_score = _clamp_score(pullback_risk)
        emotion_score = _clamp_score(
            close_position_score * 0.26
            + late_strength * 0.24
            + volume_price_confirm * 0.22
            + sector_breadth_score * 0.16
            + (100.0 - pullback_risk_score) * 0.12
        )
        if current < open_price and early_return > 2.0:
            emotion_score = _clamp_score(emotion_score - 8.0)

        return {
            "intraday_close_position_score": close_position_score,
            "intraday_high_pullback_risk_score": pullback_risk_score,
            "intraday_volume_price_confirm_score": volume_price_confirm,
            "intraday_sector_breadth_score": sector_breadth_score,
            "intraday_late_strength_score": late_strength,
            "short_burst_intraday_emotion_score_shadow": emotion_score,
            "late_return_30m_score": late_return_score,
            "late_vwap_support_score": late_vwap_support_score,
            "late_volume_share_score": late_volume_share_score,
            "late_high_near_close_score": late_high_near_close_score,
            "high_to_close_drawdown_score": high_to_close_drawdown_score,
            "morning_spike_fade_score": morning_spike_fade_score,
            "afternoon_fade_score": afternoon_fade_score,
            "max_gain_giveback_ratio": max_gain_giveback_ratio,
            "close_vs_vwap_score": close_vs_vwap_score,
            "late_price_above_vwap_ratio": _clamp_score(late_above_vwap_ratio),
            "vwap_slope_score": vwap_slope_score,
            "vwap_reclaim_score": vwap_reclaim_score,
            "open_vwap_reclaim_score": open_vwap_reclaim_score,
            "midday_vwap_support_score": midday_vwap_support_score,
            "vwap_distance_stability_score": vwap_distance_stability_score,
            "vwap_pullback_support_score": vwap_pullback_support_score,
            "vwap_breakout_confirm_score": vwap_breakout_confirm_score,
            "vwap_above_ratio_score": vwap_above_ratio_score,
            "volume_without_price_progress_risk": volume_without_price_progress_risk,
            "late_volume_efficiency_score": late_volume_efficiency_score,
            "amount_acceleration_score": amount_acceleration_score,
            "volume_spike_exhaustion_score": volume_spike_exhaustion_score,
            "early_amount_surge_score": early_amount_surge_score,
            "midday_amount_sustain_score": midday_amount_sustain_score,
            "late_amount_surge_score": late_amount_surge_score,
            "amount_trend_persistence_score": amount_trend_persistence_score,
            "volume_price_alignment_score": volume_price_alignment_score,
            "breakout_volume_confirm_score": breakout_volume_confirm_score,
            "pullback_volume_dryup_score": pullback_volume_dryup_score,
            "late_money_flow_concentration_score": late_money_flow_concentration_score,
            "opening_drive_score": opening_drive_score,
            "morning_strength_persist_score": morning_strength_persist_score,
            "morning_pullback_repair_score": morning_pullback_repair_score,
            "open_to_midday_resilience_score": open_to_midday_resilience_score,
            "sector_intraday_breadth_change": sector_breadth_change,
            "sector_late_breadth_score": sector_late_breadth,
            "leader_follower_sync_score": leader_follower_sync,
            "stock_vs_sector_intraday_alpha": stock_sector_alpha,
            "sector_peer_rank_score": sector_peer_rank,
            "market_regime_score": market_regime,
            "sector_leader_score": sector_leader,
            "open_to_high_progress_score": open_to_high_progress_score,
            "close_above_midrange_score": close_above_midrange_score,
            "low_reclaim_position_score": low_reclaim_position_score,
            "late_range_expansion_score": late_range_expansion_score,
            "high_area_acceptance_score": high_area_acceptance_score,
            "close_location_stability_score": close_location_stability_score,
            "sector_breadth_persistence_score": sector_breadth_persistence_score,
            "sector_late_acceleration_score": sector_late_acceleration_score,
            "leader_sync_persistence_score": leader_sync_persistence_score,
            "sector_alpha_confirmation_score": sector_alpha_confirmation_score,
            "sector_breadth_quality_score": sector_breadth_quality_score,
            "theme_confirmation_composite_score": theme_confirmation_composite_score,
            "stock_intraday_rank_proxy_score": stock_intraday_rank_proxy_score,
            "stock_vs_market_intraday_alpha_score": stock_vs_market_intraday_alpha_score,
            "relative_late_strength_score": relative_late_strength_score,
            "relative_vwap_strength_score": relative_vwap_strength_score,
            "relative_breakout_leadership_score": relative_breakout_leadership_score,
            "relative_resilience_score": relative_resilience_score,
            "open_high_reversal_risk": open_high_reversal_risk,
            "late_breakdown_risk": late_breakdown_risk,
            "failed_breakout_risk": failed_breakout_risk,
            "lower_low_sequence_risk": lower_low_sequence_risk,
            "volatility_expansion_reversal_risk": volatility_expansion_reversal_risk,
            "weak_close_after_volume_risk": weak_close_after_volume_risk,
            "first_hour_follow_through_score": first_hour_follow_through_score,
            "midday_hold_score": midday_hold_score,
            "afternoon_recovery_score": afternoon_recovery_score,
            "late_session_acceleration_score": late_session_acceleration_score,
            "session_consistency_score": session_consistency_score,
            "close_auction_strength_proxy_score": close_auction_strength_proxy_score,
            "return_5m_strength_score": _intraday_return_strength(prices, 1),
            "return_15m_strength_score": _intraday_return_strength(prices, 3),
            "return_60m_strength_score": _intraday_return_strength(prices, 12),
            "positive_bar_ratio_score": positive_bar_ratio_score,
            "rolling_price_slope_score": rolling_price_slope_score,
            "intraday_breakout_strength_score": intraday_breakout_strength_score,
            "breakout_hold_score": breakout_hold_score,
            "pullback_reclaim_momentum_score": pullback_reclaim_momentum_score,
            "execution_liquidity_amount_score": execution_liquidity_amount_score,
            "execution_amount_continuity_score": execution_amount_continuity_score,
            "execution_price_impact_risk": execution_price_impact_risk,
            "execution_vwap_slippage_risk": execution_vwap_slippage_risk,
            "execution_spread_proxy_score": execution_spread_proxy_score,
            "execution_turnover_depth_score": execution_turnover_depth_score,
            "execution_tradeability_score": execution_tradeability_score,
            "execution_gap_to_limit_up_score": execution_gap_to_limit_up_score,
            "execution_gap_to_limit_down_risk": execution_gap_to_limit_down_risk,
            "execution_microstructure_quality_score": execution_microstructure_quality_score,
            "cashout_late_surge_risk": cashout_late_surge_risk,
            "cashout_late_fade_risk": cashout_late_fade_risk,
            "cashout_high_volume_stall_risk": cashout_high_volume_stall_risk,
            "cashout_close_giveback_risk": cashout_close_giveback_risk,
            "cashout_tail_amount_concentration_risk": cashout_tail_amount_concentration_risk,
            "cashout_overheat_without_breadth_risk": cashout_overheat_without_breadth_risk,
            "cashout_vwap_extension_risk": cashout_vwap_extension_risk,
            "cashout_failed_late_breakout_risk": cashout_failed_late_breakout_risk,
            "cashout_auction_weakness_risk": cashout_auction_weakness_risk,
            "cashout_next_day_pressure_proxy": cashout_next_day_pressure_proxy,
            "sector_continuation_breadth_score": sector_continuation_breadth_score,
            "sector_continuation_late_breadth_score": sector_continuation_late_breadth_score,
            "sector_continuation_leader_sync_score": sector_continuation_leader_sync_score,
            "sector_continuation_alpha_support_score": sector_continuation_alpha_support_score,
            "sector_continuation_peer_rank_score": sector_continuation_peer_rank_score,
            "sector_continuation_theme_quality_score": sector_continuation_theme_quality_score,
            "sector_continuation_market_alignment_score": sector_continuation_market_alignment_score,
            "sector_continuation_breadth_acceleration_score": sector_continuation_breadth_acceleration_score,
            "sector_continuation_concentration_balance_score": sector_continuation_concentration_balance_score,
            "sector_continuation_composite_score": sector_continuation_composite_score,
            "market_environment_index_trend_score": market_environment_index_trend_score,
            "market_environment_vwap_support_score": market_environment_vwap_support_score,
            "market_environment_breadth_score": market_environment_breadth_score,
            "market_environment_limit_up_breadth_score": market_environment_limit_up_breadth_score,
            "market_environment_limit_down_risk": market_environment_limit_down_risk,
            "market_environment_failure_risk": market_environment_failure_risk,
            "market_environment_leader_continuation_score": market_environment_leader_continuation_score,
            "market_environment_crowding_risk": market_environment_crowding_risk,
            "market_environment_risk_appetite_score": market_environment_risk_appetite_score,
            "market_environment_composite_score": market_environment_composite_score,
        }
    except Exception:
        return empty


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
            "liquidity_score": None,
            "chasing_risk_score": None,
            "drawdown_depth_20": None,
            "breakout_distance_20": None,
            "relative_strength_20": None,
            "relative_strength_60": None,
            "risk_adjusted_return_20": None,
            "volume_stability_score": None,
            "trend_persistence_score": None,
            "short_emotion_heat_score": None,
            "sector_burst_breadth_score": None,
            "limit_attention_score": None,
            "intraday_reversal_risk_score": None,
            "close_strength_score": None,
            "volume_burst_quality_score": None,
            "single_name_overheat_score": None,
            "next_day_cashout_risk_score": None,
            "short_burst_emotion_score_v1": None,
            "short_burst_emotion_score_v2": None,
            "market_short_emotion_score": None,
            "limit_up_breadth_score": None,
            "limit_up_failure_risk": None,
            "leader_continuation_score": None,
            "short_burst_environment_score": None,
            "crowding_heat_score": None,
            "news_heat_score": None,
            "policy_catalyst_score": None,
            "earnings_catalyst_score": None,
            "event_freshness_score": None,
            "event_continuation_score": None,
            "negative_news_risk_score": None,
            "rumor_hype_risk_score": None,
            "short_burst_news_emotion_score_shadow": None,
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
    # 基于5日涨幅、价格位置、单日涨幅的追高风险评分
    # score = raw_value (风险分)，direction lower_is_better
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

            # 评分：base=30，逐项加分
            base = 30

            # return_5d 加分
            if return_5d > 0.20:
                base += 30
            elif return_5d > 0.12:
                base += 20
            elif return_5d > 0.08:
                base += 10

            # near_20_high 加分
            if near_20_high >= 0.99:
                base += 20
            elif near_20_high >= 0.96:
                base += 10

            # daily_return 加分
            if daily_return > 0.07:
                base += 20
            elif daily_return > 0.04:
                base += 10

            # 限制在 0-100
            base = max(0, min(100, base))
            result["chasing_risk_score"] = round(base, 2)
        else:
            result["chasing_risk_score"] = None
    except Exception:
        result["chasing_risk_score"] = None

    # ============================================================
    # drawdown_depth_20: 20日回撤深度 (%)
    # 当前价格相对近20日高点的回撤百分比
    # 与 breakout_distance_20 数值相同，但用于风险解释
    # raw: (high_20 - close_t) / high_20 * 100
    # score: lower_is_better, raw<=0->100, raw>=30->0
    # ============================================================
    try:
        if len(highs) >= 20 and len(closes) > 0:
            high_20 = max(highs[:20])
            close_t = closes[0]
            if high_20 > 0:
                # 回撤百分比：0=贴近高点, 30=回撤30%
                depth = (high_20 - close_t) / high_20 * 100
                raw = round(max(0, depth), 2)
                # score: lower_is_better 映射
                # raw <= 0 -> score 100; raw >= 30 -> score 0
                score = 100.0 - raw * (100.0 / 30.0)
                score = max(0.0, min(100.0, score))
                result["drawdown_depth_20"] = round(raw, 2)
                # score 将由 normalizer 处理 (already_scored -> clamp to 0-100)
                # 但这里 pre-compute 以确保正确分布
                result["_drawdown_depth_20_score"] = round(score, 2)
            else:
                result["drawdown_depth_20"] = None
        else:
            result["drawdown_depth_20"] = None
    except Exception:
        result["drawdown_depth_20"] = None

    # ============================================================
    # breakout_distance_20: 距20日突破距离 (%)
    # 当前价格距离近20日高点的百分比距离
    # raw: (high_20 - close_t) / high_20 * 100
    # score: lower_is_better, raw<=0->100, raw>=20->0
    # ============================================================
    try:
        if len(highs) >= 20 and len(closes) > 0:
            high_20 = max(highs[:20])
            close_t = closes[0]
            if high_20 > 0:
                # 距离百分比：0=贴近高点, 20=距离20%
                distance = (high_20 - close_t) / high_20 * 100
                raw = round(max(0, distance), 2)
                # score: lower_is_better 映射
                # raw <= 0 -> score 100; raw >= 20 -> score 0
                score = 100.0 - raw * 5.0
                score = max(0.0, min(100.0, score))
                result["breakout_distance_20"] = raw
                # score 将由 normalizer 处理 (already_scored -> clamp to 0-100)
                result["_breakout_distance_20_score"] = round(score, 2)
            else:
                result["breakout_distance_20"] = None
        else:
            result["breakout_distance_20"] = None
    except Exception:
        result["breakout_distance_20"] = None

    # ============================================================
    # relative_strength_20 / relative_strength_60: price momentum (%)
    # risk_adjusted_return_20: 20d return adjusted by daily-return volatility
    # ============================================================
    try:
        if len(closes) >= 21 and closes[20] > 0:
            return_20 = (closes[0] / closes[20] - 1.0) * 100.0
            result["relative_strength_20"] = round(return_20, 4)
            rs20_score = 50.0 + return_20 * 2.0
            result["_relative_strength_20_score"] = round(max(0.0, min(100.0, rs20_score)), 2)
        else:
            result["relative_strength_20"] = None
            result["_relative_strength_20_score"] = None

        if len(closes) >= 61 and closes[60] > 0:
            return_60 = (closes[0] / closes[60] - 1.0) * 100.0
            result["relative_strength_60"] = round(return_60, 4)
            rs60_score = 50.0 + return_60
            result["_relative_strength_60_score"] = round(max(0.0, min(100.0, rs60_score)), 2)
        else:
            result["relative_strength_60"] = None
            result["_relative_strength_60_score"] = None

        daily_returns: list[float] = []
        for i in range(20):
            if len(closes) <= i + 1 or closes[i + 1] <= 0:
                continue
            daily_returns.append(closes[i] / closes[i + 1] - 1.0)

        if result.get("relative_strength_20") is not None and len(daily_returns) >= 10:
            mean_return = sum(daily_returns) / len(daily_returns)
            variance = sum((value - mean_return) ** 2 for value in daily_returns) / len(daily_returns)
            volatility = math.sqrt(variance)
            risk_adjusted = (mean_return / volatility) if volatility > 0 else (2.5 if mean_return > 0 else 0.0)
            result["risk_adjusted_return_20"] = round(risk_adjusted, 4)
            risk_adjusted_score = 50.0 + risk_adjusted * 15.0
            result["_risk_adjusted_return_20_score"] = round(max(0.0, min(100.0, risk_adjusted_score)), 2)
        else:
            result["risk_adjusted_return_20"] = None
            result["_risk_adjusted_return_20_score"] = None
    except Exception:
        result["relative_strength_20"] = None
        result["_relative_strength_20_score"] = None
        result["relative_strength_60"] = None
        result["_relative_strength_60_score"] = None
        result["risk_adjusted_return_20"] = None
        result["_risk_adjusted_return_20_score"] = None

    # ============================================================
    # volume_stability_score: reward sustained activity, penalize one-day spikes
    # ============================================================
    try:
        amounts = [_safe_float(b.get("amount", 0)) for b in bars]
        recent_amounts = [value for value in amounts[:10] if value > 0]
        base_amounts = [value for value in amounts[:20] if value > 0]
        if len(recent_amounts) >= 5 and len(base_amounts) >= 10:
            recent_avg = sum(recent_amounts) / len(recent_amounts)
            base_avg = sum(base_amounts) / len(base_amounts)
            amount_ratio = recent_avg / base_avg if base_avg > 0 else 1.0
            mean_amount = base_avg
            amount_std = math.sqrt(sum((value - mean_amount) ** 2 for value in base_amounts) / len(base_amounts))
            coeff_var = amount_std / mean_amount if mean_amount > 0 else 0.0
            max_ratio = max(base_amounts) / base_avg if base_avg > 0 else 1.0

            score = 50.0
            if 1.05 <= amount_ratio <= 1.8:
                score += 20.0
            elif 0.9 <= amount_ratio < 1.05:
                score += 8.0
            elif amount_ratio > 2.5:
                score -= 15.0

            if coeff_var <= 0.25:
                score += 20.0
            elif coeff_var <= 0.5:
                score += 10.0
            elif coeff_var > 1.0:
                score -= 20.0
            elif coeff_var > 0.75:
                score -= 10.0

            if max_ratio > 3.0:
                score -= 25.0
            elif max_ratio > 2.2:
                score -= 12.0

            result["volume_stability_score"] = round(max(0.0, min(100.0, score)), 2)
        else:
            result["volume_stability_score"] = None
    except Exception:
        result["volume_stability_score"] = None

    # ============================================================
    # trend_persistence_score: share of recent closes above rolling MA20
    # ============================================================
    try:
        if len(closes) >= 40:
            above_count = 0
            total = 0
            for i in range(20):
                window = closes[i:i + 20]
                if len(window) < 20:
                    continue
                ma20 = sum(window) / 20
                total += 1
                if closes[i] >= ma20:
                    above_count += 1
            if total:
                result["trend_persistence_score"] = round(above_count / total * 100.0, 2)
            else:
                result["trend_persistence_score"] = None
        else:
            result["trend_persistence_score"] = None
    except Exception:
        result["trend_persistence_score"] = None

    # ============================================================
    # Short-burst emotion factors: shadow-only 1d observation inputs.
    # These distinguish next-day emotion/overheat from trend continuity.
    # ============================================================
    try:
        close_t = closes[0] if closes else 0.0
        prev_close = closes[1] if len(closes) > 1 else 0.0
        high_t = highs[0] if highs else 0.0
        low_t = lows[0] if lows else 0.0
        open_t = _safe_float(bars[0].get("open", close_t)) if bars else close_t
        day_range = high_t - low_t
        daily_return_pct = (close_t / prev_close - 1.0) * 100.0 if prev_close > 0 else 0.0

        if day_range > 0:
            close_strength = (close_t - low_t) / day_range * 100.0
            upper_shadow = (high_t - max(open_t, close_t)) / day_range * 100.0
            giveback = (high_t - close_t) / day_range * 100.0
            result["close_strength_score"] = _clamp_score(close_strength)
            result["intraday_reversal_risk_score"] = _clamp_score(upper_shadow * 0.55 + giveback * 0.45)
        else:
            result["close_strength_score"] = None
            result["intraday_reversal_risk_score"] = None

        amount_ratio = result.get("amount_ratio_20")
        volume_stability = result.get("volume_stability_score")
        if amount_ratio is not None:
            if 1.15 <= amount_ratio <= 1.9:
                volume_quality = 82.0
            elif 0.95 <= amount_ratio < 1.15 or 1.9 < amount_ratio <= 2.4:
                volume_quality = 65.0
            elif amount_ratio > 2.4:
                volume_quality = 42.0
            else:
                volume_quality = 45.0
            if volume_stability is not None:
                volume_quality = volume_quality * 0.6 + volume_stability * 0.4
            result["volume_burst_quality_score"] = _clamp_score(volume_quality)
        else:
            result["volume_burst_quality_score"] = None

        if daily_return_pct >= 9.5:
            limit_attention = 88.0
        elif daily_return_pct >= 7.0:
            limit_attention = 78.0
        elif daily_return_pct >= 4.0:
            limit_attention = 66.0
        elif daily_return_pct >= 1.5:
            limit_attention = 56.0
        elif daily_return_pct >= 0:
            limit_attention = 48.0
        else:
            limit_attention = 35.0
        result["limit_attention_score"] = _clamp_score(limit_attention)

        sector_burst = _safe_float(candidate.get("sector_burst_score"), None)
        sector_support = _safe_float(candidate.get("sector_support_score"), None)
        if sector_burst is not None and sector_support is not None:
            sector_breadth = sector_burst * 0.65 + sector_support * 0.35
        elif sector_burst is not None:
            sector_breadth = sector_burst
        elif sector_support is not None:
            sector_breadth = sector_support
        else:
            sector_breadth = None
        result["sector_burst_breadth_score"] = None if sector_breadth is None else _clamp_score(sector_breadth)

        stock_short = _safe_float(candidate.get("stock_short_score_v2"), None)
        heat_parts = [
            result.get("limit_attention_score"),
            result.get("volume_burst_quality_score"),
            result.get("sector_burst_breadth_score"),
            stock_short,
        ]
        heat_present = [value for value in heat_parts if value is not None]
        result["short_emotion_heat_score"] = (
            _clamp_score(sum(heat_present) / len(heat_present)) if heat_present else None
        )

        chasing_risk = result.get("chasing_risk_score")
        relative_strength = result.get("_relative_strength_20_score")
        sector_weakness = 50.0
        if result.get("sector_burst_breadth_score") is not None:
            sector_weakness = 100.0 - result["sector_burst_breadth_score"]
        amount_extreme = 50.0
        if amount_ratio is not None:
            amount_extreme = 80.0 if amount_ratio >= 2.5 else 60.0 if amount_ratio >= 1.8 else 35.0
        overheat_parts = [
            chasing_risk,
            relative_strength,
            sector_weakness,
            amount_extreme,
        ]
        overheat_present = [value for value in overheat_parts if value is not None]
        result["single_name_overheat_score"] = (
            _clamp_score(sum(overheat_present) / len(overheat_present)) if overheat_present else None
        )

        cashout_parts = [
            result.get("intraday_reversal_risk_score"),
            result.get("single_name_overheat_score"),
            100.0 - result["close_strength_score"] if result.get("close_strength_score") is not None else None,
            amount_extreme,
        ]
        cashout_present = [value for value in cashout_parts if value is not None]
        if result.get("sector_burst_breadth_score") is not None:
            sector_relief = max(0.0, (result["sector_burst_breadth_score"] - 55.0) * 0.25)
        else:
            sector_relief = 0.0
        result["next_day_cashout_risk_score"] = (
            _clamp_score(sum(cashout_present) / len(cashout_present) - sector_relief)
            if cashout_present else None
        )

        positive_parts = [
            result.get("short_emotion_heat_score"),
            result.get("sector_burst_breadth_score"),
            result.get("close_strength_score"),
            result.get("volume_burst_quality_score"),
            result.get("limit_attention_score"),
        ]
        risk_parts = [
            result.get("intraday_reversal_risk_score"),
            result.get("single_name_overheat_score"),
            result.get("next_day_cashout_risk_score"),
        ]
        positive_present = [value for value in positive_parts if value is not None]
        risk_present = [value for value in risk_parts if value is not None]
        if positive_present:
            positive_score = sum(positive_present) / len(positive_present)
            risk_score = sum(risk_present) / len(risk_present) if risk_present else 50.0
            result["short_burst_emotion_score_v1"] = _clamp_score(positive_score * 0.72 + (100.0 - risk_score) * 0.28)
        else:
            result["short_burst_emotion_score_v1"] = None

        weighted_positive_parts = [
            (result.get("volume_burst_quality_score"), 0.32),
            (result.get("close_strength_score"), 0.24),
            (result.get("sector_burst_breadth_score"), 0.18),
            (result.get("short_emotion_heat_score"), 0.10),
            (result.get("limit_attention_score"), 0.06),
        ]
        weighted_risk_parts = [
            (result.get("next_day_cashout_risk_score"), 0.18),
            (result.get("intraday_reversal_risk_score"), 0.14),
            (result.get("single_name_overheat_score"), 0.14),
        ]
        positive_weight = sum(weight for value, weight in weighted_positive_parts if value is not None)
        if positive_weight > 0:
            v2_positive_score = sum(value * weight for value, weight in weighted_positive_parts if value is not None) / positive_weight
            risk_weight = sum(weight for value, weight in weighted_risk_parts if value is not None)
            v2_risk_score = (
                sum(value * weight for value, weight in weighted_risk_parts if value is not None) / risk_weight
                if risk_weight > 0
                else 50.0
            )
            score_v2 = v2_positive_score * 0.78 + (100.0 - v2_risk_score) * 0.22
            if (
                result.get("limit_attention_score") is not None
                and result.get("volume_burst_quality_score") is not None
                and result["limit_attention_score"] >= 85.0
                and result["volume_burst_quality_score"] < 55.0
            ):
                score_v2 -= 8.0
            if result.get("close_strength_score") is not None and result["close_strength_score"] < 45.0:
                score_v2 -= 6.0
            result["short_burst_emotion_score_v2"] = _clamp_score(score_v2)
        else:
            result["short_burst_emotion_score_v2"] = None

        limit_up_count = _safe_float(candidate.get("market_limit_up_count"), None)
        limit_down_count = _safe_float(candidate.get("market_limit_down_count"), None)
        failure_rate = _safe_float(candidate.get("market_limit_up_failure_rate"), None)
        leader_rate = _safe_float(candidate.get("leader_continuation_rate"), None)
        concentration = _safe_float(candidate.get("market_hot_sector_concentration"), None)
        if limit_up_count is not None:
            result["limit_up_breadth_score"] = _clamp_score(limit_up_count / 100.0 * 100.0)
        else:
            result["limit_up_breadth_score"] = _coerce_candidate_score(candidate, "limit_up_breadth_score")
        result["limit_up_failure_risk"] = (
            _clamp_score(failure_rate * 100.0)
            if failure_rate is not None
            else _coerce_candidate_score(candidate, "limit_up_failure_risk")
        )
        result["leader_continuation_score"] = (
            _clamp_score(leader_rate * 100.0)
            if leader_rate is not None
            else _coerce_candidate_score(candidate, "leader_continuation_score")
        )
        result["crowding_heat_score"] = (
            _clamp_score(concentration * 100.0)
            if concentration is not None
            else _coerce_candidate_score(candidate, "crowding_heat_score")
        )
        limit_down_risk = _clamp_score(limit_down_count / 40.0 * 100.0) if limit_down_count is not None else None
        market_parts = [
            (result.get("limit_up_breadth_score"), 0.32),
            (100.0 - result["limit_up_failure_risk"] if result.get("limit_up_failure_risk") is not None else None, 0.24),
            (result.get("leader_continuation_score"), 0.24),
            (100.0 - limit_down_risk if limit_down_risk is not None else None, 0.12),
            (100.0 - result["crowding_heat_score"] if result.get("crowding_heat_score") is not None else None, 0.08),
        ]
        market_weight = sum(weight for value, weight in market_parts if value is not None)
        result["market_short_emotion_score"] = (
            _clamp_score(sum(value * weight for value, weight in market_parts if value is not None) / market_weight)
            if market_weight > 0 else _coerce_candidate_score(candidate, "market_short_emotion_score")
        )
        env_parts = [
            (result.get("market_short_emotion_score"), 0.52),
            (result.get("sector_burst_breadth_score"), 0.28),
            (100.0 - result["crowding_heat_score"] if result.get("crowding_heat_score") is not None else None, 0.20),
        ]
        env_weight = sum(weight for value, weight in env_parts if value is not None)
        result["short_burst_environment_score"] = (
            _clamp_score(sum(value * weight for value, weight in env_parts if value is not None) / env_weight)
            if env_weight > 0 else _coerce_candidate_score(candidate, "short_burst_environment_score")
        )

        news_count = _safe_float(candidate.get("news_count_3d"), None)
        policy_count = _safe_float(candidate.get("policy_catalyst_count"), None)
        earnings_count = _safe_float(candidate.get("earnings_catalyst_count"), None)
        event_age_days = _safe_float(candidate.get("event_age_days"), None)
        continuation_days = _safe_float(candidate.get("event_continuation_days"), None)
        negative_count = _safe_float(candidate.get("negative_news_count_3d"), None)
        rumor_count = _safe_float(candidate.get("rumor_risk_count"), None)
        result["news_heat_score"] = (
            _clamp_score(news_count / 6.0 * 100.0)
            if news_count is not None
            else _coerce_candidate_score(candidate, "news_heat_score")
        )
        result["policy_catalyst_score"] = (
            _clamp_score(policy_count * 35.0)
            if policy_count is not None
            else _coerce_candidate_score(candidate, "policy_catalyst_score")
        )
        result["earnings_catalyst_score"] = (
            _clamp_score(earnings_count * 35.0)
            if earnings_count is not None
            else _coerce_candidate_score(candidate, "earnings_catalyst_score")
        )
        result["event_freshness_score"] = (
            _clamp_score(100.0 - event_age_days * 16.0)
            if event_age_days is not None
            else _coerce_candidate_score(candidate, "event_freshness_score")
        )
        result["event_continuation_score"] = (
            _clamp_score(continuation_days * 28.0)
            if continuation_days is not None
            else _coerce_candidate_score(candidate, "event_continuation_score")
        )
        result["negative_news_risk_score"] = (
            _clamp_score(negative_count * 38.0)
            if negative_count is not None
            else _coerce_candidate_score(candidate, "negative_news_risk_score")
        )
        result["rumor_hype_risk_score"] = (
            _clamp_score(rumor_count * 42.0)
            if rumor_count is not None
            else _coerce_candidate_score(candidate, "rumor_hype_risk_score")
        )
        news_positive_parts = [
            (result.get("short_burst_environment_score"), 0.24),
            (result.get("news_heat_score"), 0.18),
            (result.get("policy_catalyst_score"), 0.12),
            (result.get("earnings_catalyst_score"), 0.10),
            (result.get("event_freshness_score"), 0.14),
            (result.get("event_continuation_score"), 0.12),
            (result.get("short_burst_emotion_score_v2"), 0.10),
        ]
        news_risk_parts = [
            (result.get("limit_up_failure_risk"), 0.10),
            (result.get("crowding_heat_score"), 0.08),
            (result.get("negative_news_risk_score"), 0.12),
            (result.get("rumor_hype_risk_score"), 0.10),
        ]
        positive_weight = sum(weight for value, weight in news_positive_parts if value is not None)
        if positive_weight > 0:
            positive = sum(value * weight for value, weight in news_positive_parts if value is not None) / positive_weight
            risk_weight = sum(weight for value, weight in news_risk_parts if value is not None)
            risk = (
                sum(value * weight for value, weight in news_risk_parts if value is not None) / risk_weight
                if risk_weight > 0 else 45.0
            )
            result["short_burst_news_emotion_score_shadow"] = _clamp_score(positive * 0.76 + (100.0 - risk) * 0.24)
        else:
            result["short_burst_news_emotion_score_shadow"] = None
    except Exception:
        result["short_emotion_heat_score"] = None
        result["sector_burst_breadth_score"] = None
        result["limit_attention_score"] = None
        result["intraday_reversal_risk_score"] = None
        result["close_strength_score"] = None
        result["volume_burst_quality_score"] = None
        result["single_name_overheat_score"] = None
        result["next_day_cashout_risk_score"] = None
        result["short_burst_emotion_score_v1"] = None
        result["short_burst_emotion_score_v2"] = None
        result["market_short_emotion_score"] = None
        result["limit_up_breadth_score"] = None
        result["limit_up_failure_risk"] = None
        result["leader_continuation_score"] = None
        result["short_burst_environment_score"] = None
        result["crowding_heat_score"] = None
        result["news_heat_score"] = None
        result["policy_catalyst_score"] = None
        result["earnings_catalyst_score"] = None
        result["event_freshness_score"] = None
        result["event_continuation_score"] = None
        result["negative_news_risk_score"] = None
        result["rumor_hype_risk_score"] = None
        result["short_burst_news_emotion_score_shadow"] = None

    return result
