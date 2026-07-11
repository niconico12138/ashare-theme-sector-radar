#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bars 因子分组区分度诊断脚本

验证分组是否有区分度，检查因子定义是否重复。
本阶段只做诊断和报告，不改变生产逻辑。

用法:
  python scripts/diagnose_bars_group_discrimination.py --start 2026-04-01 --end 2026-07-10
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
    """加载候选股列表。优先读取 analysis_backfilled（包含 stock_profile）。"""
    # 优先读取 analysis_backfilled（包含 stock_profile）
    analysis_path = candidate_root / date / "top30_candidates.analysis_backfilled.json"
    if analysis_path.exists():
        try:
            data = json.loads(analysis_path.read_text(encoding="utf-8"))
            return data.get("candidates", [])
        except Exception:
            pass

    # 回退到 factor_backfilled（包含最新 factor_snapshot）
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
# Group Analysis
# ============================================================

def analyze_group_discrimination(
    samples: list[dict],
    horizons: list[str],
) -> dict:
    """分析单个分组的区分度。"""
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
        median_ret = calc_median(rets)
        win_rate = sum(1 for r in rets if r > 0) / len(rets) * 100
        std_ret = calc_std(rets)

        # 极端值
        sorted_rets = sorted(rets)
        bottom_10pct = sorted_rets[:max(1, len(rets) // 10)]
        top_10pct = sorted_rets[-max(1, len(rets) // 10):]

        horizon_stats[h] = {
            "mean_return": round(mean_ret, 4),
            "median_return": round(median_ret, 4),
            "win_rate": round(win_rate, 2),
            "std": round(std_ret, 4),
            "bottom_10pct_mean": round(calc_mean(bottom_10pct), 4) if bottom_10pct else None,
            "top_10pct_mean": round(calc_mean(top_10pct), 4) if top_10pct else None,
            "sample_count": len(rets),
        }

    return {
        "sample_count": n,
        "horizon_stats": horizon_stats,
    }


def calculate_state_mapping(
    candidates: list[dict],
) -> dict:
    """计算 breakout_structure 与 drawdown_state 的映射关系。"""
    mapping = {}

    for c in candidates:
        # 优先从 stock_profile 读取
        profile = c.get("stock_profile", {})
        breakout = profile.get("breakout_structure")
        drawdown = profile.get("drawdown_state")

        # 如果 stock_profile 中没有，尝试从 reason_codes 推断
        if breakout is None:
            reason_codes = c.get("reason_codes", [])
            if "near_breakout_structure" in reason_codes:
                breakout = "near"
            elif "breakout_structure_watch" in reason_codes:
                breakout = "neutral"
            elif "far_from_breakout" in reason_codes:
                breakout = "far"
            else:
                breakout = "unknown"

        if drawdown is None:
            reason_codes = c.get("reason_codes", [])
            if "healthy_drawdown" in reason_codes:
                drawdown = "healthy"
            elif "deep_drawdown_risk" in reason_codes:
                drawdown = "deep"
            else:
                drawdown = "unknown"

        key = f"{breakout}_{drawdown}"
        if key not in mapping:
            mapping[key] = 0
        mapping[key] += 1

    return mapping


# ============================================================
# Main Diagnosis
# ============================================================

def run_diagnosis(
    start_date: str,
    end_date: str,
    candidate_root: Path,
    forward_return_root: Path,
    horizons: list[str],
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
    forward_returns_by_date: dict[str, dict[str, float]] = {}

    for date in dates:
        candidates = load_candidates(date, candidate_root)
        forward_returns = load_forward_returns(date, forward_return_root)

        if candidates:
            for c in candidates:
                c["date"] = date
            all_candidates.extend(candidates)

        if forward_returns:
            forward_returns_by_date[date] = forward_returns

    # 按状态分组分析
    state_groups = {
        "breakout_structure": {},
        "drawdown_state": {},
        "liquidity_state": {},
        "overheat_state": {},
    }

    for c in all_candidates:
        profile = c.get("stock_profile", {})
        date = c.get("date", "")
        code = c.get("code", "")

        if code not in forward_returns_by_date.get(date, {}):
            continue

        for state_name in state_groups:
            # 优先从 stock_profile 读取
            state_value = profile.get(state_name)

            # 如果 stock_profile 中没有，尝试从 reason_codes 推断
            if state_value is None:
                reason_codes = c.get("reason_codes", [])
                if state_name == "breakout_structure":
                    if "near_breakout_structure" in reason_codes:
                        state_value = "near"
                    elif "breakout_structure_watch" in reason_codes:
                        state_value = "neutral"
                    elif "far_from_breakout" in reason_codes:
                        state_value = "far"
                    else:
                        state_value = "unknown"
                elif state_name == "drawdown_state":
                    if "healthy_drawdown" in reason_codes:
                        state_value = "healthy"
                    elif "deep_drawdown_risk" in reason_codes:
                        state_value = "deep"
                    else:
                        state_value = "unknown"
                elif state_name == "liquidity_state":
                    if "liquidity_strong" in reason_codes:
                        state_value = "strong"
                    elif "liquidity_normal" in reason_codes:
                        state_value = "normal"
                    elif "liquidity_weak" in reason_codes:
                        state_value = "weak"
                    else:
                        state_value = "unknown"
                elif state_name == "overheat_state":
                    if "overheat_risk_high" in reason_codes:
                        state_value = "high"
                    elif "overheat_risk_watch" in reason_codes:
                        state_value = "normal"
                    else:
                        state_value = "unknown"
                else:
                    state_value = "unknown"
            if state_value not in state_groups[state_name]:
                state_groups[state_name][state_value] = []
            state_groups[state_name][state_value].append({
                "code": code,
                "returns": forward_returns_by_date.get(date, {}).get(code, {}),
            })

    # 分析每个状态
    state_analysis = {}
    for state_name, groups in state_groups.items():
        state_analysis[state_name] = {}
        for state_value, samples in groups.items():
            state_analysis[state_name][state_value] = analyze_group_discrimination(samples, horizons)

    # 计算 breakout_structure 与 drawdown_state 的映射关系
    state_mapping = calculate_state_mapping(all_candidates)

    # 汇总
    summary = {
        "start_date": start_date,
        "end_date": end_date,
        "total_dates": len(dates),
        "total_candidates": len(all_candidates),
        "horizons": horizons,
        "candidate_root": str(candidate_root),
        "forward_return_root": str(forward_return_root),
        "candidate_file_priority": ["analysis_backfilled", "factor_backfilled", "original"],
        "forward_return_file_pattern": "{date}.json",
        "generated_at": datetime.now().isoformat(),
    }

    return {
        "summary": summary,
        "state_analysis": state_analysis,
        "state_mapping": state_mapping,
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
    lines.append("# Bars 因子分组区分度诊断报告\n")

    # 运行摘要
    summary = diagnosis["summary"]
    lines.append("## 1. 运行摘要\n")
    lines.append(f"- 评估区间: {summary['start_date']} ~ {summary['end_date']}")
    lines.append(f"- 总天数: {summary['total_dates']}")
    lines.append(f"- 总候选股数: {summary['total_candidates']}")
    lines.append("")

    # Breakout Structure 分布
    lines.append("## 2. Breakout Structure 分组区分度\n")
    breakout = diagnosis["state_analysis"].get("breakout_structure", {})
    lines.append("| 分组 | 样本数 | 1d 均值 | 3d 均值 | 5d 均值 | 10d 均值 | 1d 胜率 |")
    lines.append("|------|--------|---------|---------|---------|----------|---------|")
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
        win_rate_str = f"{h1d.get('win_rate', 'N/A')}%" if h1d.get("status") != "insufficient_data" else "N/A"

        lines.append(f"| {group_name} | {sample_count} | {h1d_str} | {h3d_str} | {h5d_str} | {h10d_str} | {win_rate_str} |")
    lines.append("")

    # Drawdown State 分布
    lines.append("## 3. Drawdown State 分组区分度\n")
    drawdown = diagnosis["state_analysis"].get("drawdown_state", {})
    lines.append("| 分组 | 样本数 | 1d 均值 | 3d 均值 | 5d 均值 | 10d 均值 | 1d 胜率 |")
    lines.append("|------|--------|---------|---------|---------|----------|---------|")
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
        win_rate_str = f"{h1d.get('win_rate', 'N/A')}%" if h1d.get("status") != "insufficient_data" else "N/A"

        lines.append(f"| {group_name} | {sample_count} | {h1d_str} | {h3d_str} | {h5d_str} | {h10d_str} | {win_rate_str} |")
    lines.append("")

    # Liquidity State 分布
    lines.append("## 4. Liquidity State 分组区分度\n")
    liquidity = diagnosis["state_analysis"].get("liquidity_state", {})
    lines.append("| 分组 | 样本数 | 1d 均值 | 3d 均值 | 5d 均值 | 10d 均值 | 1d 胜率 |")
    lines.append("|------|--------|---------|---------|---------|----------|---------|")
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
        win_rate_str = f"{h1d.get('win_rate', 'N/A')}%" if h1d.get("status") != "insufficient_data" else "N/A"

        lines.append(f"| {group_name} | {sample_count} | {h1d_str} | {h3d_str} | {h5d_str} | {h10d_str} | {win_rate_str} |")
    lines.append("")

    # Overheat State 分布
    lines.append("## 5. Overheat State 分组区分度\n")
    overheat = diagnosis["state_analysis"].get("overheat_state", {})
    lines.append("| 分组 | 样本数 | 1d 均值 | 3d 均值 | 5d 均值 | 10d 均值 | 1d 胜率 |")
    lines.append("|------|--------|---------|---------|---------|----------|---------|")
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
        win_rate_str = f"{h1d.get('win_rate', 'N/A')}%" if h1d.get("status") != "insufficient_data" else "N/A"

        lines.append(f"| {group_name} | {sample_count} | {h1d_str} | {h3d_str} | {h5d_str} | {h10d_str} | {win_rate_str} |")
    lines.append("")

    # 状态映射
    lines.append("## 6. Breakout Structure 与 Drawdown State 映射\n")
    state_mapping = diagnosis.get("state_mapping", {})
    lines.append("| Breakout | Drawdown | 样本数 |")
    lines.append("|----------|----------|--------|")
    for key, count in sorted(state_mapping.items(), key=lambda x: -x[1]):
        parts = key.split("_", 1)
        breakout = parts[0] if len(parts) > 0 else "unknown"
        drawdown = parts[1] if len(parts) > 1 else "unknown"
        lines.append(f"| {breakout} | {drawdown} | {count} |")
    lines.append("")

    # 结论
    lines.append("## 7. 结论\n")

    # 检查 breakout_structure 区分度
    breakout = diagnosis["state_analysis"].get("breakout_structure", {})
    near_data = breakout.get("near", {}).get("horizon_stats", {}).get("5d", {})
    far_data = breakout.get("far", {}).get("horizon_stats", {}).get("5d", {})

    lines.append("### Breakout Structure 是否有区分度\n")
    if near_data.get("mean_return") is not None and far_data.get("mean_return") is not None:
        if far_data["mean_return"] > near_data["mean_return"]:
            lines.append(f"- **注意**: far 组 5d 均值 ({far_data['mean_return']:.4f}%) > near 组 ({near_data['mean_return']:.4f}%)")
            lines.append("- 当前命名或方向可能需要重新解释")
        else:
            lines.append(f"- near 组 5d 均值 ({near_data['mean_return']:.4f}%) > far 组 ({far_data['mean_return']:.4f}%)")
    else:
        lines.append("- 数据不足")
    lines.append("")

    # Drawdown State 区分度
    drawdown = diagnosis["state_analysis"].get("drawdown_state", {})
    healthy_data = drawdown.get("healthy", {}).get("horizon_stats", {}).get("5d", {})
    deep_data = drawdown.get("deep", {}).get("horizon_stats", {}).get("5d", {})

    lines.append("### Drawdown State 是否有区分度\n")
    if healthy_data.get("mean_return") is not None and deep_data.get("mean_return") is not None:
        if healthy_data["mean_return"] > deep_data["mean_return"]:
            lines.append(f"- **是**: healthy 组 5d 均值 ({healthy_data['mean_return']:.4f}%) > deep 组 ({deep_data['mean_return']:.4f}%)")
        else:
            lines.append(f"- **否**: healthy 组 5d 均值 ({healthy_data.get('mean_return', 'N/A')}%) <= deep 组 ({deep_data.get('mean_return', 'N/A')}%)")
    else:
        lines.append("- 数据不足")
    lines.append("")

    # Overheat State 有效性
    overheat = diagnosis["state_analysis"].get("overheat_state", {})
    high_data = overheat.get("high", {}).get("horizon_stats", {}).get("5d", {})
    normal_data = overheat.get("normal", {}).get("horizon_stats", {}).get("5d", {})

    lines.append("### Overheat State.high 是否有效识别风险\n")
    if high_data.get("mean_return") is not None and normal_data.get("mean_return") is not None:
        if high_data["mean_return"] < normal_data["mean_return"]:
            lines.append(f"- **是**: high 组 5d 均值 ({high_data['mean_return']:.4f}%) < normal 组 ({normal_data['mean_return']:.4f}%)")
        else:
            lines.append(f"- **否**: high 组 5d 均值 ({high_data.get('mean_return', 'N/A')}%) >= normal 组 ({normal_data.get('mean_return', 'N/A')}%)")
    else:
        lines.append("- 数据不足")
    lines.append("")

    # 建议
    lines.append("## 8. 建议\n")
    lines.append("### 是否继续 shadow-only\n")
    lines.append("- **确认**: 继续保持 shadow-only 状态")
    lines.append("")
    lines.append("### 是否建议修改 selection_quality\n")
    lines.append("- **暂不建议**: 当前 shadow policy 已足够")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Bars Group Discrimination Diagnosis"
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

    print(f"  Running Bars Group Discrimination Diagnosis...")
    print(f"  Period: {args.start} ~ {args.end}")

    # 运行诊断
    diagnosis = run_diagnosis(
        start_date=args.start,
        end_date=args.end,
        candidate_root=candidate_root,
        forward_return_root=forward_return_root,
        horizons=horizons,
    )

    # 生成报告
    from theme_sector_radar.reporting.report_filename import build_report_filename
    filename = build_report_filename("bars_group_discrimination", args.start, args.end, args.report_label)
    json_path = output_dir / f"{filename}.json"
    md_path = output_dir / f"{filename}.md"

    generate_json_report(diagnosis, json_path)
    generate_markdown_report(diagnosis, md_path)

    print(f"\n  ✅ Diagnosis complete")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")


if __name__ == "__main__":
    main()
