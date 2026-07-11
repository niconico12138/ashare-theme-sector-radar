#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Enhanced Factors 历史有效性测试

对新增个股因子做历史有效性测试，判断它们的使用方式。
本阶段只做分析脚本与报告，不改变任何生产逻辑。

用法:
  python scripts/evaluate_stock_enhanced_factors.py --start 2026-04-01 --end 2026-07-10
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
# Constants
# ============================================================

FACTOR_IDS = [
    "liquidity_score",
    "chasing_risk_score",
    "drawdown_depth_20",
    "breakout_distance_20",
    "sector_support_score",
]

HORIZONS = ["1d", "3d", "5d", "10d"]

OPPORTUNITY_TYPES = [
    "v2_recovery",
    "trend_follow",
    "short_burst",
    "consensus_confirmed",
    "divergence_review",
    "blocked",
    "unknown",
]


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
    """加载 forward returns。"""
    # 新格式
    new_path = forward_return_root / f"{date}.json"
    if new_path.exists():
        try:
            data = json.loads(new_path.read_text(encoding="utf-8"))
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
            pass

    # 旧格式
    old_path = forward_return_root / date / "forward_returns.json"
    if old_path.exists():
        try:
            data = json.loads(old_path.read_text(encoding="utf-8"))
            returns = data.get("returns", {})
            if returns:
                return returns
        except Exception:
            pass

    return None


# ============================================================
# Factor Extraction
# ============================================================

def extract_factor_score(candidate: dict, factor_id: str) -> float | None:
    """从候选股中提取因子分数。"""
    # 优先从 candidate 直接字段读取
    direct_value = candidate.get(factor_id)
    if direct_value is not None:
        return _safe_float(direct_value)

    # 从 factor_snapshot 读取
    factor_snapshot = candidate.get("factor_snapshot", {})
    factors = factor_snapshot.get("factors", [])

    for f in factors:
        if f.get("factor_id") == factor_id:
            quality = f.get("quality", "missing")
            if quality == "missing":
                return None
            score = f.get("score")
            if score is not None:
                return _safe_float(score)
            raw_value = f.get("raw_value")
            if raw_value is not None:
                return _safe_float(raw_value)

    return None


def infer_opportunity_type(candidate: dict) -> str:
    """推断 opportunity_type。"""
    opportunity_type = candidate.get("opportunity_type")
    if opportunity_type:
        return opportunity_type

    selection_bucket = candidate.get("selection_bucket", "")
    source_pool = candidate.get("source_pool", "")
    signal_type = candidate.get("signal_type", "")

    if selection_bucket == "v2_opportunity" or signal_type == "low_final_high_v2":
        return "v2_recovery"
    elif selection_bucket == "core_watch":
        return "trend_follow"
    elif source_pool == "burst_top":
        return "short_burst"
    elif selection_bucket == "divergence_review":
        return "divergence_review"
    elif selection_bucket == "blocked":
        return "blocked"
    else:
        return "unknown"


# ============================================================
# Analysis
# ============================================================

def analyze_factor_for_horizon(
    factor_scores: list[float],
    forward_returns: list[float],
    min_samples: int = 30,
) -> dict:
    """分析单个因子在单个 horizon 的表现。"""
    n = len(factor_scores)

    if n < min_samples:
        return {
            "sample_count": n,
            "rank_ic": None,
            "insufficient_sample": True,
            "quintiles": None,
            "spread": None,
        }

    # Rank IC
    rank_ic = calc_rank_ic(factor_scores, forward_returns)

    # 分位数
    pairs = sorted(zip(factor_scores, forward_returns), key=lambda x: x[0])
    chunk_size = n // 5
    quintiles = []

    for i in range(5):
        start = i * chunk_size
        end = start + chunk_size if i < 4 else n
        chunk_returns = [r for _, r in pairs[start:end]]
        quintiles.append({
            "quintile": i + 1,
            "count": len(chunk_returns),
            "mean_return": round(calc_mean(chunk_returns), 4),
        })

    # Top/Bottom spread
    top20_size = max(1, n // 5)
    top20_returns = [r for _, r in pairs[-top20_size:]]
    bottom20_returns = [r for _, r in pairs[:top20_size]]

    top20_mean = calc_mean(top20_returns)
    bottom20_mean = calc_mean(bottom20_returns)
    spread = top20_mean - bottom20_mean

    return {
        "sample_count": n,
        "rank_ic": round(rank_ic, 4) if rank_ic is not None else None,
        "insufficient_sample": False,
        "quintiles": quintiles,
        "top20_mean": round(top20_mean, 4),
        "bottom20_mean": round(bottom20_mean, 4),
        "spread": round(spread, 4),
    }


def evaluate_factor(
    factor_id: str,
    candidates_by_date: dict[str, list[dict]],
    forward_returns_by_date: dict[str, dict[str, float]],
    horizons: list[str],
    min_samples: int = 30,
) -> dict:
    """评估单个因子。"""
    # 收集所有数据
    all_factor_scores: list[float] = []
    all_returns: dict[str, list[float]] = {h: [] for h in horizons}
    all_final_scores: list[float] = []
    all_v2_scores: list[float] = []

    # 按 opportunity_type 分组
    opp_type_data: dict[str, dict[str, list[tuple[float, float]]]] = {
        ot: {h: [] for h in horizons}
        for ot in OPPORTUNITY_TYPES
    }

    for date, candidates in candidates_by_date.items():
        forward_returns = forward_returns_by_date.get(date, {})

        for c in candidates:
            code = c.get("code", "")
            if code not in forward_returns:
                continue

            factor_score = extract_factor_score(c, factor_id)
            if factor_score is None:
                continue

            fr = forward_returns[code]
            opp_type = infer_opportunity_type(c)

            # 收集基础数据
            all_factor_scores.append(factor_score)
            all_final_scores.append(_safe_float(c.get("final_score")))
            all_v2_scores.append(_safe_float(c.get("factor_composite_shadow_score_v2")))

            for horizon in horizons:
                ret = fr.get(horizon)
                if ret is not None:
                    all_returns[horizon].append(ret)
                    opp_type_data[opp_type][horizon].append((factor_score, ret))

    # 统计分布
    distribution = {
        "min": round(min(all_factor_scores), 2) if all_factor_scores else None,
        "max": round(max(all_factor_scores), 2) if all_factor_scores else None,
        "mean": round(calc_mean(all_factor_scores), 2) if all_factor_scores else None,
        "median": round(calc_median(all_factor_scores), 2) if all_factor_scores else None,
        "std": round(calc_std(all_factor_scores), 2) if all_factor_scores else None,
    }

    # 分析每个 horizon
    horizon_results = {}
    for horizon in horizons:
        scores = []
        returns = []
        for factor_score, ret in zip(all_factor_scores, all_returns[horizon][:len(all_factor_scores)]):
            scores.append(factor_score)
            returns.append(ret)

        horizon_results[horizon] = analyze_factor_for_horizon(scores, returns, min_samples)

    # 与 final_score / v2_score 的相关性
    corr_final = calc_correlation(all_factor_scores, all_final_scores)
    corr_v2 = calc_correlation(all_factor_scores, all_v2_scores)

    # 按 opportunity_type 分析
    opp_type_results = {}
    for opp_type in OPPORTUNITY_TYPES:
        opp_data = opp_type_data[opp_type]
        total_samples = sum(len(v) for v in opp_data.values())

        if total_samples == 0:
            opp_type_results[opp_type] = {
                "sample_count": 0,
                "status": "no_data",
            }
            continue

        # 找最佳 horizon
        best_horizon = None
        best_ic = None
        for horizon in horizons:
            pairs = opp_data[horizon]
            if len(pairs) >= 10:
                scores = [p[0] for p in pairs]
                returns = [p[1] for p in pairs]
                ic = calc_rank_ic(scores, returns)
                if ic is not None and (best_ic is None or abs(ic) > abs(best_ic)):
                    best_ic = ic
                    best_horizon = horizon

        opp_type_results[opp_type] = {
            "sample_count": total_samples,
            "best_horizon": best_horizon,
            "best_ic": round(best_ic, 4) if best_ic is not None else None,
        }

    return {
        "coverage": {
            "total_candidates": sum(len(c) for c in candidates_by_date.values()),
            "valid_factor_count": len(all_factor_scores),
            "usable_sample_count": len(all_factor_scores),
            "coverage_rate": round(len(all_factor_scores) / sum(len(c) for c in candidates_by_date.values()) * 100, 2) if candidates_by_date else 0,
        },
        "distribution": distribution,
        "horizon_results": horizon_results,
        "opp_type_results": opp_type_results,
        "corr_with_final_score": round(corr_final, 4) if corr_final is not None else None,
        "corr_with_v2_score": round(corr_v2, 4) if corr_v2 is not None else None,
    }


def generate_recommendation(
    factor_id: str,
    factor_result: dict,
    min_samples: int = 30,
) -> dict:
    """生成因子建议。"""
    coverage = factor_result.get("coverage", {})
    valid_count = coverage.get("valid_factor_count", 0)

    # 样本不足
    if valid_count < min_samples:
        return {
            "factor_id": factor_id,
            "recommendation": "profile_only",
            "reason": f"样本不足 ({valid_count} < {min_samples})",
            "best_horizon": None,
            "best_opportunity_type": None,
        }

    # 分析各 horizon 的 IC
    horizon_results = factor_result.get("horizon_results", {})
    best_horizon = None
    best_ic = None

    for horizon, hr in horizon_results.items():
        ic = hr.get("rank_ic")
        if ic is not None and (best_ic is None or abs(ic) > abs(best_ic)):
            best_ic = ic
            best_horizon = horizon

    # 分析 opportunity_type 切片
    opp_type_results = factor_result.get("opp_type_results", {})
    best_opp_type = None
    best_opp_ic = None

    for opp_type, otr in opp_type_results.items():
        ic = otr.get("best_ic")
        if ic is not None and (best_opp_ic is None or abs(ic) > abs(best_opp_ic)):
            best_opp_ic = ic
            best_opp_type = opp_type

    # 生成建议
    if best_ic is None:
        recommendation = "profile_only"
        reason = "无法计算有效 IC"
    elif abs(best_ic) < 0.03:
        recommendation = "profile_only"
        reason = f"IC 较弱 ({best_ic:.4f})"
    elif abs(best_ic) < 0.08:
        recommendation = "profile_only"
        reason = f"IC 可观察但不强 ({best_ic:.4f})"
    else:
        # IC > 0.08
        if factor_id == "chasing_risk_score":
            # lower_is_better 因子
            if best_ic < 0:
                recommendation = "soft_warning"
                reason = f"高追高风险对应更差后续收益 (IC={best_ic:.4f})"
            else:
                recommendation = "profile_only"
                reason = f"追高风险与收益正相关，可能有动量效应 (IC={best_ic:.4f})"
        elif factor_id == "breakout_distance_20":
            if best_ic < 0:
                recommendation = "trigger_candidate"
                reason = f"距离突破近的组表现更好 (IC={best_ic:.4f})"
            else:
                recommendation = "profile_only"
                reason = f"突破距离与收益关系不明确 (IC={best_ic:.4f})"
        elif factor_id == "liquidity_score":
            if best_ic > 0:
                recommendation = "keep"
                reason = f"高流动性对应更好后续收益 (IC={best_ic:.4f})"
            else:
                recommendation = "soft_warning"
                reason = f"低流动性可能有风险 (IC={best_ic:.4f})"
        elif factor_id == "drawdown_depth_20":
            if best_ic < 0:
                recommendation = "soft_warning"
                reason = f"深回撤对应更差后续收益 (IC={best_ic:.4f})"
            else:
                recommendation = "profile_only"
                reason = f"回撤深度与收益关系不明确 (IC={best_ic:.4f})"
        elif factor_id == "sector_support_score":
            if best_ic > 0:
                recommendation = "keep"
                reason = f"板块支持对应更好后续收益 (IC={best_ic:.4f})"
            else:
                recommendation = "profile_only"
                reason = f"板块支持与收益关系不明确 (IC={best_ic:.4f})"
        else:
            recommendation = "profile_only"
            reason = f"需要进一步验证 (IC={best_ic:.4f})"

    return {
        "factor_id": factor_id,
        "recommendation": recommendation,
        "reason": reason,
        "best_horizon": best_horizon,
        "best_opportunity_type": best_opp_type,
    }


# ============================================================
# Main Evaluation
# ============================================================

def run_evaluation(
    start_date: str,
    end_date: str,
    candidate_root: Path,
    forward_return_root: Path,
    horizons: list[str],
    min_samples: int = 30,
) -> dict:
    """运行评估。"""
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

    # 评估每个因子
    factor_results = {}
    overall_recommendations = []

    for factor_id in FACTOR_IDS:
        factor_result = evaluate_factor(
            factor_id,
            candidates_by_date,
            forward_returns_by_date,
            horizons,
            min_samples,
        )
        factor_results[factor_id] = factor_result

        recommendation = generate_recommendation(factor_id, factor_result, min_samples)
        overall_recommendations.append(recommendation)

    # 汇总
    summary = {
        "total_days": len(dates),
        "evaluated_days": len(candidates_by_date),
        "total_candidates": sum(len(c) for c in candidates_by_date.values()),
        "usable_forward_return_candidates": sum(
            len(fr) for fr in forward_returns_by_date.values()
        ),
    }

    return {
        "schema_version": "1.0",
        "start": start_date,
        "end": end_date,
        "factor_ids": FACTOR_IDS,
        "horizons": horizons,
        "summary": summary,
        "factor_results": factor_results,
        "overall_recommendations": overall_recommendations,
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
    lines.append("# Stock Enhanced Factors Evaluation\n")

    # 运行摘要
    summary = evaluation["summary"]
    lines.append("## 运行摘要\n")
    lines.append(f"- 评估区间: {evaluation['start']} ~ {evaluation['end']}")
    lines.append(f"- 总天数: {summary['total_days']}")
    lines.append(f"- 有数据天数: {summary['evaluated_days']}")
    lines.append(f"- 总候选股数: {summary['total_candidates']}")
    lines.append(f"- 有效 forward return: {summary['usable_forward_return_candidates']}")
    lines.append("")

    # 因子覆盖率表
    lines.append("## 因子覆盖率\n")
    lines.append("| 因子 | 覆盖率 | 有效样本 | 分布均值 | 分布标准差 |")
    lines.append("|------|--------|----------|----------|------------|")
    for factor_id, result in evaluation["factor_results"].items():
        coverage = result["coverage"]
        dist = result["distribution"]
        lines.append(f"| {factor_id} | {coverage['coverage_rate']:.1f}% | {coverage['valid_factor_count']} | {dist.get('mean', 'N/A')} | {dist.get('std', 'N/A')} |")
    lines.append("")

    # 因子整体有效性表
    lines.append("## 因子整体有效性\n")
    lines.append("| 因子 | 最佳 Horizon | Rank IC | Top20 均值 | Bottom20 均值 | Spread | 与 final 相关性 | 与 v2 相关性 | 建议 |")
    lines.append("|------|-------------|---------|-----------|--------------|--------|----------------|-------------|------|")

    for rec in evaluation["overall_recommendations"]:
        factor_id = rec["factor_id"]
        result = evaluation["factor_results"].get(factor_id, {})
        best_horizon = rec.get("best_horizon", "N/A")

        # 找最佳 horizon 的 IC
        best_ic = None
        if best_horizon and best_horizon in result.get("horizon_results", {}):
            best_ic = result["horizon_results"][best_horizon].get("rank_ic")

        # 找最佳 horizon 的 spread
        best_spread = None
        if best_horizon and best_horizon in result.get("horizon_results", {}):
            best_spread = result["horizon_results"][best_horizon].get("spread")

        corr_final = result.get("corr_with_final_score", "N/A")
        corr_v2 = result.get("corr_with_v2_score", "N/A")

        ic_str = f"{best_ic:.4f}" if best_ic is not None else "N/A"
        spread_str = f"{best_spread:.4f}" if best_spread is not None else "N/A"
        corr_final_str = f"{corr_final:.4f}" if corr_final is not None else "N/A"
        corr_v2_str = f"{corr_v2:.4f}" if corr_v2 is not None else "N/A"

        lines.append(f"| {factor_id} | {best_horizon} | {ic_str} | N/A | N/A | {spread_str} | {corr_final_str} | {corr_v2_str} | {rec['recommendation']} |")
    lines.append("")

    # 每个因子的建议
    lines.append("## 因子建议\n")
    for rec in evaluation["overall_recommendations"]:
        lines.append(f"### {rec['factor_id']}\n")
        lines.append(f"- 建议: **{rec['recommendation']}**")
        lines.append(f"- 原因: {rec['reason']}")
        if rec.get("best_horizon"):
            lines.append(f"- 最佳 Horizon: {rec['best_horizon']}")
        if rec.get("best_opportunity_type"):
            lines.append(f"- 最佳 Opportunity Type: {rec['best_opportunity_type']}")
        lines.append("")

    # 下一步建议
    lines.append("## 下一步建议\n")
    lines.append("1. 保持 keep 因子在 factor_snapshot 中持续使用")
    lines.append("2. profile_only 因子仅用于 stock_profile / stock_explanation 解释")
    lines.append("3. soft_warning 因子作为风险提示，不进入正向打分")
    lines.append("4. trigger_candidate 因子未来可作为条件触发候选")
    lines.append("5. drop 因子暂不使用或后续重构")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Stock Enhanced Factors Evaluation"
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
        "--min-samples",
        type=int,
        default=30,
        help="Minimum samples for valid analysis",
    )
    args = parser.parse_args()

    candidate_root = Path(args.candidate_root)
    forward_return_root = Path(args.forward_return_root)
    output_dir = Path(args.output_dir)
    horizons = [f"{h.strip()}d" for h in args.horizons.split(",")]

    print(f"  Running Stock Enhanced Factors Evaluation...")
    print(f"  Period: {args.start} ~ {args.end}")
    print(f"  Horizons: {horizons}")

    # 运行评估
    evaluation = run_evaluation(
        start_date=args.start,
        end_date=args.end,
        candidate_root=candidate_root,
        forward_return_root=forward_return_root,
        horizons=horizons,
        min_samples=args.min_samples,
    )

    # 生成报告
    filename = f"stock_enhanced_factor_evaluation_{args.start}_{args.end}"
    json_path = output_dir / f"{filename}.json"
    md_path = output_dir / f"{filename}.md"

    generate_json_report(evaluation, json_path)
    generate_markdown_report(evaluation, md_path)

    print(f"\n  ✅ Evaluation complete")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")

    # 打印建议
    print(f"\n  📊 Recommendations:")
    for rec in evaluation["overall_recommendations"]:
        print(f"     {rec['factor_id']}: {rec['recommendation']} - {rec['reason']}")


if __name__ == "__main__":
    main()
