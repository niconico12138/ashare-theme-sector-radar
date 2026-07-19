"""
板块综合评分

板块综合评分总分 100 分:
- radar_score_component: 25 分 (日报雷达分)
- momentum_component: 20 分 (动量)
- relative_strength_component: 15 分 (相对强度)
- persistence_component: 15 分 (持续性)
- drawdown_component: 10 分 (回撤)
- volatility_component: 5 分 (波动率)
- data_quality_component: 10 分 (数据质量)
- risk_penalty: 0-20 分 (风险扣分)

等级:
- strong_watch: >= 80
- watch: >= 65
- neutral: >= 50
- cooling: >= 35
- avoid: < 35

权重 Profile:
- baseline: 默认权重 (radar 25, momentum 20, relative 15, persistence 15, drawdown 10, volatility 5, data_quality 10)
- trend_confirmation: 趋势确认型权重 (radar 15, momentum 25, relative 20, persistence 20, drawdown 8, volatility 4, data_quality 8)
"""

from typing import Any, Dict, List, Optional, Tuple

from ..models import SectorSnapshot, SectorType


# 评分权重配置 - baseline (默认)
DEFAULT_WEIGHTS = {
    "radar_score_component": 25.0,
    "momentum_component": 20.0,
    "relative_strength_component": 15.0,
    "persistence_component": 15.0,
    "drawdown_component": 10.0,
    "volatility_component": 5.0,
    "data_quality_component": 10.0,
    "risk_penalty_max": 20.0,
}

# 评分权重配置 - trend_confirmation (趋势确认型)
TREND_CONFIRMATION_WEIGHTS = {
    "radar_score_component": 15.0,
    "momentum_component": 25.0,
    "relative_strength_component": 20.0,
    "persistence_component": 20.0,
    "drawdown_component": 8.0,
    "volatility_component": 4.0,
    "data_quality_component": 8.0,
    "risk_penalty_max": 20.0,
}

# 权重 profile 注册表
WEIGHT_PROFILES = {
    "baseline": DEFAULT_WEIGHTS,
    "trend_confirmation": TREND_CONFIRMATION_WEIGHTS,
}

# 等级阈值
SELECTION_LEVEL_THRESHOLDS = {
    "strong_watch": 80.0,
    "watch": 65.0,
    "neutral": 50.0,
    "cooling": 35.0,
    "avoid": 0.0,
}


def get_weight_profile(profile_name: str) -> Dict[str, float]:
    """
    获取权重 profile

    Args:
        profile_name: profile 名称 (baseline/trend_confirmation)

    Returns:
        权重字典
    """
    if profile_name not in WEIGHT_PROFILES:
        raise ValueError(f"Unknown weight profile: {profile_name}. Available: {list(WEIGHT_PROFILES.keys())}")
    return WEIGHT_PROFILES[profile_name].copy()


def validate_weights(weights: Dict[str, float]) -> bool:
    """
    校验权重总分是否为 100

    Args:
        weights: 权重字典

    Returns:
        是否校验通过
    """
    # 正向组件总分 (不含 risk_penalty_max)
    positive_sum = sum(
        v for k, v in weights.items()
        if k != "risk_penalty_max"
    )
    return abs(positive_sum - 100.0) < 0.01


def get_available_profiles() -> List[str]:
    """获取可用的权重 profile 列表"""
    return list(WEIGHT_PROFILES.keys())


def calculate_radar_score_component(
    radar_score: float,
    max_score: float = 100.0,
    weight: float = 25.0
) -> float:
    """
    计算日报雷达分组件 (0-25)

    Args:
        radar_score: 日报雷达分 (0-100)
        max_score: 最大分值
        weight: 组件权重
    """
    normalized = min(max(radar_score / max_score, 0.0), 1.0)
    return round(normalized * weight, 2)


def calculate_momentum_component(
    recent_returns: List[float],
    weight: float = 20.0
) -> float:
    """
    计算动量组件 (0-20)

    Args:
        recent_returns: 近期收益率列表 (如 [day1, day2, day3, ...])
        weight: 组件权重
    """
    if not recent_returns:
        return weight * 0.3  # 无数据时给基础分

    # 计算平均收益率
    avg_return = sum(recent_returns) / len(recent_returns)

    # 计算加权动量 (近期权重更高)
    n = len(recent_returns)
    weighted_sum = sum(recent_returns[i] * (i + 1) for i in range(n))
    total_weight = sum(range(1, n + 1))
    weighted_momentum = weighted_sum / total_weight if total_weight > 0 else 0

    # 标准化到 0-1
    if weighted_momentum >= 5.0:
        normalized = 1.0
    elif weighted_momentum >= 3.0:
        normalized = 0.8
    elif weighted_momentum >= 1.0:
        normalized = 0.6
    elif weighted_momentum >= 0:
        normalized = 0.4
    elif weighted_momentum >= -2.0:
        normalized = 0.2
    else:
        normalized = 0.0

    return round(normalized * weight, 2)


def calculate_relative_strength_component(
    sector_return: float,
    benchmark_return: float,
    all_sector_returns: Optional[List[float]] = None,
    weight: float = 15.0,
    benchmark_mode: str = "sector_median",
    benchmark_id: Optional[str] = None,
    benchmark_name: Optional[str] = None,
) -> Tuple[float, str, Optional[str], Optional[str]]:
    """
    计算相对强度组件 (0-15)

    Args:
        sector_return: 板块收益率
        benchmark_return: 基准收益率 (如行业样本中位数)
        all_sector_returns: 所有板块收益率 (用于计算中位数)
        weight: 组件权重
        benchmark_mode: 基准模式
        benchmark_id: 基准 ID (如 hs300)
        benchmark_name: 基准名称 (如 沪深300)

    Returns:
        (score, actual_benchmark_mode, actual_benchmark_id, actual_benchmark_name)
    """
    # 确定基准模式
    if benchmark_id:
        # 使用真实市场基准
        benchmark_mode = "market_benchmark"
    elif benchmark_return == 0.0 and all_sector_returns and len(all_sector_returns) > 0:
        # 没有提供基准收益率，使用行业样本中位数
        sorted_returns = sorted(all_sector_returns)
        n = len(sorted_returns)
        if n % 2 == 0:
            benchmark_return = (sorted_returns[n // 2 - 1] + sorted_returns[n // 2]) / 2
        else:
            benchmark_return = sorted_returns[n // 2]
        benchmark_mode = "sector_median"
        benchmark_id = None
        benchmark_name = None

    # 计算超额收益
    excess_return = sector_return - benchmark_return

    # 标准化到 0-1
    if excess_return >= 5.0:
        normalized = 1.0
    elif excess_return >= 3.0:
        normalized = 0.85
    elif excess_return >= 1.0:
        normalized = 0.7
    elif excess_return >= 0:
        normalized = 0.5
    elif excess_return >= -2.0:
        normalized = 0.3
    else:
        normalized = 0.1

    return round(normalized * weight, 2), benchmark_mode, benchmark_id, benchmark_name


def calculate_persistence_component(
    positive_days_count: int,
    total_days: int,
    weight: float = 15.0
) -> float:
    """
    计算持续性组件 (0-15)

    Args:
        positive_days_count: 上涨天数
        total_days: 总天数
        weight: 组件权重
    """
    if total_days == 0:
        return weight * 0.3  # 无数据时给基础分

    persistence_ratio = positive_days_count / total_days

    # 标准化到 0-1
    if persistence_ratio >= 0.8:
        normalized = 1.0
    elif persistence_ratio >= 0.6:
        normalized = 0.75
    elif persistence_ratio >= 0.4:
        normalized = 0.5
    elif persistence_ratio >= 0.2:
        normalized = 0.25
    else:
        normalized = 0.0

    return round(normalized * weight, 2)


def calculate_drawdown_component(
    max_drawdown: float,
    weight: float = 10.0
) -> float:
    """
    计算回撤组件 (0-10)

    Args:
        max_drawdown: 最大回撤 (百分数点，如 -8.68 表示 -8.68%)
        weight: 组件权重
    """
    # 回撤越小越好 (max_drawdown 是负数百分数点)
    drawdown_pct = abs(max_drawdown)  # 直接使用百分数点

    if drawdown_pct <= 2.0:
        normalized = 1.0
    elif drawdown_pct <= 5.0:
        normalized = 0.75
    elif drawdown_pct <= 10.0:
        normalized = 0.5
    elif drawdown_pct <= 15.0:
        normalized = 0.25
    else:
        normalized = 0.0

    return round(normalized * weight, 2)


def calculate_volatility_component(
    volatility: float,
    weight: float = 5.0
) -> float:
    """
    计算波动率组件 (0-5)

    Args:
        volatility: 波动率 (标准差)
        weight: 组件权重
    """
    # 波动率越低越好
    if volatility <= 1.0:
        normalized = 1.0
    elif volatility <= 2.0:
        normalized = 0.8
    elif volatility <= 3.0:
        normalized = 0.6
    elif volatility <= 5.0:
        normalized = 0.4
    else:
        normalized = 0.2

    return round(normalized * weight, 2)


def calculate_data_quality_component(
    data_quality_score: float,
    history_days: int,
    price_change_available: bool = True,
    weight: float = 10.0
) -> float:
    """
    计算数据质量组件 (0-10)

    Args:
        data_quality_score: 数据质量分 (0-100)
        history_days: 历史数据天数
        price_change_available: 涨跌幅是否可用
        weight: 组件权重
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

    # 历史数据天数调整
    if history_days >= 5:
        history_factor = 1.0
    elif history_days >= 3:
        history_factor = 0.8
    elif history_days >= 1:
        history_factor = 0.6
    else:
        history_factor = 0.3

    # 涨跌幅可用性调整
    price_factor = 1.0 if price_change_available else 0.7

    normalized = base_score * history_factor * price_factor
    return round(min(normalized, 1.0) * weight, 2)


def calculate_risk_penalty(
    max_drawdown: float,
    volatility: float,
    recent_negative_days: int,
    total_days: int,
    max_penalty: float = 20.0
) -> float:
    """
    计算风险扣分 (0-20)

    Args:
        max_drawdown: 最大回撤 (负数)
        volatility: 波动率
        recent_negative_days: 近期下跌天数
        total_days: 总天数
        max_penalty: 最大扣分

    Returns:
        风险扣分 (正数，用于从总分中减去)
    """
    penalty = 0.0

    # 回撤扣分 (0-8)
    drawdown_pct = abs(max_drawdown)  # max_drawdown 已是百分数点
    if drawdown_pct > 15:
        penalty += 8.0
    elif drawdown_pct > 10:
        penalty += 6.0
    elif drawdown_pct > 5:
        penalty += 4.0
    elif drawdown_pct > 3:
        penalty += 2.0

    # 波动率扣分 (0-6)
    if volatility > 5:
        penalty += 6.0
    elif volatility > 3:
        penalty += 4.0
    elif volatility > 2:
        penalty += 2.0

    # 下跌天数扣分 (0-6)
    if total_days > 0:
        negative_ratio = recent_negative_days / total_days
        if negative_ratio > 0.7:
            penalty += 6.0
        elif negative_ratio > 0.5:
            penalty += 4.0
        elif negative_ratio > 0.3:
            penalty += 2.0

    return round(min(penalty, max_penalty), 2)


def get_selection_level(score: float) -> str:
    """
    根据分数获取选择等级

    Args:
        score: 综合评分

    Returns:
        选择等级
    """
    for level, threshold in SELECTION_LEVEL_THRESHOLDS.items():
        if score >= threshold:
            return level
    return "avoid"


def calculate_sector_composite_score(
    radar_score: float,
    recent_returns: List[float],
    sector_return: float,
    benchmark_return: float = 0.0,
    all_sector_returns: Optional[List[float]] = None,
    positive_days_count: int = 0,
    total_days: int = 0,
    max_drawdown: float = 0.0,
    volatility: float = 0.0,
    data_quality_score: float = 50.0,
    history_days: int = 0,
    price_change_available: bool = True,
    weights: Optional[Dict[str, float]] = None,
    benchmark_id: Optional[str] = None,
    benchmark_name: Optional[str] = None,
    trend_weight_profile: str = "baseline",
) -> Dict[str, Any]:
    """
    计算板块综合评分

    Args:
        radar_score: 日报雷达分 (0-100)
        recent_returns: 近期收益率列表
        sector_return: 板块累计收益率
        benchmark_return: 基准收益率
        all_sector_returns: 所有板块收益率 (用于计算中位数)
        positive_days_count: 上涨天数
        total_days: 总天数
        max_drawdown: 最大回撤 (负数)
        volatility: 波动率
        data_quality_score: 数据质量分 (0-100)
        history_days: 历史数据天数
        price_change_available: 涨跌幅是否可用
        weights: 自定义权重 (优先于 trend_weight_profile)
        benchmark_id: 基准 ID (如 hs300)
        benchmark_name: 基准名称 (如 沪深300)
        trend_weight_profile: 趋势权重 profile (baseline/trend_confirmation)

    Returns:
        综合评分结果字典
    """
    if weights is None:
        weights = get_weight_profile(trend_weight_profile)

    # 1. 日报雷达分组件
    radar_component = calculate_radar_score_component(
        radar_score,
        weight=weights["radar_score_component"]
    )

    # 2. 动量组件
    momentum_component = calculate_momentum_component(
        recent_returns,
        weight=weights["momentum_component"]
    )

    # 3. 相对强度组件
    relative_strength_component, benchmark_mode, actual_benchmark_id, actual_benchmark_name = calculate_relative_strength_component(
        sector_return,
        benchmark_return,
        all_sector_returns,
        weight=weights["relative_strength_component"],
        benchmark_id=benchmark_id,
        benchmark_name=benchmark_name,
    )

    # 4. 持续性组件
    persistence_component = calculate_persistence_component(
        positive_days_count,
        total_days,
        weight=weights["persistence_component"]
    )

    # 5. 回撤组件
    drawdown_component = calculate_drawdown_component(
        max_drawdown,
        weight=weights["drawdown_component"]
    )

    # 6. 波动率组件
    volatility_component = calculate_volatility_component(
        volatility,
        weight=weights["volatility_component"]
    )

    # 7. 数据质量组件
    data_quality_component = calculate_data_quality_component(
        data_quality_score,
        history_days,
        price_change_available,
        weight=weights["data_quality_component"]
    )

    # 8. 风险扣分
    risk_penalty = calculate_risk_penalty(
        max_drawdown,
        volatility,
        total_days - positive_days_count,
        total_days,
        max_penalty=weights["risk_penalty_max"]
    )

    # 计算正向总分
    positive_score = (
        radar_component +
        momentum_component +
        relative_strength_component +
        persistence_component +
        drawdown_component +
        volatility_component +
        data_quality_component
    )

    # 计算最终得分
    final_score = max(positive_score - risk_penalty, 0.0)

    # 获取选择等级
    selection_level = get_selection_level(final_score)

    return {
        "sector_selection_score": round(final_score, 2),
        "selection_level": selection_level,
        "benchmark_mode": benchmark_mode,
        "benchmark_id": actual_benchmark_id,
        "benchmark_name": actual_benchmark_name,
        "trend_weight_profile": trend_weight_profile,
        "score_breakdown": {
            "radar_score_component": radar_component,
            "momentum_component": momentum_component,
            "relative_strength_component": relative_strength_component,
            "persistence_component": persistence_component,
            "drawdown_component": drawdown_component,
            "volatility_component": volatility_component,
            "data_quality_component": data_quality_component,
            "risk_penalty": risk_penalty,
            "positive_score": round(positive_score, 2),
            "final_score": round(final_score, 2),
        },
    }


def generate_strength_reasons(
    radar_score: float,
    momentum: float,
    relative_strength: float,
    persistence_ratio: float,
    selection_level: str
) -> List[str]:
    """
    生成强度原因列表

    Args:
        radar_score: 日报雷达分
        momentum: 动量
        relative_strength: 相对强度
        persistence_ratio: 持续性比例
        selection_level: 选择等级

    Returns:
        强度原因列表
    """
    reasons = []

    if radar_score >= 70:
        reasons.append("日报雷达分较高")
    elif radar_score >= 50:
        reasons.append("日报雷达分中等")

    if momentum >= 3.0:
        reasons.append("近期涨幅靠前")
    elif momentum >= 1.0:
        reasons.append("近期小幅上涨")

    if relative_strength >= 2.0:
        reasons.append("相对行业中位数明显走强")
    elif relative_strength >= 0:
        reasons.append("相对行业中位数走强")

    if persistence_ratio >= 0.7:
        reasons.append("上涨持续性强")
    elif persistence_ratio >= 0.5:
        reasons.append("上涨持续性一般")

    if selection_level == "strong_watch":
        reasons.insert(0, "综合评分优秀，建议重点关注")
    elif selection_level == "watch":
        reasons.insert(0, "综合评分良好，建议观察")

    return reasons


def generate_risk_reasons(
    max_drawdown: float,
    volatility: float,
    negative_ratio: float
) -> List[str]:
    """
    生成风险原因列表

    Args:
        max_drawdown: 最大回撤 (百分数点，如 -8.68 表示 -8.68%)
        volatility: 波动率 (百分数点)
        negative_ratio: 下跌天数比例 (0-1 小数)

    Returns:
        风险原因列表
    """
    reasons = []

    # max_drawdown 是百分数点，阈值对应的百分数点含义：
    # > 10  → 回撤超过 10%（较大）
    # > 5   → 回撤超过 5%（存在一定回撤）
    if abs(max_drawdown) > 10:
        reasons.append(f"最大回撤较大 ({max_drawdown:.1f}%)")
    elif abs(max_drawdown) > 5:
        reasons.append(f"存在一定回撤 ({max_drawdown:.1f}%)")

    if volatility > 3.0:
        reasons.append(f"波动率较高 ({volatility:.1f})")
    elif volatility > 2.0:
        reasons.append(f"波动率中等 ({volatility:.1f})")

    if negative_ratio > 0.5:
        reasons.append("下跌天数占比较高")

    return reasons


def generate_watch_points(
    selection_level: str,
    benchmark_mode: str,
    persistence_ratio: float,
    volatility: float
) -> List[str]:
    """
    生成观察要点列表

    Args:
        selection_level: 选择等级
        benchmark_mode: 基准模式
        persistence_ratio: 持续性比例
        volatility: 波动率

    Returns:
        观察要点列表
    """
    points = []

    if selection_level in ["strong_watch", "watch"]:
        points.append("观察后续是否继续跑赢行业中位数")
        if persistence_ratio < 0.6:
            points.append("持续性待确认，关注后续表现")
        if volatility > 2.5:
            points.append("波动率较高，注意仓位控制")
    elif selection_level == "neutral":
        points.append("表现中性，可作为备选观察")
        points.append("等待更多确认信号")
    elif selection_level == "cooling":
        points.append("板块降温，谨慎观察")
        points.append("若放量滞涨则降级观察")
    else:
        points.append("板块弱势，建议回避")

    if benchmark_mode == "sector_median":
        points.append("基准为行业中位数，注意行业整体表现")

    return points


def apply_insufficient_history_cap(
    final_score: float,
    trend_window_status: str,
    history_coverage_ratio: float,
) -> float:
    """
    当趋势窗口数据不足时，对趋势分设置上限。

    缺历史数据板块不应因为无回撤扣分而排到趋势榜前面。

    Args:
        final_score: 原始趋势分
        trend_window_status: 趋势窗口状态
        history_coverage_ratio: 历史数据覆盖率

    Returns:
        调整后的趋势分
    """
    # insufficient_history 或覆盖率 < 0.5 时，上限为 34.9（cooling 区间上限）
    if trend_window_status == "insufficient_history" or history_coverage_ratio < 0.5:
        return min(final_score, 34.9)
    return final_score


def generate_data_warnings(
    history_days: int,
    price_change_available: bool,
    sector_type: str
) -> List[str]:
    """
    生成数据警告列表

    Args:
        history_days: 历史数据天数
        price_change_available: 涨跌幅是否可用
        sector_type: 板块类型

    Returns:
        数据警告列表
    """
    warnings = []

    if history_days < 3:
        warnings.append(f"历史数据不足 ({history_days} 天)，评分可靠性降低")

    if not price_change_available and sector_type == "concept":
        warnings.append("概念板块缺少涨跌幅数据，评分偏保守")

    if history_days == 0:
        warnings.append("无历史数据，仅基于日报雷达分评分")

    return warnings
