#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Factor Composite Shadow Score V2 稳定性验证脚本

验证 v2 的稳定性和增量价值。
本阶段只做分析脚本和报告，不修改 v1/v2 评分逻辑。

用法:
  python scripts/evaluate_factor_composite_v2_stability.py --start 2026-04-01 --end 2026-07-10 --horizon 1d
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
# Period Analysis
# ============================================================

def analyze_period(
    candidates_by_date: dict[str, list[dict]],
    forward_returns_by_date: dict[str, dict[str, float]],
    dates: list[str],
    score_fields: list[str],
    n_top_bottom: int = 5,
) -> dict:
    """分析指定日期范围内的指标。"""
    result = {
        "sample_count": 0,
        "effective_days": 0,
        "fields": {},
    }

    # 收集所有数据
    all_data: dict[str, dict[str, list[tuple[str, float, float]]]] = {
        field: {} for field in score_fields
    }

    for date in dates:
        candidates = candidates_by_date.get(date, [])
        forward_returns = forward_returns_by_date.get(date, {})

        if not candidates or not forward_returns:
            continue

        for c in candidates:
            code = c.get("code", "")
            if code not in forward_returns:
                continue

            result["sample_count"] += 1
            ret = forward_returns[code]

            for field in score_fields:
                score = c.get(field)
                if score is not None:
                    if date not in all_data[field]:
                        all_data[field][date] = []
                    all_data[field][date].append((code, _safe_float(score), ret))

    # 计算每个字段的指标
    for field in score_fields:
        field_data = all_data[field]

        if not field_data:
            result["fields"][field] = {
                "rank_ic": None,
                "ic_mean": None,
                "ic_median": None,
                "ic_std": None,
                "positive_ic_days": 0,
                "negative_ic_days": 0,
                "ic_win_rate": None,
                "top5_return": None,
                "bottom5_return": None,
                "spread": None,
                "sample_days": 0,
            }
            continue

        # 计算每天的 IC
        daily_ics = []
        all_scores = []
        all_returns = []

        for date, pairs in field_data.items():
            scores = [p[1] for p in pairs]
            returns = [p[2] for p in pairs]
            all_scores.extend(scores)
            all_returns.extend(returns)

            ic = calc_rank_ic(scores, returns)
            if ic is not None:
                daily_ics.append(ic)

        result["fields"][field] = {
            "rank_ic": round(calc_mean(daily_ics), 4) if daily_ics else None,
            "ic_mean": round(calc_mean(daily_ics), 4) if daily_ics else None,
            "ic_median": round(calc_median(daily_ics), 4) if daily_ics else None,
            "ic_std": round(calc_std(daily_ics), 4) if len(daily_ics) >= 2 else None,
            "positive_ic_days": sum(1 for ic in daily_ics if ic > 0),
            "negative_ic_days": sum(1 for ic in daily_ics if ic < 0),
            "ic_win_rate": round(sum(1 for ic in daily_ics if ic > 0) / len(daily_ics) * 100, 2) if daily_ics else None,
            "sample_days": len(daily_ics),
        }

        # 计算 Top/Bottom spread
        if len(all_scores) >= n_top_bottom * 2:
            pairs = list(zip(all_scores, all_returns))
            pairs_sorted = sorted(pairs, key=lambda x: x[0], reverse=True)
            top = pairs_sorted[:n_top_bottom]
            bottom = pairs_sorted[-n_top_bottom:]

            result["fields"][field]["top5_return"] = round(calc_mean([r for _, r in top]), 4)
            result["fields"][field]["bottom5_return"] = round(calc_mean([r for _, r in bottom]), 4)
            result["fields"][field]["spread"] = round(
                result["fields"][field]["top5_return"] - result["fields"][field]["bottom5_return"], 4
            )

    result["effective_days"] = len([d for d in dates if any(
        all_data[field].get(d) for field in score_fields
    )])

    return result


def analyze_monthly(
    candidates_by_date: dict[str, list[dict]],
    forward_returns_by_date: dict[str, dict[str, float]],
    dates: list[str],
    score_fields: list[str],
) -> dict:
    """月度稳定性分析。"""
    # 按月分组
    monthly_dates: dict[str, list[str]] = {}
    for date in dates:
        month = date[:7]  # YYYY-MM
        if month not in monthly_dates:
            monthly_dates[month] = []
        monthly_dates[month].append(date)

    monthly_results = {}
    for month, month_dates in sorted(monthly_dates.items()):
        if len(month_dates) < 5:  # 至少 5 天
            monthly_results[month] = {"status": "insufficient_sample", "dates": len(month_dates)}
            continue

        monthly_results[month] = analyze_period(
            candidates_by_date, forward_returns_by_date, month_dates, score_fields
        )

    return monthly_results


def analyze_weekly(
    candidates_by_date: dict[str, list[dict]],
    forward_returns_by_date: dict[str, dict[str, float]],
    dates: list[str],
    score_fields: list[str],
) -> dict:
    """周度稳定性分析。"""
    # 按 ISO 周分组
    weekly_dates: dict[str, list[str]] = {}
    for date in dates:
        d = datetime.strptime(date, "%Y-%m-%d")
        iso_year, iso_week, _ = d.isocalendar()
        week_key = f"{iso_year}-W{iso_week:02d}"
        if week_key not in weekly_dates:
            weekly_dates[week_key] = []
        weekly_dates[week_key].append(date)

    weekly_results = {}
    for week, week_dates in sorted(weekly_dates.items()):
        if len(week_dates) < 3:  # 至少 3 天
            weekly_results[week] = {"status": "insufficient_sample", "dates": len(week_dates)}
            continue

        weekly_results[week] = analyze_period(
            candidates_by_date, forward_returns_by_date, week_dates, score_fields
        )

    return weekly_results


def analyze_daily_contribution(
    candidates_by_date: dict[str, list[dict]],
    forward_returns_by_date: dict[str, dict[str, float]],
    dates: list[str],
    field: str,
) -> dict:
    """日度贡献集中度分析。"""
    daily_ics = []

    for date in dates:
        candidates = candidates_by_date.get(date, [])
        forward_returns = forward_returns_by_date.get(date, {})

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
            if ic is not None:
                daily_ics.append((date, ic))

    if not daily_ics:
        return {
            "top_positive_ic_days": [],
            "top_negative_ic_days": [],
            "concentration": None,
            "ic_without_top3": None,
            "ic_without_bottom3": None,
        }

    # 按 IC 排序
    sorted_by_ic = sorted(daily_ics, key=lambda x: x[1], reverse=True)

    # Top 3 正 IC
    top_positive = [(d, ic) for d, ic in sorted_by_ic if ic > 0][:3]
    # Top 3 负 IC
    top_negative = [(d, ic) for d, ic in sorted_by_ic if ic < 0][-3:]

    # 去掉最佳 3 天后的 IC
    if len(daily_ics) > 6:
        remaining = [(d, ic) for d, ic in daily_ics if (d, ic) not in top_positive]
        ic_without_top3 = calc_mean([ic for _, ic in remaining])
    else:
        ic_without_top3 = None

    # 去掉最差 3 天后的 IC
    if len(daily_ics) > 6:
        remaining = [(d, ic) for d, ic in daily_ics if (d, ic) not in top_negative]
        ic_without_bottom3 = calc_mean([ic for _, ic in remaining])
    else:
        ic_without_bottom3 = None

    # 贡献集中度
    all_ics = [ic for _, ic in daily_ics]
    total_ic = sum(all_ics)
    if total_ic != 0 and top_positive:
        top3_contribution = sum(ic for _, ic in top_positive) / total_ic * 100
    else:
        top3_contribution = None

    return {
        "top_positive_ic_days": [(d, round(ic, 4)) for d, ic in top_positive],
        "top_negative_ic_days": [(d, round(ic, 4)) for d, ic in top_negative],
        "concentration": round(top3_contribution, 2) if top3_contribution is not None else None,
        "ic_without_top3": round(ic_without_top3, 4) if ic_without_top3 is not None else None,
        "ic_without_bottom3": round(ic_without_bottom3, 4) if ic_without_bottom3 is not None else None,
    }


def analyze_quintile(
    candidates_by_date: dict[str, list[dict]],
    forward_returns_by_date: dict[str, dict[str, float]],
    dates: list[str],
    field: str,
    n_quintiles: int = 5,
) -> dict:
    """分位数分析。"""
    all_scores = []
    all_returns = []

    for date in dates:
        candidates = candidates_by_date.get(date, [])
        forward_returns = forward_returns_by_date.get(date, {})

        for c in candidates:
            code = c.get("code", "")
            score = c.get(field)
            if score is not None and code in forward_returns:
                all_scores.append(_safe_float(score))
                all_returns.append(forward_returns[code])

    if len(all_scores) < n_quintiles * 2:
        return {
            "quintiles": [],
            "is_monotonic": None,
            "spread": None,
        }

    # 按分数排序并分组
    pairs = sorted(zip(all_scores, all_returns), key=lambda x: x[0])
    chunk_size = len(pairs) // n_quintiles

    quintiles = []
    for i in range(n_quintiles):
        start = i * chunk_size
        end = start + chunk_size if i < n_quintiles - 1 else len(pairs)
        chunk_returns = [r for _, r in pairs[start:end]]
        quintiles.append({
            "quintile": i + 1,
            "count": len(chunk_returns),
            "mean_return": round(calc_mean(chunk_returns), 4),
        })

    # 检查单调性
    means = [q["mean_return"] for q in quintiles]
    is_monotonic = all(means[i] <= means[i + 1] for i in range(len(means) - 1)) or \
                   all(means[i] >= means[i + 1] for i in range(len(means) - 1))

    # Top-Bottom spread
    top_mean = quintiles[-1]["mean_return"]
    bottom_mean = quintiles[0]["mean_return"]
    spread = top_mean - bottom_mean

    return {
        "quintiles": quintiles,
        "is_monotonic": is_monotonic,
        "spread": round(spread, 4),
    }


# ============================================================
# Main Stability Analysis
# ============================================================

def run_stability_analysis(
    start_date: str,
    end_date: str,
    candidate_root: Path,
    forward_return_root: Path,
    horizon: str = "1d",
    min_days: int = 20,
) -> dict:
    """运行稳定性分析。"""
    # 生成日期列表
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    # 加载所有数据
    candidates_by_date: dict[str, list[dict]] = {}
    forward_returns_by_date: dict[str, dict[str, float]] = {}

    for date in dates:
        candidates = load_candidates(date, candidate_root)
        forward_returns = load_forward_returns(date, forward_return_root, horizon)

        if candidates:
            candidates_by_date[date] = candidates
        if forward_returns:
            forward_returns_by_date[date] = forward_returns

    # 评估字段
    score_fields = [
        "final_score",
        "factor_composite_shadow_score",
        "factor_composite_shadow_score_v2",
    ]

    # 计算 blended scores（临时计算，不写回 candidate）
    blended_fields = []
    for blend_name, final_weight, v2_weight in [
        ("blend_final_v2_90_10", 0.90, 0.10),
        ("blend_final_v2_80_20", 0.80, 0.20),
        ("blend_final_v2_70_30", 0.70, 0.30),
    ]:
        blended_fields.append(blend_name)
        for date in dates:
            candidates = candidates_by_date.get(date, [])
            for c in candidates:
                final_score = c.get("final_score")
                v2_score = c.get("factor_composite_shadow_score_v2")
                if final_score is not None and v2_score is not None:
                    c[blend_name] = _safe_float(final_score) * final_weight + _safe_float(v2_score) * v2_weight

    all_fields = score_fields + blended_fields

    # 整体分析
    overall = analyze_period(candidates_by_date, forward_returns_by_date, dates, all_fields)

    # 月度分析
    monthly = analyze_monthly(candidates_by_date, forward_returns_by_date, dates, all_fields)

    # 周度分析
    weekly = analyze_weekly(candidates_by_date, forward_returns_by_date, dates, all_fields)

    # 日度贡献集中度（只分析 v2）
    daily_contribution = analyze_daily_contribution(
        candidates_by_date, forward_returns_by_date, dates, "factor_composite_shadow_score_v2"
    )

    # 分位数分析
    quintile_analysis = {}
    for field in ["final_score", "factor_composite_shadow_score", "factor_composite_shadow_score_v2"]:
        quintile_analysis[field] = analyze_quintile(
            candidates_by_date, forward_returns_by_date, dates, field
        )

    # 计算相关性
    correlations = {}
    for field_a in all_fields:
        for field_b in all_fields:
            if field_a >= field_b:
                continue
            scores_a = []
            scores_b = []
            for date in dates:
                candidates = candidates_by_date.get(date, [])
                for c in candidates:
                    sa = c.get(field_a)
                    sb = c.get(field_b)
                    if sa is not None and sb is not None:
                        scores_a.append(_safe_float(sa))
                        scores_b.append(_safe_float(sb))
            corr = calc_correlation(scores_a, scores_b) if len(scores_a) >= 3 else None
            correlations[f"{field_a}_vs_{field_b}"] = round(corr, 4) if corr is not None else None

    # 增量价值分析
    v2_ic = overall["fields"].get("factor_composite_shadow_score_v2", {}).get("rank_ic")
    final_ic = overall["fields"].get("final_score", {}).get("rank_ic")

    best_ic_field = None
    best_ic_value = None
    for field in all_fields:
        ic = overall["fields"].get(field, {}).get("rank_ic")
        if ic is not None and (best_ic_value is None or ic > best_ic_value):
            best_ic_value = ic
            best_ic_field = field

    best_spread_field = None
    best_spread_value = None
    for field in all_fields:
        spread = overall["fields"].get(field, {}).get("spread")
        if spread is not None and (best_spread_value is None or spread > best_spread_value):
            best_spread_value = spread
            best_spread_field = field

    # 汇总
    summary = {
        "start_date": start_date,
        "end_date": end_date,
        "total_dates": len(dates),
        "effective_dates": len([d for d in dates if d in candidates_by_date and d in forward_returns_by_date]),
        "horizon": horizon,
    }

    return {
        "summary": summary,
        "overall": overall,
        "monthly": monthly,
        "weekly": weekly,
        "daily_contribution": daily_contribution,
        "quintile_analysis": quintile_analysis,
        "correlations": correlations,
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

def generate_json_report(stability: dict, output_path: Path) -> None:
    """生成 JSON 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(stability, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generate_markdown_report(stability: dict, output_path: Path) -> None:
    """生成 Markdown 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Factor Composite V2 Stability Report\n")

    # 运行摘要
    summary = stability["summary"]
    lines.append("## 运行摘要\n")
    lines.append(f"- 评估区间: {summary['start_date']} ~ {summary['end_date']}")
    lines.append(f"- 总天数: {summary['total_dates']}")
    lines.append(f"- 有效天数: {summary['effective_dates']}")
    lines.append(f"- Horizon: {summary['horizon']}")
    lines.append("")

    # 整体指标
    lines.append("## 整体指标\n")
    lines.append("| 字段 | Rank IC | IC Win Rate | Top5 Return | Bottom5 Return | Spread |")
    lines.append("|------|---------|-------------|-------------|----------------|--------|")
    for field, data in stability["overall"]["fields"].items():
        ic = data.get("rank_ic")
        win_rate = data.get("ic_win_rate")
        top5 = data.get("top5_return")
        bottom5 = data.get("bottom5_return")
        spread = data.get("spread")

        ic_str = f"{ic:.4f}" if ic is not None else "N/A"
        win_rate_str = f"{win_rate:.1f}%" if win_rate is not None else "N/A"
        top5_str = f"{top5:.4f}%" if top5 is not None else "N/A"
        bottom5_str = f"{bottom5:.4f}%" if bottom5 is not None else "N/A"
        spread_str = f"{spread:.4f}%" if spread is not None else "N/A"

        lines.append(f"| {field} | {ic_str} | {win_rate_str} | {top5_str} | {bottom5_str} | {spread_str} |")
    lines.append("")

    # 月度稳定性
    lines.append("## 月度稳定性\n")
    lines.append("| 月份 | 有效天数 | v2 IC | v2 IC Win Rate | v2 Spread |")
    lines.append("|------|----------|-------|----------------|-----------|")
    for month, data in stability["monthly"].items():
        if isinstance(data, dict) and "status" in data and data["status"] == "insufficient_sample":
            lines.append(f"| {month} | {data['dates']} | insufficient | - | - |")
            continue
        v2_data = data.get("fields", {}).get("factor_composite_shadow_score_v2", {})
        ic = v2_data.get("rank_ic")
        win_rate = v2_data.get("ic_win_rate")
        spread = v2_data.get("spread")
        effective = data.get("effective_days", 0)

        ic_str = f"{ic:.4f}" if ic is not None else "N/A"
        win_rate_str = f"{win_rate:.1f}%" if win_rate is not None else "N/A"
        spread_str = f"{spread:.4f}%" if spread is not None else "N/A"

        lines.append(f"| {month} | {effective} | {ic_str} | {win_rate_str} | {spread_str} |")
    lines.append("")

    # 日度贡献集中度
    lines.append("## 日度贡献集中度 (v2)\n")
    contrib = stability["daily_contribution"]
    if contrib["top_positive_ic_days"]:
        lines.append("### Top 正 IC 天\n")
        for date, ic in contrib["top_positive_ic_days"]:
            lines.append(f"- {date}: {ic:.4f}")
        lines.append("")

    if contrib["top_negative_ic_days"]:
        lines.append("### Top 负 IC 天\n")
        for date, ic in contrib["top_negative_ic_days"]:
            lines.append(f"- {date}: {ic:.4f}")
        lines.append("")

    lines.append(f"- 贡献集中度 (Top3 占比): {contrib['concentration']}%" if contrib['concentration'] is not None else "- 贡献集中度: N/A")
    lines.append(f"- 去掉最佳 3 天后 IC: {contrib['ic_without_top3']}" if contrib['ic_without_top3'] is not None else "- 去掉最佳 3 天后 IC: N/A")
    lines.append(f"- 去掉最差 3 天后 IC: {contrib['ic_without_bottom3']}" if contrib['ic_without_bottom3'] is not None else "- 去掉最差 3 天后 IC: N/A")
    lines.append("")

    # 分位数分析
    lines.append("## 分位数分析\n")
    for field, data in stability["quintile_analysis"].items():
        lines.append(f"### {field}\n")
        if data["quintiles"]:
            lines.append("| Q | 平均收益 |")
            lines.append("|---|----------|")
            for q in data["quintiles"]:
                lines.append(f"| Q{q['quintile']} | {q['mean_return']:.4f}% |")
            lines.append(f"- 单调性: {'是' if data['is_monotonic'] else '否'}")
            lines.append(f"- Top-Bottom Spread: {data['spread']:.4f}%")
        else:
            lines.append("- 样本不足")
        lines.append("")

    # 增量价值
    lines.append("## 增量价值\n")
    incr = stability["incremental_value"]
    lines.append(f"- 最佳 IC 字段: {incr['best_ic_field']} (IC = {incr['best_ic_value']})" if incr['best_ic_value'] is not None else "- 最佳 IC 字段: N/A")
    lines.append(f"- 最佳 Spread 字段: {incr['best_spread_field']} (Spread = {incr['best_spread_value']})" if incr['best_spread_value'] is not None else "- 最佳 Spread 字段: N/A")
    lines.append("")

    # 稳定性结论
    lines.append("## 稳定性结论\n")

    v2_ic = stability["overall"]["fields"].get("factor_composite_shadow_score_v2", {}).get("rank_ic")
    v1_ic = stability["overall"]["fields"].get("factor_composite_shadow_score", {}).get("rank_ic")
    final_ic = stability["overall"]["fields"].get("final_score", {}).get("rank_ic")

    lines.append("### v2 是否稳定\n")
    if v2_ic is not None and v2_ic > 0:
        lines.append("- **是**: v2 Rank IC 为正")
    else:
        lines.append("- **否**: v2 Rank IC 为负或无效")
    lines.append("")

    lines.append("### v2 是否只在少数日期有效\n")
    if contrib["concentration"] is not None and contrib["concentration"] > 50:
        lines.append(f"- **是**: Top3 天贡献 {contrib['concentration']}% 的 IC")
    else:
        lines.append("- **否**: IC 分布相对均匀")
    lines.append("")

    lines.append("### v2 是否比 v1 更好\n")
    if v2_ic is not None and v1_ic is not None and v2_ic > v1_ic:
        lines.append(f"- **是**: v2 IC ({v2_ic:.4f}) > v1 IC ({v1_ic:.4f})")
    else:
        lines.append("- **否**: v2 未超过 v1")
    lines.append("")

    lines.append("### v2 是否比 final_score 更好\n")
    if v2_ic is not None and final_ic is not None and v2_ic > final_ic:
        lines.append(f"- **是**: v2 IC ({v2_ic:.4f}) > final_score IC ({final_ic:.4f})")
    else:
        lines.append("- **否**: v2 未超过 final_score")
    lines.append("")

    lines.append("### 是否建议继续 shadow-only\n")
    lines.append("- **确认**: 应继续 shadow-only 状态")
    lines.append("")

    lines.append("### 是否建议做 display_score shadow test\n")
    if v2_ic is not None and v2_ic > 0.05:
        lines.append("- **可考虑**: v2 表现较好，可考虑进入下一阶段")
    else:
        lines.append("- **暂不建议**: v2 仍需更多验证")
    lines.append("")

    lines.append("### 是否建议做 v3\n")
    if v2_ic is not None and v2_ic > 0:
        lines.append("- **可暂缓**: v2 已有正向表现，先继续验证")
    else:
        lines.append("- **建议**: 考虑 v3 优化")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Factor Composite V2 Stability Analysis"
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
    parser.add_argument(
        "--min-days",
        type=int,
        default=20,
        help="Minimum days for period analysis",
    )
    args = parser.parse_args()

    candidate_root = Path(args.candidate_root)
    forward_return_root = Path(args.forward_return_root)
    output_dir = Path(args.output_dir)

    print(f"  Running Factor Composite V2 Stability Analysis...")
    print(f"  Period: {args.start} ~ {args.end}")
    print(f"  Horizon: {args.horizon}")

    # 运行稳定性分析
    stability = run_stability_analysis(
        start_date=args.start,
        end_date=args.end,
        candidate_root=candidate_root,
        forward_return_root=forward_return_root,
        horizon=args.horizon,
        min_days=args.min_days,
    )

    # 生成报告
    filename = f"v2_stability_{args.start}_{args.end}"
    json_path = output_dir / f"{filename}.json"
    md_path = output_dir / f"{filename}.md"

    generate_json_report(stability, json_path)
    generate_markdown_report(stability, md_path)

    print(f"\n  ✅ Stability analysis complete")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")

    # 打印关键指标
    v2_ic = stability["overall"]["fields"].get("factor_composite_shadow_score_v2", {}).get("rank_ic")
    v1_ic = stability["overall"]["fields"].get("factor_composite_shadow_score", {}).get("rank_ic")
    final_ic = stability["overall"]["fields"].get("final_score", {}).get("rank_ic")

    print(f"\n  📊 Rank IC:")
    print(f"     final_score: {final_ic}" if final_ic is not None else "     final_score: N/A")
    print(f"     v1: {v1_ic}" if v1_ic is not None else "     v1: N/A")
    print(f"     v2: {v2_ic}" if v2_ic is not None else "     v2: N/A")


if __name__ == "__main__":
    main()
