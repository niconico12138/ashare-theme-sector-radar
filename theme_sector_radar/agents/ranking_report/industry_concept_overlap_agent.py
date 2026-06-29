"""
行业概念共振 Agent

计算行业与概念板块的共振。
"""

from typing import Any, Dict, List

from ...models import (
    AgentOutput,
    AgentStatus,
    FlowAlignment,
    FocusLevel,
    ResonanceResult,
    SectorScore,
    SectorSnapshot,
)


def calculate_overlap_resonance(
    industry_sectors: List[SectorSnapshot],
    concept_sectors: List[SectorSnapshot],
    industry_top: List[SectorScore],
    concept_top: List[SectorScore],
    top_n: int = 10
) -> AgentOutput:
    """
    计算行业与概念共振

    Args:
        industry_sectors: 行业板块快照列表
        concept_sectors: 概念板块快照列表
        industry_top: 行业 Top N 评分
        concept_top: 概念 Top N 评分
        top_n: Top N 数量

    Returns:
        共振结果 AgentOutput
    """
    resonance_results = []
    warnings = []

    # 获取 Top N 的行业和概念
    top_industry_ids = {s.sector_id for s in industry_sectors[:top_n]}
    top_concept_ids = {s.sector_id for s in concept_sectors[:top_n]}

    # 构建板块字典
    industry_dict = {s.sector_id: s for s in industry_sectors}
    concept_dict = {s.sector_id: s for s in concept_sectors}

    # 构建评分字典
    industry_score_dict = {s.sector_id: s for s in industry_top}
    concept_score_dict = {s.sector_id: s for s in concept_top}

    # 检查所有行业-概念组合
    for industry in industry_sectors:
        for concept in concept_sectors:
            try:
                # 计算成分股重合
                industry_constituents = {c.code for c in industry.constituents}
                concept_constituents = {c.code for c in concept.constituents}

                overlap = industry_constituents & concept_constituents
                overlap_count = len(overlap)

                if overlap_count == 0:
                    continue

                # 计算共同核心成分股
                industry_core = {c.code for c in industry.constituents if c.is_core}
                concept_core = {c.code for c in concept.constituents if c.is_core}
                common_core = industry_core & concept_core
                common_core_count = len(common_core)

                # 双强确认
                both_top_n = (
                    industry.sector_id in top_industry_ids and
                    concept.sector_id in top_concept_ids
                )

                # 资金流方向
                industry_inflow = industry.main_net_inflow > 0
                concept_inflow = concept.main_net_inflow > 0

                if industry_inflow and concept_inflow:
                    flow_alignment = FlowAlignment.BOTH_INFLOW
                elif not industry_inflow and not concept_inflow:
                    flow_alignment = FlowAlignment.BOTH_OUTFLOW
                elif industry_inflow:
                    flow_alignment = FlowAlignment.INDUSTRY_INFLOW
                else:
                    flow_alignment = FlowAlignment.CONCEPT_INFLOW

                # 计算共振分
                resonance_score = _calculate_resonance_score(
                    overlap_count=overlap_count,
                    industry_constituent_count=len(industry.constituents),
                    concept_constituent_count=len(concept.constituents),
                    common_core_count=common_core_count,
                    both_top_n=both_top_n,
                    flow_alignment=flow_alignment,
                )

                # 确定关注等级
                focus_level = _determine_resonance_focus_level(
                    resonance_score=resonance_score,
                    both_top_n=both_top_n,
                    flow_alignment=flow_alignment,
                )

                # 获取重合成分股详情
                overlap_constituents = [
                    c for c in industry.constituents if c.code in overlap
                ]

                resonance_results.append(ResonanceResult(
                    industry=industry.name,
                    concept=concept.name,
                    resonance_score=resonance_score,
                    overlap_constituent_count=overlap_count,
                    common_core_count=common_core_count,
                    flow_alignment=flow_alignment,
                    both_top_n=both_top_n,
                    focus_level=focus_level,
                    constituents=overlap_constituents[:10],  # 限制数量
                ))

            except Exception as e:
                warnings.append(
                    f"计算共振 {industry.name}-{concept.name} 失败: {str(e)}"
                )

    # 按共振分排序
    resonance_results.sort(key=lambda x: x.resonance_score, reverse=True)

    return AgentOutput(
        agent_id="industry_concept_overlap",
        status=AgentStatus.OK if not warnings else AgentStatus.DEGRADED,
        data={"resonance": [r.model_dump() for r in resonance_results]},
        warnings=warnings,
        data_sources=["fixture"],
        updated_at="",
        data_quality_score=85.0,
    )


def _calculate_resonance_score(
    overlap_count: int,
    industry_constituent_count: int,
    concept_constituent_count: int,
    common_core_count: int,
    both_top_n: bool,
    flow_alignment: FlowAlignment,
) -> float:
    """计算共振分"""
    score = 0.0

    # 成分股重合得分 (0-30)
    if industry_constituent_count > 0 and concept_constituent_count > 0:
        overlap_ratio = overlap_count / min(
            industry_constituent_count,
            concept_constituent_count
        )
        score += overlap_ratio * 30.0

    # 双强确认得分 (0-25)
    if both_top_n:
        score += 25.0

    # 资金流一致得分 (0-25)
    if flow_alignment == FlowAlignment.BOTH_INFLOW:
        score += 25.0
    elif flow_alignment in [FlowAlignment.INDUSTRY_INFLOW, FlowAlignment.CONCEPT_INFLOW]:
        score += 15.0

    # 共同核心成分股得分 (0-20)
    if common_core_count >= 3:
        score += 20.0
    elif common_core_count >= 2:
        score += 15.0
    elif common_core_count >= 1:
        score += 10.0

    return min(score, 100.0)


def _determine_resonance_focus_level(
    resonance_score: float,
    both_top_n: bool,
    flow_alignment: FlowAlignment,
) -> FocusLevel:
    """确定共振关注等级"""
    if resonance_score >= 70 and both_top_n and flow_alignment == FlowAlignment.BOTH_INFLOW:
        return FocusLevel.FOCUS
    elif resonance_score >= 50:
        return FocusLevel.WATCH
    elif resonance_score >= 30:
        return FocusLevel.CAUTION
    else:
        return FocusLevel.AVOID
