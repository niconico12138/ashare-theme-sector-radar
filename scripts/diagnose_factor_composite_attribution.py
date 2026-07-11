#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Factor Composite Attribution 诊断脚本

基于长区间样本诊断 factor_composite_shadow_score 的 bucket / factor 贡献，
判断是否需要设计 v2。

用法:
  python scripts/diagnose_factor_composite_attribution.py --start 2026-04-01 --end 2026-07-10 --horizon 1d
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
# Bucket Analysis
# ============================================================

def analyze_bucket_distribution(
    candidates: list[dict],
    bucket_name: str,
) -> dict:
    """分析 bucket 分布。"""
    scores = []
    for c in candidates:
        breakdown = c.get("factor_composite_breakdown", {})
        bucket_data = breakdown.get(bucket_name, {})
        score = bucket_data.get("score")
        if score is not None:
            scores.append(_safe_float(score))

    if not scores:
        return {
            "coverage": 0,
            "missing_rate": 100,
            "non_neutral_rate": 0,
            "std": 0,
            "min": 0,
            "max": 0,
            "mean": 50,
            "median": 50,
            "is_constant": True,
            "sample_count": 0,
        }

    non_neutral = sum(1 for s in scores if abs(s - 50) > 0.1)
    non_neutral_rate = non_neutral / len(scores) * 100 if scores else 0

    return {
        "coverage": len(scores) / len(candidates) * 100 if candidates else 0,
        "missing_rate": (len(candidates) - len(scores)) / len(candidates) * 100 if candidates else 100,
        "non_neutral_rate": non_neutral_rate,
        "std": round(calc_std(scores), 2),
        "min": round(min(scores), 2),
        "max": round(max(scores), 2),
        "mean": round(calc_mean(scores), 2),
        "median": round(calc_median(scores), 2),
        "is_constant": calc_std(scores) < 0.1,
        "sample_count": len(scores),
    }


def analyze_bucket_ic(
    candidates: list[dict],
    forward_returns: dict[str, float],
    bucket_name: str,
) -> dict:
    """分析 bucket 预测力。"""
    scores_by_date: dict[str, list[float]] = {}
    returns_by_date: dict[str, list[float]] = {}

    # 按日期分组
    for c in candidates:
        code = c.get("code", "")
        as_of = c.get("as_of", "")
        breakdown = c.get("factor_composite_breakdown", {})
        bucket_data = breakdown.get(bucket_name, {})
        score = bucket_data.get("score")

        if score is None or code not in forward_returns or not as_of:
            continue

        if as_of not in scores_by_date:
            scores_by_date[as_of] = []
            returns_by_date[as_of] = []

        scores_by_date[as_of].append(_safe_float(score))
        returns_by_date[as_of].append(forward_returns[code])

    # 计算每天的 IC
    daily_ics = []
    for date in scores_by_date:
        ic = calc_rank_ic(scores_by_date[date], returns_by_date[date])
        if ic is not None:
            daily_ics.append(ic)

    if not daily_ics:
        return {
            "overall_ic": None,
            "daily_ic_mean": None,
            "daily_ic_median": None,
            "positive_ic_days": 0,
            "negative_ic_days": 0,
            "ic_win_rate": None,
            "sample_days": 0,
        }

    positive_days = sum(1 for ic in daily_ics if ic > 0)
    negative_days = sum(1 for ic in daily_ics if ic < 0)

    return {
        "overall_ic": round(calc_mean(daily_ics), 4),
        "daily_ic_mean": round(calc_mean(daily_ics), 4),
        "daily_ic_median": round(calc_median(daily_ics), 4),
        "positive_ic_days": positive_days,
        "negative_ic_days": negative_days,
        "ic_win_rate": round(positive_days / len(daily_ics) * 100, 2) if daily_ics else None,
        "sample_days": len(daily_ics),
    }


def analyze_bucket_spread(
    candidates: list[dict],
    forward_returns: dict[str, float],
    bucket_name: str,
    n: int = 5,
) -> dict:
    """分析 bucket Top/Bottom spread。"""
    pairs = []
    for c in candidates:
        code = c.get("code", "")
        breakdown = c.get("factor_composite_breakdown", {})
        bucket_data = breakdown.get(bucket_name, {})
        score = bucket_data.get("score")

        if score is not None and code in forward_returns:
            pairs.append({
                "code": code,
                "score": _safe_float(score),
                "return": forward_returns[code],
            })

    if len(pairs) < n * 2:
        return {
            "top_n": n,
            "top_avg_return": None,
            "bottom_avg_return": None,
            "spread": None,
            "sample_count": len(pairs),
        }

    pairs_sorted = sorted(pairs, key=lambda x: x["score"], reverse=True)
    top = pairs_sorted[:n]
    bottom = pairs_sorted[-n:]

    top_avg = calc_mean([p["return"] for p in top])
    bottom_avg = calc_mean([p["return"] for p in bottom])

    return {
        "top_n": n,
        "top_avg_return": round(top_avg, 4),
        "bottom_avg_return": round(bottom_avg, 4),
        "spread": round(top_avg - bottom_avg, 4),
        "sample_count": len(pairs),
    }


# ============================================================
# Factor Analysis
# ============================================================

def analyze_factor_distribution(
    candidates: list[dict],
    factor_id: str,
) -> dict:
    """分析 factor 分布。"""
    scores = []
    for c in candidates:
        factor_snapshot = c.get("factor_snapshot", {})
        factors = factor_snapshot.get("factors", [])
        for f in factors:
            if f.get("factor_id") == factor_id and f.get("quality") != "missing":
                scores.append(_safe_float(f.get("score")))
                break

    if not scores:
        return {
            "coverage": 0,
            "missing_rate": 100,
            "non_neutral_rate": 0,
            "std": 0,
            "min": 0,
            "max": 0,
            "mean": 50,
            "median": 50,
            "is_constant": True,
            "sample_count": 0,
        }

    non_neutral = sum(1 for s in scores if abs(s - 50) > 0.1)
    non_neutral_rate = non_neutral / len(scores) * 100 if scores else 0

    return {
        "coverage": len(scores) / len(candidates) * 100 if candidates else 0,
        "missing_rate": (len(candidates) - len(scores)) / len(candidates) * 100 if candidates else 100,
        "non_neutral_rate": non_neutral_rate,
        "std": round(calc_std(scores), 2),
        "min": round(min(scores), 2),
        "max": round(max(scores), 2),
        "mean": round(calc_mean(scores), 2),
        "median": round(calc_median(scores), 2),
        "is_constant": calc_std(scores) < 0.1,
        "sample_count": len(scores),
    }


def analyze_factor_ic(
    candidates: list[dict],
    forward_returns: dict[str, float],
    factor_id: str,
) -> dict:
    """分析 factor 预测力。"""
    scores_by_date: dict[str, list[float]] = {}
    returns_by_date: dict[str, list[float]] = {}

    for c in candidates:
        code = c.get("code", "")
        as_of = c.get("as_of", "")
        factor_snapshot = c.get("factor_snapshot", {})
        factors = factor_snapshot.get("factors", [])

        factor_score = None
        for f in factors:
            if f.get("factor_id") == factor_id and f.get("quality") != "missing":
                factor_score = f.get("score")
                break

        if factor_score is None or code not in forward_returns or not as_of:
            continue

        if as_of not in scores_by_date:
            scores_by_date[as_of] = []
            returns_by_date[as_of] = []

        scores_by_date[as_of].append(_safe_float(factor_score))
        returns_by_date[as_of].append(forward_returns[code])

    daily_ics = []
    for date in scores_by_date:
        ic = calc_rank_ic(scores_by_date[date], returns_by_date[date])
        if ic is not None:
            daily_ics.append(ic)

    if not daily_ics:
        return {
            "overall_ic": None,
            "daily_ic_mean": None,
            "daily_ic_median": None,
            "positive_ic_days": 0,
            "negative_ic_days": 0,
            "ic_win_rate": None,
            "sample_days": 0,
        }

    positive_days = sum(1 for ic in daily_ics if ic > 0)
    negative_days = sum(1 for ic in daily_ics if ic < 0)

    return {
        "overall_ic": round(calc_mean(daily_ics), 4),
        "daily_ic_mean": round(calc_mean(daily_ics), 4),
        "daily_ic_median": round(calc_median(daily_ics), 4),
        "positive_ic_days": positive_days,
        "negative_ic_days": negative_days,
        "ic_win_rate": round(positive_days / len(daily_ics) * 100, 2) if daily_ics else None,
        "sample_days": len(daily_ics),
    }


def analyze_factor_spread(
    candidates: list[dict],
    forward_returns: dict[str, float],
    factor_id: str,
    n: int = 5,
) -> dict:
    """分析 factor Top/Bottom spread。"""
    pairs = []
    for c in candidates:
        code = c.get("code", "")
        factor_snapshot = c.get("factor_snapshot", {})
        factors = factor_snapshot.get("factors", [])

        factor_score = None
        for f in factors:
            if f.get("factor_id") == factor_id and f.get("quality") != "missing":
                factor_score = f.get("score")
                break

        if factor_score is not None and code in forward_returns:
            pairs.append({
                "code": code,
                "score": _safe_float(factor_score),
                "return": forward_returns[code],
            })

    if len(pairs) < n * 2:
        return {
            "top_n": n,
            "top_avg_return": None,
            "bottom_avg_return": None,
            "spread": None,
            "sample_count": len(pairs),
        }

    pairs_sorted = sorted(pairs, key=lambda x: x["score"], reverse=True)
    top = pairs_sorted[:n]
    bottom = pairs_sorted[-n:]

    top_avg = calc_mean([p["return"] for p in top])
    bottom_avg = calc_mean([p["return"] for p in bottom])

    return {
        "top_n": n,
        "top_avg_return": round(top_avg, 4),
        "bottom_avg_return": round(bottom_avg, 4),
        "spread": round(top_avg - bottom_avg, 4),
        "sample_count": len(pairs),
    }


# ============================================================
# Composite Structure Analysis
# ============================================================

def analyze_composite_structure(
    candidates: list[dict],
) -> dict:
    """分析 composite 结构。"""
    bucket_names = ["trend", "momentum", "volatility", "sector", "risk", "agent"]

    # 提取 composite 和各 bucket 分数
    composite_scores = []
    bucket_scores = {name: [] for name in bucket_names}

    for c in candidates:
        composite = c.get("factor_composite_shadow_score")
        if composite is None:
            continue

        composite_scores.append(_safe_float(composite))
        breakdown = c.get("factor_composite_breakdown", {})

        for name in bucket_names:
            bucket_data = breakdown.get(name, {})
            score = bucket_data.get("score")
            bucket_scores[name].append(_safe_float(score) if score is not None else None)

    # 计算相关性
    correlations = {}
    dominant_bucket = None
    max_corr = 0

    for name in bucket_names:
        valid_pairs = [(c, b) for c, b in zip(composite_scores, bucket_scores[name]) if b is not None]
        if len(valid_pairs) >= 3:
            comp_vals, buck_vals = zip(*valid_pairs)
            corr = calc_correlation(list(comp_vals), list(buck_vals))
            correlations[name] = corr
            if corr is not None and abs(corr) > abs(max_corr):
                max_corr = corr
                dominant_bucket = name
        else:
            correlations[name] = None

    # 检查恒定 bucket
    constant_buckets = []
    for name in bucket_names:
        valid_scores = [s for s in bucket_scores[name] if s is not None]
        if valid_scores and calc_std(valid_scores) < 0.1:
            constant_buckets.append(name)

    return {
        "correlations": correlations,
        "dominant_bucket": dominant_bucket,
        "dominant_correlation": round(max_corr, 4) if max_corr else None,
        "constant_buckets": constant_buckets,
        "composite_mean": round(calc_mean(composite_scores), 2) if composite_scores else None,
        "composite_std": round(calc_std(composite_scores), 2) if composite_scores else None,
    }


# ============================================================
# V2 Proposal Generation
# ============================================================

def generate_v2_proposals(
    bucket_analysis: dict,
    factor_analysis: dict,
    composite_structure: dict,
) -> list[dict]:
    """生成 v2 候选方案。"""
    proposals = []

    # v2_defensive: 增加 risk 权重
    proposals.append({
        "name": "v2_defensive",
        "description": "增加 risk/drawdown 权重，降低 trend 主导",
        "weights": {
            "trend": 0.20,
            "momentum": 0.10,
            "volatility": 0.10,
            "sector": 0.10,
            "risk": 0.35,
            "agent": 0.00,
            "residual": 0.15,
        },
        "rationale": "risk_bucket 有正向 IC，增加其权重可能改善整体表现",
    })

    # v2_decorrelated: 降低与 final_score 高相关 bucket
    proposals.append({
        "name": "v2_decorrelated",
        "description": "降低与 final_score 高相关 bucket，提高低相关且 IC 较好的 factor",
        "weights": {
            "trend": 0.15,
            "momentum": 0.15,
            "volatility": 0.15,
            "sector": 0.15,
            "risk": 0.30,
            "agent": 0.00,
            "residual": 0.10,
        },
        "rationale": "与 final_score 高相关 bucket 增量信息有限，需要降低其权重",
    })

    # v2_no_dead_buckets: 只使用有效 bucket
    proposals.append({
        "name": "v2_no_dead_buckets",
        "description": "只使用 coverage >= 50%、std > 1、非中性率 >= 30% 的 bucket",
        "weights": {
            "trend": 0.25,
            "momentum": 0.00,
            "volatility": 0.00,
            "sector": 0.00,
            "risk": 0.50,
            "agent": 0.00,
            "residual": 0.25,
        },
        "rationale": "剔除恒定或接近恒定的 bucket，重新归一化权重",
    })

    return proposals


# ============================================================
# Main Attribution
# ============================================================

def run_attribution(
    start_date: str,
    end_date: str,
    candidate_root: Path,
    forward_return_root: Path,
    horizon: str = "1d",
    min_samples: int = 20,
) -> dict:
    """运行归因分析。"""
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
    dates_with_returns = []

    for date in dates:
        candidates = load_candidates(date, candidate_root)
        forward_returns = load_forward_returns(date, forward_return_root, horizon)

        if candidates and forward_returns:
            # 为每个 candidate 添加 as_of 日期
            for c in candidates:
                c["as_of"] = date

            all_candidates.extend(candidates)
            all_forward_returns.update(forward_returns)
            dates_with_returns.append(date)

    # Bucket 分析
    bucket_names = ["trend", "momentum", "volatility", "sector", "risk", "agent"]
    bucket_analysis = {}

    for name in bucket_names:
        distribution = analyze_bucket_distribution(all_candidates, name)
        ic_analysis = analyze_bucket_ic(all_candidates, all_forward_returns, name)
        spread_analysis = analyze_bucket_spread(all_candidates, all_forward_returns, name)

        # 计算与 composite/final 的相关性
        composite_scores = []
        final_scores = []
        bucket_scores = []

        for c in all_candidates:
            composite = c.get("factor_composite_shadow_score")
            final = c.get("final_score")
            breakdown = c.get("factor_composite_breakdown", {})
            bucket_data = breakdown.get(name, {})
            score = bucket_data.get("score")

            if composite is not None and final is not None and score is not None:
                composite_scores.append(_safe_float(composite))
                final_scores.append(_safe_float(final))
                bucket_scores.append(_safe_float(score))

        corr_composite = calc_correlation(bucket_scores, composite_scores) if len(composite_scores) >= 3 else None
        corr_final = calc_correlation(bucket_scores, final_scores) if len(final_scores) >= 3 else None

        bucket_analysis[name] = {
            "distribution": distribution,
            "ic": ic_analysis,
            "spread": spread_analysis,
            "correlation_with_composite": round(corr_composite, 4) if corr_composite is not None else None,
            "correlation_with_final": round(corr_final, 4) if corr_final is not None else None,
        }

    # Factor 分析
    factor_ids = [
        "ma20_slope_5", "near_high_250", "stock_trend_score",
        "stock_short_score", "stock_short_score_v2", "amount_ratio_20",
        "contraction_score", "atr10_atr50", "range10_range20", "range20_range60",
        "sector_trend_score", "sector_burst_score",
        "drawdown_risk_score", "risk_penalty_score",
        "regime_router_shadow_score_v5", "agent_score",
    ]

    factor_analysis = {}

    for factor_id in factor_ids:
        distribution = analyze_factor_distribution(all_candidates, factor_id)
        ic_analysis = analyze_factor_ic(all_candidates, all_forward_returns, factor_id)
        spread_analysis = analyze_factor_spread(all_candidates, all_forward_returns, factor_id)

        # 计算与 composite/final 的相关性
        composite_scores = []
        final_scores = []
        factor_scores = []

        for c in all_candidates:
            composite = c.get("factor_composite_shadow_score")
            final = c.get("final_score")
            factor_snapshot = c.get("factor_snapshot", {})
            factors = factor_snapshot.get("factors", [])

            factor_score = None
            for f in factors:
                if f.get("factor_id") == factor_id and f.get("quality") != "missing":
                    factor_score = f.get("score")
                    break

            if composite is not None and final is not None and factor_score is not None:
                composite_scores.append(_safe_float(composite))
                final_scores.append(_safe_float(final))
                factor_scores.append(_safe_float(factor_score))

        corr_composite = calc_correlation(factor_scores, composite_scores) if len(composite_scores) >= 3 else None
        corr_final = calc_correlation(factor_scores, final_scores) if len(final_scores) >= 3 else None

        factor_analysis[factor_id] = {
            "distribution": distribution,
            "ic": ic_analysis,
            "spread": spread_analysis,
            "correlation_with_composite": round(corr_composite, 4) if corr_composite is not None else None,
            "correlation_with_final": round(corr_final, 4) if corr_final is not None else None,
        }

    # Composite 结构分析
    composite_structure = analyze_composite_structure(all_candidates)

    # 生成 v2 方案
    v2_proposals = generate_v2_proposals(bucket_analysis, factor_analysis, composite_structure)

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

    # 计算 v2 整体 IC
    v2_scores = []
    v2_returns = []
    for c in all_candidates:
        code = c.get("code", "")
        score = c.get("factor_composite_shadow_score_v2")
        if score is not None and code in all_forward_returns:
            v2_scores.append(_safe_float(score))
            v2_returns.append(all_forward_returns[code])

    v2_overall_ic = calc_rank_ic(v2_scores, v2_returns) if v2_scores else None

    # 计算 final_score 整体 IC
    final_scores = []
    final_returns = []
    for c in all_candidates:
        code = c.get("code", "")
        score = c.get("final_score")
        if score is not None and code in all_forward_returns:
            final_scores.append(_safe_float(score))
            final_returns.append(all_forward_returns[code])

    final_overall_ic = calc_rank_ic(final_scores, final_returns) if final_scores else None

    # 计算 composite 与 final 的相关性
    composite_final_scores = []
    composite_final_finals = []
    for c in all_candidates:
        composite = c.get("factor_composite_shadow_score")
        final = c.get("final_score")
        if composite is not None and final is not None:
            composite_final_scores.append(_safe_float(composite))
            composite_final_finals.append(_safe_float(final))

    composite_final_corr = calc_correlation(composite_final_scores, composite_final_finals) if len(composite_final_scores) >= 3 else None

    # 计算 v2 与 final 的相关性
    v2_final_scores = []
    v2_final_finals = []
    for c in all_candidates:
        v2 = c.get("factor_composite_shadow_score_v2")
        final = c.get("final_score")
        if v2 is not None and final is not None:
            v2_final_scores.append(_safe_float(v2))
            v2_final_finals.append(_safe_float(final))

    v2_final_corr = calc_correlation(v2_final_scores, v2_final_finals) if len(v2_final_scores) >= 3 else None

    return {
        "summary": summary,
        "overall_ic": round(overall_ic, 4) if overall_ic is not None else None,
        "v2_overall_ic": round(v2_overall_ic, 4) if v2_overall_ic is not None else None,
        "final_overall_ic": round(final_overall_ic, 4) if final_overall_ic is not None else None,
        "composite_final_correlation": round(composite_final_corr, 4) if composite_final_corr is not None else None,
        "v2_final_correlation": round(v2_final_corr, 4) if v2_final_corr is not None else None,
        "bucket_analysis": bucket_analysis,
        "factor_analysis": factor_analysis,
        "composite_structure": composite_structure,
        "v2_proposals": v2_proposals,
    }


# ============================================================
# Report Generation
# ============================================================

def generate_json_report(attribution: dict, output_path: Path) -> None:
    """生成 JSON 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(attribution, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def generate_markdown_report(attribution: dict, output_path: Path) -> None:
    """生成 Markdown 报告。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append("# Factor Composite Attribution Report\n")

    # 运行摘要
    summary = attribution["summary"]
    lines.append("## 运行摘要\n")
    lines.append(f"- 评估区间: {summary['start_date']} ~ {summary['end_date']}")
    lines.append(f"- 总天数: {summary['total_dates']}")
    lines.append(f"- 有 forward return 的天数: {summary['dates_with_returns']}")
    lines.append(f"- 总候选股数: {summary['total_candidates']}")
    lines.append(f"- Horizon: {summary['horizon']}")
    lines.append(f"- composite Rank IC: {attribution['overall_ic']}" if attribution.get("overall_ic") is not None else "- composite Rank IC: N/A")
    lines.append(f"- composite_v2 Rank IC: {attribution['v2_overall_ic']}" if attribution.get("v2_overall_ic") is not None else "- composite_v2 Rank IC: N/A")
    lines.append(f"- final_score Rank IC: {attribution['final_overall_ic']}" if attribution.get("final_overall_ic") is not None else "- final_score Rank IC: N/A")
    lines.append(f"- composite vs final 相关性: {attribution['composite_final_correlation']}" if attribution.get("composite_final_correlation") is not None else "- composite vs final 相关性: N/A")
    lines.append(f"- v2 vs final 相关性: {attribution['v2_final_correlation']}" if attribution.get("v2_final_correlation") is not None else "- v2 vs final 相关性: N/A")
    lines.append("")

    # 数据覆盖率
    lines.append("## 数据覆盖率\n")
    lines.append("| Bucket | Coverage | Missing Rate | Non-Neutral Rate | Std | Is Constant |")
    lines.append("|--------|----------|--------------|------------------|-----|-------------|")
    for name, data in attribution["bucket_analysis"].items():
        dist = data["distribution"]
        lines.append(f"| {name} | {dist['coverage']:.1f}% | {dist['missing_rate']:.1f}% | {dist['non_neutral_rate']:.1f}% | {dist['std']:.2f} | {'是' if dist['is_constant'] else '否'} |")
    lines.append("")

    # Bucket Rank IC 与 Top/Bottom
    lines.append("## Bucket Rank IC 与 Top/Bottom\n")
    lines.append("| Bucket | Overall IC | IC Win Rate | Top5 Return | Bottom5 Return | Spread |")
    lines.append("|--------|-----------|-------------|-------------|----------------|--------|")
    for name, data in attribution["bucket_analysis"].items():
        ic = data["ic"]
        spread = data["spread"]
        ic_str = f"{ic['overall_ic']:.4f}" if ic['overall_ic'] is not None else "N/A"
        win_rate = f"{ic['ic_win_rate']:.1f}%" if ic['ic_win_rate'] is not None else "N/A"
        top5 = f"{spread['top_avg_return']:.4f}%" if spread['top_avg_return'] is not None else "N/A"
        bottom5 = f"{spread['bottom_avg_return']:.4f}%" if spread['bottom_avg_return'] is not None else "N/A"
        spread_val = f"{spread['spread']:.4f}%" if spread['spread'] is not None else "N/A"
        lines.append(f"| {name} | {ic_str} | {win_rate} | {top5} | {bottom5} | {spread_val} |")
    lines.append("")

    # Factor 分布与有效性
    lines.append("## Factor 分布与有效性\n")
    lines.append("| Factor | Coverage | Non-Neutral Rate | Std | Is Constant |")
    lines.append("|--------|----------|------------------|-----|-------------|")
    for name, data in attribution["factor_analysis"].items():
        dist = data["distribution"]
        lines.append(f"| {name} | {dist['coverage']:.1f}% | {dist['non_neutral_rate']:.1f}% | {dist['std']:.2f} | {'是' if dist['is_constant'] else '否'} |")
    lines.append("")

    # Factor Rank IC 与 Top/Bottom
    lines.append("## Factor Rank IC 与 Top/Bottom\n")
    lines.append("| Factor | Overall IC | IC Win Rate | Top5 Return | Bottom5 Return | Spread |")
    lines.append("|--------|-----------|-------------|-------------|----------------|--------|")
    for name, data in attribution["factor_analysis"].items():
        ic = data["ic"]
        spread = data["spread"]
        ic_str = f"{ic['overall_ic']:.4f}" if ic['overall_ic'] is not None else "N/A"
        win_rate = f"{ic['ic_win_rate']:.1f}%" if ic['ic_win_rate'] is not None else "N/A"
        top5 = f"{spread['top_avg_return']:.4f}%" if spread['top_avg_return'] is not None else "N/A"
        bottom5 = f"{spread['bottom_avg_return']:.4f}%" if spread['bottom_avg_return'] is not None else "N/A"
        spread_val = f"{spread['spread']:.4f}%" if spread['spread'] is not None else "N/A"
        lines.append(f"| {name} | {ic_str} | {win_rate} | {top5} | {bottom5} | {spread_val} |")
    lines.append("")

    # Composite 结构诊断
    lines.append("## Composite 结构诊断\n")
    structure = attribution["composite_structure"]
    lines.append(f"- Composite 均值: {structure['composite_mean']}")
    lines.append(f"- Composite 标准差: {structure['composite_std']}")
    lines.append(f"- 主导 bucket: {structure['dominant_bucket']} (相关性: {structure['dominant_correlation']})")
    lines.append(f"- 恒定 bucket: {', '.join(structure['constant_buckets']) if structure['constant_buckets'] else '无'}")
    lines.append("")

    # v2 候选方案
    lines.append("## v2 候选方案\n")
    for proposal in attribution["v2_proposals"]:
        lines.append(f"### {proposal['name']}\n")
        lines.append(f"- 描述: {proposal['description']}")
        lines.append(f"- 权重: {json.dumps(proposal['weights'], ensure_ascii=False)}")
        lines.append(f"- 理由: {proposal['rationale']}")
        lines.append("")

    # 结论与建议
    lines.append("## 结论与建议\n")
    overall_ic = attribution.get("overall_ic")
    composite_final_corr = attribution.get("composite_final_correlation")

    lines.append("### 是否继续保留 v1\n")
    if overall_ic is not None and overall_ic > 0.01:
        lines.append("- **建议保留**: composite 有正向预测能力")
    elif overall_ic is not None and overall_ic > -0.01:
        lines.append("- **可考虑保留**: composite 预测能力接近中性")
    else:
        lines.append("- **建议优化**: composite 预测能力为负")
    lines.append("")

    lines.append("### 是否仍 shadow-only\n")
    lines.append("- **确认**: 应继续 shadow-only 状态")
    lines.append("")

    lines.append("### 是否建议进入 display_score\n")
    if overall_ic is not None and overall_ic > 0.05 and composite_final_corr is not None and composite_final_corr < 0.7:
        lines.append("- **可考虑**: 当 IC 较好且与 final_score 相关性较低时")
    else:
        lines.append("- **暂不建议**: 建议继续 shadow-only 验证")
    lines.append("")

    lines.append("### 是否建议做 v2\n")
    if overall_ic is not None and overall_ic < 0.01:
        lines.append("- **建议做 v2**: 当前 v1 预测力不足，需要优化")
    else:
        lines.append("- **可暂缓**: 当前 v1 仍有一定预测力")
    lines.append("")

    lines.append("### v2 应优先解决的问题\n")
    issues = []
    if structure.get("constant_buckets"):
        issues.append("1. 去除恒定 bucket")
    if structure.get("dominant_correlation") and structure["dominant_correlation"] > 0.8:
        issues.append("2. 降低 trend 主导")
    if attribution["bucket_analysis"].get("risk", {}).get("ic", {}).get("overall_ic", 0) > 0:
        issues.append("3. 提高 risk/drawdown 权重")
    if composite_final_corr and composite_final_corr > 0.8:
        issues.append("4. 降低与 final_score 的相关性")
    if not issues:
        issues.append("- 当前无需紧急优化")
    for issue in issues:
        lines.append(f"- {issue}")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Factor Composite Attribution Analysis"
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
        "--min-samples",
        type=int,
        default=20,
        help="Minimum samples for IC calculation",
    )
    args = parser.parse_args()

    candidate_root = Path(args.candidate_root)
    forward_return_root = Path(args.forward_return_root)
    output_dir = Path(args.output_dir)

    print(f"  Running Factor Composite Attribution Analysis...")
    print(f"  Period: {args.start} ~ {args.end}")
    print(f"  Horizon: {args.horizon}")

    # 运行归因分析
    attribution = run_attribution(
        start_date=args.start,
        end_date=args.end,
        candidate_root=candidate_root,
        forward_return_root=forward_return_root,
        horizon=args.horizon,
        min_samples=args.min_samples,
    )

    # 生成报告
    filename = f"attribution_{args.start}_{args.end}"
    json_path = output_dir / f"{filename}.json"
    md_path = output_dir / f"{filename}.md"

    generate_json_report(attribution, json_path)
    generate_markdown_report(attribution, md_path)

    print(f"\n  ✅ Attribution analysis complete")
    print(f"  📊 Overall IC: {attribution['overall_ic']}" if attribution['overall_ic'] is not None else "  📊 Overall IC: N/A")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")


if __name__ == "__main__":
    main()
