#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Bars Sources 诊断脚本

诊断 bars 数据源可用性，帮助确定哪些 source 可以使用。

用法:
  python scripts/diagnose_stock_bars_sources.py --date 2026-07-08 --codes 000001,600001 --sources cache,http,stockdb-sdk,auto
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.data.stock_bars_provider import get_stock_bars_for_factor


def diagnose_bars_sources(
    date: str,
    codes: list[str],
    sources: list[str],
    lookback: int = 80,
) -> dict:
    """诊断 bars 数据源可用性。"""
    results = []

    for code in codes:
        code_results = []
        for source in sources:
            result = get_stock_bars_for_factor(
                code=code,
                as_of=date,
                lookback=lookback,
                source=source,
            )

            # 提取示例 bar
            sample_bar = None
            if result["bars"]:
                sample_bar = result["bars"][0]

            code_results.append({
                "source": source,
                "status": result["status"],
                "bars_count": len(result["bars"]),
                "first_date": result["bars"][0].get("date") if result["bars"] else None,
                "last_date": result["bars"][-1].get("date") if result["bars"] else None,
                "missing_reason": result.get("missing_reason", ""),
                "sample_bar": sample_bar,
            })

        results.append({
            "code": code,
            "sources": code_results,
        })

    return {
        "date": date,
        "lookback": lookback,
        "results": results,
    }


def generate_markdown_report(diagnosis: dict) -> str:
    """生成 Markdown 报告。"""
    lines = []
    lines.append("# Stock Bars Sources Diagnosis\n")
    lines.append(f"- 诊断日期: {diagnosis['date']}")
    lines.append(f"- 回溯天数: {diagnosis['lookback']}")
    lines.append("")

    for code_result in diagnosis["results"]:
        code = code_result["code"]
        lines.append(f"## {code}\n")
        lines.append("| Source | Status | Bars Count | First Date | Last Date | Missing Reason |")
        lines.append("|--------|--------|------------|------------|-----------|----------------|")
        for source_result in code_result["sources"]:
            source = source_result["source"]
            status = source_result["status"]
            bars_count = source_result["bars_count"]
            first_date = source_result.get("first_date", "N/A")
            last_date = source_result.get("last_date", "N/A")
            missing_reason = source_result.get("missing_reason", "")

            status_icon = "✅" if status == "ok" else "❌"
            lines.append(f"| {source} | {status_icon} {status} | {bars_count} | {first_date} | {last_date} | {missing_reason} |")
        lines.append("")

    # 总结
    lines.append("## 总结\n")
    ok_count = sum(1 for r in diagnosis["results"] for s in r["sources"] if s["status"] == "ok" and s["bars_count"] >= 20)
    lines.append(f"- 可用 source 数量: {ok_count}")
    if ok_count > 0:
        lines.append("- ✅ 至少有一个 source 可用")
    else:
        lines.append("- ❌ 没有可用的 source")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Diagnose Stock Bars Sources"
    )
    parser.add_argument("--date", required=True, help="Date YYYY-MM-DD")
    parser.add_argument("--codes", required=True, help="Comma-separated stock codes")
    parser.add_argument("--sources", default="cache,http,stockdb-sdk,auto", help="Comma-separated sources")
    parser.add_argument("--lookback", type=int, default=80, help="Lookback days")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "reports" / "stock_bars_diagnosis"),
        help="Output directory for reports",
    )
    args = parser.parse_args()

    codes = [c.strip() for c in args.codes.split(",")]
    sources = [s.strip() for s in args.sources.split(",")]
    output_dir = Path(args.output_dir)

    print(f"  Diagnosing Stock Bars Sources...")
    print(f"  Date: {args.date}")
    print(f"  Codes: {codes}")
    print(f"  Sources: {sources}")

    # 运行诊断
    diagnosis = diagnose_bars_sources(args.date, codes, sources, args.lookback)

    # 生成报告
    md_content = generate_markdown_report(diagnosis)

    # 写入文件
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"bars_sources_{args.date}.json"
    md_path = output_dir / f"bars_sources_{args.date}.md"

    json_path.write_text(json.dumps(diagnosis, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(md_content, encoding="utf-8")

    print(f"\n  ✅ Diagnosis complete")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")

    # 打印结果
    for code_result in diagnosis["results"]:
        code = code_result["code"]
        ok_sources = [s for s in code_result["sources"] if s["status"] == "ok" and s["bars_count"] >= 20]
        if ok_sources:
            print(f"  ✅ {code}: {len(ok_sources)} source(s) available")
        else:
            print(f"  ❌ {code}: no source available")


if __name__ == "__main__":
    main()
