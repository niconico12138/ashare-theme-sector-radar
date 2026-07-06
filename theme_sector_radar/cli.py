"""
命令行入口

Theme Sector Radar CLI。
支持 daily 日报模式和 replay-cache 缓存回放模式。
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from . import __version__
from .models import SectorType
from .pipeline import run_pipeline


def get_latest_trading_date() -> str:
    """获取最近交易日"""
    today = datetime.now()
    return today.strftime("%Y-%m-%d")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="A股行业/概念板块雷达 - 独立盘后分析系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 离线 fixture 模式
  python -m theme_sector_radar.cli --as-of 2026-06-28 --top-n 10 --offline-fixture

  # 日报模式
  python -m theme_sector_radar.cli --daily --as-of 2026-06-28 --provider akshare --refresh

  # 缓存回放模式
  python -m theme_sector_radar.cli --replay-cache --start-date 2026-06-24 --end-date 2026-06-28
        """
    )

    parser.add_argument(
        "--as-of",
        type=str,
        default=None,
        help="分析日期，默认最近交易日"
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="行业和概念分别输出数量，默认 10"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="报告输出目录"
    )
    parser.add_argument(
        "--offline-fixture",
        action="store_true",
        help="使用本地 fixture 数据"
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["fixture", "akshare"],
        default="fixture",
        help="数据提供者，默认 fixture"
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="优先使用缓存数据"
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="强制刷新数据"
    )
    parser.add_argument(
        "--fallback-cache-days",
        type=int,
        default=7,
        help="缓存 fallback 回退天数，默认 7"
    )
    parser.add_argument(
        "--fixture-profile",
        type=str,
        choices=["full", "minimal", "rotation-day1", "rotation-day2"],
        default="full",
        help="Fixture 数据 profile"
    )
    parser.add_argument(
        "--compare-to",
        type=str,
        default=None,
        help="指定比较日期 (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=5,
        help="回溯天数，默认 5"
    )
    # Phase 13: unified pipeline integration
    parser.add_argument(
        "--include-unified-pipeline",
        action="store_true",
        help="在 daily 报告中嵌入 unified_pipeline 联合观察池与数据健康信息"
    )
    parser.add_argument(
        "--unified-mode",
        type=str,
        choices=["quick", "deep"],
        default="quick",
        help="unified_pipeline 运行模式 (默认: quick)"
    )
    parser.add_argument(
        "--daily",
        action="store_true",
        help="日报模式"
    )
    parser.add_argument(
        "--replay-cache",
        action="store_true",
        help="缓存回放模式"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="开始日期 (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="结束日期 (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--report-root",
        type=str,
        default="reports/theme_sector_radar",
        help="报告根目录"
    )
    parser.add_argument(
        "--download-sector-history",
        action="store_true",
        help="下载板块历史数据"
    )
    parser.add_argument(
        "--sector-type",
        type=str,
        choices=["industry", "concept", "both"],
        default="industry",
        help="板块类型"
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="指定板块名称列表，逗号分隔。PowerShell 中必须加引号: --symbols \"000001,002594\"，否则前导零会丢失"
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.0,
        help="请求间 sleep 秒数"
    )
    parser.add_argument(
        "--score-sectors",
        action="store_true",
        help="板块综合评分模式"
    )
    parser.add_argument(
        "--score-sectors-range",
        action="store_true",
        help="批量板块综合评分模式"
    )
    parser.add_argument(
        "--multi-window-consensus",
        action="store_true",
        help="多窗口趋势共识模式"
    )
    parser.add_argument(
        "--reuse-window-reports",
        action="store_true",
        help="复用已有窗口报告 (默认不复用，重新生成)"
    )
    parser.add_argument(
        "--research-agents",
        action="store_true",
        help="板块综合研判模式"
    )
    parser.add_argument(
        "--backtest-research-agents",
        action="store_true",
        help="Agent 组复盘评估模式"
    )
    parser.add_argument(
        "--backtest-agent-layers",
        action="store_true",
        help="分层 Agent 回测模式"
    )
    parser.add_argument(
        "--analyze-opportunity-rebound",
        action="store_true",
        help="Opportunity Score and Rebound Label 归因分析"
    )
    parser.add_argument(
        "--analyze-market-regime",
        action="store_true",
        help="Market Regime Layer 分层回测分析"
    )
    parser.add_argument(
        "--build-research-index",
        action="store_true",
        help="构建多日 sector_research 索引"
    )
    parser.add_argument(
        "--analyze-agent-reliability",
        action="store_true",
        help="Agent 可靠性评估"
    )
    parser.add_argument(
        "--analyze-persistence-signals",
        action="store_true",
        help="持续性信号研究"
    )
    parser.add_argument(
        "--research-catalyst-sources",
        action="store_true",
        help="外部催化数据源研究"
    )
    parser.add_argument(
        "--download-catalyst-events",
        action="store_true",
        help="下载催化事件数据"
    )
    parser.add_argument(
        "--network",
        action="store_true",
        help="启用网络下载 (AkShare stock_news_em)"
    )
    parser.add_argument(
        "--auto-symbols-from-research",
        action="store_true",
        help="从 sector_research 自动选择 symbols"
    )
    parser.add_argument(
        "--top-sectors",
        type=int,
        default=10,
        help="重点板块数"
    )
    parser.add_argument(
        "--max-symbols-per-sector",
        type=int,
        default=3,
        help="每板块最大 symbols"
    )
    parser.add_argument(
        "--max-symbols-total",
        type=int,
        default=50,
        help="全局最大 symbols"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="跳过已存在的缓存"
    )
    parser.add_argument(
        "--backtest-catalyst-events",
        action="store_true",
        help="CatalystEventAgent 信号验证"
    )
    parser.add_argument(
        "--daily-health-check",
        action="store_true",
        help="每日健康检查"
    )
    parser.add_argument(
        "--generate-research-range",
        action="store_true",
        help="批量生成多日 Agent 组研判报告"
    )
    parser.add_argument(
        "--replay-daily-from-sector-history",
        action="store_true",
        help="从 sector_history 历史数据生成日报"
    )
    parser.add_argument(
        "--history-start-date",
        type=str,
        default=None,
        help="历史数据开始日期 (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--history-end-date",
        type=str,
        default=None,
        help="历史数据结束日期 (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--history-root",
        type=str,
        default="data_cache/sector_history",
        help="历史数据根目录"
    )
    parser.add_argument(
        "--analysis-root",
        type=str,
        default="reports/backtests/sector_history",
        help="历史分析输出根目录"
    )
    parser.add_argument(
        "--score-output",
        type=str,
        default="reports/sector_scores",
        help="综合评分输出目录"
    )
    parser.add_argument(
        "--history-lookback-days",
        type=int,
        default=10,
        help="批量评分时每个 as_of 往前看的历史天数"
    )
    parser.add_argument(
        "--batch-output",
        type=str,
        default="reports/sector_scores_batch",
        help="批量评分汇总输出目录"
    )
    parser.add_argument(
        "--cache-root",
        type=str,
        default="data_cache",
        help="缓存根目录 (用于 raw_snapshot fallback)"
    )
    parser.add_argument(
        "--score-mode",
        type=str,
        choices=["composite", "dual"],
        default="dual",
        help="评分模式: composite (仅趋势持续分) 或 dual (双评分)"
    )
    parser.add_argument(
        "--trend-weight-profile",
        type=str,
        choices=["baseline", "trend_confirmation"],
        default="baseline",
        help="趋势权重 profile: baseline (默认) 或 trend_confirmation (趋势确认型)"
    )
    parser.add_argument(
        "--trend-window",
        type=int,
        choices=[5, 10, 20],
        default=10,
        help="趋势窗口: 5/10/20 个交易日 (默认 10)"
    )
    parser.add_argument(
        "--benchmark",
        type=str,
        choices=["hs300", "zz500", "zz1000", "none"],
        default="none",
        help="市场基准 (hs300/zz500/zz1000/none)"
    )
    parser.add_argument(
        "--benchmark-root",
        type=str,
        default="data_cache/benchmarks",
        help="基准缓存根目录"
    )
    parser.add_argument(
        "--benchmark-refresh",
        action="store_true",
        help="强制刷新基准数据"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    args = parser.parse_args()

    # 处理 provider
    provider_name = args.provider
    if args.offline_fixture:
        provider_name = "fixture"

    # download-sector-history 模式
    if args.download_sector_history:
        _run_download(args)
        return

    # score-sectors 模式
    if args.score_sectors:
        _run_score_sectors(args)
        return

    # score-sectors-range 模式
    if args.score_sectors_range:
        _run_score_sectors_range(args)
        return

    # multi-window-consensus 模式
    if args.multi_window_consensus:
        _run_multi_window_consensus(args)
        return

    # research-agents 模式
    if args.research_agents:
        _run_research_agents(args)
        return

    # backtest-research-agents 模式
    if args.backtest_research_agents:
        _run_backtest_research_agents(args)
        return

    # backtest-agent-layers 模式
    if args.backtest_agent_layers:
        _run_backtest_agent_layers(args)
        return

    # analyze-opportunity-rebound 模式
    if args.analyze_opportunity_rebound:
        _run_analyze_opportunity_rebound(args)
        return

    # analyze-market-regime 模式
    if args.analyze_market_regime:
        _run_analyze_market_regime(args)
        return

    # build-research-index 模式
    if args.build_research_index:
        _run_build_research_index(args)
        return

    # analyze-agent-reliability 模式
    if args.analyze_agent_reliability:
        _run_analyze_agent_reliability(args)
        return

    # analyze-persistence-signals 模式
    if args.analyze_persistence_signals:
        _run_analyze_persistence_signals(args)
        return

    # research-catalyst-sources 模式
    if args.research_catalyst_sources:
        _run_research_catalyst_sources(args)
        return

    # download-catalyst-events 模式
    if args.download_catalyst_events:
        _run_download_catalyst_events(args)
        return

    # backtest-catalyst-events 模式
    if args.backtest_catalyst_events:
        _run_backtest_catalyst_events(args)
        return

    # daily-health-check 模式
    if args.daily_health_check:
        _run_daily_health_check(args)
        return

    # generate-research-range 模式
    if args.generate_research_range:
        _run_generate_research_range(args)
        return

    # replay-daily-from-sector-history 模式
    if args.replay_daily_from_sector_history:
        _run_replay_daily_from_sector_history(args)
        return

    # replay-cache 模式
    if args.replay_cache:
        _run_replay_cache(args, provider_name)
        return

    # daily 模式或普通模式
    _run_single(args, provider_name)


def _build_unified_markdown_section(as_of_date: str, obs_pool: dict, ds: dict, rh: dict) -> str:
    """Build a Markdown section for unified pipeline results (Phase 13)."""
    lines = []
    lines.append("---")
    lines.append("")
    lines.append("## 联合观察池 (Unified Pipeline)")
    lines.append("")
    lines.append(f"**模式**: {obs_pool.get('mode', 'quick')}  |  **日期**: {as_of_date}")
    lines.append("")
    lines.append("> ⚠️ 以下为板块雷达 + 个股选股联合管线的研究候选池，**不作为操作依据或买卖推荐**。")
    lines.append("")

    # Health gate
    if rh:
        icon = {"pass": "✅", "warn": "⚠️", "fail": "❌"}.get(rh.get("status", ""), "")
        lines.append(f"### {icon} 健康门禁: {rh.get('status', '?').upper()}")
        reasons = rh.get("reasons", [])
        for r in reasons:
            lines.append(f"- {r}")
        lines.append("")

    # Data source
    if ds:
        lines.append("### 数据来源")
        csrc = ds.get("constituent_sources", {})
        qsrc = ds.get("quant_score_sources", {})
        if csrc:
            parts = [f"{k}={v}" for k, v in sorted(csrc.items()) if v]
            lines.append(f"- 成分股来源: {', '.join(parts)}")
        if qsrc:
            parts = [f"{k}={v}" for k, v in sorted(qsrc.items()) if v]
            lines.append(f"- 量化评分: {', '.join(parts)}")
        lines.append("")

    # Trend candidates
    trend = obs_pool.get("trend_top_stocks", [])
    if trend:
        lines.append("### 趋势观察候选 Top{}".format(min(len(trend), 10)))
        lines.append("")
        lines.append("| # | 代码 | 名称 | 综合分 | 量化分 | 关联度 | 板块 |")
        lines.append("|---|------|------|--------|--------|--------|------|")
        for i, s in enumerate(trend[:10], 1):
            lines.append(
                f"| {i} | {s.get('code','')} | {s.get('name','')} | "
                f"{s.get('final_score',0):.1f} | {s.get('quant_score',0):.1f} | "
                f"{s.get('relevance_score',0):.3f} | {s.get('sector_name','')} |"
            )
        lines.append("")

    # Burst candidates
    burst = obs_pool.get("burst_top_stocks", [])
    if burst:
        lines.append("### 短线观察候选 Top{}".format(min(len(burst), 10)))
        lines.append("")
        lines.append("| # | 代码 | 名称 | 综合分 | 量化分 | 关联度 | 板块 |")
        lines.append("|---|------|------|--------|--------|--------|------|")
        for i, s in enumerate(burst[:10], 1):
            lines.append(
                f"| {i} | {s.get('code','')} | {s.get('name','')} | "
                f"{s.get('final_score',0):.1f} | {s.get('quant_score',0):.1f} | "
                f"{s.get('relevance_score',0):.3f} | {s.get('sector_name','')} |"
            )
        lines.append("")

    return "\n".join(lines)


def _run_single(args, provider_name: str):
    """运行单次分析"""
    # 处理日期
    as_of_date = args.as_of or get_latest_trading_date()

    # daily 模式：输出到固定 YYYY-MM-DD 目录
    if args.daily:
        output_dir = os.path.join(args.report_root, as_of_date)
    elif args.output:
        output_dir = args.output
    else:
        output_dir = os.path.join(args.report_root, as_of_date)

    print(f"Theme Sector Radar v{__version__}")
    print(f"分析日期: {as_of_date}")
    print(f"Top N: {args.top_n}")
    print(f"输出目录: {output_dir}")
    print(f"数据提供者: {provider_name}")
    print(f"日报模式: {args.daily}")
    print("-" * 50)

    started_at = datetime.now()
    started_at_str = started_at.isoformat()

    # 确定 run_mode
    run_mode = "daily" if args.daily else "normal"
    command_args = " ".join(sys.argv[1:])

    try:
        report = run_pipeline(
            as_of_date=as_of_date,
            top_n=args.top_n,
            output_dir=output_dir,
            offline_fixture=args.offline_fixture,
            use_cache=args.use_cache,
            refresh=args.refresh,
            provider_name=provider_name,
            fallback_cache_days=args.fallback_cache_days,
            fixture_profile=args.fixture_profile,
            compare_to=args.compare_to,
            lookback_days=args.lookback_days,
            run_mode=run_mode,
            report_root=args.report_root,
        )

        finished_at = datetime.now()
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        print("-" * 50)
        print("分析完成!")
        print(f"报告状态: {getattr(report, 'status', 'ok')}")
        print(f"市场温度: {report.market_temperature.label} ({report.market_temperature.score:.0f}/100)")
        print(f"行业 Top 3: {', '.join(s.name for s in report.industry_top[:3]) if report.industry_top else '无'}")
        print(f"概念 Top 3: {', '.join(s.name for s in report.concept_top[:3]) if report.concept_top else '无'}")
        print(f"数据质量: {report.data_quality_score:.0f}/100")

        # ------------------------------------------------------------------
        # Phase 13: optionally embed unified_pipeline results
        # ------------------------------------------------------------------
        if args.include_unified_pipeline:
            print()
            print("─" * 50)
            print("运行 Unified Pipeline (联合观察池)...")
            try:
                from unified_pipeline import run_pipeline as run_unified

                trend_n = min(args.top_n, 10)
                burst_n = min(args.top_n, 10)
                unified_result = run_unified(
                    as_of_date=as_of_date,
                    trend_top_n=trend_n,
                    burst_top_n=burst_n,
                    mode=args.unified_mode,
                )
                if unified_result.get("status") == "ok":
                    obs_pool = {
                        "trend_top_stocks": unified_result.get("trend_top_stocks", [])[:10],
                        "burst_top_stocks": unified_result.get("burst_top_stocks", [])[:10],
                        "as_of_date": unified_result.get("as_of_date"),
                        "mode": unified_result.get("mode"),
                    }
                    ds = unified_result.get("data_source")
                    rh = unified_result.get("run_health")

                    # Update RadarReport model
                    report.unified_observation_pool = obs_pool
                    report.unified_data_source = ds
                    report.unified_run_health = rh

                    # Post-process saved JSON file
                    json_path = os.path.join(output_dir, "theme_sector_radar.json")
                    if os.path.exists(json_path):
                        with open(json_path, "r", encoding="utf-8") as f:
                            saved = json.load(f)
                        saved["unified_observation_pool"] = obs_pool
                        saved["unified_data_source"] = ds
                        saved["unified_run_health"] = rh
                        with open(json_path, "w", encoding="utf-8") as f:
                            json.dump(saved, f, ensure_ascii=False, indent=2)
                        print(f"  ✅ JSON 报告已更新 (含联合观察池)")

                    # Post-process Markdown file
                    md_path = os.path.join(output_dir, "theme_sector_radar.md")
                    if os.path.exists(md_path):
                        md_section = _build_unified_markdown_section(
                            as_of_date, obs_pool, ds, rh
                        )
                        with open(md_path, "r", encoding="utf-8") as f:
                            md_content = f.read()
                        with open(md_path, "w", encoding="utf-8") as f:
                            f.write(md_content.rstrip() + "\n\n" + md_section + "\n")
                        print(f"  ✅ Markdown 报告已更新 (含联合观察池)")

                    health_status = rh.get("status", "?") if rh else "?"
                    print(f"  Unified Pipeline 完成: 健康门禁 {health_status.upper()}")
                else:
                    report.unified_pipeline_error = unified_result.get("warnings", ["unknown error"])
                    print(f"  ⚠️  Unified Pipeline 返回非 ok 状态: {unified_result.get('status')}")
            except Exception as ue:
                report.unified_pipeline_error = str(ue)
                print(f"  ⚠️  Unified Pipeline 执行失败 (主流程不受影响): {ue}")

        # 生成 run_log
        if args.daily:
            # 获取 provider_status
            ps = report.provider_status
            # 转换为字典（处理 Pydantic 模型）
            if hasattr(ps, 'model_dump'):
                ps_dict = ps.model_dump()
            else:
                ps_dict = {
                    "effective_provider": ps.effective_provider,
                    "industry_source": ps.industry_source,
                    "concept_source": ps.concept_source,
                    "fallback_used": ps.fallback_used,
                    "fallback_provider": ps.fallback_provider,
                    "fallback_reason": ps.fallback_reason,
                    "industry_count": ps.industry_count,
                    "concept_count": ps.concept_count,
                    "em_industry_error": ps.em_industry_error,
                    "em_concept_error": ps.em_concept_error,
                }
            run_log = {
                "command_args": " ".join(sys.argv[1:]),
                "started_at": started_at_str,
                "finished_at": finished_at.isoformat(),
                "duration_ms": duration_ms,
                "run_mode": run_mode,
                "provider": provider_name,
                "offline_fixture": args.offline_fixture,
                "fixture_profile": args.fixture_profile,
                "data_source_mode": getattr(report, 'data_source_mode', 'unknown'),
                "status": getattr(report, 'status', 'ok'),
                "comparison_status": report.comparison.get('comparison_status', 'none'),
                "cache_fallback_used": report.cache_fallback.get('is_fallback', False),
                "warnings": getattr(report, 'warnings', []),
                "output_files": [
                    "theme_sector_radar.json",
                    "theme_sector_radar.md",
                    "raw_snapshot.json",
                ],
                "report_dir": output_dir,
                "report_root": args.report_root,
                "index_included": True,
                "comparison_source": report.comparison.get('comparison_source', 'none'),
                "input_snapshot_source": "fixture" if args.offline_fixture else "akshare",
                # Provider status tracking
                "provider_status": ps_dict,
            }
            run_log_path = os.path.join(output_dir, "run_log.json")
            os.makedirs(output_dir, exist_ok=True)
            with open(run_log_path, "w", encoding="utf-8") as f:
                json.dump(run_log, f, ensure_ascii=False, indent=2)
            print(f"run_log 已保存: {run_log_path}")

    except Exception as e:
        finished_at = datetime.now()
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        # 生成失败的 run_log
        if args.daily:
            run_log = {
                "command_args": " ".join(sys.argv[1:]),
                "started_at": started_at_str,
                "finished_at": finished_at.isoformat(),
                "duration_ms": duration_ms,
                "provider": provider_name,
                "status": "failed",
                "comparison_status": "none",
                "cache_fallback_used": False,
                "warnings": [str(e)],
                "output_files": [],
            }
            run_log_path = os.path.join(output_dir, "run_log.json")
            os.makedirs(output_dir, exist_ok=True)
            with open(run_log_path, "w", encoding="utf-8") as f:
                json.dump(run_log, f, ensure_ascii=False, indent=2)
            print(f"run_log 已保存: {run_log_path}")

        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


def _run_replay_cache(args, provider_name: str):
    """运行缓存回放"""
    start_date = args.start_date
    end_date = args.end_date

    if not start_date or not end_date:
        print("错误: --replay-cache 需要 --start-date 和 --end-date", file=sys.stderr)
        sys.exit(1)

    print(f"Theme Sector Radar v{__version__} - 缓存回放模式")
    print(f"日期范围: {start_date} ~ {end_date}")
    print(f"报告根目录: {args.report_root}")
    print("-" * 50)

    # 生成日期列表
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    # 逐日回放
    success_count = 0
    failed_count = 0

    for date_str in dates:
        print(f"\n回放 {date_str}...")
        try:
            # 检查是否有缓存
            cache_path = os.path.join("data_cache", date_str, "raw_snapshot.json")
            report_path = os.path.join(args.report_root, date_str, "theme_sector_radar.json")

            has_cache = os.path.exists(cache_path)
            has_report = os.path.exists(report_path)

            if not has_cache and not has_report:
                print(f"  跳过 {date_str}: 无缓存数据")
                # 生成失败的 run_log
                _save_replay_run_log(
                    args.report_root, date_str, "failed",
                    "无缓存数据", []
                )
                failed_count += 1
                continue

            # 运行分析
            output_dir = os.path.join(args.report_root, date_str)
            started_at = datetime.now()
            command_args = f"--replay-cache --start-date {args.start_date} --end-date {args.end_date} --as-of {date_str}"

            report = run_pipeline(
                as_of_date=date_str,
                top_n=args.top_n,
                output_dir=output_dir,
                offline_fixture=False,
                use_cache=True,
                refresh=False,
                provider_name="fixture",  # replay 模式使用 fixture
                fallback_cache_days=args.fallback_cache_days,
                compare_to=None,  # 由 lookback 自动处理
                lookback_days=args.lookback_days,
                run_mode="replay",
                report_root=args.report_root,
            )

            finished_at = datetime.now()
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)

            # 保存 run_log
            run_log = {
                "command_args": command_args,
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "duration_ms": duration_ms,
                "run_mode": "replay",
                "provider": "fixture",
                "offline_fixture": False,
                "fixture_profile": "full",  # replay 模式使用默认 fixture
                "data_source_mode": "cache_replay",
                "status": getattr(report, 'status', 'ok'),
                "comparison_status": report.comparison.get('comparison_status', 'none'),
                "cache_fallback_used": False,
                "warnings": [],
                "output_files": [
                    "theme_sector_radar.json",
                    "theme_sector_radar.md",
                    "raw_snapshot.json",
                ],
                "report_dir": output_dir,
                "report_root": args.report_root,
                "index_included": True,
                "comparison_source": report.comparison.get('comparison_source', 'none'),
                "input_snapshot_source": "cache",
            }
            run_log_path = os.path.join(output_dir, "run_log.json")
            with open(run_log_path, "w", encoding="utf-8") as f:
                json.dump(run_log, f, ensure_ascii=False, indent=2)

            print(f"  完成: {report.status}")
            success_count += 1

        except Exception as e:
            print(f"  失败: {e}")
            _save_replay_run_log(
                args.report_root, date_str, "failed",
                str(e), []
            )
            failed_count += 1

    # 生成索引
    print("\n生成报告索引...")
    _generate_index(args.report_root, dates)

    print("-" * 50)
    print(f"回放完成: 成功 {success_count}, 失败 {failed_count}")
    print(f"索引已生成: {args.report_root}/index.json")


def _save_replay_run_log(
    report_root: str,
    date_str: str,
    status: str,
    error_msg: str,
    output_files: List[str]
):
    """保存 replay run_log"""
    run_log = {
        "command_args": f"--replay-cache --as-of {date_str}",
        "started_at": datetime.now().isoformat(),
        "finished_at": datetime.now().isoformat(),
        "duration_ms": 0,
        "run_mode": "replay",
        "provider": "fixture",
        "offline_fixture": False,
        "fixture_profile": "full",
        "data_source_mode": "cache_replay",
        "status": status,
        "comparison_status": "none",
        "cache_fallback_used": False,
        "warnings": [error_msg] if error_msg else [],
        "output_files": output_files,
        "report_dir": os.path.join(report_root, date_str),
        "report_root": report_root,
        "index_included": True,
        "comparison_source": "none",
        "input_snapshot_source": "cache",
    }
    output_dir = os.path.join(report_root, date_str)
    os.makedirs(output_dir, exist_ok=True)
    run_log_path = os.path.join(output_dir, "run_log.json")
    with open(run_log_path, "w", encoding="utf-8") as f:
        json.dump(run_log, f, ensure_ascii=False, indent=2)


def _run_download(args):
    """运行板块历史数据下载"""
    from .downloader.sector_history_downloader import SectorHistoryDownloader, save_download_summary
    from .models import SectorType

    # 解析 sector_type
    if args.sector_type == "both":
        sector_types = [SectorType.INDUSTRY, SectorType.CONCEPT]
    elif args.sector_type == "industry":
        sector_types = [SectorType.INDUSTRY]
    else:
        sector_types = [SectorType.CONCEPT]

    # 解析 symbols
    symbols = None
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",")]

    # 创建下载器
    downloader = SectorHistoryDownloader(sleep_seconds=args.sleep_seconds)

    print("=" * 60)
    print("Theme Sector Radar - Sector History Download")
    print("=" * 60)
    print(f"Sector Type: {args.sector_type}")
    print(f"Start Date: {args.start_date}")
    print(f"End Date: {args.end_date}")
    if symbols:
        print(f"Symbols: {', '.join(symbols)}")
    else:
        print(f"Top N: {args.top_n}")
    print("-" * 60)

    # 下载数据
    all_summaries = []
    for sector_type in sector_types:
        print(f"\nDownloading {sector_type.value} sectors...")

        summary = downloader.download_sectors(
            sector_type=sector_type,
            start_date=args.start_date,
            end_date=args.end_date,
            symbols=symbols,
            top_n=args.top_n,
            refresh=args.refresh,
        )
        all_summaries.append(summary)

        print(f"  Success: {summary['success_count']}")
        print(f"  Failed: {summary['failed_count']}")
        print(f"  Skipped: {summary['skipped_count']}")

    # 保存摘要
    output_dir = os.path.join("reports", "data_downloads", datetime.now().strftime("%Y-%m-%d"))
    for summary in all_summaries:
        save_download_summary(summary, output_dir)

    print("-" * 60)
    print(f"Download complete! Summary saved to: {output_dir}")


def _run_score_sectors(args):
    """运行板块综合评分"""
    from .models import SectorType, RadarReport
    from .agents.sector_scoring import calculate_sector_scores
    from .agents.sector_diagnosis import diagnose_sector
    from .reports.sector_score_report import generate_sector_score_report, save_sector_score_report
    from .data.benchmark_provider import BenchmarkProvider
    from .data.benchmark_cache import BenchmarkCache

    # 处理日期
    as_of_date = args.as_of or get_latest_trading_date()
    history_start_date, history_end_date, history_resolution = _resolve_history_date_range(
        as_of_date=as_of_date,
        history_start_date=getattr(args, "history_start_date", None),
        history_end_date=getattr(args, "history_end_date", None),
        history_lookback_days=getattr(args, "history_lookback_days", 10),
        trend_window=getattr(args, "trend_window", 10),
    )

    # 解析 sector_type
    if args.sector_type == "both":
        sector_types = [SectorType.INDUSTRY, SectorType.CONCEPT]
    elif args.sector_type == "industry":
        sector_types = [SectorType.INDUSTRY]
    else:
        sector_types = [SectorType.CONCEPT]

    # 获取基准配置
    benchmark_id = args.benchmark if args.benchmark != "none" else None
    benchmark_name = None
    benchmark_data = None
    benchmark_status = "none"

    if benchmark_id:
        benchmark_provider = BenchmarkProvider()
        benchmark_cache = BenchmarkCache(args.benchmark_root)

        # 检查缓存
        if not args.benchmark_refresh and benchmark_cache.has_cache(
            benchmark_id, history_start_date, history_end_date
        ):
            benchmark_data = benchmark_cache.get_cache(
                benchmark_id, history_start_date, history_end_date
            )
            print(f"Loaded benchmark from cache: {benchmark_id}")
        else:
            # 获取基准数据
            print(f"Fetching benchmark data: {benchmark_id}...")
            benchmark_data = benchmark_provider.fetch_benchmark_data(
                benchmark_id, history_start_date, history_end_date
            )

            # 保存缓存
            if benchmark_data.status == "ok":
                benchmark_cache.set_cache(benchmark_data)
                print(f"Benchmark data cached: {benchmark_id}")

        benchmark_status = benchmark_data.status
        benchmark_name = benchmark_data.benchmark_name

    print("=" * 60)
    print("Theme Sector Radar - Sector Composite Scoring")
    print("=" * 60)
    print(f"Date: {as_of_date}")
    print(f"Sector Type: {args.sector_type}")
    print(f"History Start: {history_start_date}")
    print(f"History End: {history_end_date}")
    print(f"Top N: {args.top_n}")
    print(f"Benchmark: {benchmark_id or 'none'} ({benchmark_status})")
    print("-" * 60)

    # 读取日报数据 - 支持多个可能的位置
    report_path = os.path.join(args.report_root, as_of_date, "theme_sector_radar.json")
    if not os.path.exists(report_path):
        # 尝试在 theme_sector_radar 子目录中查找
        report_path = os.path.join(args.report_root, "theme_sector_radar", as_of_date, "theme_sector_radar.json")
    if not os.path.exists(report_path):
        print(f"Error: Report not found: {report_path}")
        sys.exit(1)

    with open(report_path, "r", encoding="utf-8") as f:
        report_data = json.load(f)

    report = RadarReport(**report_data)

    # 读取历史数据
    history_data, history_source, history_warnings = _load_history_data(
        args.history_root,
        history_start_date,
        history_end_date,
        sector_types,
        args.cache_root if hasattr(args, 'cache_root') else "data_cache",
    )

    # 计算综合评分
    all_results = []
    for sector_type in sector_types:
        if sector_type == SectorType.INDUSTRY:
            sectors = report.industry_top
        else:
            sectors = report.concept_top

        # 限制 top_n
        sectors = sectors[:args.top_n]

        if not sectors:
            print(f"No {sector_type.value} sectors found in report")
            continue

        # 计算综合评分
        scoring_output = calculate_sector_scores(
            radar_sectors=sectors,
            history_data=history_data.get(sector_type.value, {}),
            sector_type=sector_type,
            score_mode=args.score_mode,
            benchmark_data=benchmark_data,
            trend_weight_profile=args.trend_weight_profile,
            trend_window=args.trend_window,
        )

        # 诊断每个板块
        for score_data in scoring_output.data.get("scores", []):
            diagnosis = diagnose_sector(score_data, sector_type.value)
            score_data.update(diagnosis)

            # 添加历史数据来源信息
            score_data["history_source"] = history_source
            score_data["history_data_warnings"] = history_warnings

        all_results.extend(scoring_output.data.get("scores", []))

    # 按综合评分排序
    all_results.sort(key=lambda x: x.get("sector_selection_score", 0), reverse=True)

    # 生成报告
    output_dir = os.path.join(args.score_output, as_of_date)
    os.makedirs(output_dir, exist_ok=True)

    run_parameters = {
        "as_of": as_of_date,
        "sector_type": args.sector_type,
        "history_start_date": history_start_date,
        "history_end_date": history_end_date,
        "history_lookback_days": getattr(args, "history_lookback_days", None),
        "history_root": args.history_root,
        "cache_root": getattr(args, "cache_root", "data_cache"),
        "report_root": args.report_root,
        "score_output": args.score_output,
        "top_n": args.top_n,
        "score_mode": args.score_mode,
        "trend_weight_profile": args.trend_weight_profile,
        "trend_window": args.trend_window,
        "benchmark": getattr(args, "benchmark", "none"),
        "benchmark_root": getattr(args, "benchmark_root", None),
        "benchmark_refresh": getattr(args, "benchmark_refresh", False),
    }
    # 生成 JSON 报告
    json_report = {
        "report_type": "sector_scores",
        "version": "0.1.0",
        "as_of_date": as_of_date,
        "updated_at": datetime.now().isoformat(),
        "scores": all_results,
        "metadata": {
            "sector_type": args.sector_type,
            "history_start_date": history_start_date,
            "history_end_date": history_end_date,
            "top_n": args.top_n,
            "history_source": history_source,
            "history_warnings": history_warnings,
            "score_mode": args.score_mode,
            "benchmark_id": benchmark_id,
            "benchmark_name": benchmark_name,
            "benchmark_status": benchmark_status,
            "trend_weight_profile": args.trend_weight_profile,
            "trend_window": args.trend_window,
            "trend_window_description": f"{args.trend_window} 个交易日窗口",
            "input_report_path": os.path.abspath(report_path),
            "report_root": args.report_root,
            "score_output": args.score_output,
            "history_root": args.history_root,
            "cache_root": getattr(args, "cache_root", "data_cache"),
            "history_resolution": history_resolution,
            "run_parameters": run_parameters,
        },
        "disclaimer": "本报告仅用于板块强弱筛选和研究复盘，不作为个股操作依据或自动交易指令。",
    }

    json_path = os.path.join(output_dir, "sector_scores.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_report, f, ensure_ascii=False, indent=2)
    print(f"JSON report saved: {json_path}")

    # 生成 Markdown 报告
    md_report = generate_sector_score_report(json_report)
    md_path = os.path.join(output_dir, "sector_scores.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"Markdown report saved: {md_path}")

    print("-" * 60)
    print("Scoring complete!")

    # 输出 Top 5
    print("\nTop 5 Sectors:")
    for i, score_data in enumerate(all_results[:5], 1):
        level_label = score_data.get('selection_level_cn', score_data.get('selection_level', ''))
        print(f"{i}. {score_data['sector_name']}: {score_data['sector_selection_score']:.1f} ({level_label})")


def _run_score_sectors_range(args):
    """运行批量板块综合评分"""
    from datetime import datetime, timedelta
    from .reports.sector_score_batch_report import (
        generate_batch_summary,
        generate_timeseries_data,
        save_batch_reports,
    )

    # 处理日期范围
    start_date = args.start_date
    end_date = args.end_date

    if not start_date or not end_date:
        print("Error: --start-date and --end-date are required for --score-sectors-range")
        sys.exit(1)

    # 生成日期列表
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    print("=" * 60)
    print("Theme Sector Radar - Batch Sector Scoring")
    print("=" * 60)
    print(f"Date Range: {start_date} ~ {end_date}")
    print(f"Total Dates: {len(dates)}")
    print(f"Sector Type: {args.sector_type}")
    print(f"History Lookback Days: {args.history_lookback_days}")
    print(f"Top N: {args.top_n}")
    print(f"Score Mode: {args.score_mode}")
    print(f"Benchmark: {args.benchmark}")
    print("-" * 60)

    # 批量评分
    completed_dates = []
    skipped_dates = []
    failed_dates = []
    output_dirs = []
    daily_scores = {}

    for as_of_date in dates:
        print(f"\nProcessing {as_of_date}...")

        # 检查日报是否存在
        report_path = os.path.join(args.report_root, as_of_date, "theme_sector_radar.json")
        if not os.path.exists(report_path):
            print(f"  Skipped: missing daily report")
            skipped_dates.append({"date": as_of_date, "reason": "missing_daily_report"})
            continue

        # 计算历史数据日期范围
        history_start, history_end, history_resolution = _resolve_history_date_range(
            as_of_date=as_of_date,
            history_start_date=getattr(args, "history_start_date", None),
            history_end_date=getattr(args, "history_end_date", None),
            history_lookback_days=args.history_lookback_days,
            trend_window=args.trend_window,
        )

        # 创建单日评分参数
        single_args = argparse.Namespace(
            as_of=as_of_date,
            sector_type=args.sector_type,
            history_start_date=history_start,
            history_end_date=history_end,
            history_root=args.history_root,
            top_n=args.top_n,
            score_mode=args.score_mode,
            trend_weight_profile=args.trend_weight_profile,
            trend_window=args.trend_window,
            benchmark=args.benchmark,
            benchmark_root=args.benchmark_root,
            benchmark_refresh=args.benchmark_refresh,
            score_output=args.score_output,
            report_root=args.report_root,
            cache_root=args.cache_root,
        )

        try:
            # 调用单日评分
            _run_score_sectors(single_args)
            completed_dates.append(as_of_date)
            output_dirs.append(os.path.join(args.score_output, as_of_date))

            # 读取评分结果
            score_path = os.path.join(args.score_output, as_of_date, "sector_scores.json")
            if os.path.exists(score_path):
                with open(score_path, "r", encoding="utf-8") as f:
                    daily_scores[as_of_date] = json.load(f)

        except Exception as e:
            print(f"  Failed: {str(e)}")
            failed_dates.append({"date": as_of_date, "reason": str(e)[:100]})

    # 生成汇总报告
    print("\n" + "=" * 60)
    print("Generating batch reports...")
    print("=" * 60)

    batch_summary = generate_batch_summary(
        start_date=start_date,
        end_date=end_date,
        sector_type=args.sector_type,
        score_mode=args.score_mode,
        benchmark=args.benchmark,
        total_dates=len(dates),
        completed_dates=completed_dates,
        skipped_dates=skipped_dates,
        failed_dates=failed_dates,
        output_dirs=output_dirs,
    )

    timeseries_data = generate_timeseries_data(daily_scores)

    # 保存汇总报告
    batch_output_dir = os.path.join(args.batch_output, f"{start_date}_to_{end_date}")
    save_batch_reports(
        batch_output_dir,
        batch_summary,
        daily_scores,
        timeseries_data,
    )

    print("\n" + "=" * 60)
    print("Batch scoring complete!")
    print(f"Completed: {len(completed_dates)}/{len(dates)}")
    print(f"Skipped: {len(skipped_dates)}")
    print(f"Failed: {len(failed_dates)}")
    print("=" * 60)


def _run_multi_window_consensus(args):
    """运行多窗口趋势共识"""
    from .models import SectorType
    from .agents.multi_window_consensus import MultiWindowConsensusAgent
    from .reports.multi_window_consensus_report import save_multi_window_consensus_report

    # 处理日期
    as_of_date = args.as_of or get_latest_trading_date()

    # 多窗口和研判链路固定依赖 5/10/20 窗口，默认历史范围按最大窗口 20 解析
    history_start_date, history_end_date, history_resolution = _resolve_history_date_range(
        as_of_date=as_of_date,
        history_start_date=getattr(args, "history_start_date", None),
        history_end_date=getattr(args, "history_end_date", None),
        history_lookback_days=getattr(args, "history_lookback_days", 10),
        trend_window=20,
    )

    # 解析 sector_type
    if args.sector_type == "both":
        sector_types = [SectorType.INDUSTRY, SectorType.CONCEPT]
    elif args.sector_type == "industry":
        sector_types = [SectorType.INDUSTRY]
    else:
        sector_types = [SectorType.CONCEPT]

    print("=" * 60)
    print("Theme Sector Radar - Multi-Window Consensus")
    print("=" * 60)
    print(f"Date: {as_of_date}")
    print(f"Sector Type: {args.sector_type}")
    print(f"History Start: {history_start_date}")
    print(f"History End: {history_end_date}")
    print(f"Top N: {args.top_n}")
    print(f"Trend Weight Profile: {args.trend_weight_profile}")
    print(f"Benchmark: {args.benchmark}")
    print("-" * 60)

    # 定义窗口
    windows = [5, 10, 20]

    # 创建窗口报告输出目录
    consensus_dir = os.path.join(args.score_output, "..", "sector_consensus", as_of_date)
    windows_dir = os.path.join(consensus_dir, "windows")
    os.makedirs(windows_dir, exist_ok=True)

    # 收集各窗口的评分数据
    all_sectors_data = {}  # {sector_name: {window_key: score_data}}

    for window in windows:
        print(f"\nRunning scoring for trend_window={window}...")

        # 创建窗口专属输出目录
        window_output_dir = os.path.join(windows_dir, str(window))

        # 创建单日评分参数 - 使用用户提供的 history_start_date 和 history_end_date
        single_args = argparse.Namespace(
            as_of=as_of_date,
            sector_type=args.sector_type,
            history_start_date=history_start_date,
            history_end_date=history_end_date,
            history_root=args.history_root,
            top_n=args.top_n,
            score_mode=args.score_mode,
            trend_weight_profile=args.trend_weight_profile,
            trend_window=window,
            benchmark=args.benchmark,
            benchmark_root=args.benchmark_root,
            benchmark_refresh=args.benchmark_refresh,
            score_output=window_output_dir,
            report_root=args.report_root,
            cache_root=args.cache_root,
        )

        try:
            # 运行单日评分
            _run_score_sectors(single_args)

            # 读取评分结果
            score_path = os.path.join(window_output_dir, as_of_date, "sector_scores.json")
            if os.path.exists(score_path):
                with open(score_path, "r", encoding="utf-8") as f:
                    score_data = json.load(f)

                # 收集各板块的评分
                for score in score_data.get("scores", []):
                    sector_name = score.get("sector_name", "")
                    if sector_name:
                        if sector_name not in all_sectors_data:
                            all_sectors_data[sector_name] = {
                                "sector_name": sector_name,
                                "sector_type": score.get("sector_type", "industry"),
                                "windows": {},
                            }
                        all_sectors_data[sector_name]["windows"][str(window)] = {
                            "trend_continuation_score": score.get("trend_continuation_score", 0),
                            "trend_level": score.get("trend_level", ""),
                            "actual_history_days": score.get("actual_history_days", 0),
                            "history_coverage_ratio": score.get("history_coverage_ratio", 0),
                            "trend_window_status": score.get("trend_window_status", ""),
                        }

        except Exception as e:
            print(f"  Error: {str(e)}")

    # 运行多窗口共识分析
    print("\n" + "=" * 60)
    print("Running multi-window consensus analysis...")
    print("=" * 60)

    agent = MultiWindowConsensusAgent()
    sectors_data = list(all_sectors_data.values())
    consensus_results = agent.analyze_sectors(sectors_data)

    # 输出 Top 5
    print("\nTop 5 Consensus:")
    for i, result in enumerate(consensus_results[:5], 1):
        print(f"{i}. {result['sector_name']}: {result['consensus_score']:.1f} ({result['multi_window_label']})")

    # 生成报告
    report_data = {
        "as_of_date": as_of_date,
        "sector_type": args.sector_type,
        "report_type": "multi_window_consensus",
        "trend_weight_profile": args.trend_weight_profile,
        "windows": windows,
        "metadata": {
            "history_start_date": history_start_date,
            "history_end_date": history_end_date,
            "history_resolution": history_resolution,
            "benchmark": args.benchmark,
            "top_n": args.top_n,
            "report_root": args.report_root,
            "score_output": args.score_output,
            "history_root": args.history_root,
            "cache_root": getattr(args, "cache_root", "data_cache"),
        },
        "warnings": [],
        "disclaimer": "仅用于板块研究、观察和复盘，不作为操作依据。",
    }

    # 保存报告
    save_multi_window_consensus_report(consensus_dir, report_data, consensus_results)

    print("\n" + "=" * 60)
    print("Multi-window consensus complete!")
    print("=" * 60)


def _run_research_agents(args):
    """运行板块综合研判"""
    from .models import SectorType
    from .agents.sector_research import SectorResearchCoordinator

    # 处理日期
    as_of_date = args.as_of or get_latest_trading_date()

    # 多窗口和研判链路固定依赖 5/10/20 窗口，默认历史范围按最大窗口 20 解析
    history_start_date, history_end_date, history_resolution = _resolve_history_date_range(
        as_of_date=as_of_date,
        history_start_date=getattr(args, "history_start_date", None),
        history_end_date=getattr(args, "history_end_date", None),
        history_lookback_days=getattr(args, "history_lookback_days", 10),
        trend_window=20,
    )

    print("=" * 60)
    print("Theme Sector Radar - Sector Research Agents")
    print("=" * 60)
    print(f"Date: {as_of_date}")
    print(f"Sector Type: {args.sector_type}")
    print(f"History Start: {history_start_date}")
    print(f"History End: {history_end_date}")
    print(f"Top N: {args.top_n}")
    print(f"Trend Weight Profile: {args.trend_weight_profile}")
    print(f"Benchmark: {args.benchmark}")
    print("-" * 60)

    # 读取或生成 multi_window_consensus
    consensus_dir = os.path.join(args.score_output, "..", "sector_consensus", as_of_date)
    consensus_path = os.path.join(consensus_dir, "multi_window_consensus.json")

    if not os.path.exists(consensus_path):
        print("Multi-window consensus not found, generating...")
        # 创建临时参数运行 multi-window-consensus
        temp_args = argparse.Namespace(
            as_of=as_of_date,
            sector_type=args.sector_type,
            history_start_date=history_start_date,
            history_end_date=history_end_date,
            history_lookback_days=args.history_lookback_days,
            history_root=args.history_root,
            top_n=args.top_n,
            score_mode=args.score_mode,
            trend_weight_profile=args.trend_weight_profile,
            benchmark=args.benchmark,
            benchmark_root=args.benchmark_root,
            benchmark_refresh=args.benchmark_refresh,
            score_output=args.score_output,
            report_root=args.report_root,
            cache_root=args.cache_root,
        )
        _run_multi_window_consensus(temp_args)

    # 读取 multi_window_consensus
    with open(consensus_path, "r", encoding="utf-8") as f:
        multi_window_consensus = json.load(f)

    # 读取 10 日窗口的 sector_scores
    window_10_path = os.path.join(consensus_dir, "windows", "10", as_of_date, "sector_scores.json")
    if os.path.exists(window_10_path):
        with open(window_10_path, "r", encoding="utf-8") as f:
            sector_scores = json.load(f)
    else:
        print(f"Warning: Window 10 scores not found at {window_10_path}")
        sector_scores = {"scores": []}

    # 运行综合研判
    print("\nRunning sector research agents...")
    coordinator = SectorResearchCoordinator()
    research_results = coordinator.research_sectors(
        sector_scores=sector_scores,
        multi_window_consensus=multi_window_consensus,
        market_data={"benchmark_status": "ok"},
    )

    # 输出 Top 5
    print("\nTop 5 Research Results:")
    for i, result in enumerate(research_results[:5], 1):
        print(f"{i}. {result['sector_name']}: {result['consensus_label']} (confidence: {result['confidence_score']:.2f})")

    # 生成报告
    report_data = {
        "as_of_date": as_of_date,
        "sector_type": args.sector_type,
        "report_type": "sector_research",
        "version": "phase21",
        "inputs": {
            "sector_scores_source": window_10_path,
            "multi_window_consensus_source": consensus_path,
            "trend_weight_profile": args.trend_weight_profile,
            "windows": [5, 10, 20],
            "benchmark": args.benchmark,
        },
        "research_results": research_results,
        "warnings": [],
        "disclaimer": "仅用于板块研究、观察和复盘，不作为操作依据。",
    }

    # 生成 daily_summary
    from .reports.sector_research_report import generate_daily_summary
    report_data["daily_summary"] = generate_daily_summary(report_data)

    # 保存报告
    output_dir = os.path.join(args.score_output, "..", "sector_research", as_of_date)
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, "sector_research.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print(f"\nJSON report saved: {json_path}")

    # 生成 Markdown 报告
    from .reports.sector_research_report import save_sector_research_report
    save_sector_research_report(output_dir, report_data, multi_window_consensus)

    print("\n" + "=" * 60)
    print("Sector research complete!")
    print("=" * 60)


def _run_backtest_research_agents(args):
    """运行 Agent 组复盘评估"""
    from .backtest import SectorResearchBacktest
    from .reports.sector_research_backtest_report import save_backtest_report

    # 处理日期
    start_date = args.start_date
    end_date = args.end_date

    if not start_date or not end_date:
        print("Error: --start-date and --end-date are required for --backtest-research-agents")
        sys.exit(1)

    print("=" * 60)
    print("Theme Sector Radar - Agent Group Backtest")
    print("=" * 60)
    print(f"Date Range: {start_date} ~ {end_date}")
    print(f"Sector Type: {args.sector_type}")
    print(f"History Root: {args.history_root}")
    print(f"Report Root: {args.report_root}")
    print("-" * 60)

    # 运行回测
    backtest = SectorResearchBacktest(history_root=args.history_root)
    backtest_result = backtest.run_backtest(
        start_date=start_date,
        end_date=end_date,
        sector_type=args.sector_type,
        report_root=args.report_root,
    )

    # 输出摘要
    input_summary = backtest_result.get("input_summary", {})
    print(f"\nInput Summary:")
    print(f"  Research Report Count: {input_summary.get('research_report_count', 0)}")
    print(f"  Sample Count: {input_summary.get('sample_count', 0)}")
    print(f"  Skipped Dates: {len(input_summary.get('skipped_dates', []))}")

    # 按标签表现
    label_performance = backtest_result.get("label_performance", {})
    if label_performance:
        print(f"\nLabel Performance:")
        for label, stats in label_performance.items():
            avg_5d = stats.get("avg_forward_5d_return")
            if avg_5d is not None:
                print(f"  {label}: {stats.get('sample_count', 0)} samples, avg_5d={avg_5d:.2f}%")

    # 保存报告
    output_dir = os.path.join(args.report_root, "backtests", "sector_research", f"{start_date}_to_{end_date}")
    os.makedirs(output_dir, exist_ok=True)

    json_path = os.path.join(output_dir, "research_backtest.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(backtest_result, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nJSON report saved: {json_path}")

    # 生成 Markdown 报告
    save_backtest_report(output_dir, backtest_result)

    print("\n" + "=" * 60)
    print("Backtest complete!")
    print("=" * 60)


def _run_replay_daily_from_sector_history(args):
    """从 sector_history 历史数据生成日报"""
    from .backtest.replay_daily_from_sector_history import (
        DailyReplayFromSectorHistory,
        save_replay_daily_summary,
    )

    # 处理日期
    start_date = args.start_date
    end_date = args.end_date

    if not start_date or not end_date:
        print("Error: --start-date and --end-date are required for --replay-daily-from-sector-history")
        sys.exit(1)

    print("=" * 60)
    print("Theme Sector Radar - Daily Replay from Sector History")
    print("=" * 60)
    print(f"Date Range: {start_date} ~ {end_date}")
    print(f"Sector Type: {args.sector_type}")
    print(f"History Root: {args.history_root}")
    print(f"Report Root: {args.report_root}")
    print(f"Top N: {args.top_n}")
    print("-" * 60)

    # 创建 replay 实例
    replay = DailyReplayFromSectorHistory(
        history_root=args.history_root,
        report_root=args.report_root,
    )

    # 运行 replay
    result = replay.run_replay(
        start_date=start_date,
        end_date=end_date,
        sector_type=args.sector_type,
        top_n=args.top_n,
        refresh=args.refresh,
    )

    # 输出摘要
    print(f"\nGenerated Dates: {len(result.get('generated_dates', []))}")
    print(f"Reused Dates: {len(result.get('reused_dates', []))}")
    print(f"Skipped Dates: {len(result.get('skipped_dates', []))}")
    print(f"Failed Dates: {len(result.get('failed_dates', []))}")
    print(f"No-lookahead Violations: {len(result.get('no_lookahead_violations', []))}")

    # 保存摘要
    output_dir = os.path.join(
        args.report_root, "theme_sector_radar", "replay_runs",
        f"{start_date}_to_{end_date}"
    )
    save_replay_daily_summary(output_dir, result)

    print("\n" + "=" * 60)
    print("Daily replay complete!")
    print("=" * 60)


def _run_generate_research_range(args):
    """运行批量生成多日 Agent 组研判报告"""
    from .backtest.generate_research_range import ResearchRangeGenerator, save_range_run_summary

    # 处理日期
    start_date = args.start_date
    end_date = args.end_date

    if not start_date or not end_date:
        print("Error: --start-date and --end-date are required for --generate-research-range")
        sys.exit(1)

    print("=" * 60)
    print("Theme Sector Radar - Batch Research Generation")
    print("=" * 60)
    print(f"Date Range: {start_date} ~ {end_date}")
    print(f"Sector Type: {args.sector_type}")
    print(f"History Start: {history_start_date}")
    print(f"History End: {history_end_date}")
    print(f"Top N: {args.top_n}")
    print(f"Score Mode: {args.score_mode}")
    print(f"Benchmark: {args.benchmark}")
    print(f"Trend Weight Profile: {args.trend_weight_profile}")
    print("-" * 60)

    # 创建生成器
    generator = ResearchRangeGenerator(
        history_root=args.history_root,
        report_root=args.report_root,
    )

    # 运行批量生成
    result = generator.run_range(
        start_date=start_date,
        end_date=end_date,
        sector_type=args.sector_type,
        history_start_date=args.history_start_date,
        history_end_date=args.history_end_date,
        top_n=args.top_n,
        score_mode=args.score_mode,
        benchmark=args.benchmark,
        trend_weight_profile=args.trend_weight_profile,
        refresh=args.refresh,
    )

    # 输出摘要
    print(f"\nGenerated Dates: {len(result.get('generated_dates', []))}")
    print(f"Reused Dates: {len(result.get('reused_dates', []))}")
    print(f"Skipped Dates: {len(result.get('skipped_dates', []))}")
    print(f"Failed Dates: {len(result.get('failed_dates', []))}")

    # 保存摘要
    output_dir = os.path.join(
        args.report_root, "sector_research", "range_runs",
        f"{start_date}_to_{end_date}"
    )
    save_range_run_summary(output_dir, result)

    print("\n" + "=" * 60)
    print("Batch generation complete!")
    print("=" * 60)


def _run_backtest_agent_layers(args):
    """运行分层 Agent 回测"""
    from .backtest.agent_layer_backtest import AgentLayerBacktest
    from .reports.agent_layer_backtest_report import save_agent_layer_backtest_report

    # 处理日期
    start_date = args.start_date
    end_date = args.end_date

    if not start_date or not end_date:
        print("Error: --start-date and --end-date are required for --backtest-agent-layers")
        sys.exit(1)

    print("=" * 60)
    print("Theme Sector Radar - Agent Layer Backtest")
    print("=" * 60)
    print(f"Date Range: {start_date} ~ {end_date}")
    print(f"Sector Type: {args.sector_type}")
    print(f"History Root: {args.history_root}")
    print(f"Report Root: {args.report_root}")
    print("-" * 60)

    # 创建回测实例
    backtest = AgentLayerBacktest(history_root=args.history_root)

    # 运行回测
    backtest_result = backtest.run_backtest(
        start_date=start_date,
        end_date=end_date,
        sector_type=args.sector_type,
        report_root=args.report_root,
    )

    # 输出摘要
    input_summary = backtest_result.get("input_summary", {})
    print(f"\nInput Summary:")
    print(f"  Research Report Count: {input_summary.get('research_report_count', 0)}")
    print(f"  Sample Count: {input_summary.get('sample_count', 0)}")
    print(f"  Skipped Dates: {len(input_summary.get('skipped_dates', []))}")

    # 保存报告
    output_dir = os.path.join(args.report_root, "backtests", "agent_layers", f"{start_date}_to_{end_date}")
    save_agent_layer_backtest_report(output_dir, backtest_result)

    print("\n" + "=" * 60)
    print("Agent layer backtest complete!")
    print("=" * 60)


def _run_analyze_opportunity_rebound(args):
    """运行 Opportunity Rebound 归因分析"""
    from .backtest.opportunity_rebound_analysis import OpportunityReboundAnalysis
    from .reports.opportunity_rebound_report import save_opportunity_rebound_report

    start_date = args.start_date
    end_date = args.end_date

    if not start_date or not end_date:
        print("Error: --start-date and --end-date are required for --analyze-opportunity-rebound")
        sys.exit(1)

    print("=" * 60)
    print("Theme Sector Radar - Opportunity Rebound Analysis")
    print("=" * 60)
    print(f"Date Range: {start_date} ~ {end_date}")
    print(f"Sector Type: {args.sector_type}")
    print(f"Report Root: {args.report_root}")
    print("-" * 60)

    # 运行分析
    analysis = OpportunityReboundAnalysis()
    result = analysis.run_analysis(
        start_date=start_date,
        end_date=end_date,
        sector_type=args.sector_type,
        report_root=args.report_root,
    )

    # 输出摘要
    input_summary = result.get("input_summary", {})
    missed = result.get("missed_opportunity", {})
    failed = result.get("failed_rebound", {})

    print(f"\nAnalysis Summary:")
    print(f"  Sample Count: {input_summary.get('sample_count', 0)}")
    print(f"  Missed Opportunity: {missed.get('count', 0)}")
    print(f"  Failed Rebound: {failed.get('count', 0)}")

    # 保存报告
    output_dir = os.path.join(
        args.report_root, "backtests", "opportunity_rebound", f"{start_date}_to_{end_date}"
    )
    save_opportunity_rebound_report(output_dir, result)

    print("\n" + "=" * 60)
    print("Opportunity rebound analysis complete!")
    print("=" * 60)


def _run_analyze_market_regime(args):
    """运行 Market Regime Layer 分层回测分析"""
    from .backtest.market_regime_analysis import MarketRegimeAnalysis
    from .reports.market_regime_report import save_market_regime_report

    start_date = args.start_date
    end_date = args.end_date

    if not start_date or not end_date:
        print("Error: --start-date and --end-date are required for --analyze-market-regime")
        sys.exit(1)

    benchmark = getattr(args, "benchmark", "hs300")

    print("=" * 60)
    print("Theme Sector Radar - Market Regime Layer Analysis")
    print("=" * 60)
    print(f"Date Range: {start_date} ~ {end_date}")
    print(f"Sector Type: {args.sector_type}")
    print(f"Benchmark: {benchmark}")
    print(f"Report Root: {args.report_root}")
    print("-" * 60)

    # 运行分析
    analysis = MarketRegimeAnalysis()
    result = analysis.run_analysis(
        start_date=start_date,
        end_date=end_date,
        sector_type=args.sector_type,
        benchmark=benchmark,
        report_root=args.report_root,
    )

    # 输出摘要
    input_summary = result.get("input_summary", {})
    dist = result.get("regime_distribution", {})
    check = result.get("no_lookahead_check", {})

    print(f"\nAnalysis Summary:")
    print(f"  Sample Count: {input_summary.get('sample_count', 0)}")
    print(f"  no-lookahead: {'PASS' if check.get('passed') else 'FAIL'}")
    print(f"  Regime distribution:")
    for regime, count in dist.get("regime_composite_label", {}).items():
        print(f"    {regime}: {count}")

    # 保存报告
    output_dir = os.path.join(
        args.report_root, "backtests", "market_regime", f"{start_date}_to_{end_date}"
    )
    save_market_regime_report(output_dir, result)

    print("\n" + "=" * 60)
    print("Market regime analysis complete!")
    print("=" * 60)


def _run_build_research_index(args):
    """构建多日 sector_research 索引"""
    from .reports.sector_research_index import SectorResearchIndex, save_research_index

    start_date = args.start_date
    end_date = args.end_date

    if not start_date or not end_date:
        print("Error: --start-date and --end-date are required for --build-research-index")
        sys.exit(1)

    print("=" * 60)
    print("Theme Sector Radar - Build Research Index")
    print("=" * 60)
    print(f"Date Range: {start_date} ~ {end_date}")
    print(f"Report Root: {args.report_root}")
    print("-" * 60)

    # 构建索引
    indexer = SectorResearchIndex(report_root=args.report_root)
    index_data = indexer.build_index(
        start_date=start_date,
        end_date=end_date,
    )

    # 输出摘要
    print(f"\nIndex Summary:")
    print(f"  Total Days: {index_data.get('total_days', 0)}")
    print(f"  Sectors Tracked: {len(index_data.get('sector_frequency', {}))}")
    print(f"  Label Changes: {len(index_data.get('label_changes', []))}")
    print(f"  Risk Signals: {len(index_data.get('risk_signals', []))}")

    # 保存索引
    output_dir = os.path.join(args.report_root, "sector_research", "index")
    save_research_index(output_dir, index_data)

    print("\n" + "=" * 60)
    print("Research index build complete!")
    print("=" * 60)


def _run_analyze_agent_reliability(args):
    """运行 Agent 可靠性评估"""
    from .backtest.agent_reliability import AgentReliability
    from .reports.agent_reliability_report import save_agent_reliability_report

    start_date = args.start_date
    end_date = args.end_date

    if not start_date or not end_date:
        print("Error: --start-date and --end-date are required for --analyze-agent-reliability")
        sys.exit(1)

    print("=" * 60)
    print("Theme Sector Radar - Agent Reliability Analysis")
    print("=" * 60)
    print(f"Date Range: {start_date} ~ {end_date}")
    print(f"Sector Type: {args.sector_type}")
    print(f"Report Root: {args.report_root}")
    print("-" * 60)

    # 运行分析
    analysis = AgentReliability()
    result = analysis.run_analysis(
        start_date=start_date,
        end_date=end_date,
        sector_type=args.sector_type,
        report_root=args.report_root,
    )

    # 输出摘要
    print(f"\nAnalysis Summary:")
    print(f"  Total Samples: {result.get('total_samples', 0)}")
    print(f"  Agents: {len(result.get('agents', {}))}")

    for agent_id, stats in result.get("agents", {}).items():
        print(f"    {agent_id}: reliability={stats.get('reliability_score', 0):.2f}, label={stats.get('reliability_label', '')}")

    # 保存报告
    output_dir = os.path.join(
        args.report_root, "backtests", "agent_reliability", f"{start_date}_to_{end_date}"
    )
    save_agent_reliability_report(output_dir, result)

    print("\n" + "=" * 60)
    print("Agent reliability analysis complete!")
    print("=" * 60)


def _run_analyze_persistence_signals(args):
    """运行持续性信号研究"""
    from .backtest.persistence_signal_research import PersistenceSignalResearch
    from .reports.persistence_signal_report import save_persistence_signal_report

    start_date = args.start_date
    end_date = args.end_date

    if not start_date or not end_date:
        print("Error: --start-date and --end-date are required for --analyze-persistence-signals")
        sys.exit(1)

    print("=" * 60)
    print("Theme Sector Radar - Persistence Signal Research")
    print("=" * 60)
    print(f"Date Range: {start_date} ~ {end_date}")
    print(f"Sector Type: {args.sector_type}")
    print(f"Report Root: {args.report_root}")
    print("-" * 60)

    # 运行分析
    analysis = PersistenceSignalResearch()
    result = analysis.run_analysis(
        start_date=start_date,
        end_date=end_date,
        sector_type=args.sector_type,
        report_root=args.report_root,
    )

    # 输出摘要
    print(f"\nAnalysis Summary:")
    print(f"  Total Samples: {result.get('total_samples', 0)}")
    print(f"  Sectors Covered: {result.get('sectors_covered', 0)}")

    rec = result.get("recommendation", {})
    print(f"  Recommend Persistence Agent: {rec.get('recommend_persistence_agent', False)}")
    print(f"  Reason: {rec.get('reason', '')}")

    # 保存报告
    output_dir = os.path.join(
        args.report_root, "backtests", "persistence_signals", f"{start_date}_to_{end_date}"
    )
    save_persistence_signal_report(output_dir, result)

    print("\n" + "=" * 60)
    print("Persistence signal research complete!")
    print("=" * 60)


def _run_research_catalyst_sources(args):
    """运行外部催化数据源研究"""
    from .research.catalyst_data_source_research import CatalystDataSourceResearch, save_catalyst_research

    as_of_date = getattr(args, "as_of", "2026-06-29")
    sector_type = args.sector_type
    output_dir = getattr(args, "output", None)

    if not output_dir:
        output_dir = os.path.join("reports", "research", "catalyst_sources", as_of_date)

    print("=" * 60)
    print("Theme Sector Radar - Catalyst Data Source Research")
    print("=" * 60)
    print(f"As-of Date: {as_of_date}")
    print(f"Sector Type: {sector_type}")
    print(f"Output: {output_dir}")
    print("-" * 60)

    # 运行研究
    research = CatalystDataSourceResearch()
    result = research.run_research(
        as_of_date=as_of_date,
        sector_type=sector_type,
    )

    # 输出摘要
    print(f"\nResearch Summary:")
    print(f"  Total Sources: {result.get('total_sources', 0)}")
    print(f"  Available: {result.get('available_count', 0)}")
    print(f"  Partial: {result.get('partial_count', 0)}")
    print(f"  Unavailable: {result.get('unavailable_count', 0)}")

    # 保存报告
    save_catalyst_research(output_dir, result)

    print("\n" + "=" * 60)
    print("Catalyst data source research complete!")
    print("=" * 60)


def _run_download_catalyst_events(args):
    """下载催化事件数据"""
    start_date = getattr(args, "start_date", None)
    end_date = getattr(args, "end_date", None)
    as_of_date = getattr(args, "as_of", None)

    # 单日兼容模式
    if as_of_date and not start_date:
        start_date = as_of_date
        end_date = as_of_date

    if not start_date or not end_date:
        print("Error: --start-date/--end-date or --as-of required")
        sys.exit(1)

    sector_type = args.sector_type
    symbols_str = getattr(args, "symbols", "")
    max_symbols = getattr(args, "max_symbols", 20)
    max_events = getattr(args, "max_events_per_symbol", 5)
    lookback_days = getattr(args, "lookback_days", 7)
    network = getattr(args, "network", False)
    offline_fixture = getattr(args, "offline_fixture", False)
    output_dir = getattr(args, "output", None)
    auto_symbols = getattr(args, "auto_symbols_from_research", False)
    top_sectors = getattr(args, "top_sectors", 10)
    refresh = getattr(args, "refresh", False)
    report_root = args.report_root

    if not output_dir:
        if start_date == end_date:
            output_dir = os.path.join("reports", "data_downloads", "catalyst_events", start_date)
        else:
            output_dir = os.path.join("reports", "data_downloads", "catalyst_events", f"{start_date}_to_{end_date}")

    # 解析 explicit symbols
    explicit_symbols = [s.strip() for s in symbols_str.split(",") if s.strip()] if symbols_str else None

    print("=" * 60)
    print("Theme Sector Radar - Download Catalyst Events")
    print("=" * 60)
    print(f"Date Range: {start_date} ~ {end_date}")
    print(f"Mode: {'fixture' if offline_fixture else ('network' if network else 'offline')}")
    print(f"Auto Symbols: {auto_symbols}")
    print(f"Output: {output_dir}")
    print("-" * 60)

    # 使用 HistoricalCatalystCollector
    from .data.catalyst_events.historical_collector import HistoricalCatalystCollector, save_historical_collection_summary

    # 加载 fixture 数据
    fixture_data = None
    if offline_fixture:
        fixture_path = os.path.join("tests", "fixtures", "catalyst_events", "sample_stock_news.json")
        if os.path.exists(fixture_path):
            with open(fixture_path, "r", encoding="utf-8") as f:
                fixture_data = json.load(f)

    collector = HistoricalCatalystCollector()
    result = collector.collect(
        start_date=start_date,
        end_date=end_date,
        report_root=report_root,
        network=network,
        offline_fixture=offline_fixture,
        auto_symbols=auto_symbols,
        top_sectors=top_sectors,
        max_symbols_per_sector=3,
        max_symbols_total=max_symbols,
        lookback_days=lookback_days,
        refresh=refresh,
        symbols=explicit_symbols,
        fixture_data=fixture_data,
    )

    # 保存摘要
    save_historical_collection_summary(output_dir, result)

    # 生成映射质量报告
    from .data.catalyst_events.mapping_quality import MappingQualityAnalyzer, save_mapping_quality_report
    from .data.catalyst_events.cache import CatalystEventCache

    cache = CatalystEventCache()
    all_events = []
    for date_str in result.get("generated_dates", []):
        events = cache.load_events(date_str)
        if events:
            all_events.extend([e.to_dict() for e in events])

    if all_events:
        analyzer = MappingQualityAnalyzer()
        mapping_quality = analyzer.analyze(
            all_events,
            date_range=f"{start_date}_to_{end_date}",
        )
        save_mapping_quality_report(output_dir, mapping_quality)

    # 输出摘要
    print(f"\nCollection Summary:")
    print(f"  Generated Dates: {len(result.get('generated_dates', []))}")
    print(f"  Skipped Dates: {len(result.get('skipped_dates', []))}")
    print(f"  Failed Dates: {len(result.get('failed_dates', []))}")
    print(f"  Total Events: {result.get('total_events', 0)}")
    print(f"  Real Events: {result.get('real_event_count', 0)}")
    print(f"  Fixture Events: {result.get('fixture_event_count', 0)}")

    print("\n" + "=" * 60)
    print("Catalyst event collection complete!")
    print("=" * 60)


def _run_backtest_catalyst_events(args):
    """运行 CatalystEventAgent 信号验证"""
    from .backtest.catalyst_event_backtest import CatalystEventBacktest
    from .reports.catalyst_event_backtest_report import save_catalyst_event_backtest_report

    start_date = args.start_date
    end_date = args.end_date

    if not start_date or not end_date:
        print("Error: --start-date and --end-date are required for --backtest-catalyst-events")
        sys.exit(1)

    print("=" * 60)
    print("Theme Sector Radar - Catalyst Event Signal Validation")
    print("=" * 60)
    print(f"Date Range: {start_date} ~ {end_date}")
    print(f"Sector Type: {args.sector_type}")
    print(f"Report Root: {args.report_root}")
    print("-" * 60)

    # 运行回测
    backtest = CatalystEventBacktest()
    result = backtest.run_backtest(
        start_date=start_date,
        end_date=end_date,
        sector_type=args.sector_type,
        report_root=args.report_root,
    )

    # 输出摘要
    print(f"\nBacktest Summary:")
    print(f"  Total Samples: {result.get('total_samples', 0)}")
    print(f"  Cache Coverage: {result.get('cache_coverage', 0):.0%}")

    rec = result.get("recommendation", {})
    print(f"  Recommend Vote Calibration: {rec.get('recommend_vote_calibration', False)}")
    print(f"  Reason: {', '.join(rec.get('reasons', []))}")

    # 保存报告
    output_dir = os.path.join(
        args.report_root, "backtests", "catalyst_events", f"{start_date}_to_{end_date}"
    )
    save_catalyst_event_backtest_report(output_dir, result)

    print("\n" + "=" * 60)
    print("Catalyst event backtest complete!")
    print("=" * 60)


def _run_daily_health_check(args):
    """运行每日健康检查"""
    from .reports.daily_health_check import DailyHealthCheck, save_daily_health_check

    as_of_date = getattr(args, "as_of", None)
    if not as_of_date:
        print("Error: --as-of required for --daily-health-check")
        sys.exit(1)

    report_root = args.report_root
    cache_root = getattr(args, "cache_root", "data_cache")

    print("=" * 60)
    print("Theme Sector Radar - Daily Health Check")
    print("=" * 60)
    print(f"As-of Date: {as_of_date}")
    print(f"Report Root: {report_root}")
    print("-" * 60)

    # 运行健康检查
    checker = DailyHealthCheck(report_root=report_root, cache_root=cache_root)
    result = checker.run_check(as_of_date)

    # 输出摘要
    print(f"\nHealth Check Summary:")
    print(f"  Overall Status: {result.get('overall_status', 'unknown')}")
    print(f"  Data Source Mode: {result.get('data_source_mode', 'unknown')}")
    print(f"  Radar Status: {result.get('radar_status', 'unknown')}")
    print(f"  Research Status: {result.get('research_status', 'unknown')}")
    print(f"  Catalyst Status: {result.get('catalyst_status', 'unknown')}")

    warnings = result.get("warnings", [])
    if warnings:
        print(f"\n  Warnings:")
        for w in warnings:
            print(f"    - {w}")

    # 保存报告
    output_dir = os.path.join(report_root, "daily_health", as_of_date)
    save_daily_health_check(output_dir, result)

    print("\n" + "=" * 60)
    print("Daily health check complete!")
    print("=" * 60)


def _load_history_data(
    history_root: str,
    start_date: str,
    end_date: str,
    sector_types: List[SectorType],
    cache_root: str = "data_cache",
) -> Tuple[Dict[str, Any], str, List[str]]:
    """
    加载历史数据

    Args:
        history_root: 历史数据根目录 (data_cache/sector_history)
        start_date: 开始日期
        end_date: 结束日期
        sector_types: 板块类型列表
        cache_root: 缓存根目录 (data_cache)

    Returns:
        (history_data, history_source, warnings)
    """
    history_data = {}
    warnings = []
    history_source = "none"

    # A. 首选: 尝试从 sector_history 加载
    sector_history_data = {}
    for sector_type in sector_types:
        sector_type_dir = os.path.join(history_root, sector_type.value)
        if not os.path.exists(sector_type_dir):
            continue

        for filename in os.listdir(sector_type_dir):
            if not filename.endswith(".json"):
                continue

            sector_name = filename[:-5]  # 移除 .json
            filepath = os.path.join(sector_type_dir, filename)

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    sector_history = json.load(f)

                # 获取记录列表
                records = sector_history.get("records", [])

                # 筛选日期范围
                filtered_history = _filter_history_by_date(
                    records, start_date, end_date
                )

                if filtered_history:
                    # 计算指标
                    metrics = _calculate_history_metrics(filtered_history)
                    if sector_type.value not in sector_history_data:
                        sector_history_data[sector_type.value] = {}
                    sector_history_data[sector_type.value][sector_name] = metrics

            except Exception as e:
                warnings.append(f"Failed to load sector_history {filepath}: {str(e)[:100]}")

    # 检查 sector_history 是否有数据
    has_sector_history = any(
        len(sector_type_data) > 0
        for sector_type_data in sector_history_data.values()
    )

    if has_sector_history:
        history_data = sector_history_data
        history_source = "sector_history_cache"
        print(f"Loaded history from sector_history_cache")
    else:
        # B. fallback: 从 raw_snapshot 加载
        print("No sector_history data found, falling back to raw_snapshots...")
        raw_snapshot_data, raw_warnings = _load_history_from_raw_snapshots(
            cache_root, start_date, end_date, sector_types
        )
        history_data = raw_snapshot_data
        warnings.extend(raw_warnings)

        # 检查 raw_snapshot_data 是否有实际数据
        has_raw_snapshot_data = any(
            len(sector_type_data) > 0
            for sector_type_data in raw_snapshot_data.values()
        )

        if has_raw_snapshot_data:
            history_source = "raw_snapshot_fallback"
            print(f"Loaded history from raw_snapshot_fallback")
        else:
            history_source = "none"
            warnings.append("No history data available from any source")

    return history_data, history_source, warnings


def _load_history_from_raw_snapshots(
    cache_root: str,
    start_date: str,
    end_date: str,
    sector_types: List[SectorType],
) -> Tuple[Dict[str, Any], List[str]]:
    """
    从 raw_snapshot 文件加载历史数据

    Args:
        cache_root: 缓存根目录 (data_cache)
        start_date: 开始日期
        end_date: 结束日期
        sector_types: 板块类型列表

    Returns:
        (history_data, warnings)
    """
    warnings = []
    history_data = {sector_type.value: {} for sector_type in sector_types}

    # 扫描 date 目录
    if not os.path.exists(cache_root):
        return history_data, [f"Cache root not found: {cache_root}"]

    date_dirs = []
    for dirname in os.listdir(cache_root):
        # 检查是否为 YYYY-MM-DD 格式
        if len(dirname) == 10 and dirname[4] == "-" and dirname[7] == "-":
            # 如果没有指定日期范围，使用所有日期
            if start_date is None and end_date is None:
                date_dirs.append(dirname)
            elif start_date and end_date:
                if start_date <= dirname <= end_date:
                    date_dirs.append(dirname)
            elif start_date:
                if dirname >= start_date:
                    date_dirs.append(dirname)
            elif end_date:
                if dirname <= end_date:
                    date_dirs.append(dirname)

    date_dirs.sort()

    if not date_dirs:
        warnings.append(f"No date directories found in {cache_root} for range {start_date} ~ {end_date}")
        return history_data, warnings

    # 收集每个板块的时间序列数据
    sector_timeseries = {}  # {(sector_type, sector_name): [(date, data), ...]}

    for date_dir in date_dirs:
        raw_snapshot_path = os.path.join(cache_root, date_dir, "raw_snapshot.json")
        if not os.path.exists(raw_snapshot_path):
            continue

        try:
            with open(raw_snapshot_path, "r", encoding="utf-8") as f:
                snapshot = json.load(f)

            # 提取日期
            metadata = snapshot.get("metadata", {})
            snapshot_date = metadata.get("as_of_date", date_dir)

            # 提取数据
            data = snapshot.get("data", {})

            # 处理行业板块
            if SectorType.INDUSTRY in sector_types:
                industry_sectors = data.get("industry_sectors", [])
                for sector in industry_sectors:
                    sector_name = sector.get("name", "")
                    if not sector_name:
                        continue

                    key = (SectorType.INDUSTRY.value, sector_name)
                    if key not in sector_timeseries:
                        sector_timeseries[key] = []

                    sector_timeseries[key].append({
                        "date": snapshot_date,
                        "change_pct": sector.get("price_change_pct", 0.0),
                        "turnover": sector.get("turnover", 0.0),
                        "main_net_inflow": sector.get("main_net_inflow", 0.0),
                        "data_quality_score": sector.get("data_quality_score", 0.0),
                        "price_change_available": sector.get("price_change_available", True),
                        "source": ", ".join(sector.get("data_sources", [])),
                    })

            # 处理概念板块
            if SectorType.CONCEPT in sector_types:
                concept_sectors = data.get("concept_sectors", [])
                for sector in concept_sectors:
                    sector_name = sector.get("name", "")
                    if not sector_name:
                        continue

                    key = (SectorType.CONCEPT.value, sector_name)
                    if key not in sector_timeseries:
                        sector_timeseries[key] = []

                    sector_timeseries[key].append({
                        "date": snapshot_date,
                        "change_pct": sector.get("price_change_pct", 0.0),
                        "turnover": sector.get("turnover", 0.0),
                        "main_net_inflow": sector.get("main_net_inflow", 0.0),
                        "data_quality_score": sector.get("data_quality_score", 0.0),
                        "price_change_available": sector.get("price_change_available", True),
                        "source": ", ".join(sector.get("data_sources", [])),
                    })

        except Exception as e:
            warnings.append(f"Failed to load raw_snapshot {raw_snapshot_path}: {str(e)[:100]}")

    # 转换为指标
    for (sector_type, sector_name), timeseries in sector_timeseries.items():
        if sector_type not in history_data:
            history_data[sector_type] = {}

        # 按日期排序
        timeseries.sort(key=lambda x: x["date"])

        # 计算指标
        metrics = _calculate_history_metrics_from_snapshots(timeseries)
        history_data[sector_type][sector_name] = metrics

    return history_data, warnings


def _filter_history_by_date(
    history: List[Dict[str, Any]],
    start_date: str,
    end_date: str,
) -> List[Dict[str, Any]]:
    """按日期筛选历史数据"""
    if not start_date or not end_date:
        return history

    filtered = []
    for item in history:
        # 支持英文 "date" 和中文 "日期" 字段名
        date_str = item.get("date", item.get("日期", ""))
        if isinstance(date_str, str) and start_date <= date_str <= end_date:
            filtered.append(item)

    return filtered


def _calculate_history_metrics(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """计算历史数据指标"""
    if not history:
        return {
            "recent_returns": [],
            "total_return": 0.0,
            "positive_days": 0,
            "total_days": 0,
            "max_drawdown": 0.0,
            "volatility": 0.0,
            "history_days": 0,
        }

    # 提取每日收益率
    recent_returns = []

    # 首先尝试直接使用 change_pct 或 涨跌幅 字段
    has_change_pct = any(
        item.get("change_pct") is not None or item.get("涨跌幅") is not None
        for item in history
    )

    if has_change_pct:
        for item in history:
            change_pct = item.get("change_pct", item.get("涨跌幅", 0.0))
            try:
                change_pct = float(change_pct)
            except (ValueError, TypeError):
                change_pct = 0.0
            recent_returns.append(change_pct)
    else:
        # 如果没有涨跌幅字段，从收盘价计算
        # 支持中文 "收盘价" 和英文 "close" 字段名
        close_prices = []
        for item in history:
            close = item.get("close", item.get("收盘价"))
            if close is not None:
                try:
                    close_prices.append(float(close))
                except (ValueError, TypeError):
                    close_prices.append(0.0)
            else:
                close_prices.append(0.0)

        # 计算日收益率
        for i in range(len(close_prices)):
            if i == 0:
                recent_returns.append(0.0)
            else:
                prev = close_prices[i - 1]
                curr = close_prices[i]
                if prev > 0:
                    change_pct = (curr - prev) / prev * 100
                    recent_returns.append(change_pct)
                else:
                    recent_returns.append(0.0)

    # 计算累计收益率
    total_return = sum(recent_returns)

    # 计算上涨天数
    positive_days = sum(1 for r in recent_returns if r > 0)
    total_days = len(recent_returns)

    # 计算最大回撤
    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for r in recent_returns:
        cumulative += r
        if cumulative > peak:
            peak = cumulative
        drawdown = cumulative - peak
        if drawdown < max_drawdown:
            max_drawdown = drawdown

    # 计算波动率
    if total_days > 1:
        mean = sum(recent_returns) / total_days
        variance = sum((r - mean) ** 2 for r in recent_returns) / total_days
        volatility = variance ** 0.5
    else:
        volatility = 0.0

    return {
        "recent_returns": recent_returns,
        "total_return": total_return,
        "positive_days": positive_days,
        "total_days": total_days,
        "max_drawdown": max_drawdown,
        "volatility": volatility,
        "history_days": total_days,
    }


def _resolve_history_date_range(
    as_of_date: str,
    history_start_date: Optional[str] = None,
    history_end_date: Optional[str] = None,
    history_lookback_days: int = 10,
    trend_window: int = 10,
) -> Tuple[str, str, Dict[str, Any]]:
    """Resolve the history date range used by trend scoring.

    A 20-trading-day window needs more than 20 calendar days. When the caller
    does not provide an explicit start date, use a conservative calendar
    lookback so the default path does not accidentally cap trend scores as
    insufficient_history.
    """
    requested_lookback = history_lookback_days or 0
    window = trend_window or 10
    safe_lookback_days = max(requested_lookback, window * 2 + 5)

    resolved_end = history_end_date or as_of_date
    if history_start_date:
        resolved_start = history_start_date
    else:
        resolved_start = (
            datetime.strptime(as_of_date, "%Y-%m-%d") - timedelta(days=safe_lookback_days)
        ).strftime("%Y-%m-%d")

    resolution = {
        "history_start_date_was_explicit": bool(history_start_date),
        "history_end_date_was_explicit": bool(history_end_date),
        "requested_history_lookback_days": requested_lookback,
        "effective_history_lookback_days": safe_lookback_days,
        "trend_window": window,
    }
    return resolved_start, resolved_end, resolution


def _apply_trend_window(
    history: List[Dict[str, Any]],
    trend_window: int = 10,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    应用趋势窗口截取逻辑

    从历史数据中取最近 N 个有效交易日。

    Args:
        history: 历史数据列表 (已按日期升序排序)
        trend_window: 趋势窗口大小

    Returns:
        (截取后的历史数据, 窗口信息字典)
    """
    if not history:
        return [], {
            "trend_window": trend_window,
            "actual_history_days": 0,
            "history_coverage_ratio": 0.0,
            "trend_window_status": "insufficient_history",
        }

    # 取最近 N 个有效交易日
    if len(history) > trend_window:
        truncated = history[-trend_window:]
    else:
        truncated = history

    actual_days = len(truncated)
    coverage_ratio = actual_days / trend_window if trend_window > 0 else 0.0

    # 判断状态
    if actual_days >= trend_window:
        status = "ok"
    elif actual_days >= trend_window * 0.5:
        status = "ok"
    else:
        status = "insufficient_history"

    window_info = {
        "trend_window": trend_window,
        "actual_history_days": actual_days,
        "history_coverage_ratio": round(coverage_ratio, 2),
        "trend_window_status": status,
    }

    return truncated, window_info


def _calculate_history_metrics_from_snapshots(
    timeseries: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    从 raw_snapshot 时间序列计算历史数据指标

    Args:
        timeseries: 时间序列数据列表

    Returns:
        历史数据指标字典
    """
    if not timeseries:
        return {
            "recent_returns": [],
            "total_return": 0.0,
            "positive_days": 0,
            "total_days": 0,
            "max_drawdown": 0.0,
            "volatility": 0.0,
            "history_days": 0,
        }

    # 提取每日收益率
    recent_returns = []
    for item in timeseries:
        change_pct = item.get("change_pct", 0.0)
        recent_returns.append(change_pct)

    # 计算累计收益率
    total_return = sum(recent_returns)

    # 计算上涨天数
    positive_days = sum(1 for r in recent_returns if r > 0)
    total_days = len(recent_returns)

    # 计算最大回撤
    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for r in recent_returns:
        cumulative += r
        if cumulative > peak:
            peak = cumulative
        drawdown = cumulative - peak
        if drawdown < max_drawdown:
            max_drawdown = drawdown

    # 计算波动率
    if total_days > 1:
        mean = sum(recent_returns) / total_days
        variance = sum((r - mean) ** 2 for r in recent_returns) / total_days
        volatility = variance ** 0.5
    else:
        volatility = 0.0

    return {
        "recent_returns": recent_returns,
        "total_return": total_return,
        "positive_days": positive_days,
        "total_days": total_days,
        "max_drawdown": max_drawdown,
        "volatility": volatility,
        "history_days": total_days,
    }


def _generate_index(report_root: str, dates: List[str], include_experiments: bool = False):
    """生成报告索引"""
    from .reports.index_report import (
        generate_index_json,
        generate_index_md,
        is_standard_daily_dir,
        scan_daily_reports,
    )

    # 只扫描标准日报目录
    if not dates:
        dates = scan_daily_reports(report_root, include_experiments)

    reports = []
    for date_str in dates:
        # 只处理标准日报目录
        if not include_experiments and not is_standard_daily_dir(date_str):
            continue

        report_path = os.path.join(report_root, date_str, "theme_sector_radar.json")
        run_log_path = os.path.join(report_root, date_str, "run_log.json")

        if os.path.exists(report_path):
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    report_data = json.load(f)

                # 提取轮动信息
                rotation_summary = report_data.get("rotation_summary", {})
                industry_rotation = rotation_summary.get("industry", {})
                concept_rotation = rotation_summary.get("concept", {})

                reports.append({
                    "as_of_date": date_str,
                    "status": report_data.get("status", "ok"),
                    "data_quality_score": report_data.get("data_quality_score", 0),
                    "market_temperature_label": report_data.get("market_temperature", {}).get("label", "unknown"),
                    "top_industries": [s["name"] for s in report_data.get("industry_top", [])[:3]],
                    "top_concepts": [s["name"] for s in report_data.get("concept_top", [])[:3]],
                    "new_entries": industry_rotation.get("new_entries", []) + concept_rotation.get("new_entries", []),
                    "rising_fast": industry_rotation.get("rising_fast", []) + concept_rotation.get("rising_fast", []),
                    "persistent_strength": industry_rotation.get("persistent_strength", []) + concept_rotation.get("persistent_strength", []),
                    "risk_up": industry_rotation.get("risk_up", []) + concept_rotation.get("risk_up", []),
                    "report_path": report_path,
                    "markdown_path": os.path.join(report_root, date_str, "theme_sector_radar.md"),
                    "run_log_path": run_log_path,
                    "source_report_dir": os.path.join(report_root, date_str),
                    "data_source_mode": report_data.get("data_source_mode", "unknown"),
                    "fixture_profile": report_data.get("fixture_profile"),
                })
            except Exception as e:
                print(f"  读取 {date_str} 报告失败: {e}")

    # 生成 index.json
    index_json = generate_index_json(report_root, reports)
    json_path = os.path.join(report_root, "index.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(index_json, f, ensure_ascii=False, indent=2)

    # 生成 index.md
    index_md = generate_index_md(report_root, reports)
    md_path = os.path.join(report_root, "index.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(index_md)


if __name__ == "__main__":
    main()









