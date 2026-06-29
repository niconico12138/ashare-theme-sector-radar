"""
板块回避 Agent

关注等级降级解释器。
"""

from typing import Any, Dict, List

from ...models import (
    AgentOutput,
    AgentStatus,
    FocusLevel,
    RiskLevel,
    SectorScore,
)
from ...scoring.focus_level import calculate_focus_level, explain_downgrade


def calculate_avoidance_explanation(
    sector_scores: List[SectorScore]
) -> AgentOutput:
    """
    计算回避解释

    Args:
        sector_scores: 板块评分列表

    Returns:
        回避解释结果 AgentOutput
    """
    explanations = []
    warnings = []

    for score in sector_scores:
        try:
            # 计算关注等级
            focus_level, downgrade_reasons = calculate_focus_level(
                positive_score=score.positive_score,
                risk_penalty=score.risk_penalty,
                risk_level=score.risk_level,
                data_quality_score=score.data_quality_score,
            )

            # 生成降级解释
            if focus_level in [FocusLevel.CORE_ONLY, FocusLevel.CAUTION, FocusLevel.AVOID]:
                additional_reasons = explain_downgrade(
                    focus_level=focus_level,
                    positive_score=score.positive_score,
                    risk_penalty=score.risk_penalty,
                    risk_level=score.risk_level,
                    risk_flags=score.risk_flags,
                    data_quality_score=score.data_quality_score,
                )
                downgrade_reasons.extend(additional_reasons)

            explanations.append({
                "sector_id": score.sector_id,
                "name": score.name,
                "focus_level": focus_level.value,
                "downgrade_reasons": downgrade_reasons,
            })
        except Exception as e:
            warnings.append(f"计算板块 {score.name} 回避解释失败: {str(e)}")

    return AgentOutput(
        agent_id="sector_avoidance",
        status=AgentStatus.OK if not warnings else AgentStatus.DEGRADED,
        data={"explanations": explanations},
        warnings=warnings,
        data_sources=["fixture"],
        updated_at="",
        data_quality_score=85.0,
    )
