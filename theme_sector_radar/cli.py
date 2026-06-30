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
from typing import List

from . import __version__
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
        help="指定板块名称列表，逗号分隔"
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.0,
        help="请求间 sleep 秒数"
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

    # replay-cache 模式
    if args.replay_cache:
        _run_replay_cache(args, provider_name)
        return

    # daily 模式或普通模式
    _run_single(args, provider_name)


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
