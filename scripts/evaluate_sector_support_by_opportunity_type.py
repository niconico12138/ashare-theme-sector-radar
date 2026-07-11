#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sector Support Score by Opportunity Type 评估脚本

验证 sector_support_score 在不同 opportunity_type 下的有效性，
输出 shadow policy 建议。

本阶段只做分析脚本、报告、shadow policy，不改变生产规则。

用法:
  python scripts/evaluate_sector_support_by_opportunity_type.py --start 2026-04-01 --end 2026-07-10
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

    return None


# ============================================================
# Field Extraction
# ============================================================

def extract_sector_support_score(candidate: dict) -> float | None:
    """提取 sector_support_score。"""
    # 优先从 candidate 直接字段读取
    score = candidate.get("sector_support_score")
    if score is not None and _safe_float(score) > 0:
        return _safe_float(score)

    # 从 factor_snapshot 读取
    factor_snapshot = candidate.get("factor_snapshot", {})
    factors = factor_snapshot.get("factors", [])
    for f in factors:
        if f.get("factor_id") == "sector_support_score":
            quality = f.get("quality", "missing")
            if quality == "missing":
                return None
            score = f.get("score")
            if score is not None and _safe_float(score) > 0:
                return _safe_float(score)

    # 从 sector_trend_score 和 sector_burst_score 计算
    sector_trend = candidate.get("sector_trend_score")
    sector_burst = candidate.get("sector_burst_score")

    trend_val = 0
    burst_val = 0

    if sector_trend is not None and _safe_float(sector_trend) > 0:
        trend_val = _safe_float(sector_trend)
    else:
        alt_trend = candidate.get("trend_score")
        if alt_trend is not None and _safe_float(alt_trend) > 0:
            trend_val = _safe_float(alt_trend)

    if sector_burst is not None and _safe_float(sector_burst) > 0:
        burst_val = _safe_float(sector_burst)
    else:
        alt_burst = candidate.get("burst_score")
        if alt_burst is not None and _safe_float(alt_burst) > 0:
            burst_val = _safe_float(alt_burst)

    if trend_val > 0 and burst_val > 0:
        return trend_val * 0.7 + burst_val * 0.3
    elif trend_val > 0:
        return trend_val
    elif burst_val > 0:
        return burst_val

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


def get_sector_support_state(score: float | None) -> str:
    """获取 sector_support 状态。"""
    if score is None:
        return "unknown"
    if score >= 65:
        return "strong"
    elif score >= 50:
        return "neutral"
    else:
        return "weak"


# ============================================================
# Analysis
# ============================================================

def analyze_sector_support_for_opportunity(
    samples: list[dict],
    horizons: list[str],
    min_samples: int = 30,
) -> dict:
    """分析单个 opportunity_type 下 sector_support_score 的表现。"""
    n = len(samples)

    if n < min_samples:
        return {
            "sample_count": n,
            "status": "insufficient_sample",
        }

    # 提取 sector_support_score
    scores = [s.get("sector_support_score") for s in samples if s.get("sector_support_score") is not None]
    if not scores:
        return {
            "sample_count": n,
            "status": "no_sector_support_score",
        }

    # 按 sector_support_state 分组
    strong_samples = [s for s in samples if s.get("sector_support_state") == "strong"]
    neutral_samples = [s for s in samples if s.get("sector_support_state") == "neutral"]
    weak_samples = [s for s in samples if s.get("sector_support_state") == "weak"]

    # 计算每个 horizon 的指标
    horizon_results = {}
    for horizon in horizons:
        # 收集 scores 和 returns
        all_scores = []
        all_returns = []
        strong_returns = []
        weak_returns = []

        for s in samples:
            score = s.get("sector_support_score")
            fr = s.get("forward_returns", {}).get(horizon)

            if score is not None and fr is not None:
                all_scores.append(_safe_float(score))
                all_returns.append(fr)

                state = s.get("sector_support_state", "unknown")
                if state == "strong":
                    strong_returns.append(fr)
                elif state == "weak":
                    weak_returns.append(fr)

        if len(all_scores) < 3:
            horizon_results[horizon] = {"status": "insufficient_sample"}
            continue

        # Rank IC
        rank_ic = calc_rank_ic(all_scores, all_returns)

        # strong vs weak spread
        strong_mean = calc_mean(strong_returns) if strong_returns else None
        weak_mean = calc_mean(weak_returns) if weak_returns else None
        strong_vs_weak_spread = None
        if strong_mean is not None and weak_mean is not None:
            strong_vs_weak_spread = strong_mean - weak_mean

        horizon_results[horizon] = {
            "sample_count": len(all_scores),
            "rank_ic": round(rank_ic, 4) if rank_ic is not None else None,
            "strong_mean": round(strong_mean, 4) if strong_mean is not None else None,
            "weak_mean": round(weak_mean, 4) if weak_mean is not None else None,
            "strong_vs_weak_spread": round(strong_vs_weak_spread, 4) if strong_vs_weak_spread is not None else None,
        }

    # 找最佳 horizon
    best_horizon = None
    best_ic = None
    for horizon, hr in horizon_results.items():
        if hr.get("rank_ic") is not None:
            if best_ic is None or abs(hr["rank_ic"]) > abs(best_ic):
                best_ic = hr["rank_ic"]
                best_horizon = horizon

    return {
        "sample_count": n,
        "status": "ok",
        "strong_count": len(strong_samples),
        "neutral_count": len(neutral_samples),
        "weak_count": len(weak_samples),
        "horizon_results": horizon_results,
        "best_horizon": best_horizon,
        "best_ic": round(best_ic, 4) if best_ic is not None else None,
    }


def generate_policy(
    opp_type: str,
    analysis: dict,
    min_samples: int = 30,
) -> dict:
    """生成策略建议。"""
    sample_count = analysis.get("sample_count", 0)
    best_ic = analysis.get("best_ic")
    best_horizon = analysis.get("best_horizon")

    # 找最佳 horizon 的 spread
    best_spread = None
    if best_horizon:
        hr = analysis.get("horizon_results", {}).get(best_horizon, {})
        best_spread = hr.get("strong_vs_weak_spread")

    # 生成 policy
    if sample_count < min_samples:
        policy = "insufficient_sample"
        reason = f"样本不足 ({sample_count} < {min_samples})"
    elif best_ic is not None and best_ic >= 0.05 and best_spread is not None and best_spread > 0:
        policy = "enable_adjustment"
        reason = f"sector_support_score 改善了 {best_horizon} 的 strong/weak 差异 (IC={best_ic:.4f}, spread={best_spread:.4f})"
    elif best_ic is not None and 0.02 <= best_ic < 0.05:
        policy = "display_only"
        reason = f"sector_support_score 有弱正向效果 (IC={best_ic:.4f})"
    elif best_ic is not None and best_ic < -0.03 and best_spread is not None and best_spread < 0:
        policy = "disable_adjustment"
        reason = f"sector_support_score 与收益负相关 (IC={best_ic:.4f}, spread={best_spread:.4f})"
    else:
        policy = "display_only"
        reason = f"效果不明确 (IC={best_ic}, spread={best_spread})"

    # 对 blocked 和 divergence_review 特殊处理
    if opp_type == "blocked":
        policy = "disabled"
        reason = "blocked 类型不建议调整"
    elif opp_type == "divergence_review" and policy == "enable_adjustment":
        policy = "display_only"
        reason = "divergence_review 类型建议仅展示，不做调整"

    return {
        "opportunity_type": opp_type,
        "sample_count": sample_count,
        "best_horizon": best_horizon,
        "rank_ic": best_ic,
        "strong_vs_weak_spread": best_spread,
        "policy": policy,
        "reason": reason,
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
    all_samples = []
    total_candidates = 0

    for date in dates:
        candidates = load_candidates(date, candidate_root)
        forward_returns = load_forward_returns(date, forward_return_root)

        if not candidates:
            continue

        total_candidates += len(candidates)

        for c in candidates:
            code = c.get("code", "")
            if code not in (forward_returns or {}):
                continue

            # 提取字段
            sector_support_score = extract_sector_support_score(c)
            if sector_support_score is None:
                continue

            sector_support_state = get_sector_support_state(sector_support_score)
            opportunity_type = infer_opportunity_type(c)

            # 提取 forward returns
            fr = forward_returns.get(code, {})
            forward_returns_dict = {}
            for h in horizons:
                if h in fr:
                    forward_returns_dict[h] = fr[h]

            sample = {
                "date": date,
                "code": code,
                "name": c.get("name", ""),
                "opportunity_type": opportunity_type,
                "selection_bucket": c.get("selection_bucket", ""),
                "source_pool": c.get("source_pool", ""),
                "sector_support_score": sector_support_score,
                "sector_support_state": sector_support_state,
                "selection_score": _safe_float(c.get("selection_score")),
                "selection_score_adjusted": _safe_float(c.get("selection_score_adjusted")),
                "final_score": _safe_float(c.get("final_score")),
                "v2_score": _safe_float(c.get("factor_composite_shadow_score_v2")),
                "forward_returns": forward_returns_dict,
            }

            all_samples.append(sample)

    # 按 opportunity_type 分组
    opp_type_samples: dict[str, list[dict]] = {ot: [] for ot in OPPORTUNITY_TYPES}
    for s in all_samples:
        ot = s.get("opportunity_type", "unknown")
        if ot in opp_type_samples:
            opp_type_samples[ot].append(s)
        else:
            opp_type_samples["unknown"].append(s)

    # 分析每个 opportunity_type
    opp_type_results = {}
    policies = []

    for ot in OPPORTUNITY_TYPES:
        samples = opp_type_samples[ot]
        if not samples:
            opp_type_results[ot] = {
                "sample_count": 0,
                "status": "no_data",
            }
            policies.append({
                "opportunity_type": ot,
                "sample_count": 0,
                "policy": "insufficient_sample",
                "reason": "无数据",
            })
            continue

        analysis = analyze_sector_support_for_opportunity(samples, horizons, min_samples)
        opp_type_results[ot] = analysis

        policy = generate_policy(ot, analysis, min_samples)
        policies.append(policy)

    # 生成 shadow policy
    shadow_policy = {
        "description": "sector_support_score adjustment policy by opportunity_type (shadow)",
        "policies": policies,
        "recommendation": "本阶段只输出 shadow policy，不直接修改生产 selection_quality",
    }

    # 汇总
    summary = {
        "total_candidates": total_candidates,
        "usable_samples": len(all_samples),
        "factor_coverage": len(all_samples) / total_candidates if total_candidates > 0 else 0,
        "best_overall_horizon": None,
    }

    # 找最佳整体 horizon
    best_overall_ic = None
    for ot, analysis in opp_type_results.items():
        best_ic = analysis.get("best_ic")
        if best_ic is not None and (best_overall_ic is None or abs(best_ic) > abs(best_overall_ic)):
            best_overall_ic = best_ic
            summary["best_overall_horizon"] = analysis.get("best_horizon")

    return {
        "schema_version": "1.0",
        "start": start_date,
        "end": end_date,
        "summary": summary,
        "opportunity_type_results": opp_type_results,
        "sector_support_adjustment_policy_shadow": shadow_policy,
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
    lines.append("# Sector Support Score by Opportunity Type\n")

    # 运行摘要
    summary = evaluation["summary"]
    lines.append("## 运行摘要\n")
    lines.append(f"- 评估区间: {evaluation['start']} ~ {evaluation['end']}")
    lines.append(f"- 总候选股数: {summary['total_candidates']}")
    lines.append(f"- 有效样本数: {summary['usable_samples']}")
    lines.append(f"- 覆盖率: {summary['factor_coverage']:.1%}")
    lines.append("")

    # 各 opportunity_type 样本数
    lines.append("## 各 Opportunity Type 样本数\n")
    lines.append("| 类型 | 样本数 | 状态 |")
    lines.append("|------|--------|------|")
    for ot, result in evaluation["opportunity_type_results"].items():
        count = result.get("sample_count", 0)
        status = result.get("status", "ok")
        lines.append(f"| {ot} | {count} | {status} |")
    lines.append("")

    # 各 opportunity_type 最佳 horizon / IC / spread
    lines.append("## 各 Opportunity Type 有效性\n")
    lines.append("| 类型 | 样本数 | 最佳 Horizon | Rank IC | Strong-Weak Spread | Policy |")
    lines.append("|------|--------|-------------|---------|-------------------|--------|")

    policies = evaluation.get("sector_support_adjustment_policy_shadow", {}).get("policies", [])
    for policy in policies:
        ot = policy["opportunity_type"]
        result = evaluation["opportunity_type_results"].get(ot, {})
        sample_count = result.get("sample_count", 0)
        best_horizon = policy.get("best_horizon", "N/A")
        rank_ic = policy.get("rank_ic")
        spread = policy.get("strong_vs_weak_spread")
        policy_type = policy.get("policy", "N/A")

        ic_str = f"{rank_ic:.4f}" if rank_ic is not None else "N/A"
        spread_str = f"{spread:.4f}" if spread is not None else "N/A"

        lines.append(f"| {ot} | {sample_count} | {best_horizon} | {ic_str} | {spread_str} | {policy_type} |")
    lines.append("")

    # Shadow Policy 建议
    lines.append("## Shadow Policy 建议\n")
    lines.append("本阶段只输出 shadow policy，不直接修改生产 selection_quality。\n")
    for policy in policies:
        lines.append(f"### {policy['opportunity_type']}\n")
        lines.append(f"- Policy: **{policy['policy']}**")
        lines.append(f"- 原因: {policy['reason']}")
        lines.append("")

    # 结论
    lines.append("## 结论\n")
    lines.append("### 是否建议下一阶段修改 selection_quality\n")
    enable_count = sum(1 for p in policies if p["policy"] == "enable_adjustment")
    if enable_count > 0:
        lines.append(f"- **可考虑**: 有 {enable_count} 个 opportunity_type 建议 enable_adjustment")
        lines.append("- 建议先在 shadow 模式验证，再决定是否修改生产规则")
    else:
        lines.append("- **暂不建议**: 无 opportunity_type 建议 enable_adjustment")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Sector Support Score by Opportunity Type Evaluation"
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

    print(f"  Running Sector Support by Opportunity Type Evaluation...")
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
    filename = f"sector_support_by_opportunity_type_{args.start}_{args.end}"
    json_path = output_dir / f"{filename}.json"
    md_path = output_dir / f"{filename}.md"

    generate_json_report(evaluation, json_path)
    generate_markdown_report(evaluation, md_path)

    print(f"\n  ✅ Evaluation complete")
    print(f"  📄 JSON report: {json_path}")
    print(f"  📝 Markdown report: {md_path}")

    # 打印策略建议
    policies = evaluation.get("sector_support_adjustment_policy_shadow", {}).get("policies", [])
    print(f"\n  📊 Policy Suggestions:")
    for p in policies:
        print(f"     {p['opportunity_type']}: {p['policy']} - {p['reason']}")


if __name__ == "__main__":
    main()
