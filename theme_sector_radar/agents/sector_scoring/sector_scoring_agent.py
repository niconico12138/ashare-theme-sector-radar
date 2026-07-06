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
    benchmark_returns = {"1d": 0.0, "3d": 0.0, "5d": 0.0}
    if benchmark_data and hasattr(benchmark_data, 'records') and benchmark_data.records:
        from ...data.benchmark_provider import BenchmarkProvider
        bp = BenchmarkProvider()
        benchmark_returns = bp.calculate_benchmark_returns(benchmark_data)

    # 提取所有板块的收益率 (用于计算中位数)
    all_sector_returns = []
    for sector in radar_sectors:
        sector_history = history_data.get(sector.name, {})
        sector_return = sector_history.get("total_return", 0.0)
        all_sector_returns.append(sector_return)

    # 计算每个板块的评分
    for sector in radar_sectors:
        try:
            # 获取历史数据
            sector_history = history_data.get(sector.name, {})
            recent_returns = sector_history.get("recent_returns", [])
            total_return = sector_history.get("total_return", 0.0)
            positive_days = sector_history.get("positive_days", 0)
            total_days = sector_history.get("total_days", 0)
            max_drawdown = sector_history.get("max_drawdown", 0.0)
            volatility = sector_history.get("volatility", 0.0)
            history_days = sector_history.get("history_days", 0)

            # 应用趋势窗口截取
            if recent_returns and len(recent_returns) > trend_window:
                truncated_returns = recent_returns[-trend_window:]
                actual_history_days = len(truncated_returns)
                history_coverage_ratio = actual_history_days / trend_window if trend_window > 0 else 0.0

                # 重新计算指标
                total_return = sum(truncated_returns)
                positive_days = sum(1 for r in truncated_returns if r > 0)
                total_days = len(truncated_returns)

                # 重新计算最大回撤
                cumulative = 0.0
                peak = 0.0
                max_drawdown = 0.0
                for r in truncated_returns:
                    cumulative += r
                    if cumulative > peak:
                        peak = cumulative
                    drawdown = cumulative - peak
                    if drawdown < max_drawdown:
                        max_drawdown = drawdown

                # 重新计算波动率
                if total_days > 1:
                    mean = sum(truncated_returns) / total_days
                    variance = sum((r - mean) ** 2 for r in truncated_returns) / total_days
                    volatility = variance ** 0.5
                else:
                    volatility = 0.0

                recent_returns = truncated_returns
                trend_window_status = "ok" if actual_history_days >= trend_window * 0.5 else "insufficient_history"
            else:
                actual_history_days = len(recent_returns)
                history_coverage_ratio = actual_history_days / trend_window if trend_window > 0 else 0.0
                trend_window_status = "ok" if actual_history_days >= trend_window * 0.5 else "insufficient_history"

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
            # 确定基准收益率 - 根据 trend_window 选择对应窗口
            benchmark_key = f"{trend_window}d" if trend_window in [5, 10, 20] else "5d"
            actual_benchmark_return = benchmark_returns.get(benchmark_key, benchmark_returns.get("5d", 0.0))
            # 如果有 benchmark_data 但对应窗口不可用，记录警告
            if benchmark_data and benchmark_key not in benchmark_returns:
                warnings_list.append(f"trend_window={trend_window} 对应的 benchmark 数据不可用，使用 5d 回退")

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
                benchmark_id=benchmark_data.benchmark_id if benchmark_data else None,
                benchmark_name=benchmark_data.benchmark_name if benchmark_data else None,
                trend_weight_profile=trend_weight_profile,
            )

            # 计算短线爆发评分
            burst_result = calculate_short_term_burst_score(
                radar_score=radar_score,
                one_day_change=recent_returns[-1] if recent_returns else None,
                recent_returns=recent_returns,
                turnover=sector.turnover if hasattr(sector, 'turnover') else None,
                main_net_inflow=sector.main_net_inflow if hasattr(sector, 'main_net_inflow') else None,
                current_rank=None,  # 需要从外部传入
                previous_rank=None,
                data_quality_score=data_quality_score,
                price_change_available=price_change_available,
                history_days=history_days,
                history_source="sector_history_cache",
            )

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
                "history_days": history_days,
            }

            results.append(result)

        except Exception as e:
            warnings_list.append(f"计算板块 {sector.name} 综合评分失败: {str(e)}")

    # 按趋势持续评分排序
    results.sort(key=lambda x: x["sector_selection_score"], reverse=True)

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
