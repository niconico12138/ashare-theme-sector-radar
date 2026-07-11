"""
因子快照构建模块

从候选股字典中读取已有字段，生成 factor_snapshot。
第二阶段：支持 bars 数据计算真实因子值。
"""

from __future__ import annotations

from typing import Any

from theme_sector_radar.factors.schema import FactorValue, FactorSnapshot
from theme_sector_radar.factors.registry import FACTOR_REGISTRY, FactorMetadata
from theme_sector_radar.factors.normalizer import normalize_factor
from theme_sector_radar.factors.calculators import calculate_bar_factors


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为 float。"""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extract_factor_value(
    candidate: dict,
    metadata: FactorMetadata,
) -> FactorValue:
    """从候选股字典中提取单个因子的值。

    Args:
        candidate: 候选股字典
        metadata: 因子元数据

    Returns:
        FactorValue 实例
    """
    # 字段映射：factor_id -> candidate 中的字段名
    field_mapping = {
        "ma20_slope_5": "ma20_slope_5",
        "stock_trend_score": "stock_trend_score",
        "stock_short_score": "stock_short_score",
        "stock_short_score_v2": "stock_short_score_v2",
        "drawdown_risk_score": "drawdown_risk_score",
        "risk_penalty_score": "risk_penalty_score",
        "regime_router_shadow_score_v5": "regime_router_shadow_score_v5",
        "sector_trend_score": "sector_trend_score",
        "sector_burst_score": "sector_burst_score",
        "final_score": "final_score",
        "agent_score": "agent_score",
        "trend_agent_score": "trend_agent_score",
        "short_agent_score": "short_agent_score",
    }

    field_name = field_mapping.get(metadata.factor_id, metadata.factor_id)

    # 特殊处理 sector_support_score：从 sector_trend_score 和 sector_burst_score 计算
    if metadata.factor_id == "sector_support_score":
        # 尝试多种字段名
        sector_trend = _safe_float(candidate.get("sector_trend_score"))
        sector_burst = _safe_float(candidate.get("sector_burst_score"))

        # 如果 sector_trend_score/sector_burst_score 为 0 或 None，尝试替代字段
        if sector_trend == 0:
            sector_trend = _safe_float(candidate.get("trend_score"))
        if sector_burst == 0:
            sector_burst = _safe_float(candidate.get("burst_score"))

        if sector_trend > 0 and sector_burst > 0:
            raw_value = sector_trend * 0.7 + sector_burst * 0.3
        elif sector_trend > 0:
            raw_value = sector_trend
        elif sector_burst > 0:
            raw_value = sector_burst
        else:
            raw_value = None
    else:
        raw_value = candidate.get(field_name)

    # 如果字段不存在，标记为 missing
    if raw_value is None:
        raw_value = None
        quality = "missing"
        score = 50.0
    else:
        # 使用 normalizer 归一化
        score, quality = normalize_factor(raw_value, metadata)

    # 收集相关 tags
    tags: list[str] = []
    breakdown_key = f"{field_name}_breakdown"
    if breakdown_key in candidate:
        tags.append("has_breakdown")
    tags_key = f"{field_name}_tags"
    if tags_key in candidate:
        tags.extend(candidate[tags_key][:3])  # 只取前3个标签

    return FactorValue(
        factor_id=metadata.factor_id,
        raw_value=raw_value,
        score=score,
        category=metadata.category,
        source_project=metadata.source_project,
        direction=metadata.direction,
        lookback_days=metadata.lookback_days,
        quality=quality,
        display_name=metadata.display_name,
        description=metadata.description,
        tags=tags,
    )


def build_factor_snapshot(
    candidate: dict,
    as_of: str | None = None,
    bars: list[dict] | None = None,
) -> dict:
    """从候选股字典构建 factor_snapshot。

    Args:
        candidate: 候选股字典（包含各种评分字段）
        as_of: 数据日期（可选）
        bars: 日线数据（可选），用于计算 bars 因子

    Returns:
        factor_snapshot 普通 dict，方便写入 JSON
    """
    code = candidate.get("code", "")
    name = candidate.get("name", "")

    # 如果有 bars，先计算 bars 因子
    bar_factors: dict[str, float | None] = {}
    if bars:
        try:
            bar_factors = calculate_bar_factors(candidate, bars)
        except Exception:
            # bars 计算异常时降级，不影响后续流程
            bar_factors = {}

    # 构建所有启用因子的值
    factors: list[FactorValue] = []
    for metadata in FACTOR_REGISTRY.values():
        if metadata.enabled:
            # 优先使用 bars 计算的真实值
            if metadata.factor_id in bar_factors and bar_factors[metadata.factor_id] is not None:
                # 用 bars 计算的值覆盖 candidate 中的字段
                candidate_with_bar = dict(candidate)
                candidate_with_bar[metadata.factor_id] = bar_factors[metadata.factor_id]
                fv = _extract_factor_value(candidate_with_bar, metadata)
                # 标记为 bars 计算
                if "bars_calculated" not in fv.tags:
                    fv.tags.append("bars_calculated")
            else:
                fv = _extract_factor_value(candidate, metadata)
            factors.append(fv)

    # 构建汇总信息
    missing_factors = [f.factor_id for f in factors if f.quality == "missing"]
    bars_calculated = [f.factor_id for f in factors if "bars_calculated" in f.tags]

    summary = {
        "factor_count": len(factors),
        "missing_count": len(missing_factors),
        "missing_factors": missing_factors,
        "bars_calculated": bars_calculated,
        "bars_available": bool(bars),
        "avg_score": round(
            sum(f.score for f in factors) / len(factors) if factors else 0, 2
        ),
    }

    snapshot = FactorSnapshot(
        schema_version="1.0",
        as_of=as_of or "",
        code=code,
        name=name,
        factors=factors,
        summary=summary,
    )

    return snapshot.to_dict()
