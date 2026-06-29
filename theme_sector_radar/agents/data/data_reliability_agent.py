"""
数据可靠性 Agent

计算数据质量分，评估数据可靠性。
"""

from typing import Any, Dict, List

from ...models import AgentOutput, AgentStatus, SectorSnapshot


def calculate_data_reliability(sectors: List[SectorSnapshot]) -> AgentOutput:
    """
    计算数据可靠性

    Args:
        sectors: 板块快照列表

    Returns:
        可靠性评估 AgentOutput
    """
    reliability_data = {
        "overall_score": 0.0,
        "sector_scores": {},
        "issues": [],
    }
    warnings = []

    total_score = 0.0
    sector_count = len(sectors)

    for sector in sectors:
        score = 100.0
        issues = []

        # 数据源数量检查
        source_count = len(sector.data_sources)
        if source_count < 2:
            score -= 15
            issues.append(f"数据源不足 ({source_count}个)")

        # 成分股覆盖率检查
        constituent_count = len(sector.constituents)
        if constituent_count == 0:
            score -= 20
            issues.append("无成分股数据")
        elif constituent_count < 5:
            score -= 10
            issues.append(f"成分股数量偏少 ({constituent_count})")

        # 资金流数据检查
        if sector.main_net_inflow == 0 and constituent_count > 0:
            score -= 10
            issues.append("缺少资金流数据")

        # 数据新鲜度检查 (简化处理)
        if not sector.updated_at:
            score -= 5
            issues.append("缺少更新时间")

        # 限制最低分
        score = max(score, 0.0)

        reliability_data["sector_scores"][sector.sector_id] = {
            "score": score,
            "issues": issues,
        }

        total_score += score

        if issues:
            warnings.append(f"板块 {sector.name} 数据质量问题: {'; '.join(issues)}")

    # 计算平均分
    if sector_count > 0:
        reliability_data["overall_score"] = total_score / sector_count

    reliability_data["issues"] = warnings

    return AgentOutput(
        agent_id="data_reliability",
        status=AgentStatus.OK if not warnings else AgentStatus.DEGRADED,
        data=reliability_data,
        warnings=warnings,
        data_sources=["fixture"],
        updated_at="",
        data_quality_score=reliability_data["overall_score"],
    )
