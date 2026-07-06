"""
短线爆发评分

短线爆发评分总分 100 分:
- radar_today_component: 30 分 (当日雷达分)
- one_day_change_component: 20 分 (单日涨幅)
- three_day_momentum_component: 15 分 (3日动量)
- volume_or_heat_component: 10 分 (成交额或热度)
- rank_jump_component: 10 分 (排名跳升)
- data_quality_component: 10 分 (数据质量)
- burst_risk_penalty: 0-20 分 (风险扣分)

等级:
- burst_hot: >= 80
- burst_watch: >= 65
- burst_neutral: >= 50
- burst_fading: >= 35
- burst_avoid: < 35
"""

from typing import Any, Dict, List, Optional, Tuple

from ..models import SectorSnapshot


# 短线爆发等级阈值
BURST_LEVEL_THRESHOLDS = {
    "burst_hot": 80.0,
    "burst_watch": 65.0,
    "burst_neutral": 50.0,
    "burst_fading": 35.0,
    "burst_avoid": 0.0,
}


def calculate_radar_today_component(
    radar_score: float,
    max_score: float = 100.0,
    weight: float = 30.0
) -> float:
    """
    计算当日雷达分组件 (0-30)

    Args:
        radar_score: 日报雷达分 (0-100)
        max_score: 最大分值
        weight: 组件权重
    """
    normalized = min(max(radar_score / max_score, 0.0), 1.0)
    return round(normalized * weight, 2)


def calculate_one_day_change_component(
    one_day_change: Optional[float],
    weight: float = 20.0
) -> Tuple[float, bool]:
    """
    计算单日涨幅组件 (0-20)

    Args:
        one_day_change: 单日涨幅 (%)
        weight: 组件权重

    Returns:
        (score, is_missing)
    """
    if one_day_change is None:
        return 0.0, True  # 缺失时为 0

    # 标准化到 0-1
    if one_day_change >= 5.0:
        normalized = 1.0
    elif one_day_change >= 3.0:
        normalized = 0.8
    elif one_day_change >= 1.0:
        normalized = 0.6
    elif one_day_change >= 0:
        normalized = 0.4
    elif one_day_change >= -2.0:
        normalized = 0.2
    else:
        normalized = 0.0

    return round(normalized * weight, 2), False


def calculate_three_day_momentum_component(
    recent_returns: List[float],
    weight: float = 15.0
) -> Tuple[float, bool]:
    """
    计算 3 日动量组件 (0-15)

    Args:
        recent_returns: 近期收益率列表
        weight: 组件权重

    Returns:
        (score, is_missing)
    """
    if not recent_returns or len(recent_returns) < 3:
        return weight * 0.3, True  # 缺失时给基础分

    # 使用最近 3 天的收益率
    last_3 = recent_returns[-3:]
    avg_return = sum(last_3) / len(last_3)

    # 标准化到 0-1
    if avg_return >= 3.0:
        normalized = 1.0
    elif avg_return >= 1.5:
        normalized = 0.8
    elif avg_return >= 0.5:
        normalized = 0.6
    elif avg_return >= 0:
        normalized = 0.4
    elif avg_return >= -1.0:
        normalized = 0.2
    else:
        normalized = 0.0

    return round(normalized * weight, 2), False


def calculate_volume_or_heat_component(
    turnover: Optional[float],
    main_net_inflow: Optional[float],
    weight: float = 10.0
) -> Tuple[float, bool]:
    """
    计算成交额或热度组件 (0-10)

    Args:
        turnover: 成交额
        main_net_inflow: 主力净流入
        weight: 组件权重

    Returns:
        (score, is_missing)
    """
    if turnover is None and main_net_inflow is None:
        return weight * 0.5, True  # 缺失时给中性分

    score = 0.0

    # 成交额得分 (0-5)
    if turnover is not None:
        if turnover >= 10_000_000_000:  # 100亿
            score += 5.0
        elif turnover >= 5_000_000_000:  # 50亿
            score += 4.0
        elif turnover >= 1_000_000_000:  # 10亿
            score += 3.0
        elif turnover >= 0:
            score += 2.0
        else:
            score += 1.0
    else:
        score += 2.5  # 中性分

    # 资金流入得分 (0-5)
    if main_net_inflow is not None:
        if main_net_inflow >= 500_000_000:  # 5亿
            score += 5.0
        elif main_net_inflow >= 100_000_000:  # 1亿
            score += 4.0
        elif main_net_inflow >= 0:
            score += 3.0
        elif main_net_inflow >= -100_000_000:
            score += 2.0
        else:
            score += 1.0
    else:
        score += 2.5  # 中性分

    return round(min(score, weight), 2), False


def calculate_rank_jump_component(
    current_rank: Optional[int],
    previous_rank: Optional[int],
    weight: float = 10.0
) -> Tuple[float, bool]:
    """
    计算排名跳升组件 (0-10)

    Args:
        current_rank: 当前排名
        previous_rank: 上期排名
        weight: 组件权重

    Returns:
        (score, is_missing)
    """
    if current_rank is None or previous_rank is None:
        return weight * 0.5, True  # 缺失时给中性分

    # 计算排名变化
    rank_change = previous_rank - current_rank  # 正数表示上升

    # 标准化到 0-1
    if rank_change >= 10:
        normalized = 1.0
    elif rank_change >= 5:
        normalized = 0.8
    elif rank_change >= 2:
        normalized = 0.6
    elif rank_change >= 0:
        normalized = 0.5
    elif rank_change >= -2:
        normalized = 0.3
    else:
        normalized = 0.1

    return round(normalized * weight, 2), False


def calculate_burst_data_quality_component(
    data_quality_score: float,
    price_change_available: bool = True,
    history_days: int = 0,
    weight: float = 10.0
) -> float:
    """
    计算数据质量组件 (0-10)

    Args:
        data_quality_score: 数据质量分 (0-100)
        price_change_available: 涨跌幅是否可用
        history_days: 历史数据天数
        weight: 组件权重

    Returns:
        数据质量组件得分
    """
    # 基础数据质量分
    if data_quality_score >= 80:
        base_score = 1.0
    elif data_quality_score >= 60:
        base_score = 0.8
    elif data_quality_score >= 40:
        base_score = 0.6
    elif data_quality_score >= 20:
        base_score = 0.4
    else:
        base_score = 0.2

    # 涨跌幅可用性调整
    price_factor = 1.0 if price_change_available else 0.7

    # 历史数据天数调整
    if history_days >= 5:
        history_factor = 1.0
    elif history_days >= 3:
        history_factor = 0.9
    elif history_days >= 1:
        history_factor = 0.8
    else:
        history_factor = 0.7

    normalized = base_score * price_factor * history_factor
    return round(min(normalized, 1.0) * weight, 2)


def calculate_burst_risk_penalty(
    one_day_change: Optional[float],
    persistence_ratio: float,
    history_source: str = "sector_history_cache",
    price_change_available: bool = True,
    max_penalty: float = 20.0
) -> float:
    """
    计算短线风险扣分 (0-20)

    Args:
        one_day_change: 单日涨幅
        persistence_ratio: 持续性比例
        history_source: 历史数据来源
        price_change_available: 涨跌幅是否可用
        max_penalty: 最大扣分

    Returns:
        风险扣分 (正数，用于从总分中减去)
    """
    penalty = 0.0

    # 单日涨幅过高扣分 (0-8)
    if one_day_change is not None:
        if one_day_change > 8:
            penalty += 8.0
        elif one_day_change > 5:
            penalty += 5.0
        elif one_day_change > 3:
            penalty += 2.0

    # 持续性差但当日爆发扣分 (0-5)
    if one_day_change is not None and one_day_change > 3 and persistence_ratio < 0.4:
        penalty += 5.0  # 短线脉冲，需确认持续性

    # 数据来源为 raw_snapshot_fallback 扣分 (0-3)
    if history_source == "raw_snapshot_fallback":
        penalty += 3.0

    # 涨跌幅不可用扣分 (0-2)
    if not price_change_available:
        penalty += 2.0

    return round(min(penalty, max_penalty), 2)


def get_burst_level(score: float) -> str:
    """
    根据分数获取短线爆发等级

    Args:
        score: 短线爆发评分

    Returns:
        短线爆发等级
    """
    for level, threshold in BURST_LEVEL_THRESHOLDS.items():
        if score >= threshold:
            return level
    return "burst_avoid"


def calculate_short_term_burst_score(
    radar_score: float,
    one_day_change: Optional[float] = None,
    recent_returns: Optional[List[float]] = None,
    turnover: Optional[float] = None,
    main_net_inflow: Optional[float] = None,
    current_rank: Optional[int] = None,
    previous_rank: Optional[int] = None,
    data_quality_score: float = 50.0,
    price_change_available: bool = True,
    history_days: int = 0,
    history_source: str = "sector_history_cache",
) -> Dict[str, Any]:
    """
    计算短线爆发评分

    Args:
        radar_score: 日报雷达分 (0-100)
        one_day_change: 单日涨幅 (%)
        recent_returns: 近期收益率列表
        turnover: 成交额
        main_net_inflow: 主力净流入
        current_rank: 当前排名
        previous_rank: 上期排名
        data_quality_score: 数据质量分 (0-100)
        price_change_available: 涨跌幅是否可用
        history_days: 历史数据天数
        history_source: 历史数据来源

    Returns:
        短线爆发评分结果字典
    """
    warnings = []

    # 检查涨跌幅可用性
    if not price_change_available:
        warnings.append("涨跌幅数据不可用，短线爆发评分可能不准确")

    # 1. 当日雷达分组件 (30分)
    radar_today = calculate_radar_today_component(radar_score)

    # 2. 单日涨幅组件 (20分)
    one_day_change_score, one_day_missing = calculate_one_day_change_component(one_day_change)
    if one_day_missing:
        warnings.append("one_day_change 缺失，该组件为 0")

    # 3. 3日动量组件 (15分)
    three_day_momentum, momentum_missing = calculate_three_day_momentum_component(
        recent_returns or []
    )
    if momentum_missing:
        warnings.append("recent_returns 不足 3 天，使用基础分")

    # 4. 成交额或热度组件 (10分)
    volume_heat, volume_missing = calculate_volume_or_heat_component(turnover, main_net_inflow)
    if volume_missing:
        warnings.append("turnover 和 main_net_inflow 均缺失，使用中性分")

    # 5. 排名跳升组件 (10分)
    rank_jump, rank_missing = calculate_rank_jump_component(current_rank, previous_rank)
    if rank_missing:
        warnings.append("rank 数据缺失，使用中性分")

    # 6. 数据质量组件 (10分)
    data_quality = calculate_burst_data_quality_component(
        data_quality_score, price_change_available, history_days
    )

    # 7. 风险扣分 (0-20)
    persistence_ratio = 0.5  # 默认值
    if recent_returns and len(recent_returns) > 0:
        positive_days = sum(1 for r in recent_returns if r > 0)
        persistence_ratio = positive_days / len(recent_returns)

    burst_risk = calculate_burst_risk_penalty(
        one_day_change, persistence_ratio, history_source, price_change_available
    )

    # 计算正向总分
    positive_score = (
        radar_today +
        one_day_change_score +
        three_day_momentum +
        volume_heat +
        rank_jump +
        data_quality
    )

    # 计算最终得分
    final_score = max(positive_score - burst_risk, 0.0)

    # 获取短线爆发等级
    burst_level = get_burst_level(final_score)

    return {
        "short_term_burst_score": round(final_score, 2),
        "burst_level": burst_level,
        "burst_breakdown": {
            "radar_today_component": radar_today,
            "one_day_change_component": one_day_change_score,
            "three_day_momentum_component": three_day_momentum,
            "volume_or_heat_component": volume_heat,
            "rank_jump_component": rank_jump,
            "data_quality_component": data_quality,
            "burst_risk_penalty": burst_risk,
            "positive_score": round(positive_score, 2),
            "final_score": round(final_score, 2),
        },
        "warnings": warnings,
    }


def interpret_dual_scores(
    trend_score: float,
    trend_level: str,
    burst_score: float,
    burst_level: str,
) -> Dict[str, Any]:
    """
    解读双评分结果

    Args:
        trend_score: 趋势持续分
        trend_level: 趋势持续等级
        burst_score: 短线爆发分
        burst_level: 短线爆发等级

    Returns:
        解读结果字典
    """
    # 判断 profile
    if trend_score >= 65 and burst_score >= 65:
        profile = "trend_and_burst_aligned"
        summary = "趋势和短线都强，双重确认"
        watch_points = [
            "趋势和短线双重确认，可重点关注",
            "观察是否能持续保持双强态势",
        ]
    elif trend_score >= 65 and burst_score < 50:
        profile = "trend_only"
        summary = "趋势强但短线不热，中长期趋势观察价值较高"
        watch_points = [
            "趋势持续性好，但短线缺乏爆发力",
            "观察是否有催化剂推动短线表现",
        ]
    elif trend_score < 50 and burst_score >= 65:
        profile = "burst_without_trend_confirmation"
        summary = "短线强但趋势未确认，需谨慎"
        watch_points = [
            "短线爆发，但趋势持续性尚未确认",
            "观察次日是否继续跑赢行业中位数",
            "若高开低走则短线爆发降级",
        ]
    elif trend_score < 50 and burst_score < 50:
        profile = "weak_or_cooling"
        summary = "趋势和短线都弱，建议回避"
        watch_points = [
            "板块整体表现疲弱",
            "等待明确的反转信号",
        ]
    else:
        profile = "neutral"
        summary = "表现中性，可作为备选观察"
        watch_points = [
            "等待更多确认信号",
            "关注后续表现",
        ]

    return {
        "profile": profile,
        "summary": summary,
        "watch_points": watch_points,
    }


def apply_burst_insufficient_history_cap(
    burst_score: float,
    history_days: int,
    actual_history_days: int = None,
) -> tuple:
    """
    当历史数据不足时，对短线爆发分设置上限。

    缺历史数据板块不应因为少回撤扣分 / 少弱数据扣分而排在短线爆发榜前面。

    Args:
        burst_score: 原始短线爆发分
        history_days: 原始历史数据天数 (从 sector_history 读取)
        actual_history_days: 实际可用的历史数据天数 (截取后)

    Returns:
        (adjusted_score, cap_applied, cap_reason)
    """
    if actual_history_days is None:
        actual_history_days = history_days

    if history_days == 0 or actual_history_days == 0:
        # 完全无历史数据 -> cap 到 34.9 (burst_avoid 区间上限)
        if burst_score > 34.9:
            return 34.9, True, "history_days=0，短线分上限 34.9 (burst_avoid)"
        return burst_score, False, ""

    if 0 < actual_history_days < 3:
        # 历史数据不足 3 天 -> cap 到 49.9 (burst_fading 区间上限)
        if burst_score > 49.9:
            return 49.9, True, f"actual_history_days={actual_history_days} (<3)，短线分上限 49.9 (burst_fading)"
        return burst_score, False, ""

    # actual_history_days >= 3: 不 cap
    return burst_score, False, ""


from typing import Tuple
