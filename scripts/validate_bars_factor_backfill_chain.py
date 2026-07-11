#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bars Factor Backfill Chain 验证脚本

验证新定义是否真正进入回填、存储、诊断全链路。

用法:
  python scripts/validate_bars_factor_backfill_chain.py --start 2026-04-01 --end 2026-07-10
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


def calc_correlation(x: list[float], y: list[float]) -> float | None:
    """计算 Pearson correlation。"""
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
    """加载候选股列表。优先读取 factor_backfilled（包含最新 factor_snapshot）。"""
    # 优先读取 factor_backfilled（包含最新 factor_snapshot）
    backfilled_path = candidate_root / date / "top30_candidates.factor_backfilled.json"
    if backfilled_path.exists():
        try:
            data = json.loads(backfilled_path.read_text(encoding="utf-8"))
            return data.get("candidates", [])
        except Exception:
            pass

    # 回退到 analysis_backfilled
    analysis_path = candidate_root / date / "top30_candidates.analysis_backfilled.json"
    if analysis_path.exists():
        try:
            data = json.loads(analysis_path.read_text(encoding="utf-8"))
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
# Chain Validation
# ============================================================

def validate_raw_value_chain(
    candidates: list[dict],
) -> dict:
    """验证 raw_value 链路。"""
    breakout_values = []
    drawdown_values = []

    for c in candidates:
        factor_snapshot = c.get("factor_snapshot", {})
        factors = factor_snapshot.get("factors", [])

        for f in factors:
            if f.get("factor_id") == "breakout_distance_20":
                raw_value = f.get("raw_value")
                if raw_value is not None:
                    breakout_values.append(_safe_float(raw_value))

            if f.get("factor_id") == "drawdown_depth_20":
                raw_value = f.get("raw_value")
                if raw_value is not None:
                    drawdown_values.append(_safe_float(raw_value))

    # 比较 raw_value
    min_len = min(len(breakout_values), len(drawdown_values))
    if min_len == 0:
        return {
            "sample_count": 0,
            "equal_raw_value_count": 0,
            "equal_raw_value_ratio": 0.0,
            "raw_value_correlation": None,
            "mean_abs_diff": None,
            "max_abs_diff": None,
        }

    equal_count = sum(1 for i in range(min_len) if breakout_values[i] == drawdown_values[i])
    abs_diffs = [abs(breakout_values[i] - drawdown_values[i]) for i in range(min_len)]

    return {
        "sample_count": min_len,
        "equal_raw_value_count": equal_count,
        "equal_raw_value_ratio": round(equal_count / min_len, 4) if min_len > 0 else 0.0,
        "raw_value_correlation": round(calc_correlation(breakout_values, drawdown_values), 4) if len(breakout_values) >= 3 else None,
        "mean_abs_diff": round(calc_mean(abs_diffs), 4) if abs_diffs else None,
        "max_abs_diff": round(max(abs_diffs), 4) if abs_diffs else None,
    }


def validate_state_mapping(
    candidates: list[dict],
) -> dict:
    """验证状态映射。"""
    mapping = {}

    for c in candidates:
        # 优先从 stock_profile 读取，如果没有则从 reason_codes 推断
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


def analyze_state_distribution(
    candidates: list[dict],
) -> dict:
    """分析状态分布。"""
    breakout_dist = {}
    drawdown_dist = {}

    for c in candidates:
        # 优先从 stock_profile 读取，如果没有则从 reason_codes 推断
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

        if breakout not in breakout_dist:
            breakout_dist[breakout] = 0
        breakout_dist[breakout] += 1

        if drawdown not in drawdown_dist:
            drawdown_dist[drawdown] = 0
        drawdown_dist[drawdown] += 1

    return {
        "breakout_distribution": breakout_dist,
        "drawdown_distribution": drawdown_dist,
    }


# ============================================================
# Main Validation
# ============================================================

def run_validation(
    start_date: str,
    end_date: str,
    candidate_root: Path,
    forward_return_root: Path,
) -> dict:
    """运行验证。"""
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

    # 验证 raw_value 链路
    raw_value_validation = validate_raw_value_chain(all_candidates)

    # 验证状态映射
    state_mapping = validate_state_mapping(all_candidates)

    # 分析状态分布
    state_distribution = analyze_state_distribution(all_candidates)

    # 汇总
    summary = {
        "start_date": start_date,
        "end_date": end_date,
        "total_dates": len(dates),
        "total_candidates": len(all_candidates),
        "generated_at": datetime.now().isoformat(),
        "candidate_root": str(candidate_root),
        "forward_return_root": str(forward_return_root),
        "candidate_file_priority": ["factor_backfilled", "analysis_backfilled", "original"],
        "forward_return_file_pattern": "{date}.json",
    }

    return {
        "summary": summary,
        "raw_value_validation": raw_value_validation,
        "state_mapping": state_mapping,
        "state_distribution": state_distribution,
    }


# ============================================================
# Report Generation
# ============================================================

def generate_json_report(validation: dict, output_path: Path) -> None:
    """生成 JSON 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generate_markdown_report(validation: dict, output_path: Path) -> None:
    """生成 Markdown 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Bars Factor Backfill Chain 验证报告\n")

    # 运行摘要
    summary = validation["summary"]
    lines.append("## 1. 运行摘要\n")
    lines.append(f"- 评估区间: {summary['start_date']} ~ {summary['end_date']}")
    lines.append(f"- 总天数: {summary['total_dates']}")
    lines.append(f"- 总候选股数: {summary['total_candidates']}")
    lines.append(f"- 报告生成时间: {summary['generated_at']}")
    lines.append(f"- candidate_root: {summary.get('candidate_root', 'N/A')}")
    lines.append(f"- forward_return_root: {summary.get('forward_return_root', 'N/A')}")
    lines.append(f"- candidate_file_priority: {summary.get('candidate_file_priority', [])}")
    lines.append(f"- forward_return_file_pattern: {summary.get('forward_return_file_pattern', 'N/A')}")
    lines.append("")

    # Raw Value 对比
    lines.append("## 2. Raw Value 对比\n")
    raw_val = validation["raw_value_validation"]
    lines.append(f"- sample_count: {raw_val['sample_count']}")
    lines.append(f"- equal_raw_value_count: {raw_val['equal_raw_value_count']}")
    lines.append(f"- equal_raw_value_ratio: {raw_val['equal_raw_value_ratio']}")
    lines.append(f"- raw_value_correlation: {raw_val['raw_value_correlation']}")
    lines.append(f"- mean_abs_diff: {raw_val['mean_abs_diff']}")
    lines.append(f"- max_abs_diff: {raw_val['max_abs_diff']}")
    lines.append("")

    # 状态交叉表
    lines.append("## 3. 状态交叉表\n")
    state_mapping = validation.get("state_mapping", {})
    lines.append("| Breakout | Drawdown | 样本数 |")
    lines.append("|----------|----------|--------|")
    for key, count in sorted(state_mapping.items(), key=lambda x: -x[1]):
        parts = key.split("_", 1)
        breakout = parts[0] if len(parts) > 0 else "unknown"
        drawdown = parts[1] if len(parts) > 1 else "unknown"
        lines.append(f"| {breakout} | {drawdown} | {count} |")
    lines.append("")

    # 状态分布
    lines.append("## 4. 状态分布\n")
    state_dist = validation.get("state_distribution", {})
    breakout_dist = state_dist.get("breakout_distribution", {})
    drawdown_dist = state_dist.get("drawdown_distribution", {})

    lines.append("### Breakout Structure\n")
    lines.append("| 状态 | 样本数 |")
    lines.append("|------|--------|")
    for state, count in sorted(breakout_dist.items(), key=lambda x: -x[1]):
        lines.append(f"| {state} | {count} |")
    lines.append("")

    lines.append("### Drawdown State\n")
    lines.append("| 状态 | 样本数 |")
    lines.append("|------|--------|")
    for state, count in sorted(drawdown_dist.items(), key=lambda x: -x[1]):
        lines.append(f"| {state} | {count} |")
    lines.append("")

    # 结论
    lines.append("## 5. 结论\n")
    lines.append("### Raw Value 是否仍相同\n")
    if raw_val["equal_raw_value_ratio"] == 1.0:
        lines.append("- **是**: raw_value 仍完全相同，新定义可能未进入链路")
    else:
        lines.append(f"- **否**: equal_raw_value_ratio = {raw_val['equal_raw_value_ratio']}")
    lines.append("")

    lines.append("### 状态是否仍一一对应\n")
    if len(state_mapping) <= 4:
        lines.append("- **可能**: 状态映射较少，可能存在一一对应")
    else:
        lines.append("- **否**: 状态映射较多，不完全一一对应")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Bars Factor Backfill Chain Validation"
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
        "--report-label",
        default="",
        help="Optional label for report filename (e.g., phase41)",
    )
    args = parser.parse_args()

    candidate_root = Path(args.candidate_root)
    forward_return_root = Path(args.forward_return_root)
    output_dir = Path(args.output_dir)

    print(f"  Running Bars Factor Backfill Chain Validation...")
    print(f"  Period: {args.start} ~ {args.end}")

    # 运行验证
    validation = run_validation(
        start_date=args.start,
        end_date=args.end,
        candidate_root=candidate_root,
        forward_return_root=forward_return_root,
    )

    # 生成报告
    from theme_sector_radar.reporting.report_filename import build_report_filename
    filename = build_report_filename("bars_factor_backfill_chain_validation", args.start, args.end, args.report_label)
    json_path = output_dir / f"{filename}.json"
    md_path = output_dir / f"{filename}.md"

    generate_json_report(validation, json_path)
    generate_markdown_report(validation, md_path)

    print(f"\n  ✅ Validation complete")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")

    # 打印关键指标
    raw_val = validation["raw_value_validation"]
    print(f"\n  📊 Raw Value Validation:")
    print(f"     sample_count: {raw_val['sample_count']}")
    print(f"     equal_raw_value_ratio: {raw_val['equal_raw_value_ratio']}")
    print(f"     raw_value_correlation: {raw_val['raw_value_correlation']}")


if __name__ == "__main__":
    main()
