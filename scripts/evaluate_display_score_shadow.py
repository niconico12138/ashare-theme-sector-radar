#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Display Score Shadow 评估脚本

评估 display_score_shadow 的表现，判断是否优于 final_score 和 v2。

用法:
  python scripts/evaluate_display_score_shadow.py --start 2026-04-01 --end 2026-07-10 --horizon 1d
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


def calc_std(values: list[float]) -> float:
    """计算标准差。"""
    if len(values) < 2:
        return 0.0
    mean = calc_mean(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def calc_rank_ic(scores: list[float], returns: list[float]) -> float | None:
    """计算 Rank IC (Spearman correlation)。"""
    n = len(scores)
    if n < 3 or n != len(returns):
        return None

    def rank(values: list[float]) -> list[float]:
        indexed = sorted(enumerate(values), key=lambda x: x[1])
        ranks = [0.0] * len(values)
        for rank_val, (orig_idx, _) in enumerate(indexed, 1):
            ranks[orig_idx] = float(rank_val)
        return ranks

    rank_scores = rank(scores)
    rank_returns = rank(returns)

    mean_s = calc_mean(rank_scores)
    mean_r = calc_mean(rank_returns)

    cov = sum((s - mean_s) * (r - mean_r) for s, r in zip(rank_scores, rank_returns)) / n
    std_s = math.sqrt(sum((s - mean_s) ** 2 for s in rank_scores) / n)
    std_r = math.sqrt(sum((r - mean_r) ** 2 for r in rank_returns) / n)

    if std_s == 0 or std_r == 0:
        return 0.0

    return cov / (std_s * std_r)


def calc_correlation(x: list[float], y: list[float]) -> float | None:
    """计算 Pearson 相关系数。"""
    n = len(x)
    if n < 3 or n != len(y):
        return None

    mean_x = calc_mean(x)
    mean_y = calc_mean(y)

    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y)) / n
    std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / n)
    std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / n)

    if std_x == 0 or std_y == 0:
        return 0.0

    return cov / (std_x * std_y)


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


def load_forward_returns(date: str, forward_return_root: Path, horizon: str = "1d") -> dict[str, float] | None:
    """加载 forward returns。"""
    path = forward_return_root / f"{date}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("items", [])
        result = {}
        for item in items:
            code = item.get("code", "")
            ret = item.get(horizon)
            if code and ret is not None:
                result[code] = ret
        return result if result else None
    except Exception:
        return None


# ============================================================
# Evaluation
# ============================================================

SCORE_FIELDS = [
    "final_score",
    "factor_composite_shadow_score_v2",
    "display_score_shadow_90_10",
    "display_score_shadow_80_20",
    "display_score_shadow_70_30",
]


def evaluate_single_day(
    date: str,
    candidates: list[dict],
    forward_returns: dict[str, float],
) -> dict:
    """评估单天的数据。"""
    result = {
        "date": date,
        "candidate_count": len(candidates),
        "forward_return_count": len(forward_returns),
        "fields": {},
    }

    for field in SCORE_FIELDS:
        scores = []
        returns = []
        for c in candidates:
            code = c.get("code", "")
            score = c.get(field)
            if score is not None and code in forward_returns:
                scores.append(_safe_float(score))
                returns.append(forward_returns[code])

        if scores and returns:
            ic = calc_rank_ic(scores, returns)

            # Top N returns
            pairs = sorted(zip(scores, returns), key=lambda x: x[0], reverse=True)
            top5 = pairs[:5] if len(pairs) >= 5 else pairs
            top10 = pairs[:10] if len(pairs) >= 10 else pairs
            top20 = pairs[:20] if len(pairs) >= 20 else pairs

            # Bottom 5
            bottom5 = pairs[-5:] if len(pairs) >= 5 else []

            result["fields"][field] = {
                "rank_ic": ic,
                "sample_count": len(scores),
                "top5_return": round(calc_mean([r for _, r in top5]), 4) if top5 else None,
                "top10_return": round(calc_mean([r for _, r in top10]), 4) if top10 else None,
                "top20_return": round(calc_mean([r for _, r in top20]), 4) if top20 else None,
                "bottom5_return": round(calc_mean([r for _, r in bottom5]), 4) if bottom5 else None,
                "spread": round(
                    calc_mean([r for _, r in top5]) - calc_mean([r for _, r in bottom5]), 4
                ) if top5 and bottom5 else None,
            }

    return result


def evaluate_multi_day(
    start_date: str,
    end_date: str,
    candidate_root: Path,
    forward_return_root: Path,
    horizon: str = "1d",
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

    # 加载所有数据
    all_candidates = []
    all_forward_returns = {}
    daily_results = []
    dates_with_returns = []

    for date in dates:
        candidates = load_candidates(date, candidate_root)
        forward_returns = load_forward_returns(date, forward_return_root, horizon)

        if candidates and forward_returns:
            all_candidates.extend(candidates)
            all_forward_returns.update(forward_returns)
            dates_with_returns.append(date)

            daily_result = evaluate_single_day(date, candidates, forward_returns)
            daily_results.append(daily_result)

    # 跨日汇总各字段
    field_summary = {}
    for field in SCORE_FIELDS:
        all_values = []
        all_rank_ics = []
        all_top5 = []
        all_bottom5 = []
        coverage_sum = 0

        for dr in daily_results:
            fr = dr["fields"].get(field, {})
            if fr.get("rank_ic") is not None:
                all_rank_ics.append(fr["rank_ic"])
            if fr.get("top5_return") is not None:
                all_top5.append(fr["top5_return"])
            if fr.get("bottom5_return") is not None:
                all_bottom5.append(fr["bottom5_return"])

        field_summary[field] = {
            "avg_rank_ic": round(calc_mean(all_rank_ics), 4) if all_rank_ics else None,
            "ic_win_rate": round(sum(1 for ic in all_rank_ics if ic > 0) / len(all_rank_ics) * 100, 2) if all_rank_ics else None,
            "avg_top5_return": round(calc_mean(all_top5), 4) if all_top5 else None,
            "avg_bottom5_return": round(calc_mean(all_bottom5), 4) if all_bottom5 else None,
            "avg_spread": round(calc_mean(all_top5) - calc_mean(all_bottom5), 4) if all_top5 and all_bottom5 else None,
            "sample_days": len(all_rank_ics),
        }

    # 计算相关性
    correlations = {}
    for field_a in SCORE_FIELDS:
        for field_b in SCORE_FIELDS:
            if field_a >= field_b:
                continue
            scores_a = []
            scores_b = []
            for c in all_candidates:
                sa = c.get(field_a)
                sb = c.get(field_b)
                if sa is not None and sb is not None:
                    scores_a.append(_safe_float(sa))
                    scores_b.append(_safe_float(sb))
            corr = calc_correlation(scores_a, scores_b) if len(scores_a) >= 3 else None
            correlations[f"{field_a}_vs_{field_b}"] = round(corr, 4) if corr is not None else None

    # 月度稳定性
    monthly_dates: dict[str, list[str]] = {}
    for date in dates:
        month = date[:7]
        if month not in monthly_dates:
            monthly_dates[month] = []
        monthly_dates[month].append(date)

    monthly_stability = {}
    for month, month_dates in sorted(monthly_dates.items()):
        month_ics = {field: [] for field in SCORE_FIELDS}
        for date in month_dates:
            dr = next((d for d in daily_results if d["date"] == date), None)
            if dr:
                for field in SCORE_FIELDS:
                    ic = dr["fields"].get(field, {}).get("rank_ic")
                    if ic is not None:
                        month_ics[field].append(ic)

        monthly_stability[month] = {
            field: round(calc_mean(ics), 4) if ics else None
            for field, ics in month_ics.items()
        }

    # 汇总
    summary = {
        "start_date": start_date,
        "end_date": end_date,
        "total_dates": len(dates),
        "dates_with_returns": len(dates_with_returns),
        "total_candidates": len(all_candidates),
        "horizon": horizon,
    }

    # 找出最佳字段
    best_ic_field = None
    best_ic_value = None
    for field, data in field_summary.items():
        ic = data.get("avg_rank_ic")
        if ic is not None and (best_ic_value is None or ic > best_ic_value):
            best_ic_value = ic
            best_ic_field = field

    best_spread_field = None
    best_spread_value = None
    for field, data in field_summary.items():
        spread = data.get("avg_spread")
        if spread is not None and (best_spread_value is None or spread > best_spread_value):
            best_spread_value = spread
            best_spread_field = field

    return {
        "summary": summary,
        "field_summary": field_summary,
        "correlations": correlations,
        "monthly_stability": monthly_stability,
        "incremental_value": {
            "best_ic_field": best_ic_field,
            "best_ic_value": best_ic_value,
            "best_spread_field": best_spread_field,
            "best_spread_value": best_spread_value,
        },
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
    lines.append("# Display Score Shadow 评估报告\n")

    # 运行摘要
    summary = evaluation["summary"]
    lines.append("## 运行摘要\n")
    lines.append(f"- 评估区间: {summary['start_date']} ~ {summary['end_date']}")
    lines.append(f"- 总天数: {summary['total_dates']}")
    lines.append(f"- 有 forward return 的天数: {summary['dates_with_returns']}")
    lines.append(f"- 总候选股数: {summary['total_candidates']}")
    lines.append(f"- Horizon: {summary['horizon']}")
    lines.append("")

    # 整体指标
    lines.append("## 整体指标\n")
    lines.append("| 字段 | Avg Rank IC | IC Win Rate | Avg Top5 Return | Avg Bottom5 Return | Avg Spread |")
    lines.append("|------|-------------|-------------|-----------------|-------------------|------------|")
    for field, data in evaluation["field_summary"].items():
        ic = data.get("avg_rank_ic")
        win_rate = data.get("ic_win_rate")
        top5 = data.get("avg_top5_return")
        bottom5 = data.get("avg_bottom5_return")
        spread = data.get("avg_spread")

        ic_str = f"{ic:.4f}" if ic is not None else "N/A"
        win_rate_str = f"{win_rate:.1f}%" if win_rate is not None else "N/A"
        top5_str = f"{top5:.4f}%" if top5 is not None else "N/A"
        bottom5_str = f"{bottom5:.4f}%" if bottom5 is not None else "N/A"
        spread_str = f"{spread:.4f}%" if spread is not None else "N/A"

        lines.append(f"| {field} | {ic_str} | {win_rate_str} | {top5_str} | {bottom5_str} | {spread_str} |")
    lines.append("")

    # 月度稳定性
    lines.append("## 月度稳定性\n")
    lines.append("| 月份 | final_score IC | v2 IC | shadow_90_10 IC | shadow_80_20 IC | shadow_70_30 IC |")
    lines.append("|------|---------------|-------|-----------------|-----------------|-----------------|")
    for month, data in evaluation["monthly_stability"].items():
        final_ic = data.get("final_score")
        v2_ic = data.get("factor_composite_shadow_score_v2")
        s90 = data.get("display_score_shadow_90_10")
        s80 = data.get("display_score_shadow_80_20")
        s70 = data.get("display_score_shadow_70_30")

        final_str = f"{final_ic:.4f}" if final_ic is not None else "N/A"
        v2_str = f"{v2_ic:.4f}" if v2_ic is not None else "N/A"
        s90_str = f"{s90:.4f}" if s90 is not None else "N/A"
        s80_str = f"{s80:.4f}" if s80 is not None else "N/A"
        s70_str = f"{s70:.4f}" if s70 is not None else "N/A"

        lines.append(f"| {month} | {final_str} | {v2_str} | {s90_str} | {s80_str} | {s70_str} |")
    lines.append("")

    # 相关性
    lines.append("## 与 final_score 相关性\n")
    for field in SCORE_FIELDS:
        if field == "final_score":
            continue
        corr = evaluation["correlations"].get(f"final_score_vs_{field}")
        if corr is not None:
            lines.append(f"- {field}: {corr:.4f}")
        else:
            lines.append(f"- {field}: N/A")
    lines.append("")

    # 增量价值
    lines.append("## 增量价值\n")
    incr = evaluation["incremental_value"]
    lines.append(f"- 最佳 IC 字段: {incr['best_ic_field']} (IC = {incr['best_ic_value']})" if incr['best_ic_value'] is not None else "- 最佳 IC 字段: N/A")
    lines.append(f"- 最佳 Spread 字段: {incr['best_spread_field']} (Spread = {incr['best_spread_value']})" if incr['best_spread_value'] is not None else "- 最佳 Spread 字段: N/A")
    lines.append("")

    # 结论
    lines.append("## 结论\n")

    final_ic = evaluation["field_summary"].get("final_score", {}).get("avg_rank_ic")
    v2_ic = evaluation["field_summary"].get("factor_composite_shadow_score_v2", {}).get("avg_rank_ic")
    best_ic = incr.get("best_ic_value")

    lines.append("### 哪个 shadow display score 表现最好\n")
    if incr["best_ic_field"]:
        lines.append(f"- **{incr['best_ic_field']}** (IC = {incr['best_ic_value']})")
    else:
        lines.append("- 无法判断")
    lines.append("")

    lines.append("### 是否优于 final_score\n")
    if best_ic is not None and final_ic is not None and best_ic > final_ic:
        lines.append(f"- **是**: {incr['best_ic_field']} IC ({best_ic:.4f}) > final_score IC ({final_ic:.4f})")
    else:
        lines.append("- **否**: 未优于 final_score")
    lines.append("")

    lines.append("### 是否优于纯 v2\n")
    if best_ic is not None and v2_ic is not None and best_ic > v2_ic:
        lines.append(f"- **是**: {incr['best_ic_field']} IC ({best_ic:.4f}) > v2 IC ({v2_ic:.4f})")
    else:
        lines.append("- **否**: 未优于纯 v2")
    lines.append("")

    lines.append("### 是否建议继续 shadow\n")
    lines.append("- **确认**: 应继续 shadow 状态")
    lines.append("")

    lines.append("### 是否建议进入正式 display_score\n")
    if best_ic is not None and best_ic > 0.05:
        lines.append("- **可考虑**: 表现较好，可考虑进入下一阶段")
    else:
        lines.append("- **暂不建议**: 仍需更多验证")
    lines.append("")

    lines.append("### 若不建议，原因是什么\n")
    if best_ic is None or best_ic <= 0.05:
        lines.append("- IC 不够强，需要更多数据验证")
    else:
        lines.append("- 当前表现较好，可继续验证")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Display Score Shadow Evaluation"
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
        "--horizon",
        default="1d",
        help="Forward return horizon (1d, 3d, 5d, 10d)",
    )
    args = parser.parse_args()

    candidate_root = Path(args.candidate_root)
    forward_return_root = Path(args.forward_return_root)
    output_dir = Path(args.output_dir)

    print(f"  Evaluating Display Score Shadow...")
    print(f"  Period: {args.start} ~ {args.end}")
    print(f"  Horizon: {args.horizon}")

    # 运行评估
    evaluation = evaluate_multi_day(
        start_date=args.start,
        end_date=args.end,
        candidate_root=candidate_root,
        forward_return_root=forward_return_root,
        horizon=args.horizon,
    )

    # 生成报告
    filename = f"display_shadow_{args.start}_{args.end}"
    json_path = output_dir / f"{filename}.json"
    md_path = output_dir / f"{filename}.md"

    generate_json_report(evaluation, json_path)
    generate_markdown_report(evaluation, md_path)

    print(f"\n  ✅ Evaluation complete")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")

    # 打印关键指标
    print(f"\n  📊 Rank IC:")
    for field in SCORE_FIELDS:
        ic = evaluation["field_summary"].get(field, {}).get("avg_rank_ic")
        print(f"     {field}: {ic}" if ic is not None else f"     {field}: N/A")


if __name__ == "__main__":
    main()
