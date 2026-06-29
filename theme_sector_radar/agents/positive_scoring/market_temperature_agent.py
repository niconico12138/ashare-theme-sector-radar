"""
市场温度 Agent

计算市场短线温度。
"""

from typing import Any, Dict

from ...models import AgentOutput, AgentStatus, MarketTemperature


def calculate_market_temperature(market_data: Dict[str, Any]) -> AgentOutput:
    """
    计算市场温度

    Args:
        market_data: 市场概览数据

    Returns:
        温度计算结果 AgentOutput
    """
    advance_count = market_data.get("advance_count", 0)
    decline_count = market_data.get("decline_count", 0)
    limit_up_count = market_data.get("limit_up_count", 0)
    limit_down_count = market_data.get("limit_down_count", 0)
    total_turnover = market_data.get("total_turnover", 0)
    index_change_pct = market_data.get("index_change_pct", 0)

    # 计算温度分 (0-100)
    temperature_score = 50.0  # 基础温度

    # 涨跌家数影响
    total_stocks = advance_count + decline_count
    if total_stocks > 0:
        advance_ratio = advance_count / total_stocks
        if advance_ratio >= 0.7:
            temperature_score += 15.0
        elif advance_ratio >= 0.6:
            temperature_score += 10.0
        elif advance_ratio <= 0.3:
            temperature_score -= 15.0
        elif advance_ratio <= 0.4:
            temperature_score -= 10.0

    # 涨停/跌停影响
    if limit_up_count >= 50:
        temperature_score += 10.0
    elif limit_up_count >= 30:
        temperature_score += 5.0

    if limit_down_count >= 30:
        temperature_score -= 10.0
    elif limit_down_count >= 15:
        temperature_score -= 5.0

    # 指数涨跌幅影响
    if index_change_pct >= 2:
        temperature_score += 10.0
    elif index_change_pct >= 1:
        temperature_score += 5.0
    elif index_change_pct <= -2:
        temperature_score -= 10.0
    elif index_change_pct <= -1:
        temperature_score -= 5.0

    # 限制范围
    temperature_score = max(0.0, min(100.0, temperature_score))

    # 确定温度标签
    if temperature_score >= 70:
        label = "hot"
        description = "市场情绪偏热，短线机会较多但需注意追高风险"
    elif temperature_score >= 55:
        label = "warm"
        description = "市场情绪偏暖，可适度参与强势板块"
    elif temperature_score >= 45:
        label = "neutral"
        description = "市场情绪中性，建议精选板块和个股"
    elif temperature_score >= 30:
        label = "cool"
        description = "市场情绪偏冷，建议控制仓位"
    else:
        label = "cold"
        description = "市场情绪冰冷，建议观望为主"

    temperature = MarketTemperature(
        score=temperature_score,
        label=label,
        description=description,
        advance_count=advance_count,
        decline_count=decline_count,
        limit_up_count=limit_up_count,
        limit_down_count=limit_down_count,
    )

    return AgentOutput(
        agent_id="market_temperature",
        status=AgentStatus.OK,
        data=temperature.model_dump(),
        warnings=[],
        data_sources=["fixture"],
        updated_at="",
        data_quality_score=85.0,
    )
