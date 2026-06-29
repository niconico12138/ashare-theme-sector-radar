"""
板块覆盖率 Agent

计算每个板块的成分股覆盖率。
"""

from typing import Any, Dict, List

from ...models import AgentOutput, AgentStatus, SectorSnapshot


def calculate_sector_coverage(sectors: List[SectorSnapshot]) -> AgentOutput:
    """
    计算板块覆盖率

    Args:
        sectors: 板块快照列表

    Returns:
        覆盖率结果 AgentOutput
    """
    coverage_data = {}
    warnings = []

    for sector in sectors:
        constituents = sector.constituents
        total = len(constituents)

        if total == 0:
            coverage_data[sector.sector_id] = {
                "total_constituents": 0,
                "available_quotes": 0,
                "valid_change_pct": 0,
                "core_count": 0,
                "coverage_rate": 0.0,
            }
            continue

        available_quotes = sum(1 for c in constituents if c.turnover > 0)
        valid_change_pct = sum(1 for c in constituents if c.change_pct != 0)
        core_count = sum(1 for c in constituents if c.is_core)

        coverage_rate = (available_quotes / total * 100) if total > 0 else 0

        coverage_data[sector.sector_id] = {
            "total_constituents": total,
            "available_quotes": available_quotes,
            "valid_change_pct": valid_change_pct,
            "core_count": core_count,
            "coverage_rate": coverage_rate,
        }

        if coverage_rate < 50:
            warnings.append(f"板块 {sector.name} 覆盖率偏低 ({coverage_rate:.0f}%)")

    return AgentOutput(
        agent_id="sector_coverage",
        status=AgentStatus.OK if not warnings else AgentStatus.DEGRADED,
        data={"coverage": coverage_data},
        warnings=warnings,
        data_sources=["fixture"],
        updated_at="",
        data_quality_score=85.0 if not warnings else 65.0,
    )
