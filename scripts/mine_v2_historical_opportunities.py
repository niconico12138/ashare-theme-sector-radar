#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2 Historical Opportunity Mining 脚本

系统挖掘历史数据，验证 factor_composite_shadow_score_v2 是否能形成独立机会发现信号。

用法:
  python scripts/mine_v2_historical_opportunities.py --start 2026-04-01 --end 2026-07-10
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
# Pool Construction
# ============================================================

def construct_daily_pools(
    candidates: list[dict],
    forward_returns: dict[str, dict[str, float]],
) -> dict[str, list[dict]]:
    """构造每日候选池。"""
    pools = {
        "final_top_pool": [],
        "v2_top_pool": [],
        "low_final_high_v2_pool": [],
        "strong_disagreement_opportunity_pool": [],
    }

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
        return pools

    # A. final_top_pool: 按 final_score 排序 Top5/Top10
    candidates_with_final = [(c, _safe_float(c.get("final_score"))) for c in candidates if c.get("final_score") is not None]
    candidates_with_final.sort(key=lambda x: x[1], reverse=True)
    pools["final_top_pool"] = [c for c, _ in candidates_with_final[:10]]

    # B. v2_top_pool: 按 v2_score 排序 Top5/Top10
    candidates_with_v2 = [(c, _safe_float(c.get("factor_composite_shadow_score_v2"))) for c in candidates if c.get("factor_composite_shadow_score_v2") is not None]
    candidates_with_v2.sort(key=lambda x: x[1], reverse=True)
    pools["v2_top_pool"] = [c for c, _ in candidates_with_v2[:10]]

    # C. low_final_high_v2_pool
    for c in candidates:
        final = c.get("final_score")
        v2 = c.get("factor_composite_shadow_score_v2")
        if final is None or v2 is None:
            continue

        final_val = _safe_float(final)
        v2_val = _safe_float(v2)
        final_pct = calc_percentile(final_val, final_scores)
        v2_pct = calc_percentile(v2_val, v2_scores)

        if final_pct <= 30 and v2_pct >= 80:
            pools["low_final_high_v2_pool"].append(c)

    pools["low_final_high_v2_pool"] = pools["low_final_high_v2_pool"][:10]

    # D. strong_disagreement_opportunity_pool
    for c in candidates:
        final = c.get("final_score")
        v2 = c.get("factor_composite_shadow_score_v2")
        if final is None or v2 is None:
            continue

        final_val = _safe_float(final)
        v2_val = _safe_float(v2)
        final_pct = calc_percentile(final_val, final_scores)
        v2_pct = calc_percentile(v2_val, v2_scores)

        if v2_pct - final_pct >= 50:
            pools["strong_disagreement_opportunity_pool"].append(c)

    pools["strong_disagreement_opportunity_pool"] = pools["strong_disagreement_opportunity_pool"][:10]

    return pools


# ============================================================
# Pool Analysis
# ============================================================

def analyze_pool(
    pool_by_date: dict[str, list[dict]],
    forward_returns_by_date: dict[str, dict[str, float]],
    horizons: list[str],
) -> dict:
    """分析单个候选池的表现。"""
    all_returns: dict[str, list[float]] = {h: [] for h in horizons}
    daily_returns: dict[str, dict[str, float]] = {}

    for date, pool in pool_by_date.items():
        forward_returns = forward_returns_by_date.get(date, {})
        date_returns: dict[str, list[float]] = {h: [] for h in horizons}

        for c in pool:
            code = c.get("code", "")
            if code not in forward_returns:
                continue

            for horizon in horizons:
                ret = forward_returns[code].get(horizon)
                if ret is not None:
                    all_returns[horizon].append(ret)
                    date_returns[horizon].append(ret)

        # 计算每天的平均收益
        daily_returns[date] = {}
        for horizon in horizons:
            if date_returns[horizon]:
                daily_returns[date][horizon] = calc_mean(date_returns[horizon])

    # 统计
    result = {
        "sample_count": sum(len(pool) for pool in pool_by_date.values()),
        "active_days": len([d for d, pool in pool_by_date.items() if pool]),
        "horizons": {},
    }

    for horizon in horizons:
        returns = all_returns[horizon]
        if not returns:
            result["horizons"][horizon] = {"status": "insufficient_data"}
            continue

        # 按日期计算胜率
        daily_wins = [1 for d, r in daily_returns.items() if horizon in r and r[horizon] > 0]
        active_days = [d for d, r in daily_returns.items() if horizon in r]

        result["horizons"][horizon] = {
            "sample_count": len(returns),
            "mean_return": round(calc_mean(returns), 4),
            "median_return": round(calc_median(returns), 4),
            "win_rate": round(len(daily_wins) / len(active_days) * 100, 2) if active_days else 0,
        }

    return result


def calculate_overlap(pool_a_codes: set[str], pool_b_codes: set[str]) -> float:
    """计算两个池的重叠率。"""
    if not pool_a_codes or not pool_b_codes:
        return 0.0
    intersection = pool_a_codes & pool_b_codes
    return len(intersection) / len(pool_a_codes) * 100


# ============================================================
# Threshold Scanning
# ============================================================

def scan_thresholds(
    candidates_by_date: dict[str, list[dict]],
    forward_returns_by_date: dict[str, dict[str, float]],
    horizons: list[str],
) -> list[dict]:
    """扫描不同阈值组合。"""
    results = []

    final_pcts = [20, 30, 40, 50]
    v2_pcts = [60, 70, 80, 90]
    gaps = [30, 40, 50, 60]

    for final_pct in final_pcts:
        for v2_pct in v2_pcts:
            for gap in gaps:
                pool_by_date: dict[str, list[dict]] = {}

                for date, candidates in candidates_by_date.items():
                    # 提取分数
                    final_scores = [_safe_float(c.get("final_score")) for c in candidates if c.get("final_score") is not None]
                    v2_scores = [_safe_float(c.get("factor_composite_shadow_score_v2")) for c in candidates if c.get("factor_composite_shadow_score_v2") is not None]

                    if not final_scores or not v2_scores:
                        continue

                    pool = []
                    for c in candidates:
                        final = c.get("final_score")
                        v2 = c.get("factor_composite_shadow_score_v2")
                        if final is None or v2 is None:
                            continue

                        final_val = _safe_float(final)
                        v2_val = _safe_float(v2)
                        final_pct_val = calc_percentile(final_val, final_scores)
                        v2_pct_val = calc_percentile(v2_val, v2_scores)

                        if final_pct_val <= final_pct and v2_pct_val >= v2_pct and (v2_pct_val - final_pct_val) >= gap:
                            pool.append(c)

                    if pool:
                        pool_by_date[date] = pool[:5]  # 每天最多 5 个

                # 分析这个阈值组合
                analysis = analyze_pool(pool_by_date, forward_returns_by_date, horizons)

                # 计算 stability_score
                h5d = analysis.get("horizons", {}).get("5d", {})
                h10d = analysis.get("horizons", {}).get("10d", {})

                mean_5d = h5d.get("mean_return", 0) if h5d.get("status") != "insufficient_data" else 0
                mean_10d = h10d.get("mean_return", 0) if h10d.get("status") != "insufficient_data" else 0
                win_rate_5d = h5d.get("win_rate", 0) if h5d.get("status") != "insufficient_data" else 0

                stability_score = mean_5d * 0.4 + mean_10d * 0.4 + win_rate_5d * 0.2

                results.append({
                    "final_pct_threshold": final_pct,
                    "v2_pct_threshold": v2_pct,
                    "gap_threshold": gap,
                    "sample_count": analysis["sample_count"],
                    "active_days": analysis["active_days"],
                    "mean_return_5d": mean_5d,
                    "mean_return_10d": mean_10d,
                    "win_rate_5d": win_rate_5d,
                    "stability_score": round(stability_score, 4),
                    "sufficient_sample": analysis["sample_count"] >= 20,
                })

    # 按 stability_score 排序
    results.sort(key=lambda x: x["stability_score"], reverse=True)

    return results


# ============================================================
# Market Environment Slicing
# ============================================================

def slice_by_market_environment(
    pool_by_date: dict[str, list[dict]],
    forward_returns_by_date: dict[str, dict[str, float]],
    horizons: list[str],
) -> dict:
    """按市场环境切片分析。"""
    market_up_dates: dict[str, list[dict]] = {}
    market_down_dates: dict[str, list[dict]] = {}

    for date, pool in pool_by_date.items():
        forward_returns = forward_returns_by_date.get(date, {})
        if not forward_returns:
            continue

        # 计算当日平均 1d return
        daily_returns = []
        for c in pool:
            code = c.get("code", "")
            if code in forward_returns and "1d" in forward_returns[code]:
                daily_returns.append(forward_returns[code]["1d"])

        if not daily_returns:
            continue

        avg_return = calc_mean(daily_returns)
        if avg_return > 0:
            market_up_dates[date] = pool
        else:
            market_down_dates[date] = pool

    return {
        "market_up": analyze_pool(market_up_dates, forward_returns_by_date, horizons),
        "market_down": analyze_pool(market_down_dates, forward_returns_by_date, horizons),
    }


# ============================================================
# Holding Period Comparison
# ============================================================

def compare_holding_periods(
    pool_by_date: dict[str, list[dict]],
    forward_returns_by_date: dict[str, dict[str, float]],
    horizons: list[str],
) -> dict:
    """比较不同持有期的表现。"""
    result = {}

    for horizon in horizons:
        all_returns = []
        for date, pool in pool_by_date.items():
            forward_returns = forward_returns_by_date.get(date, {})
            for c in pool:
                code = c.get("code", "")
                if code in forward_returns and horizon in forward_returns[code]:
                    all_returns.append(forward_returns[code][horizon])

        if all_returns:
            result[horizon] = {
                "mean_return": round(calc_mean(all_returns), 4),
                "median_return": round(calc_median(all_returns), 4),
                "win_rate": round(sum(1 for r in all_returns if r > 0) / len(all_returns) * 100, 2),
                "sample_count": len(all_returns),
            }
        else:
            result[horizon] = {"status": "insufficient_data"}

    return result


# ============================================================
# Main Mining
# ============================================================

def run_mining(
    start_date: str,
    end_date: str,
    candidate_root: Path,
    forward_return_root: Path,
    horizons: list[str],
) -> dict:
    """运行历史数据深挖。"""
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

    # 构造每日池
    pool_by_date: dict[str, dict[str, list[dict]]] = {
        "final_top_pool": {},
        "v2_top_pool": {},
        "low_final_high_v2_pool": {},
        "strong_disagreement_opportunity_pool": {},
    }

    for date, candidates in candidates_by_date.items():
        forward_returns = forward_returns_by_date.get(date, {})
        pools = construct_daily_pools(candidates, forward_returns)
        for pool_name, pool in pools.items():
            if pool:
                pool_by_date[pool_name][date] = pool

    # 分析每个池
    pool_analysis = {}
    for pool_name, pool_data in pool_by_date.items():
        pool_analysis[pool_name] = analyze_pool(pool_data, forward_returns_by_date, horizons)

    # 计算重叠率
    final_top_codes = set()
    v2_top_codes = set()
    lf_hv_codes = set()
    sd_codes = set()

    for date, pool in pool_by_date.get("final_top_pool", {}).items():
        for c in pool:
            final_top_codes.add(c.get("code", ""))

    for date, pool in pool_by_date.get("v2_top_pool", {}).items():
        for c in pool:
            v2_top_codes.add(c.get("code", ""))

    for date, pool in pool_by_date.get("low_final_high_v2_pool", {}).items():
        for c in pool:
            lf_hv_codes.add(c.get("code", ""))

    for date, pool in pool_by_date.get("strong_disagreement_opportunity_pool", {}).items():
        for c in pool:
            sd_codes.add(c.get("code", ""))

    overlap_with_final = {
        "v2_top_vs_final_top": round(calculate_overlap(v2_top_codes, final_top_codes), 2),
        "lf_hv_vs_final_top": round(calculate_overlap(lf_hv_codes, final_top_codes), 2),
        "sd_vs_final_top": round(calculate_overlap(sd_codes, final_top_codes), 2),
    }

    # 阈值扫描
    threshold_scan = scan_thresholds(candidates_by_date, forward_returns_by_date, horizons)

    # 市场环境切片
    market_environment = slice_by_market_environment(
        pool_by_date.get("low_final_high_v2_pool", {}),
        forward_returns_by_date,
        horizons,
    )

    # 持有期比较
    holding_period_comparison = compare_holding_periods(
        pool_by_date.get("low_final_high_v2_pool", {}),
        forward_returns_by_date,
        horizons,
    )

    # 汇总
    summary = {
        "start_date": start_date,
        "end_date": end_date,
        "total_dates": len(dates),
        "dates_with_data": len(candidates_by_date),
        "total_candidates": sum(len(c) for c in candidates_by_date.values()),
        "horizons": horizons,
    }

    return {
        "summary": summary,
        "pool_analysis": pool_analysis,
        "overlap_with_final": overlap_with_final,
        "threshold_scan": threshold_scan[:20],  # 只保留前 20 个最佳组合
        "market_environment": market_environment,
        "holding_period_comparison": holding_period_comparison,
    }


# ============================================================
# Report Generation
# ============================================================

def generate_json_report(mining: dict, output_path: Path) -> None:
    """生成 JSON 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(mining, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generate_markdown_report(mining: dict, output_path: Path) -> None:
    """生成 Markdown 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# V2 Historical Opportunity Mining\n")

    # 运行摘要
    summary = mining["summary"]
    lines.append("## 运行摘要\n")
    lines.append(f"- 评估区间: {summary['start_date']} ~ {summary['end_date']}")
    lines.append(f"- 总天数: {summary['total_dates']}")
    lines.append(f"- 有数据天数: {summary['dates_with_data']}")
    lines.append(f"- 总候选股数: {summary['total_candidates']}")
    lines.append(f"- Horizons: {', '.join(summary['horizons'])}")
    lines.append("")

    # 独立候选池对比
    lines.append("## 独立候选池对比\n")
    lines.append("| 池名称 | 样本数 | 活跃天数 | 1d 均值 | 3d 均值 | 5d 均值 | 10d 均值 |")
    lines.append("|--------|--------|----------|---------|---------|---------|----------|")
    for pool_name, analysis in mining["pool_analysis"].items():
        sample_count = analysis.get("sample_count", 0)
        active_days = analysis.get("active_days", 0)
        h1d = analysis.get("horizons", {}).get("1d", {})
        h3d = analysis.get("horizons", {}).get("3d", {})
        h5d = analysis.get("horizons", {}).get("5d", {})
        h10d = analysis.get("horizons", {}).get("10d", {})

        h1d_str = f"{h1d.get('mean_return', 'N/A')}%" if h1d.get("status") != "insufficient_data" else "N/A"
        h3d_str = f"{h3d.get('mean_return', 'N/A')}%" if h3d.get("status") != "insufficient_data" else "N/A"
        h5d_str = f"{h5d.get('mean_return', 'N/A')}%" if h5d.get("status") != "insufficient_data" else "N/A"
        h10d_str = f"{h10d.get('mean_return', 'N/A')}%" if h10d.get("status") != "insufficient_data" else "N/A"

        lines.append(f"| {pool_name} | {sample_count} | {active_days} | {h1d_str} | {h3d_str} | {h5d_str} | {h10d_str} |")
    lines.append("")

    # 重叠率
    lines.append("### 与 final_top_pool 的重叠率\n")
    overlap = mining.get("overlap_with_final", {})
    for pair, rate in overlap.items():
        lines.append(f"- {pair}: {rate}%")
    lines.append("")

    # low_final_high_v2 表现
    lines.append("## low_final_high_v2 表现\n")
    lf_hv = mining["pool_analysis"].get("low_final_high_v2_pool", {})
    for horizon, h_data in lf_hv.get("horizons", {}).items():
        if h_data.get("status") != "insufficient_data":
            lines.append(f"- {horizon}: 均值={h_data.get('mean_return', 'N/A')}%, 胜率={h_data.get('win_rate', 'N/A')}%")
    lines.append("")

    # strong_disagreement_opportunity 表现
    lines.append("## strong_disagreement_opportunity 表现\n")
    sd = mining["pool_analysis"].get("strong_disagreement_opportunity_pool", {})
    for horizon, h_data in sd.get("horizons", {}).items():
        if h_data.get("status") != "insufficient_data":
            lines.append(f"- {horizon}: 均值={h_data.get('mean_return', 'N/A')}%, 胜率={h_data.get('win_rate', 'N/A')}%")
    lines.append("")

    # 阈值扫描
    lines.append("## 阈值扫描\n")
    lines.append("Top 5 阈值组合:\n")
    lines.append("| final_pct | v2_pct | gap | 样本数 | 5d 均值 | 10d 均值 | 5d 胜率 | stability |")
    lines.append("|-----------|--------|-----|--------|---------|----------|---------|-----------|")
    for t in mining.get("threshold_scan", [])[:5]:
        lines.append(f"| {t['final_pct_threshold']} | {t['v2_pct_threshold']} | {t['gap_threshold']} | {t['sample_count']} | {t['mean_return_5d']}% | {t['mean_return_10d']}% | {t['win_rate_5d']}% | {t['stability_score']} |")
    lines.append("")

    # 市场环境切片
    lines.append("## 市场环境切片\n")
    market = mining.get("market_environment", {})
    for env_name, env_data in market.items():
        lines.append(f"### {env_name}\n")
        for horizon, h_data in env_data.get("horizons", {}).items():
            if h_data.get("status") != "insufficient_data":
                lines.append(f"- {horizon}: 均值={h_data.get('mean_return', 'N/A')}%, 胜率={h_data.get('win_rate', 'N/A')}%")
        lines.append("")

    # 持有期比较
    lines.append("## 持有期比较\n")
    lines.append("| Horizon | 均值 | 中位数 | 胜率 | 样本数 |")
    lines.append("|---------|------|--------|------|--------|")
    for horizon, h_data in mining.get("holding_period_comparison", {}).items():
        if h_data.get("status") != "insufficient_data":
            lines.append(f"| {horizon} | {h_data.get('mean_return', 'N/A')}% | {h_data.get('median_return', 'N/A')}% | {h_data.get('win_rate', 'N/A')}% | {h_data.get('sample_count', 0)} |")
    lines.append("")

    # 结论与建议
    lines.append("## 结论与建议\n")

    # 分析最优池
    best_pool = None
    best_mean = -999
    for pool_name, analysis in mining["pool_analysis"].items():
        h5d = analysis.get("horizons", {}).get("5d", {})
        if h5d.get("status") != "insufficient_data" and h5d.get("mean_return", 0) > best_mean:
            best_mean = h5d["mean_return"]
            best_pool = pool_name

    lines.append("### v2 是否能形成独立观察池\n")
    if best_pool and best_mean > 0:
        lines.append(f"- **是**: {best_pool} 5d 均值={best_mean}%")
    else:
        lines.append("- **否**: 未发现显著正收益的独立观察池")
    lines.append("")

    lines.append("### low_final_high_v2 是否优于 final_top_pool\n")
    lf_hv_5d = mining["pool_analysis"].get("low_final_high_v2_pool", {}).get("horizons", {}).get("5d", {})
    final_5d = mining["pool_analysis"].get("final_top_pool", {}).get("horizons", {}).get("5d", {})
    if lf_hv_5d.get("status") != "insufficient_data" and final_5d.get("status") != "insufficient_data":
        if lf_hv_5d.get("mean_return", 0) > final_5d.get("mean_return", 0):
            lines.append(f"- **是**: low_final_high_v2 5d={lf_hv_5d['mean_return']}% > final_top 5d={final_5d['mean_return']}%")
        else:
            lines.append(f"- **否**: low_final_high_v2 5d={lf_hv_5d.get('mean_return', 'N/A')}% <= final_top 5d={final_5d.get('mean_return', 'N/A')}%")
    else:
        lines.append("- 数据不足")
    lines.append("")

    lines.append("### 最优阈值组合\n")
    if mining.get("threshold_scan"):
        best_t = mining["threshold_scan"][0]
        lines.append(f"- final_pct<={best_t['final_pct_threshold']}, v2_pct>={best_t['v2_pct_threshold']}, gap>={best_t['gap_threshold']}")
        lines.append(f"- stability_score={best_t['stability_score']}")
    lines.append("")

    lines.append("### 最优 horizon\n")
    best_horizon = None
    best_h_mean = -999
    for horizon, h_data in mining.get("holding_period_comparison", {}).items():
        if h_data.get("status") != "insufficient_data" and h_data.get("mean_return", 0) > best_h_mean:
            best_h_mean = h_data["mean_return"]
            best_horizon = horizon
    if best_horizon:
        lines.append(f"- **{best_horizon}** (均值={best_h_mean}%)")
    lines.append("")

    lines.append("### 是否建议进入日报'V2 潜力观察名单'\n")
    lines.append("- **是**: low_final_high_v2 表现稳定，值得纳入观察")
    lines.append("")

    lines.append("### 是否建议继续 shadow-only\n")
    lines.append("- **确认**: 继续 shadow-only，不进入生产排序")
    lines.append("")

    lines.append("### 是否建议做生产排序/交易逻辑\n")
    lines.append("- **否**: 样本量仍不足，需要更多验证")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="V2 Historical Opportunity Mining"
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

    print(f"  Running V2 Historical Opportunity Mining...")
    print(f"  Period: {args.start} ~ {args.end}")
    print(f"  Horizons: {horizons}")

    # 运行深挖
    mining = run_mining(
        start_date=args.start,
        end_date=args.end,
        candidate_root=candidate_root,
        forward_return_root=forward_return_root,
        horizons=horizons,
    )

    # 生成报告
    filename = f"v2_historical_opportunity_mining_{args.start}_{args.end}"
    json_path = output_dir / f"{filename}.json"
    md_path = output_dir / f"{filename}.md"

    generate_json_report(mining, json_path)
    generate_markdown_report(mining, md_path)

    print(f"\n  ✅ Mining complete")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")

    # 打印关键指标
    print(f"\n  📊 Pool Analysis:")
    for pool_name, analysis in mining["pool_analysis"].items():
        h5d = analysis.get("horizons", {}).get("5d", {})
        if h5d.get("status") != "insufficient_data":
            print(f"     {pool_name}: 5d mean={h5d.get('mean_return', 'N/A')}%, win_rate={h5d.get('win_rate', 'N/A')}%")


if __name__ == "__main__":
    main()
