"""
Stock Profile 模块

为候选股生成个股画像，包括趋势、动量、成交量、波动率、风险、板块支持等状态。
不改变 final_score、不改变排序、不加入交易指令。
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


def _get_factor_score(candidate: dict, factor_id: str) -> float | None:
    """从 factor_snapshot 中获取因子分数。"""
    factor_snapshot = candidate.get("factor_snapshot")
    if factor_snapshot is None:
        factor_snapshot = {}
    factors = factor_snapshot.get("factors", [])

    for f in factors:
        if f.get("factor_id") == factor_id:
            quality = f.get("quality", "missing")
            if quality == "missing":
                return None
            return _safe_float(f.get("score"))

    return None


def _get_factor_raw_value(candidate: dict, factor_id: str) -> float | None:
    """从 factor_snapshot 中获取因子原始值。"""
    factor_snapshot = candidate.get("factor_snapshot")
    if factor_snapshot is None:
        factor_snapshot = {}
    factors = factor_snapshot.get("factors", [])

    for f in factors:
        if f.get("factor_id") == factor_id:
            quality = f.get("quality", "missing")
            if quality == "missing":
                return None
            raw_value = f.get("raw_value")
            if raw_value is not None:
                return _safe_float(raw_value)
            # 如果 raw_value 缺失，返回 score 作为 fallback
            return _safe_float(f.get("score"))

    return None


def _get_field(candidate: dict, *keys) -> float | None:
    """从 candidate 中获取字段值。"""
    for key in keys:
        value = candidate.get(key)
        if value is not None:
            return _safe_float(value)
    return None


def build_stock_profile(candidate: dict) -> dict:
    """为候选股生成个股画像。

    Args:
        candidate: 候选股字典

    Returns:
        个股画像字典
    """
    # 趋势状态
    stock_trend_score = _get_field(candidate, "stock_trend_score")
    ma20_slope = _get_factor_score(candidate, "ma20_slope_5")
    near_high_250 = _get_factor_score(candidate, "near_high_250")
    breakout_distance = _get_factor_score(candidate, "breakout_distance_20")

    # 如果 factor_snapshot 中没有，尝试从 candidate 直接读取
    if breakout_distance is None:
        breakout_distance = _get_field(candidate, "breakout_distance_20")

    if stock_trend_score is not None and stock_trend_score >= 70:
        trend_state = "uptrend"
    elif ma20_slope is not None and ma20_slope >= 65:
        trend_state = "uptrend"
    elif stock_trend_score is not None and stock_trend_score >= 55:
        trend_state = "repair"
    elif near_high_250 is not None and near_high_250 >= 60:
        trend_state = "repair"
    elif breakout_distance is not None and breakout_distance <= 5:
        trend_state = "repair"
    elif stock_trend_score is not None and stock_trend_score < 45:
        trend_state = "weak"
    else:
        trend_state = "unknown"

    # 动量状态
    stock_short_score = _get_field(candidate, "stock_short_score_v2")
    sector_burst_score = _get_field(candidate, "sector_burst_score")

    if stock_short_score is not None and stock_short_score >= 70:
        momentum_state = "strong"
    elif sector_burst_score is not None and sector_burst_score >= 70:
        momentum_state = "strong"
    elif stock_short_score is not None and stock_short_score >= 50:
        momentum_state = "neutral"
    elif stock_short_score is not None and stock_short_score < 45:
        momentum_state = "weak"
    else:
        momentum_state = "unknown"

    # 成交量状态
    amount_ratio = _get_factor_score(candidate, "amount_ratio_20")

    if amount_ratio is not None and amount_ratio >= 65:
        volume_state = "confirmed"
    elif amount_ratio is not None and amount_ratio <= 40:
        volume_state = "dry_up"
    elif amount_ratio is not None:
        volume_state = "neutral"
    else:
        volume_state = "unknown"

    # 波动率状态
    contraction_score = _get_factor_score(candidate, "contraction_score")

    if contraction_score is not None and contraction_score >= 65:
        volatility_state = "contracting"
    elif contraction_score is not None and contraction_score <= 40:
        volatility_state = "expanding"
    elif contraction_score is not None:
        volatility_state = "normal"
    else:
        volatility_state = "unknown"

    # 风险状态
    drawdown_risk = _get_factor_score(candidate, "drawdown_risk_score")
    risk_penalty = _get_factor_score(candidate, "risk_penalty_score")
    chasing_risk = _get_factor_score(candidate, "chasing_risk_score")
    drawdown_depth = _get_factor_score(candidate, "drawdown_depth_20")

    # 如果 factor_snapshot 中没有，尝试从 candidate 直接读取
    if chasing_risk is None:
        chasing_risk = _get_field(candidate, "chasing_risk_score")
    if drawdown_depth is None:
        drawdown_depth = _get_field(candidate, "drawdown_depth_20")

    # 优先使用新因子
    if chasing_risk is not None and chasing_risk >= 75:
        risk_state = "high"
    elif drawdown_depth is not None and drawdown_depth > 30:
        risk_state = "high"
    elif drawdown_risk is not None and risk_penalty is not None:
        if drawdown_risk <= 35 and risk_penalty <= 35:
            risk_state = "low"
        elif drawdown_risk >= 70 or risk_penalty >= 70:
            risk_state = "high"
        else:
            risk_state = "medium"
    elif drawdown_risk is not None or risk_penalty is not None:
        risk_state = "medium"
    elif chasing_risk is not None and chasing_risk >= 60:
        risk_state = "medium"
    else:
        risk_state = "unknown"

    # 板块支持
    sector_support_score = _get_factor_score(candidate, "sector_support_score")
    sector_trend = _get_field(candidate, "sector_trend_score")
    sector_burst = _get_field(candidate, "sector_burst_score")

    # 如果 factor_snapshot 中没有，尝试从 candidate 直接读取
    if sector_support_score is None:
        sector_support_score = _get_field(candidate, "sector_support_score")

    # 如果 sector_support_score 仍为 0 或 None，尝试从 sector_trend_score 和 sector_burst_score 计算
    # 同时检查 trend_score 和 burst_score 作为替代字段
    if sector_support_score is None or sector_support_score == 0:
        # 尝试多种字段名
        trend_val = 0
        burst_val = 0

        if sector_trend is not None and _safe_float(sector_trend) > 0:
            trend_val = _safe_float(sector_trend)
        else:
            alt_trend = _get_field(candidate, "trend_score")
            if alt_trend is not None and _safe_float(alt_trend) > 0:
                trend_val = _safe_float(alt_trend)

        if sector_burst is not None and _safe_float(sector_burst) > 0:
            burst_val = _safe_float(sector_burst)
        else:
            alt_burst = _get_field(candidate, "burst_score")
            if alt_burst is not None and _safe_float(alt_burst) > 0:
                burst_val = _safe_float(alt_burst)

        if trend_val > 0 and burst_val > 0:
            sector_support_score = trend_val * 0.7 + burst_val * 0.3
        elif trend_val > 0:
            sector_support_score = trend_val
        elif burst_val > 0:
            sector_support_score = burst_val

    # 优先使用 sector_support_score（历史验证显示该因子有用）
    if sector_support_score is not None and sector_support_score > 0:
        if sector_support_score >= 65:
            sector_support = "strong"
        elif sector_support_score >= 50:
            sector_support = "neutral"
        elif sector_support_score < 50:
            sector_support = "weak"
        else:
            sector_support = "unknown"
    elif sector_trend is not None:
        if sector_trend >= 65:
            sector_support = "strong"
        elif sector_trend < 45:
            sector_support = "weak"
        else:
            sector_support = "neutral"
    else:
        sector_support = "unknown"

    # V2 信号
    selection_bucket = candidate.get("selection_bucket", "")
    signal_type = candidate.get("signal_type", "")
    v2_score = _get_field(candidate, "v2_score", "factor_composite_shadow_score_v2")

    if selection_bucket == "v2_opportunity" or signal_type == "low_final_high_v2":
        v2_signal = "opportunity"
    elif selection_bucket == "core_watch" and v2_score is not None and v2_score >= 50:
        v2_signal = "confirmed"
    elif selection_bucket == "divergence_review" or signal_type == "high_final_low_v2":
        v2_signal = "divergent"
    else:
        v2_signal = "none"

    # ============================================================
    # 新增 profile 字段 (第三十二阶段: bars 因子)
    # ============================================================

    # 流动性状态 - 使用 raw_value 分桶
    liquidity_score_raw = _get_factor_raw_value(candidate, "liquidity_score")
    liquidity_score_score = _get_factor_score(candidate, "liquidity_score")

    # 优先使用 raw_value，如果缺失则使用 score
    liquidity_score = liquidity_score_raw if liquidity_score_raw is not None else liquidity_score_score

    if liquidity_score is not None and liquidity_score >= 75:
        liquidity_state = "strong"
    elif liquidity_score is not None and liquidity_score >= 40:
        liquidity_state = "normal"
    elif liquidity_score is not None and liquidity_score < 40:
        liquidity_state = "weak"
    else:
        liquidity_state = "unknown"

    # 过热状态 - 使用 raw_value 分桶
    chasing_risk_raw = _get_factor_raw_value(candidate, "chasing_risk_score")
    chasing_risk_score = _get_factor_score(candidate, "chasing_risk_score")

    # 优先使用 raw_value，如果缺失则使用 score
    chasing_risk = chasing_risk_raw if chasing_risk_raw is not None else chasing_risk_score

    if chasing_risk is not None and chasing_risk >= 70:
        overheat_state = "high"
    elif chasing_risk is not None and chasing_risk >= 50:
        overheat_state = "normal"
    elif chasing_risk is not None:
        overheat_state = "low"
    else:
        overheat_state = "unknown"

    # 回撤状态 - 使用 raw_value 分桶
    drawdown_depth_raw = _get_factor_raw_value(candidate, "drawdown_depth_20")
    drawdown_depth_score = _get_factor_score(candidate, "drawdown_depth_20")

    # 优先使用 raw_value，如果缺失则使用 score
    drawdown_depth = drawdown_depth_raw if drawdown_depth_raw is not None else drawdown_depth_score

    if drawdown_depth is not None and drawdown_depth > 15:
        drawdown_state = "deep"
    elif drawdown_depth is not None and drawdown_depth <= 5:
        drawdown_state = "healthy"
    elif drawdown_depth is not None:
        drawdown_state = "normal"
    else:
        drawdown_state = "unknown"

    # 突破结构 - 使用 raw_value 分桶
    breakout_distance_raw = _get_factor_raw_value(candidate, "breakout_distance_20")
    breakout_distance_score = _get_factor_score(candidate, "breakout_distance_20")

    # 优先使用 raw_value，如果缺失则使用 score
    breakout_distance = breakout_distance_raw if breakout_distance_raw is not None else breakout_distance_score

    if breakout_distance is not None and breakout_distance <= 5:
        breakout_structure = "near"
    elif breakout_distance is not None and breakout_distance <= 15:
        breakout_structure = "neutral"
    elif breakout_distance is not None and breakout_distance > 15:
        breakout_structure = "far"
    else:
        breakout_structure = "unknown"

    # 更新 risk_state（如果需要）
    if drawdown_state == "deep" and risk_state in ("unknown", "low"):
        risk_state = "medium"
    if liquidity_state == "weak" and risk_state in ("unknown", "low"):
        risk_state = "medium"
    if overheat_state == "high" and risk_state in ("unknown", "low"):
        risk_state = "medium"

    return {
        "trend_state": trend_state,
        "momentum_state": momentum_state,
        "volume_state": volume_state,
        "volatility_state": volatility_state,
        "risk_state": risk_state,
        "sector_support": sector_support,
        "v2_signal": v2_signal,
        "liquidity_state": liquidity_state,
        "overheat_state": overheat_state,
        "drawdown_state": drawdown_state,
        "breakout_structure": breakout_structure,
    }
