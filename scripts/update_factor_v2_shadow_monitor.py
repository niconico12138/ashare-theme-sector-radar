#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2 Shadow Monitor 固化脚本

将 factor_composite_shadow_score_v2 固化为独立 shadow 监控字段，
用于日报展示、分歧样本识别和持续表现追踪。

用法:
  python scripts/update_factor_v2_shadow_monitor.py --start 2026-04-01 --end 2026-07-10 --lookback-days 60
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
# Percentile Calculation
# ============================================================

def calc_percentile(value: float, values: list[float]) -> float:
    """计算百分位数 (0-100)。"""
    if not values:
        return 50.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    count_below = sum(1 for v in sorted_vals if v < value)
    return count_below / n * 100


# ============================================================
# Monitor Analysis
# ============================================================

def analyze_latest_snapshot(
    candidates: list[dict],
    date: str,
) -> dict:
    """分析最新日期快照。"""
    v2_scores = []
    final_scores = []

    for c in candidates:
        v2 = c.get("factor_composite_shadow_score_v2")
        final = c.get("final_score")
        if v2 is not None:
            v2_scores.append(_safe_float(v2))
        if final is not None:
            final_scores.append(_safe_float(final))

    # 计算相关性
    paired_v2 = []
    paired_final = []
    for c in candidates:
        v2 = c.get("factor_composite_shadow_score_v2")
        final = c.get("final_score")
        if v2 is not None and final is not None:
            paired_v2.append(_safe_float(v2))
            paired_final.append(_safe_float(final))

    correlation = calc_correlation(paired_v2, paired_final) if len(paired_v2) >= 3 else None

    # Top/Low v2 candidates
    candidates_with_v2 = [(c, _safe_float(c.get("factor_composite_shadow_score_v2")))
                          for c in candidates if c.get("factor_composite_shadow_score_v2") is not None]
    candidates_with_v2.sort(key=lambda x: x[1], reverse=True)

    top_v2 = [
        {
            "code": c.get("code", ""),
            "name": c.get("name", ""),
            "v2_score": round(v2, 2),
            "final_score": round(_safe_float(c.get("final_score")), 2),
        }
        for c, v2 in candidates_with_v2[:5]
    ]

    low_v2 = [
        {
            "code": c.get("code", ""),
            "name": c.get("name", ""),
            "v2_score": round(v2, 2),
            "final_score": round(_safe_float(c.get("final_score")), 2),
        }
        for c, v2 in candidates_with_v2[-5:]
    ]

    return {
        "date": date,
        "candidate_count": len(candidates),
        "v2_coverage": len(v2_scores) / len(candidates) * 100 if candidates else 0,
        "v2_mean": round(calc_mean(v2_scores), 2) if v2_scores else None,
        "v2_std": round(calc_std(v2_scores), 2) if v2_scores else None,
        "v2_min": round(min(v2_scores), 2) if v2_scores else None,
        "v2_max": round(max(v2_scores), 2) if v2_scores else None,
        "final_score_mean": round(calc_mean(final_scores), 2) if final_scores else None,
        "final_score_std": round(calc_std(final_scores), 2) if final_scores else None,
        "v2_final_correlation": round(correlation, 4) if correlation is not None else None,
        "top_v2_candidates": top_v2,
        "low_v2_candidates": low_v2,
    }


def identify_divergence_samples(
    candidates: list[dict],
) -> list[dict]:
    """识别分歧样本。"""
    divergence_samples = []

    # 提取所有 v2 和 final_score
    v2_scores = [_safe_float(c.get("factor_composite_shadow_score_v2")) for c in candidates
                 if c.get("factor_composite_shadow_score_v2") is not None]
    final_scores = [_safe_float(c.get("final_score")) for c in candidates
                    if c.get("final_score") is not None]

    if not v2_scores or not final_scores:
        return divergence_samples

    for c in candidates:
        code = c.get("code", "")
        name = c.get("name", "")
        v2 = c.get("factor_composite_shadow_score_v2")
        final = c.get("final_score")

        if v2 is None or final is None:
            continue

        v2_val = _safe_float(v2)
        final_val = _safe_float(final)

        v2_percentile = calc_percentile(v2_val, v2_scores)
        final_percentile = calc_percentile(final_val, final_scores)
        diff_percentile = v2_percentile - final_percentile

        # high_final_low_v2: final >= 80%, v2 <= 30%
        if final_percentile >= 80 and v2_percentile <= 30:
            divergence_samples.append({
                "code": code,
                "name": name,
                "final_score": round(final_val, 2),
                "factor_composite_shadow_score_v2": round(v2_val, 2),
                "final_percentile": round(final_percentile, 1),
                "v2_percentile": round(v2_percentile, 1),
                "diff_percentile": round(diff_percentile, 1),
                "reason": "high_final_low_v2",
                "boards": c.get("boards", []),
                "source_pool": c.get("source_pool", ""),
            })

        # low_final_high_v2: final <= 30%, v2 >= 80%
        if final_percentile <= 30 and v2_percentile >= 80:
            divergence_samples.append({
                "code": code,
                "name": name,
                "final_score": round(final_val, 2),
                "factor_composite_shadow_score_v2": round(v2_val, 2),
                "final_percentile": round(final_percentile, 1),
                "v2_percentile": round(v2_percentile, 1),
                "diff_percentile": round(diff_percentile, 1),
                "reason": "low_final_high_v2",
                "boards": c.get("boards", []),
                "source_pool": c.get("source_pool", ""),
            })

        # high_v2_risk_confirmed: v2 >= 80% and drawdown_risk_score is valid
        if v2_percentile >= 80:
            drawdown = c.get("drawdown_risk_score")
            if drawdown is not None:
                divergence_samples.append({
                    "code": code,
                    "name": name,
                    "final_score": round(final_val, 2),
                    "factor_composite_shadow_score_v2": round(v2_val, 2),
                    "final_percentile": round(final_percentile, 1),
                    "v2_percentile": round(v2_percentile, 1),
                    "diff_percentile": round(diff_percentile, 1),
                    "reason": "high_v2_risk_confirmed",
                    "boards": c.get("boards", []),
                    "source_pool": c.get("source_pool", ""),
                })

        # weak_v2_warning: final high but v2 low
        if final_percentile >= 70 and v2_percentile <= 40:
            divergence_samples.append({
                "code": code,
                "name": name,
                "final_score": round(final_val, 2),
                "factor_composite_shadow_score_v2": round(v2_val, 2),
                "final_percentile": round(final_percentile, 1),
                "v2_percentile": round(v2_percentile, 1),
                "diff_percentile": round(diff_percentile, 1),
                "reason": "weak_v2_warning",
                "boards": c.get("boards", []),
                "source_pool": c.get("source_pool", ""),
            })

    return divergence_samples


def analyze_historical_performance(
    candidates_by_date: dict[str, list[dict]],
    forward_returns_by_date: dict[str, dict[str, float]],
    dates: list[str],
) -> dict:
    """分析历史表现。"""
    daily_ics = []
    daily_top5 = []
    daily_bottom5 = []

    for date in dates:
        candidates = candidates_by_date.get(date, [])
        forward_returns = forward_returns_by_date.get(date, {})

        scores = []
        returns = []
        for c in candidates:
            code = c.get("code", "")
            v2 = c.get("factor_composite_shadow_score_v2")
            if v2 is not None and code in forward_returns:
                scores.append(_safe_float(v2))
                returns.append(forward_returns[code])

        if scores and returns:
            ic = calc_rank_ic(scores, returns)
            if ic is not None:
                daily_ics.append(ic)

            # Top/Bottom
            pairs = sorted(zip(scores, returns), key=lambda x: x[0], reverse=True)
            if len(pairs) >= 5:
                top5 = pairs[:5]
                bottom5 = pairs[-5:]
                daily_top5.append(calc_mean([r for _, r in top5]))
                daily_bottom5.append(calc_mean([r for _, r in bottom5]))

    if not daily_ics:
        return {
            "v2_ic_mean": None,
            "v2_ic_win_rate": None,
            "v2_top5_return": None,
            "v2_bottom5_return": None,
            "v2_spread": None,
            "sample_days": 0,
        }

    positive_days = sum(1 for ic in daily_ics if ic > 0)

    return {
        "v2_ic_mean": round(calc_mean(daily_ics), 4),
        "v2_ic_win_rate": round(positive_days / len(daily_ics) * 100, 2),
        "v2_top5_return": round(calc_mean(daily_top5), 4) if daily_top5 else None,
        "v2_bottom5_return": round(calc_mean(daily_bottom5), 4) if daily_bottom5 else None,
        "v2_spread": round(calc_mean(daily_top5) - calc_mean(daily_bottom5), 4) if daily_top5 and daily_bottom5 else None,
        "sample_days": len(daily_ics),
    }


def determine_monitor_status(
    historical_performance: dict,
) -> dict:
    """确定监控状态灯。"""
    ic_mean = historical_performance.get("v2_ic_mean")
    win_rate = historical_performance.get("v2_ic_win_rate")
    sample_days = historical_performance.get("sample_days", 0)

    if sample_days < 10:
        status = "yellow"
        reason = "样本不足 (少于 10 天)"
    elif ic_mean is not None and ic_mean > 0 and win_rate is not None and win_rate >= 55:
        status = "green"
        reason = f"v2 IC 为正 ({ic_mean:.4f}) 且 win_rate >= 55% ({win_rate:.1f}%)"
    elif ic_mean is not None and ic_mean < 0 and win_rate is not None and win_rate < 45:
        status = "red"
        reason = f"v2 IC 为负 ({ic_mean:.4f}) 且 win_rate < 45% ({win_rate:.1f}%)"
    else:
        status = "yellow"
        reason = f"v2 IC 接近 0 或样本不足"

    return {
        "status": status,
        "reason": reason,
    }


# ============================================================
# Main Monitor
# ============================================================

def run_monitor(
    start_date: str,
    end_date: str,
    candidate_root: Path,
    forward_return_root: Path,
    lookback_days: int = 60,
    latest_date: str | None = None,
) -> dict:
    """运行监控分析。"""
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
        forward_returns = load_forward_returns(date, forward_return_root)

        if candidates:
            candidates_by_date[date] = candidates
        if forward_returns:
            forward_returns_by_date[date] = forward_returns

    # 确定最新日期
    if latest_date and latest_date in candidates_by_date:
        latest = latest_date
    else:
        # 找到最后一个有 candidates 的日期
        latest = None
        for date in reversed(dates):
            if date in candidates_by_date:
                latest = date
                break

    if not latest:
        return {
            "status": "error",
            "message": "没有找到有 candidates 的日期",
        }

    # 最新日期快照
    latest_candidates = candidates_by_date[latest]
    latest_snapshot = analyze_latest_snapshot(latest_candidates, latest)

    # 分歧样本识别
    divergence_samples = identify_divergence_samples(latest_candidates)

    # 历史表现追踪
    lookback_start = datetime.strptime(latest, "%Y-%m-%d") - timedelta(days=lookback_days)
    lookback_dates = [d for d in dates if d >= lookback_start.strftime("%Y-%m-%d") and d <= latest]

    historical_performance = analyze_historical_performance(
        candidates_by_date, forward_returns_by_date, lookback_dates
    )

    # 状态灯
    monitor_status = determine_monitor_status(historical_performance)

    return {
        "latest_snapshot": latest_snapshot,
        "divergence_samples": divergence_samples,
        "historical_performance": historical_performance,
        "monitor_status": monitor_status,
        "lookback_days": lookback_days,
        "lookback_dates_count": len(lookback_dates),
    }


# ============================================================
# Report Generation
# ============================================================

def generate_json_report(monitor: dict, output_path: Path) -> None:
    """生成 JSON 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(monitor, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generate_jsonl_report(monitor: dict, output_path: Path) -> None:
    """生成 JSONL 报告（每日一行）。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 最新快照
    latest = monitor.get("latest_snapshot", {})
    line = {
        "type": "latest_snapshot",
        "date": latest.get("date"),
        "v2_mean": latest.get("v2_mean"),
        "v2_std": latest.get("v2_std"),
        "v2_final_correlation": latest.get("v2_final_correlation"),
        "candidate_count": latest.get("candidate_count"),
    }
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")

    # 分歧样本
    for sample in monitor.get("divergence_samples", []):
        line = {"type": "divergence_sample", **sample}
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    # 状态灯
    status = monitor.get("monitor_status", {})
    line = {"type": "monitor_status", **status}
    with open(output_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def generate_markdown_report(monitor: dict, output_path: Path) -> None:
    """生成 Markdown 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# V2 Shadow Monitor\n")

    # 最新快照
    latest = monitor.get("latest_snapshot", {})
    lines.append("## 最新快照\n")
    lines.append(f"- 日期: {latest.get('date')}")
    lines.append(f"- 候选股数: {latest.get('candidate_count')}")
    lines.append(f"- v2 覆盖率: {latest.get('v2_coverage', 0):.1f}%")
    lines.append(f"- v2 均值: {latest.get('v2_mean')}")
    lines.append(f"- v2 标准差: {latest.get('v2_std')}")
    lines.append(f"- v2 最小值: {latest.get('v2_min')}")
    lines.append(f"- v2 最大值: {latest.get('v2_max')}")
    lines.append(f"- final_score 均值: {latest.get('final_score_mean')}")
    lines.append(f"- final_score 标准差: {latest.get('final_score_std')}")
    lines.append(f"- v2 vs final_score 相关性: {latest.get('v2_final_correlation')}")
    lines.append("")

    # Top/Low v2 candidates
    lines.append("### Top V2 候选股\n")
    for c in latest.get("top_v2_candidates", []):
        lines.append(f"- {c['code']} {c['name']}: v2={c['v2_score']}, final={c['final_score']}")
    lines.append("")

    lines.append("### Low V2 候选股\n")
    for c in latest.get("low_v2_candidates", []):
        lines.append(f"- {c['code']} {c['name']}: v2={c['v2_score']}, final={c['final_score']}")
    lines.append("")

    # 分歧样本
    lines.append("## 分歧样本\n")
    divergence = monitor.get("divergence_samples", [])
    if divergence:
        lines.append("| 代码 | 名称 | final_score | v2_score | final% | v2% | diff% | 原因 |")
        lines.append("|------|------|-------------|----------|--------|-----|-------|------|")
        for s in divergence[:20]:  # 最多显示 20 条
            lines.append(f"| {s['code']} | {s['name']} | {s['final_score']} | {s['factor_composite_shadow_score_v2']} | {s['final_percentile']}% | {s['v2_percentile']}% | {s['diff_percentile']}% | {s['reason']} |")
    else:
        lines.append("- 无分歧样本")
    lines.append("")

    # 历史表现追踪
    lines.append("## 历史表现追踪\n")
    hist = monitor.get("historical_performance", {})
    lines.append(f"- 回溯天数: {monitor.get('lookback_days')}")
    lines.append(f"- 有效天数: {hist.get('sample_days')}")
    lines.append(f"- v2 Rank IC 均值: {hist.get('v2_ic_mean')}")
    lines.append(f"- v2 IC Win Rate: {hist.get('v2_ic_win_rate')}%")
    lines.append(f"- v2 Top5 平均收益: {hist.get('v2_top5_return')}%")
    lines.append(f"- v2 Bottom5 平均收益: {hist.get('v2_bottom5_return')}%")
    lines.append(f"- v2 Spread: {hist.get('v2_spread')}%")
    lines.append("")

    # 状态灯
    lines.append("## 状态灯\n")
    status = monitor.get("monitor_status", {})
    status_icon = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(status.get("status"), "⚪")
    lines.append(f"- 状态: {status_icon} {status.get('status')}")
    lines.append(f"- 原因: {status.get('reason')}")
    lines.append("")

    # 使用边界
    lines.append("## 使用边界\n")
    lines.append("- v2 不参与正式排序")
    lines.append("- v2 不构成买卖建议")
    lines.append("- v2 仅作为风险/防守维度参考")
    lines.append("- final_score 与 v2 分歧时，只标记'需要复核'，不自动剔除")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="V2 Shadow Monitor"
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
        "--lookback-days",
        type=int,
        default=60,
        help="Lookback days for historical performance",
    )
    parser.add_argument(
        "--latest-date",
        default=None,
        help="Latest date to analyze (default: last date with candidates)",
    )
    args = parser.parse_args()

    candidate_root = Path(args.candidate_root)
    forward_return_root = Path(args.forward_return_root)
    output_dir = Path(args.output_dir)

    print(f"  Running V2 Shadow Monitor...")
    print(f"  Period: {args.start} ~ {args.end}")
    print(f"  Lookback: {args.lookback_days} days")

    # 运行监控
    monitor = run_monitor(
        start_date=args.start,
        end_date=args.end,
        candidate_root=candidate_root,
        forward_return_root=forward_return_root,
        lookback_days=args.lookback_days,
        latest_date=args.latest_date,
    )

    if monitor.get("status") == "error":
        print(f"  ❌ Error: {monitor.get('message')}")
        return

    # 生成报告
    json_path = output_dir / "v2_shadow_monitor.json"
    md_path = output_dir / "v2_shadow_monitor.md"
    jsonl_path = output_dir / "v2_shadow_monitor.jsonl"

    generate_json_report(monitor, json_path)
    generate_jsonl_report(monitor, jsonl_path)
    generate_markdown_report(monitor, md_path)

    print(f"\n  ✅ Monitor complete")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")
    print(f"  📋 JSONL report: {jsonl_path}")

    # 打印状态
    status = monitor.get("monitor_status", {})
    status_icon = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(status.get("status"), "⚪")
    print(f"\n  {status_icon} Status: {status.get('status')}")
    print(f"     {status.get('reason')}")


if __name__ == "__main__":
    main()
