"""
主流程编排

串联各 Agent 完成完整的板块雷达分析。
支持重试、缓存 fallback、资金流关联和成分股补充。
"""

import json
import os
import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .agents.data import (
    calculate_data_reliability,
    calculate_sector_coverage,
    normalize_sector_data,
)
from .agents.defense_risk import (
    calculate_avoidance_explanation,
    calculate_risk_assessment,
)
from .agents.positive_scoring import (
    calculate_concept_heat,
    calculate_industry_flow,
    calculate_market_temperature,
)
from .agents.ranking_report import (
    calculate_overlap_resonance,
    generate_sector_ranking,
)
from .config import get_config
from .data.cache import DataCache
from .data.fixture_provider import FixtureProvider
from .data.providers import DataProvider
from .models import (
    AgentStatus,
    FocusLevel,
    MarketTemperature,
    RadarContext,
    RadarReport,
    ResonanceResult,
    SectorScore,
    SectorType,
)
from .history.sector_trend_history import load_sector_trend_history
from .reports.json_report import generate_json_report, save_json_report
from .reports.markdown_report import generate_markdown_report, save_markdown_report


def run_pipeline(
    as_of_date: str,
    top_n: int = 10,
    output_dir: str = None,
    offline_fixture: bool = False,
    use_cache: bool = False,
    refresh: bool = False,
    provider_name: str = "fixture",
    fallback_cache_days: int = 7,
    fixture_profile: str = "full",
    compare_to: str = None,
    lookback_days: int = 5,
    run_mode: str = "normal",
    report_root: str = None,
    history_root: str = None,
) -> RadarReport:
    """
    运行完整的板块雷达分析流程

    Args:
        as_of_date: 分析日期
        top_n: Top N 数量
        output_dir: 输出目录
        offline_fixture: 是否使用离线 fixture
        use_cache: 是否使用缓存
        refresh: 是否强制刷新
        provider_name: 数据提供者名称 (fixture/akshare)
        fallback_cache_days: 缓存 fallback 回退天数
        fixture_profile: Fixture 数据 profile (full/minimal/rotation-day1/rotation-day2)
        compare_to: 指定比较日期
        lookback_days: 回溯天数

    Returns:
        RadarReport 最终报告
    """
    config = get_config()
    config["top_n"] = top_n
    config["fallback_cache_days"] = fallback_cache_days

    # 初始化上下文
    context = RadarContext(
        as_of_date=as_of_date,
        config=config,
    )

    # 初始化缓存
    cache = DataCache()

    # 选择数据提供者
    provider = _create_provider(provider_name, offline_fixture, fixture_profile)

    # Phase 1: 数据获取（带缓存和 fallback）
    print("Phase 1: 获取数据...")
    industry_sectors, concept_sectors, market_data, cache_info, provider_status = _fetch_data_with_cache(
        provider=provider,
        as_of_date=as_of_date,
        top_n=top_n,
        cache=cache,
        use_cache=use_cache,
        refresh=refresh,
        offline_fixture=offline_fixture,
        fallback_cache_days=fallback_cache_days,
        config=config,
    )

    context.raw_data = {
        "industry_sectors": [s.model_dump() for s in industry_sectors],
        "concept_sectors": [s.model_dump() for s in concept_sectors],
        "market_data": market_data,
    }

    # Phase 2: 数据标准化
    print("Phase 2: 数据标准化...")
    industry_output = normalize_sector_data(
        [s.model_dump() for s in industry_sectors],
        SectorType.INDUSTRY,
    )
    concept_output = normalize_sector_data(
        [s.model_dump() for s in concept_sectors],
        SectorType.CONCEPT,
    )

    context.normalized_data = {
        "industry": industry_output.data,
        "concept": concept_output.data,
    }

    # Phase 3: 覆盖率和数据质量
    print("Phase 3: 评估数据质量...")
    coverage_output = calculate_sector_coverage(industry_sectors + concept_sectors)
    reliability_output = calculate_data_reliability(industry_sectors + concept_sectors)

    context.agent_outputs["coverage"] = coverage_output.data
    context.agent_outputs["reliability"] = reliability_output.data
    context.data_quality_score = reliability_output.data_quality_score

    # Phase 4: 市场温度
    print("Phase 4: 计算市场温度...")
    temperature_output = calculate_market_temperature(market_data)
    market_temperature = MarketTemperature(**temperature_output.data)

    context.agent_outputs["market_temperature"] = temperature_output.data

    # Phase 5: 资金流关联
    print("Phase 5: 关联资金流...")
    fund_flow_coverage = _enrich_fund_flow(
        provider=provider,
        industry_sectors=industry_sectors,
        concept_sectors=concept_sectors,
        as_of_date=as_of_date,
        offline_fixture=offline_fixture,
    )

    # Phase 6: 正向评分
    print("Phase 6: 计算正向评分...")
    industry_flow_output = calculate_industry_flow(
        industry_sectors, market_temperature.score
    )
    concept_heat_output = calculate_concept_heat(concept_sectors)

    context.agent_outputs["industry_flow"] = industry_flow_output.data
    context.agent_outputs["concept_heat"] = concept_heat_output.data

    # Phase 7: 风险评估
    print("Phase 7: 风险评估...")
    risk_output = calculate_risk_assessment(industry_sectors + concept_sectors)
    context.agent_outputs["risk"] = risk_output.data

    # Phase 8: 排名和关注等级
    print("Phase 8: 生成排名...")
    resolved_history_root = history_root or os.path.join(
        cache.cache_dir,
        "sector_history",
    )
    industry_history, trend_history_warnings = load_sector_trend_history(
        resolved_history_root,
        sector_type=SectorType.INDUSTRY,
        as_of_date=as_of_date,
    )
    matched_history_count = sum(
        sector.name in industry_history for sector in industry_sectors
    )
    maturity_counts = {
        window: sum(
            len(industry_history.get(sector.name, {}).get("recent_returns", []))
            >= window
            for sector in industry_sectors
        )
        for window in (5, 10, 20)
    }
    if matched_history_count < len(industry_sectors):
        trend_history_warnings.append(
            "正式行业趋势历史覆盖不足: "
            f"{matched_history_count}/{len(industry_sectors)}"
        )
    if maturity_counts[5] < len(industry_sectors):
        trend_history_warnings.append(
            "正式行业趋势五日成熟覆盖不足: "
            f"{maturity_counts[5]}/{len(industry_sectors)}"
        )
    context.warnings.extend(trend_history_warnings)
    context.agent_outputs["base_industry_trend_history"] = {
        "root": str(resolved_history_root),
        "available_history_count": len(industry_history),
        "matched_sector_count": matched_history_count,
        "five_day_mature_count": maturity_counts[5],
        "ten_day_mature_count": maturity_counts[10],
        "twenty_day_mature_count": maturity_counts[20],
        "candidate_sector_count": len(industry_sectors),
        "status": (
            "ok" if maturity_counts[5] == len(industry_sectors) else "degraded"
        ),
        "warnings": trend_history_warnings,
    }
    ranking_output = generate_sector_ranking(
        industry_sectors,
        concept_sectors,
        market_temperature.score,
        top_n,
        industry_history=industry_history,
    )
    ranking_history = ranking_output.data.get("industry_trend_history", {})
    three_layer_shadow_summary = {
        key: ranking_history.get(key, default)
        for key, default in (
            ("three_layer_shadow_available_count", 0),
            ("three_layer_shadow_error_count", 0),
            ("three_layer_shadow_state_counts", {}),
        )
    }
    successful_industry_count = int(
        ranking_history.get("successful_score_count", len(industry_sectors))
    )
    failed_industry_count = int(ranking_history.get("failed_score_count", 0))
    ranking_degraded = ranking_output.status != AgentStatus.OK
    if ranking_output.warnings:
        context.warnings.extend(ranking_output.warnings)
    effective_counts = {
        window: int(ranking_history.get(f"effective_{window}d_count", 0))
        for window in (5, 10, 20)
    }
    context.agent_outputs["base_industry_trend_history"].update(
        {
            "effective_five_day_count": effective_counts[5],
            "effective_ten_day_count": effective_counts[10],
            "effective_twenty_day_count": effective_counts[20],
            "successful_score_count": successful_industry_count,
            "failed_score_count": failed_industry_count,
        }
    )
    if effective_counts[5] < len(industry_sectors):
        effective_warning = (
            "正式行业五日相对强度有效覆盖不足: "
            f"{effective_counts[5]}/{len(industry_sectors)}"
        )
        context.warnings.append(effective_warning)
        context.agent_outputs["base_industry_trend_history"]["warnings"].append(
            effective_warning
        )
        context.agent_outputs["base_industry_trend_history"]["status"] = "degraded"
    context.agent_outputs["ranking"] = ranking_output.data

    # 解析排名结果
    industry_scores = [
        SectorScore(**s) for s in ranking_output.data.get("industry_top", [])
    ]
    concept_scores = [
        SectorScore(**s) for s in ranking_output.data.get("concept_top", [])
    ]

    # Phase 9: 成分股补充
    print("Phase 9: 补充成分股...")
    constituent_coverage = _enrich_constituents(
        provider=provider,
        industry_scores=industry_scores,
        concept_scores=concept_scores,
        offline_fixture=offline_fixture,
    )

    # Phase 10: 回避解释
    print("Phase 10: 生成回避解释...")
    avoidance_output = calculate_avoidance_explanation(industry_scores + concept_scores)
    context.agent_outputs["avoidance"] = avoidance_output.data

    # 更新关注等级
    avoidance_map = {
        e["sector_id"]: e
        for e in avoidance_output.data.get("explanations", [])
    }
    for score in industry_scores + concept_scores:
        if score.sector_id in avoidance_map:
            exp = avoidance_map[score.sector_id]
            score.focus_level = FocusLevel(exp["focus_level"])
            score.downgrade_reasons = exp.get("downgrade_reasons", [])

    # Phase 11: 共振检测
    print("Phase 11: 检测共振...")
    overlap_output = calculate_overlap_resonance(
        industry_sectors, concept_sectors,
        industry_scores, concept_scores, top_n
    )
    context.agent_outputs["overlap"] = overlap_output.data

    resonance_results = [
        ResonanceResult(**r) for r in overlap_output.data.get("resonance", [])
    ]

    # 确定数据来源和状态
    data_sources = _get_data_sources(provider_name, offline_fixture, industry_sectors, concept_sectors)
    report_status = _determine_report_status(
        industry_count=successful_industry_count,
        concept_count=len(concept_sectors),
        config=config,
    )
    if (
        maturity_counts[5] < len(industry_sectors)
        or effective_counts[5] < len(industry_sectors)
        or ranking_degraded
    ) and report_status != "failed":
        report_status = "degraded"

    # Phase 12: 轮动追踪
    print("Phase 12: 轮动追踪...")
    from .history.snapshot_loader import load_previous_snapshot
    from .history.rotation_tracker import calculate_rotation

    # 确定报告目录
    report_dirs = [report_root] if report_root else ["reports/theme_sector_radar"]

    previous_snapshot = load_previous_snapshot(
        current_date=as_of_date,
        compare_to=compare_to,
        lookback_days=lookback_days,
        report_dirs=report_dirs,
    )

    rotation_result = calculate_rotation(
        current_industry=industry_scores,
        current_concept=concept_scores,
        previous_data=previous_snapshot,
    )
    _apply_rotation_ranks(industry_scores, rotation_result.industry_details)
    _apply_rotation_ranks(concept_scores, rotation_result.concept_details)

    # 构建 comparison 信息
    comparison_info = {
        "compare_to_date": compare_to,
        "comparison_source": _get_comparison_source(compare_to, lookback_days, previous_snapshot),
        "comparison_status": rotation_result.comparison_status,
        "warnings": rotation_result.comparison_warnings,
    }

    # Phase 13: 生成报告
    print("Phase 13: 生成报告...")
    report = _build_report(
        as_of_date=as_of_date,
        market_temperature=market_temperature,
        industry_top=industry_scores,
        concept_top=concept_scores,
        overlap=resonance_results,
        data_sources=data_sources,
        data_quality_score=context.data_quality_score,
        status=report_status,
        cache_info=cache_info,
        fund_flow_coverage=fund_flow_coverage,
        constituent_coverage=constituent_coverage,
        industry_count=successful_industry_count,
        concept_count=len(concept_sectors),
        rotation_result=rotation_result,
        comparison_info=comparison_info,
        run_mode=run_mode,
        provider_name=provider_name,
        offline_fixture=offline_fixture,
        fixture_profile=fixture_profile,
        report_dir=output_dir,
        command_args="",  # 由 CLI 传递
        provider_status=provider_status,
        warnings=context.warnings,
        industry_three_layer_shadow_summary=three_layer_shadow_summary,
    )

    # 保存报告
    if output_dir:
        # 确定 data_source_mode
        if offline_fixture:
            data_source_mode = "fixture"
        elif provider_name == "akshare":
            if cache_info and cache_info.get("is_fallback"):
                data_source_mode = "cache_fallback"
            elif cache_info and cache_info.get("cache_created_at"):
                data_source_mode = "cache_replay"
            else:
                data_source_mode = "akshare_refresh"
        else:
            data_source_mode = "unknown"

        _save_reports(
            output_dir=output_dir,
            as_of_date=as_of_date,
            market_temperature=market_temperature,
            industry_top=industry_scores,
            concept_top=concept_scores,
            overlap=resonance_results,
            data_sources=data_sources,
            data_quality_score=context.data_quality_score,
            context=context,
            status=report_status,
            cache_info=cache_info,
            fund_flow_coverage=fund_flow_coverage,
            constituent_coverage=constituent_coverage,
            industry_count=successful_industry_count,
            concept_count=len(concept_sectors),
            rotation_summary={
                "industry": rotation_result.industry_rotation,
                "concept": rotation_result.concept_rotation,
            } if rotation_result else None,
            comparison_info=comparison_info,
            run_mode=run_mode,
            provider_name=provider_name,
            offline_fixture=offline_fixture,
            fixture_profile=fixture_profile,
            data_source_mode=data_source_mode,
            provider_status=provider_status,
            warnings=context.warnings,
            industry_three_layer_shadow_summary=three_layer_shadow_summary,
        )

    return report


def _create_provider(
    provider_name: str,
    offline_fixture: bool,
    fixture_profile: str = "full"
) -> DataProvider:
    """创建数据提供者"""
    if offline_fixture or provider_name == "fixture":
        return FixtureProvider(profile=fixture_profile)
    elif provider_name == "akshare":
        try:
            from .data.akshare_provider import AkShareProvider
            return AkShareProvider()
        except ImportError as e:
            warnings.warn(f"无法导入 AkShareProvider: {e}，回退到 FixtureProvider")
            return FixtureProvider(profile=fixture_profile)
    else:
        warnings.warn(f"未知的 provider: {provider_name}，使用 FixtureProvider")
        return FixtureProvider(profile=fixture_profile)


def _fetch_data_with_cache(
    provider: DataProvider,
    as_of_date: str,
    top_n: int,
    cache: DataCache,
    use_cache: bool,
    refresh: bool,
    offline_fixture: bool,
    fallback_cache_days: int,
    config: dict,
) -> Tuple[list, list, dict, dict, Any]:
    """
    带缓存和 fallback 的数据获取

    Returns:
        (industry_sectors, concept_sectors, market_data, cache_info, provider_status)
    """
    cache_key = "raw_snapshot"
    cache_info = {
        "is_fallback": False,
        "source_as_of_date": None,
        "cache_created_at": None,
    }
    provider_status = None

    # 检查缓存
    if use_cache and not refresh:
        cached = cache.get(cache_key, as_of_date)
        if cached and "data" in cached:
            print("  使用缓存数据...")
            data = cached["data"]
            industry_sectors = _dict_list_to_sectors(
                data.get("industry_sectors", []),
                SectorType.INDUSTRY
            )
            concept_sectors = _dict_list_to_sectors(
                data.get("concept_sectors", []),
                SectorType.CONCEPT
            )
            market_data = data.get("market_data", {})
            return industry_sectors, concept_sectors, market_data, cache_info, provider_status

    # 检查是否为历史日期（非今天）
    from datetime import datetime, date
    today = date.today().isoformat()
    is_historical_date = as_of_date < today

    # 如果是历史日期，优先从 sector_history 读取数据
    if is_historical_date and not offline_fixture:
        print(f"  检测到历史日期 {as_of_date}，优先从 sector_history 读取...")
        industry_sectors, industry_meta = _load_sector_history_fallback(
            cache.cache_dir,
            SectorType.INDUSTRY,
            as_of_date,
            top_n * 2,
        )
        concept_sectors, concept_meta = _load_sector_history_fallback(
            cache.cache_dir,
            SectorType.CONCEPT,
            as_of_date,
            top_n * 2,
        )

        # 如果 sector_history 有数据，直接使用
        if len(industry_sectors) > 0 and len(concept_sectors) > 0:
            print(f"  从 sector_history 读取到 {len(industry_sectors)} 个行业板块, {len(concept_sectors)} 个概念板块")
            market_data = provider.get_market_overview(as_of_date)

            # 更新 provider_status
            if hasattr(provider, 'get_provider_status'):
                provider_status = provider.get_provider_status()
                if provider_status is None:
                    from .data.akshare_provider import ProviderStatusInfo
                    provider_status = ProviderStatusInfo()
                provider_status.fallback_used = True
                provider_status.fallback_provider = "sector_history_cache"
                provider_status.fallback_reason = f"历史日期 {as_of_date}，使用 sector_history_cache"
                provider_status.industry_source = "sector_history/ths_industry_index"
                provider_status.industry_count = len(industry_sectors)
                provider_status.concept_source = "sector_history/ths_concept_index"
                provider_status.concept_count = len(concept_sectors)
                provider_status.concept_price_change_available = True

            # 更新 cache_info
            cache_info["is_fallback"] = True
            cache_info["fallback_source"] = "sector_history_cache"
            cache_info["source_as_of_date"] = industry_meta.get("source_as_of_date") or concept_meta.get("source_as_of_date")

            # 缓存数据
            cache_data = {
                "industry_sectors": [s.model_dump() for s in industry_sectors],
                "concept_sectors": [s.model_dump() for s in concept_sectors],
                "market_data": market_data,
            }
            cache.set(
                cache_key,
                cache_data,
                as_of_date=as_of_date,
                metadata={
                    "provider": "akshare",
                    "created_at": datetime.now().isoformat(),
                    "as_of_date": as_of_date,
                    "data_sources": ["sector_history/ths_industry_index", "sector_history/ths_concept_index"],
                    "is_fallback": True,
                    "source_as_of_date": cache_info["source_as_of_date"],
                }
            )
            cache_info["cache_created_at"] = datetime.now().isoformat()

            return industry_sectors, concept_sectors, market_data, cache_info, provider_status
        else:
            print(f"  sector_history 中无 {as_of_date} 的数据，降级到实时接口")

    # 获取真实数据（实时接口）
    industry_sectors = provider.get_industry_sectors(as_of_date, top_n * 2)
    concept_sectors = provider.get_concept_sectors(as_of_date, top_n * 2)
    market_data = provider.get_market_overview(as_of_date)

    # 获取 provider status（如果 provider 支持）
    if hasattr(provider, 'get_provider_status'):
        provider_status = provider.get_provider_status()

    # 检查数据完整性，必要时 fallback
    industry_min = config.get("industry_min_count", 20)
    concept_min = config.get("concept_min_count", 20)

    if not offline_fixture and len(industry_sectors) < industry_min:
        history_sectors, history_meta = _load_sector_history_fallback(
            cache.cache_dir,
            SectorType.INDUSTRY,
            as_of_date,
            top_n * 2,
        )
        if len(history_sectors) > len(industry_sectors):
            print(
                f"  使用 sector_history fallback 补充行业板块: "
                f"{len(history_sectors)} 个 (source_as_of_date={history_meta.get('source_as_of_date')})"
            )
            industry_sectors = history_sectors
            cache_info["is_fallback"] = True
            cache_info["fallback_source"] = "sector_history_cache"
            cache_info["industry_source_as_of_date"] = history_meta.get("source_as_of_date")
            cache_info["source_as_of_date"] = history_meta.get("source_as_of_date")
            if provider_status is not None:
                provider_status.fallback_used = True
                provider_status.fallback_provider = "sector_history_cache"
                provider_status.fallback_reason = "行业实时接口数据不足，使用 sector_history_cache"
                provider_status.industry_source = "sector_history/ths_industry_index"
                provider_status.industry_count = len(industry_sectors)

    if not offline_fixture and len(industry_sectors) < industry_min:
        print(f"  行业板块数量不足 ({len(industry_sectors)}/{industry_min})，尝试缓存 fallback...")
        fallback = cache.find_fallback_cache(
            cache_key, as_of_date, fallback_cache_days, industry_min
        )
        if fallback and "data" in fallback:
            fallback_data = fallback["data"]
            fallback_industry = _dict_list_to_sectors(
                fallback_data.get("industry_sectors", []),
                SectorType.INDUSTRY
            )
            if len(fallback_industry) > len(industry_sectors):
                industry_sectors = fallback_industry
                cache_info["is_fallback"] = True
                cache_info["fallback_source"] = cache_info.get("fallback_source") or "raw_snapshot_cache"
                cache_info["source_as_of_date"] = fallback.get("metadata", {}).get("source_as_of_date")
                if provider_status is not None:
                    provider_status.fallback_used = True
                    provider_status.fallback_provider = "raw_snapshot_cache"
                    provider_status.fallback_reason = "行业实时接口数据不足，使用 raw_snapshot_cache"
                    provider_status.industry_count = len(industry_sectors)
    if not offline_fixture and len(concept_sectors) < concept_min:
        history_sectors, history_meta = _load_sector_history_fallback(
            cache.cache_dir,
            SectorType.CONCEPT,
            as_of_date,
            top_n * 2,
        )
        if len(history_sectors) > len(concept_sectors):
            print(
                f"  使用 sector_history fallback 补充概念板块: "
                f"{len(history_sectors)} 个 (source_as_of_date={history_meta.get('source_as_of_date')})"
            )
            concept_sectors = history_sectors
            cache_info["is_fallback"] = True
            cache_info["fallback_source"] = "sector_history_cache"
            cache_info["concept_source_as_of_date"] = history_meta.get("source_as_of_date")
            if not cache_info.get("source_as_of_date"):
                cache_info["source_as_of_date"] = history_meta.get("source_as_of_date")
            if provider_status is not None:
                provider_status.fallback_used = True
                provider_status.fallback_provider = "sector_history_cache"
                if not provider_status.fallback_reason:
                    provider_status.fallback_reason = "概念实时接口数据不足，使用 sector_history_cache"
                provider_status.concept_source = "sector_history/ths_concept_index"
                provider_status.concept_count = len(concept_sectors)
                provider_status.concept_price_change_available = True

    if not offline_fixture and len(concept_sectors) < concept_min:
        print(f"  概念板块数量不足 ({len(concept_sectors)}/{concept_min})，尝试缓存 fallback...")
        fallback = cache.find_fallback_cache(
            cache_key, as_of_date, fallback_cache_days, concept_min
        )
        if fallback and "data" in fallback:
            fallback_data = fallback["data"]
            fallback_concept = _dict_list_to_sectors(
                fallback_data.get("concept_sectors", []),
                SectorType.CONCEPT
            )
            if len(fallback_concept) > len(concept_sectors):
                concept_sectors = fallback_concept
                cache_info["is_fallback"] = True
                cache_info["fallback_source"] = cache_info.get("fallback_source") or "raw_snapshot_cache"
                if not cache_info["source_as_of_date"]:
                    cache_info["source_as_of_date"] = fallback.get("metadata", {}).get("source_as_of_date")
                if provider_status is not None:
                    provider_status.fallback_used = True
                    provider_status.fallback_provider = "raw_snapshot_cache"
                    if not provider_status.fallback_reason:
                        provider_status.fallback_reason = "概念实时接口数据不足，使用 raw_snapshot_cache"
                    provider_status.concept_count = len(concept_sectors)

    if not offline_fixture:
        cache_data = {
            "industry_sectors": [s.model_dump() for s in industry_sectors],
            "concept_sectors": [s.model_dump() for s in concept_sectors],
            "market_data": market_data,
        }
        # 确定实际数据源
        actual_sources = ["akshare/eastmoney"]
        if provider_status and provider_status.fallback_used:
            actual_sources = [provider_status.industry_source, provider_status.concept_source]

        cache.set(
            cache_key,
            cache_data,
            as_of_date=as_of_date,
            metadata={
                "provider": "akshare",
                "created_at": datetime.now().isoformat(),
                "as_of_date": as_of_date,
                "data_sources": actual_sources,
                "is_fallback": False,
            }
        )
        cache_info["cache_created_at"] = datetime.now().isoformat()

    return industry_sectors, concept_sectors, market_data, cache_info, provider_status


def _dict_list_to_sectors(
    dict_list: List[Dict[str, Any]],
    sector_type: SectorType
) -> list:
    """将字典列表转换为 SectorSnapshot 列表"""
    from .models import SectorSnapshot
    return [SectorSnapshot(**d) for d in dict_list]


def _load_sector_history_fallback(
    cache_dir: str,
    sector_type: SectorType,
    as_of_date: str,
    top_n: int,
) -> Tuple[List[Any], Dict[str, Any]]:
    """Load sector history cache as daily fallback without lookahead."""
    from .models import SectorSnapshot

    type_dir = "industry" if sector_type == SectorType.INDUSTRY else "concept"
    history_dir = os.path.join(cache_dir, "sector_history", type_dir)
    meta = {
        "fallback_source": "sector_history_cache",
        "source_as_of_date": None,
        "available_count": 0,
    }
    if not os.path.isdir(history_dir):
        return [], meta

    def _field(record: Dict[str, Any], *names: str) -> Any:
        for name in names:
            if name in record:
                return record.get(name)
        return None

    def _to_float(value: Any) -> float:
        if value is None or value == "":
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    source_name = (
        "sector_history/ths_industry_index"
        if sector_type == SectorType.INDUSTRY
        else "sector_history/ths_concept_index"
    )
    sector_id_prefix = (
        "sector_history_industry"
        if sector_type == SectorType.INDUSTRY
        else "sector_history_concept"
    )

    sectors = []
    source_dates = []
    for filename in os.listdir(history_dir):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(history_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        records = payload.get("records", [])
        usable_records = [
            record for record in records
            if str(_field(record, "日期", "date", "trade_date") or "") <= as_of_date
        ]
        if not usable_records:
            continue

        latest = usable_records[-1]
        previous = usable_records[-2] if len(usable_records) >= 2 else None
        latest_date = str(_field(latest, "日期", "date", "trade_date") or "")
        latest_close = _to_float(_field(latest, "收盘价", "close", "收盘"))
        previous_close = _to_float(_field(previous, "收盘价", "close", "收盘")) if previous else 0.0
        change_pct = 0.0
        if previous_close:
            change_pct = round((latest_close - previous_close) / previous_close * 100, 4)
        turnover = _to_float(_field(latest, "成交额", "amount", "turnover"))
        name = str(payload.get("sector_name") or os.path.splitext(filename)[0])
        sectors.append(
            SectorSnapshot(
                sector_id=f"{sector_id_prefix}_{name}",
                name=name,
                type=sector_type,
                price_change_pct=change_pct,
                turnover=turnover,
                main_net_inflow=0.0,
                constituents=[],
                data_sources=[source_name],
                updated_at=latest_date,
                data_quality_score=85.0 if latest_date == as_of_date else 80.0,
                price_change_available=True,
            )
        )
        source_dates.append(latest_date)

    sectors.sort(key=lambda s: s.price_change_pct, reverse=True)
    meta["available_count"] = len(sectors)
    if source_dates:
        meta["source_as_of_date"] = max(source_dates)
    return sectors[:top_n], meta


def _enrich_fund_flow(
    provider: DataProvider,
    industry_sectors: list,
    concept_sectors: list,
    as_of_date: str,
    offline_fixture: bool,
) -> dict:
    """
    关联资金流数据

    Returns:
        资金流覆盖率信息
    """
    coverage = {
        "industry_matched": 0,
        "concept_matched": 0,
        "unmatched": 0,
        "status": "ok",
    }

    if offline_fixture:
        return coverage

    # 尝试获取资金流数据
    try:
        from .data.akshare_provider import AkShareProvider
        if not isinstance(provider, AkShareProvider):
            return coverage

        # 获取行业资金流
        industry_flow_result = provider.get_sector_flows(as_of_date, SectorType.INDUSTRY)
        if industry_flow_result.status == "ok" and industry_flow_result.data:
            flow_dict = {f["sector_name"]: f for f in industry_flow_result.data}
            for sector in industry_sectors:
                if sector.name in flow_dict:
                    sector.main_net_inflow = flow_dict[sector.name].get("main_net_inflow", 0.0)
                    coverage["industry_matched"] += 1
                else:
                    coverage["unmatched"] += 1

        # 获取概念资金流
        concept_flow_result = provider.get_sector_flows(as_of_date, SectorType.CONCEPT)
        if concept_flow_result.status == "ok" and concept_flow_result.data:
            flow_dict = {f["sector_name"]: f for f in concept_flow_result.data}
            for sector in concept_sectors:
                if sector.name in flow_dict:
                    sector.main_net_inflow = flow_dict[sector.name].get("main_net_inflow", 0.0)
                    coverage["concept_matched"] += 1
                else:
                    coverage["unmatched"] += 1

    except Exception as e:
        coverage["status"] = "degraded"
        warnings.warn(f"资金流关联失败: {str(e)}")

    return coverage


def _enrich_constituents(
    provider: DataProvider,
    industry_scores: List[SectorScore],
    concept_scores: List[SectorScore],
    offline_fixture: bool,
) -> dict:
    """
    补充 Top N 板块的成分股

    Returns:
        成分股覆盖率信息
    """
    coverage = {
        "enriched_count": 0,
        "total_candidates": len(industry_scores) + len(concept_scores),
        "coverage_rate": 0.0,
        "status": "ok",
    }

    if offline_fixture:
        # Fixture 模式下已有成分股数据
        coverage["enriched_count"] = coverage["total_candidates"]
        coverage["coverage_rate"] = 100.0
        return coverage

    try:
        from .data.akshare_provider import AkShareProvider
        if not isinstance(provider, AkShareProvider):
            return coverage

        # 补充行业板块成分股
        for score in industry_scores:
            if not score.constituents:
                result = provider.get_sector_constituents(score.name, SectorType.INDUSTRY)
                if result.status == "ok" and result.data:
                    from .models import ConstituentSnapshot
                    score.constituents = [
                        ConstituentSnapshot(**c) for c in result.data[:10]
                    ]
                    coverage["enriched_count"] += 1
                # 失败时不崩溃，保持空列表

        # 补充概念板块成分股
        for score in concept_scores:
            if not score.constituents:
                result = provider.get_sector_constituents(score.name, SectorType.CONCEPT)
                if result.status == "ok" and result.data:
                    from .models import ConstituentSnapshot
                    score.constituents = [
                        ConstituentSnapshot(**c) for c in result.data[:10]
                    ]
                    coverage["enriched_count"] += 1
                # 失败时不崩溃，保持空列表

    except Exception as e:
        coverage["status"] = "degraded"
        warnings.warn(f"成分股补充失败: {str(e)}")

    # 计算覆盖率
    if coverage["total_candidates"] > 0:
        coverage["coverage_rate"] = (coverage["enriched_count"] / coverage["total_candidates"]) * 100

    return coverage


def _determine_report_status(
    industry_count: int,
    concept_count: int,
    config: dict,
) -> str:
    """确定报告状态"""
    industry_min = config.get("industry_min_count", 20)
    concept_min = config.get("concept_min_count", 20)

    if industry_count == 0 and concept_count == 0:
        return "failed"
    elif industry_count < industry_min // 2 or concept_count < concept_min // 2:
        return "degraded"
    elif industry_count < industry_min or concept_count < concept_min:
        return "degraded"
    else:
        return "ok"


def _get_data_sources(
    provider_name: str,
    offline_fixture: bool,
    industry_sectors: list = None,
    concept_sectors: list = None,
) -> List[str]:
    """获取数据来源列表"""
    if offline_fixture or provider_name == "fixture":
        return ["fixture"]
    elif provider_name == "akshare":
        # 从实际数据中提取来源
        sources = set()
        if industry_sectors:
            for s in industry_sectors:
                if hasattr(s, 'data_sources') and s.data_sources:
                    sources.update(s.data_sources)
        if concept_sectors:
            for s in concept_sectors:
                if hasattr(s, 'data_sources') and s.data_sources:
                    sources.update(s.data_sources)
        if sources:
            return list(sources)
        # 默认
        return ["akshare/eastmoney_industry", "akshare/eastmoney_concept"]
    return ["unknown"]


def _save_reports(
    output_dir: str,
    as_of_date: str,
    market_temperature: MarketTemperature,
    industry_top: List[SectorScore],
    concept_top: List[SectorScore],
    overlap: List[ResonanceResult],
    data_sources: List[str],
    data_quality_score: float,
    context: RadarContext,
    status: str = "ok",
    cache_info: dict = None,
    fund_flow_coverage: dict = None,
    constituent_coverage: dict = None,
    industry_count: int = 0,
    concept_count: int = 0,
    rotation_summary: dict = None,
    comparison_info: dict = None,
    run_mode: str = "normal",
    provider_name: str = "fixture",
    offline_fixture: bool = False,
    fixture_profile: str = None,
    data_source_mode: str = "fixture",
    command_args: str = "",
    provider_status=None,
    warnings: List[str] = None,
    industry_three_layer_shadow_summary: dict = None,
):
    """保存报告文件"""
    os.makedirs(output_dir, exist_ok=True)

    # 保存 JSON
    json_path = os.path.join(output_dir, "theme_sector_radar.json")
    json_report = generate_json_report(
        as_of_date=as_of_date,
        market_temperature=market_temperature,
        industry_top=industry_top,
        concept_top=concept_top,
        overlap=overlap,
        data_sources=data_sources,
        data_quality_score=data_quality_score,
        status=status,
        cache_info=cache_info,
        fund_flow_coverage=fund_flow_coverage,
        constituent_coverage=constituent_coverage,
        industry_count=industry_count,
        concept_count=concept_count,
        rotation_summary=rotation_summary,
        comparison=comparison_info,
        run_mode=run_mode,
        provider=provider_name,
        offline_fixture=offline_fixture,
        fixture_profile=fixture_profile,
        data_source_mode=data_source_mode,
        report_dir=output_dir,
        generated_by_command=command_args,
        provider_status=provider_status,
        warnings=warnings,
        industry_three_layer_shadow_summary=industry_three_layer_shadow_summary,
    )
    save_json_report(json_report, json_path)
    print(f"JSON 报告已保存: {json_path}")

    # 保存 Markdown
    md_path = os.path.join(output_dir, "theme_sector_radar.md")
    md_report = generate_markdown_report(
        as_of_date=as_of_date,
        market_temperature=market_temperature,
        industry_top=industry_top,
        concept_top=concept_top,
        overlap=overlap,
        data_quality_score=data_quality_score,
        status=status,
        cache_info=cache_info,
        fund_flow_coverage=fund_flow_coverage,
        constituent_coverage=constituent_coverage,
        industry_count=industry_count,
        concept_count=concept_count,
        rotation_summary=rotation_summary,
        comparison=comparison_info,
        provider_status=provider_status,
        warnings=warnings,
    )
    save_markdown_report(md_report, md_path)
    print(f"Markdown 报告已保存: {md_path}")

    # 保存原始快照
    snapshot_path = os.path.join(output_dir, "raw_snapshot.json")

    # 自定义序列化器，处理 dataclass 等不可 JSON 序列化的对象
    def _default_serializer(obj):
        """自定义序列化器"""
        # 处理 dataclass
        if hasattr(obj, '__dataclass_fields__'):
            return {k: getattr(obj, k) for k in obj.__dataclass_fields__}
        # 处理 Pydantic 模型
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        # 处理其他不可序列化的对象
        return str(obj)

    save_json_report(
        context.model_dump(),
        snapshot_path,
        default=_default_serializer,
    )
    print(f"原始快照已保存: {snapshot_path}")


def _build_report(
    as_of_date: str,
    market_temperature: MarketTemperature,
    industry_top: List[SectorScore],
    concept_top: List[SectorScore],
    overlap: List[ResonanceResult],
    data_sources: List[str],
    data_quality_score: float,
    status: str = "ok",
    cache_info: dict = None,
    fund_flow_coverage: dict = None,
    constituent_coverage: dict = None,
    industry_count: int = 0,
    concept_count: int = 0,
    rotation_result=None,
    comparison_info: dict = None,
    run_mode: str = "normal",
    provider_name: str = "fixture",
    offline_fixture: bool = False,
    fixture_profile: str = None,
    report_dir: str = None,
    command_args: str = "",
    provider_status=None,
    warnings: List[str] = None,
    industry_three_layer_shadow_summary: dict = None,
) -> RadarReport:
    """构建最终报告"""
    from .models import DataCompleteness, ProviderStatus

    # 构建 rotation_summary
    rotation_summary = {}
    if rotation_result:
        rotation_summary = {
            "industry": rotation_result.industry_rotation,
            "concept": rotation_result.concept_rotation,
        }

    # 确定 data_source_mode
    if offline_fixture:
        data_source_mode = "fixture"
    elif provider_name == "akshare":
        if cache_info and cache_info.get("is_fallback"):
            data_source_mode = "cache_fallback"
        elif cache_info and cache_info.get("cache_created_at"):
            data_source_mode = "cache_replay"
        else:
            data_source_mode = "akshare_refresh"
    else:
        data_source_mode = "unknown"

    # 构建 provider_status
    if provider_status is not None:
        # 从 AkShareProvider 的 ProviderStatusInfo 转换为 ProviderStatus 模型
        ps = ProviderStatus(
            industry_sectors="ok" if provider_status.industry_count > 0 else "failed",
            concept_sectors="ok" if provider_status.concept_count > 0 else "failed",
            effective_provider=provider_status.effective_provider,
            industry_source=provider_status.industry_source,
            concept_source=provider_status.concept_source,
            fallback_used=provider_status.fallback_used,
            fallback_provider=provider_status.fallback_provider,
            fallback_reason=provider_status.fallback_reason,
            industry_count=provider_status.industry_count,
            concept_count=provider_status.concept_count,
            em_industry_error=provider_status.em_industry_error,
            em_concept_error=provider_status.em_concept_error,
            concept_price_change_available=provider_status.concept_price_change_available,
        )
    else:
        ps = ProviderStatus()

    return RadarReport(
        as_of_date=as_of_date,
        updated_at=datetime.now().isoformat(),
        data_sources=data_sources,
        data_quality_score=data_quality_score,
        market_temperature=market_temperature,
        industry_top=industry_top,
        concept_top=concept_top,
        overlap=overlap,
        status=status,
        provider_status=ps,
        data_completeness=DataCompleteness(
            industry_count=industry_count,
            concept_count=concept_count,
        ),
        cache_fallback=cache_info or {},
        fund_flow_coverage=fund_flow_coverage or {},
        constituent_coverage=constituent_coverage or {},
        rotation_summary=rotation_summary,
        comparison=comparison_info or {},
        run_mode=run_mode,
        provider=provider_name,
        offline_fixture=offline_fixture,
        fixture_profile=fixture_profile,
        data_source_mode=data_source_mode,
        report_dir=report_dir or "",
        generated_by_command=command_args,
        warnings=warnings or [],
        industry_three_layer_shadow_summary=(
            industry_three_layer_shadow_summary or {}
        ),
    )


def _get_comparison_source(
    compare_to: str,
    lookback_days: int,
    previous_snapshot: Any,
) -> str:
    """获取比较数据来源"""
    if compare_to:
        return f"specified_date:{compare_to}"
    elif previous_snapshot:
        return f"lookback:{lookback_days}days"
    else:
        return "none"


def _apply_rotation_ranks(
    scores: List[SectorScore],
    details: List[Dict[str, Any]],
) -> None:
    """Preserve already-computed rotation ranks on report sector rows."""
    details_by_id = {item.get("sector_id"): item for item in details}
    for score in scores:
        detail = details_by_id.get(score.sector_id)
        if detail is None:
            continue
        score.current_rank = detail.get("current_rank")
        score.rank_tied = bool(detail.get("rank_tied", False))
        score.rank_tie_count = int(detail.get("rank_tie_count", 1))
        score.previous_rank = detail.get("previous_rank")
        score.rank_change = detail.get("rank_change")
