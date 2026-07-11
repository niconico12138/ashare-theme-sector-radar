#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Analysis Fields 历史回填脚本

对历史 top30_candidates.json 回填 selection_quality / stock_profile / stock_explanation 相关结构字段，
确保每只历史 candidate 都能被归入合理的 opportunity_type。

本阶段不改变生产 selection_quality 规则，只修历史样本结构。

用法:
  python scripts/backfill_stock_analysis_fields.py --start 2026-04-01 --end 2026-07-10 --write-copy
  python scripts/backfill_stock_analysis_fields.py --start 2026-04-01 --end 2026-07-10 --force
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

from theme_sector_radar.reporting.daily_decision_summary import normalize_stock_item
from theme_sector_radar.reporting.selection_quality import classify_stock_candidate
from theme_sector_radar.reporting.stock_profile import build_stock_profile
from theme_sector_radar.reporting.stock_explanation import build_stock_explanation


# ============================================================
# Helpers
# ============================================================

def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为 float。"""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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


def load_candidate_file(date: str, candidate_root: Path) -> dict | None:
    """加载候选股文件。优先读取 factor_backfilled（包含最新 factor_snapshot）。"""
    # 优先读取 factor_backfilled（包含最新 factor_snapshot）
    backfilled_path = candidate_root / date / "top30_candidates.factor_backfilled.json"
    if backfilled_path.exists():
        try:
            return json.loads(backfilled_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 回退到原始文件
    original_path = candidate_root / date / "top30_candidates.json"
    if original_path.exists():
        try:
            return json.loads(original_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    return None


# ============================================================
# Backfill Logic
# ============================================================

def infer_source_pool(candidate: dict) -> str:
    """推断 source_pool。"""
    # 优先从 candidate 直接读取
    source_pool = candidate.get("source_pool")
    if source_pool:
        # 规范化 source_pool
        if source_pool in ("trend", "both"):
            return "trend_top"
        elif source_pool == "burst":
            return "burst_top"
        return source_pool

    # 从 signal_type 推断
    signal_type = candidate.get("signal_type", "")
    if signal_type == "low_final_high_v2":
        return "v2_potential"
    elif signal_type == "high_final_low_v2":
        return "divergence_review"

    # 从 selection_bucket 推断
    selection_bucket = candidate.get("selection_bucket", "")
    if selection_bucket == "v2_opportunity":
        return "v2_potential"
    elif selection_bucket == "divergence_review":
        return "divergence_review"
    elif selection_bucket == "blocked":
        return "unknown_source"

    # 从字段特征推断
    stock_short_score = _safe_float(candidate.get("stock_short_score_v2"))
    if stock_short_score > 60:
        return "burst_top"

    final_score = _safe_float(candidate.get("final_score"))
    if final_score >= 55:
        return "trend_top"

    return "unknown_source"


def backfill_stock_analysis_fields(data: dict) -> dict:
    """回填 stock analysis fields。

    Returns:
        回填后的数据（不修改原数据）
    """
    # 深拷贝数据
    result = json.loads(json.dumps(data))
    candidates = result.get("candidates", [])

    for c in candidates:
        # 1. 推断 source_pool
        source_pool = infer_source_pool(c)
        c["source_pool"] = source_pool

        # 2. 规范化字段
        normalized = normalize_stock_item(c, source_pool)
        c.update(normalized)

        # 3. 分类
        classification = classify_stock_candidate(c, source_pool)
        c["selection_bucket"] = classification["selection_bucket"]
        c["selection_score"] = classification["selection_score"]
        c["selection_score_adjusted"] = classification["selection_score_adjusted"]
        c["quality_level"] = classification["quality_level"]
        c["quality_confirmations"] = classification["quality_confirmations"]
        c["soft_warnings"] = classification["soft_warnings"]
        c["hard_blockers"] = classification["hard_blockers"]
        c["action_state"] = classification["action_state"]

        # 4. 生成 stock_profile
        profile = build_stock_profile(c)
        c["stock_profile"] = profile
        c["sector_support_state"] = profile.get("sector_support", "unknown")

        # 5. 生成 stock_explanation
        explanation = build_stock_explanation(c, profile)
        c["opportunity_type"] = explanation["opportunity_type"]
        c["reason_codes"] = explanation["reason_codes"]
        c["invalidation_flags"] = explanation["invalidation_flags"]
        c["historical_hint"] = explanation["historical_hint"]
        c["explanation_text"] = explanation["explanation_text"]

        # 6. 生成 bars_factor_policy (从 classification 中获取)
        c["bars_factor_policy"] = classification.get("bars_factor_policy", {})

    return result


# ============================================================
# Report Generation
# ============================================================

def generate_report(
    start_date: str,
    end_date: str,
    daily_results: list[dict],
) -> dict:
    """生成报告。"""
    processed_days = sum(1 for r in daily_results if r["status"] == "processed")
    processed_candidates = sum(r["candidate_count"] for r in daily_results if r["status"] == "processed")

    # 统计 opportunity_type 分布
    opportunity_type_counts: dict[str, int] = {}
    selection_bucket_counts: dict[str, int] = {}
    source_pool_counts: dict[str, int] = {}
    sector_support_state_counts: dict[str, int] = {}
    missing_counts = {"final_score": 0, "v2_score": 0, "factor_snapshot": 0, "sector_support_score": 0}

    for r in daily_results:
        if r["status"] != "processed":
            continue

        for ot in r.get("opportunity_types", {}):
            opportunity_type_counts[ot] = opportunity_type_counts.get(ot, 0) + r["opportunity_types"][ot]

        for sb in r.get("selection_buckets", {}):
            selection_bucket_counts[sb] = selection_bucket_counts.get(sb, 0) + r["selection_buckets"][sb]

        for sp in r.get("source_pools", {}):
            source_pool_counts[sp] = source_pool_counts.get(sp, 0) + r["source_pools"][sp]

        for ss in r.get("sector_support_states", {}):
            sector_support_state_counts[ss] = sector_support_state_counts.get(ss, 0) + r["sector_support_states"][ss]

        for mc in r.get("missing_counts", {}):
            missing_counts[mc] = missing_counts.get(mc, 0) + r["missing_counts"][mc]

    return {
        "schema_version": "1.0",
        "start": start_date,
        "end": end_date,
        "processed_days": processed_days,
        "processed_candidates": processed_candidates,
        "opportunity_type_counts": opportunity_type_counts,
        "selection_bucket_counts": selection_bucket_counts,
        "source_pool_counts": source_pool_counts,
        "sector_support_state_counts": sector_support_state_counts,
        "missing_counts": missing_counts,
    }


# ============================================================
# Main Backfill
# ============================================================

def backfill_date(
    date: str,
    candidate_root: Path,
    output_root: Path,
    dry_run: bool = False,
    force: bool = False,
    write_copy: bool = True,
) -> dict:
    """回填单天数据。"""
    result = {
        "date": date,
        "status": "unknown",
        "candidate_count": 0,
        "opportunity_types": {},
        "selection_buckets": {},
        "source_pools": {},
        "sector_support_states": {},
        "missing_counts": {"final_score": 0, "v2_score": 0, "factor_snapshot": 0, "sector_support_score": 0},
    }

    # 加载 candidate 文件（优先读取 factor_backfilled，包含最新 factor_snapshot）
    data = load_candidate_file(date, candidate_root)
    if data is None:
        result["status"] = "missing_candidate_file"
        return result

    candidates = data.get("candidates", [])
    if not candidates:
        result["status"] = "no_candidates"
        return result

    result["candidate_count"] = len(candidates)

    # 回填
    if dry_run:
        result["status"] = "dry_run"
        return result

    try:
        backfilled_data = backfill_stock_analysis_fields(data)
        result["status"] = "processed"

        # 统计分布
        for c in backfilled_data.get("candidates", []):
            ot = c.get("opportunity_type", "unknown")
            result["opportunity_types"][ot] = result["opportunity_types"].get(ot, 0) + 1

            sb = c.get("selection_bucket", "unknown")
            result["selection_buckets"][sb] = result["selection_buckets"].get(sb, 0) + 1

            sp = c.get("source_pool", "unknown")
            result["source_pools"][sp] = result["source_pools"].get(sp, 0) + 1

            ss = c.get("sector_support_state", "unknown")
            result["sector_support_states"][ss] = result["sector_support_states"].get(ss, 0) + 1

            if c.get("final_score") is None:
                result["missing_counts"]["final_score"] += 1
            if c.get("v2_score") is None and c.get("factor_composite_shadow_score_v2") is None:
                result["missing_counts"]["v2_score"] += 1
            if c.get("factor_snapshot") is None:
                result["missing_counts"]["factor_snapshot"] += 1
            if c.get("sector_support_score") is None:
                result["missing_counts"]["sector_support_score"] += 1

        # 写入文件
        if write_copy:
            output_path = output_root / date / "top30_candidates.analysis_backfilled.json"
        elif force:
            output_path = candidate_path
        else:
            output_path = output_root / date / "top30_candidates.analysis_backfilled.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(backfilled_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    except Exception as e:
        result["status"] = f"error: {str(e)}"

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Backfill Stock Analysis Fields"
    )
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    parser.add_argument(
        "--candidate-root",
        default=str(PROJECT_ROOT / "reports" / "agent_bridge"),
        help="Root directory for candidate files",
    )
    parser.add_argument(
        "--output-root",
        default=str(PROJECT_ROOT / "reports" / "agent_bridge"),
        help="Output root directory",
    )
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--force", action="store_true", help="Force overwrite original files")
    parser.add_argument("--write-copy", action="store_true", default=True, help="Write to copy file")
    args = parser.parse_args()

    candidate_root = Path(args.candidate_root)
    output_root = Path(args.output_root)

    print(f"  Backfilling Stock Analysis Fields...")
    print(f"  Period: {args.start} ~ {args.end}")
    print(f"  Mode: {'dry-run' if args.dry_run else 'force' if args.force else 'write-copy' if args.write_copy else 'default'}")

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

    for date in dates:
        result = backfill_date(
            date=date,
            candidate_root=candidate_root,
            output_root=output_root,
            dry_run=args.dry_run,
            force=args.force,
            write_copy=args.write_copy,
        )
        daily_results.append(result)

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
    report = generate_report(args.start, args.end, daily_results)

    # 写入报告
    output_dir = Path(PROJECT_ROOT / "reports" / "stock_analysis_backfill")
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"stock_analysis_backfill_{args.start}_{args.end}"
    json_path = output_dir / f"{filename}.json"
    md_path = output_dir / f"{filename}.md"

    # JSON 报告
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # MD 报告
    lines = []
    lines.append("# Stock Analysis Fields Backfill Report\n")
    lines.append("## 运行摘要\n")
    lines.append(f"- 评估区间: {args.start} ~ {args.end}")
    lines.append(f"- 处理天数: {report['processed_days']}")
    lines.append(f"- 处理候选股: {report['processed_candidates']}")
    lines.append("")
    lines.append("## Opportunity Type 分布\n")
    lines.append("| 类型 | 数量 |")
    lines.append("|------|------|")
    for ot, count in sorted(report["opportunity_type_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"| {ot} | {count} |")
    lines.append("")
    lines.append("## Selection Bucket 分布\n")
    lines.append("| Bucket | 数量 |")
    lines.append("|--------|------|")
    for sb, count in sorted(report["selection_bucket_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"| {sb} | {count} |")
    lines.append("")
    lines.append("## Source Pool 分布\n")
    lines.append("| Source Pool | 数量 |")
    lines.append("|-------------|------|")
    for sp, count in sorted(report["source_pool_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"| {sp} | {count} |")
    lines.append("")
    lines.append("## Sector Support State 分布\n")
    lines.append("| State | 数量 |")
    lines.append("|-------|------|")
    for ss, count in sorted(report["sector_support_state_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"| {ss} | {count} |")
    lines.append("")
    lines.append("## Missing Counts\n")
    lines.append("| 字段 | 缺失数 |")
    lines.append("|------|--------|")
    for field, count in report["missing_counts"].items():
        lines.append(f"| {field} | {count} |")
    lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n  ✅ Backfill complete")
    print(f"  📊 Processed: {report['processed_days']} days, {report['processed_candidates']} candidates")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")

    # 打印 opportunity_type 分布
    print(f"\n  📊 Opportunity Type Distribution:")
    for ot, count in sorted(report["opportunity_type_counts"].items(), key=lambda x: -x[1]):
        print(f"     {ot}: {count}")


if __name__ == "__main__":
    main()
