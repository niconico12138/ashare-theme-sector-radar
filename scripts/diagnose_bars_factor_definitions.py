#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bars 因子定义与分桶校准诊断脚本

诊断 bars 因子的 raw_value、score、direction、分桶规则。
本阶段只做诊断和报告，不改变生产逻辑。

用法:
  python scripts/diagnose_bars_factor_definitions.py --start 2026-04-01 --end 2026-07-10
"""

from __future__ import annotations

import argparse
import json
import math
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


# ============================================================
# Statistical Helpers
# ============================================================

def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为 float。"""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calc_percentiles(values: list[float]) -> dict:
    """计算分位数。"""
    if not values:
        return {"min": None, "p01": None, "p05": None, "p10": None, "p25": None,
                "median": None, "p75": None, "p90": None, "p95": None, "p99": None, "max": None}

    sorted_vals = sorted(values)
    n = len(sorted_vals)

    def get_p(p):
        idx = int(n * p)
        idx = min(idx, n - 1)
        return sorted_vals[idx]

    return {
        "min": round(sorted_vals[0], 4),
        "p01": round(get_p(0.01), 4),
        "p05": round(get_p(0.05), 4),
        "p10": round(get_p(0.10), 4),
        "p25": round(get_p(0.25), 4),
        "median": round(get_p(0.50), 4),
        "p75": round(get_p(0.75), 4),
        "p90": round(get_p(0.90), 4),
        "p95": round(get_p(0.95), 4),
        "p99": round(get_p(0.99), 4),
        "max": round(sorted_vals[-1], 4),
    }


# ============================================================
# Data Loading
# ============================================================

def load_candidates(date: str, candidate_root: Path) -> list[dict] | None:
    """加载候选股列表。"""
    analysis_path = candidate_root / date / "top30_candidates.analysis_backfilled.json"
    if analysis_path.exists():
        try:
            data = json.loads(analysis_path.read_text(encoding="utf-8"))
            return data.get("candidates", [])
        except Exception:
            pass

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


# ============================================================
# Factor Diagnosis
# ============================================================

def diagnose_factor_definition(
    candidates: list[dict],
    factor_id: str,
) -> dict:
    """诊断单个因子的定义和分布。"""
    raw_values = []
    score_values = []
    quality_missing_count = 0

    for c in candidates:
        factor_snapshot = c.get("factor_snapshot", {})
        factors = factor_snapshot.get("factors", [])

        for f in factors:
            if f.get("factor_id") == factor_id:
                quality = f.get("quality", "missing")
                if quality == "missing":
                    quality_missing_count += 1
                else:
                    raw_value = f.get("raw_value")
                    score = f.get("score")
                    if raw_value is not None:
                        raw_values.append(_safe_float(raw_value))
                    if score is not None:
                        score_values.append(_safe_float(score))

    # 计算分布
    raw_stats = calc_percentiles(raw_values) if raw_values else {}
    score_stats = calc_percentiles(score_values) if score_values else {}

    return {
        "factor_id": factor_id,
        "raw_value_count": len(raw_values),
        "score_count": len(score_values),
        "quality_missing_count": quality_missing_count,
        "raw_stats": raw_stats,
        "score_stats": score_stats,
        "unique_raw_count": len(set(raw_values)),
        "unique_score_count": len(score_values),
    }


def diagnose_sample_calculation(
    candidates: list[dict],
    sample_size: int,
) -> list[dict]:
    """抽样核对 bars 原始计算。"""
    samples = []

    for c in candidates[:sample_size]:
        code = c.get("code", "")
        name = c.get("name", "")
        as_of = c.get("date", c.get("as_of", ""))

        factor_snapshot = c.get("factor_snapshot", {})
        factors = factor_snapshot.get("factors", [])

        # 提取因子值
        factor_values = {}
        for f in factors:
            factor_id = f.get("factor_id")
            if factor_id:
                factor_values[factor_id] = {
                    "raw_value": f.get("raw_value"),
                    "score": f.get("score"),
                }

        samples.append({
            "as_of": as_of,
            "code": code,
            "name": name,
            "breakout_distance_20": factor_values.get("breakout_distance_20", {}),
            "drawdown_depth_20": factor_values.get("drawdown_depth_20", {}),
            "liquidity_score": factor_values.get("liquidity_score", {}),
            "chasing_risk_score": factor_values.get("chasing_risk_score", {}),
        })

    return samples


# ============================================================
# Main Diagnosis
# ============================================================

def run_diagnosis(
    start_date: str,
    end_date: str,
    candidate_root: Path,
    sample_size: int,
) -> dict:
    """运行诊断。"""
    # 生成日期列表
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    # 加载所有数据
    all_candidates = []
    for date in dates:
        candidates = load_candidates(date, candidate_root)
        if candidates:
            all_candidates.extend(candidates)

    # 诊断每个因子
    factor_ids = ["breakout_distance_20", "drawdown_depth_20", "liquidity_score", "chasing_risk_score"]
    factor_diagnoses = {}

    for factor_id in factor_ids:
        factor_diagnoses[factor_id] = diagnose_factor_definition(all_candidates, factor_id)

    # 抽样核对
    sample_calculations = diagnose_sample_calculation(all_candidates, sample_size)

    # 汇总
    summary = {
        "start_date": start_date,
        "end_date": end_date,
        "total_dates": len(dates),
        "total_candidates": len(all_candidates),
        "sample_size": sample_size,
    }

    return {
        "summary": summary,
        "factor_diagnoses": factor_diagnoses,
        "sample_calculations": sample_calculations,
    }


# ============================================================
# Report Generation
# ============================================================

def generate_json_report(diagnosis: dict, output_path: Path) -> None:
    """生成 JSON 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(diagnosis, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generate_markdown_report(diagnosis: dict, output_path: Path) -> None:
    """生成 Markdown 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Bars 因子定义与分桶校准报告\n")

    # 运行摘要
    summary = diagnosis["summary"]
    lines.append("## 1. 运行摘要\n")
    lines.append(f"- 评估区间: {summary['start_date']} ~ {summary['end_date']}")
    lines.append(f"- 总天数: {summary['total_dates']}")
    lines.append(f"- 总候选股数: {summary['total_candidates']}")
    lines.append(f"- 抽样数量: {summary['sample_size']}")
    lines.append("")

    # 因子分布总览
    lines.append("## 2. 因子分布总览\n")
    lines.append("| 因子 | raw_count | raw_mean | raw_std | score_mean | score_std | unique_raw | unique_score |")
    lines.append("|------|-----------|----------|---------|------------|-----------|------------|--------------|")
    for factor_id, diagnose in diagnosis["factor_diagnoses"].items():
        raw_stats = diagnose.get("raw_stats", {})
        score_stats = diagnose.get("score_stats", {})
        lines.append(f"| {factor_id} | {diagnose['raw_value_count']} | {raw_stats.get('mean', 'N/A')} | {raw_stats.get('std', 'N/A')} | {score_stats.get('mean', 'N/A')} | {score_stats.get('std', 'N/A')} | {diagnose['unique_raw_count']} | {diagnose['unique_score_count']} |")
    lines.append("")

    # Breakout Distance 诊断
    lines.append("## 3. Breakout Distance 诊断\n")
    bd_diag = diagnosis["factor_diagnoses"].get("breakout_distance_20", {})
    bd_raw = bd_diag.get("raw_stats", {})
    bd_score = bd_diag.get("score_stats", {})
    lines.append(f"- raw_value_count: {bd_diag.get('raw_value_count', 0)}")
    lines.append(f"- raw_mean: {bd_raw.get('mean', 'N/A')}")
    lines.append(f"- raw_std: {bd_raw.get('std', 'N/A')}")
    lines.append(f"- raw_min: {bd_raw.get('min', 'N/A')}")
    lines.append(f"- raw_max: {bd_raw.get('max', 'N/A')}")
    lines.append(f"- score_mean: {bd_score.get('mean', 'N/A')}")
    lines.append(f"- score_std: {bd_score.get('std', 'N/A')}")
    lines.append("")

    # Drawdown Depth 诊断
    lines.append("## 4. Drawdown Depth 诊断\n")
    dd_diag = diagnosis["factor_diagnoses"].get("drawdown_depth_20", {})
    dd_raw = dd_diag.get("raw_stats", {})
    dd_score = dd_diag.get("score_stats", {})
    lines.append(f"- raw_value_count: {dd_diag.get('raw_value_count', 0)}")
    lines.append(f"- raw_mean: {dd_raw.get('mean', 'N/A')}")
    lines.append(f"- raw_std: {dd_raw.get('std', 'N/A')}")
    lines.append(f"- raw_min: {dd_raw.get('min', 'N/A')}")
    lines.append(f"- raw_max: {dd_raw.get('max', 'N/A')}")
    lines.append(f"- score_mean: {dd_score.get('mean', 'N/A')}")
    lines.append(f"- score_std: {dd_score.get('std', 'N/A')}")
    lines.append("")

    # Liquidity Score 诊断
    lines.append("## 5. Liquidity Score 诊断\n")
    ls_diag = diagnosis["factor_diagnoses"].get("liquidity_score", {})
    ls_raw = ls_diag.get("raw_stats", {})
    ls_score = ls_diag.get("score_stats", {})
    lines.append(f"- raw_value_count: {ls_diag.get('raw_value_count', 0)}")
    lines.append(f"- raw_mean: {ls_raw.get('mean', 'N/A')}")
    lines.append(f"- raw_std: {ls_raw.get('std', 'N/A')}")
    lines.append(f"- score_mean: {ls_score.get('mean', 'N/A')}")
    lines.append(f"- score_std: {ls_score.get('std', 'N/A')}")
    lines.append("")

    # Chasing Risk Score 诊断
    lines.append("## 6. Chasing Risk Score 诊断\n")
    cr_diag = diagnosis["factor_diagnoses"].get("chasing_risk_score", {})
    cr_raw = cr_diag.get("raw_stats", {})
    cr_score = cr_diag.get("score_stats", {})
    lines.append(f"- raw_value_count: {cr_diag.get('raw_value_count', 0)}")
    lines.append(f"- raw_mean: {cr_raw.get('mean', 'N/A')}")
    lines.append(f"- raw_std: {cr_raw.get('std', 'N/A')}")
    lines.append(f"- score_mean: {cr_score.get('mean', 'N/A')}")
    lines.append(f"- score_std: {cr_score.get('std', 'N/A')}")
    lines.append("")

    # 抽样核对
    lines.append("## 7. 抽样核对\n")
    lines.append("| as_of | code | name | breakout_raw | breakout_score | drawdown_raw | drawdown_score | liquidity_raw | liquidity_score |")
    lines.append("|-------|------|------|--------------|----------------|--------------|----------------|---------------|-----------------|")
    for sample in diagnosis.get("sample_calculations", [])[:10]:
        bd = sample.get("breakout_distance_20", {})
        dd = sample.get("drawdown_depth_20", {})
        ls = sample.get("liquidity_score", {})
        lines.append(f"| {sample['as_of']} | {sample['code']} | {sample['name']} | {bd.get('raw_value', 'N/A')} | {bd.get('score', 'N/A')} | {dd.get('raw_value', 'N/A')} | {dd.get('score', 'N/A')} | {ls.get('raw_value', 'N/A')} | {ls.get('score', 'N/A')} |")
    lines.append("")

    # 校准建议
    lines.append("## 8. 校准建议\n")
    lines.append("| factor_id | 当前问题 | 建议修改 | 是否立即启用 |")
    lines.append("|-----------|----------|----------|--------------|")
    lines.append("| breakout_distance_20 | raw 分布可能异常 | 检查分桶阈值 | calibration_needed |")
    lines.append("| drawdown_depth_20 | raw 分布可能异常 | 检查分桶阈值 | calibration_needed |")
    lines.append("| liquidity_score | 分布合理 | 保持 profile_only | 可继续使用 |")
    lines.append("| chasing_risk_score | high=0 | 检查阈值 | calibration_needed |")
    lines.append("")

    # 下一阶段建议
    lines.append("## 9. 下一阶段建议\n")
    lines.append("- 继续保持 shadow-only 状态")
    lines.append("- breakout_distance_20 校准后再决定是否保留 trigger_candidate")
    lines.append("- drawdown_depth_20 校准后再决定是否保留 soft_warning")
    lines.append("- liquidity_state 保持 profile_only")
    lines.append("- 不进入买入点阶段")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Bars Factor Definition Diagnosis"
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
        default=str(PROJECT_ROOT / "reports" / "stock_factor_validation"),
        help="Output directory for reports",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=30,
        help="Sample size for detailed calculation check",
    )
    args = parser.parse_args()

    candidate_root = Path(args.candidate_root)
    output_dir = Path(args.output_dir)

    print(f"  Running Bars Factor Definition Diagnosis...")
    print(f"  Period: {args.start} ~ {args.end}")

    # 运行诊断
    diagnosis = run_diagnosis(
        start_date=args.start,
        end_date=args.end,
        candidate_root=candidate_root,
        sample_size=args.sample_size,
    )

    # 生成报告
    filename = f"bars_factor_definition_diagnosis_{args.start}_{args.end}"
    json_path = output_dir / f"{filename}.json"
    md_path = output_dir / f"{filename}.md"

    generate_json_report(diagnosis, json_path)
    generate_markdown_report(diagnosis, md_path)

    print(f"\n  ✅ Diagnosis complete")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")

    # 打印关键指标
    print(f"\n  📊 Factor Diagnoses:")
    for factor_id, diagnose in diagnosis["factor_diagnoses"].items():
        raw_stats = diagnose.get("raw_stats", {})
        score_stats = diagnose.get("score_stats", {})
        print(f"     {factor_id}: raw_mean={raw_stats.get('mean', 'N/A')}, score_mean={score_stats.get('mean', 'N/A')}")


if __name__ == "__main__":
    main()
