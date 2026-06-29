"""
板块风险 Agent

量化风险汇总，计算风险扣分、风险等级和风险标志。
"""

from typing import Any, Dict, List, Tuple

from ...models import AgentOutput, AgentStatus, RiskLevel, SectorSnapshot
from ...scoring.risk_score import calculate_risk_penalty


def calculate_risk_assessment(sectors: List[SectorSnapshot]) -> AgentOutput:
    """
    计算风险评估

    Args:
        sectors: 板块快照列表

    Returns:
        风险评估结果 AgentOutput
    """
    assessments = []
    warnings = []

    for sector in sectors:
        try:
            penalty, risk_level, risk_flags, risk_reasons = calculate_risk_penalty(sector)
            assessments.append({
                "sector_id": sector.sector_id,
                "name": sector.name,
                "risk_penalty": penalty,
                "risk_level": risk_level.value,
                "risk_flags": risk_flags,
                "risk_reasons": risk_reasons,
            })

            if risk_level == RiskLevel.HIGH:
                warnings.append(f"板块 {sector.name} 风险等级高")
        except Exception as e:
            warnings.append(f"计算板块 {sector.name} 风险失败: {str(e)}")

    return AgentOutput(
        agent_id="sector_risk",
        status=AgentStatus.OK if not warnings else AgentStatus.DEGRADED,
        data={"assessments": assessments},
        warnings=warnings,
        data_sources=["fixture"],
        updated_at="",
        data_quality_score=85.0,
    )
