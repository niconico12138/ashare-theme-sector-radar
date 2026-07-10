#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
因子失效诊断脚本

分析为什么高分组没有跑赢低分组。
不做权重调整，只输出诊断结论。

用法:
  python scripts/diagnose_factor_failure.py \
    --aggregate-path reports/selection_validation/aggregate/2026-06-01_to_2026-07-07/selection_validation_aggregate.json \
    --validation-root reports/selection_validation \
    --candidate-root reports/agent_bridge \
    --output-dir reports/selection_validation/diagnostics/2026-06-01_to_2026-07-07
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
# SPEARMAN RANK CORRELATION (hand-written, no scipy)
# ======================================================================

def _rank(values: list[float]) -> list[float]:
    """Assign ranks to values. Ties get average rank."""
    n = len(values)
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1  # 1-based average rank
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


def spearman_correlation(x: list[float], y: list[float]) -> float | None:
    """Compute Spearman rank correlation. Returns None if insufficient data."""
    if len(x) < 3 or len(y) < 3:
        return None
    n = len(x)
    rx = _rank(x)
    ry = _rank(y)

    # Pearson on ranks
    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n
    cov = sum((rx[i] - mean_rx) * (ry[i] - mean_ry) for i in range(n))
    std_x = math.sqrt(sum((rx[i] - mean_rx) ** 2 for i in range(n)))
    std_y = math.sqrt(sum((ry[i] - mean_ry) ** 2 for i in range(n)))

    if std_x == 0 or std_y == 0:
        return 0.0
    return round(cov / (std_x * std_y), 4)


# ======================================================================
# DATA LOADING
# ======================================================================

def load_per_candidate_records(
    aggregate_path: Path,
    validation_root: Path,
    candidate_root: Path,
) -> list[dict]:
    """Load and merge per-candidate records from all valid dates."""
    agg = json.loads(aggregate_path.read_text(encoding="utf-8"))
    ok_dates = [
        row["date"] for row in agg.get("date_status_table", [])
        if row.get("status") == "ok"
    ]

    records = []
    missing_fields_count = 0

    for date in ok_dates:
        # Load validation
        val_path = validation_root / date / "next_day_selection_validation.json"
        if not val_path.exists():
            continue
        val = json.loads(val_path.read_text(encoding="utf-8"))
        per_stock = val.get("per_stock", [])
        market_regime = None
        for row in agg.get("date_status_table", []):
            if row["date"] == date:
                market_regime = row.get("market_regime")
                break

        # Load top30 candidates for enriched fields
        t30_path = candidate_root / date / "top30_candidates.json"
        candidate_lookup = {}
        if t30_path.exists():
            try:
                t30 = json.loads(t30_path.read_text(encoding="utf-8"))
                for c in t30.get("candidates", []):
                    candidate_lookup[str(c.get("code", ""))] = c
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
            cand = candidate_lookup.get(code, {})
            rank = rank_lookup.get(code, {})

            record = {
                "date": date,
                "code": code,
                "name": ps.get("name", ""),
                "market_regime": market_regime,
                # From validation
                "next_return_pct": ps.get("next_return_pct"),
                "next_high_return_pct": ps.get("next_high_return_pct"),
                "next_low_return_pct": ps.get("next_low_return_pct"),
                "max_intraday_drawdown_pct": ps.get("max_intraday_drawdown_pct"),
                "data_available": ps.get("data_available", False),
                # From candidate (enriched)
                "decision_score": ps.get("decision_score") or cand.get("decision_score"),
                "stock_short_score": ps.get("stock_short_score") or cand.get("stock_short_score"),
                "stock_trend_score": cand.get("stock_trend_score"),
                "sector_leader_score": cand.get("sector_leader_score"),
                "risk_penalty_score": cand.get("risk_penalty_score"),
                "trade_eligibility": ps.get("trade_eligibility") or cand.get("trade_eligibility"),
                "source_pool": ps.get("source_pool") or cand.get("source_pool"),
                "agent_analysis_status": cand.get("agent_analysis_status"),
                # From ranking (optional)
                "agent_score": ps.get("agent_score") or rank.get("agent_score"),
                "risk_adjusted_score": rank.get("risk_adjusted_score"),
                "risk_level": rank.get("risk_level"),
            }

            # Track missing fields
            key_fields = ["decision_score", "stock_short_score", "next_return_pct"]
            for f in key_fields:
                if record.get(f) is None:
                    missing_fields_count += 1
                    break

            records.append(record)

    return records


# ======================================================================
# FACTOR PERFORMANCE BY REGIME
# ======================================================================

def _safe_float(v, default=None):
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _avg(values: list[float]) -> float | None:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), 4)


def _split_by_quantile(items: list[dict], field: str, n: int = 3) -> dict[str, list[dict]]:
    valid = [(i, _safe_float(i.get(field))) for i in items]
    valid = [(i, v) for i, v in valid if v is not None]
    valid.sort(key=lambda x: x[1], reverse=True)
    total = len(valid)
    if total == 0:
        return {}
    group_size = max(1, total // n)
    labels = ["high", "mid", "low"][:n]
    groups: dict[str, list[dict]] = {l: [] for l in labels}
    for idx, (item, _) in enumerate(valid):
        g = min(idx // group_size, n - 1)
        groups[labels[g]].append(item)
    return groups


def compute_regime_breakdown(records: list[dict]) -> dict:
    """Compute factor performance by market regime."""
    regimes = defaultdict(list)
    for r in records:
        if r.get("data_available") and r.get("next_return_pct") is not None:
            regimes[r.get("market_regime", "unknown")].append(r)

    result = {}
    for regime, items in regimes.items():
        if len(items) < 3:
            continue

        # Decision score top5 vs bottom10
        sorted_by_ds = sorted(items, key=lambda x: _safe_float(x.get("decision_score"), 0), reverse=True)
        top5_ret = [_safe_float(x.get("next_return_pct")) for x in sorted_by_ds[:5]]
        bot10_ret = [_safe_float(x.get("next_return_pct")) for x in sorted_by_ds[-10:]]
        ds_gap = None
        if top5_ret and bot10_ret:
            t5a = _avg(top5_ret)
            b10a = _avg(bot10_ret)
            if t5a is not None and b10a is not None:
                ds_gap = round(t5a - b10a, 4)

        # Score bucket gaps
        gaps = {}
        for field in ["stock_short_score", "stock_trend_score", "sector_leader_score"]:
            groups = _split_by_quantile(items, field, 3)
            h = groups.get("high", [])
            l = groups.get("low", [])
            h_ret = [_safe_float(x.get("next_return_pct")) for x in h]
            l_ret = [_safe_float(x.get("next_return_pct")) for x in l]
            ha = _avg(h_ret)
            la = _avg(l_ret)
            if ha is not None and la is not None:
                gaps[field] = round(ha - la, 4)

        # Risk penalty: low vs high
        rp_groups = _split_by_quantile(items, "risk_penalty_score", 3)
        rp_low = rp_groups.get("high", [])  # high in split = low penalty (reversed)
        rp_high = rp_groups.get("low", [])
        rp_low_ret = [_safe_float(x.get("next_return_pct")) for x in rp_low]
        rp_high_ret = [_safe_float(x.get("next_return_pct")) for x in rp_high]
        rp_gap = None
        if rp_low_ret and rp_high_ret:
            rla = _avg(rp_low_ret)
            rha = _avg(rp_high_ret)
            if rla is not None and rha is not None:
                rp_gap = round(rla - rha, 4)

        # Trade eligibility
        elig_groups = {}
        for elig in ["focus", "watch", "backup", "avoid"]:
            g = [x for x in items if x.get("trade_eligibility") == elig]
            rets = [_safe_float(x.get("next_return_pct")) for x in g]
            elig_groups[elig] = {"avg_return": _avg(rets), "count": len(g)}

        # Source pool
        pool_groups = {}
        for pool in ["trend", "burst"]:
            g = [x for x in items if x.get("source_pool") == pool]
            rets = [_safe_float(x.get("next_return_pct")) for x in g]
            pool_groups[pool] = {"avg_return": _avg(rets), "count": len(g)}

        # Agent analyzed vs skipped
        analyzed = [x for x in items if x.get("agent_analysis_status") in ("pending_agent_analysis", "analyzed")]
        skipped = [x for x in items if x.get("agent_analysis_status") == "skipped_by_agent_stock_limit"]
        analyzed_ret = [_safe_float(x.get("next_return_pct")) for x in analyzed]
        skipped_ret = [_safe_float(x.get("next_return_pct")) for x in skipped]

        result[regime] = {
            "sample_count": len(items),
            "decision_score_gap": ds_gap,
            "score_gaps": gaps,
            "risk_penalty_gap": rp_gap,
            "trade_eligibility": elig_groups,
            "source_pool": pool_groups,
            "agent_analyzed_avg": _avg(analyzed_ret),
            "agent_skipped_avg": _avg(skipped_ret),
        }

    return result


# ======================================================================
# RANK CORRELATION
# ======================================================================

def compute_rank_correlations(records: list[dict]) -> dict:
    """Compute daily and overall Spearman rank correlations."""
    score_fields = [
        "decision_score", "stock_short_score", "stock_trend_score",
        "sector_leader_score", "risk_penalty_score", "agent_score",
    ]

    # Group by date
    by_date: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r.get("data_available") and r.get("next_return_pct") is not None:
            by_date[r["date"]].append(r)

    daily_corrs: dict[str, dict[str, float | None]] = {}
    for date, items in sorted(by_date.items()):
        returns = [_safe_float(x.get("next_return_pct")) for x in items]
        returns = [r for r in returns if r is not None]
        if len(returns) < 5:
            continue

        date_corrs = {}
        for field in score_fields:
            vals = [_safe_float(x.get(field)) for x in items]
            # Align: only use items where both return and field are non-None
            aligned = [(r, v) for r, v in zip(
                [_safe_float(x.get("next_return_pct")) for x in items],
                vals
            ) if r is not None and v is not None]
            if len(aligned) < 3:
                date_corrs[field] = None
                continue
            x = [a[1] for a in aligned]
            y = [a[0] for a in aligned]
            date_corrs[field] = spearman_correlation(x, y)
        daily_corrs[date] = date_corrs

    # Aggregate
    overall = {}
    for field in score_fields:
        corrs = [daily_corrs[d].get(field) for d in daily_corrs if daily_corrs[d].get(field) is not None]
        if corrs:
            avg_corr = round(sum(corrs) / len(corrs), 4)
            pos_count = sum(1 for c in corrs if c > 0)
            neg_count = sum(1 for c in corrs if c < 0)
            consistency = round(pos_count / len(corrs) * 100, 1) if corrs else None
            overall[field] = {
                "avg_correlation": avg_corr,
                "positive_date_count": pos_count,
                "negative_date_count": neg_count,
                "valid_date_count": len(corrs),
                "consistency": consistency,
            }
        else:
            overall[field] = {"avg_correlation": None, "valid_date_count": 0}

    return {"daily": daily_corrs, "overall": overall}


# ======================================================================
# HIGH SCORE RISK EXPOSURE
# ======================================================================

def compute_risk_exposure(records: list[dict]) -> dict:
    """Compare risk profiles of top5 vs bottom10 by decision_score."""
    valid = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]
    if len(valid) < 15:
        return {"error": "insufficient_samples"}

    sorted_by_ds = sorted(valid, key=lambda x: _safe_float(x.get("decision_score"), 0), reverse=True)
    top5 = sorted_by_ds[:5]
    bot10 = sorted_by_ds[-10:]

    def _avg_field(items, field):
        vals = [_safe_float(x.get(field)) for x in items]
        return _avg(vals)

    def _dist(items, field):
        d = defaultdict(int)
        for x in items:
            d[str(x.get(field, "missing"))] += 1
        return dict(d)

    top5_avg_return = _avg([_safe_float(x.get("next_return_pct")) for x in top5])
    bot10_avg_return = _avg([_safe_float(x.get("next_return_pct")) for x in bot10])

    top5_avg_low = _avg([_safe_float(x.get("next_low_return_pct")) for x in top5])
    bot10_avg_low = _avg([_safe_float(x.get("next_low_return_pct")) for x in bot10])

    top5_avg_dd = _avg([_safe_float(x.get("max_intraday_drawdown_pct")) for x in top5])
    bot10_avg_dd = _avg([_safe_float(x.get("max_intraday_drawdown_pct")) for x in bot10])

    # Diagnoses
    flags = []
    if top5_avg_low is not None and bot10_avg_low is not None:
        if top5_avg_low < bot10_avg_low:
            flags.append("high_score_higher_drawdown")

    top5_pools = _dist(top5, "source_pool")
    if top5_pools.get("burst", 0) > len(top5) * 0.6:
        # Check if broad_down regime exists and top5 performed poorly there
        top5_burst_in_down = [
            x for x in top5
            if x.get("source_pool") == "burst" and x.get("market_regime") == "broad_down"
        ]
        if top5_burst_in_down:
            avg_ret = _avg([_safe_float(x.get("next_return_pct")) for x in top5_burst_in_down])
            if avg_ret is not None and avg_ret < -1.0:
                flags.append("offensive_concentration_risk")

    top5_rp = _avg([_safe_float(x.get("risk_penalty_score")) for x in top5])
    bot10_rp = _avg([_safe_float(x.get("risk_penalty_score")) for x in bot10])
    if top5_rp is not None and bot10_rp is not None:
        if top5_rp > bot10_rp:
            flags.append("score_risk_conflict")

    return {
        "top5": {
            "avg_return": top5_avg_return,
            "avg_risk_penalty": _avg_field(top5, "risk_penalty_score"),
            "avg_stock_short_score": _avg_field(top5, "stock_short_score"),
            "avg_stock_trend_score": _avg_field(top5, "stock_trend_score"),
            "avg_sector_leader_score": _avg_field(top5, "sector_leader_score"),
            "avg_next_low_return_pct": top5_avg_low,
            "avg_max_drawdown_pct": top5_avg_dd,
            "risk_level_dist": _dist(top5, "risk_level"),
            "trade_eligibility_dist": _dist(top5, "trade_eligibility"),
            "source_pool_dist": top5_pools,
        },
        "bottom10": {
            "avg_return": bot10_avg_return,
            "avg_risk_penalty": _avg_field(bot10, "risk_penalty_score"),
            "avg_stock_short_score": _avg_field(bot10, "stock_short_score"),
            "avg_stock_trend_score": _avg_field(bot10, "stock_trend_score"),
            "avg_sector_leader_score": _avg_field(bot10, "sector_leader_score"),
            "avg_next_low_return_pct": bot10_avg_low,
            "avg_max_drawdown_pct": bot10_avg_dd,
            "risk_level_dist": _dist(bot10, "risk_level"),
            "trade_eligibility_dist": _dist(bot10, "trade_eligibility"),
            "source_pool_dist": _dist(bot10, "source_pool"),
        },
        "flags": flags,
    }


# ======================================================================
# AGENT INCREMENTAL DIAGNOSTIC
# ======================================================================

def compute_agent_diagnostic(records: list[dict]) -> dict:
    """Diagnose agent incremental value."""
    analyzed = [r for r in records if r.get("data_available") and r.get("agent_analysis_status") in ("pending_agent_analysis", "analyzed") and r.get("next_return_pct") is not None]
    skipped = [r for r in records if r.get("data_available") and r.get("agent_analysis_status") == "skipped_by_agent_stock_limit" and r.get("next_return_pct") is not None]

    if len(analyzed) < 5 or len(skipped) < 5:
        return {"flags": ["insufficient_agent_samples"], "analyzed_count": len(analyzed), "skipped_count": len(skipped)}

    a_ret = [_safe_float(x.get("next_return_pct")) for x in analyzed]
    s_ret = [_safe_float(x.get("next_return_pct")) for x in skipped]

    a_avg = _avg(a_ret)
    s_avg = _avg(s_ret)
    a_low = _avg([_safe_float(x.get("next_low_return_pct")) for x in analyzed])
    s_low = _avg([_safe_float(x.get("next_low_return_pct")) for x in skipped])

    flags = []
    a_ds = _avg([_safe_float(x.get("decision_score")) for x in analyzed])
    s_ds = _avg([_safe_float(x.get("decision_score")) for x in skipped])
    if a_ds is not None and s_ds is not None and a_avg is not None and s_avg is not None:
        if a_ds > s_ds and a_avg < s_avg:
            flags.append("agent_selection_high_beta_risk")

    # Check by regime
    for regime in ["broad_up", "broad_down"]:
        a_reg = [x for x in analyzed if x.get("market_regime") == regime]
        s_reg = [x for x in skipped if x.get("market_regime") == regime]
        if len(a_reg) >= 3 and len(s_reg) >= 3:
            a_r = _avg([_safe_float(x.get("next_return_pct")) for x in a_reg])
            s_r = _avg([_safe_float(x.get("next_return_pct")) for x in s_reg])
            if a_r is not None and s_r is not None:
                if regime == "broad_up" and a_r > s_r and regime == "broad_down":
                    pass  # would need both conditions

    # Check offensive profile: good in up, bad in down
    a_up = [x for x in analyzed if x.get("market_regime") == "broad_up"]
    a_down = [x for x in analyzed if x.get("market_regime") == "broad_down"]
    if len(a_up) >= 3 and len(a_down) >= 3:
        a_up_ret = _avg([_safe_float(x.get("next_return_pct")) for x in a_up])
        a_down_ret = _avg([_safe_float(x.get("next_return_pct")) for x in a_down])
        if a_up_ret is not None and a_down_ret is not None:
            if a_up_ret > 1.0 and a_down_ret < -2.0:
                flags.append("agent_offensive_profile")

    return {
        "analyzed_count": len(analyzed),
        "skipped_count": len(skipped),
        "analyzed_avg_return": a_avg,
        "skipped_avg_return": s_avg,
        "analyzed_avg_low": a_low,
        "skipped_avg_low": s_low,
        "analyzed_avg_decision_score": a_ds,
        "skipped_avg_decision_score": s_ds,
        "flags": flags,
    }


# ======================================================================
# FORWARD RETURN QUALITY
# ======================================================================

def compute_forward_return_quality(records: list[dict]) -> dict:
    """Check forward return data quality."""
    returns = [_safe_float(r.get("next_return_pct")) for r in records if r.get("data_available")]
    returns = [r for r in returns if r is not None]

    missing = sum(1 for r in records if not r.get("data_available", True))
    extreme = sum(1 for r in returns if abs(r) > 20)

    return {
        "sample_count": len(returns),
        "missing_count": missing,
        "extreme_return_count": extreme,
        "min_return": round(min(returns), 4) if returns else None,
        "max_return": round(max(returns), 4) if returns else None,
        "notes": "Returns are as_of close → next close (1-day horizon)" if returns else "no data",
    }


# ======================================================================
# DIAGNOSIS SUMMARY
# ======================================================================

def generate_diagnosis_summary(
    regime_breakdown: dict,
    rank_corrs: dict,
    risk_exposure: dict,
    agent_diag: dict,
    fwd_quality: dict,
    aggregate: dict,
) -> dict:
    """Generate diagnosis summary with likely causes and recommendations."""
    likely_causes = []
    primary_findings = []

    # Check regime breakdown
    up_data = regime_breakdown.get("broad_up", {})
    down_data = regime_breakdown.get("broad_down", {})

    up_ds_gap = up_data.get("decision_score_gap")
    down_ds_gap = down_data.get("decision_score_gap")

    if up_ds_gap is not None and down_ds_gap is not None:
        if up_ds_gap > 0 and down_ds_gap < 0:
            likely_causes.append("offensive_factor_profile")
            primary_findings.append("Decision score works in up markets but hurts in down markets (offensive profile)")
        elif up_ds_gap is not None and up_ds_gap < 0 and down_ds_gap is not None and down_ds_gap < 0:
            likely_causes.append("factor_direction_misaligned")
            primary_findings.append("Decision score underperforms in ALL market regimes")

    # Check risk exposure
    risk_flags = risk_exposure.get("flags", [])
    if "high_score_higher_drawdown" in risk_flags:
        likely_causes.append("high_score_higher_drawdown")
        primary_findings.append("Top-scored stocks have deeper drawdowns than bottom-scored")
    if "offensive_concentration_risk" in risk_flags:
        likely_causes.append("offensive_concentration_risk")
        primary_findings.append("Top scores concentrate in burst pool which suffers in down markets")
    if "score_risk_conflict" in risk_flags:
        likely_causes.append("score_risk_conflict")
        primary_findings.append("High-scoring stocks paradoxically have higher risk penalty scores")

    # Check rank correlation
    ds_corr = rank_corrs.get("overall", {}).get("decision_score", {})
    if ds_corr.get("avg_correlation") is not None:
        if abs(ds_corr["avg_correlation"]) < 0.05:
            likely_causes.append("weak_rank_correlation")
            primary_findings.append(f"Decision score has near-zero rank correlation with returns (ρ={ds_corr['avg_correlation']})")
        elif ds_corr["avg_correlation"] < -0.05:
            likely_causes.append("factor_direction_misaligned")
            primary_findings.append(f"Decision score is negatively correlated with returns (ρ={ds_corr['avg_correlation']})")

    # Check agent
    agent_flags = agent_diag.get("flags", [])
    if "agent_selection_high_beta_risk" in agent_flags:
        likely_causes.append("agent_selection_high_beta_risk")
        primary_findings.append("Agent-analyzed stocks score higher but deliver lower returns")
    if "agent_offensive_profile" in agent_flags:
        likely_causes.append("offensive_factor_profile")
        primary_findings.append("Agent selection performs well in up markets but poorly in down markets")

    # Sample size
    cov = aggregate.get("coverage_summary", {})
    if cov.get("valid_date_count", 0) < 30:
        likely_causes.append("sample_size_still_limited")
        primary_findings.append(f"Only {cov.get('valid_date_count', 0)} valid dates — insufficient for statistical significance")

    # Forward return quality
    if fwd_quality.get("extreme_return_count", 0) > 0:
        likely_causes.append("missing_or_noisy_forward_data")
        primary_findings.append(f"{fwd_quality['extreme_return_count']} extreme returns (|r|>20%) detected")

    # Risk filter value
    te = aggregate.get("factor_performance_summary", {}).get("trade_eligibility", {})
    focus_ba = te.get("focus_vs_backup_avoid_gap")
    if focus_ba is not None and focus_ba < 0:
        likely_causes.append("risk_filter_defensive_not_alpha")
        primary_findings.append("Focus group underperforms backup/avoid — risk filter provides defensive value, not alpha")

    # Recommended steps
    recommended = []
    if "sample_size_still_limited" in likely_causes:
        recommended.append("Continue accumulating样本 (target 30+ trading days)")
    if "offensive_factor_profile" in likely_causes:
        recommended.append("Model separately by market regime (up/down/mixed)")
    if "weak_rank_correlation" in likely_causes or "factor_direction_misaligned" in likely_causes:
        recommended.append("Conduct factor direction calibration experiment")
    if "high_score_higher_drawdown" in likely_causes:
        recommended.append("Validate risk-adjusted returns (Sharpe/Sortino) instead of raw returns")
    if "risk_filter_defensive_not_alpha" in likely_causes:
        recommended.append("Separate alpha generation from risk filtering")
    if not recommended:
        recommended.append("Continue accumulating样本 before any conclusions")

    if not primary_findings:
        primary_findings.append("All factor signals are inconclusive — no clear failure mode identified")

    return {
        "primary_findings": primary_findings,
        "likely_causes": likely_causes,
        "recommended_next_steps": recommended,
        "do_not_do": [
            "Do not change scoring weights based on current diagnosis",
            "Do not increase agent analysis count to fix factor failure",
            "Do not judge based on single-day top5 performance",
        ],
    }


# ======================================================================
# MARKDOWN REPORT
# ======================================================================

def generate_markdown(
    diagnosis: dict,
    regime_breakdown: dict,
    rank_corrs: dict,
    risk_exposure: dict,
    agent_diag: dict,
    fwd_quality: dict,
    summary: dict,
) -> str:
    lines = []
    lines.append(f"# Factor Failure Diagnosis — 2026-06-01 to 2026-07-07")
    lines.append(f"")

    # 1. Executive Summary
    lines.append(f"## 1. Executive Summary")
    lines.append(f"")
    for f in summary.get("primary_findings", []):
        lines.append(f"- {f}")
    lines.append(f"")

    # 2. Data Coverage
    cov = diagnosis.get("coverage", {})
    lines.append(f"## 2. Data Coverage")
    lines.append(f"")
    lines.append(f"- Valid dates: {cov.get('valid_date_count', 0)}")
    lines.append(f"- Total candidate records: {cov.get('total_records', 0)}")
    lines.append(f"- Records with forward data: {cov.get('records_with_data', 0)}")
    lines.append(f"")

    # 3. Market Regime Breakdown
    lines.append(f"## 3. Market Regime Breakdown")
    lines.append(f"")
    for regime in ["broad_up", "broad_down", "mixed"]:
        rd = regime_breakdown.get(regime, {})
        if not rd:
            continue
        lines.append(f"### {regime} (n={rd.get('sample_count', 0)})")
        lines.append(f"")
        ds_gap = rd.get("decision_score_gap")
        lines.append(f"- decision_score gap: {ds_gap:.4f}" if ds_gap is not None else "- decision_score gap: N/A")
        for field, gap in rd.get("score_gaps", {}).items():
            lines.append(f"- {field} gap (high-low): {gap:.4f}")
        rp_gap = rd.get("risk_penalty_gap")
        lines.append(f"- risk_penalty gap (low-high): {rp_gap:.4f}" if rp_gap is not None else "- risk_penalty gap: N/A")
        lines.append(f"- Trade eligibility:")
        for elig in ["focus", "watch", "backup", "avoid"]:
            info = rd.get("trade_eligibility", {}).get(elig, {})
            avg = info.get("avg_return")
            cnt = info.get("count", 0)
            avg_s = f"{avg:.2f}%" if avg is not None else "N/A"
            lines.append(f"  - {elig}: avg={avg_s} (n={cnt})")
        lines.append(f"- Source pool:")
        for pool in ["trend", "burst"]:
            info = rd.get("source_pool", {}).get(pool, {})
            avg = info.get("avg_return")
            cnt = info.get("count", 0)
            avg_s = f"{avg:.2f}%" if avg is not None else "N/A"
            lines.append(f"  - {pool}: avg={avg_s} (n={cnt})")
        a_avg = rd.get("agent_analyzed_avg")
        s_avg = rd.get("agent_skipped_avg")
        lines.append(f"- Agent analyzed avg: {a_avg:.2f}%" if a_avg is not None else "- Agent analyzed avg: N/A")
        lines.append(f"- Agent skipped avg: {s_avg:.2f}%" if s_avg is not None else "- Agent skipped avg: N/A")
        lines.append(f"")

    # 4. Rank Correlation
    lines.append(f"## 4. Rank Correlation Diagnostics")
    lines.append(f"")
    lines.append(f"| {'Factor':<25} {'Avg ρ':>8} {'Pos dates':>10} {'Neg dates':>10} {'Consistency':>12} |")
    lines.append(f"|{'─'*27}|{'─'*10}|{'─'*12}|{'─'*12}|{'─'*14}|")
    for field, info in rank_corrs.get("overall", {}).items():
        avg = info.get("avg_correlation")
        avg_s = f"{avg:.4f}" if avg is not None else "N/A"
        pos = info.get("positive_date_count", 0)
        neg = info.get("negative_date_count", 0)
        cons = info.get("consistency")
        cons_s = f"{cons:.1f}%" if cons is not None else "N/A"
        lines.append(f"| {field:<25} {avg_s:>8} {pos:>10} {neg:>10} {cons_s:>12} |")
    lines.append(f"")

    # 5. High Score Risk Exposure
    lines.append(f"## 5. High Score Risk Exposure")
    lines.append(f"")
    if risk_exposure.get("error"):
        lines.append(f"- {risk_exposure['error']}")
    else:
        for group in ["top5", "bottom10"]:
            info = risk_exposure.get(group, {})
            lines.append(f"### {group}")
            lines.append(f"- avg_return: {info.get('avg_return', 'N/A')}")
            lines.append(f"- avg_risk_penalty: {info.get('avg_risk_penalty', 'N/A')}")
            lines.append(f"- avg_next_low_return: {info.get('avg_next_low_return_pct', 'N/A')}")
            lines.append(f"- avg_max_drawdown: {info.get('avg_max_drawdown_pct', 'N/A')}")
            lines.append(f"- source_pool_dist: {info.get('source_pool_dist', {})}")
            lines.append(f"- trade_eligibility_dist: {info.get('trade_eligibility_dist', {})}")
            lines.append(f"")
        flags = risk_exposure.get("flags", [])
        if flags:
            lines.append(f"**Flags:** {', '.join(flags)}")
        else:
            lines.append(f"**Flags:** none")
    lines.append(f"")

    # 6. Agent Incremental
    lines.append(f"## 6. Agent Incremental Diagnostics")
    lines.append(f"")
    lines.append(f"- analyzed: n={agent_diag.get('analyzed_count', 0)}, avg_return={agent_diag.get('analyzed_avg_return', 'N/A')}")
    lines.append(f"- skipped: n={agent_diag.get('skipped_count', 0)}, avg_return={agent_diag.get('skipped_avg_return', 'N/A')}")
    lines.append(f"- analyzed avg decision_score: {agent_diag.get('analyzed_avg_decision_score', 'N/A')}")
    lines.append(f"- skipped avg decision_score: {agent_diag.get('skipped_avg_decision_score', 'N/A')}")
    a_flags = agent_diag.get("flags", [])
    if a_flags:
        lines.append(f"- **Flags:** {', '.join(a_flags)}")
    lines.append(f"")

    # 7. Forward Return Quality
    lines.append(f"## 7. Forward Return Quality")
    lines.append(f"")
    lines.append(f"- sample_count: {fwd_quality.get('sample_count', 0)}")
    lines.append(f"- missing_count: {fwd_quality.get('missing_count', 0)}")
    lines.append(f"- extreme_return_count: {fwd_quality.get('extreme_return_count', 0)}")
    lines.append(f"- min_return: {fwd_quality.get('min_return', 'N/A')}")
    lines.append(f"- max_return: {fwd_quality.get('max_return', 'N/A')}")
    lines.append(f"- notes: {fwd_quality.get('notes', '')}")
    lines.append(f"")

    # 8. Likely Causes
    lines.append(f"## 8. Likely Causes")
    lines.append(f"")
    for c in summary.get("likely_causes", []):
        lines.append(f"- {c}")
    lines.append(f"")

    # 9. Recommended Next Steps
    lines.append(f"## 9. Recommended Next Steps")
    lines.append(f"")
    for s in summary.get("recommended_next_steps", []):
        lines.append(f"- {s}")
    lines.append(f"")

    # 10. Do Not Do
    lines.append(f"## 10. Do Not Do")
    lines.append(f"")
    for d in summary.get("do_not_do", []):
        lines.append(f"- {d}")
    lines.append(f"")

    return "\n".join(lines)


# ======================================================================
# MAIN
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="Diagnose factor failure")
    parser.add_argument("--aggregate-path", required=True)
    parser.add_argument("--validation-root", default="reports/selection_validation")
    parser.add_argument("--candidate-root", default="reports/agent_bridge")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    aggregate_path = Path(args.aggregate_path)
    validation_root = Path(args.validation_root)
    candidate_root = Path(args.candidate_root)
    output_dir = Path(args.output_dir)

    print(f"  Loading aggregate...")
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))

    print(f"  Loading per-candidate records...")
    records = load_per_candidate_records(aggregate_path, validation_root, candidate_root)
    print(f"  Loaded {len(records)} records")

    # Filter to available data
    valid_records = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]
    print(f"  Records with forward data: {len(valid_records)}")

    # Compute diagnostics
    print(f"  Computing regime breakdown...")
    regime_breakdown = compute_regime_breakdown(records)

    print(f"  Computing rank correlations...")
    rank_corrs = compute_rank_correlations(records)

    print(f"  Computing risk exposure...")
    risk_exposure = compute_risk_exposure(records)

    print(f"  Computing agent diagnostic...")
    agent_diag = compute_agent_diagnostic(records)

    print(f"  Computing forward return quality...")
    fwd_quality = compute_forward_return_quality(records)

    # Coverage
    coverage = {
        "valid_date_count": aggregate.get("coverage_summary", {}).get("valid_date_count", 0),
        "total_records": len(records),
        "records_with_data": len(valid_records),
    }

    # Build diagnosis
    diagnosis = {
        "as_of": "2026-06-01 to 2026-07-07",
        "coverage": coverage,
        "regime_breakdown": regime_breakdown,
        "rank_correlations": rank_corrs,
        "risk_exposure": risk_exposure,
        "agent_diagnostic": agent_diag,
        "forward_return_quality": fwd_quality,
    }

    # Summary
    summary = generate_diagnosis_summary(
        regime_breakdown, rank_corrs, risk_exposure, agent_diag, fwd_quality, aggregate
    )
    diagnosis["summary"] = summary

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "factor_failure_diagnosis.json"
    json_path.write_text(json.dumps(diagnosis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ JSON: {json_path}")

    md = generate_markdown(diagnosis, regime_breakdown, rank_corrs, risk_exposure, agent_diag, fwd_quality, summary)
    md_path = output_dir / "factor_failure_diagnosis.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  ✅ Markdown: {md_path}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"  Diagnosis Summary")
    print(f"{'='*60}")
    for f in summary.get("primary_findings", []):
        print(f"  📋 {f}")
    print(f"\n  Likely causes:")
    for c in summary.get("likely_causes", []):
        print(f"    - {c}")
    print(f"\n  Recommended:")
    for s in summary.get("recommended_next_steps", []):
        print(f"    - {s}")


if __name__ == "__main__":
    main()
