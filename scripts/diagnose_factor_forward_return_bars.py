#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bars 数据源诊断脚本

诊断为什么 build_factor_forward_returns.py 的 matched_count=0，
检查 bars 数据源可用性和覆盖情况。

用法:
  python scripts/diagnose_factor_forward_return_bars.py --start 2026-07-01 --end 2026-07-10
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _parse_date(value: str) -> datetime:
    """解析日期字符串。"""
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(value[:10] if fmt == "%Y-%m-%d" else value[:8], fmt)
        except ValueError:
            continue
    raise ValueError(f"unsupported date: {value}")


def _date_key(value: str) -> str:
    """转换为 YYYY-MM-DD 格式。"""
    return _parse_date(value).strftime("%Y-%m-%d")


def _service_date(value: datetime) -> str:
    """转换为 YYYYMMDD 格式。"""
    return value.strftime("%Y%m%d")


def _coerce_float(value: Any) -> float | None:
    """安全转换为 float。"""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_code(code: str) -> str:
    """标准化股票代码格式。

    支持格式:
    - 600001
    - sh600001
    - 600001.SH
    - SZ000001
    - 000001.SZ
    """
    code = code.strip().upper()

    # 去除前缀
    if code.startswith("SH"):
        code = code[2:]
    elif code.startswith("SZ"):
        code = code[2:]

    # 去除后缀
    if "." in code:
        code = code.split(".")[0]

    return code


def load_candidates(date: str, candidate_root: Path) -> list[dict] | None:
    """加载候选股列表。"""
    # 优先使用 backfilled 文件
    backfilled_path = candidate_root / date / "top30_candidates.factor_backfilled.json"
    if backfilled_path.exists():
        try:
            data = json.loads(backfilled_path.read_text(encoding="utf-8"))
            return data.get("candidates", [])
        except Exception:
            pass

    original_path = candidate_root / date / "top30_candidates.json"
    if original_path.exists():
        try:
            data = json.loads(original_path.read_text(encoding="utf-8"))
            return data.get("candidates", [])
        except Exception:
            return None

    return None


def diagnose_bars_availability(
    start_date: str,
    end_date: str,
    candidate_root: Path,
) -> dict:
    """诊断 bars 数据可用性。"""
    # 生成日期列表
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    # 统计
    stats = {
        "total_dates": len(dates),
        "missing_candidate_file": 0,
        "no_candidates": 0,
        "total_candidates": 0,
        "missing_reason_counts": {
            "missing_candidate_file": 0,
            "no_candidates": 0,
            "no_bars_provider": 0,
            "bars_empty": 0,
            "bars_date_not_cover_as_of": 0,
            "bars_no_future_window": 0,
            "exception": 0,
        },
        "provider_status": {},
        "sample_bars": [],
    }

    # 检查 bars provider 可用性
    provider_status = {
        "http": {"available": False, "error": None, "latest_date": None},
        "stockdb_sdk": {"available": False, "error": None, "latest_date": None},
    }

    # 检查 HTTP client
    try:
        from theme_sector_radar.data.market_data_http_client import MarketDataHttpClient
        http_client = MarketDataHttpClient()
        health = http_client.health_check()
        provider_status["http"]["available"] = True
        provider_status["http"]["latest_date"] = health.get("latest_daily_date")
    except Exception as e:
        provider_status["http"]["error"] = str(e)

    # 检查 StockDB SDK
    try:
        from theme_sector_radar.data.stockdb_sdk_client import StockDBSdkClient
        sdk_client = StockDBSdkClient()
        latest = sdk_client.get_latest_daily_date()
        provider_status["stockdb_sdk"]["available"] = True
        provider_status["stockdb_sdk"]["latest_date"] = latest
    except Exception as e:
        provider_status["stockdb_sdk"]["error"] = str(e)

    stats["provider_status"] = provider_status

    # 诊断每天的数据
    for date in dates:
        candidates = load_candidates(date, candidate_root)
        if candidates is None:
            stats["missing_reason_counts"]["missing_candidate_file"] += 1
            continue
        if not candidates:
            stats["no_candidates"] += 1
            continue

        stats["total_candidates"] += len(candidates)

        # 取样检查 bars
        if len(stats["sample_bars"]) < 3:
            for c in candidates[:1]:
                code = c.get("code", "")
                normalized = normalize_code(code)
                stats["sample_bars"].append({
                    "date": date,
                    "code": code,
                    "normalized_code": normalized,
                    "name": c.get("name", ""),
                })

    return stats


def generate_json_report(stats: dict, output_path: Path) -> None:
    """生成 JSON 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generate_markdown_report(stats: dict, output_path: Path) -> None:
    """生成 Markdown 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Bars 数据源诊断报告\n")

    # 运行摘要
    lines.append("## 运行摘要\n")
    lines.append(f"- 诊断天数: {stats['total_dates']}")
    lines.append(f"- 总候选股数: {stats['total_candidates']}")
    lines.append("")

    # Provider 状态
    lines.append("## 数据源状态\n")
    for provider, status in stats["provider_status"].items():
        lines.append(f"### {provider}\n")
        lines.append(f"- 可用: {'是' if status['available'] else '否'}")
        if status.get("latest_date"):
            lines.append(f"- 最新日期: {status['latest_date']}")
        if status.get("error"):
            lines.append(f"- 错误: {status['error']}")
        lines.append("")

    # 失败原因统计
    lines.append("## 失败原因统计\n")
    for reason, count in stats["missing_reason_counts"].items():
        if count > 0:
            lines.append(f"- {reason}: {count}")
    lines.append("")

    # 样例 bars
    if stats["sample_bars"]:
        lines.append("## 样例候选股\n")
        lines.append("| 日期 | 代码 | 标准化代码 | 名称 |")
        lines.append("|------|------|-----------|------|")
        for sample in stats["sample_bars"]:
            lines.append(f"| {sample['date']} | {sample['code']} | {sample['normalized_code']} | {sample['name']} |")
        lines.append("")

    # 结论
    lines.append("## 结论\n")
    http_available = stats["provider_status"].get("http", {}).get("available", False)
    sdk_available = stats["provider_status"].get("stockdb_sdk", {}).get("available", False)

    if http_available or sdk_available:
        lines.append("- ✅ 至少一个数据源可用")
        if not http_available:
            lines.append("- ⚠️ HTTP 数据源不可用，建议检查 market_data_service")
        if not sdk_available:
            lines.append("- ⚠️ StockDB SDK 不可用，建议检查本地数据库")
    else:
        lines.append("- ❌ 没有可用的 bars 数据源")
        lines.append("- 建议: 启动 market_data_service 或配置 StockDB SDK")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Diagnose bars data availability"
    )
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument(
        "--candidate-root",
        default=str(PROJECT_ROOT / "reports" / "agent_bridge"),
        help="Root directory for candidate files",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports" / "factor_composite_shadow_score"),
        help="Output directory for reports",
    )
    args = parser.parse_args()

    candidate_root = Path(args.candidate_root)
    output_dir = Path(args.output_dir)

    print(f"  Diagnosing bars data availability...")
    print(f"  Period: {args.start} ~ {args.end}")

    # 运行诊断
    stats = diagnose_bars_availability(args.start, args.end, candidate_root)

    # 生成报告
    filename = f"bars_diagnosis_{args.start}_{args.end}"
    json_path = output_dir / f"{filename}.json"
    md_path = output_dir / f"{filename}.md"

    generate_json_report(stats, json_path)
    generate_markdown_report(stats, md_path)

    print(f"\n  ✅ Diagnosis complete")
    print(f"  📊 Total candidates: {stats['total_candidates']}")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")

    # 打印 provider 状态
    for provider, status in stats["provider_status"].items():
        status_icon = "✅" if status["available"] else "❌"
        print(f"  {status_icon} {provider}: {'available' if status['available'] else status.get('error', 'unknown')}")


if __name__ == "__main__":
    main()
