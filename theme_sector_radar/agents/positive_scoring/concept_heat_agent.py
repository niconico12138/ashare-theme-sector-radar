"""
概念热度 Agent

计算概念板块热度评分。
"""

from typing import Any, Dict, List

from ...models import AgentOutput, AgentStatus, SectorSnapshot
from ...scoring.concept_score import calculate_concept_phase, calculate_concept_score


def calculate_concept_heat(sectors: List[SectorSnapshot]) -> AgentOutput:
    """
    计算概念板块热度评分

    Args:
        sectors: 概念板块快照列表

    Returns:
        评分结果 AgentOutput
    """
    scores = []
    warnings = []

    for sector in sectors:
        try:
            # 计算阶段
            phase = calculate_concept_phase(sector)
            # 计算评分
            score = calculate_concept_score(sector, phase)
            scores.append({
                "sector_id": sector.sector_id,
                "name": sector.name,
                "positive_score": score,
                "phase": phase.value,
            })
        except Exception as e:
            warnings.append(f"计算概念 {sector.name} 评分失败: {str(e)}")

    # 按分数排序
    scores.sort(key=lambda x: x["positive_score"], reverse=True)

    return AgentOutput(
        agent_id="concept_heat",
        status=AgentStatus.OK if not warnings else AgentStatus.DEGRADED,
        data={"scores": scores},
        warnings=warnings,
        data_sources=["fixture"],
        updated_at="",
        data_quality_score=85.0,
    )
