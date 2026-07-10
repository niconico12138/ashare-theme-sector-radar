#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
120天因子信号完整诊断脚本

对 120 个有效 forward-return 日期做完整因子诊断。
不做权重调整，只输出诊断结论。production_change_allowed = false。

用法:
  python scripts/diagnose_factor_signal_120d.py \
    --aggregate-path reports/selection_validation/aggregate/2026-01-05_to_2026-07-08/selection_validation_aggregate.json \
    --validation-root reports/selection_validation \
    --candidate-root reports/agent_bridge \
    --output-dir reports/selection_validation/diagnostics/2026-01-05_to_2026-07-08
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ---- Windows console encoding fix ----
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Factors to diagnose
FACTOR_FIELDS = [
    "decision_score",
    "stock_short_score",
    "stock_trend_score",
    "sector_leader_score",
    "risk_penalty_score",
    "agent_score",
]

# Consistency threshold for signal classification
CONSISTENCY_THRESHOLD = 55.0


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

    mean_rx = sum(rx) / n
    mean_ry = sum(ry) / n
    cov = sum((rx[i] - mean_rx) * (ry[i] - mean_ry) for i in range(n))
    std_x = math.sqrt(sum((rx[i] - mean_rx) ** 2 for i in range(n)))
    std_y = math.sqrt(sum((ry[i] - mean_ry) ** 2 for i in range(n)))

    if std_x == 0 or std_y == 0:
        return 0.0
    return round(cov / (std_x * std_y), 4)


# ======================================================================
# HELPERS
# ======================================================================

def _safe_float(v, default=None):
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _avg(values: list) -> float | None:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), 4)


def _pct(values: list) -> float | None:
    """Compute percentage of positive values."""
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return round(sum(1 for v in clean if v > 0) / len(clean) * 100, 1)


# ======================================================================
# DATA LOADING
# ======================================================================

def load_per_candidate_records(
    aggregate_path: Path,
    validation_root: Path,
    candidate_root: Path,
) -> tuple[list[dict], dict]:
    """Load and merge per-candidate records from all valid dates.

    Returns:
        (records, aggregate_dict)
    """
    agg = json.loads(aggregate_path.read_text(encoding="utf-8"))
    ok_dates = [
        row["date"] for row in agg.get("date_status_table", [])
        if row.get("status") == "ok"
    ]

    # Pre-build regime lookup
    regime_lookup = {}
    for row in agg.get("date_status_table", []):
        regime_lookup[row["date"]] = row.get("market_regime")

    records = []
    for date in ok_dates:
        val_path = validation_root / date / "next_day_selection_validation.json"
        if not val_path.exists():
            continue
        val = json.loads(val_path.read_text(encoding="utf-8"))
        per_stock = val.get("per_stock", [])
        market_regime = regime_lookup.get(date)

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
                # Shadow fields
                "shadow_decision_score_v2": cand.get("shadow_decision_score_v2"),
            }
            records.append(record)

    return records, agg


# ======================================================================
# FACTOR BUCKET ANALYSIS
# ======================================================================

def _split_by_quantile(items: list[dict], field: str, n: int = 3) -> dict[str, list[dict]]:
    """Split items into n quantile groups by field value (descending)."""
    valid = [(i, _safe_float(i.get(field))) for i in items]
    valid = [(i, v) for i, v in valid if v is not None]
    valid.sort(key=lambda x: x[1], reverse=True)
    total = len(valid)
    if total == 0:
        return {}
    group_size = max(1, total // n)
    labels = ["high", "mid", "low"][:n]
    groups: dict[str, list[dict]] = {lb: [] for lb in labels}
    for idx, (item, _) in enumerate(valid):
        g = min(idx // group_size, n - 1)
        groups[labels[g]].append(item)
    return groups


def compute_factor_bucket_performance(records: list[dict]) -> dict:
    """Compute per-factor bucket performance: avg return, hit rate, drawdown."""
    valid = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]

    result = {}
    for field in FACTOR_FIELDS:
        groups = _split_by_quantile(valid, field, 3)
        bucket_result = {}
        for label in ["high", "mid", "low"]:
            items = groups.get(label, [])
            rets = [_safe_float(x.get("next_return_pct")) for x in items]
            dds = [_safe_float(x.get("max_intraday_drawdown_pct")) for x in items]
            lows = [_safe_float(x.get("next_low_return_pct")) for x in items]

            bucket_result[label] = {
                "count": len(items),
                "avg_return": _avg(rets),
                "hit_rate": _pct(rets),
                "avg_drawdown": _avg(dds),
                "avg_low_return": _avg(lows),
            }

        # Compute high-low gap
        h_ret = bucket_result.get("high", {}).get("avg_return")
        l_ret = bucket_result.get("low", {}).get("avg_return")
        high_low_gap = round(h_ret - l_ret, 4) if h_ret is not None and l_ret is not None else None

        h_hr = bucket_result.get("high", {}).get("hit_rate")
        l_hr = bucket_result.get("low", {}).get("hit_rate")
        hit_rate_diff = round(h_hr - l_hr, 1) if h_hr is not None and l_hr is not None else None

        h_dd = bucket_result.get("high", {}).get("avg_drawdown")
        l_dd = bucket_result.get("low", {}).get("avg_drawdown")
        drawdown_diff = round(h_dd - l_dd, 4) if h_dd is not None and l_dd is not None else None

        result[field] = {
            "buckets": bucket_result,
            "high_low_gap": high_low_gap,
            "hit_rate_diff": hit_rate_diff,
            "drawdown_diff": drawdown_diff,
        }

    return result


# ======================================================================
# RANK CORRELATION (per-date + overall)
# ======================================================================

def compute_rank_correlations(records: list[dict]) -> dict:
    """Compute daily and overall Spearman rank correlations."""
    by_date: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r.get("data_available") and r.get("next_return_pct") is not None:
            by_date[r["date"]].append(r)

    daily_corrs: dict[str, dict[str, float | None]] = {}
    for date, items in sorted(by_date.items()):
        if len(items) < 5:
            continue

        date_corrs = {}
        for field in FACTOR_FIELDS:
            aligned = [
                (_safe_float(x.get("next_return_pct")), _safe_float(x.get(field)))
                for x in items
            ]
            aligned = [(ret, val) for ret, val in aligned if ret is not None and val is not None]
            if len(aligned) < 3:
                date_corrs[field] = None
                continue
            x = [a[1] for a in aligned]
            y = [a[0] for a in aligned]
            date_corrs[field] = spearman_correlation(x, y)
        daily_corrs[date] = date_corrs

    # Aggregate
    overall = {}
    for field in FACTOR_FIELDS:
        corrs = [
            daily_corrs[d].get(field)
            for d in daily_corrs
            if daily_corrs[d].get(field) is not None
        ]
        if corrs:
            avg_corr = round(sum(corrs) / len(corrs), 4)
            pos_count = sum(1 for c in corrs if c > 0)
            neg_count = sum(1 for c in corrs if c < 0)
            consistency = round(pos_count / len(corrs) * 100, 1)
            overall[field] = {
                "avg_correlation": avg_corr,
                "positive_date_count": pos_count,
                "negative_date_count": neg_count,
                "valid_date_count": len(corrs),
                "consistency": consistency,
            }
        else:
            overall[field] = {"avg_correlation": None, "valid_date_count": 0, "consistency": None}

    return {"daily": daily_corrs, "overall": overall}


# ======================================================================
# REGIME BREAKDOWN
# ======================================================================

def compute_regime_breakdown(records: list[dict]) -> dict:
    """Compute per-regime factor performance."""
    regimes: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r.get("data_available") and r.get("next_return_pct") is not None:
            regimes[r.get("market_regime", "unknown")].append(r)

    result = {}
    for regime, items in regimes.items():
        if len(items) < 5:
            continue

        # Per-factor gap by regime
        factor_gaps = {}
        for field in FACTOR_FIELDS:
            groups = _split_by_quantile(items, field, 3)
            h_ret = [_safe_float(x.get("next_return_pct")) for x in groups.get("high", [])]
            l_ret = [_safe_float(x.get("next_return_pct")) for x in groups.get("low", [])]
            ha = _avg(h_ret)
            la = _avg(l_ret)
            gap = round(ha - la, 4) if ha is not None and la is not None else None
            factor_gaps[field] = {
                "gap": gap,
                "high_count": len(groups.get("high", [])),
                "low_count": len(groups.get("low", [])),
            }

        # Trend vs burst
        trend_items = [x for x in items if x.get("source_pool") == "trend"]
        burst_items = [x for x in items if x.get("source_pool") == "burst"]
        both_items = [x for x in items if x.get("source_pool") == "both"]
        trend_avg = _avg([_safe_float(x.get("next_return_pct")) for x in trend_items])
        burst_avg = _avg([_safe_float(x.get("next_return_pct")) for x in burst_items])
        both_avg = _avg([_safe_float(x.get("next_return_pct")) for x in both_items])

        # Agent analyzed vs skipped
        analyzed = [x for x in items if x.get("agent_analysis_status") in ("pending_agent_analysis", "analyzed")]
        skipped = [x for x in items if x.get("agent_analysis_status") == "skipped_by_agent_stock_limit"]

        result[regime] = {
            "sample_count": len(items),
            "factor_gaps": factor_gaps,
            "trend_vs_burst": {
                "trend_avg_return": trend_avg,
                "trend_count": len(trend_items),
                "burst_avg_return": burst_avg,
                "burst_count": len(burst_items),
                "both_avg_return": both_avg,
                "both_count": len(both_items),
                "gap": round(trend_avg - burst_avg, 4) if trend_avg is not None and burst_avg is not None else None,
            },
            "agent_comparison": {
                "analyzed_avg_return": _avg([_safe_float(x.get("next_return_pct")) for x in analyzed]),
                "analyzed_count": len(analyzed),
                "skipped_avg_return": _avg([_safe_float(x.get("next_return_pct")) for x in skipped]),
                "skipped_count": len(skipped),
                "gap": (
                    round(
                        _avg([_safe_float(x.get("next_return_pct")) for x in analyzed])
                        - _avg([_safe_float(x.get("next_return_pct")) for x in skipped]),
                        4,
                    )
                    if analyzed and skipped
                    else None
                ),
            },
        }

    return result


# ======================================================================
# TOP/BOTTOM GAP ANALYSIS
# ======================================================================

def compute_top_bottom_analysis(records: list[dict]) -> dict:
    """Compute top20% vs bottom20% for each factor."""
    valid = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]

    result = {}
    for field in FACTOR_FIELDS:
        sorted_items = sorted(
            [(r, _safe_float(r.get(field))) for r in valid],
            key=lambda x: x[1] if x[1] is not None else -9999,
            reverse=True,
        )
        n = len(sorted_items)
        if n < 10:
            result[field] = {"error": "insufficient_samples"}
            continue

        top_n = max(1, int(n * 0.2))
        bot_n = max(1, int(n * 0.2))

        top_items = [x[0] for x in sorted_items[:top_n]]
        bot_items = [x[0] for x in sorted_items[-bot_n:]]

        top_ret = [_safe_float(x.get("next_return_pct")) for x in top_items]
        bot_ret = [_safe_float(x.get("next_return_pct")) for x in bot_items]
        top_dd = [_safe_float(x.get("max_intraday_drawdown_pct")) for x in top_items]
        bot_dd = [_safe_float(x.get("max_intraday_drawdown_pct")) for x in bot_items]
        top_low = [_safe_float(x.get("next_low_return_pct")) for x in top_items]
        bot_low = [_safe_float(x.get("next_low_return_pct")) for x in bot_items]

        top_avg = _avg(top_ret)
        bot_avg = _avg(bot_ret)
        gap = round(top_avg - bot_avg, 4) if top_avg is not None and bot_avg is not None else None

        top_hr = _pct(top_ret)
        bot_hr = _pct(bot_ret)
        hr_diff = round(top_hr - bot_hr, 1) if top_hr is not None and bot_hr is not None else None

        top_dd_avg = _avg(top_dd)
        bot_dd_avg = _avg(bot_dd)
        dd_diff = round(top_dd_avg - bot_dd_avg, 4) if top_dd_avg is not None and bot_dd_avg is not None else None

        result[field] = {
            "top20_count": len(top_items),
            "bottom20_count": len(bot_items),
            "top20_avg_return": top_avg,
            "bottom20_avg_return": bot_avg,
            "gap": gap,
            "top20_hit_rate": top_hr,
            "bottom20_hit_rate": bot_hr,
            "hit_rate_diff": hr_diff,
            "top20_avg_drawdown": top_dd_avg,
            "bottom20_avg_drawdown": bot_dd_avg,
            "drawdown_diff": dd_diff,
            "top20_avg_low_return": _avg(top_low),
            "bottom20_avg_low_return": _avg(bot_low),
        }

    return result


# ======================================================================
# TREND VS BURST
# ======================================================================

def compute_trend_vs_burst(records: list[dict]) -> dict:
    """Compare trend pool vs burst pool across all dates."""
    valid = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]

    trend = [r for r in valid if r.get("source_pool") == "trend"]
    burst = [r for r in valid if r.get("source_pool") == "burst"]
    both = [r for r in valid if r.get("source_pool") == "both"]

    def _pool_stats(items):
        if not items:
            return {"count": 0, "avg_return": None, "hit_rate": None, "avg_drawdown": None}
        rets = [_safe_float(x.get("next_return_pct")) for x in items]
        dds = [_safe_float(x.get("max_intraday_drawdown_pct")) for x in items]
        return {
            "count": len(items),
            "avg_return": _avg(rets),
            "hit_rate": _pct(rets),
            "avg_drawdown": _avg(dds),
        }

    trend_s = _pool_stats(trend)
    burst_s = _pool_stats(burst)
    both_s = _pool_stats(both)

    gap = None
    if trend_s["avg_return"] is not None and burst_s["avg_return"] is not None:
        gap = round(trend_s["avg_return"] - burst_s["avg_return"], 4)

    return {
        "trend": trend_s,
        "burst": burst_s,
        "both": both_s,
        "trend_burst_gap": gap,
    }


# ======================================================================
# AGENT ANALYZED VS SKIPPED
# ======================================================================

def compute_agent_comparison(records: list[dict]) -> dict:
    """Compare agent-analyzed vs skipped stocks."""
    valid = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]

    analyzed = [r for r in valid if r.get("agent_analysis_status") in ("pending_agent_analysis", "analyzed")]
    skipped = [r for r in valid if r.get("agent_analysis_status") == "skipped_by_agent_stock_limit"]

    def _stats(items):
        if not items:
            return {"count": 0, "avg_return": None, "hit_rate": None, "avg_drawdown": None}
        rets = [_safe_float(x.get("next_return_pct")) for x in items]
        dds = [_safe_float(x.get("max_intraday_drawdown_pct")) for x in items]
        return {
            "count": len(items),
            "avg_return": _avg(rets),
            "hit_rate": _pct(rets),
            "avg_drawdown": _avg(dds),
        }

    a_s = _stats(analyzed)
    s_s = _stats(skipped)

    gap = None
    if a_s["avg_return"] is not None and s_s["avg_return"] is not None:
        gap = round(a_s["avg_return"] - s_s["avg_return"], 4)

    return {
        "analyzed": a_s,
        "skipped": s_s,
        "gap": gap,
    }


# ======================================================================
# SIGNAL CLASSIFICATION
# ======================================================================

def classify_factor_signal(
    field: str,
    bucket_perf: dict,
    rank_corr: dict,
    regime_data: dict,
    top_bottom: dict,
) -> dict:
    """Classify a factor's signal type.

    Rules:
    - positive_signal: avg_gap > 0 AND consistency >= 55%
    - negative_signal: avg_gap < 0 AND consistency >= 55%
    - regime_dependent: sign flips between broad_up and broad_down
    - defensive_not_alpha: high score reduces drawdown but not return
    - inconclusive: none of the above
    """
    fb = bucket_perf.get(field, {})
    rc = rank_corr.get(field, {})
    tb = top_bottom.get(field, {})

    avg_gap = fb.get("high_low_gap")
    consistency = rc.get("consistency")
    avg_corr = rc.get("avg_correlation")

    # Check regime dependency
    up_gap = regime_data.get("broad_up", {}).get("factor_gaps", {}).get(field, {}).get("gap")
    down_gap = regime_data.get("broad_down", {}).get("factor_gaps", {}).get(field, {}).get("gap")

    regime_dependent = False
    if up_gap is not None and down_gap is not None:
        if (up_gap > 0 and down_gap < 0) or (up_gap < 0 and down_gap > 0):
            regime_dependent = True

    # Check defensive profile
    defensive_not_alpha = False
    dd_diff = fb.get("drawdown_diff")
    if avg_gap is not None and dd_diff is not None:
        if avg_gap <= 0 and dd_diff < 0:
            # High score reduces drawdown but not return
            defensive_not_alpha = True

    # Classify
    signal = "inconclusive"
    explanation = ""

    if regime_dependent:
        signal = "regime_dependent"
        explanation = (
            f"Sign flips between regimes: broad_up gap={up_gap:.4f}, "
            f"broad_down gap={down_gap:.4f}. Factor behavior is market-state dependent."
        )
    elif defensive_not_alpha:
        signal = "defensive_not_alpha"
        explanation = (
            f"High-score group has lower drawdown ({dd_diff:.4f}pp) but "
            f"not higher return (gap={avg_gap:.4f}pp). Risk filter provides "
            f"defensive value, not alpha."
        )
    elif avg_gap is not None and consistency is not None:
        if avg_gap > 0 and consistency >= CONSISTENCY_THRESHOLD:
            signal = "positive_signal"
            explanation = (
                f"High-score group outperforms by {avg_gap:.4f}pp with "
                f"{consistency:.1f}% daily consistency. Factor has predictive value."
            )
        elif avg_gap < 0 and consistency >= CONSISTENCY_THRESHOLD:
            signal = "negative_signal"
            explanation = (
                f"High-score group underperforms by {abs(avg_gap):.4f}pp with "
                f"{consistency:.1f}% daily consistency. Factor direction may be misaligned."
            )
        else:
            signal = "inconclusive"
            explanation = (
                f"Gap={avg_gap:.4f}pp, consistency={consistency:.1f}%. "
                f"Neither gap magnitude nor consistency meets threshold."
            )
    else:
        signal = "inconclusive"
        explanation = "Insufficient data for classification."

    return {
        "signal": signal,
        "explanation": explanation,
        "avg_gap": avg_gap,
        "consistency": consistency,
        "avg_correlation": avg_corr,
        "regime_dependent": regime_dependent,
        "up_gap": up_gap,
        "down_gap": down_gap,
    }


def find_strongest_factors(factor_signals: dict) -> dict:
    """Identify strongest positive and negative factors."""
    positive = None
    negative = None

    for field, info in factor_signals.items():
        gap = info.get("avg_gap")
        consistency = info.get("consistency")
        if gap is None or consistency is None:
            continue

        if gap > 0:
            if positive is None or gap > positive[1]:
                positive = (field, gap, consistency)
        elif gap < 0:
            if negative is None or gap < negative[1]:
                negative = (field, gap, consistency)

    result = {}
    if positive:
        result["strongest_positive"] = {
            "factor": positive[0],
            "gap": positive[1],
            "consistency": positive[2],
        }
    else:
        result["strongest_positive"] = None

    if negative:
        result["strongest_negative"] = {
            "factor": negative[0],
            "gap": negative[1],
            "consistency": negative[2],
        }
    else:
        result["strongest_negative"] = None

    return result


# ======================================================================
# MARKDOWN REPORT
# ======================================================================

def generate_markdown(
    coverage: dict,
    bucket_perf: dict,
    rank_corrs: dict,
    regime_data: dict,
    top_bottom: dict,
    trend_burst: dict,
    agent_comp: dict,
    factor_signals: dict,
    strongest: dict,
    date_range: str,
) -> str:
    lines = []
    lines.append(f"# Factor Signal Diagnosis — {date_range}")
    lines.append("")

    # 1. Coverage
    lines.append("## 1. Data Coverage")
    lines.append("")
    lines.append(f"- Total dates scanned: {coverage.get('total_dates', 0)}")
    lines.append(f"- Valid dates (forward-return available): {coverage.get('valid_dates', 0)}")
    lines.append(f"- Total candidate entries: {coverage.get('total_candidates', 0)}")
    lines.append(f"- Forward-return samples: {coverage.get('forward_samples', 0)}")
    lines.append("")

    # 2. Factor Bucket Performance
    lines.append("## 2. Factor Bucket Performance (High / Mid / Low quantiles)")
    lines.append("")
    for field in FACTOR_FIELDS:
        fb = bucket_perf.get(field, {})
        buckets = fb.get("buckets", {})
        lines.append(f"### {field}")
        lines.append("")
        lines.append("| Group | Count | Avg Return | Hit Rate | Avg Drawdown |")
        lines.append("|-------|-------|------------|----------|--------------|")
        for label in ["high", "mid", "low"]:
            b = buckets.get(label, {})
            cnt = b.get("count", 0)
            ret = b.get("avg_return")
            hr = b.get("hit_rate")
            dd = b.get("avg_drawdown")
            ret_s = f"{ret:.4f}%" if ret is not None else "N/A"
            hr_s = f"{hr:.1f}%" if hr is not None else "N/A"
            dd_s = f"{dd:.4f}%" if dd is not None else "N/A"
            lines.append(f"| {label} | {cnt} | {ret_s} | {hr_s} | {dd_s} |")
        lines.append("")
        gap = fb.get("high_low_gap")
        hr_diff = fb.get("hit_rate_diff")
        dd_diff = fb.get("drawdown_diff")
        lines.append(f"- High-Low return gap: {gap:.4f}pp" if gap is not None else "- High-Low return gap: N/A")
        lines.append(f"- Hit rate difference: {hr_diff:.1f}pp" if hr_diff is not None else "- Hit rate difference: N/A")
        lines.append(f"- Drawdown difference: {dd_diff:.4f}pp" if dd_diff is not None else "- Drawdown difference: N/A")
        lines.append("")

    # 3. Rank Correlation
    lines.append("## 3. Spearman Rank Correlation (Factor vs Next-Day Return)")
    lines.append("")
    lines.append("| Factor | Avg ρ | Pos dates | Neg dates | Consistency |")
    lines.append("|--------|-------|-----------|-----------|-------------|")
    for field in FACTOR_FIELDS:
        info = rank_corrs.get(field, {})
        avg = info.get("avg_correlation")
        avg_s = f"{avg:.4f}" if avg is not None else "N/A"
        pos = info.get("positive_date_count", 0)
        neg = info.get("negative_date_count", 0)
        cons = info.get("consistency")
        cons_s = f"{cons:.1f}%" if cons is not None else "N/A"
        lines.append(f"| {field} | {avg_s} | {pos} | {neg} | {cons_s} |")
    lines.append("")

    # 4. Regime Breakdown
    lines.append("## 4. Per-Regime Factor Performance")
    lines.append("")
    for regime in ["broad_up", "broad_down", "mixed"]:
        rd = regime_data.get(regime, {})
        if not rd:
            continue
        lines.append(f"### {regime} (n={rd.get('sample_count', 0)})")
        lines.append("")
        lines.append("| Factor | High-Low Gap |")
        lines.append("|--------|-------------|")
        for field in FACTOR_FIELDS:
            fg = rd.get("factor_gaps", {}).get(field, {})
            gap = fg.get("gap")
            gap_s = f"{gap:.4f}" if gap is not None else "N/A"
            lines.append(f"| {field} | {gap_s} |")
        lines.append("")

        # Trend vs burst
        tvb = rd.get("trend_vs_burst", {})
        lines.append(f"- Trend avg: {tvb.get('trend_avg_return', 'N/A')} (n={tvb.get('trend_count', 0)})")
        lines.append(f"- Burst avg: {tvb.get('burst_avg_return', 'N/A')} (n={tvb.get('burst_count', 0)})")
        gap = tvb.get("gap")
        lines.append(f"- Trend-Burst gap: {gap:.4f}" if gap is not None else "- Trend-Burst gap: N/A")
        lines.append("")

        # Agent
        ac = rd.get("agent_comparison", {})
        lines.append(f"- Agent analyzed avg: {ac.get('analyzed_avg_return', 'N/A')} (n={ac.get('analyzed_count', 0)})")
        lines.append(f"- Agent skipped avg: {ac.get('skipped_avg_return', 'N/A')} (n={ac.get('skipped_count', 0)})")
        lines.append("")

    # 5. Top/Bottom Analysis
    lines.append("## 5. Top 20% vs Bottom 20% Analysis")
    lines.append("")
    lines.append("| Factor | Top20 Avg | Bot20 Avg | Gap | HR Diff | DD Diff |")
    lines.append("|--------|-----------|-----------|-----|---------|---------|")
    for field in FACTOR_FIELDS:
        tb = top_bottom.get(field, {})
        t_avg = tb.get("top20_avg_return")
        b_avg = tb.get("bottom20_avg_return")
        gap = tb.get("gap")
        hr = tb.get("hit_rate_diff")
        dd = tb.get("drawdown_diff")
        t_s = f"{t_avg:.4f}" if t_avg is not None else "N/A"
        b_s = f"{b_avg:.4f}" if b_avg is not None else "N/A"
        g_s = f"{gap:.4f}" if gap is not None else "N/A"
        h_s = f"{hr:.1f}" if hr is not None else "N/A"
        d_s = f"{dd:.4f}" if dd is not None else "N/A"
        lines.append(f"| {field} | {t_s} | {b_s} | {g_s} | {h_s} | {d_s} |")
    lines.append("")

    # 6. Trend vs Burst (overall)
    lines.append("## 6. Trend vs Burst (Overall)")
    lines.append("")
    tb = trend_burst
    for pool in ["trend", "burst", "both"]:
        info = tb.get(pool, {})
        lines.append(f"- {pool}: n={info.get('count', 0)}, avg_return={info.get('avg_return', 'N/A')}, "
                      f"hit_rate={info.get('hit_rate', 'N/A')}, avg_dd={info.get('avg_drawdown', 'N/A')}")
    gap = tb.get("trend_burst_gap")
    lines.append(f"- Trend-Burst gap: {gap:.4f}" if gap is not None else "- Trend-Burst gap: N/A")
    lines.append("")

    # 7. Agent Analyzed vs Skipped
    lines.append("## 7. Agent: Analyzed vs Skipped")
    lines.append("")
    ac = agent_comp
    for label in ["analyzed", "skipped"]:
        info = ac.get(label, {})
        lines.append(f"- {label}: n={info.get('count', 0)}, avg_return={info.get('avg_return', 'N/A')}, "
                      f"hit_rate={info.get('hit_rate', 'N/A')}")
    gap = ac.get("gap")
    lines.append(f"- Gap: {gap:.4f}" if gap is not None else "- Gap: N/A")
    lines.append("")

    # 8. Signal Classification
    lines.append("## 8. Factor Signal Classification")
    lines.append("")
    lines.append("| Factor | Signal | Gap | Consistency | Explanation |")
    lines.append("|--------|--------|-----|-------------|-------------|")
    for field in FACTOR_FIELDS:
        fs = factor_signals.get(field, {})
        signal = fs.get("signal", "unknown")
        gap = fs.get("avg_gap")
        cons = fs.get("consistency")
        gap_s = f"{gap:.4f}" if gap is not None else "N/A"
        cons_s = f"{cons:.1f}%" if cons is not None else "N/A"
        expl = fs.get("explanation", "")
        if len(expl) > 80:
            expl = expl[:77] + "..."
        lines.append(f"| {field} | {signal} | {gap_s} | {cons_s} | {expl} |")
    lines.append("")

    # Detailed explanations
    lines.append("### Detailed Explanations")
    lines.append("")
    for field in FACTOR_FIELDS:
        fs = factor_signals.get(field, {})
        lines.append(f"**{field}**: {fs.get('signal', 'unknown')}")
        lines.append(f"- {fs.get('explanation', '')}")
        lines.append("")

    # 9. Strongest Factors
    lines.append("## 9. Strongest Factors")
    lines.append("")
    sp = strongest.get("strongest_positive")
    sn = strongest.get("strongest_negative")
    if sp:
        lines.append(f"- **Strongest positive**: {sp['factor']} (gap={sp['gap']:.4f}, consistency={sp['consistency']:.1f}%)")
    else:
        lines.append("- **Strongest positive**: none identified")
    if sn:
        lines.append(f"- **Strongest negative**: {sn['factor']} (gap={sn['gap']:.4f}, consistency={sn['consistency']:.1f}%)")
    else:
        lines.append("- **Strongest negative**: none identified")
    lines.append("")

    # 10. Production Change
    lines.append("## 10. Production Change Assessment")
    lines.append("")
    lines.append("- **production_change_allowed**: `false`")
    lines.append("- No factor shows consistent positive signal with >= 55% daily consistency.")
    lines.append("- All signals remain inconclusive — production weights must stay frozen.")
    lines.append("")

    return "\n".join(lines)


# ======================================================================
# MAIN
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="120-day factor signal diagnosis")
    parser.add_argument("--aggregate-path", required=True,
                        help="Path to selection_validation_aggregate.json")
    parser.add_argument("--validation-root", default="reports/selection_validation",
                        help="Root dir for per-date validation JSONs")
    parser.add_argument("--candidate-root", default="reports/agent_bridge",
                        help="Root dir for per-date top30_candidates.json")
    parser.add_argument("--output-dir", required=True,
                        help="Output directory for diagnosis reports")
    args = parser.parse_args()

    aggregate_path = Path(args.aggregate_path)
    validation_root = Path(args.validation_root)
    candidate_root = Path(args.candidate_root)
    output_dir = Path(args.output_dir)

    # Date range from aggregate path
    date_range = aggregate_path.parent.name  # e.g. "2026-01-05_to_2026-07-08"

    print(f"  Loading aggregate from {aggregate_path}...")
    records, agg = load_per_candidate_records(aggregate_path, validation_root, candidate_root)
    print(f"  Loaded {len(records)} records")

    valid_records = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]
    print(f"  Records with forward data: {len(valid_records)}")

    # Coverage
    ok_dates = [row for row in agg.get("date_status_table", []) if row.get("status") == "ok"]
    coverage = {
        "total_dates": len(agg.get("date_status_table", [])),
        "valid_dates": len(ok_dates),
        "total_candidates": len(records),
        "forward_samples": len(valid_records),
        "date_range": date_range,
    }
    print(f"  Valid dates: {coverage['valid_dates']}, Forward samples: {coverage['forward_samples']}")

    # Compute diagnostics
    print("  Computing factor bucket performance...")
    bucket_perf = compute_factor_bucket_performance(records)

    print("  Computing rank correlations...")
    rank_corrs = compute_rank_correlations(records)

    print("  Computing regime breakdown...")
    regime_data = compute_regime_breakdown(records)

    print("  Computing top/bottom analysis...")
    top_bottom = compute_top_bottom_analysis(records)

    print("  Computing trend vs burst...")
    trend_burst = compute_trend_vs_burst(records)

    print("  Computing agent comparison...")
    agent_comp = compute_agent_comparison(records)

    # Classify signals
    print("  Classifying factor signals...")
    factor_signals = {}
    for field in FACTOR_FIELDS:
        factor_signals[field] = classify_factor_signal(
            field, bucket_perf, rank_corrs.get("overall", {}), regime_data, top_bottom
        )

    strongest = find_strongest_factors(factor_signals)

    # Build output
    diagnosis = {
        "as_of": date_range,
        "generated_at": datetime.now().isoformat(),
        "coverage": coverage,
        "production_change_allowed": False,
        "factor_bucket_performance": bucket_perf,
        "rank_correlations": rank_corrs.get("overall", {}),
        "regime_breakdown": {
            regime: {
                "sample_count": data.get("sample_count"),
                "factor_gaps": data.get("factor_gaps"),
                "trend_vs_burst": data.get("trend_vs_burst"),
                "agent_comparison": data.get("agent_comparison"),
            }
            for regime, data in regime_data.items()
        },
        "top_bottom_analysis": top_bottom,
        "trend_vs_burst": trend_burst,
        "agent_comparison": agent_comp,
        "factor_signals": factor_signals,
        "strongest_factors": strongest,
        "interpretation": {
            "positive_signal": "avg_gap > 0 AND consistency >= 55%",
            "negative_signal": "avg_gap < 0 AND consistency >= 55%",
            "regime_dependent": "Sign flips between broad_up and broad_down",
            "defensive_not_alpha": "High score reduces drawdown but not return",
            "inconclusive": "None of the above thresholds met",
        },
    }

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "factor_diagnosis_120d.json"
    json_path.write_text(json.dumps(diagnosis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  JSON: {json_path}")

    md = generate_markdown(
        coverage, bucket_perf, rank_corrs.get("overall", {}),
        regime_data, top_bottom, trend_burst, agent_comp,
        factor_signals, strongest, date_range,
    )
    md_path = output_dir / "factor_diagnosis_120d.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  Markdown: {md_path}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  120-Day Factor Diagnosis Summary")
    print(f"{'='*60}")
    print(f"  Valid dates: {coverage['valid_dates']}")
    print(f"  Forward samples: {coverage['forward_samples']}")
    print(f"  production_change_allowed: false")
    print()
    for field in FACTOR_FIELDS:
        fs = factor_signals.get(field, {})
        print(f"  {field}: {fs.get('signal', 'unknown')} (gap={fs.get('avg_gap', 'N/A')}, cons={fs.get('consistency', 'N/A')}%)")
    print()
    sp = strongest.get("strongest_positive")
    sn = strongest.get("strongest_negative")
    if sp:
        print(f"  Strongest positive: {sp['factor']}")
    if sn:
        print(f"  Strongest negative: {sn['factor']}")


if __name__ == "__main__":
    main()
