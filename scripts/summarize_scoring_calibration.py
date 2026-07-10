#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scoring Calibration Summary Script

Reads aggregate_scoring_calibration.json and produces:
1. scoring_calibration_summary.json - with evidence ratings, recommendations, and data quality
2. scoring_calibration_summary.md - human-readable summary

Usage:
  python scripts/summarize_scoring_calibration.py \\
    --aggregate-path reports/scoring_calibration/aggregate/2026-07-01_to_2026-07-08/aggregate_scoring_calibration.json \\
    --bridge-root reports/agent_bridge \\
    --min-aihf-coverage 0.5
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Evidence classification
# ---------------------------------------------------------------------------

def classify_evidence(sample_count: int) -> str:
    """Classify evidence strength based on sample count.

    Returns one of: ``no_data``, ``thin``, ``usable``, ``strong``.
    """
    if sample_count == 0:
        return "no_data"
    if sample_count < 10:
        return "thin"
    if sample_count < 30:
        return "usable"
    return "strong"


# ---------------------------------------------------------------------------
# AIHF coverage computation (mirrors run_daily_bridge_report logic)
# ---------------------------------------------------------------------------

def compute_aihf_coverage_for_date(date: str, bridge_root: Path) -> dict:
    """Compute AIHF ranking coverage for a single date.

    Tries to read from daily_bridge_report.json first (if aihf_coverage exists),
    otherwise computes on-the-fly from top30_candidates.json + aihf_stock_ranking.json.
    """
    # Try bridge report first
    bridge_path = bridge_root / date / "daily_bridge_report.json"
    if bridge_path.exists():
        try:
            report = json.loads(bridge_path.read_text(encoding="utf-8"))
            cov = report.get("aihf_coverage", {})
            if cov and cov.get("top30_candidate_count", 0) > 0:
                return cov
        except Exception:
            pass

    # Compute on-the-fly
    top30_path = bridge_root / date / "top30_candidates.json"
    ranking_path = bridge_root / date / "aihf_stock_ranking.json"

    result = {
        "top30_candidate_count": 0,
        "aihf_input_coverage_ratio": 0.0,
        "coverage_status": "missing_data",
        "rerun_aihf_bridge_recommended": False,
        "coverage_risk_reason": "",
        "excluded_candidate_codes": [],
    }

    if not top30_path.exists():
        result["coverage_risk_reason"] = "top30_candidates.json not found"
        return result

    try:
        top30 = json.loads(top30_path.read_text(encoding="utf-8"))
        candidates = top30.get("candidates", [])
        result["top30_candidate_count"] = len(candidates)
    except Exception:
        result["coverage_risk_reason"] = "failed to parse top30_candidates.json"
        return result

    if not ranking_path.exists():
        result["coverage_risk_reason"] = "aihf_stock_ranking.json not found"
        return result

    try:
        ranking = json.loads(ranking_path.read_text(encoding="utf-8"))
        items = ranking.get("items", [])
        rank_codes = {str(i.get("code", "")).strip() for i in items if i.get("code")}
        cand_codes = {str(c.get("code", "")).strip() for c in candidates if c.get("code")}

        excluded = sorted(cand_codes - rank_codes)
        result["excluded_candidate_codes"] = excluded

        if cand_codes:
            ratio = len(cand_codes & rank_codes) / len(cand_codes)
            result["aihf_input_coverage_ratio"] = round(ratio, 4)

            if ratio < 0.5:
                result["coverage_status"] = "stale_or_mismatched_ranking"
                result["rerun_aihf_bridge_recommended"] = True
                result["coverage_risk_reason"] = (
                    f"ranking coverage below 50% ({result['aihf_input_coverage_ratio']:.1%})"
                )
            elif ratio < 0.8:
                result["coverage_status"] = "partial"
                result["rerun_aihf_bridge_recommended"] = False
                result["coverage_risk_reason"] = (
                    f"ranking covers {result['aihf_input_coverage_ratio']:.1%} of candidates"
                )
            else:
                result["coverage_status"] = "healthy"
                result["rerun_aihf_bridge_recommended"] = False
    except Exception:
        result["coverage_risk_reason"] = "failed to parse aihf_stock_ranking.json"

    return result


def assess_agent_score_data_quality(
    dates: list[str],
    bridge_root: Path,
    min_coverage: float,
) -> dict:
    """Assess agent_score data quality across all dates in the aggregate."""
    healthy = []
    partial = []
    stale = []
    missing_report = []
    excluded = []
    warnings = []

    for date in sorted(dates):
        bridge_path = bridge_root / date / "daily_bridge_report.json"
        if not bridge_path.exists():
            missing_report.append(date)
            warnings.append({
                "date": date,
                "type": "missing_bridge_report",
                "message": f" daily_bridge_report.json not found for {date}",
            })
            continue

        cov = compute_aihf_coverage_for_date(date, bridge_root)
        status = cov.get("coverage_status", "missing_data")
        ratio = cov.get("aihf_input_coverage_ratio", 0.0)

        if status == "stale_or_mismatched_ranking" or ratio < min_coverage:
            stale.append(date)
            excluded.append(date)
            warnings.append({
                "date": date,
                "type": "low_aihf_ranking_coverage",
                "message": (
                    f" {date}: coverage={ratio:.1%}, status={status}. "
                    f"Agent score samples from this date should be interpreted with caution."
                ),
            })
        elif status == "partial":
            partial.append(date)
            warnings.append({
                "date": date,
                "type": "partial_aihf_ranking_coverage",
                "message": (
                    f" {date}: coverage={ratio:.1%}, status=partial. "
                    f"Agent score samples are available but not all candidates covered."
                ),
            })
        else:
            healthy.append(date)

    return {
        "bridge_dates_checked": len(dates),
        "healthy_dates": healthy,
        "partial_dates": partial,
        "stale_or_mismatched_dates": stale,
        "missing_bridge_report_dates": missing_report,
        "excluded_from_agent_score_interpretation": excluded,
        "min_aihf_coverage": min_coverage,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Per-bucket evaluation
# ---------------------------------------------------------------------------

def evaluate_bucket_performance(
    bucket_data: dict,
    bucket_name: str,
    horizon: str = "1d",
) -> dict:
    """Return a flat summary dict for a single bucket."""
    stats = bucket_data.get("horizons", {}).get(horizon, {})
    sample_count = stats.get("sample_count", 0)
    return {
        "bucket": bucket_name,
        "sample_count": sample_count,
        "avg_return_pct": stats.get("avg_return_pct"),
        "hit_rate": stats.get("hit_rate"),
        "evidence": classify_evidence(sample_count),
    }


# ---------------------------------------------------------------------------
# Recommendation logic
# ---------------------------------------------------------------------------

def determine_recommendation(
    layer_name: str,
    buckets: dict,
    candidate_count: int,
    horizon: str = "1d",
    data_quality: dict | None = None,
    influence: dict | None = None,
    market_adjusted: dict | None = None,
    presence_effect: dict | None = None,
    coverage_rollup: dict | None = None,
    exec_rollup: dict | None = None,
) -> dict:
    """Decide what recommendation to emit for a score layer.

    Returns a dict with keys: ``type``, ``reason``, ``evidence``, ``coverage_ratio``, ``notes``.
    """
    performances = {
        name: evaluate_bucket_performance(data, name, horizon)
        for name, data in buckets.items()
    }

    high = performances.get("80+", {})
    mid = performances.get("60-80", {})
    very_low = performances.get("<40", {})
    missing = performances.get("missing", {})

    total_samples = sum(p["sample_count"] for p in performances.values())
    coverage_ratio = total_samples / candidate_count if candidate_count > 0 else 0.0

    base = {
        "type": "insufficient_evidence",
        "reason": "",
        "evidence": classify_evidence(total_samples),
        "coverage_ratio": coverage_ratio,
        "notes": [],
    }

    # ---- Special case: agent_score all missing ----
    missing_bucket = buckets.get("missing", {})
    missing_candidate_count = missing_bucket.get("candidate_count", 0)
    if layer_name == "agent_score" and missing_candidate_count == candidate_count:
        result = {
            **base,
            "type": "missing_field_gap",
            "reason": "agent_score is missing for all candidates",
        }
        _attach_quality_notes(result, data_quality, influence, market_adjusted, presence_effect, coverage_rollup, exec_rollup)
        return result

    # ---- High bucket needs sufficient samples ----
    if high.get("evidence") in ("no_data", "thin"):
        result = {
            **base,
            "type": "insufficient_evidence",
            "reason": f"High bucket (80+) has insufficient samples: {high.get('sample_count', 0)}",
        }
        _attach_quality_notes(result, data_quality, influence, market_adjusted, presence_effect, coverage_rollup, exec_rollup)
        return result

    high_ret = high.get("avg_return_pct")
    mid_ret = mid.get("avg_return_pct")
    very_low_ret = very_low.get("avg_return_pct")

    # ---- Risk filter: very-low bucket notably bad ----
    if (
        very_low.get("evidence") in ("usable", "strong")
        and very_low_ret is not None
        and very_low_ret < -2.0
    ):
        result = {
            **base,
            "type": "risk_filter_candidate",
            "reason": f"Very low bucket (<40) has notably bad performance: {very_low_ret:.2f}%",
        }
        _attach_quality_notes(result, data_quality, influence, market_adjusted, presence_effect, coverage_rollup, exec_rollup)
        return result

    # ---- Downweight: high bucket not better than mid ----
    if high_ret is not None and mid_ret is not None and high_ret <= mid_ret:
        result = {
            **base,
            "type": "downweight_candidate",
            "reason": f"High bucket (80+) not better than mid bucket: {high_ret:.2f}% vs {mid_ret:.2f}%",
        }
        _attach_quality_notes(result, data_quality, influence, market_adjusted, presence_effect, coverage_rollup, exec_rollup)
        return result

    # ---- Keep candidate: high bucket notably better ----
    if high_ret is not None and mid_ret is not None and high_ret > mid_ret + 1.0:
        result = {
            **base,
            "type": "keep_candidate",
            "reason": f"High bucket (80+) performs notably better: {high_ret:.2f}% vs {mid_ret:.2f}%",
        }
        _attach_quality_notes(result, data_quality, influence, market_adjusted, presence_effect, coverage_rollup, exec_rollup)
        return result

    # ---- Default: not enough evidence for a strong call ----
    result = {
        **base,
        "type": "insufficient_evidence",
        "reason": "Insufficient evidence for strong conclusion",
    }
    _attach_quality_notes(result, data_quality, influence, market_adjusted, presence_effect, coverage_rollup, exec_rollup)
    return result


def _attach_quality_notes(result: dict, data_quality: dict | None, influence: dict | None = None, market_adjusted: dict | None = None, presence_effect: dict | None = None, coverage_rollup: dict | None = None, exec_rollup: dict | None = None) -> None:
    """Attach data quality, influence, market-adjusted, presence, and coverage notes."""
    if data_quality:
        excluded = data_quality.get("excluded_from_agent_score_interpretation", [])
        if excluded:
            result["notes"].append(
                "Agent score evidence is quality-limited by stale/mismatched AIHF ranking dates."
            )
            result["notes"].append(
                f"Excluded dates: {', '.join(excluded)}"
            )
    if influence:
        inf_warnings = influence.get("warnings", [])
        has_outlier = any(w["type"] == "single_day_outlier" for w in inf_warnings)
        has_concentrated = any(w["type"] == "positive_evidence_concentrated" for w in inf_warnings)
        if has_outlier or has_concentrated:
            result["notes"].append(
                "Agent score evidence may be influenced by concentrated single-date returns."
            )
    if market_adjusted:
        interp = market_adjusted.get("interpretation", {})
        if not interp.get("has_positive_alpha_signal", False):
            result["notes"].append(
                "Market-adjusted view does not yet show robust agent_score alpha."
            )
    if presence_effect:
        interp = presence_effect.get("interpretation", {})
        if interp.get("has_presence_signal", False):
            result["notes"].append(
                "Agent score presence shows positive separation versus missing-score candidates."
            )
        else:
            result["notes"].append(
                "Agent score presence effect is not yet robust enough for scoring changes."
            )
    if coverage_rollup and presence_effect:
        has_presence = presence_effect.get("interpretation", {}).get("has_presence_signal", False)
        poor_dates = coverage_rollup.get("poor_dates", [])
        if has_presence and poor_dates:
            result["notes"].append(
                "Agent score coverage should be monitored as a candidate-pool quality signal."
            )
    if exec_rollup:
        fallback_dates = exec_rollup.get("fallback_only_dates", [])
        degraded_dates = exec_rollup.get("degraded_dates", [])
        if fallback_dates or degraded_dates:
            result["notes"].append(
                "Agent score calibration is limited by fallback/default agent execution on historical dates."
            )


# ---------------------------------------------------------------------------
# Per-date agent_score analysis
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def compute_agent_score_by_date(
    dates: list[str],
    bridge_root: Path,
    cal_root: Path,
    data_quality: dict | None,
    horizons: tuple[str, ...] = ("1d",),
) -> dict:
    """Compute per-date agent_score bucket breakdown and quality status.

    Reads per-date scoring_calibration.json when available, otherwise
    recomputes from top30_candidates.json + forward_returns.json.
    """
    # Import evaluate_score_layers lazily to avoid circular imports
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.evaluate_scoring_calibration import (
        evaluate_score_layers,
        load_candidates,
        load_forward_returns,
    )

    excluded_set = set(
        (data_quality or {}).get("excluded_from_agent_score_interpretation", [])
    )

    dates_result = {}
    for date in sorted(dates):
        # Try per-date calibration file first
        cal_path = cal_root / date / "scoring_calibration.json"
        cal_data = _load_json(cal_path)

        if cal_data and "agent_score" in cal_data.get("layers", {}):
            agent_layer = cal_data["layers"]["agent_score"]
            buckets = agent_layer.get("buckets", {})
        else:
            # Recompute from top30 + forward_returns
            top30_path = bridge_root / date / "top30_candidates.json"
            returns_path = cal_root.parent / "forward_returns" / date / "forward_returns.json"
            candidates = load_candidates(top30_path) if top30_path.exists() else []
            forward_returns = load_forward_returns(returns_path) if returns_path.exists() else {}
            if candidates:
                full_result = evaluate_score_layers(
                    candidates, forward_returns, horizons=horizons, as_of=date
                )
                buckets = full_result.get("layers", {}).get("agent_score", {}).get("buckets", {})
            else:
                buckets = {}

        # Compute summary stats
        candidate_count = sum(b.get("candidate_count", 0) for b in buckets.values())
        missing_count = buckets.get("missing", {}).get("candidate_count", 0)
        has_agent_score = candidate_count - missing_count
        coverage_ratio = has_agent_score / candidate_count if candidate_count > 0 else 0.0

        # Horizon stats (all buckets including missing)
        horizon_stats = {"sample_count": 0, "avg_return_pct": None, "hit_rate": None}
        returns_list = []
        for bname, bdata in buckets.items():
            h = bdata.get("horizons", {}).get(horizons[0] if horizons else "1d", {})
            sc = h.get("sample_count", 0)
            avg = h.get("avg_return_pct")
            if sc > 0 and avg is not None:
                returns_list.append((sc, avg))
                horizon_stats["sample_count"] += sc
        if returns_list:
            total_sc = sum(s for s, _ in returns_list)
            horizon_stats["avg_return_pct"] = round(
                sum(s * a for s, a in returns_list) / total_sc, 4
            ) if total_sc > 0 else None
            # Recompute hit_rate from all buckets
            hit_count = 0
            for bname, bdata in buckets.items():
                h = bdata.get("horizons", {}).get(horizons[0] if horizons else "1d", {})
                sc = h.get("sample_count", 0)
                hr = h.get("hit_rate")
                if sc > 0 and hr is not None:
                    hit_count += round(hr * sc)
            horizon_stats["hit_rate"] = (
                round(hit_count / horizon_stats["sample_count"], 4)
                if horizon_stats["sample_count"] > 0 else None
            )

        # Bucket distribution
        bucket_dist = {}
        for bname in ("80+", "60-80", "40-60", "<40", "missing"):
            bd = buckets.get(bname, {})
            bucket_dist[bname] = {
                "candidate_count": bd.get("candidate_count", 0),
                "sample_count": bd.get("horizons", {}).get(
                    horizons[0] if horizons else "1d", {}
                ).get("sample_count", 0),
            }

        # Quality status
        quality_status = "unknown"
        if data_quality:
            if date in data_quality.get("stale_or_mismatched_dates", []):
                quality_status = "stale_or_mismatched_ranking"
            elif date in data_quality.get("partial_dates", []):
                quality_status = "partial"
            elif date in data_quality.get("healthy_dates", []):
                quality_status = "healthy"
            elif date in data_quality.get("missing_bridge_report_dates", []):
                quality_status = "missing_bridge_report"

        dates_result[date] = {
            "candidate_count": candidate_count,
            "agent_score_count": has_agent_score,
            "missing_agent_score_count": missing_count,
            "coverage_ratio": round(coverage_ratio, 4),
            "horizons": {horizons[0] if horizons else "1d": horizon_stats},
            "bucket_distribution": bucket_dist,
            "quality_status": quality_status,
            "excluded_from_interpretation": date in excluded_set,
        }

    return {"dates": dates_result}


# ---------------------------------------------------------------------------
# Agent score date influence analysis
# ---------------------------------------------------------------------------

def compute_agent_score_date_influence(by_date: dict) -> dict:
    """Analyze whether agent_score conclusions are dominated by few dates.

    Only dates with samples and not excluded participate.
    """
    dates = by_date.get("dates", {})

    # Filter to eligible dates
    eligible = {}
    for date, d in dates.items():
        if d.get("excluded_from_interpretation"):
            continue
        h = d.get("horizons", {}).get("1d", {})
        if h.get("sample_count", 0) == 0:
            continue
        eligible[date] = {
            "sample_count": h["sample_count"],
            "avg_return_pct": h.get("avg_return_pct"),
            "hit_rate": h.get("hit_rate"),
        }

    if not eligible:
        return {
            "date_count_with_samples": 0,
            "total_samples": 0,
            "top_positive_date": None,
            "top_negative_date": None,
            "max_abs_avg_return_date": None,
            "concentration": {
                "largest_date_sample_share": 0.0,
                "largest_positive_return_contribution_share": 0.0,
            },
            "warnings": [],
        }

    total_samples = sum(d["sample_count"] for d in eligible.values())

    # Find top dates
    top_positive = max(
        eligible.items(),
        key=lambda x: x[1]["avg_return_pct"] if x[1]["avg_return_pct"] is not None else -float("inf"),
    )
    top_negative = min(
        eligible.items(),
        key=lambda x: x[1]["avg_return_pct"] if x[1]["avg_return_pct"] is not None else float("inf"),
    )
    max_abs = max(
        eligible.items(),
        key=lambda x: abs(x[1]["avg_return_pct"]) if x[1]["avg_return_pct"] is not None else 0,
    )

    # Concentration metrics
    largest_date = max(eligible.items(), key=lambda x: x[1]["sample_count"])
    largest_sample_share = largest_date[1]["sample_count"] / total_samples if total_samples > 0 else 0.0

    # Positive return contribution share
    positive_dates = {
        date: d for date, d in eligible.items()
        if d["avg_return_pct"] is not None and d["avg_return_pct"] > 0
    }
    if positive_dates:
        total_positive_samples = sum(d["sample_count"] for d in positive_dates.values())
        largest_pos_date = max(positive_dates.items(), key=lambda x: x[1]["sample_count"])
        positive_contribution_share = (
            largest_pos_date[1]["sample_count"] / total_positive_samples
            if total_positive_samples > 0 else 0.0
        )
    else:
        positive_contribution_share = 0.0

    # Warnings
    warnings = []

    for date, d in eligible.items():
        avg = d["avg_return_pct"]
        sc = d["sample_count"]
        if avg is not None and abs(avg) >= 5.0 and sc >= 5:
            warnings.append({
                "date": date,
                "type": "single_day_outlier",
                "message": f" {date}: avg_return={avg:.2f}%, samples={sc}. Single-day return is abnormally large.",
            })
        if total_samples > 0 and sc / total_samples >= 0.35:
            warnings.append({
                "date": date,
                "type": "sample_concentration",
                "message": f" {date}: {sc}/{total_samples} samples ({sc/total_samples:.1%}). Dominates the aggregate.",
            })

    if positive_contribution_share >= 0.5 and len(positive_dates) > 0:
        pos_date = max(positive_dates.items(), key=lambda x: x[1]["sample_count"])
        warnings.append({
            "date": pos_date[0],
            "type": "positive_evidence_concentrated",
            "message": (
                f" Positive evidence is concentrated in {pos_date[0]} "
                f"({pos_date[1]['sample_count']}/{sum(d['sample_count'] for d in positive_dates.values())} positive samples)."
            ),
        })

    return {
        "date_count_with_samples": len(eligible),
        "total_samples": total_samples,
        "top_positive_date": top_positive[0],
        "top_negative_date": top_negative[0],
        "max_abs_avg_return_date": max_abs[0],
        "concentration": {
            "largest_date_sample_share": round(largest_sample_share, 4),
            "largest_positive_return_contribution_share": round(positive_contribution_share, 4),
        },
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Outlier date context analysis
# ---------------------------------------------------------------------------

def compute_agent_score_outlier_context(
    influence: dict,
    aggregate_data: dict,
    bridge_root: Path,
    cal_root: Path,
) -> dict:
    """Analyze context for dates flagged as single_day_outlier.

    Reads top30_candidates.json and forward_returns.json for each outlier date
    to determine whether the anomaly is market-wide, sector-clustered, or stock-driven.
    """
    # Import helpers lazily
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.evaluate_scoring_calibration import load_candidates, load_forward_returns

    outlier_warnings = [
        w for w in influence.get("warnings", [])
        if w.get("type") == "single_day_outlier"
    ]
    outlier_dates = {w["date"] for w in outlier_warnings}

    # Also exclude dates that are in agent_score_by_date as excluded
    by_date = {}  # will be passed in or read from aggregate
    dates_evaluated = aggregate_data.get("dates_evaluated", [])

    contexts = {}
    for date in sorted(outlier_dates):
        # Skip excluded dates
        # (caller should filter, but double-check)
        top30_path = bridge_root / date / "top30_candidates.json"
        returns_path = cal_root.parent / "forward_returns" / date / "forward_returns.json"

        candidates = load_candidates(top30_path) if top30_path.exists() else []
        forward_returns = load_forward_returns(returns_path) if returns_path.exists() else {}

        if not candidates or not forward_returns:
            contexts[date] = {
                "sample_count": 0,
                "avg_return_pct": None,
                "hit_rate": None,
                "candidate_codes": [],
                "top_return_contributors": [],
                "sector_distribution": {},
                "max_single_stock_return": None,
                "top3_return_contribution_share": 0.0,
                "interpretation": "insufficient_context",
                "notes": ["Missing candidate or forward return data"],
            }
            continue

        # Build code -> candidate lookup
        code_to_candidate = {str(c.get("code", "")).strip(): c for c in candidates if c.get("code")}

        # Build per-stock return + score data
        stock_data = []
        for code, rets in forward_returns.items():
            if not isinstance(rets, dict):
                continue
            r1d = rets.get("1d")
            if r1d is None:
                continue
            cand = code_to_candidate.get(code, {})
            stock_data.append({
                "code": code,
                "forward_return_1d": round(r1d, 4),
                "agent_score": cand.get("agent_score"),
                "sector_name": _extract_sector(cand),
            })

        if not stock_data:
            contexts[date] = {
                "sample_count": 0,
                "avg_return_pct": None,
                "hit_rate": None,
                "candidate_codes": [],
                "top_return_contributors": [],
                "sector_distribution": {},
                "max_single_stock_return": None,
                "top3_return_contribution_share": 0.0,
                "interpretation": "insufficient_context",
                "notes": ["No forward return data with 1d horizon"],
            }
            continue

        # Sort by return
        stock_data.sort(key=lambda x: x["forward_return_1d"], reverse=True)

        # Stats
        returns_all = [s["forward_return_1d"] for s in stock_data]
        avg_return = round(sum(returns_all) / len(returns_all), 4)
        hit_count = sum(1 for r in returns_all if r > 0)
        hit_rate = round(hit_count / len(returns_all), 4) if returns_all else 0.0

        # Top 5 contributors
        top5 = stock_data[:5]

        # Sector distribution
        sector_dist = {}
        for s in stock_data:
            sector = s.get("sector_name", "unknown")
            sector_dist[sector] = sector_dist.get(sector, 0) + 1

        # Max single stock return
        max_return = stock_data[0]["forward_return_1d"] if stock_data else None

        # Top3 return contribution share
        positive_returns = [s for s in stock_data if s["forward_return_1d"] > 0]
        total_positive = sum(s["forward_return_1d"] for s in positive_returns)
        top3_positive = [s for s in stock_data if s["forward_return_1d"] > 0][:3]
        top3_sum = sum(s["forward_return_1d"] for s in top3_positive)
        top3_share = round(top3_sum / total_positive, 4) if total_positive > 0 else 0.0

        # Interpretation
        interpretation, notes = _interpret_outlier(
            top3_share, sector_dist, hit_rate, len(stock_data)
        )

        contexts[date] = {
            "sample_count": len(stock_data),
            "avg_return_pct": avg_return,
            "hit_rate": hit_rate,
            "candidate_codes": [s["code"] for s in stock_data],
            "top_return_contributors": top5,
            "sector_distribution": sector_dist,
            "max_single_stock_return": max_return,
            "top3_return_contribution_share": top3_share,
            "interpretation": interpretation,
            "notes": notes,
        }

    return {"outlier_dates": contexts}


def _extract_sector(candidate: dict) -> str:
    """Extract sector/theme name from candidate fields."""
    # Try common field names
    for key in ("sector_name", "theme_name", "industry_name", "board_name"):
        val = candidate.get(key)
        if val:
            return str(val)
    # Try boards list
    boards = candidate.get("boards", [])
    if boards and isinstance(boards, list):
        return str(boards[0])
    board_types = candidate.get("board_types", [])
    if board_types and isinstance(board_types, list):
        return str(board_types[0])
    return "unknown"


def _interpret_outlier(
    top3_share: float,
    sector_dist: dict,
    hit_rate: float,
    total_stocks: int,
) -> tuple[str, list[str]]:
    """Determine interpretation for an outlier date."""
    notes = []

    # Check top3 concentration
    if top3_share >= 0.7:
        notes.append(f"Top 3 stocks contribute {top3_share:.1%} of positive returns — single-stock driven.")
        return "concentrated_stock_driven", notes

    # Check sector concentration
    if sector_dist:
        max_sector = max(sector_dist.items(), key=lambda x: x[1])
        max_sector_share = max_sector[1] / total_stocks if total_stocks > 0 else 0
        if max_sector_share >= 0.6:
            notes.append(f"Sector '{max_sector[0]}' dominates with {max_sector_share:.1%} of candidates.")
            return "sector_cluster", notes

    # Check market broad rally
    if hit_rate >= 0.8 and len(sector_dist) >= 3:
        notes.append(f"High hit rate ({hit_rate:.1%}) across {len(sector_dist)} sectors — broad market rally.")
        return "market_broad_rally", notes

    # Mixed
    notes.append("Mixed drivers: no single dominant factor.")
    return "mixed", notes


# ---------------------------------------------------------------------------
# Market-adjusted agent_score analysis
# ---------------------------------------------------------------------------

def compute_agent_score_market_adjusted(
    aggregate_data: dict,
    bridge_root: Path,
    cal_root: Path,
    data_quality: dict | None = None,
) -> dict:
    """Compute date-mean-adjusted agent_score returns.

    For each stock on each date, adjusted_return = stock_return - date_mean_return.
    This removes market beta to reveal agent_score alpha.
    """
    sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.evaluate_scoring_calibration import load_candidates, load_forward_returns

    excluded_set = set(
        (data_quality or {}).get("excluded_from_agent_score_interpretation", [])
    )
    dates = aggregate_data.get("dates_evaluated", [])

    # Collect per-date data
    date_data = {}  # date -> list of {code, return_1d, agent_score, bucket}
    for date in sorted(dates):
        if date in excluded_set:
            continue

        top30_path = bridge_root / date / "top30_candidates.json"
        returns_path = cal_root.parent / "forward_returns" / date / "forward_returns.json"

        candidates = load_candidates(top30_path) if top30_path.exists() else []
        forward_returns = load_forward_returns(returns_path) if returns_path.exists() else {}

        if not candidates or not forward_returns:
            continue

        code_to_candidate = {str(c.get("code", "")).strip(): c for c in candidates if c.get("code")}

        stocks = []
        for code, rets in forward_returns.items():
            if not isinstance(rets, dict):
                continue
            r1d = rets.get("1d")
            if r1d is None:
                continue
            cand = code_to_candidate.get(code, {})
            agent_score = cand.get("agent_score")
            # Assign bucket
            if agent_score is None:
                bucket = "missing"
            elif agent_score >= 80:
                bucket = "80+"
            elif agent_score >= 60:
                bucket = "60-80"
            elif agent_score >= 40:
                bucket = "40-60"
            else:
                bucket = "<40"
            stocks.append({
                "code": code,
                "return_1d": r1d,
                "agent_score": agent_score,
                "bucket": bucket,
            })

        if stocks:
            date_data[date] = stocks

    # Compute date baselines and adjusted returns
    date_baselines = {}
    all_adjusted = []  # list of {bucket, adjusted_return, date}

    for date, stocks in date_data.items():
        returns = [s["return_1d"] for s in stocks]
        mean_return = sum(returns) / len(returns) if returns else 0.0

        date_baselines[date] = {
            "candidate_mean_1d_return": round(mean_return, 4),
            "candidate_count": len(stocks),
            "adjusted_sample_count": len(stocks),
        }

        for s in stocks:
            adjusted = s["return_1d"] - mean_return
            all_adjusted.append({
                "bucket": s["bucket"],
                "adjusted_return": round(adjusted, 4),
                "date": date,
            })

    # Aggregate by bucket
    bucket_order = ("80+", "60-80", "40-60", "<40", "missing")
    buckets = {}
    for bname in bucket_order:
        bucket_items = [a for a in all_adjusted if a["bucket"] == bname]
        if not bucket_items:
            buckets[bname] = {
                "sample_count": 0,
                "avg_adjusted_return_pct": None,
                "hit_rate_above_date_mean": None,
            }
            continue
        adjusted_returns = [a["adjusted_return"] for a in bucket_items]
        avg_adj = sum(adjusted_returns) / len(adjusted_returns)
        hit_count = sum(1 for r in adjusted_returns if r > 0)
        hit_rate = hit_count / len(adjusted_returns) if adjusted_returns else 0.0
        buckets[bname] = {
            "sample_count": len(bucket_items),
            "avg_adjusted_return_pct": round(avg_adj, 4),
            "hit_rate_above_date_mean": round(hit_rate, 4),
        }

    # Interpretation
    notes = []
    high_bucket = buckets.get("80+", {})
    mid_bucket = buckets.get("60-80", {})
    high_samples = high_bucket.get("sample_count", 0)
    mid_samples = mid_bucket.get("sample_count", 0)
    high_avg = high_bucket.get("avg_adjusted_return_pct")
    mid_avg = mid_bucket.get("avg_adjusted_return_pct")

    has_positive_alpha = False
    if (high_samples >= 10 and high_avg is not None and high_avg > 0) or \
       (mid_samples >= 10 and mid_avg is not None and mid_avg > 0):
        has_positive_alpha = True
    elif high_samples < 10 and mid_samples < 10:
        notes.append("High agent_score buckets still have insufficient adjusted samples.")

    # Check mid bucket neutrality
    low_bucket = buckets.get("40-60", {})
    low_avg = low_bucket.get("avg_adjusted_return_pct")
    if low_avg is not None and abs(low_avg) < 0.5:
        notes.append("Mid agent_score bucket is mostly date-beta neutral.")

    return {
        "method": "date_mean_adjusted_1d",
        "excluded_dates": sorted(excluded_set),
        "date_baselines": date_baselines,
        "buckets": buckets,
        "interpretation": {
            "has_positive_alpha_signal": has_positive_alpha,
            "notes": notes,
        },
    }


# ---------------------------------------------------------------------------
# Agent score presence effect analysis
# ---------------------------------------------------------------------------

def compute_agent_score_presence_effect(
    market_adjusted: dict,
) -> dict:
    """Compare present vs missing agent_score candidates using date-adjusted returns.

    Reuses the date mean adjustment from compute_agent_score_market_adjusted.
    """
    if not market_adjusted:
        return {
            "method": "agent_score_present_vs_missing_date_adjusted_1d",
            "excluded_dates": [],
            "present": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "missing": {"sample_count": 0, "avg_adjusted_return_pct": None, "hit_rate_above_date_mean": None},
            "spread": {"avg_adjusted_return_pct": None, "hit_rate_diff": None},
            "interpretation": {"has_presence_signal": False, "notes": ["No market-adjusted data available."]},
        }

    excluded_set = set(market_adjusted.get("excluded_dates", []))

    # Collect all adjusted returns with presence info
    # Re-read the raw data to determine presence/missing
    # The market_adjusted dict has buckets but not per-stock presence info
    # We need to reconstruct from the buckets: present = 80+ + 60-80 + 40-60 + <40, missing = missing
    buckets = market_adjusted.get("buckets", {})

    present_items = []
    missing_items = []

    # For the presence effect, we need per-stock adjusted returns
    # Since market_adjusted only stores bucket-level aggregates, we need to
    # recompute from the source data. Let's store per-stock data in market_adjusted.
    # Actually, let's just recompute from the date_baselines and raw data.

    # Hmm, we don't have per-stock data in market_adjusted. Let me check what we have.
    # The buckets have sample_count, avg_adjusted_return_pct, hit_rate_above_date_mean
    # For presence effect, we need present vs missing split.

    # The present group = 80+ + 60-80 + 40-60 + <40 buckets combined
    # The missing group = missing bucket

    present_buckets = ("80+", "60-80", "40-60", "<40")

    # Combine present buckets
    present_samples = 0
    present_weighted_sum = 0.0
    present_hit_count = 0

    for bname in present_buckets:
        bd = buckets.get(bname, {})
        sc = bd.get("sample_count", 0)
        avg = bd.get("avg_adjusted_return_pct")
        hr = bd.get("hit_rate_above_date_mean")
        if sc > 0 and avg is not None:
            present_samples += sc
            present_weighted_sum += sc * avg
        if sc > 0 and hr is not None:
            present_hit_count += round(hr * sc)

    present_avg = round(present_weighted_sum / present_samples, 4) if present_samples > 0 else None
    present_hr = round(present_hit_count / present_samples, 4) if present_samples > 0 else None

    # Missing bucket
    missing_bd = buckets.get("missing", {})
    missing_samples = missing_bd.get("sample_count", 0)
    missing_avg = missing_bd.get("avg_adjusted_return_pct")
    missing_hr = missing_bd.get("hit_rate_above_date_mean")

    # Spread
    if present_avg is not None and missing_avg is not None:
        spread_avg = round(present_avg - missing_avg, 4)
    else:
        spread_avg = None
    if present_hr is not None and missing_hr is not None:
        spread_hr = round(present_hr - missing_hr, 4)
    else:
        spread_hr = None

    # Interpretation
    notes = []
    has_presence = False
    if present_samples >= 30 and missing_samples >= 5 and spread_avg is not None and spread_avg > 1.0:
        has_presence = True
    elif present_samples < 30:
        notes.append("Present group has insufficient samples for robust comparison.")
    elif missing_samples < 5:
        notes.append("Missing group has insufficient samples for robust comparison.")
    elif spread_avg is not None and spread_avg <= 1.0:
        notes.append(f"Spread ({spread_avg:+.2f}%) is below 1.0% threshold.")

    return {
        "method": "agent_score_present_vs_missing_date_adjusted_1d",
        "excluded_dates": sorted(excluded_set),
        "present": {
            "sample_count": present_samples,
            "avg_adjusted_return_pct": present_avg,
            "hit_rate_above_date_mean": present_hr,
        },
        "missing": {
            "sample_count": missing_samples,
            "avg_adjusted_return_pct": missing_avg,
            "hit_rate_above_date_mean": missing_hr,
        },
        "spread": {
            "avg_adjusted_return_pct": spread_avg,
            "hit_rate_diff": spread_hr,
        },
        "interpretation": {
            "has_presence_signal": has_presence,
            "notes": notes,
        },
    }


# ---------------------------------------------------------------------------
# Agent score coverage quality rollup
# ---------------------------------------------------------------------------

def compute_agent_score_coverage_quality_rollup(
    dates: list[str],
    bridge_root: Path,
) -> dict:
    """Roll up agent_score coverage quality across all dates.

    Reads from daily_bridge_report.json if available, otherwise falls back
    to computing from top30_candidates.json directly.
    """
    healthy = []
    partial = []
    poor = []
    ratios = []
    warnings = []

    for date in sorted(dates):
        # Try bridge report first
        bridge_path = bridge_root / date / "daily_bridge_report.json"
        cov_qual = None
        if bridge_path.exists():
            try:
                report = json.loads(bridge_path.read_text(encoding="utf-8"))
                cov_qual = report.get("agent_score_coverage_quality")
            except Exception:
                pass

        # Fallback: compute from top30_candidates.json
        if not cov_qual or cov_qual.get("candidate_count", 0) == 0:
            cov_qual = _compute_coverage_quality_from_top30(bridge_root / date)

        status = cov_qual.get("quality_status", "unknown")
        ratio = cov_qual.get("coverage_ratio", 0.0)

        if status == "healthy":
            healthy.append(date)
        elif status == "partial":
            partial.append(date)
        elif status == "poor":
            poor.append(date)
            warnings.append({
                "date": date,
                "type": "low_agent_score_coverage",
                "message": (
                    f" {date}: coverage={ratio:.1%}, status={status}. "
                    f"Candidate pool quality may be at risk."
                ),
            })

        ratios.append(ratio)

    avg_ratio = round(sum(ratios) / len(ratios), 4) if ratios else 0.0

    return {
        "dates_checked": len(dates),
        "healthy_dates": healthy,
        "partial_dates": partial,
        "poor_dates": poor,
        "avg_coverage_ratio": avg_ratio,
        "warnings": warnings,
    }


def _compute_coverage_quality_from_top30(top30_dir: Path) -> dict:
    """Compute coverage quality from top30_candidates.json directly."""
    top30_path = top30_dir / "top30_candidates.json"
    result = {
        "candidate_count": 0,
        "agent_score_present_count": 0,
        "agent_score_missing_count": 0,
        "coverage_ratio": 0.0,
        "missing_codes": [],
        "quality_status": "unknown",
        "notes": [],
    }

    if not top30_path.exists():
        return result

    try:
        top30 = json.loads(top30_path.read_text(encoding="utf-8"))
        candidates = top30.get("candidates", [])
        result["candidate_count"] = len(candidates)

        present = 0
        missing_codes = []
        for c in candidates:
            code = str(c.get("code", "")).strip()
            has_score = (
                c.get("agent_score") is not None
                or c.get("risk_adjusted_score") is not None
                or c.get("ranking_score") is not None
            )
            if has_score:
                present += 1
            elif code:
                missing_codes.append(code)

        result["agent_score_present_count"] = present
        result["agent_score_missing_count"] = len(missing_codes)
        result["missing_codes"] = sorted(missing_codes)

        if len(candidates) > 0:
            result["coverage_ratio"] = round(present / len(candidates), 4)

        ratio = result["coverage_ratio"]
        if ratio >= 0.8:
            result["quality_status"] = "healthy"
        elif ratio >= 0.5:
            result["quality_status"] = "partial"
        else:
            result["quality_status"] = "poor"

    except Exception:
        pass

    return result


# ---------------------------------------------------------------------------
# Agent execution quality rollup
# ---------------------------------------------------------------------------

def compute_agent_execution_quality_rollup(
    dates: list[str],
    bridge_root: Path,
) -> dict:
    """Roll up agent execution quality across all dates.

    Reads from daily_bridge_report.json if available, otherwise falls back
    to computing from aihf_stock_ranking.json directly.
    """
    healthy = []
    degraded = []
    fallback_only = []
    unknown = []
    default_total = 0
    warnings = []

    for date in sorted(dates):
        # Try bridge report first
        bridge_path = bridge_root / date / "daily_bridge_report.json"
        exec_qual = None
        if bridge_path.exists():
            try:
                report = json.loads(bridge_path.read_text(encoding="utf-8"))
                exec_qual = report.get("agent_execution_quality")
            except Exception:
                pass

        # Fallback: compute from aihf_stock_ranking.json
        if not exec_qual or exec_qual.get("analyzed_stock_count", 0) == 0:
            exec_qual = _compute_execution_quality_from_ranking(bridge_root / date)

        status = exec_qual.get("quality_status", "unknown")
        default_count = exec_qual.get("default_score_count", 0)

        if status == "healthy":
            healthy.append(date)
        elif status == "degraded":
            degraded.append(date)
            warnings.append({
                "date": date,
                "type": "degraded_agent_execution",
                "message": f" {date}: {default_count} stocks have default agent_score.",
            })
        elif status == "fallback_only":
            fallback_only.append(date)
            warnings.append({
                "date": date,
                "type": "fallback_only_agent_execution",
                "message": f" {date}: All agent_score values are default (50.0). Agent execution produced no useful signal.",
            })
        else:
            unknown.append(date)

        default_total += default_count

    return {
        "dates_checked": len(dates),
        "healthy_dates": healthy,
        "degraded_dates": degraded,
        "fallback_only_dates": fallback_only,
        "unknown_dates": unknown,
        "default_score_total": default_total,
        "warnings": warnings,
    }


def _compute_execution_quality_from_ranking(bridge_dir: Path) -> dict:
    """Compute execution quality from aihf_stock_ranking.json directly."""
    ranking_path = bridge_dir / "aihf_stock_ranking.json"

    result = {
        "analyzed_stock_count": 0,
        "succeeded_agent_count": 0,
        "failed_agent_count": 0,
        "default_score_count": 0,
        "quality_status": "unknown",
        "notes": [],
    }

    if not ranking_path.exists():
        return result

    try:
        ranking = json.loads(ranking_path.read_text(encoding="utf-8"))
        items = ranking.get("items", [])
        meta = ranking.get("run_meta", {})

        result["analyzed_stock_count"] = len(items)
        result["succeeded_agent_count"] = len(meta.get("succeeded_agents", []))
        result["failed_agent_count"] = len(meta.get("failed_agents", []))

        if not items:
            return result

        default_count = 0
        for item in items:
            agent_score = item.get("agent_score")
            contributing = item.get("contributing_agents", 0)
            if agent_score == 50.0 and contributing == 0:
                default_count += 1

        result["default_score_count"] = default_count

        failed = result["failed_agent_count"]
        all_default = default_count == len(items)
        no_contrib = all(item.get("contributing_agents", 0) == 0 for item in items)

        if failed == 0 and default_count == 0:
            result["quality_status"] = "healthy"
        elif all_default and no_contrib:
            result["quality_status"] = "fallback_only"
        elif default_count > 0 or failed > 0:
            result["quality_status"] = "degraded"
        else:
            result["quality_status"] = "healthy"

    except Exception:
        pass

    return result


# ---------------------------------------------------------------------------
# Aggregate summary
# ---------------------------------------------------------------------------

def summarize_scoring_calibration(
    aggregate_data: dict,
    data_quality: dict | None = None,
    bridge_root: Path | None = None,
    cal_root: Path | None = None,
) -> dict:
    """Build the summary dict from aggregate calibration data."""
    layers = aggregate_data.get("layers", {})
    candidate_count = aggregate_data.get("coverage", {}).get("candidate_count", 0)
    horizons = aggregate_data.get("horizons", ["1d"])
    primary_horizon = horizons[0] if horizons else "1d"
    dates = aggregate_data.get("dates_evaluated", [])

    summary = {
        "schema_version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "as_of": aggregate_data.get("as_of", ""),
        "dates_evaluated": dates,
        "candidate_count": candidate_count,
        "primary_horizon": primary_horizon,
        "layers": {},
    }

    for layer_name, layer_data in layers.items():
        buckets_summary = {
            bname: evaluate_bucket_performance(bdata, bname, primary_horizon)
            for bname, bdata in layer_data.get("buckets", {}).items()
        }
        summary["layers"][layer_name] = {
            "source_fields": layer_data.get("source_fields", []),
            "buckets": buckets_summary,
            "recommendation": determine_recommendation(
                layer_name,
                layer_data.get("buckets", {}),
                candidate_count,
                primary_horizon,
                data_quality=data_quality if layer_name == "agent_score" else None,
            ),
        }

    if data_quality:
        summary["agent_score_data_quality"] = data_quality

    # Per-date agent_score analysis (compute before layers for influence)
    influence = None
    if dates and bridge_root and cal_root:
        by_date = compute_agent_score_by_date(
            dates, bridge_root, cal_root, data_quality,
            horizons=tuple(horizons),
        )
        summary["agent_score_by_date"] = by_date
        influence = compute_agent_score_date_influence(by_date)
        summary["agent_score_date_influence"] = influence

        # Outlier context analysis
        has_outlier = any(w["type"] == "single_day_outlier" for w in influence.get("warnings", []))
        if has_outlier:
            outlier_ctx = compute_agent_score_outlier_context(
                influence, aggregate_data, bridge_root, cal_root,
            )
            summary["agent_score_outlier_context"] = outlier_ctx

        # Market-adjusted analysis
        market_adj = compute_agent_score_market_adjusted(
            aggregate_data, bridge_root, cal_root, data_quality,
        )
        summary["agent_score_market_adjusted"] = market_adj

        # Presence effect analysis
        presence = compute_agent_score_presence_effect(market_adj)
        summary["agent_score_presence_effect"] = presence

        # Coverage quality rollup
        if bridge_root:
            coverage_rollup = compute_agent_score_coverage_quality_rollup(dates, bridge_root)
            summary["agent_score_coverage_quality_rollup"] = coverage_rollup

            # Pipeline warnings from poor coverage dates
            poor_dates = coverage_rollup.get("poor_dates", [])
            if poor_dates:
                if "pipeline_warnings" not in summary:
                    summary["pipeline_warnings"] = []
                summary["pipeline_warnings"].append({
                    "type": "poor_agent_score_coverage_dates",
                    "severity": "warn",
                    "dates": poor_dates,
                    "avg_coverage_ratio": coverage_rollup.get("avg_coverage_ratio", 0),
                    "message": (
                        f"Poor agent_score coverage on {len(poor_dates)} date(s): "
                        f"{', '.join(poor_dates)}. Candidate pool quality may be at risk."
                    ),
                })

            # Execution quality rollup
            exec_rollup = compute_agent_execution_quality_rollup(dates, bridge_root)
            summary["agent_execution_quality_rollup"] = exec_rollup

            # Pipeline warnings from fallback execution
            fallback_dates = exec_rollup.get("fallback_only_dates", [])
            if fallback_dates:
                if "pipeline_warnings" not in summary:
                    summary["pipeline_warnings"] = []
                summary["pipeline_warnings"].append({
                    "type": "fallback_only_agent_execution",
                    "severity": "warn",
                    "dates": fallback_dates,
                    "message": (
                        f"Fallback-only agent execution on {len(fallback_dates)} date(s): "
                        f"{', '.join(fallback_dates)}. Agent scores are default values."
                    ),
                })

    # Re-compute agent_score recommendation with all notes
    if (influence or market_adj or presence) and "agent_score" in summary.get("layers", {}):
        agent_layer = layers.get("agent_score", {})
        summary["layers"]["agent_score"]["recommendation"] = determine_recommendation(
            "agent_score",
            agent_layer.get("buckets", {}),
            candidate_count,
            primary_horizon,
            data_quality=data_quality,
            influence=influence,
            market_adjusted=market_adj if market_adj else None,
            presence_effect=presence if presence else None,
            coverage_rollup=coverage_rollup if coverage_rollup else None,
            exec_rollup=exec_rollup if exec_rollup else None,
        )

    return summary


# ---------------------------------------------------------------------------
# Markdown generation
# ---------------------------------------------------------------------------

def generate_summary_markdown(summary: dict) -> str:
    """Render the summary as a Markdown document."""
    lines = [
        "# Scoring Calibration Summary",
        "",
        f"**Generated At**: {summary.get('generated_at', '')}",
        f"**As Of**: {summary.get('as_of', '-')}",
        f"**Dates Evaluated**: {', '.join(summary.get('dates_evaluated', []))}",
        f"**Candidate Count**: {summary.get('candidate_count', 0)}",
        f"**Primary Horizon**: {summary.get('primary_horizon', '1d')}",
        "",
        "## Layer Summaries",
        "",
    ]

    for layer_name, layer_data in summary.get("layers", {}).items():
        rec = layer_data.get("recommendation", {})
        lines.append(f"### {layer_name}")
        lines.append("")
        lines.append(f"**Recommendation**: {rec.get('type', 'unknown')}")
        lines.append(f"**Reason**: {rec.get('reason', '')}")
        lines.append(f"**Evidence**: {rec.get('evidence', 'unknown')}")
        lines.append(f"**Coverage Ratio**: {rec.get('coverage_ratio', 0):.1%}")

        # Notes
        notes = rec.get("notes", [])
        if notes:
            lines.append("")
            for note in notes:
                lines.append(f"> ⚠️ {note}")
        lines.append("")

        lines.append("| Bucket | Samples | Avg Return | Hit Rate | Evidence |")
        lines.append("|--------|---------|------------|----------|----------|")
        for bname, bdata in layer_data.get("buckets", {}).items():
            samples = bdata.get("sample_count", 0)
            avg_ret = bdata.get("avg_return_pct")
            hit_rate = bdata.get("hit_rate")
            evidence = bdata.get("evidence", "unknown")
            avg_str = f"{avg_ret:.2f}%" if avg_ret is not None else "-"
            hit_str = f"{hit_rate:.1%}" if hit_rate is not None else "-"
            lines.append(f"| {bname} | {samples} | {avg_str} | {hit_str} | {evidence} |")
        lines.append("")

    # Missing field gaps section
    missing_gaps = [
        lname
        for lname, ldata in summary.get("layers", {}).items()
        if ldata.get("recommendation", {}).get("type") == "missing_field_gap"
    ]
    if missing_gaps:
        lines.append("## Missing Field Gaps")
        lines.append("")
        for gap in missing_gaps:
            lines.append(f"- **{gap}**: All candidates missing this score layer")
        lines.append("")

    # Agent Score Data Quality section
    dq = summary.get("agent_score_data_quality")
    if dq:
        lines.append("## Agent Score Data Quality")
        lines.append("")
        lines.append(f"- **Bridge dates checked**: {dq.get('bridge_dates_checked', 0)}")
        healthy = dq.get("healthy_dates", [])
        partial = dq.get("partial_dates", [])
        stale = dq.get("stale_or_mismatched_dates", [])
        missing_r = dq.get("missing_bridge_report_dates", [])
        lines.append(f"- **Healthy**: {len(healthy)} ({', '.join(healthy) if healthy else '-'})")
        lines.append(f"- **Partial**: {len(partial)} ({', '.join(partial) if partial else '-'})")
        lines.append(f"- **Stale/Mismatched**: {len(stale)} ({', '.join(stale) if stale else '-'})")
        if missing_r:
            lines.append(f"- **Missing bridge report**: {len(missing_r)} ({', '.join(missing_r)})")
        excluded = dq.get("excluded_from_agent_score_interpretation", [])
        lines.append(f"- **Excluded from interpretation**: {len(excluded)} ({', '.join(excluded) if excluded else '-'})")
        lines.append("")

        warnings = dq.get("warnings", [])
        if warnings:
            lines.append("### Warnings")
            lines.append("")
            lines.append("| Date | Type | Message |")
            lines.append("|------|------|---------|")
            for w in warnings:
                lines.append(f"| {w.get('date', '')} | {w.get('type', '')} | {w.get('message', '')} |")
            lines.append("")

    # Agent Score By Date section
    by_date = summary.get("agent_score_by_date", {}).get("dates", {})
    if by_date:
        lines.append("## Agent Score By Date")
        lines.append("")
        lines.append("| Date | Quality | Excluded | Agent Score Coverage | 1d Samples | Avg Return | Hit Rate | Buckets |")
        lines.append("|------|---------|----------|---------------------|------------|------------|----------|---------|")
        for date in sorted(by_date.keys()):
            d = by_date[date]
            quality = d.get("quality_status", "unknown")
            excluded = "Yes" if d.get("excluded_from_interpretation") else "No"
            cov = d.get("coverage_ratio", 0)
            h = d.get("horizons", {}).get("1d", {})
            samples = h.get("sample_count", 0)
            avg_ret = h.get("avg_return_pct")
            hit_rate = h.get("hit_rate")
            bd = d.get("bucket_distribution", {})
            bucket_str = " ".join(
                f"{b}:{bd.get(b, {}).get('candidate_count', 0)}"
                for b in ("80+", "60-80", "40-60", "<40", "missing")
                if bd.get(b, {}).get("candidate_count", 0) > 0
            )
            avg_str = f"{avg_ret:.2f}%" if avg_ret is not None else "-"
            hit_str = f"{hit_rate:.1%}" if hit_rate is not None else "-"
            lines.append(
                f"| {date} | {quality} | {excluded} | {cov:.1%} "
                f"| {samples} | {avg_str} | {hit_str} | {bucket_str} |"
            )
        lines.append("")

    # Agent Score Date Influence section
    influence = summary.get("agent_score_date_influence", {})
    if influence and influence.get("date_count_with_samples", 0) > 0:
        lines.append("## Agent Score Date Influence")
        lines.append("")
        lines.append(f"- **Total samples**: {influence.get('total_samples', 0)}")
        lines.append(f"- **Top positive date**: {influence.get('top_positive_date', '-')}")
        lines.append(f"- **Top negative date**: {influence.get('top_negative_date', '-')}")
        lines.append(f"- **Max abs avg return date**: {influence.get('max_abs_avg_return_date', '-')}")
        conc = influence.get("concentration", {})
        lines.append(f"- **Largest date sample share**: {conc.get('largest_date_sample_share', 0):.1%}")
        lines.append(f"- **Largest positive return contribution share**: {conc.get('largest_positive_return_contribution_share', 0):.1%}")
        lines.append("")

        inf_warnings = influence.get("warnings", [])
        if inf_warnings:
            lines.append("### Warnings")
            lines.append("")
            lines.append("| Date | Type | Message |")
            lines.append("|------|------|---------|")
            for w in inf_warnings:
                lines.append(f"| {w.get('date', '')} | {w.get('type', '')} | {w.get('message', '')} |")
            lines.append("")

    # Agent Score Outlier Context section
    outlier_ctx = summary.get("agent_score_outlier_context", {}).get("outlier_dates", {})
    if outlier_ctx:
        lines.append("## Agent Score Outlier Context")
        lines.append("")
        lines.append("| Date | Interpretation | Avg Return | Hit Rate | Top Contributors | Sector Distribution | Notes |")
        lines.append("|------|---------------|------------|----------|-----------------|--------------------|-------|")
        for date in sorted(outlier_ctx.keys()):
            ctx = outlier_ctx[date]
            interp = ctx.get("interpretation", "unknown")
            avg = ctx.get("avg_return_pct")
            avg_str = f"{avg:.2f}%" if avg is not None else "-"
            hit = ctx.get("hit_rate")
            hit_str = f"{hit:.1%}" if hit is not None else "-"
            # Top contributors (code: return)
            contribs = ctx.get("top_return_contributors", [])
            contrib_str = ", ".join(
                f"{c['code']}({c['forward_return_1d']:+.1f}%)"
                for c in contribs[:3]
            ) if contribs else "-"
            # Sector distribution (top 3)
            sd = ctx.get("sector_distribution", {})
            sd_sorted = sorted(sd.items(), key=lambda x: x[1], reverse=True)[:3]
            sector_str = ", ".join(f"{s}:{n}" for s, n in sd_sorted) if sd_sorted else "-"
            # Notes
            notes = ctx.get("notes", [])
            notes_str = "; ".join(notes[:2]) if notes else "-"
            lines.append(
                f"| {date} | {interp} | {avg_str} | {hit_str} "
                f"| {contrib_str} | {sector_str} | {notes_str} |"
            )
        lines.append("")

    # Agent Score Market-Adjusted View section
    market_adj = summary.get("agent_score_market_adjusted", {})
    if market_adj and market_adj.get("date_baselines"):
        lines.append("## Agent Score Market-Adjusted View")
        lines.append("")
        lines.append(f"- **Method**: {market_adj.get('method', 'unknown')}")
        excluded = market_adj.get("excluded_dates", [])
        if excluded:
            lines.append(f"- **Excluded dates**: {', '.join(excluded)}")
        lines.append("")

        # Date baselines table
        baselines = market_adj.get("date_baselines", {})
        if baselines:
            lines.append("### Date Baselines")
            lines.append("")
            lines.append("| Date | Candidate Mean 1d Return | Candidate Count | Adjusted Samples |")
            lines.append("|------|------------------------|-----------------|------------------|")
            for date in sorted(baselines.keys()):
                b = baselines[date]
                mean_ret = b.get("candidate_mean_1d_return")
                mean_str = f"{mean_ret:+.2f}%" if mean_ret is not None else "-"
                lines.append(
                    f"| {date} | {mean_str} | {b.get('candidate_count', 0)} "
                    f"| {b.get('adjusted_sample_count', 0)} |"
                )
            lines.append("")

        # Bucket table
        buckets = market_adj.get("buckets", {})
        if buckets:
            lines.append("### Adjusted Returns by Agent Score Bucket")
            lines.append("")
            lines.append("| Bucket | Samples | Avg Adjusted Return | Hit Rate Above Date Mean |")
            lines.append("|--------|---------|--------------------|-----------------------|")
            for bname in ("80+", "60-80", "40-60", "<40", "missing"):
                bd = buckets.get(bname, {})
                sc = bd.get("sample_count", 0)
                avg = bd.get("avg_adjusted_return_pct")
                hr = bd.get("hit_rate_above_date_mean")
                avg_str = f"{avg:+.2f}%" if avg is not None else "-"
                hr_str = f"{hr:.1%}" if hr is not None else "-"
                lines.append(f"| {bname} | {sc} | {avg_str} | {hr_str} |")
            lines.append("")

        # Interpretation
        interp = market_adj.get("interpretation", {})
        if interp:
            has_alpha = interp.get("has_positive_alpha_signal", False)
            lines.append(f"**Positive alpha signal**: {'Yes' if has_alpha else 'No'}")
            for note in interp.get("notes", []):
                lines.append(f"> ⚠️ {note}")
            lines.append("")

    # Agent Score Presence Effect section
    presence = summary.get("agent_score_presence_effect", {})
    if presence and (presence.get("present", {}).get("sample_count", 0) > 0 or
                     presence.get("missing", {}).get("sample_count", 0) > 0):
        lines.append("## Agent Score Presence Effect")
        lines.append("")
        lines.append(f"- **Method**: {presence.get('method', 'unknown')}")
        excluded = presence.get("excluded_dates", [])
        if excluded:
            lines.append(f"- **Excluded dates**: {', '.join(excluded)}")
        lines.append("")

        # Present vs Missing table
        present = presence.get("present", {})
        missing = presence.get("missing", {})
        lines.append("| Group | Samples | Avg Adjusted Return | Hit Rate Above Date Mean |")
        lines.append("|-------|---------|--------------------|-----------------------|")

        def _fmt_group(g):
            sc = g.get("sample_count", 0)
            avg = g.get("avg_adjusted_return_pct")
            hr = g.get("hit_rate_above_date_mean")
            avg_str = f"{avg:+.2f}%" if avg is not None else "-"
            hr_str = f"{hr:.1%}" if hr is not None else "-"
            return f"| {sc} | {avg_str} | {hr_str} |"

        lines.append(f"| **Present** {_fmt_group(present)}")
        lines.append(f"| **Missing** {_fmt_group(missing)}")
        lines.append("")

        # Spread
        spread = presence.get("spread", {})
        spread_avg = spread.get("avg_adjusted_return_pct")
        spread_hr = spread.get("hit_rate_diff")
        spread_avg_str = f"{spread_avg:+.2f}%" if spread_avg is not None else "-"
        spread_hr_str = f"{spread_hr:+.1%}" if spread_hr is not None else "-"
        lines.append(f"| **Spread** | {spread_avg_str} | {spread_hr_str} | |")
        lines.append("")

        # Interpretation
        interp = presence.get("interpretation", {})
        has_signal = interp.get("has_presence_signal", False)
        lines.append(f"**Presence signal**: {'Yes' if has_signal else 'No'}")
        for note in interp.get("notes", []):
            lines.append(f"> ⚠️ {note}")
        lines.append("")

    # Agent Score Coverage Quality Rollup section
    cov_rollup = summary.get("agent_score_coverage_quality_rollup", {})
    if cov_rollup and cov_rollup.get("dates_checked", 0) > 0:
        lines.append("## Agent Score Coverage Quality Rollup")
        lines.append("")
        lines.append(f"- **Dates checked**: {cov_rollup.get('dates_checked', 0)}")
        healthy = cov_rollup.get("healthy_dates", [])
        partial = cov_rollup.get("partial_dates", [])
        poor = cov_rollup.get("poor_dates", [])
        avg = cov_rollup.get("avg_coverage_ratio", 0.0)
        lines.append(f"- **Healthy**: {len(healthy)} ({', '.join(healthy) if healthy else '-'})")
        lines.append(f"- **Partial**: {len(partial)} ({', '.join(partial) if partial else '-'})")
        lines.append(f"- **Poor**: {len(poor)} ({', '.join(poor) if poor else '-'})")
        lines.append(f"- **Avg coverage ratio**: {avg:.1%}")
        lines.append("")

        warnings = cov_rollup.get("warnings", [])
        if warnings:
            lines.append("### Warnings")
            lines.append("")
            lines.append("| Date | Type | Message |")
            lines.append("|------|------|---------|")
            for w in warnings:
                lines.append(f"| {w.get('date', '')} | {w.get('type', '')} | {w.get('message', '')} |")
            lines.append("")

    # Pipeline warnings section
    pipeline_warnings = summary.get("pipeline_warnings", [])
    if pipeline_warnings:
        lines.append("## Pipeline Warnings")
        lines.append("")
        for pw in pipeline_warnings:
            severity = pw.get("severity", "warn").upper()
            pw_type = pw.get("type", "unknown")
            msg = pw.get("message", "")
            lines.append(f"- [{severity}] **{pw_type}**: {msg}")
        lines.append("")

    # Agent Execution Quality Rollup section
    exec_rollup = summary.get("agent_execution_quality_rollup", {})
    if exec_rollup and exec_rollup.get("dates_checked", 0) > 0:
        lines.append("## Agent Execution Quality Rollup")
        lines.append("")
        lines.append(f"- **Dates checked**: {exec_rollup.get('dates_checked', 0)}")
        healthy = exec_rollup.get("healthy_dates", [])
        degraded = exec_rollup.get("degraded_dates", [])
        fallback = exec_rollup.get("fallback_only_dates", [])
        unknown = exec_rollup.get("unknown_dates", [])
        lines.append(f"- **Healthy**: {len(healthy)} ({', '.join(healthy) if healthy else '-'})")
        lines.append(f"- **Degraded**: {len(degraded)} ({', '.join(degraded) if degraded else '-'})")
        lines.append(f"- **Fallback-only**: {len(fallback)} ({', '.join(fallback) if fallback else '-'})")
        if unknown:
            lines.append(f"- **Unknown**: {len(unknown)} ({', '.join(unknown)})")
        lines.append(f"- **Default score total**: {exec_rollup.get('default_score_total', 0)}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize scoring calibration")
    parser.add_argument(
        "--aggregate-path",
        required=True,
        help="Path to aggregate_scoring_calibration.json",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: same directory as aggregate file)",
    )
    parser.add_argument(
        "--bridge-root",
        default=str(PROJECT_ROOT / "reports" / "agent_bridge"),
        help="Root directory for agent bridge reports",
    )
    parser.add_argument(
        "--min-aihf-coverage",
        type=float,
        default=0.5,
        help="Minimum AIHF coverage ratio to avoid exclusion (default: 0.5)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    aggregate_path = Path(args.aggregate_path)

    if not aggregate_path.exists():
        print(f"ERROR: Aggregate file not found: {aggregate_path}", file=sys.stderr)
        return 2

    aggregate_data = json.loads(aggregate_path.read_text(encoding="utf-8"))

    # Assess agent score data quality
    dates = aggregate_data.get("dates_evaluated", [])
    bridge_root = Path(args.bridge_root)
    data_quality = None
    if dates and bridge_root.exists():
        data_quality = assess_agent_score_data_quality(
            dates, bridge_root, args.min_aihf_coverage
        )

    summary = summarize_scoring_calibration(
        aggregate_data,
        data_quality=data_quality,
        bridge_root=bridge_root,
        cal_root=aggregate_path.parent.parent.parent,  # reports/scoring_calibration
    )

    output_dir = Path(args.output_dir) if args.output_dir else aggregate_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "scoring_calibration_summary.json"
    md_path = output_dir / "scoring_calibration_summary.md"

    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md_path.write_text(generate_summary_markdown(summary), encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    print()
    print("Recommendations:")
    for layer_name, layer_data in summary.get("layers", {}).items():
        rec = layer_data.get("recommendation", {})
        notes = rec.get("notes", [])
        note_str = f" [{'; '.join(notes)}]" if notes else ""
        print(f"  {layer_name}: {rec.get('type', 'unknown')}{note_str}")

    if data_quality:
        excluded = data_quality.get("excluded_from_agent_score_interpretation", [])
        if excluded:
            print(f"\n⚠️  Excluded dates (low AIHF coverage): {', '.join(excluded)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
