#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
影子决策分 V2 评估脚本

比较 current decision_score vs shadow_decision_score_v2 的历史表现。
不修改生产评分逻辑，只输出对比结论。

用法:
  python scripts/evaluate_shadow_decision_score.py \
    --validation-root reports/selection_validation \
    --candidate-root reports/agent_bridge \
    --aggregate-path reports/selection_validation/aggregate/2026-06-01_to_2026-07-07/selection_validation_aggregate.json \
    --output-dir reports/selection_validation/shadow_score/2026-06-01_to_2026-07-07
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ======================================================================
# SPEARMAN RANK CORRELATION (hand-written)
# ======================================================================

def _rank(values: list[float]) -> list[float]:
    n = len(values)
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


def spearman_correlation(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3 or len(y) < 3:
        return None
    n = len(x)
    rx = _rank(x)
    ry = _rank(y)
    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n
    cov = sum((rx[i] - mean_rx) * (ry[i] - mean_ry) for i in range(n))
    std_x = math.sqrt(sum((rx[i] - mean_rx) ** 2 for i in range(n)))
    std_y = math.sqrt(sum((ry[i] - mean_ry) ** 2 for i in range(n)))
    if std_x == 0 or std_y == 0:
        return 0.0
    return round(cov / (std_x * std_y), 4)


def _safe_float(v, default=None):
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ======================================================================
# DATA LOADING
# ======================================================================

def load_calibrated_records(
    aggregate_path: Path,
    validation_root: Path,
    candidate_root: Path,
) -> list[dict]:
    """Load per-candidate records enriched with shadow scores."""
    agg = json.loads(aggregate_path.read_text(encoding="utf-8"))
    ok_dates = [row["date"] for row in agg.get("date_status_table", [])
                if row.get("status") == "ok"]

    records = []
    for date in ok_dates:
        val_path = validation_root / date / "next_day_selection_validation.json"
        if not val_path.exists():
            continue
        val = json.loads(val_path.read_text(encoding="utf-8"))
        per_stock = val.get("per_stock", [])

        # Market regime
        market_regime = None
        for row in agg.get("date_status_table", []):
            if row["date"] == date:
                market_regime = row.get("market_regime")
                break

        # Load candidates for shadow scores
        t30_path = candidate_root / date / "top30_candidates.json"
        cand_lookup = {}
        if t30_path.exists():
            try:
                t30 = json.loads(t30_path.read_text(encoding="utf-8"))
                for c in t30.get("candidates", []):
                    cand_lookup[str(c.get("code", ""))] = c
            except Exception:
                pass

        # Load ranking (optional)
        rank_path = candidate_root / date / "aihf_stock_ranking.json"
        rank_lookup = {}
        if rank_path.exists():
            try:
                rank = json.loads(rank_path.read_text(encoding="utf-8"))
                for r in rank.get("items", []):
                    rank_lookup[str(r.get("code", ""))] = r
            except Exception:
                pass

        for ps in per_stock:
            code = str(ps.get("code", ""))
            cand = cand_lookup.get(code, {})
            rank = rank_lookup.get(code, {})

            record = {
                "date": date,
                "code": code,
                "name": ps.get("name", ""),
                "market_regime": market_regime,
                "next_return_pct": ps.get("next_return_pct"),
                "data_available": ps.get("data_available", False),
                # Current scores
                "decision_score": ps.get("decision_score") or cand.get("decision_score"),
                "stock_short_score": ps.get("stock_short_score") or cand.get("stock_short_score"),
                "stock_trend_score": cand.get("stock_trend_score"),
                "sector_leader_score": cand.get("sector_leader_score"),
                "risk_penalty_score": cand.get("risk_penalty_score"),
                "trade_eligibility": ps.get("trade_eligibility") or cand.get("trade_eligibility"),
                "source_pool": ps.get("source_pool") or cand.get("source_pool"),
                "agent_analysis_status": cand.get("agent_analysis_status"),
                "agent_score": ps.get("agent_score") or rank.get("agent_score"),
                # Shadow scores
                "hard_risk_penalty": cand.get("hard_risk_penalty"),
                "volatility_elasticity_score": cand.get("volatility_elasticity_score"),
                "drawdown_risk_score": cand.get("drawdown_risk_score"),
                "shadow_decision_score_v2": cand.get("shadow_decision_score_v2"),
            }
            records.append(record)

    return records


# ======================================================================
# FACTOR EVALUATION
# ======================================================================

def evaluate_factor(
    records: list[dict],
    factor: str,
    regime: str | None = None,
) -> dict:
    """Evaluate a single factor's predictive power."""
    subset = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]
    if regime:
        subset = [r for r in subset if r.get("market_regime") == regime]

    if len(subset) < 5:
        return {"sample_count": len(subset), "error": "insufficient_samples"}

    # Sort by factor
    valid = [(r, _safe_float(r.get(factor))) for r in subset]
    valid = [(r, v) for r, v in valid if v is not None]
    if len(valid) < 5:
        return {"sample_count": len(valid), "error": "factor_missing"}

    valid.sort(key=lambda x: x[1], reverse=True)
    n = len(valid)

    # Top5 vs Bottom10
    top5 = valid[:5]
    bot10 = valid[-10:] if n >= 10 else valid[n // 2:]
    top5_ret = [_safe_float(r.get("next_return_pct")) for r, _ in top5]
    bot10_ret = [_safe_float(r.get("next_return_pct")) for r, _ in bot10]
    top5_ret = [r for r in top5_ret if r is not None]
    bot10_ret = [r for r in bot10_ret if r is not None]

    top5_avg = round(sum(top5_ret) / len(top5_ret), 4) if top5_ret else None
    bot10_avg = round(sum(bot10_ret) / len(bot10_ret), 4) if bot10_ret else None
    gap = round(top5_avg - bot10_avg, 4) if top5_avg is not None and bot10_avg is not None else None

    # High vs Low bucket (top/bottom 30%)
    bucket_n = max(1, int(n * 0.3))
    high_ret = [_safe_float(r.get("next_return_pct")) for r, _ in valid[:bucket_n]]
    low_ret = [_safe_float(r.get("next_return_pct")) for r, _ in valid[-bucket_n:]]
    high_ret = [r for r in high_ret if r is not None]
    low_ret = [r for r in low_ret if r is not None]
    high_avg = round(sum(high_ret) / len(high_ret), 4) if high_ret else None
    low_avg = round(sum(low_ret) / len(low_ret), 4) if low_ret else None
    bucket_gap = round(high_avg - low_avg, 4) if high_avg is not None and low_avg is not None else None

    # Spearman correlation
    all_vals = [_safe_float(r.get(factor)) for r in subset]
    all_rets = [_safe_float(r.get("next_return_pct")) for r in subset]
    aligned = [(v, ret) for v, ret in zip(all_vals, all_rets) if v is not None and ret is not None]
    corr = None
    if len(aligned) >= 3:
        corr = spearman_correlation([a[0] for a in aligned], [a[1] for a in aligned])

    # Positive/negative gap dates
    by_date: dict[str, list] = defaultdict(list)
    for r in subset:
        by_date[r["date"]].append(r)

    pos_dates = 0
    neg_dates = 0
    for date, items in by_date.items():
        vals = [_safe_float(x.get(factor)) for x in items]
        rets = [_safe_float(x.get("next_return_pct")) for x in items]
        aligned_d = [(v, ret) for v, ret in zip(vals, rets) if v is not None and ret is not None]
        if len(aligned_d) >= 3:
            d_corr = spearman_correlation([a[0] for a in aligned_d], [a[1] for a in aligned_d])
            if d_corr is not None:
                if d_corr > 0:
                    pos_dates += 1
                elif d_corr < 0:
                    neg_dates += 1

    valid_dates = pos_dates + neg_dates
    consistency = round(pos_dates / valid_dates * 100, 1) if valid_dates > 0 else None

    return {
        "sample_count": n,
        "date_count": len(by_date),
        "top5_avg_return": top5_avg,
        "bottom10_avg_return": bot10_avg,
        "top5_bottom10_gap": gap,
        "high_bucket_avg_return": high_avg,
        "low_bucket_avg_return": low_avg,
        "high_low_gap": bucket_gap,
        "spearman_corr": corr,
        "positive_corr_date_count": pos_dates,
        "negative_corr_date_count": neg_dates,
        "consistency_positive": consistency,
    }


# ======================================================================
# MAIN
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="Evaluate shadow decision score v2")
    parser.add_argument("--validation-root", default="reports/selection_validation")
    parser.add_argument("--candidate-root", default="reports/agent_bridge")
    parser.add_argument("--aggregate-path", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    validation_root = Path(args.validation_root)
    candidate_root = Path(args.candidate_root)
    aggregate_path = Path(args.aggregate_path)
    output_dir = Path(args.output_dir)

    print(f"  Loading calibrated records...")
    records = load_calibrated_records(aggregate_path, validation_root, candidate_root)
    print(f"  Loaded {len(records)} records")

    valid_records = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]
    print(f"  Records with forward data: {len(valid_records)}")

    # Coverage
    agg = json.loads(aggregate_path.read_text(encoding="utf-8"))
    coverage = agg.get("coverage_summary", {})
    coverage["total_records"] = len(records)
    coverage["records_with_data"] = len(valid_records)

    # Evaluate factors
    factors_to_compare = [
        "decision_score",
        "shadow_decision_score_v2",
        "risk_penalty_score",
        "hard_risk_penalty",
        "volatility_elasticity_score",
        "drawdown_risk_score",
    ]

    factor_results = {}
    for factor in factors_to_compare:
        print(f"  Evaluating {factor}...")
        all_eval = evaluate_factor(records, factor, regime=None)
        up_eval = evaluate_factor(records, factor, regime="broad_up")
        down_eval = evaluate_factor(records, factor, regime="broad_down")
        mixed_eval = evaluate_factor(records, factor, regime="mixed")
        factor_results[factor] = {
            "all": all_eval,
            "broad_up": up_eval,
            "broad_down": down_eval,
            "mixed": mixed_eval,
        }

    # Improvement assessment
    current_gap = factor_results.get("decision_score", {}).get("all", {}).get("top5_bottom10_gap")
    shadow_gap = factor_results.get("shadow_decision_score_v2", {}).get("all", {}).get("top5_bottom10_gap")
    current_corr = factor_results.get("decision_score", {}).get("all", {}).get("spearman_corr")
    shadow_corr = factor_results.get("shadow_decision_score_v2", {}).get("all", {}).get("spearman_corr")

    shadow_score_improved = False
    improvement_reasons = []
    valid_date_count = coverage.get("valid_date_count", 0)

    if valid_date_count >= 20:
        if shadow_gap is not None and current_gap is not None:
            if shadow_gap > current_gap + 0.5:
                shadow_score_improved = True
                improvement_reasons.append(f"shadow gap ({shadow_gap:.2f}) > current gap ({current_gap:.2f}) + 0.5pp")
        if shadow_corr is not None and current_corr is not None:
            if shadow_corr > current_corr + 0.05:
                shadow_score_improved = True
                improvement_reasons.append(f"shadow corr ({shadow_corr:.4f}) > current corr ({current_corr:.4f}) + 0.05")

    # Risk decomposition summary
    decomp_summary = {}
    for field in ["hard_risk_penalty", "volatility_elasticity_score", "drawdown_risk_score"]:
        vals = [_safe_float(r.get(field)) for r in records if r.get("data_available")]
        vals = [v for v in vals if v is not None]
        if vals:
            decomp_summary[field] = {
                "mean": round(sum(vals) / len(vals), 2),
                "min": round(min(vals), 2),
                "max": round(max(vals), 2),
                "std": round(math.sqrt(sum((v - sum(vals)/len(vals))**2 for v in vals) / len(vals)), 2),
            }

    # Build output
    output = {
        "as_of": "2026-06-01 to 2026-07-07",
        "coverage": coverage,
        "factor_results": factor_results,
        "risk_decomposition_summary": decomp_summary,
        "improvement_assessment": {
            "shadow_score_improved": shadow_score_improved,
            "improvement_reasons": improvement_reasons,
            "current_decision_gap": current_gap,
            "shadow_decision_gap": shadow_gap,
            "current_spearman_corr": current_corr,
            "shadow_spearman_corr": shadow_corr,
            "valid_date_count": valid_date_count,
            "production_change_allowed": False,
        },
        "recommendations": _build_recommendations(shadow_score_improved, factor_results, decomp_summary),
    }

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "shadow_decision_score_evaluation.json"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ JSON: {json_path}")

    md = _generate_markdown(output)
    md_path = output_dir / "shadow_decision_score_evaluation.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  ✅ Markdown: {md_path}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"  Shadow Score Evaluation Summary")
    print(f"{'='*60}")
    print(f"  Current decision_score gap: {current_gap}")
    print(f"  Shadow v2 gap: {shadow_gap}")
    print(f"  Current Spearman: {current_corr}")
    print(f"  Shadow Spearman: {shadow_corr}")
    print(f"  Shadow improved: {shadow_score_improved}")
    print(f"  All production_change_allowed: false")


def _build_recommendations(improved: bool, factor_results: dict, decomp: dict) -> list[dict]:
    recs = []
    recs.append({
        "action": "do_not_change_production_weights",
        "reason": "Shadow score experiment requires more validation before production changes",
        "production_change_allowed": False,
    })
    if improved:
        recs.append({
            "action": "shadow_score_shows_potential",
            "reason": "Shadow v2 outperforms current decision_score in backtest. Consider promoting to production after further validation.",
            "production_change_allowed": False,
        })
    else:
        recs.append({
            "action": "shadow_score_needs_more_data",
            "reason": "Shadow v2 does not yet outperform current decision_score. Continue accumulating data.",
            "production_change_allowed": False,
        })

    # Risk decomposition insight
    hard = decomp.get("hard_risk_penalty", {})
    elast = decomp.get("volatility_elasticity_score", {})
    drawdown = decomp.get("drawdown_risk_score", {})

    if hard.get("mean", 0) > 5:
        recs.append({
            "action": "review_hard_risk_penalties",
            "reason": f"Average hard_risk_penalty is {hard.get('mean', 0):.1f}. Some penalties may be overly aggressive.",
            "production_change_allowed": False,
        })
    if elast.get("mean", 0) > 60:
        recs.append({
            "action": "elasticity_stocks_may_outperform",
            "reason": f"Average elasticity score is {elast.get('mean', 0):.1f}. High-elasticity stocks may have alpha that current risk_penalty misses.",
            "production_change_allowed": False,
        })
    if drawdown.get("mean", 0) > 10:
        recs.append({
            "action": "drawdown_risk_elevated",
            "reason": f"Average drawdown_risk is {drawdown.get('mean', 0):.1f}. Consider tighter drawdown controls.",
            "production_change_allowed": False,
        })

    return recs


def _generate_markdown(output: dict) -> str:
    lines = []
    lines.append(f"# Shadow Decision Score V2 Evaluation — 2026-06-01 to 2026-07-07")
    lines.append(f"")

    # 1. Executive Summary
    lines.append(f"## 1. Executive Summary")
    lines.append(f"")
    impl = output.get("improvement_assessment", {})
    if impl.get("shadow_score_improved"):
        lines.append(f"**Shadow Decision Score V2 shows improvement over current decision_score.**")
    else:
        lines.append(f"**Shadow Decision Score V2 does not yet outperform current decision_score.**")
    lines.append(f"")
    for r in impl.get("improvement_reasons", []):
        lines.append(f"- {r}")
    if not impl.get("improvement_reasons"):
        lines.append(f"- No significant improvement detected")
    lines.append(f"")

    # 2. Dataset Summary
    cov = output.get("coverage", {})
    lines.append(f"## 2. Dataset Summary")
    lines.append(f"")
    lines.append(f"- Valid dates: {cov.get('valid_date_count', 0)}")
    lines.append(f"- Total records: {cov.get('total_records', 0)}")
    lines.append(f"- Records with forward data: {cov.get('records_with_data', 0)}")
    lines.append(f"")

    # 3. Current vs Shadow Comparison
    lines.append(f"## 3. Current vs Shadow Comparison")
    lines.append(f"")
    lines.append(f"| {'Factor':<30} {'Gap':>8} {'Bucket Gap':>11} {'Spearman':>9} {'Pos%':>6} {'Conf':>6} |")
    lines.append(f"|{'─'*32}|{'─'*10}|{'─'*13}|{'─'*11}|{'─'*8}|{'─'*8}|")
    for factor in ["decision_score", "shadow_decision_score_v2", "risk_penalty_score"]:
        info = output.get("factor_results", {}).get(factor, {}).get("all", {})
        gap = info.get("top5_bottom10_gap")
        bucket = info.get("high_low_gap")
        corr = info.get("spearman_corr")
        cons = info.get("consistency_positive")
        n = info.get("sample_count", 0)
        gap_s = f"{gap:.2f}" if gap is not None else "N/A"
        bucket_s = f"{bucket:.2f}" if bucket is not None else "N/A"
        corr_s = f"{corr:.4f}" if corr is not None else "N/A"
        cons_s = f"{cons:.1f}" if cons is not None else "N/A"
        conf = "high" if n >= 300 and gap is not None and abs(gap) >= 1 and cons and cons >= 60 else "medium" if n >= 150 else "low"
        lines.append(f"| {factor:<30} {gap_s:>8} {bucket_s:>11} {corr_s:>9} {cons_s:>6} {conf:>6} |")
    lines.append(f"")

    # 4. Risk Decomposition Diagnostics
    lines.append(f"## 4. Risk Decomposition Diagnostics")
    lines.append(f"")
    lines.append(f"| {'Component':<30} {'Mean':>8} {'Min':>8} {'Max':>8} {'Std':>8} |")
    lines.append(f"|{'─'*32}|{'─'*10}|{'─'*10}|{'─'*10}|{'─'*10}|")
    for field in ["hard_risk_penalty", "volatility_elasticity_score", "drawdown_risk_score"]:
        info = output.get("risk_decomposition_summary", {}).get(field, {})
        lines.append(f"| {field:<30} {info.get('mean', 'N/A'):>8} {info.get('min', 'N/A'):>8} {info.get('max', 'N/A'):>8} {info.get('std', 'N/A'):>8} |")
    lines.append(f"")

    # 5. Market Regime Breakdown
    lines.append(f"## 5. Market Regime Breakdown")
    lines.append(f"")
    for regime in ["broad_up", "broad_down", "mixed"]:
        lines.append(f"### {regime}")
        lines.append(f"")
        lines.append(f"| {'Factor':<30} {'Gap':>8} {'Spearman':>9} |")
        lines.append(f"|{'─'*32}|{'─'*10}|{'─'*11}|")
        for factor in ["decision_score", "shadow_decision_score_v2"]:
            info = output.get("factor_results", {}).get(factor, {}).get(regime, {})
            gap = info.get("top5_bottom10_gap")
            corr = info.get("spearman_corr")
            gap_s = f"{gap:.2f}" if gap is not None else "N/A"
            corr_s = f"{corr:.4f}" if corr is not None else "N/A"
            lines.append(f"| {factor:<30} {gap_s:>8} {corr_s:>9} |")
        lines.append(f"")

    # 6. Improvement Assessment
    lines.append(f"## 6. Improvement Assessment")
    lines.append(f"")
    lines.append(f"- **shadow_score_improved**: {impl.get('shadow_score_improved', False)}")
    lines.append(f"- **current_decision_gap**: {impl.get('current_decision_gap', 'N/A')}")
    lines.append(f"- **shadow_decision_gap**: {impl.get('shadow_decision_gap', 'N/A')}")
    lines.append(f"- **current_spearman_corr**: {impl.get('current_spearman_corr', 'N/A')}")
    lines.append(f"- **shadow_spearman_corr**: {impl.get('shadow_spearman_corr', 'N/A')}")
    lines.append(f"")

    # 7. Recommendations
    lines.append(f"## 7. Recommendations")
    lines.append(f"")
    for rec in output.get("recommendations", []):
        lines.append(f"- **{rec['action']}**: {rec['reason']}")
    lines.append(f"")

    # 8. Do Not Change
    lines.append(f"## 8. Do Not Change Production Yet")
    lines.append(f"")
    lines.append(f"**All production_change_allowed = false.** Shadow score is an experiment.")
    lines.append(f"Do not modify production decision_score until shadow v2 demonstrates")
    lines.append(f"consistent improvement across multiple market regimes with sufficient sample size.")
    lines.append(f"")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
