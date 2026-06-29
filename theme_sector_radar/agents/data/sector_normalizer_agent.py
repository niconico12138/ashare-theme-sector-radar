"""
板块标准化 Agent

将不同数据源字段统一成内部契约。
"""

from typing import Any, Dict, List

from ...data.snapshots import normalize_sector_data as _normalize_sector_data
from ...models import AgentOutput, AgentStatus, SectorSnapshot, SectorType


def normalize_sector_data(
    raw_sectors: List[Dict[str, Any]],
    sector_type: SectorType,
    all_constituents: Dict[str, List[Dict[str, Any]]] = None
) -> AgentOutput:
    """
    标准化板块数据

    Args:
        raw_sectors: 原始板块数据列表
        sector_type: 板块类型
        all_constituents: 所有板块的成分股数据

    Returns:
        标准化后的 AgentOutput
    """
    if all_constituents is None:
        all_constituents = {}

    normalized_sectors = []
    warnings = []

    for raw_sector in raw_sectors:
        sector_id = raw_sector.get("sector_id", raw_sector.get("board_code", ""))
        constituents = all_constituents.get(sector_id, [])

        try:
            normalized = _normalize_sector_data(raw_sector, sector_type, constituents)
            normalized_sectors.append(normalized)
        except Exception as e:
            warnings.append(f"标准化板块 {sector_id} 失败: {str(e)}")

    return AgentOutput(
        agent_id="sector_normalizer",
        status=AgentStatus.OK if not warnings else AgentStatus.DEGRADED,
        data={"sectors": [s.model_dump() for s in normalized_sectors]},
        warnings=warnings,
        data_sources=["fixture"],
        updated_at="",
        data_quality_score=80.0 if not warnings else 60.0,
    )
