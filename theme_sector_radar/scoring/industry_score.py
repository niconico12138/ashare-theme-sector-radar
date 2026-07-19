"""
行业板块评分

行业板块总分 100 分:
- 趋势强度: 25分
- 资金流: 25分
- 板块宽度: 20分
- 持续性: 15分
- 市场适配: 10分
- 数据质量: 5分
"""

import math
from typing import Any, Dict, List, Optional

from ..config import get_config
from ..models import SectorSnapshot


def _clip(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _wealth_path(recent_returns: List[float]) -> List[float]:
    wealth = 1.0
    path = [wealth]
    for daily_return in recent_returns:
        wealth *= 1.0 + float(daily_return) / 100.0
        path.append(wealth)
    return path


def _positive_trend_fit(recent_returns: List[float]) -> float:
    path = _wealth_path(recent_returns)
    values = [math.log(max(value, 1e-12)) for value in path]
    count = len(values)
    if count < 2:
        return 0.0
    x_mean = (count - 1) / 2.0
    y_mean = sum(values) / count
    covariance = sum(
        (index - x_mean) * (value - y_mean)
        for index, value in enumerate(values)
    )
    x_variance = sum((index - x_mean) ** 2 for index in range(count))
    if x_variance <= 0:
        return 0.0
    slope = covariance / x_variance
    if slope <= 0:
        return 0.0
    fitted = [y_mean + slope * (index - x_mean) for index in range(count)]
    total_variance = sum((value - y_mean) ** 2 for value in values)
    if total_variance <= 0:
        return 0.0
    residual = sum((value - estimate) ** 2 for value, estimate in zip(values, fitted))
    return _clip(1.0 - residual / total_variance)


def _continuous_breakout_quality(recent_returns: List[float]) -> float:
    path = _wealth_path(recent_returns[-20:])
    if len(path) < 21:
        return 0.0
    prior_high = max(path[:-1])
    distance_pct = (path[-1] / prior_high - 1.0) * 100.0
    return _clip((distance_pct + 2.0) / 4.0)


def calculate_trend_strength_score(
    snapshot: SectorSnapshot,
    trend_features: Optional[Dict[str, Any]] = None,
) -> float:
    """
    计算趋势强度得分 (0-25)

    使用 5/10/20 日横截面相对强度、20 日正向趋势拟合度和突破质量。
    历史不足的组件不计分，避免把单日脉冲当作趋势。
    """
    features = trend_features or {}
    recent_returns = [float(value) for value in features.get("recent_returns", [])]
    percentiles = features.get("relative_strength_percentiles", {})
    score = 0.0
    for window, weight in ((5, 7.0), (10, 7.0), (20, 5.0)):
        if len(recent_returns) >= window and window in percentiles:
            score += _clip(float(percentiles[window])) * weight

    if len(recent_returns) >= 20:
        score += _positive_trend_fit(recent_returns[-20:]) * 3.0
        score += _continuous_breakout_quality(recent_returns[-20:]) * 3.0

    return round(min(score, 25.0), 2)


def calculate_capital_flow_score(snapshot: SectorSnapshot) -> float:
    """
    计算资金流得分 (0-25)

    考虑因素:
    - 主力净流入
    - 净流入占成交额比例
    """
    score = 0.0

    # 主力净流入得分 (0-15)
    inflow = snapshot.main_net_inflow
    if inflow >= 1_000_000_000:  # 10亿
        score += 15.0
    elif inflow >= 500_000_000:  # 5亿
        score += 12.0
    elif inflow >= 100_000_000:  # 1亿
        score += 8.0
    elif inflow >= 0:
        score += 4.0
    else:
        score += 0.0

    # 净流入占成交额比例得分 (0-10)
    if snapshot.turnover > 0:
        ratio = inflow / snapshot.turnover
        if ratio >= 0.1:
            score += 10.0
        elif ratio >= 0.05:
            score += 7.0
        elif ratio >= 0:
            score += 4.0
        else:
            score += 0.0
    else:
        score += 2.0

    return min(score, 25.0)


def calculate_sector_breadth_score(snapshot: SectorSnapshot) -> float:
    """
    计算板块宽度得分 (0-20)

    考虑因素:
    - 上涨家数比例
    - 核心成分股数量
    """
    score = 0.0

    constituents = snapshot.constituents
    if not constituents:
        return 5.0  # 无数据时给基础分

    total = len(constituents)
    advancing = sum(1 for c in constituents if c.change_pct > 0)
    core_count = sum(1 for c in constituents if c.is_core)

    # 上涨家数比例得分 (0-12)
    advance_ratio = advancing / total if total > 0 else 0
    if advance_ratio >= 0.8:
        score += 12.0
    elif advance_ratio >= 0.6:
        score += 9.0
    elif advance_ratio >= 0.4:
        score += 6.0
    else:
        score += 2.0

    # 核心成分股数量得分 (0-8)
    if core_count >= 5:
        score += 8.0
    elif core_count >= 3:
        score += 5.0
    elif core_count >= 1:
        score += 3.0
    else:
        score += 0.0

    return min(score, 20.0)


def _max_drawdown_pct(recent_returns: List[float]) -> float:
    path = _wealth_path(recent_returns)
    peak = path[0]
    drawdown = 0.0
    for value in path:
        peak = max(peak, value)
        drawdown = min(drawdown, (value / peak - 1.0) * 100.0)
    return drawdown


def _drawdown_control_score(recent_returns: List[float]) -> float:
    drawdown = abs(_max_drawdown_pct(recent_returns))
    if drawdown <= 2.0:
        return 3.0
    if drawdown <= 5.0:
        return 2.0
    if drawdown <= 8.0:
        return 1.0
    return 0.0


def calculate_continuity_score(
    snapshot: SectorSnapshot,
    trend_features: Optional[Dict[str, Any]] = None,
) -> float:
    """
    计算持续性得分 (0-15)

    使用多日上涨比例、正向趋势拟合度、最大回撤和排名驻留率。
    少于 10 个有效日时不计持续性分。
    """
    features = trend_features or {}
    recent_returns = [float(value) for value in features.get("recent_returns", [])]
    if len(recent_returns) < 10:
        return 0.0

    last_10 = recent_returns[-10:]
    score = sum(value > 0 for value in last_10) / 10.0 * 4.0
    if len(recent_returns) >= 20:
        last_20 = recent_returns[-20:]
        score += sum(value > 0 for value in last_20) / 20.0 * 3.0
    else:
        last_20 = recent_returns

    score += _positive_trend_fit(last_20) * 3.0
    score += _drawdown_control_score(last_20)

    rank_percentiles = [
        float(value) for value in features.get("daily_rank_percentiles", [])[-10:]
    ]
    if len(rank_percentiles) == 10:
        score += sum(value >= 0.75 for value in rank_percentiles) / 10.0 * 2.0

    return round(min(score, 15.0), 2)


def calculate_market_fit_score(
    snapshot: SectorSnapshot,
    market_temperature: float = 50.0
) -> float:
    """
    计算市场适配得分 (0-10)

    市场温度高时奖励进攻板块，市场弱时惩罚高波动题材
    """
    score = 5.0  # 默认适配
    if not snapshot.price_change_available:
        return score

    # 高温市场 + 正涨幅板块 = 高适配
    if market_temperature >= 70 and snapshot.price_change_pct > 0:
        score = 8.0
    elif market_temperature >= 70 and snapshot.price_change_pct < 0:
        score = 3.0
    elif market_temperature < 30 and snapshot.price_change_pct > 2:
        score = 6.0  # 弱市中的强势板块
    elif market_temperature < 30 and snapshot.price_change_pct < 0:
        score = 2.0

    return min(score, 10.0)


def calculate_data_quality_score(snapshot: SectorSnapshot) -> float:
    """
    计算数据质量得分 (0-5)
    """
    score = 3.0  # 默认

    if snapshot.data_quality_score >= 80:
        score = 5.0
    elif snapshot.data_quality_score >= 60:
        score = 4.0
    elif snapshot.data_quality_score >= 40:
        score = 3.0
    else:
        score = 1.0

    return min(score, 5.0)


def calculate_industry_score(
    snapshot: SectorSnapshot,
    market_temperature: float = 50.0,
    config: Dict[str, Any] = None,
    trend_features: Optional[Dict[str, Any]] = None,
) -> float:
    """
    计算行业板块总分 (0-100)

    各维度得分范围:
    - trend_strength: 0-25
    - capital_flow: 0-25
    - sector_breadth: 0-20
    - continuity: 0-15
    - market_fit: 0-10
    - data_quality: 0-5
    """
    breakdown = calculate_industry_score_breakdown(
        snapshot,
        market_temperature,
        config,
        trend_features,
    )
    return breakdown["final_score"]


def calculate_industry_score_breakdown(
    snapshot: SectorSnapshot,
    market_temperature: float = 50.0,
    config: Dict[str, Any] = None,
    trend_features: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    计算行业板块评分 breakdown

    Returns:
        包含各维度得分的字典
    """
    if config is None:
        config = get_config()

    # 计算各维度得分 (各维度已定义最大值)
    trend_score = calculate_trend_strength_score(snapshot, trend_features)  # 0-25
    flow_score = calculate_capital_flow_score(snapshot)  # 0-25
    breadth_score = calculate_sector_breadth_score(snapshot)  # 0-20
    continuity_score = calculate_continuity_score(snapshot, trend_features)  # 0-15
    market_fit_score = calculate_market_fit_score(snapshot, market_temperature)  # 0-10
    data_quality_score_val = calculate_data_quality_score(snapshot)  # 0-5

    # 正向总分
    positive_score = (
        trend_score +
        flow_score +
        breadth_score +
        continuity_score +
        market_fit_score +
        data_quality_score_val
    )

    history_days = len((trend_features or {}).get("recent_returns", []))
    relative_percentiles = dict(
        (trend_features or {}).get("relative_strength_percentiles", {})
    )
    if history_days < 5:
        history_status = "insufficient_history"
    elif 5 not in relative_percentiles:
        history_status = "reference_unavailable"
    elif history_days >= 20 and all(
        window in relative_percentiles for window in (5, 10, 20)
    ):
        history_status = "ok"
    else:
        history_status = "partial_history"

    return {
        "trend_strength": round(trend_score, 2),
        "fund_flow": round(flow_score, 2),
        "breadth": round(breadth_score, 2),
        "persistence": round(continuity_score, 2),
        "market_fit": round(market_fit_score, 2),
        "data_quality": round(data_quality_score_val, 2),
        "price_change_available": snapshot.price_change_available,
        "trend_history_days": history_days,
        "trend_history_coverage_ratio": round(min(history_days / 20.0, 1.0), 4),
        "trend_history_status": history_status,
        "trend_relative_strength_percentiles": relative_percentiles,
        "positive_score": round(positive_score, 2),
        "final_score": round(min(positive_score, 100.0), 2),
    }
