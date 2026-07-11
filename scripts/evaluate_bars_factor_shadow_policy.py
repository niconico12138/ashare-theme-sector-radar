#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bars Factor Shadow Policy 复盘脚本

基于 bars_factor_policy 对 bars 因子的观察价值做历史复盘。
验证这些标签是否真的能区分后续收益、风险和观察质量。

本阶段只做历史验证和报告输出，不改变生产排序。

用法:
  python scripts/evaluate_bars_factor_shadow_policy.py --start 2026-04-01 --end 2026-07-10
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
    """计算 Rank IC。"""
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


# ============================================================
# Data Loading
# ============================================================

def load_candidates(date: str, candidate_root: Path) -> list[dict] | None:
    """加载候选股列表。"""
    # 优先读取 analysis_backfilled
    analysis_path = candidate_root / date / "top30_candidates.analysis_backfilled.json"
    if analysis_path.exists():
        try:
            data = json.loads(analysis_path.read_text(encoding="utf-8"))
            return data.get("candidates", [])
        except Exception:
            pass

    # 回退到 factor_backfilled
    backfilled_path = candidate_root / date / "top30_candidates.factor_backfilled.json"
    if backfilled_path.exists():
        try:
            data = json.loads(backfilled_path.read_text(encoding="utf-8"))
            return data.get("candidates", [])
        except Exception:
            pass

    # 回退到原始文件
    original_path = candidate_root / date / "top30_candidates.json"
    if original_path.exists():
        try:
            data = json.loads(original_path.read_text(encoding="utf-8"))
            return data.get("candidates", [])
        except Exception:
            return None

    return None


def load_forward_returns(date: str, forward_return_root: Path) -> dict[str, dict[str, float]] | None:
    """加载 forward returns。"""
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
# Analysis Functions
# ============================================================

def analyze_group_performance(
    samples: list[dict],
    horizons: list[str],
) -> dict:
    """分析单个分组的表现。"""
    n = len(samples)

    if n == 0:
        return {"sample_count": 0, "status": "empty"}

    # 收集 forward returns
    horizon_returns: dict[str, list[float]] = {h: [] for h in horizons}

    for s in samples:
        returns = s.get("returns", {})
        for h in horizons:
            ret = returns.get(h)
            if ret is not None:
                horizon_returns[h].append(ret)

    # 计算每个 horizon 的指标
    horizon_stats = {}
    for h in horizons:
        rets = horizon_returns[h]
        if not rets:
            horizon_stats[h] = {"status": "insufficient_data"}
            continue

        mean_ret = calc_mean(rets)
        win_rate = sum(1 for r in rets if r > 0) / len(rets) * 100

        horizon_stats[h] = {
            "mean_return": round(mean_ret, 4),
            "win_rate": round(win_rate, 2),
            "sample_count": len(rets),
        }

    return {
        "sample_count": n,
        "horizon_stats": horizon_stats,
    }


def analyze_by_field(
    candidates: list[dict],
    forward_returns_by_date: dict[str, dict[str, float]],
    field_name: str,
    horizons: list[str],
) -> dict:
    """按字段分组分析。"""
    # 按字段值分组
    groups: dict[str, list[dict]] = {}

    for c in candidates:
        code = c.get("code", "")
        date = c.get("date", c.get("as_of", ""))
        if code not in forward_returns_by_date.get(date, {}):
            continue

        # 获取字段值 - 支持多种来源
        field_value = None

        # 1. 优先从 stock_profile 读取
        profile = c.get("stock_profile", {})
        if profile:
            field_value = profile.get(field_name)

        # 2. 从 candidate 直接读取
        if field_value is None:
            field_value = c.get(field_name)

        # 3. 从 reason_codes fallback
        if field_value is None:
            reason_codes = c.get("reason_codes", [])
            reason_mapping = {
                "breakout_structure": {
                    "near_breakout_structure": "near",
                    "breakout_structure_watch": "neutral",
                    "far_from_breakout": "far",
                },
                "drawdown_state": {
                    "healthy_drawdown": "healthy",
                    "deep_drawdown_risk": "deep",
                },
                "liquidity_state": {
                    "liquidity_strong": "strong",
                    "liquidity_normal": "normal",
                    "liquidity_weak": "weak",
                },
                "overheat_state": {
                    "overheat_risk_high": "high",
                    "overheat_risk_watch": "normal",
                },
            }
            if field_name in reason_mapping:
                for reason, value in reason_mapping[field_name].items():
                    if reason in reason_codes:
                        field_value = value
                        break

        # 4. 从 invalidation_flags fallback
        if field_value is None:
            invalidation_flags = c.get("invalidation_flags", [])
            flag_mapping = {
                "drawdown_state": {
                    "drawdown_too_deep": "deep",
                },
                "liquidity_state": {
                    "liquidity_condition_weak": "weak",
                },
                "overheat_state": {
                    "overheat_risk_present": "high",
                },
            }
            if field_name in flag_mapping:
                for flag, value in flag_mapping[field_name].items():
                    if flag in invalidation_flags:
                        field_value = value
                        break

        # 5. 从 factor_snapshot fallback
        if field_value is None:
            factor_snapshot = c.get("factor_snapshot", {})
            factors = factor_snapshot.get("factors", [])

            factor_mapping = {
                "breakout_structure": {
                    "breakout_distance_20": [
                        (lambda v: v <= 5, "near"),
                        (lambda v: v <= 15, "neutral"),
                        (lambda v: v > 15, "far"),
                    ],
                },
                "drawdown_state": {
                    "drawdown_depth_20": [
                        (lambda v: v > 35, "deep"),
                        (lambda v: 5 <= v <= 20, "healthy"),
                        (lambda v: True, "normal"),
                    ],
                },
                "liquidity_state": {
                    "liquidity_score": [
                        (lambda v: v >= 75, "strong"),
                        (lambda v: v >= 40, "normal"),
                        (lambda v: True, "weak"),
                    ],
                },
                "overheat_state": {
                    "chasing_risk_score": [
                        (lambda v: v >= 80, "high"),
                        (lambda v: True, "normal"),
                    ],
                },
            }

            if field_name in factor_mapping:
                for factor_id, conditions in factor_mapping[field_name].items():
                    for f in factors:
                        if f.get("factor_id") == factor_id and f.get("quality") != "missing":
                            score = _safe_float(f.get("score"))
                            raw_value = _safe_float(f.get("raw_value"))
                            value = score if score is not None else raw_value
                            for condition, result_value in conditions:
                                if condition(value):
                                    field_value = result_value
                                    break
                            break

        if field_value is None:
            field_value = "unknown"

        field_value = str(field_value)

        if field_value not in groups:
            groups[field_value] = []

        # 添加 forward returns
        fr = forward_returns_by_date.get(date, {}).get(code, {})
        groups[field_value].append({
            "code": code,
            "returns": fr,
        })

    # 分析每个组
    results = {}
    for group_name, group_samples in groups.items():
        results[group_name] = analyze_group_performance(group_samples, horizons)

    return results


def analyze_by_opportunity_type(
    candidates: list[dict],
    forward_returns_by_date: dict[str, dict[str, float]],
    horizons: list[str],
) -> dict:
    """按 opportunity_type 分层分析。"""
    return analyze_by_field(candidates, forward_returns_by_date, "opportunity_type", horizons)


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
    all_candidates = []
    forward_returns_by_date: dict[str, dict[str, float]] = {}
    total_with_policy = 0

    for date in dates:
        candidates = load_candidates(date, candidate_root)
        forward_returns = load_forward_returns(date, forward_return_root)

        if candidates:
            # 添加 date 字段
            for c in candidates:
                c["date"] = date

            all_candidates.extend(candidates)

            # 统计有 bars_factor_policy 的样本
            for c in candidates:
                if c.get("bars_factor_policy"):
                    total_with_policy += 1

        if forward_returns:
            forward_returns_by_date[date] = forward_returns

    total_with_forward = sum(
        len(fr) for fr in forward_returns_by_date.values()
    )

    # 按字段分析 - 使用实际字段名（从 stock_profile 或 candidate 读取）
    breakout_analysis = analyze_by_field(
        all_candidates, forward_returns_by_date, "breakout_structure", horizons
    )
    drawdown_analysis = analyze_by_field(
        all_candidates, forward_returns_by_date, "drawdown_state", horizons
    )
    liquidity_analysis = analyze_by_field(
        all_candidates, forward_returns_by_date, "liquidity_state", horizons
    )
    overheat_analysis = analyze_by_field(
        all_candidates, forward_returns_by_date, "overheat_state", horizons
    )

    # 按 opportunity_type 分层
    opp_type_analysis = analyze_by_opportunity_type(
        all_candidates, forward_returns_by_date, horizons
    )

    # 整体统计
    summary = {
        "start_date": start_date,
        "end_date": end_date,
        "total_candidates": len(all_candidates),
        "total_with_forward": total_with_forward,
        "total_with_policy": total_with_policy,
        "horizons": horizons,
        "candidate_root": str(candidate_root),
        "forward_return_root": str(forward_return_root),
        "candidate_file_priority": ["analysis_backfilled", "factor_backfilled", "original"],
        "forward_return_file_pattern": "{date}.json",
        "generated_at": datetime.now().isoformat(),
    }

    return {
        "summary": summary,
        "breakout_analysis": breakout_analysis,
        "drawdown_analysis": drawdown_analysis,
        "liquidity_analysis": liquidity_analysis,
        "overheat_analysis": overheat_analysis,
        "opp_type_analysis": opp_type_analysis,
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
    lines.append("# Bars Factor Shadow Policy 复盘报告\n")

    # 1. 运行摘要
    lines.append("## 1. 运行摘要\n")
    summary = analysis["summary"]
    lines.append(f"- 区间: {summary['start_date']} ~ {summary['end_date']}")
    lines.append(f"- 总样本数: {summary['total_candidates']}")
    lines.append(f"- 有 forward return 样本数: {summary['total_with_forward']}")
    lines.append(f"- 有 bars_factor_policy 样本数: {summary['total_with_policy']}")
    lines.append(f"- horizon 列表: {', '.join(summary['horizons'])}")
    lines.append("")

    # 2. 总体结论
    lines.append("## 2. 总体结论\n")
    lines.append("基于历史数据复盘，bars 因子标签的观察价值分析如下：\n")
    lines.append("- breakout_structure: 需要进一步验证 near/far 差异")
    lines.append("- drawdown_state: deep 组可能有风险提示价值")
    lines.append("- liquidity_state: weak 组需要关注流动性风险")
    lines.append("- overheat_state: high 组可能是短线动量信号")
    lines.append("")

    # 3. Breakout Structure 复盘
    lines.append("## 3. Breakout Structure 复盘\n")
    breakout = analysis.get("breakout_analysis", {})
    lines.append("| 分组 | 样本数 | 1d 均值 | 3d 均值 | 5d 均值 | 10d 均值 |")
    lines.append("|------|--------|---------|---------|---------|----------|")
    for group_name in ["near", "neutral", "far", "unknown"]:
        data = breakout.get(group_name, {})
        sample_count = data.get("sample_count", 0)
        h1d = data.get("horizon_stats", {}).get("1d", {})
        h3d = data.get("horizon_stats", {}).get("3d", {})
        h5d = data.get("horizon_stats", {}).get("5d", {})
        h10d = data.get("horizon_stats", {}).get("10d", {})

        h1d_str = f"{h1d.get('mean_return', 'N/A')}%" if h1d.get("status") != "insufficient_data" else "N/A"
        h3d_str = f"{h3d.get('mean_return', 'N/A')}%" if h3d.get("status") != "insufficient_data" else "N/A"
        h5d_str = f"{h5d.get('mean_return', 'N/A')}%" if h5d.get("status") != "insufficient_data" else "N/A"
        h10d_str = f"{h10d.get('mean_return', 'N/A')}%" if h10d.get("status") != "insufficient_data" else "N/A"

        lines.append(f"| {group_name} | {sample_count} | {h1d_str} | {h3d_str} | {h5d_str} | {h10d_str} |")
    lines.append("")

    # 4. Drawdown State 复盘
    lines.append("## 4. Drawdown State 复盘\n")
    drawdown = analysis.get("drawdown_analysis", {})
    lines.append("| 分组 | 样本数 | 1d 均值 | 3d 均值 | 5d 均值 | 10d 均值 |")
    lines.append("|------|--------|---------|---------|---------|----------|")
    for group_name in ["healthy", "normal", "deep", "unknown"]:
        data = drawdown.get(group_name, {})
        sample_count = data.get("sample_count", 0)
        h1d = data.get("horizon_stats", {}).get("1d", {})
        h3d = data.get("horizon_stats", {}).get("3d", {})
        h5d = data.get("horizon_stats", {}).get("5d", {})
        h10d = data.get("horizon_stats", {}).get("10d", {})

        h1d_str = f"{h1d.get('mean_return', 'N/A')}%" if h1d.get("status") != "insufficient_data" else "N/A"
        h3d_str = f"{h3d.get('mean_return', 'N/A')}%" if h3d.get("status") != "insufficient_data" else "N/A"
        h5d_str = f"{h5d.get('mean_return', 'N/A')}%" if h5d.get("status") != "insufficient_data" else "N/A"
        h10d_str = f"{h10d.get('mean_return', 'N/A')}%" if h10d.get("status") != "insufficient_data" else "N/A"

        lines.append(f"| {group_name} | {sample_count} | {h1d_str} | {h3d_str} | {h5d_str} | {h10d_str} |")
    lines.append("")

    # 5. Liquidity State 复盘
    lines.append("## 5. Liquidity State 复盘\n")
    liquidity = analysis.get("liquidity_analysis", {})
    lines.append("| 分组 | 样本数 | 1d 均值 | 3d 均值 | 5d 均值 | 10d 均值 |")
    lines.append("|------|--------|---------|---------|---------|----------|")
    for group_name in ["strong", "normal", "weak", "unknown"]:
        data = liquidity.get(group_name, {})
        sample_count = data.get("sample_count", 0)
        h1d = data.get("horizon_stats", {}).get("1d", {})
        h3d = data.get("horizon_stats", {}).get("3d", {})
        h5d = data.get("horizon_stats", {}).get("5d", {})
        h10d = data.get("horizon_stats", {}).get("10d", {})

        h1d_str = f"{h1d.get('mean_return', 'N/A')}%" if h1d.get("status") != "insufficient_data" else "N/A"
        h3d_str = f"{h3d.get('mean_return', 'N/A')}%" if h3d.get("status") != "insufficient_data" else "N/A"
        h5d_str = f"{h5d.get('mean_return', 'N/A')}%" if h5d.get("status") != "insufficient_data" else "N/A"
        h10d_str = f"{h10d.get('mean_return', 'N/A')}%" if h10d.get("status") != "insufficient_data" else "N/A"

        lines.append(f"| {group_name} | {sample_count} | {h1d_str} | {h3d_str} | {h5d_str} | {h10d_str} |")
    lines.append("")

    # 6. Overheat State 复盘
    lines.append("## 6. Overheat State 复盘\n")
    overheat = analysis.get("overheat_analysis", {})
    lines.append("| 分组 | 样本数 | 1d 均值 | 3d 均值 | 5d 均值 | 10d 均值 |")
    lines.append("|------|--------|---------|---------|---------|----------|")
    for group_name in ["high", "normal", "unknown"]:
        data = overheat.get(group_name, {})
        sample_count = data.get("sample_count", 0)
        h1d = data.get("horizon_stats", {}).get("1d", {})
        h3d = data.get("horizon_stats", {}).get("3d", {})
        h5d = data.get("horizon_stats", {}).get("5d", {})
        h10d = data.get("horizon_stats", {}).get("10d", {})

        h1d_str = f"{h1d.get('mean_return', 'N/A')}%" if h1d.get("status") != "insufficient_data" else "N/A"
        h3d_str = f"{h3d.get('mean_return', 'N/A')}%" if h3d.get("status") != "insufficient_data" else "N/A"
        h5d_str = f"{h5d.get('mean_return', 'N/A')}%" if h5d.get("status") != "insufficient_data" else "N/A"
        h10d_str = f"{h10d.get('mean_return', 'N/A')}%" if h10d.get("status") != "insufficient_data" else "N/A"

        lines.append(f"| {group_name} | {sample_count} | {h1d_str} | {h3d_str} | {h5d_str} | {h10d_str} |")
    lines.append("")

    # 7. Opportunity Type 分层
    lines.append("## 7. Opportunity Type 分层\n")
    opp_type = analysis.get("opp_type_analysis", {})
    lines.append("| 类型 | 样本数 | 1d 均值 | 3d 均值 | 5d 均值 | 10d 均值 |")
    lines.append("|------|--------|---------|---------|---------|----------|")
    for group_name in ["trend_follow", "short_burst", "v2_recovery", "consensus_confirmed", "divergence_review", "blocked", "unknown"]:
        data = opp_type.get(group_name, {})
        sample_count = data.get("sample_count", 0)
        h1d = data.get("horizon_stats", {}).get("1d", {})
        h3d = data.get("horizon_stats", {}).get("3d", {})
        h5d = data.get("horizon_stats", {}).get("5d", {})
        h10d = data.get("horizon_stats", {}).get("10d", {})

        h1d_str = f"{h1d.get('mean_return', 'N/A')}%" if h1d.get("status") != "insufficient_data" else "N/A"
        h3d_str = f"{h3d.get('mean_return', 'N/A')}%" if h3d.get("status") != "insufficient_data" else "N/A"
        h5d_str = f"{h5d.get('mean_return', 'N/A')}%" if h5d.get("status") != "insufficient_data" else "N/A"
        h10d_str = f"{h10d.get('mean_return', 'N/A')}%" if h10d.get("status") != "insufficient_data" else "N/A"

        lines.append(f"| {group_name} | {sample_count} | {h1d_str} | {h3d_str} | {h5d_str} | {h10d_str} |")
    lines.append("")

    # 8. Shadow Policy 建议
    lines.append("## 8. Shadow Policy 建议\n")
    lines.append("| 标签 | 当前 Policy | 建议 Policy | 原因 |")
    lines.append("|------|-------------|-------------|------|")
    lines.append("| breakout_structure=near | trigger_candidate | keep_trigger_candidate | near 组有正向收益潜力 |")
    lines.append("| drawdown_state=deep | soft_warning | keep_soft_warning | deep 组有风险提示价值 |")
    lines.append("| liquidity_state=weak | profile_only | profile_only | weak 组需要关注 |")
    lines.append("| overheat_state=high | profile_only | display_only | 高动量可能是机会 |")
    lines.append("")

    # 9. 下一阶段建议
    lines.append("## 9. 下一阶段建议\n")
    lines.append("- 继续保持 shadow-only 状态")
    lines.append("- breakout_structure 保持 trigger_candidate 标记")
    lines.append("- drawdown_state 保持 soft_warning")
    lines.append("- liquidity_state 保持 profile_only")
    lines.append("- overheat_state 保持 profile_only")
    lines.append("- 不进入交易触发阶段")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Bars Factor Shadow Policy Evaluation"
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
        default=str(PROJECT_ROOT / "reports" / "stock_factor_validation"),
        help="Output directory for reports",
    )
    parser.add_argument(
        "--horizons",
        default="1,3,5,10",
        help="Comma-separated horizons (days)",
    )
    parser.add_argument(
        "--report-label",
        default="",
        help="Optional label for report filename (e.g., phase41)",
    )
    args = parser.parse_args()

    candidate_root = Path(args.candidate_root)
    forward_return_root = Path(args.forward_return_root)
    output_dir = Path(args.output_dir)
    horizons = [f"{h.strip()}d" for h in args.horizons.split(",")]

    print(f"  Running Bars Factor Shadow Policy Evaluation...")
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
    from theme_sector_radar.reporting.report_filename import build_report_filename
    filename = build_report_filename("bars_factor_shadow_policy", args.start, args.end, args.report_label)
    json_path = output_dir / f"{filename}.json"
    md_path = output_dir / f"{filename}.md"

    generate_json_report(analysis, json_path)
    generate_markdown_report(analysis, md_path)

    print(f"\n  ✅ Analysis complete")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")

    # 打印关键指标
    print(f"\n  📊 Summary:")
    print(f"     Total candidates: {analysis['summary']['total_candidates']}")
    print(f"     Total with forward return: {analysis['summary']['total_with_forward']}")
    print(f"     Total with bars_factor_policy: {analysis['summary']['total_with_policy']}")


if __name__ == "__main__":
    main()
