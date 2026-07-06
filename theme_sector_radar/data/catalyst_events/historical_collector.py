"""
历史催化事件采集器

支持按日期区间批量采集历史事件缓存。
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .cache import CatalystEventCache
from .downloader import CatalystEventDownloader


class HistoricalCatalystCollector:
    """
    历史催化事件采集器

    支持按日期区间批量采集历史事件缓存。
    """

    def __init__(
        self,
        history_root: str = "data_cache/sector_history",
        catalyst_root: str = "data_cache/catalyst_events",
    ):
        self.history_root = history_root
        self.catalyst_root = catalyst_root
        self.cache = CatalystEventCache(catalyst_root)
        self.downloader = CatalystEventDownloader(
            cache_root=catalyst_root,
            history_root=history_root,
        )

    def collect(
        self,
        start_date: str,
        end_date: str,
        report_root: str = "reports",
        network: bool = False,
        offline_fixture: bool = False,
        auto_symbols: bool = False,
        top_sectors: int = 10,
        max_symbols_per_sector: int = 3,
        max_symbols_total: int = 50,
        lookback_days: int = 7,
        refresh: bool = False,
        symbols: Optional[List[str]] = None,
        fixture_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        批量采集历史事件

        Args:
            start_date: 开始日期
            end_date: 结束日期
            report_root: 报告根目录
            network: 是否联网
            offline_fixture: 是否使用 fixture
            auto_symbols: 是否自动选 symbols
            top_sectors: 重点板块数
            max_symbols_per_sector: 每板块最大 symbols
            max_symbols_total: 全局最大 symbols
            lookback_days: 回溯天数
            refresh: 是否强制刷新
            symbols: 指定 symbols

        Returns:
            采集结果
        """
        generated_dates = []
        skipped_dates = []
        failed_dates = []
        total_events = 0
        mapped_events = 0
        unmapped_events = 0
        real_event_count = 0
        fixture_event_count = 0
        warnings = []

        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        date_count = (end - current).days + 1

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")

            # 检查是否已存在
            if not refresh and self.cache.exists(date_str):
                skipped_dates.append(date_str)
                current += timedelta(days=1)
                continue

            try:
                # 选择 symbols
                day_symbols = self._select_symbols(
                    date_str, report_root, symbols, auto_symbols,
                    top_sectors, max_symbols_per_sector, max_symbols_total
                )

                if not day_symbols:
                    skipped_dates.append(date_str)
                    warnings.append(f"{date_str}: 无可用 symbols，跳过")
                    current += timedelta(days=1)
                    continue

                # 下载事件
                result = self.downloader.download(
                    as_of_date=date_str,
                    symbols=day_symbols,
                    max_events_per_symbol=5,
                    lookback_days=lookback_days,
                    network=network,
                    offline_fixture=offline_fixture,
                    fixture_data=fixture_data,
                )

                # 保存到缓存
                self.cache.save_events(date_str, result["events"], result["source_status"])

                # 统计
                total_events += result["total_events"]
                mapped_events += result["mapped_to_sectors"]
                unmapped_events += result["unmapped"]

                for event in result["events"]:
                    if event.source == "fixture":
                        fixture_event_count += 1
                    else:
                        real_event_count += 1

                generated_dates.append(date_str)

            except Exception as e:
                failed_dates.append({"date": date_str, "reason": str(e)[:200]})
                warnings.append(f"{date_str}: 采集失败 - {str(e)[:100]}")

            current += timedelta(days=1)

        # 汇总
        missing_cache_dates = []
        current = datetime.strptime(start_date, "%Y-%m-%d")
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            if not self.cache.exists(date_str):
                missing_cache_dates.append(date_str)
            current += timedelta(days=1)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "date_count": date_count,
            "generated_dates": generated_dates,
            "skipped_dates": skipped_dates,
            "failed_dates": failed_dates,
            "total_events": total_events,
            "mapped_events": mapped_events,
            "unmapped_events": unmapped_events,
            "real_event_count": real_event_count,
            "fixture_event_count": fixture_event_count,
            "missing_cache_dates": missing_cache_dates,
            "warnings": warnings,
        }

    def _select_symbols(
        self,
        date_str: str,
        report_root: str,
        explicit_symbols: Optional[List[str]],
        auto_symbols: bool,
        top_sectors: int,
        max_symbols_per_sector: int,
        max_symbols_total: int,
    ) -> List[str]:
        """选择 symbols"""
        if explicit_symbols:
            return explicit_symbols[:max_symbols_total]

        if not auto_symbols:
            return []

        # 从 sector_research 中选 symbols
        symbols = []

        # 尝试从 sector_research.json 读取
        research_path = os.path.join(
            report_root, "sector_research", date_str, "sector_research.json"
        )
        if os.path.exists(research_path):
            try:
                with open(research_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 从 daily_summary.top_watch_names 获取板块名
                summary = data.get("daily_summary", {})
                top_names = summary.get("top_watch_names", [])[:top_sectors]

                # 从 research_results 中获取板块名
                results = data.get("research_results", [])
                for r in results[:top_sectors]:
                    name = r.get("sector_name", "")
                    if name and name not in top_names:
                        top_names.append(name)

                # 简化：使用板块名称作为 symbols（后续可扩展为成分股）
                for name in top_names[:max_symbols_total]:
                    if name not in symbols:
                        symbols.append(name)

            except Exception:
                pass

        # 如果没有找到，使用默认 symbols
        if not symbols:
            symbols = ["600519", "300750", "000858"]

        return symbols[:max_symbols_total]


def save_historical_collection_summary(
    output_dir: str,
    summary_data: Dict[str, Any],
):
    """保存历史采集摘要"""
    os.makedirs(output_dir, exist_ok=True)

    # 保存 JSON
    json_path = os.path.join(output_dir, "catalyst_historical_collection_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"JSON summary saved: {json_path}")

    # 生成 Markdown
    md_report = generate_historical_collection_summary_md(summary_data)
    md_path = os.path.join(output_dir, "catalyst_historical_collection_summary.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"Markdown summary saved: {md_path}")


def generate_historical_collection_summary_md(summary_data: Dict[str, Any]) -> str:
    """生成历史采集摘要 Markdown"""
    lines = []

    lines.append("# 催化事件历史采集摘要")
    lines.append("")
    lines.append("> **免责声明**: 本报告仅用于数据采集验证，不作为操作依据。")
    lines.append("")

    lines.append("## 总览")
    lines.append("")
    lines.append(f"- **日期范围**: {summary_data.get('start_date', '')} ~ {summary_data.get('end_date', '')}")
    lines.append(f"- **总日期数**: {summary_data.get('date_count', 0)}")
    lines.append(f"- **成功日期**: {len(summary_data.get('generated_dates', []))}")
    lines.append(f"- **跳过日期**: {len(summary_data.get('skipped_dates', []))}")
    lines.append(f"- **失败日期**: {len(summary_data.get('failed_dates', []))}")
    lines.append("")

    lines.append("## 事件统计")
    lines.append("")
    lines.append(f"- **总事件数**: {summary_data.get('total_events', 0)}")
    lines.append(f"- **映射到板块**: {summary_data.get('mapped_events', 0)}")
    lines.append(f"- **未映射**: {summary_data.get('unmapped_events', 0)}")
    lines.append(f"- **真实事件**: {summary_data.get('real_event_count', 0)}")
    lines.append(f"- **Fixture 事件**: {summary_data.get('fixture_event_count', 0)}")
    lines.append("")

    # 缺失缓存日期
    missing = summary_data.get("missing_cache_dates", [])
    if missing:
        lines.append("## 缺失缓存日期")
        lines.append("")
        for d in missing[:10]:
            lines.append(f"- {d}")
        if len(missing) > 10:
            lines.append(f"- ... 共 {len(missing)} 天")
        lines.append("")

    # 警告
    warnings = summary_data.get("warnings", [])
    if warnings:
        lines.append("## 警告")
        lines.append("")
        for w in warnings[:10]:
            lines.append(f"- {w}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*本报告由 Theme Sector Radar 自动生成，仅用于数据采集验证，不作为操作依据。*")

    return "\n".join(lines)
