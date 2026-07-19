#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险组件质量诊断脚本

诊断 risk decomposition 子组件和 tags 是否有质量、方向是否正确。
不调整公式，不改生产权重，只输出诊断结论。

用法:
  python scripts/diagnose_risk_component_quality.py \
    --validation-root reports/selection_validation \
    --candidate-root reports/agent_bridge \
    --aggregate-path reports/selection_validation/aggregate/2026-06-01_to_2026-07-07/selection_validation_aggregate.json \
    --shadow-path reports/selection_validation/shadow_score/2026-06-01_to_2026-07-07/shadow_decision_score_evaluation.json \
    --output-dir reports/selection_validation/diagnostics/2026-06-01_to_2026-07-07/risk_components
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
# SPEARMAN (reused)
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
    rx, ry = _rank(x), _rank(y)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    sx = math.sqrt(sum((rx[i] - mx) ** 2 for i in range(n)))
    sy = math.sqrt(sum((ry[i] - my) ** 2 for i in range(n)))
    if sx == 0 or sy == 0:
        return 0.0
    return round(cov / (sx * sy), 4)


def _safe(v, default=None):
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ======================================================================
# DATA LOADING
# ======================================================================

def load_records(aggregate_path: Path, validation_root: Path, candidate_root: Path) -> list[dict]:
    agg = json.loads(aggregate_path.read_text(encoding="utf-8"))
    ok_dates = [r["date"] for r in agg.get("date_status_table", []) if r.get("status") == "ok"]

    records = []
    for date in ok_dates:
        val_path = validation_root / date / "next_day_selection_validation.json"
        if not val_path.exists():
            continue
        val = json.loads(val_path.read_text(encoding="utf-8"))
        per_stock = val.get("per_stock", [])

        market_regime = None
        for r in agg.get("date_status_table", []):
            if r["date"] == date:
                market_regime = r.get("market_regime")
                break

        t30_path = candidate_root / date / "top30_candidates.json"
        cand_lookup = {}
        if t30_path.exists():
            try:
                t30 = json.loads(t30_path.read_text(encoding="utf-8"))
                for c in t30.get("candidates", []):
                    cand_lookup[str(c.get("code", ""))] = c
            except Exception:
                pass

        for ps in per_stock:
            code = str(ps.get("code", ""))
            cand = cand_lookup.get(code, {})
            records.append({
                "date": date, "code": code, "name": ps.get("name", ""),
                "market_regime": market_regime,
                "next_return_pct": ps.get("next_return_pct"),
                "data_available": ps.get("data_available", False),
                "decision_score": ps.get("decision_score") or cand.get("decision_score"),
                "stock_short_score": ps.get("stock_short_score") or cand.get("stock_short_score"),
                "stock_trend_score": cand.get("stock_trend_score"),
                "sector_leader_score": cand.get("sector_leader_score"),
                "risk_penalty_score": cand.get("risk_penalty_score"),
                "risk_tags": cand.get("risk_tags", []),
                "trade_eligibility": ps.get("trade_eligibility") or cand.get("trade_eligibility"),
                "source_pool": ps.get("source_pool") or cand.get("source_pool"),
                "hard_risk_penalty": cand.get("hard_risk_penalty"),
                "trade_risk_penalty": cand.get("trade_risk_penalty"),
                "volatility_elasticity_score": cand.get("volatility_elasticity_score"),
                "drawdown_risk_score": cand.get("drawdown_risk_score"),
                "risk_quality_tags": cand.get("risk_quality_tags", []),
                "risk_decomposition_tags": cand.get("risk_decomposition_tags", []),
                "risk_decomposition_breakdown": cand.get("risk_decomposition_breakdown", {}),
                "shadow_decision_score_v2": cand.get("shadow_decision_score_v2"),
            })
    return records


# ======================================================================
# COMPONENT DISTRIBUTION
# ======================================================================

def compute_distribution(values: list[float]) -> dict:
    clean = [v for v in values if v is not None]
    if not clean:
        return {"sample_count": 0, "missing_count": len(values), "min": None, "max": None,
                "mean": None, "std": None, "unique_count": 0, "spread": None,
                "bucket_distribution": {}, "quality_flags": ["excessive_missing"]}

    n = len(clean)
    mn, mx = min(clean), max(clean)
    mean = sum(clean) / n
    var = sum((v - mean) ** 2 for v in clean) / max(1, n - 1)
    std = math.sqrt(var)
    unique = len(set(round(v, 2) for v in clean))
    spread = round(mx - mn, 4)

    buckets = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
    for v in clean:
        if v < 20:
            buckets["0-20"] += 1
        elif v < 40:
            buckets["20-40"] += 1
        elif v < 60:
            buckets["40-60"] += 1
        elif v < 80:
            buckets["60-80"] += 1
        else:
            buckets["80-100"] += 1

    flags = []
    if unique <= 1:
        flags.append("constant_value")
    if spread < 10:
        flags.append("low_spread")
    if unique <= 3 and n > 10:
        flags.append("low_unique_count")
    missing = len(values) - n
    if missing > len(values) * 0.5:
        flags.append("excessive_missing")

    return {
        "sample_count": n, "missing_count": missing,
        "min": round(mn, 4), "max": round(mx, 4),
        "mean": round(mean, 4), "std": round(std, 4),
        "unique_count": unique, "spread": spread,
        "bucket_distribution": buckets, "quality_flags": flags,
    }


# ======================================================================
# COMPONENT-RETURN RELATIONSHIP
# ======================================================================

def compute_return_relationship(records: list[dict], field: str, regime: str | None = None) -> dict:
    subset = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]
    if regime:
        subset = [r for r in subset if r.get("market_regime") == regime]

    vals = [_safe(r.get(field)) for r in subset]
    rets = [_safe(r.get("next_return_pct")) for r in subset]
    aligned = [(v, ret) for v, ret in zip(vals, rets) if v is not None and ret is not None]

    if len(aligned) < 5:
        return {"sample_count": len(aligned), "error": "insufficient_samples"}

    xs = [a[0] for a in aligned]
    ys = [a[1] for a in aligned]
    corr = spearman_correlation(xs, ys)

    # High/low buckets (top/bottom 30%)
    sorted_pairs = sorted(aligned, key=lambda x: x[0], reverse=True)
    n = len(sorted_pairs)
    bn = max(1, int(n * 0.3))
    high_ret = [p[1] for p in sorted_pairs[:bn]]
    low_ret = [p[1] for p in sorted_pairs[-bn:]]
    high_avg = round(sum(high_ret) / len(high_ret), 4) if high_ret else None
    low_avg = round(sum(low_ret) / len(low_ret), 4) if low_ret else None
    gap = round(high_avg - low_avg, 4) if high_avg is not None and low_avg is not None else None

    high_hit = round(sum(1 for r in high_ret if r > 0) / len(high_ret) * 100, 1) if high_ret else None
    low_hit = round(sum(1 for r in low_ret if r > 0) / len(low_ret) * 100, 1) if low_ret else None

    # By date for consistency
    by_date = defaultdict(list)
    for r in subset:
        v = _safe(r.get(field))
        ret = _safe(r.get("next_return_pct"))
        if v is not None and ret is not None:
            by_date[r["date"]].append((v, ret))

    pos_dates, neg_dates = 0, 0
    for date_items in by_date.values():
        if len(date_items) < 3:
            continue
        dc = spearman_correlation([p[0] for p in date_items], [p[1] for p in date_items])
        if dc is not None:
            if dc > 0:
                pos_dates += 1
            elif dc < 0:
                neg_dates += 1

    return {
        "sample_count": n, "spearman_corr": corr,
        "high_bucket_avg": high_avg, "low_bucket_avg": low_avg,
        "high_low_gap": gap, "high_hit_rate": high_hit, "low_hit_rate": low_hit,
        "positive_corr_dates": pos_dates, "negative_corr_dates": neg_dates,
    }


# ======================================================================
# TAG DIAGNOSTICS
# ======================================================================

def compute_tag_diagnostics(records: list[dict], tag_field: str) -> dict:
    """Diagnose each unique tag in a tag field."""
    tag_records: dict[str, list[dict]] = defaultdict(list)
    no_tag_records = []

    for r in records:
        if not r.get("data_available") or r.get("next_return_pct") is None:
            continue
        tags = r.get(tag_field, [])
        if not tags:
            no_tag_records.append(r)
        else:
            for t in tags:
                tag_records[t].append(r)

    no_tag_ret = [_safe(r.get("next_return_pct")) for r in no_tag_records]
    no_tag_avg = round(sum(no_tag_ret) / len(no_tag_ret), 4) if no_tag_ret else None

    results = {}
    for tag, items in sorted(tag_records.items()):
        rets = [_safe(r.get("next_return_pct")) for r in items]
        rets = [r for r in rets if r is not None]
        lows = [_safe(r.get("next_low_return_pct")) for r in items]
        dds = [_safe(r.get("max_intraday_drawdown_pct")) for r in items]

        avg_ret = round(sum(rets) / len(rets), 4) if rets else None
        sorted_rets = sorted(rets)
        median_ret = round(sorted_rets[len(sorted_rets) // 2], 4) if sorted_rets else None
        hit_rate = round(sum(1 for r in rets if r > 0) / len(rets) * 100, 1) if rets else None
        avg_low = round(sum(l for l in lows if l is not None) / max(1, sum(1 for l in lows if l is not None)), 4) if any(l is not None for l in lows) else None
        avg_dd = round(sum(d for d in dds if d is not None) / max(1, sum(1 for d in dds if d is not None)), 4) if any(d is not None for d in dds) else None

        # Regime distribution
        regime_dist = defaultdict(int)
        for r in items:
            regime_dist[r.get("market_regime", "unknown")] += 1

        # Diagnose direction
        flags = []
        if len(rets) < 20:
            flags.append("insufficient_samples")
        if avg_ret is not None and no_tag_avg is not None:
            if avg_ret < no_tag_avg - 0.5:
                flags.append("valid_negative_risk_tag")
            elif avg_ret > no_tag_avg + 0.5:
                flags.append("wrong_direction_tag")

        results[tag] = {
            "sample_count": len(items),
            "avg_return": avg_ret, "median_return": median_ret,
            "hit_rate": hit_rate, "avg_next_low_return": avg_low,
            "avg_max_drawdown": avg_dd,
            "regime_distribution": dict(regime_dist),
            "baseline_avg_return_no_tag": no_tag_avg,
            "flags": flags,
        }

    return {"tags": results, "no_tag_avg_return": no_tag_avg, "no_tag_count": len(no_tag_records)}


# ======================================================================
# TRADE ELIGIBILITY DIAGNOSTICS
# ======================================================================

def compute_eligibility_diagnostics(records: list[dict]) -> dict:
    groups = defaultdict(list)
    for r in records:
        if r.get("data_available") and r.get("next_return_pct") is not None:
            groups[r.get("trade_eligibility", "unknown")].append(r)

    results = {}
    for elig, items in groups.items():
        rets = [_safe(r.get("next_return_pct")) for r in items]
        rets = [r for r in rets if r is not None]
        lows = [_safe(r.get("next_low_return_pct")) for r in items]
        dds = [_safe(r.get("max_intraday_drawdown_pct")) for r in items]
        dates = set(r.get("date") for r in items)

        avg_ret = round(sum(rets) / len(rets), 4) if rets else None
        hit_rate = round(sum(1 for r in rets if r > 0) / len(rets) * 100, 1) if rets else None
        avg_low = round(sum(l for l in lows if l is not None) / max(1, sum(1 for l in lows if l is not None)), 4) if any(l is not None for l in lows) else None
        avg_dd = round(sum(d for d in dds if d is not None) / max(1, sum(1 for d in dds if d is not None)), 4) if any(d is not None for d in dds) else None

        # Regime breakdown
        regime_groups = defaultdict(list)
        for r in items:
            regime_groups[r.get("market_regime", "unknown")].append(r)
        regime_stats = {}
        for reg, reg_items in regime_groups.items():
            reg_rets = [_safe(r.get("next_return_pct")) for r in reg_items]
            reg_rets = [r for r in reg_rets if r is not None]
            regime_stats[reg] = {
                "count": len(reg_items),
                "avg_return": round(sum(reg_rets) / len(reg_rets), 4) if reg_rets else None,
            }

        results[elig] = {
            "sample_count": len(items), "avg_return": avg_ret,
            "hit_rate": hit_rate, "avg_next_low_return": avg_low,
            "avg_max_drawdown": avg_dd, "date_count": len(dates),
            "regime_breakdown": regime_stats,
        }

    # Diagnose
    flags = []
    focus_ret = results.get("focus", {}).get("avg_return")
    avoid_ret = results.get("avoid", {}).get("avg_return")
    if focus_ret is not None and avoid_ret is not None and avoid_ret > focus_ret:
        flags.append("avoid_not_valid_as_negative_filter")

    backup_down = results.get("backup", {}).get("regime_breakdown", {}).get("broad_down", {})
    focus_down = results.get("focus", {}).get("regime_breakdown", {}).get("broad_down", {})
    if backup_down.get("avg_return") is not None and focus_down.get("avg_return") is not None:
        if backup_down["avg_return"] > focus_down["avg_return"]:
            flags.append("backup_defensive_value")

    if focus_ret is not None and focus_ret <= 0:
        flags.append("focus_not_alpha_group")

    return {"groups": results, "flags": flags}


# ======================================================================
# ROOT CAUSES
# ======================================================================

def identify_root_causes(
    distributions: dict,
    return_rels: dict,
    tag_diag: dict,
    elig_diag: dict,
) -> list[dict]:
    causes = []

    # hard_risk
    hr_dist = distributions.get("hard_risk_penalty", {})
    if hr_dist.get("quality_flags"):
        if "constant_value" in hr_dist["quality_flags"]:
            causes.append({
                "cause": "hard_risk_penalty_constant_due_to_partial_data_risk",
                "evidence": f"hard_risk_penalty unique={hr_dist['unique_count']}, spread={hr_dist.get('spread')}. All candidates get the same partial_data_risk penalty.",
                "severity": "high",
            })

    # elasticity
    elast_rel = return_rels.get("volatility_elasticity_score", {})
    if elast_rel.get("high_low_gap") is not None and elast_rel["high_low_gap"] < 0:
        causes.append({
            "cause": "elasticity_definition_captures_overheat_not_alpha",
            "evidence": f"volatility_elasticity high bucket avg={elast_rel.get('high_bucket_avg')}, low bucket avg={elast_rel.get('low_bucket_avg')}, gap={elast_rel['high_low_gap']}. High elasticity stocks underperform.",
            "severity": "high",
        })

    # drawdown
    dd_dist = distributions.get("drawdown_risk_score", {})
    if dd_dist.get("spread") is not None and dd_dist["spread"] < 10:
        causes.append({
            "cause": "drawdown_risk_underpowered",
            "evidence": f"drawdown_risk_score spread={dd_dist['spread']}, unique={dd_dist['unique_count']}. Insufficient variation to be predictive.",
            "severity": "medium",
        })

    # tags
    all_tag_flags = []
    for tag_info in tag_diag.get("tags", {}).values():
        all_tag_flags.extend(tag_info.get("flags", []))
    wrong_count = sum(1 for f in all_tag_flags if f == "wrong_direction_tag")
    valid_count = sum(1 for f in all_tag_flags if f == "valid_negative_risk_tag")
    if wrong_count > valid_count:
        causes.append({
            "cause": "risk_tags_direction_mixed",
            "evidence": f"wrong_direction_tag count={wrong_count}, valid_negative_risk_tag count={valid_count}. More tags point wrong way than right.",
            "severity": "high",
        })

    # eligibility
    elig_flags = elig_diag.get("flags", [])
    if "avoid_not_valid_as_negative_filter" in elig_flags:
        causes.append({
            "cause": "trade_eligibility_not_predictive",
            "evidence": "avoid group average return > focus group. Eligibility ordering is inverted.",
            "severity": "high",
        })
    if "focus_not_alpha_group" in elig_flags:
        causes.append({
            "cause": "trade_eligibility_not_predictive",
            "evidence": "focus group has non-positive average return.",
            "severity": "medium",
        })

    # insufficient samples
    insuff_tags = [t for t, info in tag_diag.get("tags", {}).items()
                   if "insufficient_samples" in info.get("flags", [])]
    if insuff_tags:
        causes.append({
            "cause": "insufficient_tag_samples",
            "evidence": f"Tags with <20 samples: {', '.join(insuff_tags[:5])}",
            "severity": "low",
        })

    # missing intraday
    missing_intraday = sum(1 for r in tag_diag.get("tags", {}).values()
                          if r.get("avg_max_drawdown") is None)
    if missing_intraday > 0:
        causes.append({
            "cause": "missing_intraday_features",
            "evidence": f"{missing_intraday} tags missing intraday drawdown data.",
            "severity": "low",
        })

    return causes


# ======================================================================
# RECOMMENDATIONS
# ======================================================================

def build_recommendations(root_causes: list[dict]) -> list[dict]:
    cause_set = {rc["cause"] for rc in root_causes}
    recs = []

    if "hard_risk_penalty_constant_due_to_partial_data_risk" in cause_set:
        recs.append({
            "action": "split_partial_data_risk_out_of_hard_risk",
            "reason": "hard_risk_penalty is constant because all candidates share partial_data_risk. Separate data-quality risk from structural risk (ST/delisted/liquidity).",
            "production_change_allowed": False,
        })
    if "elasticity_definition_captures_overheat_not_alpha" in cause_set:
        recs.append({
            "action": "recalibrate_elasticity_as_alpha_candidate_not_risk_component",
            "reason": "volatility_elasticity_score is negatively correlated with returns. High-elasticity stocks underperform. Consider whether elasticity should be an alpha signal or removed entirely.",
            "production_change_allowed": False,
        })
    if "drawdown_risk_underpowered" in cause_set:
        recs.append({
            "action": "redesign_drawdown_risk_with_high_low_close_features",
            "reason": "drawdown_risk_score has insufficient spread. Use actual intraday high/low/close patterns instead of rule-based proxies.",
            "production_change_allowed": False,
        })
    if "risk_tags_direction_mixed" in cause_set:
        recs.append({
            "action": "tag_level_blacklist_or_whitelist_experiment",
            "reason": "More risk tags point wrong direction than right. Test tag-level blacklisting or whitelisting before using tags in scoring.",
            "production_change_allowed": False,
        })
    if "trade_eligibility_not_predictive" in cause_set:
        recs.append({
            "action": "regime_specific_risk_tag_validation",
            "reason": "Trade eligibility groups do not separate returns. Test eligibility within specific market regimes.",
            "production_change_allowed": False,
        })

    recs.append({
        "action": "do_not_change_production_weights",
        "reason": "Risk component quality is insufficient for production changes. All recommendations are experimental.",
        "production_change_allowed": False,
    })

    return recs


# ======================================================================
# MARKDOWN
# ======================================================================

def generate_markdown(output: dict) -> str:
    L = []
    L.append("# Risk Component Quality Diagnosis — 2026-06-01 to 2026-07-07")
    L.append("")

    # 1
    L.append("## 1. Executive Summary")
    L.append("")
    for rc in output.get("root_causes", []):
        L.append(f"- **{rc['cause']}** (severity: {rc['severity']}): {rc['evidence'][:120]}")
    L.append("")

    # 2
    cov = output.get("dataset_summary", {})
    L.append("## 2. Dataset Summary")
    L.append("")
    L.append(f"- Valid dates: {cov.get('valid_date_count', 0)}")
    L.append(f"- Total records: {cov.get('total_records', 0)}")
    L.append(f"- Records with forward data: {cov.get('records_with_data', 0)}")
    L.append("")

    # 3
    L.append("## 3. Component Distribution")
    L.append("")
    L.append(f"| {'Component':<30} {'N':>5} {'Min':>7} {'Max':>7} {'Mean':>7} {'Spread':>7} {'Unique':>7} {'Flags'} |")
    L.append(f"|{'─'*32}|{'─'*7}|{'─'*9}|{'─'*9}|{'─'*9}|{'─'*9}|{'─'*9}|{'─'*20}|")
    for comp in ["risk_penalty_score", "hard_risk_penalty", "trade_risk_penalty", "volatility_elasticity_score", "drawdown_risk_score", "shadow_decision_score_v2"]:
        d = output.get("distributions", {}).get(comp, {})
        n = d.get("sample_count", 0)
        mn = f"{d['min']:.1f}" if d.get("min") is not None else "N/A"
        mx = f"{d['max']:.1f}" if d.get("max") is not None else "N/A"
        mean = f"{d['mean']:.1f}" if d.get("mean") is not None else "N/A"
        spread = f"{d['spread']:.1f}" if d.get("spread") is not None else "N/A"
        unique = d.get("unique_count", 0)
        flags = ", ".join(d.get("quality_flags", [])) or "—"
        L.append(f"| {comp:<30} {n:>5} {mn:>7} {mx:>7} {mean:>7} {spread:>7} {unique:>7} {flags} |")
    L.append("")

    # 4
    L.append("## 4. Component Return Relationship")
    L.append("")
    L.append(f"| {'Component':<30} {'Corr':>8} {'High Avg':>9} {'Low Avg':>9} {'Gap':>8} {'High Hit':>9} {'Low Hit':>8} |")
    L.append(f"|{'─'*32}|{'─'*10}|{'─'*11}|{'─'*11}|{'─'*10}|{'─'*11}|{'─'*10}|")
    for comp in ["risk_penalty_score", "hard_risk_penalty", "trade_risk_penalty", "volatility_elasticity_score", "drawdown_risk_score"]:
        rr = output.get("return_relationships", {}).get(comp, {})
        corr = rr.get("spearman_corr")
        h = rr.get("high_bucket_avg")
        l = rr.get("low_bucket_avg")
        g = rr.get("high_low_gap")
        hh = rr.get("high_hit_rate")
        lh = corr_low_hit = rr.get("low_hit_rate")
        L.append(f"| {comp:<30} {corr if corr is not None else 'N/A':>8} "
                 f"{f'{h:.2f}' if h is not None else 'N/A':>9} "
                 f"{f'{l:.2f}' if l is not None else 'N/A':>9} "
                 f"{f'{g:.2f}' if g is not None else 'N/A':>8} "
                 f"{f'{hh:.1f}' if hh is not None else 'N/A':>9} "
                 f"{f'{lh:.1f}' if lh is not None else 'N/A':>8} |")
    L.append("")

    # 5
    L.append("## 5. Risk Tag Return Diagnostics")
    L.append("")
    raw_tag_diag = output.get("tag_diagnostics", {})
    if "tags" in raw_tag_diag:
        tag_diag = raw_tag_diag
    else:
        risk_tag_diag = raw_tag_diag.get("risk_tags", {})
        merged_tags = {}
        for tag_group in (
            "risk_tags",
            "risk_decomposition_tags",
            "risk_quality_tags",
        ):
            merged_tags.update(raw_tag_diag.get(tag_group, {}).get("tags", {}))
        tag_diag = {
            "tags": merged_tags,
            "no_tag_avg_return": risk_tag_diag.get("no_tag_avg_return"),
            "no_tag_count": risk_tag_diag.get("no_tag_count", 0),
        }
    L.append(f"Baseline avg return (no tag): {tag_diag.get('no_tag_avg_return', 'N/A')}")
    L.append(f"Baseline count: {tag_diag.get('no_tag_count', 0)}")
    L.append("")
    L.append(f"| {'Tag':<35} {'N':>5} {'Avg Ret':>9} {'Hit%':>6} {'Avg Low':>9} {'Flags'} |")
    L.append(f"|{'─'*37}|{'─'*7}|{'─'*11}|{'─'*8}|{'─'*11}|{'─'*30}|")
    for tag, info in sorted(tag_diag.get("tags", {}).items(), key=lambda x: -x[1].get("sample_count", 0)):
        n = info.get("sample_count", 0)
        avg = info.get("avg_return")
        hit = info.get("hit_rate")
        low = info.get("avg_next_low_return")
        flags = ", ".join(info.get("flags", [])) or "—"
        L.append(f"| {tag:<35} {n:>5} {f'{avg:.2f}' if avg is not None else 'N/A':>9} "
                 f"{f'{hit:.1f}' if hit is not None else 'N/A':>6} "
                 f"{f'{low:.2f}' if low is not None else 'N/A':>9} {flags} |")
    L.append("")

    # 6
    L.append("## 6. Trade Eligibility Diagnostics")
    L.append("")
    elig = output.get("eligibility_diagnostics", {})
    L.append(f"Flags: {', '.join(elig.get('flags', [])) or 'none'}")
    L.append("")
    L.append(f"| {'Eligibility':<15} {'N':>5} {'Avg Ret':>9} {'Hit%':>6} {'Avg Low':>9} {'Dates':>6} |")
    L.append(f"|{'─'*17}|{'─'*7}|{'─'*11}|{'─'*8}|{'─'*11}|{'─'*8}|")
    for elig_name in ["focus", "watch", "backup", "avoid"]:
        info = elig.get("groups", {}).get(elig_name, {})
        n = info.get("sample_count", 0)
        avg = info.get("avg_return")
        hit = info.get("hit_rate")
        low = info.get("avg_next_low_return")
        dates = info.get("date_count", 0)
        L.append(f"| {elig_name:<15} {n:>5} {f'{avg:.2f}' if avg is not None else 'N/A':>9} "
                 f"{f'{hit:.1f}' if hit is not None else 'N/A':>6} "
                 f"{f'{low:.2f}' if low is not None else 'N/A':>9} {dates:>6} |")
    L.append("")

    # 7
    L.append("## 7. Root Causes")
    L.append("")
    for rc in output.get("root_causes", []):
        L.append(f"### {rc['cause']}")
        L.append(f"- Severity: {rc['severity']}")
        L.append(f"- Evidence: {rc['evidence']}")
        L.append("")

    # 8
    L.append("## 8. Recommendations")
    L.append("")
    for rec in output.get("recommendations", []):
        L.append(f"- **{rec['action']}**: {rec['reason']}")
    L.append("")

    # 9
    L.append("## 9. Do Not Change Production Yet")
    L.append("")
    L.append("All `production_change_allowed = false`. Risk component quality is insufficient.")
    L.append("Do not modify production scoring until component definitions are redesigned.")
    L.append("")

    return "\n".join(L)


# ======================================================================
# MAIN
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="Diagnose risk component quality")
    parser.add_argument("--validation-root", default="reports/selection_validation")
    parser.add_argument("--candidate-root", default="reports/agent_bridge")
    parser.add_argument("--aggregate-path", required=True)
    parser.add_argument("--shadow-path", default=None)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    validation_root = Path(args.validation_root)
    candidate_root = Path(args.candidate_root)
    aggregate_path = Path(args.aggregate_path)
    output_dir = Path(args.output_dir)

    print(f"  Loading records...")
    records = load_records(aggregate_path, validation_root, candidate_root)
    valid = [r for r in records if r.get("data_available") and r.get("next_return_pct") is not None]
    print(f"  Total: {len(records)}, with forward data: {len(valid)}")

    # Coverage
    agg = json.loads(aggregate_path.read_text(encoding="utf-8"))
    coverage = agg.get("coverage_summary", {})
    coverage["total_records"] = len(records)
    coverage["records_with_data"] = len(valid)

    # 1. Component distributions
    print(f"  Computing distributions...")
    distributions = {}
    for field in ["risk_penalty_score", "hard_risk_penalty", "trade_risk_penalty",
                  "volatility_elasticity_score", "drawdown_risk_score", "shadow_decision_score_v2"]:
        vals = [_safe(r.get(field)) for r in records]
        distributions[field] = compute_distribution(vals)

    # 2. Component-return relationships
    print(f"  Computing return relationships...")
    return_rels = {}
    for field in ["risk_penalty_score", "hard_risk_penalty", "trade_risk_penalty",
                  "volatility_elasticity_score", "drawdown_risk_score"]:
        return_rels[field] = compute_return_relationship(records, field)

    # 3. Tag diagnostics
    print(f"  Computing tag diagnostics...")
    risk_tag_diag = compute_tag_diagnostics(records, "risk_tags")
    decomp_tag_diag = compute_tag_diagnostics(records, "risk_decomposition_tags")
    quality_tag_diag = compute_tag_diagnostics(records, "risk_quality_tags")

    # 4. Trade eligibility
    print(f"  Computing eligibility diagnostics...")
    elig_diag = compute_eligibility_diagnostics(records)

    # 5. Root causes
    root_causes = identify_root_causes(distributions, return_rels,
                                        {"tags": {**risk_tag_diag.get("tags", {}), **decomp_tag_diag.get("tags", {}), **quality_tag_diag.get("tags", {})}},
                                        elig_diag)

    # 6. Recommendations
    recommendations = build_recommendations(root_causes)

    # Build output
    output = {
        "as_of": "2026-06-01 to 2026-07-07",
        "dataset_summary": coverage,
        "distributions": distributions,
        "return_relationships": return_rels,
        "tag_diagnostics": {
            "risk_tags": risk_tag_diag,
            "risk_decomposition_tags": decomp_tag_diag,
            "risk_quality_tags": quality_tag_diag,
        },
        "eligibility_diagnostics": elig_diag,
        "root_causes": root_causes,
        "recommendations": recommendations,
    }

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "risk_component_quality.json"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ JSON: {json_path}")

    md_path = output_dir / "risk_component_quality.md"
    md_path.write_text(generate_markdown(output), encoding="utf-8")
    print(f"  ✅ Markdown: {md_path}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  Root Causes:")
    for rc in root_causes:
        print(f"  🔴 [{rc['severity']}] {rc['cause']}")
    print(f"\n  Recommendations:")
    for rec in recommendations:
        print(f"  📋 {rec['action']}")
    print(f"\n  All production_change_allowed: false")


if __name__ == "__main__":
    main()
