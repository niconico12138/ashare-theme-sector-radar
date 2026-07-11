#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Factor Composite Shadow Score 负 IC 诊断脚本

诊断为什么 factor_composite_shadow_score 的 Rank IC 为负。
本阶段只做分析脚本和报告，不改变生产逻辑。

用法:
  python scripts/diagnose_factor_composite_negative_ic.py --start 2026-07-01 --end 2026-07-10 --horizon 1d
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


def load_forward_returns(date: str, forward_return_root: Path) -> dict[str, float] | None:
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
            ret = item.get("1d")  # 默认使用 1d return
            if code and ret is not None:
                result[code] = ret
        return result if result else None
    except Exception:
        return None


# ============================================================
# Diagnosis Functions
# ============================================================

def diagnose_date_level(
    date: str,
    candidates: list[dict],
    forward_returns: dict[str, float],
    horizon: str,
) -> dict:
    """日期级诊断。"""
    result = {
        "date": date,
        "candidate_count": len(candidates),
        "forward_return_count": len(forward_returns),
        "scores": {},
    }

    # 提取各 score 字段
    score_fields = [
        "final_score",
        "factor_composite_shadow_score",
        "regime_router_shadow_score_v5",
        "agent_score",
    ]

    for field in score_fields:
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
            top5_returns = sorted(zip(scores, returns), key=lambda x: x[0], reverse=True)[:5]
            top5_avg = calc_mean([r for _, r in top5_returns]) if top5_returns else None

            result["scores"][field] = {
                "rank_ic": ic,
                "sample_count": len(scores),
                "mean": calc_mean(scores),
                "std": calc_std(scores),
                "top5_avg_return": top5_avg,
                "is_negative": ic is not None and ic < 0,
            }

    return result


def diagnose_bucket_level(
    candidates: list[dict],
    forward_returns: dict[str, float],
) -> dict:
    """Bucket 级别诊断。"""
    result = {
        "buckets": {},
        "missing_buckets": [],
    }

    bucket_names = ["trend", "momentum", "volatility", "sector", "risk", "agent"]

    for bucket_name in bucket_names:
        scores = []
        returns = []
        composite_scores = []
        final_scores = []

        for c in candidates:
            code = c.get("code", "")
            breakdown = c.get("factor_composite_breakdown", {})
            bucket_data = breakdown.get(bucket_name, {})
            bucket_score = bucket_data.get("score")

            if bucket_score is None:
                continue
            if code not in forward_returns:
                continue

            scores.append(_safe_float(bucket_score))
            returns.append(forward_returns[code])
            composite_scores.append(_safe_float(c.get("factor_composite_shadow_score")))
            final_scores.append(_safe_float(c.get("final_score")))

        if not scores:
            result["missing_buckets"].append(bucket_name)
            continue

        ic = calc_rank_ic(scores, returns)
        corr_composite = calc_correlation(scores, composite_scores)
        corr_final = calc_correlation(scores, final_scores)

        result["buckets"][bucket_name] = {
            "rank_ic": ic,
            "sample_count": len(scores),
            "mean": calc_mean(scores),
            "std": calc_std(scores),
            "correlation_with_composite": corr_composite,
            "correlation_with_final": corr_final,
            "coverage": len(scores) / len(candidates) * 100 if candidates else 0,
            "is_negative": ic is not None and ic < 0,
        }

    return result


def diagnose_factor_level(
    candidates: list[dict],
    forward_returns: dict[str, float],
) -> dict:
    """因子级别诊断。"""
    result = {
        "factors": {},
        "missing_factors": [],
    }

    factor_ids = [
        "ma20_slope_5",
        "near_high_250",
        "stock_trend_score",
        "stock_short_score_v2",
        "amount_ratio_20",
        "contraction_score",
        "sector_trend_score",
        "sector_burst_score",
        "drawdown_risk_score",
        "risk_penalty_score",
    ]

    for factor_id in factor_ids:
        scores = []
        returns = []
        composite_scores = []
        final_scores = []

        for c in candidates:
            code = c.get("code", "")
            factor_snapshot = c.get("factor_snapshot", {})
            factors = factor_snapshot.get("factors", [])

            # 查找因子
            factor_value = None
            for f in factors:
                if f.get("factor_id") == factor_id and f.get("quality") != "missing":
                    factor_value = f.get("score")
                    break

            if factor_value is None or code not in forward_returns:
                continue

            scores.append(_safe_float(factor_value))
            returns.append(forward_returns[code])
            composite_scores.append(_safe_float(c.get("factor_composite_shadow_score")))
            final_scores.append(_safe_float(c.get("final_score")))

        if not scores:
            result["missing_factors"].append(factor_id)
            continue

        ic = calc_rank_ic(scores, returns)
        corr_composite = calc_correlation(scores, composite_scores)
        corr_final = calc_correlation(scores, final_scores)

        result["factors"][factor_id] = {
            "rank_ic": ic,
            "sample_count": len(scores),
            "mean": calc_mean(scores),
            "std": calc_std(scores),
            "correlation_with_composite": corr_composite,
            "correlation_with_final": corr_final,
            "coverage": len(scores) / len(candidates) * 100 if candidates else 0,
            "is_negative": ic is not None and ic < 0,
        }

    return result


def diagnose_top_bottom_spread(
    candidates: list[dict],
    forward_returns: dict[str, float],
    n: int = 5,
) -> dict:
    """Top/Bottom spread 诊断。"""
    result = {
        "top_n": n,
        "top_codes": [],
        "top_avg_return": None,
        "bottom_codes": [],
        "bottom_avg_return": None,
        "spread": None,
        "inverted_signal": False,
    }

    # 提取 factor_composite_shadow_score 和 forward return
    pairs = []
    for c in candidates:
        code = c.get("code", "")
        score = c.get("factor_composite_shadow_score")
        if score is not None and code in forward_returns:
            pairs.append({
                "code": code,
                "score": _safe_float(score),
                "return": forward_returns[code],
            })

    if len(pairs) < n * 2:
        return result

    # 按分数排序
    pairs_sorted = sorted(pairs, key=lambda x: x["score"], reverse=True)

    top = pairs_sorted[:n]
    bottom = pairs_sorted[-n:]

    result["top_codes"] = [p["code"] for p in top]
    result["top_avg_return"] = calc_mean([p["return"] for p in top])
    result["bottom_codes"] = [p["code"] for p in bottom]
    result["bottom_avg_return"] = calc_mean([p["return"] for p in bottom])
    result["spread"] = result["top_avg_return"] - result["bottom_avg_return"]
    result["inverted_signal"] = result["spread"] is not None and result["spread"] < 0

    return result


def diagnose_direction_issues(
    bucket_diagnosis: dict,
    factor_diagnosis: dict,
) -> dict:
    """方向错误检查。"""
    result = {
        "issues": [],
        "risk_bucket_reversed": False,
        "contraction_reversed": False,
        "amount_ratio_crowded": False,
        "near_high_crowded": False,
        "short_score_overheated": False,
    }

    # 检查 risk_bucket
    risk_bucket = bucket_diagnosis.get("buckets", {}).get("risk", {})
    if risk_bucket.get("is_negative"):
        result["risk_bucket_reversed"] = True
        result["issues"].append("risk_bucket has negative IC, may need direction adjustment")

    # 检查 contraction_score
    contraction = factor_diagnosis.get("factors", {}).get("contraction_score", {})
    if contraction.get("is_negative"):
        result["contraction_reversed"] = True
        result["issues"].append("contraction_score has negative IC, high contraction may not always be good")

    # 检查 amount_ratio_20
    amount_ratio = factor_diagnosis.get("factors", {}).get("amount_ratio_20", {})
    if amount_ratio.get("is_negative"):
        result["amount_ratio_crowded"] = True
        result["issues"].append("amount_ratio_20 has negative IC, chasing volume may be risky")

    # 检查 near_high_250
    near_high = factor_diagnosis.get("factors", {}).get("near_high_250", {})
    if near_high.get("is_negative"):
        result["near_high_crowded"] = True
        result["issues"].append("near_high_250 has negative IC, chasing highs may be crowded")

    # 检查 stock_short_score_v2
    short_score = factor_diagnosis.get("factors", {}).get("stock_short_score_v2", {})
    if short_score.get("is_negative"):
        result["short_score_overheated"] = True
        result["issues"].append("stock_short_score_v2 has negative IC, momentum may be overheated")

    return result


# ============================================================
# Main Diagnosis
# ============================================================

def run_diagnosis(
    start_date: str,
    end_date: str,
    candidate_root: Path,
    forward_return_root: Path,
    horizon: str = "1d",
) -> dict:
    """运行完整诊断。"""
    # 生成日期列表
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    # 收集所有数据
    all_candidates = []
    all_forward_returns = {}
    daily_results = []
    dates_with_returns = []

    for date in dates:
        candidates = load_candidates(date, candidate_root)
        forward_returns = load_forward_returns(date, forward_return_root)

        if candidates and forward_returns:
            all_candidates.extend(candidates)
            all_forward_returns.update(forward_returns)
            dates_with_returns.append(date)

            daily_result = diagnose_date_level(date, candidates, forward_returns, horizon)
            daily_results.append(daily_result)

    # Bucket 级别诊断
    bucket_diagnosis = diagnose_bucket_level(all_candidates, all_forward_returns)

    # Factor 级别诊断
    factor_diagnosis = diagnose_factor_level(all_candidates, all_forward_returns)

    # Top/Bottom spread
    spread_diagnosis = diagnose_top_bottom_spread(all_candidates, all_forward_returns)

    # 方向错误检查
    direction_issues = diagnose_direction_issues(bucket_diagnosis, factor_diagnosis)

    # 汇总
    summary = {
        "start_date": start_date,
        "end_date": end_date,
        "total_dates": len(dates),
        "dates_with_returns": len(dates_with_returns),
        "total_candidates": len(all_candidates),
        "horizon": horizon,
    }

    # 计算整体 IC
    all_scores = []
    all_returns = []
    for c in all_candidates:
        code = c.get("code", "")
        score = c.get("factor_composite_shadow_score")
        if score is not None and code in all_forward_returns:
            all_scores.append(_safe_float(score))
            all_returns.append(all_forward_returns[code])

    overall_ic = calc_rank_ic(all_scores, all_returns) if all_scores else None

    return {
        "summary": summary,
        "overall_ic": overall_ic,
        "daily_results": daily_results,
        "bucket_diagnosis": bucket_diagnosis,
        "factor_diagnosis": factor_diagnosis,
        "spread_diagnosis": spread_diagnosis,
        "direction_issues": direction_issues,
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
    lines.append("# Factor Composite Shadow Score 负 IC 诊断报告\n")

    # 运行摘要
    summary = diagnosis["summary"]
    lines.append("## 运行摘要\n")
    lines.append(f"- 评估区间: {summary['start_date']} ~ {summary['end_date']}")
    lines.append(f"- 总天数: {summary['total_dates']}")
    lines.append(f"- 有 forward return 的天数: {summary['dates_with_returns']}")
    lines.append(f"- 总候选股数: {summary['total_candidates']}")
    lines.append(f"- Horizon: {summary['horizon']}")
    lines.append(f"- 整体 Rank IC: {diagnosis['overall_ic']:.4f}" if diagnosis['overall_ic'] is not None else "- 整体 Rank IC: N/A")
    lines.append("")

    # 日期级 IC 表
    lines.append("## 日期级 IC 表\n")
    lines.append("| 日期 | 样本数 | final_score IC | composite IC | composite Top5 Return |")
    lines.append("|------|--------|---------------|--------------|----------------------|")
    for dr in diagnosis["daily_results"]:
        date = dr["date"]
        count = dr["candidate_count"]
        final_ic = dr["scores"].get("final_score", {}).get("rank_ic")
        composite_ic = dr["scores"].get("factor_composite_shadow_score", {}).get("rank_ic")
        top5_ret = dr["scores"].get("factor_composite_shadow_score", {}).get("top5_avg_return")

        final_ic_str = f"{final_ic:.4f}" if final_ic is not None else "N/A"
        composite_ic_str = f"{composite_ic:.4f}" if composite_ic is not None else "N/A"
        top5_ret_str = f"{top5_ret:.4f}%" if top5_ret is not None else "N/A"

        lines.append(f"| {date} | {count} | {final_ic_str} | {composite_ic_str} | {top5_ret_str} |")
    lines.append("")

    # Bucket 级 IC 表
    lines.append("## Bucket 级 IC 表\n")
    lines.append("| Bucket | Rank IC | 样本数 | 与 composite 相关性 | 与 final 相关性 |")
    lines.append("|--------|---------|--------|-------------------|---------------|")
    for bucket_name, bucket_data in diagnosis["bucket_diagnosis"].get("buckets", {}).items():
        ic = bucket_data.get("rank_ic")
        count = bucket_data.get("sample_count", 0)
        corr_composite = bucket_data.get("correlation_with_composite")
        corr_final = bucket_data.get("correlation_with_final")

        ic_str = f"{ic:.4f}" if ic is not None else "N/A"
        corr_c_str = f"{corr_composite:.4f}" if corr_composite is not None else "N/A"
        corr_f_str = f"{corr_final:.4f}" if corr_final is not None else "N/A"

        lines.append(f"| {bucket_name} | {ic_str} | {count} | {corr_c_str} | {corr_f_str} |")
    lines.append("")

    # Factor 级 IC 表
    lines.append("## Factor 级 IC 表\n")
    lines.append("| Factor | Rank IC | 样本数 | 与 composite 相关性 | 与 final 相关性 |")
    lines.append("|--------|---------|--------|-------------------|---------------|")
    for factor_id, factor_data in diagnosis["factor_diagnosis"].get("factors", {}).items():
        ic = factor_data.get("rank_ic")
        count = factor_data.get("sample_count", 0)
        corr_composite = factor_data.get("correlation_with_composite")
        corr_final = factor_data.get("correlation_with_final")

        ic_str = f"{ic:.4f}" if ic is not None else "N/A"
        corr_c_str = f"{corr_composite:.4f}" if corr_composite is not None else "N/A"
        corr_f_str = f"{corr_final:.4f}" if corr_final is not None else "N/A"

        lines.append(f"| {factor_id} | {ic_str} | {count} | {corr_c_str} | {corr_f_str} |")
    lines.append("")

    # Top/Bottom Spread
    spread = diagnosis["spread_diagnosis"]
    lines.append("## Top/Bottom Spread\n")
    lines.append(f"- Top{spread['top_n']} 平均收益: {spread['top_avg_return']:.4f}%" if spread['top_avg_return'] is not None else "- Top5 平均收益: N/A")
    lines.append(f"- Bottom{spread['top_n']} 平均收益: {spread['bottom_avg_return']:.4f}%" if spread['bottom_avg_return'] is not None else "- Bottom5 平均收益: N/A")
    lines.append(f"- Spread: {spread['spread']:.4f}%" if spread['spread'] is not None else "- Spread: N/A")
    lines.append(f"- Signal Inverted: {'是' if spread['inverted_signal'] else '否'}")
    lines.append("")

    # 可能的负 IC 原因
    lines.append("## 可能的负 IC 原因\n")
    issues = diagnosis["direction_issues"].get("issues", [])
    if issues:
        for issue in issues:
            lines.append(f"- ⚠️ {issue}")
    else:
        lines.append("- 未发现明显的方向错误")
    lines.append("")

    # 建议
    lines.append("## 建议\n")
    overall_ic = diagnosis.get("overall_ic")

    lines.append("### a. 保持 shadow-only\n")
    if overall_ic is not None and overall_ic < -0.1:
        lines.append("- **强烈建议**: 当前 IC 为负且较强，应保持 shadow-only 状态")
    elif overall_ic is not None and overall_ic < 0:
        lines.append("- **建议**: 当前 IC 为负，建议保持 shadow-only 状态")
    else:
        lines.append("- 当前 IC 为正，可考虑进一步验证")
    lines.append("")

    lines.append("### b. 暂不进入 display_score\n")
    if overall_ic is not None and overall_ic < 0:
        lines.append("- **确认**: 暂不进入 display_score")
    else:
        lines.append("- 可考虑进一步验证后进入")
    lines.append("")

    lines.append("### c. 是否需要反向某些 bucket\n")
    direction_issues = diagnosis["direction_issues"]
    if direction_issues.get("risk_bucket_reversed"):
        lines.append("- ⚠️ risk_bucket 可能需要调整方向")
    if direction_issues.get("contraction_reversed"):
        lines.append("- ⚠️ contraction_score 可能需要调整方向")
    if not any([direction_issues.get("risk_bucket_reversed"), direction_issues.get("contraction_reversed")]):
        lines.append("- 当前 bucket 方向看起来合理")
    lines.append("")

    lines.append("### d. 是否需要降低趋势/动量/量能权重\n")
    if direction_issues.get("near_high_crowded") or direction_issues.get("amount_ratio_crowded"):
        lines.append("- ⚠️ 趋势/动量/量能因子可能需要降低权重")
    else:
        lines.append("- 当前权重看起来合理")
    lines.append("")

    lines.append("### e. 是否需要增加过热/拥挤惩罚\n")
    if direction_issues.get("short_score_overheated"):
        lines.append("- ⚠️ 建议增加过热/拥挤惩罚")
    else:
        lines.append("- 当前过热惩罚看起来合理")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Diagnose Factor Composite Shadow Score Negative IC"
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

    print(f"  Diagnosing Factor Composite Shadow Score Negative IC...")
    print(f"  Period: {args.start} ~ {args.end}")
    print(f"  Horizon: {args.horizon}")

    # 运行诊断
    diagnosis = run_diagnosis(
        start_date=args.start,
        end_date=args.end,
        candidate_root=candidate_root,
        forward_return_root=forward_return_root,
        horizon=args.horizon,
    )

    # 生成报告
    filename = f"negative_ic_diagnosis_{args.start}_{args.end}"
    json_path = output_dir / f"{filename}.json"
    md_path = output_dir / f"{filename}.md"

    generate_json_report(diagnosis, json_path)
    generate_markdown_report(diagnosis, md_path)

    print(f"\n  ✅ Diagnosis complete")
    print(f"  📊 Overall IC: {diagnosis['overall_ic']:.4f}" if diagnosis['overall_ic'] is not None else "  📊 Overall IC: N/A")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")


if __name__ == "__main__":
    main()
