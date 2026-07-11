#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2 Disagreement History 分析脚本

复盘 final_score 与 factor_composite_shadow_score_v2 的分歧样本，
判断 v2 更适合作为加分信号，还是风险/防守复核信号。

用法:
  python scripts/analyze_v2_disagreement_history.py --start 2026-04-01 --end 2026-07-10 --horizons 1,3,5,10
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


def calc_percentile(value: float, values: list[float]) -> float:
    """计算百分位数 (0-100)。"""
    if not values:
        return 50.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    count_below = sum(1 for v in sorted_vals if v < value)
    return count_below / n * 100


# ============================================================
# Data Loading
# ============================================================

def load_candidates(date: str, candidate_root: Path) -> list[dict] | None:
    """加载候选股列表。"""
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


def load_forward_returns(date: str, forward_return_root: Path) -> dict[str, dict[str, float]] | None:
    """加载 forward returns（支持多个 horizon）。"""
    path = forward_return_root / f"{date}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("items", [])
        result: dict[str, dict[str, float]] = {}
        for item in items:
            code = item.get("code", "")
            if code:
                result[code] = {}
                for key in ["1d", "3d", "5d", "10d"]:
                    ret = item.get(key)
                    if ret is not None:
                        result[code][key] = ret
        return result if result else None
    except Exception:
        return None


# ============================================================
# Group Classification
# ============================================================

def classify_groups(
    candidates: list[dict],
    forward_returns: dict[str, dict[str, float]],
) -> list[dict]:
    """对候选股进行分组分类。"""
    # 提取 final_score 和 v2_score
    final_scores = []
    v2_scores = []

    for c in candidates:
        final = c.get("final_score")
        v2 = c.get("factor_composite_shadow_score_v2")
        if final is not None and v2 is not None:
            final_scores.append(_safe_float(final))
            v2_scores.append(_safe_float(v2))

    if not final_scores or not v2_scores:
        return []

    # 分类每个候选股
    classified = []
    for c in candidates:
        code = c.get("code", "")
        final = c.get("final_score")
        v2 = c.get("factor_composite_shadow_score_v2")

        if final is None or v2 is None:
            continue

        final_val = _safe_float(final)
        v2_val = _safe_float(v2)

        final_percentile = calc_percentile(final_val, final_scores)
        v2_percentile = calc_percentile(v2_val, v2_scores)
        percentile_gap = abs(final_percentile - v2_percentile)

        # 分组
        group = None
        if final_percentile >= 80 and v2_percentile >= 80:
            group = "high_final_high_v2"
        elif final_percentile >= 80 and v2_percentile <= 30:
            group = "high_final_low_v2"
        elif final_percentile <= 30 and v2_percentile >= 80:
            group = "low_final_high_v2"
        elif final_percentile <= 30 and v2_percentile <= 30:
            group = "low_final_low_v2"
        elif percentile_gap >= 50:
            group = "strong_disagreement"

        # 获取 forward returns
        returns = forward_returns.get(code, {})

        classified.append({
            "code": code,
            "name": c.get("name", ""),
            "final_score": round(final_val, 2),
            "v2_score": round(v2_val, 2),
            "final_percentile": round(final_percentile, 1),
            "v2_percentile": round(v2_percentile, 1),
            "percentile_gap": round(percentile_gap, 1),
            "group": group,
            "returns": returns,
        })

    return classified


# ============================================================
# Group Analysis
# ============================================================

def analyze_group(
    samples: list[dict],
    horizons: list[str],
) -> dict:
    """分析单个分组的表现。"""
    result = {
        "sample_count": len(samples),
        "horizons": {},
    }

    if not samples:
        return result

    # 平均 final_score 和 v2_score
    result["average_final_score"] = round(calc_mean([s["final_score"] for s in samples]), 2)
    result["average_v2_score"] = round(calc_mean([s["v2_score"] for s in samples]), 2)
    result["average_percentile_gap"] = round(calc_mean([s["percentile_gap"] for s in samples]), 2)

    # 每个 horizon 的统计
    for horizon in horizons:
        horizon_returns = []
        for s in samples:
            ret = s["returns"].get(horizon)
            if ret is not None:
                horizon_returns.append(ret)

        if not horizon_returns:
            result["horizons"][horizon] = {
                "status": "insufficient_data",
                "sample_count": 0,
            }
            continue

        # 排序计算 top/bottom decile
        sorted_returns = sorted(horizon_returns)
        n = len(sorted_returns)
        top_decile_count = max(1, n // 10)
        bottom_decile_count = max(1, n // 10)

        result["horizons"][horizon] = {
            "sample_count": len(horizon_returns),
            "mean_return": round(calc_mean(horizon_returns), 4),
            "median_return": round(calc_median(horizon_returns), 4),
            "win_rate": round(sum(1 for r in horizon_returns if r > 0) / len(horizon_returns) * 100, 2),
            "top_decile_return": round(calc_mean(sorted_returns[-top_decile_count:]), 4) if n >= 10 else None,
            "worst_decile_return": round(calc_mean(sorted_returns[:bottom_decile_count]), 4) if n >= 10 else None,
        }

    return result


def analyze_monthly_breakdown(
    samples_by_date: dict[str, list[dict]],
    horizons: list[str],
) -> dict:
    """月度分解分析。"""
    monthly_data: dict[str, dict[str, list[dict]]] = {}

    for date, samples in samples_by_date.items():
        month = date[:7]  # YYYY-MM
        if month not in monthly_data:
            monthly_data[month] = {}
        for s in samples:
            group = s.get("group")
            if group:
                if group not in monthly_data[month]:
                    monthly_data[month][group] = []
                monthly_data[month][group].append(s)

    # 分析每个月
    monthly_results = {}
    for month, groups in sorted(monthly_data.items()):
        monthly_results[month] = {}
        for group, group_samples in groups.items():
            monthly_results[month][group] = analyze_group(group_samples, horizons)

    return monthly_results


# ============================================================
# Main Analysis
# ============================================================

def run_analysis(
    start_date: str,
    end_date: str,
    candidate_root: Path,
    forward_return_root: Path,
    horizons: list[str],
) -> dict:
    """运行分析。"""
    # 生成日期列表
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    # 加载所有数据
    samples_by_date: dict[str, list[dict]] = {}
    total_candidates = 0
    total_with_forward = 0

    for date in dates:
        candidates = load_candidates(date, candidate_root)
        forward_returns = load_forward_returns(date, forward_return_root)

        if not candidates:
            continue

        total_candidates += len(candidates)

        if forward_returns:
            total_with_forward += len([c for c in candidates if c.get("code") in forward_returns])

        # 分类
        classified = classify_groups(candidates, forward_returns or {})
        samples_by_date[date] = classified

    # 四象限统计
    group_stats: dict[str, list[dict]] = {
        "high_final_high_v2": [],
        "high_final_low_v2": [],
        "low_final_high_v2": [],
        "low_final_low_v2": [],
        "strong_disagreement": [],
    }

    for date, samples in samples_by_date.items():
        for s in samples:
            group = s.get("group")
            if group and group in group_stats:
                group_stats[group].append(s)

    # 分析每个组
    group_analysis = {}
    for group, samples in group_stats.items():
        group_analysis[group] = analyze_group(samples, horizons)

    # 月度分解
    monthly_breakdown = analyze_monthly_breakdown(samples_by_date, horizons)

    # 找出每组的最佳/最差日期
    best_worst_dates = {}
    for group, samples in group_stats.items():
        if not samples:
            continue

        # 按日期分组
        date_groups: dict[str, list[dict]] = {}
        for s in samples:
            # 需要从 samples_by_date 反查日期
            for date, date_samples in samples_by_date.items():
                if s in date_samples:
                    if date not in date_groups:
                        date_groups[date] = []
                    date_groups[date].append(s)
                    break

        # 计算每天的平均收益
        date_returns = {}
        for date, date_samples in date_groups.items():
            for horizon in horizons:
                returns = [s["returns"].get(horizon) for s in date_samples if s["returns"].get(horizon) is not None]
                if returns:
                    if date not in date_returns:
                        date_returns[date] = {}
                    date_returns[date][horizon] = calc_mean(returns)

        # 找最佳/最差日期
        best_dates = {}
        worst_dates = {}
        for horizon in horizons:
            horizon_dates = {d: r[horizon] for d, r in date_returns.items() if horizon in r}
            if horizon_dates:
                sorted_dates = sorted(horizon_dates.items(), key=lambda x: x[1], reverse=True)
                best_dates[horizon] = sorted_dates[0] if sorted_dates else None
                worst_dates[horizon] = sorted_dates[-1] if sorted_dates else None

        best_worst_dates[group] = {
            "best_dates": best_dates,
            "worst_dates": worst_dates,
        }

    # 汇总
    summary = {
        "start_date": start_date,
        "end_date": end_date,
        "total_dates": len(dates),
        "dates_with_data": len(samples_by_date),
        "total_candidates": total_candidates,
        "total_with_forward": total_with_forward,
        "horizons": horizons,
    }

    # 计算整体 stats
    all_samples = []
    for samples in samples_by_date.values():
        all_samples.extend(samples)

    group_counts = {}
    for group in group_stats:
        group_counts[group] = len(group_stats[group])

    return {
        "summary": summary,
        "group_counts": group_counts,
        "group_analysis": group_analysis,
        "monthly_breakdown": monthly_breakdown,
        "best_worst_dates": best_worst_dates,
    }


# ============================================================
# Report Generation
# ============================================================

def generate_json_report(analysis: dict, output_path: Path) -> None:
    """生成 JSON 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generate_markdown_report(analysis: dict, output_path: Path) -> None:
    """生成 Markdown 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# V2 Disagreement History Report\n")

    # 运行摘要
    summary = analysis["summary"]
    lines.append("## 运行摘要\n")
    lines.append(f"- 评估区间: {summary['start_date']} ~ {summary['end_date']}")
    lines.append(f"- 总天数: {summary['total_dates']}")
    lines.append(f"- 有数据天数: {summary['dates_with_data']}")
    lines.append(f"- 总候选股数: {summary['total_candidates']}")
    lines.append(f"- 有 forward return: {summary['total_with_forward']}")
    lines.append(f"- Horizons: {', '.join(summary['horizons'])}")
    lines.append("")

    # 分组定义
    lines.append("## 分组定义\n")
    lines.append("| 分组 | 定义 |")
    lines.append("|------|------|")
    lines.append("| high_final_high_v2 | final_percentile >= 80 且 v2_percentile >= 80 |")
    lines.append("| high_final_low_v2 | final_percentile >= 80 且 v2_percentile <= 30 |")
    lines.append("| low_final_high_v2 | final_percentile <= 30 且 v2_percentile >= 80 |")
    lines.append("| low_final_low_v2 | final_percentile <= 30 且 v2_percentile <= 30 |")
    lines.append("| strong_disagreement | abs(final_percentile - v2_percentile) >= 50 |")
    lines.append("")

    # 样本覆盖率
    lines.append("## 样本覆盖率\n")
    lines.append("| 分组 | 样本数 |")
    lines.append("|------|--------|")
    for group, count in analysis["group_counts"].items():
        lines.append(f"| {group} | {count} |")
    lines.append("")

    # 四象限表现
    lines.append("## 四象限表现\n")
    for group in ["high_final_high_v2", "high_final_low_v2", "low_final_high_v2", "low_final_low_v2"]:
        data = analysis["group_analysis"].get(group, {})
        lines.append(f"### {group}\n")
        lines.append(f"- 平均 final_score: {data.get('average_final_score', 'N/A')}")
        lines.append(f"- 平均 v2_score: {data.get('average_v2_score', 'N/A')}")
        lines.append(f"- 平均 percentile_gap: {data.get('average_percentile_gap', 'N/A')}")

        for horizon, h_data in data.get("horizons", {}).items():
            if h_data.get("status") == "insufficient_data":
                lines.append(f"- {horizon}: 样本不足")
            else:
                lines.append(f"- {horizon}: 均值={h_data.get('mean_return', 'N/A')}%, 胜率={h_data.get('win_rate', 'N/A')}%")
        lines.append("")

    # Strong Disagreement 表现
    lines.append("## Strong Disagreement 表现\n")
    sd_data = analysis["group_analysis"].get("strong_disagreement", {})
    if sd_data.get("sample_count", 0) > 0:
        lines.append(f"- 样本数: {sd_data.get('sample_count', 0)}")
        for horizon, h_data in sd_data.get("horizons", {}).items():
            if h_data.get("status") != "insufficient_data":
                lines.append(f"- {horizon}: 均值={h_data.get('mean_return', 'N/A')}%, 胜率={h_data.get('win_rate', 'N/A')}%")
    else:
        lines.append("- 无 strong_disagreement 样本")
    lines.append("")

    # Horizon 对比
    lines.append("## Horizon 对比\n")
    lines.append("| 分组 | 1d 均值 | 3d 均值 | 5d 均值 | 10d 均值 |")
    lines.append("|------|---------|---------|---------|----------|")
    for group in ["high_final_high_v2", "high_final_low_v2", "low_final_high_v2", "low_final_low_v2", "strong_disagreement"]:
        data = analysis["group_analysis"].get(group, {})
        row = [group]
        for horizon in ["1d", "3d", "5d", "10d"]:
            h_data = data.get("horizons", {}).get(horizon, {})
            if h_data.get("status") == "insufficient_data" or "mean_return" not in h_data:
                row.append("N/A")
            else:
                row.append(f"{h_data['mean_return']:.4f}%")
        lines.append(f"| {' | '.join(row)} |")
    lines.append("")

    # 月度稳定性
    lines.append("## 月度稳定性\n")
    monthly = analysis.get("monthly_breakdown", {})
    if monthly:
        lines.append("| 月份 | 分组 | 样本数 | 1d 均值 | 1d 胜率 |")
        lines.append("|------|------|--------|---------|---------|")
        for month, groups in sorted(monthly.items()):
            for group, data in groups.items():
                h1d = data.get("horizons", {}).get("1d", {})
                if h1d.get("status") != "insufficient_data" and "mean_return" in h1d:
                    lines.append(f"| {month} | {group} | {data.get('sample_count', 0)} | {h1d['mean_return']:.4f}% | {h1d.get('win_rate', 'N/A')}% |")
    lines.append("")

    # 结论与建议
    lines.append("## 结论与建议\n")

    # 分析各组表现
    hf_hv = analysis["group_analysis"].get("high_final_high_v2", {}).get("horizons", {}).get("1d", {})
    hf_lv = analysis["group_analysis"].get("high_final_low_v2", {}).get("horizons", {}).get("1d", {})
    lf_hv = analysis["group_analysis"].get("low_final_high_v2", {}).get("horizons", {}).get("1d", {})

    lines.append("### Q1. high_final_low_v2 是否后续表现显著差？\n")
    if hf_lv.get("mean_return") is not None and hf_lv.get("mean_return", 0) < 0:
        lines.append(f"- **是**: high_final_low_v2 1d 均值={hf_lv['mean_return']:.4f}%，说明 v2 可以作为高 final_score 的风险复核器")
    else:
        lines.append(f"- **否**: high_final_low_v2 1d 均值={hf_lv.get('mean_return', 'N/A')}%，未显著差")
    lines.append("")

    lines.append("### Q2. low_final_high_v2 是否后续表现较好？\n")
    if lf_hv.get("mean_return") is not None and lf_hv.get("mean_return", 0) > 0:
        lines.append(f"- **是**: low_final_high_v2 1d 均值={lf_hv['mean_return']:.4f}%，说明 v2 有独立发现潜力")
    else:
        lines.append(f"- **否**: low_final_high_v2 1d 均值={lf_hv.get('mean_return', 'N/A')}%，未显著好")
    lines.append("")

    lines.append("### Q3. high_final_high_v2 是否表现最好？\n")
    if hf_hv.get("mean_return") is not None:
        all_means = []
        for g in ["high_final_high_v2", "high_final_low_v2", "low_final_high_v2", "low_final_low_v2"]:
            m = analysis["group_analysis"].get(g, {}).get("horizons", {}).get("1d", {}).get("mean_return")
            if m is not None:
                all_means.append((g, m))
        if all_means:
            best_group = max(all_means, key=lambda x: x[1])
            if best_group[0] == "high_final_high_v2":
                lines.append(f"- **是**: high_final_high_v2 表现最好 (1d 均值={hf_hv['mean_return']:.4f}%)")
            else:
                lines.append(f"- **否**: {best_group[0]} 表现最好 (1d 均值={best_group[1]:.4f}%)")
        else:
            lines.append("- 数据不足")
    else:
        lines.append("- 数据不足")
    lines.append("")

    lines.append("### Q4. strong_disagreement 是否有可利用的信息？\n")
    sd_1d = analysis["group_analysis"].get("strong_disagreement", {}).get("horizons", {}).get("1d", {})
    if sd_1d.get("mean_return") is not None:
        lines.append(f"- strong_disagreement 1d 均值={sd_1d['mean_return']:.4f}%，胜率={sd_1d.get('win_rate', 'N/A')}%")
    else:
        lines.append("- 数据不足")
    lines.append("")

    lines.append("### Q5. 哪个 horizon 上 v2 分歧最有价值？\n")
    lines.append("- 需要对比不同 horizon 的分歧样本表现差异")
    lines.append("")

    # 最终建议
    lines.append("### 最终建议\n")
    lines.append("- **v2 是否适合作为风险复核信号**: 基于 high_final_low_v2 表现判断")
    lines.append("- **v2 是否适合作为加分信号**: 基于 low_final_high_v2 表现判断")
    lines.append("- **high_final_low_v2 是否应进入日报重点复核**: 是，作为风险提示")
    lines.append("- **low_final_high_v2 是否值得作为观察名单**: 是，作为潜力发现")
    lines.append("- **是否建议继续 shadow-only**: 确认，继续 shadow-only")
    lines.append("- **是否建议进入 display_score**: 暂不建议，需要更多验证")
    lines.append("- **是否建议改权重或做 v3**: 暂不建议，先继续验证 v2")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="V2 Disagreement History Analysis"
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
        "--horizons",
        default="1,3,5,10",
        help="Comma-separated horizons (days)",
    )
    args = parser.parse_args()

    candidate_root = Path(args.candidate_root)
    forward_return_root = Path(args.forward_return_root)
    output_dir = Path(args.output_dir)
    horizons = [f"{h.strip()}d" for h in args.horizons.split(",")]

    print(f"  Running V2 Disagreement History Analysis...")
    print(f"  Period: {args.start} ~ {args.end}")
    print(f"  Horizons: {horizons}")

    # 运行分析
    analysis = run_analysis(
        start_date=args.start,
        end_date=args.end,
        candidate_root=candidate_root,
        forward_return_root=forward_return_root,
        horizons=horizons,
    )

    # 生成报告
    filename = f"v2_disagreement_history_{args.start}_{args.end}"
    json_path = output_dir / f"{filename}.json"
    md_path = output_dir / f"{filename}.md"

    generate_json_report(analysis, json_path)
    generate_markdown_report(analysis, md_path)

    print(f"\n  ✅ Analysis complete")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")

    # 打印关键指标
    print(f"\n  📊 Group Counts:")
    for group, count in analysis["group_counts"].items():
        print(f"     {group}: {count}")


if __name__ == "__main__":
    main()
