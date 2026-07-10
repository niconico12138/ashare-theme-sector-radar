"""
风险拆分模块

将 trade_risk 的 risk_penalty_score 拆分为四个独立维度：
1. hard_risk_penalty: 真正必须扣的硬风险 (ST/退市/流动性/数据缺失)
2. trade_risk_penalty: 短期执行风险 (涨停、冲高回落、超涨)
3. volatility_elasticity_score: 高波动/高弹性特征 (不一定是坏事)
4. drawdown_risk_score: 真实回撤风险 (冲高回落/超涨)

用于 shadow 实验，不替代生产 risk_penalty_score。
新增 risk_quality_tags 提供人类可读的规则触发说明。
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


def _is_st(name: str) -> bool:
    if not name:
        return False
    upper = name.upper()
    return "ST" in upper or "*ST" in upper


def _is_delisted(name: str) -> bool:
    if not name:
        return False
    return any(kw in name for kw in ["退", "退市", "摘牌"])


def _is_non_main_board(code: str) -> bool:
    if not code or not isinstance(code, str):
        return True
    code = code.strip()
    if len(code) != 6 or not code.isdigit():
        return True
    return not code.startswith(("600", "601", "603", "605", "000", "001", "002", "003"))


def decompose_trade_risk(stock: dict) -> dict:
    """Decompose risk_penalty_score into three independent dimensions.

    Args:
        stock: Candidate dict with all scoring fields.

    Returns:
        dict with hard_risk_penalty, volatility_elasticity_score,
        drawdown_risk_score, risk_decomposition_tags, risk_decomposition_breakdown.
    """
    tags: list[str] = []
    breakdown: dict[str, Any] = {}

    name = stock.get("name", "")
    code = stock.get("code", "")
    change_pct = _safe_float(stock.get("change_pct", stock.get("pct_change", 0)))
    amount = _safe_float(stock.get("amount", 0))
    volume = _safe_float(stock.get("volume", 0))
    turnover_rate = _safe_float(stock.get("turnover_rate", 0))
    volume_ratio = _safe_float(stock.get("volume_ratio", 0))
    stock_short_score = _safe_float(stock.get("stock_short_score", 50))
    stock_trend_score = _safe_float(stock.get("stock_trend_score", 50))
    sector_leader_score = _safe_float(stock.get("sector_leader_score", 50))
    decision_score = _safe_float(stock.get("decision_score", 50))
    final_score = _safe_float(stock.get("final_score", 0))
    quant_score = _safe_float(stock.get("quant_score", 0))
    source_pool = stock.get("source_pool", "")
    risk_tags = stock.get("risk_tags", [])
    invalid_reason = stock.get("invalid_reason", "")

    # ================================================================
    # 1. HARD RISK PENALTY (0-50, negative impact)
    #    真正必须扣的硬风险：ST、退市、流动性极差、数据缺失
    # ================================================================
    hard_risk = 0.0

    # ST / Delisted / Non-main-board
    if _is_st(name):
        hard_risk += 50.0
        tags.append("hard_st_stock")
    if _is_delisted(name):
        hard_risk += 50.0
        tags.append("hard_delisted")
    if _is_non_main_board(code):
        hard_risk += 30.0
        tags.append("hard_non_main_board")

    # Invalid reason from trade_risk
    if invalid_reason:
        if invalid_reason in ("st_stock", "delisted_stock"):
            hard_risk += 50.0
        elif invalid_reason == "non_main_board":
            hard_risk += 30.0
        tags.append(f"hard_invalid_{invalid_reason}")

    # Data quality risk (missing fields)
    has_amount = amount > 0
    has_change = change_pct != 0
    has_quant = quant_score > 0
    has_final = final_score > 0
    data_missing = sum(1 for v in [has_amount, has_change, has_quant, has_final] if not v)
    if data_missing >= 3:
        hard_risk += 12.0
        tags.append("hard_data_quality_risk")
    elif data_missing >= 2:
        hard_risk += 6.0
        tags.append("hard_partial_data_risk")

    # Low liquidity (real trading constraint)
    if has_amount:
        if amount < 5_000_000:
            hard_risk += 15.0
            tags.append("hard_low_liquidity")
        elif amount < 20_000_000:
            hard_risk += 5.0
            tags.append("hard_moderate_liquidity_risk")

    if turnover_rate > 0 and turnover_rate < 0.5:
        hard_risk += 3.0
        tags.append("hard_low_turnover")

    # Sector laggard (confirmed underperformer)
    sector_role = stock.get("sector_role", "unknown")
    if sector_role == "laggard":
        hard_risk += 10.0
        tags.append("hard_sector_laggard")

    hard_risk = min(50.0, hard_risk)
    breakdown["hard_risk_penalty"] = round(hard_risk, 2)

    # ================================================================
    # 2. VOLATILITY ELASTICITY SCORE (0-100, NOT a penalty)
    #    高波动/高弹性特征，这些股票弹性大，不一定负面
    # ================================================================
    elasticity = 50.0  # neutral baseline

    # High change_pct → high elasticity (positive)
    if change_pct > 7:
        elasticity += 20.0
        tags.append("elast_high_change")
    elif change_pct > 4:
        elasticity += 12.0
        tags.append("elast_moderate_change")
    elif change_pct > 2:
        elasticity += 6.0

    # High volume_ratio → high activity
    if volume_ratio > 4:
        elasticity += 15.0
        tags.append("elast_high_volume_ratio")
    elif volume_ratio > 2:
        elasticity += 8.0
        tags.append("elast_moderate_volume_ratio")
    elif volume_ratio > 1.5:
        elasticity += 4.0

    # High turnover → active trading
    if turnover_rate > 5:
        elasticity += 10.0
        tags.append("elast_high_turnover")
    elif turnover_rate > 3:
        elasticity += 5.0

    # High short score → momentum
    if stock_short_score > 75:
        elasticity += 8.0
        tags.append("elast_high_short_score")
    elif stock_short_score > 60:
        elasticity += 4.0

    # Burst pool → short-term explosive
    if source_pool == "burst":
        elasticity += 10.0
        tags.append("elast_burst_pool")
    elif source_pool == "both":
        elasticity += 5.0

    elasticity = max(0.0, min(100.0, elasticity))
    breakdown["volatility_elasticity_score"] = round(elasticity, 2)

    # ================================================================
    # 3. DRAWDOWN RISK SCORE (0-50, negative impact)
    #    真实回撤风险：冲高回落、超涨、趋势走弱
    # ================================================================
    drawdown_risk = 0.0

    # Near limit up (涨停) → high next-day drawdown risk
    if change_pct > 9.5:
        drawdown_risk += 15.0
        tags.append("drawdown_near_limit_up")
    elif change_pct > 7:
        drawdown_risk += 10.0
        tags.append("drawdown_overheated")

    # Volume stagnation (放量滞涨) → distribution signal
    if volume_ratio > 2 and 0 <= change_pct <= 0.5:
        drawdown_risk += 12.0
        tags.append("drawdown_volume_stagnation")

    # Short score overheated
    if stock_short_score > 85:
        drawdown_risk += 10.0
        tags.append("drawdown_short_overheated")
    elif stock_short_score > 75:
        drawdown_risk += 5.0
        tags.append("drawdown_short_elevated")

    # Weak trend with high short score → pullback risk
    if stock_short_score > 60 and stock_trend_score < 40:
        drawdown_risk += 8.0
        tags.append("drawdown_trend_short_divergence")

    # High decision score but weak fundamentals → overvaluation risk
    if decision_score > 70 and final_score < 50:
        drawdown_risk += 5.0
        tags.append("drawdown_score_fundamental_divergence")

    # Check risk_tags from original trade_risk for drawdown signals
    drawdown_related_tags = {"overheated", "running_hot", "near_limit_up",
                             "volume_stagnation", "high_volatility"}
    for rt in risk_tags:
        if rt in drawdown_related_tags:
            drawdown_risk += 3.0
            if f"drawdown_from_{rt}" not in tags:
                tags.append(f"drawdown_from_{rt}")

    drawdown_risk = min(50.0, drawdown_risk)
    breakdown["drawdown_risk_score"] = round(drawdown_risk, 2)

    # ================================================================
    # 4. TRADE RISK PENALTY (0-40, negative impact)
    #    短期执行风险：涨停、冲高回落、超涨、连续强势但收盘位置差
    # ================================================================
    trade_risk = 0.0

    # Near limit-up → high next-day reversal risk
    if change_pct > 9.5:
        trade_risk += 15.0
        tags.append("trade_near_limit_up")
    elif change_pct > 8:
        trade_risk += 10.0
        tags.append("trade_strong_change")

    # High rejection (high - close large relative to range) → upper shadow risk
    # Approximate: if short_score is very high but trend is weak, likely rejection
    if stock_short_score > 70 and stock_trend_score < 40:
        trade_risk += 8.0
        tags.append("trade_high_rejection")

    # Overextended above short moving average
    if stock_short_score > 80 and stock_trend_score < 50:
        trade_risk += 5.0
        tags.append("trade_overextended")

    # Consecutive strong days with poor close position
    if change_pct > 3 and stock_short_score > 70 and stock_trend_score < 45:
        trade_risk += 5.0
        tags.append("trade_consecutive_poor_close")

    # Abnormal turnover without close strength
    if volume_ratio > 3 and stock_short_score < 50:
        trade_risk += 5.0
        tags.append("trade_abnormal_turnover_weak_close")

    # Sector laggard with momentum → likely fake breakout
    if sector_role == "laggard" and stock_short_score > 60:
        trade_risk += 3.0
        tags.append("trade_laggard_momentum")

    # Original risk_tags that indicate trade risk
    trade_related_tags = {"near_limit_up", "overheated", "running_hot",
                          "high_rejection", "volume_stagnation"}
    for rt in risk_tags:
        if rt in trade_related_tags:
            trade_risk += 2.0
            if f"trade_from_{rt}" not in tags:
                tags.append(f"trade_from_{rt}")

    trade_risk = min(40.0, trade_risk)
    breakdown["trade_risk_penalty"] = round(trade_risk, 2)

    # ================================================================
    # RISK QUALITY TAGS (human-readable, category-prefixed)
    # ================================================================
    quality_tags: list[str] = []
    for t in tags:
        if t.startswith("hard_"):
            quality_tags.append(f"hard:{t[5:]}")
        elif t.startswith("trade_"):
            quality_tags.append(f"trade:{t[6:]}")
        elif t.startswith("elast_"):
            quality_tags.append(f"elast:{t[6:]}")
        elif t.startswith("drawdown_"):
            quality_tags.append(f"drawdown:{t[9:]}")
        else:
            quality_tags.append(t)

    # ================================================================
    # Summary breakdown
    # ================================================================
    breakdown["net_risk_impact"] = round(-hard_risk - trade_risk - drawdown_risk, 2)
    breakdown["elasticity_bonus"] = round(elasticity * 0.1, 2)  # how much elasticity helps

    return {
        "hard_risk_penalty": round(hard_risk, 2),
        "trade_risk_penalty": round(trade_risk, 2),
        "volatility_elasticity_score": round(elasticity, 2),
        "drawdown_risk_score": round(drawdown_risk, 2),
        "risk_quality_tags": quality_tags,
        "risk_decomposition_tags": tags,
        "risk_decomposition_breakdown": breakdown,
    }
