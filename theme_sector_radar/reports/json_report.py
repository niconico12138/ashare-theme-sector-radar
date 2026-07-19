"""
JSON 报告生成

生成符合契约的 JSON 报告。
"""

import json
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List

from ..models import (
    MarketTemperature,
    RadarReport,
    ResonanceResult,
    SectorScore,
)


def generate_json_report(
    as_of_date: str,
    market_temperature: MarketTemperature,
    industry_top: List[SectorScore],
    concept_top: List[SectorScore],
    overlap: List[ResonanceResult],
    data_sources: List[str] = None,
    data_quality_score: float = 85.0,
    status: str = "ok",
    cache_info: dict = None,
    fund_flow_coverage: dict = None,
    constituent_coverage: dict = None,
    industry_count: int = 0,
    concept_count: int = 0,
    rotation_summary: dict = None,
    comparison: dict = None,
    run_mode: str = "normal",
    provider: str = "fixture",
    offline_fixture: bool = False,
    fixture_profile: str = None,
    data_source_mode: str = "fixture",
    report_dir: str = "",
    generated_by_command: str = "",
    provider_status=None,
    warnings: List[str] = None,
    industry_three_layer_shadow_summary: dict = None,
) -> Dict[str, Any]:
    """
    生成 JSON 报告

    Args:
        as_of_date: 分析日期
        market_temperature: 市场温度
        industry_top: 行业 Top N
        concept_top: 概念 Top N
        overlap: 共振列表
        data_sources: 数据来源
        data_quality_score: 数据质量分
        status: 报告状态 (ok/degraded/failed)
        cache_info: 缓存信息
        fund_flow_coverage: 资金流覆盖率
        constituent_coverage: 成分股覆盖率
        industry_count: 行业板块数量
        concept_count: 概念板块数量
        rotation_summary: 轮动摘要
        comparison: 比较信息
        run_mode: 运行模式
        provider: 数据提供者
        offline_fixture: 是否离线 fixture
        fixture_profile: fixture profile
        data_source_mode: 数据来源模式
        report_dir: 报告目录
        generated_by_command: 生成命令
        provider_status: 数据提供者状态（ProviderStatus 模型）

    Returns:
        JSON 报告字典
    """
    if data_sources is None:
        data_sources = ["fixture"]

    # 构建风险摘要
    risk_summary = _build_risk_summary(industry_top, concept_top)

    # 构建数据质量详情
    data_quality = _build_data_quality_detail(
        industry_top, concept_top, data_quality_score
    )

    # 构建 provider_status
    if provider_status is not None:
        # 从 ProviderStatus 模型或 dataclass 转换为字典
        if hasattr(provider_status, 'model_dump'):
            ps_dict = provider_status.model_dump()
        elif hasattr(provider_status, '__dataclass_fields__'):
            ps_dict = {k: getattr(provider_status, k) for k in provider_status.__dataclass_fields__}
        else:
            ps_dict = provider_status
    else:
        # 默认值
        ps_dict = {
            "industry_sectors": "ok" if industry_count > 0 else "degraded",
            "concept_sectors": "ok" if concept_count > 0 else "degraded",
            "fund_flow": fund_flow_coverage.get("status", "ok") if fund_flow_coverage else "ok",
            "constituents": constituent_coverage.get("status", "ok") if constituent_coverage else "ok",
        }

    # 构建 data_completeness
    data_completeness = {
        "industry_count": industry_count,
        "concept_count": concept_count,
        "industry_min_count": 20,
        "concept_min_count": 20,
    }

    report = {
        "report_type": "theme_sector_radar",
        "version": "0.1.0",
        "as_of_date": as_of_date,
        "updated_at": datetime.now().isoformat(),
        "data_sources": data_sources,
        "data_quality_score": data_quality_score,
        "market_temperature": market_temperature.model_dump(),
        "industry_top": [_format_sector_score(s) for s in industry_top],
        "concept_top": [_format_sector_score(s) for s in concept_top],
        "overlap": [_format_resonance(r) for r in overlap],
        "risk_summary": risk_summary,
        "data_quality": data_quality,
        "disclaimer": "本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。",
        "status": status,
        "provider_status": ps_dict,
        "data_completeness": data_completeness,
        "cache_fallback": cache_info or {},
        "fund_flow_coverage": fund_flow_coverage or {},
        "constituent_coverage": constituent_coverage or {},
        "rotation_summary": rotation_summary or {},
        "comparison": comparison or {},
        "warnings": warnings or [],
        "industry_three_layer_shadow_summary": (
            industry_three_layer_shadow_summary or {}
        ),
        # 数据来源追踪字段
        "run_mode": run_mode,
        "provider": provider,
        "offline_fixture": offline_fixture,
        "fixture_profile": fixture_profile,
        "data_source_mode": data_source_mode,
        "report_dir": report_dir,
        "generated_by_command": generated_by_command,
    }

    return report


def _build_risk_summary(
    industry_top: List[SectorScore],
    concept_top: List[SectorScore]
) -> Dict[str, Any]:
    """构建风险摘要"""
    all_scores = industry_top + concept_top

    high_risk_count = sum(1 for s in all_scores if s.risk_level.value == "high")
    medium_risk_count = sum(1 for s in all_scores if s.risk_level.value == "medium")

    overheat_sectors = [
        s.name for s in all_scores if "overheat" in s.risk_flags
    ]
    divergence_sectors = [
        s.name for s in all_scores if "divergence" in s.risk_flags
    ]

    return {
        "high_risk_count": high_risk_count,
        "medium_risk_count": medium_risk_count,
        "overheat_sectors": overheat_sectors,
        "divergence_sectors": divergence_sectors,
    }


def _build_data_quality_detail(
    industry_top: List[SectorScore],
    concept_top: List[SectorScore],
    overall_score: float
) -> Dict[str, Any]:
    """构建数据质量详情"""
    all_scores = industry_top + concept_top

    low_quality_sectors = [
        s.name for s in all_scores if s.data_quality_score < 60
    ]

    return {
        "overall_score": overall_score,
        "low_quality_sectors": low_quality_sectors,
        "sector_count": len(all_scores),
    }


def _format_sector_score(score: SectorScore) -> Dict[str, Any]:
    """格式化板块评分"""
    return {
        "sector_id": score.sector_id,
        "name": score.name,
        "type": score.type.value,
        "score": round(score.score, 2),
        "positive_score": round(score.positive_score, 2),
        "risk_penalty": round(score.risk_penalty, 2),
        "focus_level": score.focus_level.value,
        "phase": score.phase.value,
        "risk_level": score.risk_level.value,
        "risk_flags": score.risk_flags,
        "reasons": score.reasons,
        "downgrade_reasons": score.downgrade_reasons,
        "watch_points": score.watch_points,
        "constituents": [
            {
                "code": c.code,
                "name": c.name,
                "change_pct": c.change_pct,
                "is_core": c.is_core,
            }
            for c in score.constituents[:10]
        ],
        "data_sources": score.data_sources,
        "updated_at": score.updated_at,
        "data_quality_score": score.data_quality_score,
        "turnover": score.turnover,
        "main_net_inflow": score.main_net_inflow,
        "score_breakdown": score.score_breakdown,
        "current_rank": score.current_rank,
        "rank_tied": score.rank_tied,
        "rank_tie_count": score.rank_tie_count,
        "previous_rank": score.previous_rank,
        "rank_change": score.rank_change,
    }


def _format_resonance(resonance: ResonanceResult) -> Dict[str, Any]:
    """格式化共振结果"""
    return {
        "industry": resonance.industry,
        "concept": resonance.concept,
        "resonance_score": round(resonance.resonance_score, 2),
        "overlap_constituent_count": resonance.overlap_constituent_count,
        "common_core_count": resonance.common_core_count,
        "flow_alignment": resonance.flow_alignment.value,
        "both_top_n": resonance.both_top_n,
        "focus_level": resonance.focus_level.value,
        "constituents": [
            {
                "code": c.code,
                "name": c.name,
                "change_pct": c.change_pct,
                "is_core": c.is_core,
            }
            for c in resonance.constituents[:10]
        ],
    }


def save_json_report(
    report: Dict[str, Any],
    filepath: str,
    *,
    default=None,
):
    """保存 JSON 报告"""
    serialized = json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
        default=default,
    )
    target = os.path.abspath(filepath)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=os.path.dirname(target),
            prefix=f".{os.path.basename(target)}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = temp_file.name
            temp_file.write(serialized)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, target)
        temp_path = None
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
