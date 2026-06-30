"""
关注等级计算

根据正向评分、风险扣分和数据质量计算最终关注等级。
"""

from typing import Any, Dict, List, Tuple

from ..config import get_config
from ..models import FocusLevel, RiskLevel


def calculate_focus_level(
    positive_score: float,
    risk_penalty: float,
    risk_level: RiskLevel,
    data_quality_score: float,
    config: Dict[str, Any] = None,
    price_change_available: bool = True,
) -> Tuple[FocusLevel, List[str]]:
    """
    计算关注等级

    Args:
        positive_score: 正向评分 (0-100)
        risk_penalty: 风险扣分 (正数，例如 3.0)
        risk_level: 风险等级
        data_quality_score: 数据质量分
        price_change_available: 涨跌幅是否可用

    返回: (focus_level, downgrade_reasons)
    """
    if config is None:
        config = get_config()

    thresholds = config.get("focus_level_thresholds", {})
    # final_score = positive_score - risk_penalty (risk_penalty 为正数)
    final_score = positive_score - risk_penalty

    downgrade_reasons = []

    # 涨跌幅不可用时，不能输出高置信 focus
    if not price_change_available and final_score >= thresholds.get("focus_min_score", 80):
        downgrade_reasons.append("涨跌幅数据不可用，无法确认板块热度，降级处理")

    # 数据质量低时不能输出 focus
    if data_quality_score < 60 and final_score >= thresholds.get("focus_min_score", 80):
        downgrade_reasons.append(f"数据质量分偏低 ({data_quality_score:.0f})，降级处理")

    # 高强度 + 高风险时应输出 core_only，而不是 focus
    if positive_score >= thresholds.get("focus_min_score", 80) and risk_level == RiskLevel.HIGH:
        downgrade_reasons.append("板块强度高但风险等级高，只关注核心成分股")
        return FocusLevel.CORE_ONLY, downgrade_reasons

    # 正常等级判断
    if final_score >= thresholds.get("focus_min_score", 80) and not downgrade_reasons:
        return FocusLevel.FOCUS, downgrade_reasons
    elif final_score >= thresholds.get("watch_min_score", 65):
        if downgrade_reasons:
            return FocusLevel.WATCH, downgrade_reasons
        return FocusLevel.WATCH, downgrade_reasons
    elif final_score >= thresholds.get("caution_min_score", 45):
        downgrade_reasons.append(f"最终评分偏低 ({final_score:.1f})")
        return FocusLevel.CAUTION, downgrade_reasons
    else:
        downgrade_reasons.append(f"最终评分过低 ({final_score:.1f})")
        return FocusLevel.AVOID, downgrade_reasons


def explain_downgrade(
    focus_level: FocusLevel,
    positive_score: float,
    risk_penalty: float,
    risk_level: RiskLevel,
    risk_flags: List[str],
    data_quality_score: float
) -> List[str]:
    """
    生成降级解释

    Args:
        risk_penalty: 风险扣分 (正数)
    """
    reasons = []

    if focus_level == FocusLevel.CORE_ONLY:
        reasons.append("板块强度高但短期涨幅过热或分歧大")
        if "overheat" in risk_flags:
            reasons.append("存在过热风险，只适合观察核心成分股")
        if "divergence" in risk_flags:
            reasons.append("资金流与价格表现出现背离")
        if risk_level == RiskLevel.HIGH:
            reasons.append("风险等级为高，建议只关注核心成分股强弱")

    elif focus_level == FocusLevel.CAUTION:
        if risk_penalty >= 10:  # 正数比较
            reasons.append("风险扣分较高")
        if data_quality_score < 60:
            reasons.append("数据质量需要确认")
        if positive_score < 65:
            reasons.append("正向信号强度不足")

    elif focus_level == FocusLevel.AVOID:
        if positive_score < 45:
            reasons.append("板块正向强度不足")
        if risk_penalty >= 15:  # 正数比较
            reasons.append("风险问题突出")
        if data_quality_score < 40:
            reasons.append("数据质量过低，无法可靠评估")

    return reasons


def generate_watch_points(
    focus_level: FocusLevel,
    score_breakdown: Dict[str, Any],
    risk_breakdown: Dict[str, Any]
) -> List[str]:
    """
    生成观察要点

    Args:
        focus_level: 关注等级
        score_breakdown: 评分 breakdown
        risk_breakdown: 风险 breakdown

    Returns:
        观察要点列表
    """
    watch_points = []

    if focus_level == FocusLevel.FOCUS:
        # focus 板块：说明为什么高分且风险可控
        if score_breakdown.get("trend_strength", 0) >= 15:
            watch_points.append("趋势强度高，可继续关注")
        if score_breakdown.get("fund_flow", 0) >= 15:
            watch_points.append("资金流入明显，注意持续性")
        if risk_breakdown.get("risk_level") == RiskLevel.LOW:
            watch_points.append("风险等级低，可适度参与")

    elif focus_level == FocusLevel.WATCH:
        # watch 板块：说明还缺什么确认
        if score_breakdown.get("persistence", 0) < 10:
            watch_points.append("持续性待确认，观察后续表现")
        if score_breakdown.get("breadth", 0) < 10:
            watch_points.append("板块宽度不足，关注成分股联动")
        if risk_breakdown.get("risk_level") == RiskLevel.MEDIUM:
            watch_points.append("存在中等风险，需谨慎观察")

    elif focus_level == FocusLevel.CORE_ONLY:
        # core_only 板块：说明为什么不能直接重点关注
        if "overheat" in risk_breakdown.get("risk_flags", []):
            watch_points.append("存在过热风险，只观察核心成分股")
        if "divergence" in risk_breakdown.get("risk_flags", []):
            watch_points.append("资金流与价格背离，等待确认")
        watch_points.append("板块强度高但风险大，不宜追高")

    elif focus_level == FocusLevel.CAUTION:
        # caution 板块：说明主要风险
        if risk_breakdown.get("total_penalty", 0) >= 10:  # 正数比较
            watch_points.append("风险扣分较高，需等待风险释放")
        if score_breakdown.get("positive_score", 0) < 65:
            watch_points.append("正向信号强度不足，观望为主")

    return watch_points
