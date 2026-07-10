"""
交易化风险模块

评估个股的交易风险，输出 risk_penalty_score、risk_tags、trade_eligibility。
仅输出风险分类，不给出买卖建议。
分层要求: focus / watch / backup / avoid / invalid 至少输出3种。
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
    keywords = ["退", "退市", "摘牌"]
    return any(kw in name for kw in keywords)


def _is_non_main_board(code: str) -> bool:
    """Return True if code is NOT on main board (600/601/603/605/000/001/002/003)."""
    if not code or not isinstance(code, str):
        return True
    code = code.strip()
    if len(code) != 6 or not code.isdigit():
        return True
    main_prefixes = ("600", "601", "603", "605", "000", "001", "002", "003")
    return not code.startswith(main_prefixes)


def compute_trade_risk(stock: dict) -> dict:
    """Compute trade risk assessment for a stock.

    Args:
        stock: Stock dict with fields like name, code, change_pct, amount,
               volume, turnover_rate, volume_ratio, sector_role,
               stock_short_score, stock_trend_score, decision_score,
               sector_leader_score, source_pool, etc.

    Returns:
        dict with risk_penalty_score (0-50), risk_tags, trade_eligibility, invalid_reason.
    """
    tags: list[str] = []
    penalty = 0.0
    invalid_reason = ""
    eligibility = "focus"

    name = stock.get("name", "")
    code = stock.get("code", "")

    change_pct = _safe_float(stock.get("change_pct", stock.get("pct_change", 0)))
    amount = _safe_float(stock.get("amount", 0))
    volume = _safe_float(stock.get("volume", 0))
    turnover_rate = _safe_float(stock.get("turnover_rate", 0))
    volume_ratio = _safe_float(stock.get("volume_ratio", 0))
    sector_role = stock.get("sector_role", "unknown")
    stock_short_score = _safe_float(stock.get("stock_short_score", 50))
    stock_trend_score = _safe_float(stock.get("stock_trend_score", 50))
    decision_score = _safe_float(stock.get("decision_score", 50))
    final_score = _safe_float(stock.get("final_score", 0))
    quant_score = _safe_float(stock.get("quant_score", 0))
    sector_leader_score = _safe_float(stock.get("sector_leader_score", 50))
    source_pool = stock.get("source_pool", "")
    burst_score = _safe_float(stock.get("burst_score", stock.get("sector_burst_score", 0)))

    # === Rule 1: ST / Delisted / Non-main-board → invalid ===
    if _is_st(name):
        eligibility = "invalid"
        invalid_reason = "st_stock"
        tags.append("st_stock")
        return _build_result(penalty, tags, eligibility, invalid_reason)

    if _is_delisted(name):
        eligibility = "invalid"
        invalid_reason = "delisted_stock"
        tags.append("delisted_stock")
        return _build_result(penalty, tags, eligibility, invalid_reason)

    if _is_non_main_board(code):
        eligibility = "invalid"
        invalid_reason = "non_main_board"
        tags.append("non_main_board")
        return _build_result(penalty, tags, eligibility, invalid_reason)

    # === Rule 2: Data quality risk (missing key fields) ===
    has_amount = amount > 0
    has_change = change_pct != 0
    has_quant = quant_score > 0
    has_final = final_score > 0

    data_missing_count = sum(1 for v in [has_amount, has_change, has_quant, has_final] if not v)
    if data_missing_count >= 3:
        penalty += 6.0
        tags.append("data_quality_risk")
    elif data_missing_count >= 2:
        penalty += 3.0
        tags.append("partial_data_risk")

    # === Rule 3: Low liquidity ===
    if has_amount:
        if amount < 5_000_000:
            penalty += 15.0
            tags.append("low_liquidity")
        elif amount < 20_000_000:
            penalty += 8.0
            tags.append("moderate_liquidity_risk")

    if turnover_rate > 0 and turnover_rate < 0.5:
        penalty += 5.0
        tags.append("low_turnover")

    # === Rule 4: Overheated (涨幅过热) ===
    if change_pct > 9.5:
        penalty += 15.0
        tags.append("near_limit_up")
    elif change_pct > 7:
        penalty += 10.0
        tags.append("overheated")
    elif change_pct > 5:
        penalty += 5.0
        tags.append("running_hot")

    # === Rule 5: Volume stagnation (放量滞涨) ===
    if volume_ratio > 2 and 0 <= change_pct <= 0.5:
        penalty += 10.0
        tags.append("volume_stagnation")

    # === Rule 6: High volatility ===
    if volume_ratio > 4:
        penalty += 5.0
        tags.append("high_volatility")

    # === Rule 7: Sector position risk (stronger penalties) ===
    if sector_role == "laggard":
        penalty += 15.0
        tags.append("sector_laggard_risk")
    elif sector_role == "follower":
        penalty += 10.0
        tags.append("follower_risk")
    elif sector_role == "unknown":
        penalty += 3.0
        tags.append("unknown_sector_role")

    # === Rule 8: Low sector leader score ===
    if sector_leader_score < 20:
        penalty += 10.0
        tags.append("very_low_leader_score")
    elif sector_leader_score < 35:
        penalty += 6.0
        tags.append("low_leader_score")

    # === Rule 9: Weak individual scores ===
    if stock_short_score < 40:
        penalty += 8.0
        tags.append("weak_short_score")
    elif stock_short_score < 50:
        penalty += 3.0
        tags.append("below_avg_short_score")

    if stock_trend_score < 35:
        penalty += 8.0
        tags.append("weak_trend_score")
    elif stock_trend_score < 45:
        penalty += 3.0
        tags.append("below_avg_trend_score")

    # === Rule 10: Weak decision score ===
    if decision_score < 25:
        penalty += 10.0
        tags.append("very_low_decision_score")
    elif decision_score < 35:
        penalty += 6.0
        tags.append("low_decision_score")
    elif decision_score < 45:
        penalty += 2.0
        tags.append("moderate_decision_score")

    # === Rule 11: Trend pool with zero burst (weak short-term signal) ===
    if source_pool == "trend" and burst_score <= 0 and stock_short_score < 45:
        penalty += 4.0
        tags.append("trend_pool_weak_burst")

    # === Rule 12: Short score overheated ===
    if stock_short_score > 85:
        penalty += 10.0
        tags.append("short_score_overheated")
    elif stock_short_score > 75:
        penalty += 5.0

    # === Determine final eligibility ===
    penalty = min(50.0, penalty)

    if penalty >= 25:
        eligibility = "avoid"
    elif penalty >= 15:
        eligibility = "backup"
    elif penalty >= 8:
        eligibility = "watch"
    else:
        # For focus: require strong scores
        has_good_score = (
            (stock_short_score >= 50 and stock_trend_score >= 50)
            or decision_score >= 50
            or sector_leader_score >= 60
        )
        if has_good_score:
            eligibility = "focus"
        else:
            eligibility = "watch"

    return _build_result(penalty, tags, eligibility, invalid_reason)


def _build_result(
    penalty: float,
    tags: list[str],
    eligibility: str,
    invalid_reason: str,
) -> dict:
    return {
        "risk_penalty_score": round(penalty, 2),
        "risk_tags": tags,
        "trade_eligibility": eligibility,
        "invalid_reason": invalid_reason,
    }
