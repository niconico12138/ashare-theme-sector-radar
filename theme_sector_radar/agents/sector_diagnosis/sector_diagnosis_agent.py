"""
板块诊断 Agent

根据评分 breakdown 生成诊断信息:
- strength_reasons
- risk_reasons
- watch_points
- data_warnings
"""

from typing import Any, Dict, List, Optional


def diagnose_sector(
    score_data: Dict[str, Any],
    sector_type: str = "industry",
) -> Dict[str, Any]:
    """
    诊断板块，生成详细信息

    Args:
        score_data: 综合评分结果数据
        sector_type: 板块类型

    Returns:
        诊断结果字典
    """
    sector_name = score_data.get("sector_name", "")
    selection_level = score_data.get("selection_level", "neutral")
    score_breakdown = score_data.get("score_breakdown", {})
    history_days = score_data.get("history_days", 0)

    # 生成强度原因
    strength_reasons = _generate_strength_reasons(score_data)

    # 生成风险原因
    risk_reasons = _generate_risk_reasons(score_data)

    # 生成观察要点
    watch_points = _generate_watch_points(score_data)

    # 生成数据警告
    data_warnings = _generate_data_warnings(score_data, sector_type)

    # 生成综合诊断
    diagnosis_summary = _generate_diagnosis_summary(
        selection_level, strength_reasons, risk_reasons
    )

    return {
        "sector_name": sector_name,
        "sector_type": sector_type,
        "selection_level": selection_level,
        "diagnosis_summary": diagnosis_summary,
        "strength_reasons": strength_reasons,
        "risk_reasons": risk_reasons,
        "watch_points": watch_points,
        "data_warnings": data_warnings,
        "score_breakdown": score_breakdown,
        "history_days": history_days,
    }


def _generate_strength_reasons(score_data: Dict[str, Any]) -> List[str]:
    """
    生成强度原因列表
    """
    reasons = []
    score_breakdown = score_data.get("score_breakdown", {})
    radar_score = score_data.get("radar_score", 0)
    history_days = score_data.get("history_days", 0)

    # 日报雷达分
    if radar_score >= 70:
        reasons.append("日报雷达分较高")
    elif radar_score >= 50:
        reasons.append("日报雷达分中等")

    # 动量
    momentum = score_breakdown.get("momentum_component", 0)
    if momentum >= 15:
        reasons.append("近期涨幅靠前")
    elif momentum >= 10:
        reasons.append("近期小幅上涨")

    # 相对强度
    relative_strength = score_breakdown.get("relative_strength_component", 0)
    if relative_strength >= 12:
        reasons.append("相对行业中位数明显走强")
    elif relative_strength >= 8:
        reasons.append("相对行业中位数走强")

    # 持续性
    persistence = score_breakdown.get("persistence_component", 0)
    if persistence >= 12:
        reasons.append("上涨持续性强")
    elif persistence >= 8:
        reasons.append("上涨持续性一般")

    # 数据质量
    data_quality = score_breakdown.get("data_quality_component", 0)
    if data_quality >= 8:
        reasons.append("数据质量良好")
    elif data_quality >= 5:
        reasons.append("数据质量一般")

    return reasons


def _generate_risk_reasons(score_data: Dict[str, Any]) -> List[str]:
    """
    生成风险原因列表
    """
    reasons = []
    score_breakdown = score_data.get("score_breakdown", {})

    # 风险扣分
    risk_penalty = score_breakdown.get("risk_penalty", 0)
    if risk_penalty >= 15:
        reasons.append("风险扣分较高，存在明显风险")
    elif risk_penalty >= 10:
        reasons.append("存在一定风险")
    elif risk_penalty >= 5:
        reasons.append("风险可控")

    # 回撤
    drawdown = score_breakdown.get("drawdown_component", 0)
    if drawdown <= 3:
        reasons.append("回撤较大，注意仓位控制")
    elif drawdown <= 5:
        reasons.append("存在一定回撤")

    # 波动率
    volatility = score_breakdown.get("volatility_component", 0)
    if volatility <= 2:
        reasons.append("波动率较高")
    elif volatility <= 3:
        reasons.append("波动率中等")

    return reasons


def _generate_watch_points(score_data: Dict[str, Any]) -> List[str]:
    """
    生成观察要点列表
    """
    points = []
    selection_level = score_data.get("selection_level", "neutral")
    benchmark_mode = score_data.get("benchmark_mode", "sector_median")
    score_breakdown = score_data.get("score_breakdown", {})

    if selection_level in ["strong_watch", "watch"]:
        points.append("观察后续是否继续跑赢行业中位数")
        persistence = score_breakdown.get("persistence_component", 0)
        if persistence < 8:
            points.append("持续性待确认，关注后续表现")
        volatility = score_breakdown.get("volatility_component", 0)
        if volatility <= 3:
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


def _generate_data_warnings(
    score_data: Dict[str, Any],
    sector_type: str,
) -> List[str]:
    """
    生成数据警告列表
    """
    warnings = []
    history_days = score_data.get("history_days", 0)
    score_breakdown = score_data.get("score_breakdown", {})
    data_quality = score_breakdown.get("data_quality_component", 0)

    if history_days < 3:
        warnings.append(f"历史数据不足 ({history_days} 天)，评分可靠性降低")

    if sector_type == "concept":
        # 检查是否有涨跌幅数据警告
        score_data_warnings = score_data.get("data_warnings", [])
        for warning in score_data_warnings:
            if "涨跌幅" in warning:
                warnings.append(warning)
                break

    if history_days == 0:
        warnings.append("无历史数据，仅基于日报雷达分评分")

    if data_quality < 5:
        warnings.append("数据质量评分较低")

    return warnings


def _generate_diagnosis_summary(
    selection_level: str,
    strength_reasons: List[str],
    risk_reasons: List[str],
) -> str:
    """
    生成诊断摘要
    """
    if selection_level == "strong_watch":
        if not risk_reasons:
            return "板块表现优秀，风险可控，建议重点关注"
        else:
            return "板块表现优秀，但存在一定风险，建议关注核心成分股"
    elif selection_level == "watch":
        if not risk_reasons:
            return "板块表现良好，建议观察"
        else:
            return "板块表现良好，但需注意风险"
    elif selection_level == "neutral":
        return "板块表现中性，可作为备选观察"
    elif selection_level == "cooling":
        return "板块降温，建议谨慎观察"
    else:
        return "板块弱势，建议回避"
