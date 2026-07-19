"""
板块综合评分 Agent

调用 sector_composite_score 和 short_term_burst_score 生成双评分结果。
"""

import warnings as warnings_module
from typing import Any, Dict, List, Optional

from ...models import AgentOutput, AgentStatus, SectorScore, SectorType
from ...scoring.sector_composite_score import (
    calculate_sector_composite_score,
    apply_insufficient_history_cap,
    generate_data_warnings,
    generate_risk_reasons,
    generate_strength_reasons,
    generate_watch_points,
    get_selection_level,
)
from ...scoring.short_term_burst_score import (
    apply_burst_insufficient_history_cap,
    calculate_short_term_burst_score,
    get_burst_level,
    interpret_dual_scores,
)



TREND_LEVEL_CN = {
    "strong_watch": "重点观察",
    "watch": "观察",
    "neutral": "中性",
    "cooling": "降温",
    "avoid": "偏弱",
}

BURST_LEVEL_CN = {
    "burst_hot": "短线强势",
    "burst_watch": "短线活跃",
    "burst_neutral": "短线中性",
    "burst_fading": "短线降温",
    "burst_avoid": "短线偏弱",
}


def translate_trend_level(level: str) -> str:
    return TREND_LEVEL_CN.get(level, level)


def translate_burst_level(level: str) -> str:
    return BURST_LEVEL_CN.get(level, level)

def calculate_sector_scores(
    radar_sectors: List[SectorScore],
    history_data: Dict[str, Any],
    sector_type: SectorType = SectorType.INDUSTRY,
    benchmark_mode: str = "sector_median",
    config: Optional[Dict[str, Any]] = None,
    score_mode: str = "dual",
    benchmark_data: Optional[Any] = None,
    trend_weight_profile: str = "baseline",
    trend_window: int = 10,
    history_source: str = "sector_history_cache",
) -> AgentOutput:
    """
    计算板块综合评分

    Args:
        radar_sectors: 日报雷达板块列表
        history_data: 历史数据字典
        sector_type: 板块类型
        benchmark_mode: 基准模式
        config: 配置字典
        score_mode: 评分模式 (composite/dual)
        benchmark_data: 基准数据 (BenchmarkData 对象)
        trend_weight_profile: 趋势权重 profile (baseline/trend_confirmation)
        trend_window: 趋势窗口 (5/10/20)

    Returns:
        AgentOutput: 包含综合评分结果的 Agent 输出
    """
    warnings_list = []
    results = []

    # 计算基准收益率
    benchmark_returns = {}
    if benchmark_data and hasattr(benchmark_data, 'records') and benchmark_data.records:
        from ...data.benchmark_provider import BenchmarkProvider
        bp = BenchmarkProvider()
        benchmark_returns = bp.calculate_benchmark_returns(benchmark_data)

    benchmark_key = f"{trend_window}d" if trend_window in [5, 10, 20] else "5d"
    benchmark_available = benchmark_key in benchmark_returns
    if benchmark_data and not benchmark_available:
        warnings_list.append(
            f"trend_window={trend_window} 对应的 {benchmark_key} benchmark 数据不可用，"
            "回退到同窗口板块中位数"
        )

    # 所有横截面收益必须使用同一趋势窗口。
    window_metrics = {
        sector.name: _calculate_window_metrics(
            history_data.get(sector.name, {}),
            trend_window,
        )
        for sector in radar_sectors
    }
    all_sector_returns = [
        metrics["total_return"]
        for metrics in window_metrics.values()
        if metrics["actual_history_days"] > 0
    ]

    # 计算每个板块的评分
    for position, sector in enumerate(radar_sectors, start=1):
        try:
            current_rank = sector.current_rank or position
            metrics = window_metrics[sector.name]
            recent_returns = metrics["recent_returns"]
            total_return = metrics["total_return"]
            positive_days = metrics["positive_days"]
            total_days = metrics["total_days"]
            max_drawdown = metrics["max_drawdown"]
            volatility = metrics["volatility"]
            history_days = metrics["history_days"]
            actual_history_days = metrics["actual_history_days"]
            history_coverage_ratio = metrics["history_coverage_ratio"]
            trend_window_status = metrics["trend_window_status"]

            # 获取日报雷达分
            radar_score = sector.score

            # 获取数据质量信息
            data_quality_score = sector.data_quality_score
            price_change_available = True
            if hasattr(sector, "score_breakdown"):
                price_change_available = sector.score_breakdown.get(
                    "price_change_available", True
                )

            # 计算趋势持续评分
            # 市场基准必须与趋势窗口同期限；不可用时交给横截面中位数回退。
            actual_benchmark_return = benchmark_returns.get(benchmark_key, 0.0)
            actual_benchmark_id = (
                benchmark_data.benchmark_id if benchmark_available else None
            )
            actual_benchmark_name = (
                benchmark_data.benchmark_name if benchmark_available else None
            )

            composite_result = calculate_sector_composite_score(
                radar_score=radar_score,
                recent_returns=recent_returns,
                sector_return=total_return,
                benchmark_return=actual_benchmark_return,
                all_sector_returns=all_sector_returns,
                positive_days_count=positive_days,
                total_days=total_days,
                max_drawdown=max_drawdown,
                volatility=volatility,
                data_quality_score=data_quality_score,
                history_days=history_days,
                price_change_available=price_change_available,
                benchmark_id=actual_benchmark_id,
                benchmark_name=actual_benchmark_name,
                trend_weight_profile=trend_weight_profile,
            )
            composite_result["score_breakdown"][
                "price_change_available"
            ] = price_change_available

            # 计算短线爆发评分
            burst_result = calculate_short_term_burst_score(
                radar_score=radar_score,
                one_day_change=recent_returns[-1] if recent_returns else None,
                recent_returns=recent_returns,
                turnover=sector.turnover,
                main_net_inflow=sector.main_net_inflow,
                current_rank=current_rank,
                previous_rank=sector.previous_rank,
                data_quality_score=data_quality_score,
                price_change_available=price_change_available,
                history_days=history_days,
                history_source=history_source,
            )
            burst_result["burst_breakdown"][
                "price_change_available"
            ] = price_change_available

            # M1: 应用短线 insufficient_history 上限
            burst_capped, burst_cap_applied, burst_cap_reason = apply_burst_insufficient_history_cap(
                burst_result["short_term_burst_score"],
                history_days,
                actual_history_days,
            )
            if burst_cap_applied:
                burst_result["short_term_burst_score"] = burst_capped
                burst_result["burst_level"] = get_burst_level(burst_capped)
                burst_result["_burst_history_cap_applied"] = True
                burst_result["_burst_history_cap_reason"] = burst_cap_reason
            else:
                burst_result["_burst_history_cap_applied"] = False

            # 生成诊断信息
            persistence_ratio = positive_days / total_days if total_days > 0 else 0.5
            negative_ratio = 1.0 - persistence_ratio

            strength_reasons = generate_strength_reasons(
                radar_score=radar_score,
                momentum=total_return,
                relative_strength=total_return,  # 简化处理
                persistence_ratio=persistence_ratio,
                selection_level=composite_result["selection_level"],
            )

            risk_reasons = generate_risk_reasons(
                max_drawdown=max_drawdown,
                volatility=volatility,
                negative_ratio=negative_ratio,
            )

            watch_points = generate_watch_points(
                selection_level=composite_result["selection_level"],
                benchmark_mode=composite_result["benchmark_mode"],
                persistence_ratio=persistence_ratio,
                volatility=volatility,
            )

            data_warnings = generate_data_warnings(
                history_days=history_days,
                price_change_available=price_change_available,
                sector_type=sector_type.value,
            )

            # 应用 insufficient_history 上限
            capped_score = apply_insufficient_history_cap(
                composite_result["sector_selection_score"],
                trend_window_status,
                history_coverage_ratio,
            )
            if capped_score != composite_result["sector_selection_score"]:
                composite_result["sector_selection_score"] = capped_score
                composite_result["selection_level"] = get_selection_level(capped_score)
                composite_result["score_breakdown"]["_history_cap_applied"] = True

            # 解读双评分
            dual_interpretation = interpret_dual_scores(
                trend_score=composite_result["sector_selection_score"],
                trend_level=composite_result["selection_level"],
                burst_score=burst_result["short_term_burst_score"],
                burst_level=burst_result["burst_level"],
            )

            # 构建结果
            selection_level = composite_result["selection_level"]
            burst_level = burst_result["burst_level"]
            result = {
                "sector_id": sector.sector_id,
                "sector_name": sector.name,
                "sector_type": sector_type.value,
                # 保持旧字段兼容
                "sector_selection_score": composite_result["sector_selection_score"],
                "selection_level": selection_level,
                "selection_level_cn": translate_trend_level(selection_level),
                # 新增双评分字段
                "trend_continuation_score": composite_result["sector_selection_score"],
                "trend_level": selection_level,
                "trend_level_cn": translate_trend_level(selection_level),
                "trend_breakdown": composite_result["score_breakdown"],
                "short_term_burst_score": burst_result["short_term_burst_score"],
                "burst_level": burst_level,
                "burst_level_cn": translate_burst_level(burst_level),
                "burst_breakdown": burst_result["burst_breakdown"],
                "_burst_history_cap_applied": burst_result.get("_burst_history_cap_applied", False),
                "_burst_history_cap_reason": burst_result.get("_burst_history_cap_reason", ""),
                "score_interpretation": dual_interpretation,
                # 通用字段
                "rotation_phase": _determine_rotation_phase(
                    total_return, persistence_ratio, volatility
                ),
                "benchmark_mode": composite_result["benchmark_mode"],
                "benchmark_id": composite_result.get("benchmark_id"),
                "benchmark_name": composite_result.get("benchmark_name"),
                "trend_weight_profile": composite_result.get("trend_weight_profile", "baseline"),
                "trend_window": trend_window,
                "actual_history_days": actual_history_days,
                "history_coverage_ratio": round(history_coverage_ratio, 2),
                "trend_window_status": trend_window_status,
                "score_breakdown": composite_result["score_breakdown"],
                "strength_reasons": strength_reasons,
                "risk_reasons": risk_reasons,
                "watch_points": watch_points,
                "data_warnings": data_warnings + burst_result.get("warnings", []),
                "radar_score": radar_score,
                "radar_rank": current_rank,
                "radar_rank_tied": sector.rank_tied,
                "radar_rank_tie_count": sector.rank_tie_count,
                "history_days": history_days,
            }

            results.append(result)

        except Exception as e:
            warnings_list.append(f"计算板块 {sector.name} 综合评分失败: {str(e)}")

    _assign_result_ranks(results, "sector_selection_score", "trend")
    _assign_result_ranks(results, "short_term_burst_score", "burst")
    results.sort(
        key=lambda item: (
            -item["sector_selection_score"],
            item["sector_id"],
            item["sector_name"],
        )
    )

    return AgentOutput(
        agent_id="sector_scoring",
        status=AgentStatus.OK if not warnings_list else AgentStatus.DEGRADED,
        data={
            "scores": results,
            "sector_type": sector_type.value,
            "benchmark_mode": benchmark_mode,
            "total_count": len(results),
            "score_mode": score_mode,
        },
        warnings=warnings_list,
    )


def _assign_result_ranks(
    results: List[Dict[str, Any]],
    score_key: str,
    prefix: str,
) -> None:
    ordered = sorted(
        results,
        key=lambda item: (
            -item[score_key],
            item["sector_id"],
            item["sector_name"],
        ),
    )
    score_keys = [round(float(item[score_key]), 8) for item in ordered]
    tie_counts = {key: score_keys.count(key) for key in set(score_keys)}
    current_rank = 0
    previous_key = None

    for position, (item, value) in enumerate(zip(ordered, score_keys), start=1):
        if value != previous_key:
            current_rank = position
            previous_key = value
        tie_count = tie_counts[value]
        item[f"{prefix}_rank"] = current_rank
        item[f"{prefix}_rank_tied"] = tie_count > 1
        item[f"{prefix}_rank_tie_count"] = tie_count


def _calculate_window_metrics(
    sector_history: Dict[str, Any],
    trend_window: int,
) -> Dict[str, Any]:
    if trend_window <= 0:
        raise ValueError("trend_window must be positive")

    source_returns = list(sector_history.get("recent_returns", []))
    recent_returns = source_returns[-trend_window:]
    actual_history_days = len(recent_returns)
    coverage = actual_history_days / trend_window

    wealth = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for daily_return in recent_returns:
        wealth *= 1.0 + daily_return / 100.0
        peak = max(peak, wealth)
        max_drawdown = min(max_drawdown, (wealth / peak - 1.0) * 100.0)

    if actual_history_days > 1:
        mean = sum(recent_returns) / actual_history_days
        variance = sum(
            (daily_return - mean) ** 2 for daily_return in recent_returns
        ) / actual_history_days
        volatility = variance ** 0.5
    else:
        volatility = 0.0

    return {
        "recent_returns": recent_returns,
        "total_return": (wealth - 1.0) * 100.0,
        "positive_days": sum(1 for daily_return in recent_returns if daily_return > 0),
        "total_days": actual_history_days,
        "max_drawdown": max_drawdown,
        "volatility": volatility,
        "history_days": sector_history.get("history_days", len(source_returns)),
        "actual_history_days": actual_history_days,
        "history_coverage_ratio": coverage,
        "trend_window_status": (
            "ok"
            if coverage >= 1.0
            else "partial_history"
            if coverage >= 0.5
            else "insufficient_history"
        ),
    }


def _determine_rotation_phase(
    total_return: float,
    persistence_ratio: float,
    volatility: float,
) -> str:
    """
    判断板块轮动阶段

    Args:
        total_return: 累计收益率
        persistence_ratio: 上涨天数比例
        volatility: 波动率

    Returns:
        轮动阶段
    """
    if total_return > 3 and persistence_ratio > 0.6:
        return "leading"
    elif total_return > 0 and persistence_ratio > 0.5:
        return "improving"
    elif total_return < 0 and persistence_ratio < 0.4:
        return "weakening"
    else:
        return "lagging"
