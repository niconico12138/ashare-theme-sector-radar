"""
板块轮动追踪器

计算轮动指标和分类。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..models import RiskLevel, SectorScore


@dataclass
class RotationResult:
    """轮动追踪结果"""
    industry_rotation: Dict[str, List[str]]
    concept_rotation: Dict[str, List[str]]
    industry_details: List[Dict[str, Any]]
    concept_details: List[Dict[str, Any]]
    comparison_status: str
    comparison_warnings: List[str]


def calculate_rotation(
    current_industry: List[SectorScore],
    current_concept: List[SectorScore],
    previous_data: Optional[Dict[str, Any]],
) -> RotationResult:
    """
    计算轮动指标

    Args:
        current_industry: 当前行业板块评分列表
        current_concept: 当前概念板块评分列表
        previous_data: 历史快照数据

    Returns:
        RotationResult 轮动追踪结果
    """
    comparison_warnings = []

    if previous_data is None:
        # 没有历史数据，标记为新条目
        comparison_status = "no_previous_data"
        comparison_warnings.append("未找到历史快照，所有板块标记为新晋")

        industry_details = _mark_all_as_new(current_industry)
        concept_details = _mark_all_as_new(current_concept)

        return RotationResult(
            industry_rotation=_empty_rotation(),
            concept_rotation=_empty_rotation(),
            industry_details=industry_details,
            concept_details=concept_details,
            comparison_status=comparison_status,
            comparison_warnings=comparison_warnings,
        )

    # 提取历史数据
    previous_industry = _extract_sectors_from_snapshot(previous_data, "industry_top")
    previous_concept = _extract_sectors_from_snapshot(previous_data, "concept_top")

    comparison_status = "ok"

    # 计算行业轮动
    industry_details, industry_rotation = _calculate_sector_rotation(
        current=current_industry,
        previous=previous_industry,
        sector_type="industry",
    )

    # 计算概念轮动
    concept_details, concept_rotation = _calculate_sector_rotation(
        current=current_concept,
        previous=previous_concept,
        sector_type="concept",
    )

    return RotationResult(
        industry_rotation=industry_rotation,
        concept_rotation=concept_rotation,
        industry_details=industry_details,
        concept_details=concept_details,
        comparison_status=comparison_status,
        comparison_warnings=comparison_warnings,
    )


def _extract_sectors_from_snapshot(
    snapshot: Dict[str, Any],
    key: str,
) -> List[Dict[str, Any]]:
    """从快照中提取板块数据"""
    return snapshot.get(key, [])


def _mark_all_as_new(sectors: List[SectorScore]) -> List[Dict[str, Any]]:
    """标记所有板块为新条目"""
    details = []
    for i, sector in enumerate(sectors):
        details.append({
            "sector_id": sector.sector_id,
            "name": sector.name,
            "type": sector.type.value,
            "current_rank": i + 1,
            "previous_rank": None,
            "rank_change": None,
            "previous_score": None,
            "score_change": None,
            "rotation_tags": ["new_entry"],
            "positive_score": sector.positive_score,
            "risk_penalty": sector.risk_penalty,
            "score": sector.score,
            "focus_level": sector.focus_level.value,
            "risk_level": sector.risk_level.value,
        })
    return details


def _empty_rotation() -> Dict[str, List[str]]:
    """空轮动分类"""
    return {
        "new_entries": [],
        "dropped_out": [],
        "rising_fast": [],
        "persistent_strength": [],
        "risk_up": [],
    }


def _calculate_sector_rotation(
    current: List[SectorScore],
    previous: List[Dict[str, Any]],
    sector_type: str,
) -> tuple:
    """
    计算板块轮动

    Returns:
        (details, rotation_summary)
    """
    # 构建历史排名和分数映射
    prev_rank_map = {}
    prev_score_map = {}
    prev_risk_map = {}
    prev_names = set()

    for item in previous:
        name = item.get("name", "")
        prev_names.add(name)
        # 历史排名基于列表位置
        rank = previous.index(item) + 1
        prev_rank_map[name] = rank
        prev_score_map[name] = item.get("score", 0.0)
        prev_risk_map[name] = item.get("risk_penalty", 0.0)

    # 当前 Top N 名称集合
    current_names = {s.name for s in current}

    # 计算轮动指标
    details = []
    rotation_summary = _empty_rotation()

    for i, sector in enumerate(current):
        current_rank = i + 1
        name = sector.name

        # 查找历史数据
        previous_rank = prev_rank_map.get(name)
        previous_score = prev_score_map.get(name)
        previous_risk = prev_risk_map.get(name)

        # 计算变化
        if previous_rank is not None:
            rank_change = previous_rank - current_rank
        else:
            rank_change = None

        if previous_score is not None:
            score_change = sector.score - previous_score
        else:
            score_change = None

        # 计算风险变化
        risk_change = None
        if previous_risk is not None:
            risk_change = sector.risk_penalty - previous_risk

        # 识别轮动标签
        rotation_tags = _identify_rotation_tags(
            name=name,
            current_rank=current_rank,
            previous_rank=previous_rank,
            rank_change=rank_change,
            score_change=score_change,
            risk_change=risk_change,
            current_score=sector.score,
            previous_score=previous_score,
            risk_level=sector.risk_level,
            prev_risk_level=_get_previous_risk_level(previous, name),
        )

        # 分类
        if "new_entry" in rotation_tags:
            rotation_summary["new_entries"].append(name)
        if "rising_fast" in rotation_tags:
            rotation_summary["rising_fast"].append(name)
        if "persistent_strength" in rotation_tags:
            rotation_summary["persistent_strength"].append(name)
        if "risk_up" in rotation_tags:
            rotation_summary["risk_up"].append(name)

        details.append({
            "sector_id": sector.sector_id,
            "name": name,
            "type": sector.type.value,
            "current_rank": current_rank,
            "previous_rank": previous_rank,
            "rank_change": rank_change,
            "previous_score": previous_score,
            "score_change": round(score_change, 2) if score_change is not None else None,
            "rotation_tags": rotation_tags,
            "positive_score": sector.positive_score,
            "risk_penalty": sector.risk_penalty,
            "score": sector.score,
            "focus_level": sector.focus_level.value,
            "risk_level": sector.risk_level.value,
        })

    # 识别掉出的板块
    dropped_out = prev_names - current_names
    rotation_summary["dropped_out"] = list(dropped_out)

    return details, rotation_summary


def _get_previous_risk_level(
    previous: List[Dict[str, Any]],
    name: str,
) -> Optional[RiskLevel]:
    """获取历史风险等级"""
    for item in previous:
        if item.get("name") == name:
            risk_level_str = item.get("risk_level", "low")
            try:
                return RiskLevel(risk_level_str)
            except ValueError:
                return RiskLevel.LOW
    return None


def _identify_rotation_tags(
    name: str,
    current_rank: int,
    previous_rank: Optional[int],
    rank_change: Optional[int],
    score_change: Optional[float],
    risk_change: Optional[float],
    current_score: float,
    previous_score: Optional[float],
    risk_level: RiskLevel,
    prev_risk_level: Optional[RiskLevel],
) -> List[str]:
    """识别轮动标签"""
    tags = []

    # new_entry
    if previous_rank is None:
        tags.append("new_entry")
        return tags  # 新条目直接返回

    # rising_fast
    if (rank_change is not None and rank_change >= 3) or \
       (score_change is not None and score_change >= 8):
        tags.append("rising_fast")

    # falling
    if rank_change is not None and rank_change <= -3:
        tags.append("falling")

    # persistent_strength
    if previous_rank is not None and current_score >= 75:
        tags.append("persistent_strength")

    # risk_up
    if risk_change is not None and risk_change >= 5:
        tags.append("risk_up")
    elif prev_risk_level is not None and _risk_level_order(risk_level) > _risk_level_order(prev_risk_level):
        tags.append("risk_up")

    # risk_down
    if risk_change is not None and risk_change <= -5:
        tags.append("risk_down")
    elif prev_risk_level is not None and _risk_level_order(risk_level) < _risk_level_order(prev_risk_level):
        tags.append("risk_down")

    # score_up
    if score_change is not None and score_change >= 5:
        tags.append("score_up")

    # score_down
    if score_change is not None and score_change <= -5:
        tags.append("score_down")

    return tags


def _risk_level_order(level: RiskLevel) -> int:
    """风险等级排序"""
    order = {
        RiskLevel.LOW: 0,
        RiskLevel.MEDIUM: 1,
        RiskLevel.HIGH: 2,
    }
    return order.get(level, 0)
