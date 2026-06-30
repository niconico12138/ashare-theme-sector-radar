"""
板块排名 Agent

生成行业 Top N、概念 Top N、共振 Top N。
"""

from typing import Any, Dict, List

from ...models import (
    AgentOutput,
    AgentStatus,
    ConceptPhase,
    FocusLevel,
    RiskLevel,
    SectorScore,
    SectorSnapshot,
)
from ...scoring.concept_score import calculate_concept_phase, calculate_concept_score_breakdown
from ...scoring.focus_level import calculate_focus_level, explain_downgrade, generate_watch_points
from ...scoring.industry_score import calculate_industry_score_breakdown
from ...scoring.risk_score import calculate_risk_penalty, calculate_risk_breakdown


def generate_sector_ranking(
    industry_sectors: List[SectorSnapshot],
    concept_sectors: List[SectorSnapshot],
    market_temperature: float = 50.0,
    top_n: int = 10
) -> AgentOutput:
    """
    生成板块排名

    Args:
        industry_sectors: 行业板块快照列表
        concept_sectors: 概念板块快照列表
        market_temperature: 市场温度
        top_n: Top N 数量

    Returns:
        排名结果 AgentOutput
    """
    industry_scores = []
    concept_scores = []
    warnings = []

    # 计算行业评分
    for sector in industry_sectors:
        try:
            # 计算评分 breakdown
            score_breakdown = calculate_industry_score_breakdown(sector, market_temperature)
            positive_score = score_breakdown["positive_score"]

            # 计算风险 breakdown（risk_penalty 为正数）
            risk_breakdown = calculate_risk_breakdown(sector)
            risk_penalty = risk_breakdown["total_penalty"]  # 正数
            risk_level = risk_breakdown["risk_level"]
            risk_flags = risk_breakdown["risk_flags"]

            # 计算最终分数: final_score = positive_score - risk_penalty
            final_score = positive_score - risk_penalty

            score = SectorScore(
                sector_id=sector.sector_id,
                name=sector.name,
                type=sector.type,
                score=final_score,
                positive_score=positive_score,
                risk_penalty=risk_penalty,  # 正数
                risk_level=risk_level,
                risk_flags=risk_flags,
                constituents=sector.constituents,
                data_sources=sector.data_sources,
                updated_at=sector.updated_at,
                data_quality_score=sector.data_quality_score,
                score_breakdown={
                    **score_breakdown,
                    "risk_penalty": round(risk_penalty, 2),  # 正数
                    "final_score": round(final_score, 2),
                    "risk_breakdown": risk_breakdown,
                },
            )

            # 计算关注等级
            focus_level, downgrade_reasons = calculate_focus_level(
                positive_score=positive_score,
                risk_penalty=risk_penalty,
                risk_level=risk_level,
                data_quality_score=sector.data_quality_score,
            )
            score.focus_level = focus_level
            score.downgrade_reasons = downgrade_reasons

            # 生成观察要点
            score.watch_points = generate_watch_points(
                focus_level=focus_level,
                score_breakdown=score_breakdown,
                risk_breakdown=risk_breakdown,
            )

            industry_scores.append(score)
        except Exception as e:
            warnings.append(f"计算行业 {sector.name} 排名失败: {str(e)}")

    # 计算概念评分
    for sector in concept_sectors:
        try:
            # 计算阶段和评分 breakdown
            phase = calculate_concept_phase(sector)
            score_breakdown = calculate_concept_score_breakdown(sector, phase)
            positive_score = score_breakdown["positive_score"]

            # 计算风险 breakdown（risk_penalty 为正数）
            risk_breakdown = calculate_risk_breakdown(sector)
            risk_penalty = risk_breakdown["total_penalty"]  # 正数
            risk_level = risk_breakdown["risk_level"]
            risk_flags = risk_breakdown["risk_flags"]

            # 计算最终分数: final_score = positive_score - risk_penalty
            final_score = positive_score - risk_penalty

            score = SectorScore(
                sector_id=sector.sector_id,
                name=sector.name,
                type=sector.type,
                score=final_score,
                positive_score=positive_score,
                risk_penalty=risk_penalty,  # 正数
                phase=phase,
                risk_level=risk_level,
                risk_flags=risk_flags,
                constituents=sector.constituents,
                data_sources=sector.data_sources,
                updated_at=sector.updated_at,
                data_quality_score=sector.data_quality_score,
                score_breakdown={
                    **score_breakdown,
                    "risk_penalty": round(risk_penalty, 2),  # 正数
                    "final_score": round(final_score, 2),
                    "risk_breakdown": risk_breakdown,
                },
            )

            # 计算关注等级
            focus_level, downgrade_reasons = calculate_focus_level(
                positive_score=positive_score,
                risk_penalty=risk_penalty,
                risk_level=risk_level,
                data_quality_score=sector.data_quality_score,
                price_change_available=sector.price_change_available,
            )
            score.focus_level = focus_level
            score.downgrade_reasons = downgrade_reasons

            # 生成观察要点
            score.watch_points = generate_watch_points(
                focus_level=focus_level,
                score_breakdown=score_breakdown,
                risk_breakdown=risk_breakdown,
            )

            concept_scores.append(score)
        except Exception as e:
            warnings.append(f"计算概念 {sector.name} 排名失败: {str(e)}")

    # 排序
    industry_scores.sort(key=lambda x: x.score, reverse=True)
    concept_scores.sort(key=lambda x: x.score, reverse=True)

    return AgentOutput(
        agent_id="sector_ranking",
        status=AgentStatus.OK if not warnings else AgentStatus.DEGRADED,
        data={
            "industry_top": [s.model_dump() for s in industry_scores[:top_n]],
            "concept_top": [s.model_dump() for s in concept_scores[:top_n]],
        },
        warnings=warnings,
        data_sources=["fixture"],
        updated_at="",
        data_quality_score=85.0,
    )
