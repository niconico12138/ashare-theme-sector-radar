"""
板块轮动 Agent

判断板块轮动阶段:
- leading: 领先板块，相对强度高且动量强
- improving: 改善板块，动量转正但相对强度一般
- weakening: 弱化板块，动量转负但相对强度尚可
- lagging: 落后板块，相对强度低且动量弱

输入:
- relative_strength
- momentum_change
- recent_return
- benchmark_return (可选)

第一版如果没有 benchmark_return，使用行业样本中位数作为相对基准，
并在结果中标记 benchmark_mode=sector_median
"""

from typing import Any, Dict, List, Optional, Tuple


def determine_rotation_phase(
    sector_return: float,
    recent_returns: List[float],
    all_sector_returns: Optional[List[float]] = None,
    benchmark_return: Optional[float] = None,
) -> Tuple[str, str, Dict[str, Any]]:
    """
    判断板块轮动阶段

    Args:
        sector_return: 板块累计收益率
        recent_returns: 近期收益率列表
        all_sector_returns: 所有板块收益率 (用于计算中位数)
        benchmark_return: 基准收益率

    Returns:
        (phase, benchmark_mode, details)
    """
    # 计算基准收益率
    benchmark_mode = "sector_median"
    if benchmark_return is None:
        if all_sector_returns and len(all_sector_returns) > 0:
            sorted_returns = sorted(all_sector_returns)
            n = len(sorted_returns)
            if n % 2 == 0:
                benchmark_return = (sorted_returns[n // 2 - 1] + sorted_returns[n // 2]) / 2
            else:
                benchmark_return = sorted_returns[n // 2]
        else:
            benchmark_return = 0.0
            benchmark_mode = "default"

    # 计算相对强度
    relative_strength = sector_return - benchmark_return

    # 计算动量变化 (近期趋势)
    momentum_change = _calculate_momentum_change(recent_returns)

    # 计算波动率
    volatility = _calculate_volatility(recent_returns)

    # 判断轮动阶段
    phase = _classify_rotation_phase(
        relative_strength=relative_strength,
        momentum_change=momentum_change,
        sector_return=sector_return,
        recent_returns=recent_returns,
    )

    # 生成详细信息
    details = {
        "relative_strength": round(relative_strength, 2),
        "momentum_change": round(momentum_change, 2),
        "volatility": round(volatility, 2),
        "benchmark_return": round(benchmark_return, 2),
        "benchmark_mode": benchmark_mode,
        "sector_return": round(sector_return, 2),
        "positive_days": sum(1 for r in recent_returns if r > 0),
        "total_days": len(recent_returns),
    }

    return phase, benchmark_mode, details


def _calculate_momentum_change(recent_returns: List[float]) -> float:
    """
    计算动量变化 (近期趋势)

    使用加权平均，近期权重更高
    """
    if not recent_returns:
        return 0.0

    n = len(recent_returns)
    if n == 1:
        return recent_returns[0]

    # 加权平均
    weighted_sum = sum(recent_returns[i] * (n - i) for i in range(n))
    total_weight = sum(range(1, n + 1))

    return weighted_sum / total_weight if total_weight > 0 else 0.0


def _calculate_volatility(recent_returns: List[float]) -> float:
    """
    计算波动率 (标准差)
    """
    if not recent_returns or len(recent_returns) < 2:
        return 0.0

    mean = sum(recent_returns) / len(recent_returns)
    variance = sum((r - mean) ** 2 for r in recent_returns) / len(recent_returns)

    return variance ** 0.5


def _classify_rotation_phase(
    relative_strength: float,
    momentum_change: float,
    sector_return: float,
    recent_returns: List[float],
) -> str:
    """
    分类轮动阶段

    Args:
        relative_strength: 相对强度 (超额收益)
        momentum_change: 动量变化
        sector_return: 累计收益率
        recent_returns: 近期收益率

    Returns:
        轮动阶段
    """
    # 计算上涨天数比例
    positive_days = sum(1 for r in recent_returns if r > 0)
    total_days = len(recent_returns)
    persistence_ratio = positive_days / total_days if total_days > 0 else 0.5

    # leading: 相对强度高且动量强
    if relative_strength > 2 and momentum_change > 1 and persistence_ratio > 0.6:
        return "leading"

    # improving: 动量转正但相对强度一般
    if momentum_change > 0 and relative_strength > 0 and persistence_ratio > 0.4:
        return "improving"

    # weakening: 动量转负但相对强度尚可
    if momentum_change < 0 and relative_strength > -2 and persistence_ratio < 0.5:
        return "weakening"

    # lagging: 相对强度低且动量弱
    return "lagging"


def get_rotation_phase_description(phase: str) -> str:
    """
    获取轮动阶段描述
    """
    descriptions = {
        "leading": "领先板块，相对强度高且动量强，建议重点关注",
        "improving": "改善板块，动量转正，可作为备选观察",
        "weakening": "弱化板块，动量转负，需谨慎观察",
        "lagging": "落后板块，相对强度低且动量弱，建议回避",
    }
    return descriptions.get(phase, "未知阶段")


def get_rotation_phase_actions(phase: str) -> List[str]:
    """
    获取轮动阶段建议操作
    """
    actions = {
        "leading": [
            "观察是否持续领跑",
            "关注资金流入情况",
            "注意过热风险",
        ],
        "improving": [
            "等待更多确认信号",
            "观察是否突破关键阻力",
            "关注成交量配合",
        ],
        "weakening": [
            "谨慎观察，等待企稳",
            "关注支撑位表现",
            "若跌破支撑则降级观察",
        ],
        "lagging": [
            "建议回避",
            "等待板块轮动机会",
            "关注超跌反弹可能",
        ],
    }
    return actions.get(phase, ["建议观望"])
