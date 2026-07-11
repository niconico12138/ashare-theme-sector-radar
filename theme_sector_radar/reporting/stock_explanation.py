"""
Stock Explanation 模块

为候选股生成入池解释，包括机会类型、原因码、失效标志、历史提示等。
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


def _get_field(candidate: dict, *keys) -> float | None:
    """从 candidate 中获取字段值。"""
    for key in keys:
        value = candidate.get(key)
        if value is not None:
            return _safe_float(value)
    return None


def build_stock_explanation(candidate: dict, profile: dict | None = None) -> dict:
    """为候选股生成入池解释。

    Args:
        candidate: 候选股字典
        profile: 个股画像（可选，如果为 None 则不使用）

    Returns:
        入池解释字典
    """
    selection_bucket = candidate.get("selection_bucket", "")
    signal_type = candidate.get("signal_type", "")
    source_pool = candidate.get("source_pool", "")
    data_quality = candidate.get("data_quality", "ok")

    # 获取 profile 字段
    if profile:
        trend_state = profile.get("trend_state", "unknown")
        momentum_state = profile.get("momentum_state", "unknown")
        volume_state = profile.get("volume_state", "unknown")
        volatility_state = profile.get("volatility_state", "unknown")
        risk_state = profile.get("risk_state", "unknown")
        sector_support = profile.get("sector_support", "unknown")
        v2_signal = profile.get("v2_signal", "none")
    else:
        trend_state = "unknown"
        momentum_state = "unknown"
        volume_state = "unknown"
        volatility_state = "unknown"
        risk_state = "unknown"
        sector_support = "unknown"
        v2_signal = "none"

    # ============================================================
    # opportunity_type
    # ============================================================
    if selection_bucket == "blocked":
        opportunity_type = "blocked"
    elif selection_bucket == "v2_opportunity":
        opportunity_type = "v2_recovery"
    elif selection_bucket == "divergence_review":
        opportunity_type = "divergence_review"
    elif source_pool == "burst_top" or momentum_state == "strong":
        opportunity_type = "short_burst"
    elif selection_bucket == "core_watch" and v2_signal == "confirmed":
        opportunity_type = "consensus_confirmed"
    elif selection_bucket == "core_watch":
        opportunity_type = "trend_follow"
    else:
        opportunity_type = "unknown"

    # ============================================================
    # reason_codes
    # ============================================================
    reason_codes = []

    if selection_bucket == "v2_opportunity":
        reason_codes.append("v2_opportunity")
    if selection_bucket == "core_watch":
        reason_codes.append("core_watch")
    if selection_bucket == "divergence_review":
        reason_codes.append("score_divergence")
    if trend_state in ("uptrend", "repair"):
        reason_codes.append(f"trend_{trend_state}")
    if momentum_state == "strong":
        reason_codes.append("short_momentum_strong")
    if volume_state == "confirmed":
        reason_codes.append("volume_confirmed")
    if volatility_state == "contracting":
        reason_codes.append("volatility_contracting")
    if risk_state == "low":
        reason_codes.append("low_risk_profile")
    if sector_support == "strong":
        reason_codes.append("sector_supported")
    if v2_signal == "opportunity":
        reason_codes.append("v2_independent_signal")
    if risk_state == "high":
        reason_codes.append("risk_high")
    if sector_support == "weak":
        reason_codes.append("sector_weak")

    # 新增 reason_codes (第二十一阶段-B & 第三十二阶段: bars 因子)
    liquidity_score = _get_field(candidate, "liquidity_score")
    if liquidity_score is not None:
        if liquidity_score >= 70:
            reason_codes.append("liquidity_strong")
        elif liquidity_score >= 40:
            reason_codes.append("liquidity_normal")
        elif liquidity_score < 40:
            reason_codes.append("liquidity_weak")

    chasing_risk = _get_field(candidate, "chasing_risk_score")
    if chasing_risk is not None:
        if chasing_risk >= 75:
            reason_codes.append("overheat_risk_high")
        elif chasing_risk >= 60:
            reason_codes.append("overheat_risk_watch")

    drawdown_depth = _get_field(candidate, "drawdown_depth_20")
    if drawdown_depth is not None:
        if drawdown_depth > 35:
            reason_codes.append("deep_drawdown_risk")
        elif 5 <= drawdown_depth <= 20:
            reason_codes.append("healthy_drawdown")

    breakout_distance = _get_field(candidate, "breakout_distance_20")
    if breakout_distance is not None:
        if breakout_distance <= 5:
            reason_codes.append("near_breakout_structure")
        elif breakout_distance <= 15:
            reason_codes.append("breakout_structure_watch")
        else:
            reason_codes.append("far_from_breakout")

    sector_support_score = _get_field(candidate, "sector_support_score")
    if sector_support_score is not None:
        if sector_support_score >= 65:
            reason_codes.append("sector_supported_from_score")
            reason_codes.append("sector_support_confirmed")
        elif sector_support_score >= 50:
            reason_codes.append("sector_support_neutral")
        elif sector_support_score < 50:
            reason_codes.append("sector_support_weak")

    # ============================================================
    # invalidation_flags
    # ============================================================
    invalidation_flags = []

    if trend_state in ("uptrend", "repair"):
        invalidation_flags.append("trend_score_deteriorates")
    if risk_state in ("low", "medium"):
        invalidation_flags.append("risk_score_rises")
    if sector_support == "strong":
        invalidation_flags.append("sector_support_lost")
    if volume_state == "confirmed":
        invalidation_flags.append("volume_confirmation_lost")
    if v2_signal in ("opportunity", "confirmed"):
        invalidation_flags.append("v2_signal_fades")
    if data_quality != "ok":
        invalidation_flags.append("data_quality_deteriorates")
    if selection_bucket == "blocked":
        invalidation_flags.append("hard_blocker_present")

    # 新增 invalidation_flags (第二十一阶段-B & 第三十二阶段: bars 因子)
    if liquidity_score is not None and liquidity_score < 40:
        invalidation_flags.append("liquidity_condition_weak")
    if chasing_risk is not None and chasing_risk >= 75:
        invalidation_flags.append("overheat_risk_present")
    if drawdown_depth is not None and drawdown_depth > 35:
        invalidation_flags.append("drawdown_too_deep")

    # 新增 invalidation_flags (第二十四阶段: sector_support_score)
    if sector_support_score is not None and sector_support_score < 50:
        invalidation_flags.append("sector_support_weak_present")

    # 新增 invalidation_flags (第三十二阶段: bars 因子)
    breakout_distance = _get_field(candidate, "breakout_distance_20")
    if breakout_distance is not None and breakout_distance > 15 and opportunity_type == "trend_follow":
        invalidation_flags.append("breakout_structure_not_ready")

    # ============================================================
    # historical_hint
    # ============================================================
    if opportunity_type == "v2_recovery" or signal_type == "low_final_high_v2":
        historical_hint = {
            "matched_pattern": "low_final_high_v2",
            "best_horizon": "10d",
            "historical_5d_mean": 2.5995,
            "historical_10d_mean": 5.6829,
            "confidence": "medium",
        }
    else:
        historical_hint = {
            "matched_pattern": "none",
            "best_horizon": "unknown",
            "historical_5d_mean": None,
            "historical_10d_mean": None,
            "confidence": "unknown",
        }

    # ============================================================
    # explanation_text
    # ============================================================
    explanation_texts = {
        "v2_recovery": "final 不高但 v2 较强，属于独立机会观察；历史同类样本偏 5d/10d 观察。",
        "trend_follow": "主评分较强，趋势画像支持，作为核心观察样本。",
        "consensus_confirmed": "主评分与 v2 共振，趋势画像支持，作为核心观察样本。",
        "short_burst": "短线动量较强，适合短周期观察。",
        "divergence_review": "主评分与 v2 出现分歧，需要人工复核信号一致性。",
        "blocked": "存在关键数据或风险阻断，暂不纳入精简观察池。",
        "unknown": "信息不足，暂无法分类。",
    }

    explanation_text = explanation_texts.get(opportunity_type, "信息不足，暂无法分类。")

    return {
        "opportunity_type": opportunity_type,
        "reason_codes": reason_codes,
        "invalidation_flags": invalidation_flags,
        "historical_hint": historical_hint,
        "explanation_text": explanation_text,
    }
