#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Factor Composite Shadow Score 历史回填脚本

为历史 top30_candidates.json 回填 factor_snapshot 和 factor_composite_shadow_score，
使评估脚本能获得真实样本。

本阶段只做历史文件回填和报告，不改变生产排序逻辑。

用法:
  python scripts/backfill_factor_composite_shadow_score.py --start 2026-07-01 --end 2026-07-10 --write-copy
  python scripts/backfill_factor_composite_shadow_score.py --start 2026-07-01 --end 2026-07-10 --force
  python scripts/backfill_factor_composite_shadow_score.py --start 2026-07-01 --end 2026-07-10 --dry-run
  python scripts/backfill_factor_composite_shadow_score.py --start 2026-07-01 --end 2026-07-10 --with-bars --bars-source http
"""

from __future__ import annotations

import argparse
import json
import os
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

from theme_sector_radar.factors.snapshot import build_factor_snapshot
from theme_sector_radar.scoring.factor_composite_shadow_score import compute_factor_composite_shadow_score
from theme_sector_radar.scoring.factor_composite_shadow_score_v2 import compute_factor_composite_shadow_score_v2
from theme_sector_radar.scoring.display_score_shadow import compute_display_score_shadow
from theme_sector_radar.data.stock_bars_provider import get_stock_bars_for_factor


# ============================================================
# Helpers
# ============================================================

def _service_date(value: datetime) -> str:
    """转换为 YYYYMMDD 格式。"""
    return value.strftime("%Y%m%d")


# ============================================================
# Data Loading
# ============================================================

def load_top30_candidates(path: Path) -> dict | None:
    """加载 top30_candidates.json。"""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def find_forward_return_file(date: str, forward_return_root: Path) -> Path | None:
    """查找 forward return 文件。

    支持常见命名：
    - {date}.json
    - forward_returns_{date}.json
    - forward_return_{date}.json
    """
    patterns = [
        f"{date}.json",
        f"forward_returns_{date}.json",
        f"forward_return_{date}.json",
    ]
    for pattern in patterns:
        path = forward_return_root / date / pattern
        if path.exists():
            return path
    return None


def load_forward_returns(date: str, forward_return_root: Path) -> dict[str, float] | None:
    """加载 forward returns。"""
    path = find_forward_return_file(date, forward_return_root)
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("returns", {})
    except Exception:
        return None


# ============================================================
# Backfill Logic
# ============================================================

def is_already_backfilled(data: dict) -> bool:
    """检查是否已经回填过。"""
    candidates = data.get("candidates", [])
    if not candidates:
        return False
    # 检查第一个 candidate 是否有 factor_composite_shadow_score
    first = candidates[0]
    return "factor_composite_shadow_score" in first


def backfill_candidates(data: dict, bars_map: dict[str, list[dict]] | None = None) -> dict:
    """回填 candidates 的 factor_snapshot 和 factor_composite_shadow_score。

    Args:
        data: 原始数据
        bars_map: 可选的 bars 数据映射 {code: bars}

    Returns:
        回填后的数据（不修改原数据）
    """
    # 深拷贝数据
    result = json.loads(json.dumps(data))
    candidates = result.get("candidates", [])

    for c in candidates:
        # 获取 bars
        code = c.get("code", "")
        bars = bars_map.get(code) if bars_map else None

        # 生成 factor_snapshot
        c["factor_snapshot"] = build_factor_snapshot(c, as_of=None, bars=bars)

        # 计算 factor_composite_shadow_score
        composite_result = compute_factor_composite_shadow_score(c)
        c["factor_composite_shadow_score"] = composite_result["factor_composite_shadow_score"]
        c["factor_composite_breakdown"] = composite_result["factor_composite_breakdown"]
        c["factor_composite_tags"] = composite_result["factor_composite_tags"]

        # 计算 factor_composite_shadow_score_v2
        composite_v2_result = compute_factor_composite_shadow_score_v2(c)
        c["factor_composite_shadow_score_v2"] = composite_v2_result["factor_composite_shadow_score_v2"]
        c["factor_composite_breakdown_v2"] = composite_v2_result["factor_composite_breakdown_v2"]
        c["factor_composite_tags_v2"] = composite_v2_result["factor_composite_tags_v2"]

        # 计算 display_score_shadow
        display_result = compute_display_score_shadow(c)
        c["display_score_shadow_90_10"] = display_result["display_score_shadow_90_10"]
        c["display_score_shadow_80_20"] = display_result["display_score_shadow_80_20"]
        c["display_score_shadow_70_30"] = display_result["display_score_shadow_70_30"]
        c["display_score_shadow_breakdown"] = display_result["display_score_shadow_breakdown"]
        c["display_score_shadow_tags"] = display_result["display_score_shadow_tags"]

    return result


def calc_forward_return_coverage(
    candidates: list[dict],
    forward_returns: dict[str, float] | None,
) -> dict:
    """计算 forward return 匹配率。"""
    if not forward_returns:
        return {
            "has_forward_return": False,
            "candidate_count": len(candidates),
            "matched_count": 0,
            "coverage_rate": 0.0,
        }

    candidate_codes = {c.get("code", "") for c in candidates}
    forward_codes = set(forward_returns.keys())
    matched = candidate_codes & forward_codes

    return {
        "has_forward_return": True,
        "candidate_count": len(candidates),
        "forward_return_count": len(forward_returns),
        "matched_count": len(matched),
        "coverage_rate": round(len(matched) / len(candidates) * 100, 2) if candidates else 0,
    }


# ============================================================
# Report Generation
# ============================================================

def generate_json_report(report: dict, output_path: Path) -> None:
    """生成 JSON 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generate_markdown_report(report: dict, output_path: Path) -> None:
    """生成 Markdown 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Factor Composite Shadow Score 回填报告\n")

    # 运行摘要
    summary = report["summary"]
    lines.append("## 运行摘要\n")
    lines.append(f"- 评估区间: {summary['start_date']} ~ {summary['end_date']}")
    lines.append(f"- 总天数: {summary['total_dates']}")
    lines.append(f"- 已处理天数: {summary['processed_dates']}")
    lines.append(f"- 回填 candidate 数量: {summary['backfilled_candidates']}")
    lines.append(f"- 已有 factor_composite_shadow_score: {summary['existing_composite_scores']}")
    lines.append(f"- 新增 factor_composite_shadow_score: {summary['new_composite_scores']}")
    lines.append(f"- forward return 覆盖率: {summary['forward_return_coverage']:.1f}%")
    lines.append("")

    # 每日状态表
    lines.append("## 每日状态\n")
    lines.append("| 日期 | 状态 | Candidates | Forward Return |")
    lines.append("|------|------|-----------|----------------|")
    for daily in report["daily_results"]:
        status = daily["status"]
        count = daily["candidate_count"]
        fr_status = daily.get("forward_return_status", "N/A")
        lines.append(f"| {daily['date']} | {status} | {count} | {fr_status} |")
    lines.append("")

    # 建议
    lines.append("## 建议\n")
    if summary["processed_dates"] > 0 and summary["forward_return_coverage"] > 50:
        lines.append("- **建议立即重新运行 evaluate_factor_composite_shadow_score.py**")
        lines.append(f"- 已回填 {summary['processed_dates']} 天数据，forward return 覆盖率 {summary['forward_return_coverage']:.1f}%")
    elif summary["processed_dates"] > 0:
        lines.append("- **可考虑运行评估脚本**")
        lines.append(f"- 已回填 {summary['processed_dates']} 天数据，但 forward return 覆盖率较低 ({summary['forward_return_coverage']:.1f}%)")
    else:
        lines.append("- **暂无足够数据运行评估**")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# Main Backfill
# ============================================================

def backfill_date(
    date: str,
    candidate_root: Path,
    forward_return_root: Path,
    output_root: Path,
    dry_run: bool = False,
    force: bool = False,
    write_copy: bool = False,
    bars_map: dict[str, list[dict]] | None = None,
) -> dict:
    """回填单天数据。"""
    result = {
        "date": date,
        "status": "unknown",
        "candidate_count": 0,
        "existing_composite_score": False,
        "backfilled": False,
        "forward_return_status": "no_forward_return",
        "forward_return_coverage": 0.0,
        "bars_requested_count": 0,
        "bars_matched_count": 0,
        "bars_missing_count": 0,
    }

    # 加载 candidate 文件
    candidate_path = candidate_root / date / "top30_candidates.json"
    data = load_top30_candidates(candidate_path)
    if data is None:
        result["status"] = "missing_candidate_file"
        return result

    candidates = data.get("candidates", [])
    if not candidates:
        result["status"] = "no_candidates"
        return result

    result["candidate_count"] = len(candidates)

    # 检查是否已回填
    if is_already_backfilled(data):
        result["existing_composite_score"] = True
        if not force:
            result["status"] = "already_backfilled"
            return result

    # 加载 forward return
    forward_returns = load_forward_returns(date, forward_return_root)
    fr_coverage = calc_forward_return_coverage(candidates, forward_returns)
    result["forward_return_coverage"] = fr_coverage["coverage_rate"]
    if fr_coverage["has_forward_return"]:
        result["forward_return_status"] = f"matched {fr_coverage['matched_count']}/{fr_coverage['candidate_count']}"

    # 统计 bars 覆盖
    if bars_map:
        result["bars_requested_count"] = len(candidates)
        result["bars_matched_count"] = sum(1 for c in candidates if c.get("code", "") in bars_map)
        result["bars_missing_count"] = result["candidate_count"] - result["bars_matched_count"]

    # 回填
    if dry_run:
        result["status"] = "dry_run"
        result["backfilled"] = True
        return result

    try:
        backfilled_data = backfill_candidates(data, bars_map)
        result["backfilled"] = True
        result["status"] = "processed"

        # 写入文件
        if write_copy:
            output_path = output_root / date / "top30_candidates.factor_backfilled.json"
        elif force:
            output_path = candidate_path
        else:
            # 默认写副本
            output_path = output_root / date / "top30_candidates.factor_backfilled.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(backfilled_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    except Exception as e:
        result["status"] = f"error: {str(e)}"

    return result


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Backfill Factor Composite Shadow Score"
    )
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument(
        "--candidate-root",
        default=str(PROJECT_ROOT / "reports" / "agent_bridge"),
        help="Root directory for candidate files",
    )
    parser.add_argument(
        "--forward-return-root",
        default=str(PROJECT_ROOT / "reports" / "forward_returns"),
        help="Root directory for forward return files",
    )
    parser.add_argument(
        "--output-root",
        default=str(PROJECT_ROOT / "reports" / "agent_bridge"),
        help="Output root directory",
    )
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--force", action="store_true", help="Force overwrite original files")
    parser.add_argument("--write-copy", action="store_true", help="Write to copy file")
    parser.add_argument("--with-bars", action="store_true", help="Fetch bars for new factors (requires network)")
    parser.add_argument("--bars-source", choices=["auto", "http", "stockdb-sdk"], default="auto", help="Bars data source")
    args = parser.parse_args()

    candidate_root = Path(args.candidate_root)
    forward_return_root = Path(args.forward_return_root)
    output_root = Path(args.output_root)

    print(f"  Backfilling Factor Composite Shadow Score...")
    print(f"  Period: {args.start} ~ {args.end}")
    print(f"  Mode: {'dry-run' if args.dry_run else 'force' if args.force else 'write-copy' if args.write_copy else 'default'}")
    print(f"  With bars: {args.with_bars}")

    # 生成日期列表
    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    # 处理每天
    daily_results = []
    total_backfilled = 0
    total_existing = 0
    total_coverage = 0
    coverage_count = 0

    for date in dates:
        # 如果需要 bars，为当天所有 candidate 获取 bars
        bars_map = None
        if args.with_bars:
            bars_map = {}
            candidate_path = candidate_root / date / "top30_candidates.json"
            data = load_top30_candidates(candidate_path)
            if data:
                candidates = data.get("candidates", [])
                for c in candidates:
                    code = c.get("code", "")
                    if code:
                        try:
                            # 使用统一的 stock_bars_provider
                            bars_result = get_stock_bars_for_factor(
                                code=code,
                                as_of=date,
                                lookback=80,
                                source=args.bars_source,
                            )
                            if bars_result["status"] == "ok":
                                bars_map[code] = bars_result["bars"]
                        except Exception:
                            pass  # 优雅降级

        result = backfill_date(
            date=date,
            candidate_root=candidate_root,
            forward_return_root=forward_return_root,
            output_root=output_root,
            dry_run=args.dry_run,
            force=args.force,
            write_copy=args.write_copy,
            bars_map=bars_map,
        )
        daily_results.append(result)

        if result["backfilled"]:
            total_backfilled += result["candidate_count"]
        if result["existing_composite_score"]:
            total_existing += result["candidate_count"]
        if result["forward_return_coverage"] > 0:
            total_coverage += result["forward_return_coverage"]
            coverage_count += 1

        # 打印状态
        status_icon = {
            "processed": "✅",
            "dry_run": "🔍",
            "already_backfilled": "⏭️",
            "missing_candidate_file": "❌",
            "no_candidates": "⚠️",
        }.get(result["status"].split(":")[0], "❓")
        print(f"  {status_icon} {date}: {result['status']} ({result['candidate_count']} candidates)")

    # 生成报告
    avg_coverage = total_coverage / coverage_count if coverage_count > 0 else 0
    report = {
        "summary": {
            "start_date": args.start,
            "end_date": args.end,
            "total_dates": len(dates),
            "processed_dates": sum(1 for r in daily_results if r["status"] in ("processed", "dry_run")),
            "backfilled_candidates": total_backfilled,
            "existing_composite_scores": total_existing,
            "new_composite_scores": total_backfilled - total_existing if total_backfilled > total_existing else 0,
            "forward_return_coverage": avg_coverage,
        },
        "daily_results": daily_results,
    }

    # 写入报告
    output_dir = Path(PROJECT_ROOT / "reports" / "factor_composite_shadow_score")
    filename = f"backfill_{args.start}_{args.end}"
    json_path = output_dir / f"{filename}.json"
    md_path = output_dir / f"{filename}.md"

    generate_json_report(report, json_path)
    generate_markdown_report(report, md_path)

    print(f"\n  ✅ Backfill complete")
    print(f"  📊 Processed: {report['summary']['processed_dates']}/{len(dates)} days")
    print(f"  📦 Backfilled candidates: {total_backfilled}")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")


if __name__ == "__main__":
    main()
