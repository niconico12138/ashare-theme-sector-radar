#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Factor Composite Shadow Score 多日归因验证脚本

验证 factor_composite_shadow_score 是否相对 final_score、
regime_router_shadow_score_v5、agent_score 具有增量解释力。

本阶段只做分析报告和验证，不改变任何生产排序逻辑。

用法:
  python scripts/evaluate_factor_composite_shadow_score.py --start 2026-07-01 --end 2026-07-10
  python scripts/evaluate_factor_composite_shadow_score.py --start 2026-07-01 --end 2026-07-10 --top-n 5,10,20
"""

from __future__ import annotations

import argparse
import json
import math
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


# ============================================================
# Data Loading
# ============================================================

def load_top30_candidates(date: str, candidate_root: Path) -> dict | None:
    """加载某天的 top30_candidates.json。

    优先使用 factor_backfilled 文件，回退到原文件。
    """
    # 优先使用 backfilled 文件
    backfilled_path = candidate_root / date / "top30_candidates.factor_backfilled.json"
    if backfilled_path.exists():
        try:
            return json.loads(backfilled_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 回退到原文件
    path = candidate_root / date / "top30_candidates.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_forward_returns(date: str, forward_return_root: Path) -> dict[str, float] | None:
    """加载某天的 forward returns。

    支持两种格式:
    1. 新格式: forward_return_root / f"{date}.json" -> {"items": [{"code": "600001", "5d": 0.05, ...}]}
    2. 旧格式: forward_return_root / date / "forward_returns.json" -> {"returns": {"600001": 0.05, ...}}

    Returns:
        dict mapping stock code -> forward return (e.g., 5-day return)
        如果文件不存在，返回 None
    """
    # 尝试新格式
    new_path = forward_return_root / f"{date}.json"
    if new_path.exists():
        try:
            data = json.loads(new_path.read_text(encoding="utf-8"))
            items = data.get("items", [])
            # 转换为 {code: return} 格式，使用 5d return
            result = {}
            for item in items:
                code = item.get("code", "")
                ret = item.get("5d") or item.get("5d")
                if code and ret is not None:
                    result[code] = ret
            if result:
                return result
        except Exception:
            pass

    # 尝试旧格式
    old_path = forward_return_root / date / "forward_returns.json"
    if old_path.exists():
        try:
            data = json.loads(old_path.read_text(encoding="utf-8"))
            return data.get("returns", {})
        except Exception:
            return None

    return None


# ============================================================
# Statistical Helpers (no pandas/numpy)
# ============================================================

def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全转换为 float。"""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calc_mean(values: list[float]) -> float:
    """计算均值。"""
    if not values:
        return 0.0
    return sum(values) / len(values)


def calc_median(values: list[float]) -> float:
    """计算中位数。"""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n % 2 == 1:
        return sorted_vals[n // 2]
    else:
        return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2


def calc_std(values: list[float]) -> float:
    """计算标准差。"""
    if len(values) < 2:
        return 0.0
    mean = calc_mean(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def calc_rank_ic(scores: list[float], returns: list[float]) -> float | None:
    """计算 Rank IC (Spearman correlation)。

    如果样本不足（<5），返回 None
    """
    n = len(scores)
    if n < 5 or n != len(returns):
        return None

    # 计算排名
    def rank(values: list[float]) -> list[float]:
        indexed = sorted(enumerate(values), key=lambda x: x[1])
        ranks = [0.0] * len(values)
        for rank_val, (orig_idx, _) in enumerate(indexed, 1):
            ranks[orig_idx] = float(rank_val)
        return ranks

    rank_scores = rank(scores)
    rank_returns = rank(returns)

    # 计算 Pearson correlation on ranks (使用 population std)
    mean_s = calc_mean(rank_scores)
    mean_r = calc_mean(rank_returns)

    cov = sum((s - mean_s) * (r - mean_r) for s, r in zip(rank_scores, rank_returns)) / n
    # 使用 population std (除以 n)
    std_s = math.sqrt(sum((s - mean_s) ** 2 for s in rank_scores) / n)
    std_r = math.sqrt(sum((r - mean_r) ** 2 for r in rank_returns) / n)

    if std_s == 0 or std_r == 0:
        return 0.0

    return cov / (std_s * std_r)


def calc_quintile_returns(
    scores: list[float],
    returns: list[float],
    n_quintiles: int = 5,
) -> list[dict] | None:
    """计算分位数组合表现。

    Returns:
        list of dicts with quintile info, or None if insufficient
    """
    n = len(scores)
    if n < n_quintiles * 2 or n != len(returns):
        return None

    # 创建 (score, return) 对并排序
    pairs = sorted(zip(scores, returns), key=lambda x: x[0])
    chunk_size = n // n_quintiles

    quintiles = []
    for i in range(n_quintiles):
        start = i * chunk_size
        end = start + chunk_size if i < n_quintiles - 1 else n
        chunk_returns = [r for _, r in pairs[start:end]]
        quintiles.append({
            "quintile": i + 1,
            "count": len(chunk_returns),
            "mean_return": round(calc_mean(chunk_returns), 6),
            "median_return": round(calc_median(chunk_returns), 6),
        })

    return quintiles


def calc_correlation(x: list[float], y: list[float]) -> float | None:
    """计算 Pearson 相关系数。"""
    n = len(x)
    if n < 5 or n != len(y):
        return None

    mean_x = calc_mean(x)
    mean_y = calc_mean(y)

    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / n
    # 使用 population std (除以 n)
    std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / n)
    std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / n)

    if std_x == 0 or std_y == 0:
        return 0.0

    return cov / (std_x * std_y)


# ============================================================
# Evaluation
# ============================================================

SCORE_FIELDS = [
    "final_score",
    "regime_router_shadow_score_v5",
    "factor_composite_shadow_score",
    "factor_composite_shadow_score_v2",
    "agent_score",
    "trend_agent_score",
    "short_agent_score",
]


def evaluate_single_day(
    date: str,
    candidates: list[dict],
    forward_returns: dict[str, float] | None,
) -> dict:
    """评估单天的数据。"""
    result = {
        "date": date,
        "candidate_count": len(candidates),
        "has_forward_returns": forward_returns is not None,
        "forward_return_count": len(forward_returns) if forward_returns else 0,
        "fields": {},
    }

    for field in SCORE_FIELDS:
        field_result = {
            "coverage": 0,
            "missing": 0,
            "values": [],
            "top_n_returns": {},
            "rank_ic": None,
            "quintiles": None,
        }

        # 提取分数和对应的 forward return
        scores = []
        returns = []
        for c in candidates:
            code = c.get("code", "")
            score = c.get(field)
            if score is not None:
                field_result["coverage"] += 1
                score_float = _safe_float(score)
                if score_float > 0:  # 有效分数
                    scores.append(score_float)
                    field_result["values"].append(score_float)
                    # 如果有 forward return，匹配
                    if forward_returns and code in forward_returns:
                        returns.append(forward_returns[code])
            else:
                field_result["missing"] += 1

        field_result["coverage"] = round(
            field_result["coverage"] / len(candidates) * 100, 2
        ) if candidates else 0

        # 计算统计
        if field_result["values"]:
            field_result["min"] = round(min(field_result["values"]), 2)
            field_result["max"] = round(max(field_result["values"]), 2)
            field_result["mean"] = round(calc_mean(field_result["values"]), 2)
            field_result["median"] = round(calc_median(field_result["values"]), 2)
            field_result["std"] = round(calc_std(field_result["values"]), 2)

        # 计算 TopN 后续收益
        if scores and returns:
            # 按分数排序
            paired = sorted(zip(scores, returns), key=lambda x: x[0], reverse=True)
            for top_n in [5, 10, 20]:
                if len(paired) >= top_n:
                    top_returns = [r for _, r in paired[:top_n]]
                    field_result["top_n_returns"][f"top_{top_n}"] = round(
                        calc_mean(top_returns), 6
                    )

        # 计算 Rank IC
        if scores and returns:
            field_result["rank_ic"] = calc_rank_ic(scores, returns)

        # 计算分位数
        if scores and returns:
            field_result["quintiles"] = calc_quintile_returns(scores, returns)

        result["fields"][field] = field_result

    return result


def evaluate_multi_day(
    start_date: str,
    end_date: str,
    candidate_root: Path,
    forward_return_root: Path,
) -> dict:
    """多日评估。"""
    # 生成日期列表
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    daily_results = []
    missing_candidate_files = []
    no_forward_return_dates = []

    for date in dates:
        candidates_data = load_top30_candidates(date, candidate_root)
        if candidates_data is None:
            missing_candidate_files.append(date)
            continue

        candidates = candidates_data.get("candidates", [])
        forward_returns = load_forward_returns(date, forward_return_root)

        if forward_returns is None:
            no_forward_return_dates.append(date)

        daily_result = evaluate_single_day(date, candidates, forward_returns)
        daily_results.append(daily_result)

    # 汇总统计
    summary = {
        "start_date": start_date,
        "end_date": end_date,
        "total_dates": len(dates),
        "evaluated_dates": len(daily_results),
        "missing_candidate_files": missing_candidate_files,
        "no_forward_return_dates": no_forward_return_dates,
    }

    # 跨日汇总各字段
    field_summary = {}
    for field in SCORE_FIELDS:
        all_values = []
        all_rank_ics = []
        coverage_sum = 0

        for dr in daily_results:
            fr = dr["fields"].get(field, {})
            all_values.extend(fr.get("values", []))
            if fr.get("rank_ic") is not None:
                all_rank_ics.append(fr["rank_ic"])
            coverage_sum += fr.get("coverage", 0)

        field_summary[field] = {
            "total_samples": len(all_values),
            "avg_coverage": round(coverage_sum / len(daily_results), 2) if daily_results else 0,
            "overall_mean": round(calc_mean(all_values), 2) if all_values else None,
            "overall_std": round(calc_std(all_values), 2) if all_values else None,
            "avg_rank_ic": round(calc_mean(all_rank_ics), 4) if all_rank_ics else None,
            "rank_ic_count": len(all_rank_ics),
        }

    # 计算各字段间相关性（使用日均值）
    correlation_results = {}
    for field_a in SCORE_FIELDS:
        for field_b in SCORE_FIELDS:
            if field_a >= field_b:
                continue
            daily_means_a = []
            daily_means_b = []
            for dr in daily_results:
                values_a = dr["fields"].get(field_a, {}).get("values", [])
                values_b = dr["fields"].get(field_b, {}).get("values", [])
                if values_a and values_b:
                    daily_means_a.append(calc_mean(values_a))
                    daily_means_b.append(calc_mean(values_b))

            corr = calc_correlation(daily_means_a, daily_means_b)
            correlation_results[f"{field_a}_vs_{field_b}"] = round(corr, 4) if corr is not None else None

    return {
        "summary": summary,
        "field_summary": field_summary,
        "correlation_results": correlation_results,
        "daily_results": daily_results,
    }


# ============================================================
# Report Generation
# ============================================================

def generate_json_report(evaluation: dict, output_path: Path) -> None:
    """生成 JSON 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(evaluation, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generate_markdown_report(evaluation: dict, output_path: Path) -> None:
    """生成 Markdown 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Factor Composite Shadow Score 评估报告\n")

    # 运行摘要
    summary = evaluation["summary"]
    lines.append("## 运行摘要\n")
    lines.append(f"- 评估区间: {summary['start_date']} ~ {summary['end_date']}")
    lines.append(f"- 总天数: {summary['total_dates']}")
    lines.append(f"- 已评估天数: {summary['evaluated_dates']}")
    lines.append(f"- 缺失 candidate 文件: {len(summary['missing_candidate_files'])} 天")
    lines.append(f"- 无 forward return: {len(summary['no_forward_return_dates'])} 天")
    lines.append("")

    # 数据覆盖率
    lines.append("## 数据覆盖率\n")
    lines.append("| 字段 | 平均覆盖率 | 总样本数 | 平均 Rank IC |")
    lines.append("|------|-----------|---------|-------------|")
    for field, fs in evaluation["field_summary"].items():
        coverage = fs.get("avg_coverage", 0)
        samples = fs.get("total_samples", 0)
        ic = fs.get("avg_rank_ic")
        ic_str = f"{ic:.4f}" if ic is not None else "N/A"
        lines.append(f"| {field} | {coverage:.1f}% | {samples} | {ic_str} |")
    lines.append("")

    # 各评分字段分布
    lines.append("## 各评分字段分布\n")
    for field, fs in evaluation["field_summary"].items():
        lines.append(f"### {field}\n")
        if fs.get("overall_mean") is not None:
            lines.append(f"- 均值: {fs['overall_mean']:.2f}")
            lines.append(f"- 标准差: {fs['overall_std']:.2f}")
        else:
            lines.append("- 无有效数据")
        lines.append("")

    # Rank IC 对比
    lines.append("## Rank IC 对比\n")
    lines.append("Rank IC 衡量分数与后续收益的单调相关性，绝对值越大越有预测力。\n")
    for field, fs in evaluation["field_summary"].items():
        ic = fs.get("avg_rank_ic")
        count = fs.get("rank_ic_count", 0)
        if ic is not None:
            strength = "强" if abs(ic) > 0.1 else "中等" if abs(ic) > 0.05 else "弱"
            lines.append(f"- {field}: {ic:.4f} ({strength}, {count} 天)")
        else:
            lines.append(f"- {field}: N/A (样本不足)")
    lines.append("")

    # 与既有评分相关性
    lines.append("## 与既有评分相关性\n")
    lines.append("各字段日均值的 Pearson 相关系数:\n")
    for pair, corr in evaluation.get("correlation_results", {}).items():
        if corr is not None:
            lines.append(f"- {pair}: {corr:.4f}")
        else:
            lines.append(f"- {pair}: N/A")
    lines.append("")

    # 结论
    lines.append("## 结论\n")

    # 分析 factor_composite_shadow_score
    fc_stats = evaluation["field_summary"].get("factor_composite_shadow_score", {})
    fc_ic = fc_stats.get("avg_rank_ic")
    fs_ic = evaluation["field_summary"].get("final_score", {}).get("avg_rank_ic")
    agent_ic = evaluation["field_summary"].get("agent_score", {}).get("avg_rank_ic")

    lines.append("### a. 是否建议继续保留 factor_composite_shadow_score\n")
    if fc_ic is not None and abs(fc_ic) > 0.03:
        lines.append("- **建议保留**: factor_composite_shadow_score 显示出一定的预测能力")
    elif fc_ic is not None:
        lines.append("- **可考虑保留**: factor_composite_shadow_score 预测能力较弱，但可作为辅助参考")
    else:
        lines.append("- **数据不足**: 无法评估预测能力，建议积累更多数据后再评估")
    lines.append("")

    lines.append("### b. 是否建议进入 display_score\n")
    if fc_ic is not None and abs(fc_ic) > 0.08:
        lines.append("- **建议考虑**: factor_composite_shadow_score 表现出较好的预测能力")
    else:
        lines.append("- **暂不建议**: 建议继续作为 shadow-only 验证")
    lines.append("")

    lines.append("### c. 是否仍仅作为解释字段\n")
    if fc_ic is not None and abs(fc_ic) > 0.08:
        lines.append("- 可考虑提升为参考字段")
    else:
        lines.append("- **是**: 建议继续仅作为解释字段")
    lines.append("")

    lines.append("### d. 哪些 bucket 可能贡献最大/最弱\n")
    lines.append("- 需要更细粒度的 bucket 级别评估（后续阶段）")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate Factor Composite Shadow Score"
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
        "--output-dir",
        default=str(PROJECT_ROOT / "reports" / "factor_composite_shadow_score"),
        help="Output directory for reports",
    )
    parser.add_argument(
        "--top-n",
        default="5,10,20",
        help="Comma-separated list of top-N values",
    )
    args = parser.parse_args()

    candidate_root = Path(args.candidate_root)
    forward_return_root = Path(args.forward_return_root)
    output_dir = Path(args.output_dir)

    print(f"  Evaluating Factor Composite Shadow Score...")
    print(f"  Period: {args.start} ~ {args.end}")
    print(f"  Candidate root: {candidate_root}")
    print(f"  Forward return root: {forward_return_root}")

    # 运行评估
    evaluation = evaluate_multi_day(
        start_date=args.start,
        end_date=args.end,
        candidate_root=candidate_root,
        forward_return_root=forward_return_root,
    )

    # 生成报告
    filename = f"evaluation_{args.start}_{args.end}"
    json_path = output_dir / f"{filename}.json"
    md_path = output_dir / f"{filename}.md"

    generate_json_report(evaluation, json_path)
    generate_markdown_report(evaluation, md_path)

    print(f"  ✅ Evaluation complete")
    print(f"  📊 Evaluated dates: {evaluation['summary']['evaluated_dates']}/{evaluation['summary']['total_dates']}")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")

    # 打印关键指标
    for field, fs in evaluation["field_summary"].items():
        ic = fs.get("avg_rank_ic")
        if ic is not None:
            print(f"  {field}: Rank IC = {ic:.4f}")


if __name__ == "__main__":
    main()
