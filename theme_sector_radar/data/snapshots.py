"""
快照数据处理

提供快照数据的处理和转换功能。
"""

from typing import Any, Dict, List, Optional

from ..models import ConstituentSnapshot, SectorSnapshot, SectorType


def normalize_sector_data(
    raw_data: Dict[str, Any],
    sector_type: SectorType,
    constituents: List[Dict[str, Any]] = None
) -> SectorSnapshot:
    """
    标准化板块数据

    支持多种字段名别名，包括：
    - 英文字段名 (sector_id, name, price_change_pct, etc.)
    - 中文字段名 (板块代码, 板块名称, 涨跌幅, etc.)
    - AkShare 常用字段名

    Args:
        raw_data: 原始板块数据
        sector_type: 板块类型
        constituents: 成分股数据

    Returns:
        标准化的板块快照
    """
    if constituents is None:
        constituents = []

    # 解析成分股
    parsed_constituents = [
        normalize_constituent_data(c)
        for c in constituents
    ]

    # 提取板块 ID
    sector_id = (
        raw_data.get("sector_id") or
        raw_data.get("board_code") or
        raw_data.get("板块代码") or
        raw_data.get("code") or
        ""
    )

    # 提取板块名称
    name = (
        raw_data.get("name") or
        raw_data.get("board_name") or
        raw_data.get("板块名称") or
        ""
    )

    # 提取涨跌幅
    price_change_pct = _safe_float(
        raw_data.get("price_change_pct") or
        raw_data.get("change_pct") or
        raw_data.get("涨跌幅") or
        0.0
    )

    # 提取成交额
    turnover = _safe_float(
        raw_data.get("turnover") or
        raw_data.get("amount") or
        raw_data.get("成交额") or
        0.0
    )

    # 提取主力净流入
    main_net_inflow = _safe_float(
        raw_data.get("main_net_inflow") or
        raw_data.get("net_inflow") or
        raw_data.get("主力净流入-净额") or
        0.0
    )

    # 提取数据来源
    data_sources = raw_data.get("data_sources", [])

    # 提取更新时间
    updated_at = raw_data.get("updated_at", "")

    # 提取数据质量分
    data_quality_score = _safe_float(raw_data.get("data_quality_score", 0.0))

    return SectorSnapshot(
        sector_id=str(sector_id),
        name=str(name),
        type=sector_type,
        price_change_pct=price_change_pct,
        turnover=turnover,
        main_net_inflow=main_net_inflow,
        constituents=parsed_constituents,
        data_sources=data_sources,
        updated_at=updated_at,
        data_quality_score=data_quality_score,
    )


def normalize_constituent_data(raw_data: Dict[str, Any]) -> ConstituentSnapshot:
    """
    标准化成分股数据

    支持多种字段名别名。
    """
    code = (
        raw_data.get("code") or
        raw_data.get("symbol") or
        raw_data.get("代码") or
        ""
    )

    name = (
        raw_data.get("name") or
        raw_data.get("stock_name") or
        raw_data.get("名称") or
        ""
    )

    change_pct = _safe_float(
        raw_data.get("change_pct") or
        raw_data.get("pct_change") or
        raw_data.get("涨跌幅") or
        0.0
    )

    turnover = _safe_float(
        raw_data.get("turnover") or
        raw_data.get("amount") or
        raw_data.get("成交额") or
        0.0
    )

    is_core = raw_data.get("is_core", False)

    return ConstituentSnapshot(
        code=str(code),
        name=str(name),
        change_pct=change_pct,
        turnover=turnover,
        is_core=bool(is_core),
    )


def _safe_float(value: Any) -> float:
    """安全转换为浮点数"""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def calculate_data_quality_score(
    sector: SectorSnapshot,
    has_flow_data: bool = True
) -> float:
    """
    计算数据质量分

    Args:
        sector: 板块快照
        has_flow_data: 是否有资金流数据

    Returns:
        数据质量分 (0-100)
    """
    score = 50.0  # 基础分

    # 数据源数量
    source_count = len(sector.data_sources)
    if source_count >= 3:
        score += 20.0
    elif source_count >= 2:
        score += 15.0
    elif source_count >= 1:
        score += 10.0

    # 成分股数量
    constituent_count = len(sector.constituents)
    if constituent_count >= 10:
        score += 15.0
    elif constituent_count >= 5:
        score += 10.0
    elif constituent_count >= 1:
        score += 5.0

    # 资金流数据
    if has_flow_data:
        score += 10.0

    # 更新时间
    if sector.updated_at:
        score += 5.0

    return min(score, 100.0)


def merge_sector_data(
    sectors: List[SectorSnapshot],
    key: str = "sector_id"
) -> Dict[str, SectorSnapshot]:
    """
    合并板块数据

    Args:
        sectors: 板块快照列表
        key: 合并键

    Returns:
        合并后的字典
    """
    result = {}
    for sector in sectors:
        sector_key = getattr(sector, key)
        result[sector_key] = sector
    return result
