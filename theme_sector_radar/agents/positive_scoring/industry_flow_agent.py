"""
行业流向 Agent

计算行业板块正向评分。
"""

from typing import Any, Dict, List

from ...models import AgentOutput, AgentStatus, SectorSnapshot
from ...scoring.industry_score import calculate_industry_score


def calculate_industry_flow(
    sectors: List[SectorSnapshot],
    market_temperature: float = 50.0
) -> AgentOutput:
    """
    计算行业板块正向评分

    Args:
        sectors: 行业板块快照列表
        market_temperature: 市场温度

    Returns:
        评分结果 AgentOutput
    """
    scores = []
    warnings = []

    for sector in sectors:
        try:
            score = calculate_industry_score(sector, market_temperature)
            scores.append({
                "sector_id": sector.sector_id,
                "name": sector.name,
                "positive_score": score,
            })
        except Exception as e:
            warnings.append(f"计算行业 {sector.name} 评分失败: {str(e)}")

    # 按分数排序
    scores.sort(key=lambda x: x["positive_score"], reverse=True)

    return AgentOutput(
        agent_id="industry_flow",
        status=AgentStatus.OK if not warnings else AgentStatus.DEGRADED,
        data={"scores": scores},
        warnings=warnings,
        data_sources=["fixture"],
        updated_at="",
        data_quality_score=85.0,
    )
