"""Paper-only research helpers for intraday timing factor categories."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median
from typing import Any, Mapping

from theme_sector_radar.timing.factor_catalog import TIMING_FACTOR_CATEGORIES


@dataclass(frozen=True)
class IntradayFactorResearchSpec:
    factor_id: str
    category: str
    direction: str = "higher_is_better"
    description: str = ""


INTRADAY_FACTOR_RESEARCH_SPECS = [
    IntradayFactorResearchSpec("opening_drive_score", "price_momentum", description="Opening launch strength."),
    IntradayFactorResearchSpec("morning_strength_persist_score", "price_momentum", description="Morning momentum persistence."),
    IntradayFactorResearchSpec("late_return_30m_score", "price_momentum", description="Late 30-minute return strength."),
    IntradayFactorResearchSpec("amount_acceleration_score", "volume_money_flow", description="Intraday amount acceleration."),
    IntradayFactorResearchSpec("late_volume_efficiency_score", "volume_money_flow", description="Late volume efficiency."),
    IntradayFactorResearchSpec("volume_spike_exhaustion_score", "volume_money_flow", "lower_is_better", "Volume spike exhaustion risk."),
    IntradayFactorResearchSpec("close_vs_vwap_score", "vwap_mean_price", description="Close price versus VWAP."),
    IntradayFactorResearchSpec("late_price_above_vwap_ratio", "vwap_mean_price", description="Late time-above-VWAP ratio."),
    IntradayFactorResearchSpec("vwap_slope_score", "vwap_mean_price", description="VWAP slope strength."),
    IntradayFactorResearchSpec("vwap_reclaim_score", "vwap_mean_price", description="VWAP reclaim behavior."),
    IntradayFactorResearchSpec("late_high_near_close_score", "intraday_position", description="Close location near intraday high."),
    IntradayFactorResearchSpec("intraday_close_position_score", "intraday_position", description="Close position inside day range."),
    IntradayFactorResearchSpec("intraday_high_pullback_risk_score", "intraday_position", "lower_is_better", "Pullback from intraday high."),
    IntradayFactorResearchSpec("max_gain_giveback_ratio", "intraday_position", "lower_is_better", "Maximum gain giveback ratio."),
    IntradayFactorResearchSpec("sector_late_breadth_score", "sector_confirmation", description="Late sector breadth."),
    IntradayFactorResearchSpec("sector_intraday_breadth_change", "sector_confirmation", description="Sector breadth improvement."),
    IntradayFactorResearchSpec("leader_follower_sync_score", "sector_confirmation", description="Leader/follower synchronization."),
    IntradayFactorResearchSpec("intraday_sector_breadth_score", "sector_confirmation", description="Intraday sector breadth."),
    IntradayFactorResearchSpec("stock_vs_sector_intraday_alpha", "relative_strength", description="Stock alpha versus sector intraday."),
    IntradayFactorResearchSpec("sector_peer_rank_score", "relative_strength", description="Candidate peer rank inside sector."),
    IntradayFactorResearchSpec("market_regime_score", "relative_strength", description="Market regime support."),
    IntradayFactorResearchSpec("sector_leader_score", "relative_strength", description="Sector leadership score."),
    IntradayFactorResearchSpec("high_to_close_drawdown_score", "risk_reversal", "lower_is_better", "High-to-close drawdown risk."),
    IntradayFactorResearchSpec("morning_spike_fade_score", "risk_reversal", "lower_is_better", "Morning spike fade risk."),
    IntradayFactorResearchSpec("afternoon_fade_score", "risk_reversal", "lower_is_better", "Afternoon fade risk."),
    IntradayFactorResearchSpec("volume_without_price_progress_risk", "risk_reversal", "lower_is_better", "Volume without price progress risk."),
    IntradayFactorResearchSpec("intraday_late_strength_score", "time_structure", description="Late-session strength."),
    IntradayFactorResearchSpec("morning_pullback_repair_score", "time_structure", description="Morning pullback repair."),
    IntradayFactorResearchSpec("open_to_midday_resilience_score", "time_structure", description="Open-to-midday resilience."),
    IntradayFactorResearchSpec("short_burst_intraday_emotion_score_shadow", "time_structure", description="Short-burst intraday emotion overlay."),
]


def evaluate_intraday_factor_research(
    samples: list[Mapping[str, Any]],
    *,
    return_field: str = "forward_return_pct",
    min_labeled_samples: int = 20,
    win_return_pct: float = 0.0,
    thresholds: list[float] | None = None,
) -> dict[str, Any]:
    thresholds = thresholds or [40.0, 50.0, 60.0, 70.0, 80.0]
    factor_reports = {
        spec.factor_id: _evaluate_factor(samples, spec, return_field, min_labeled_samples, win_return_pct, thresholds)
        for spec in INTRADAY_FACTOR_RESEARCH_SPECS
    }
    category_reports = {
        category: _category_report(category, factor_reports)
        for category in TIMING_FACTOR_CATEGORIES
    }
    valuable = [
        report for report in factor_reports.values()
        if report["rating"] in {"valuable", "watchlist"}
    ]
    valuable.sort(key=lambda item: (item.get("value_score") or -999.0), reverse=True)
    pending = [
        report for report in factor_reports.values()
        if report["rating"] == "insufficient_labeled_samples"
    ]
    return {
        "schema_version": "intraday_factor_research.v1",
        "summary": {
            "sample_count": len(samples),
            "labeled_sample_count": sum(1 for row in samples if _float(row.get(return_field)) is not None),
            "category_count": len(category_reports),
            "factor_count": len(factor_reports),
            "valuable_factor_count": len([item for item in valuable if item["rating"] == "valuable"]),
            "watchlist_factor_count": len([item for item in valuable if item["rating"] == "watchlist"]),
            "pending_validation_factor_count": len(pending),
            "return_field": return_field,
            "min_labeled_samples": min_labeled_samples,
        },
        "categories": category_reports,
        "factors": factor_reports,
        "valuable_factors": valuable,
        "shadow_only": True,
        "paper_trading_only": True,
        "does_not_modify_official_scores": True,
        "no_execution_signals": True,
    }


def _evaluate_factor(
    samples: list[Mapping[str, Any]],
    spec: IntradayFactorResearchSpec,
    return_field: str,
    min_labeled_samples: int,
    win_return_pct: float,
    thresholds: list[float],
) -> dict[str, Any]:
    rows = []
    for sample in samples:
        value = _float(sample.get(spec.factor_id))
        ret = _float(sample.get(return_field))
        if value is None:
            continue
        rows.append({"value": value, "return": ret})
    labeled = [row for row in rows if row["return"] is not None]
    base = {
        "factor_id": spec.factor_id,
        "category": spec.category,
        "direction": spec.direction,
        "description": spec.description,
        "coverage_count": len(rows),
        "labeled_sample_count": len(labeled),
        "rating": "insufficient_labeled_samples",
        "value_score": None,
        "threshold": None,
        "high_avg_return_pct": None,
        "low_avg_return_pct": None,
        "adjusted_spread_pct": None,
        "high_win_rate": None,
        "low_win_rate": None,
        "threshold_results": {},
    }
    if len(labeled) < min_labeled_samples:
        return base

    threshold = median(row["value"] for row in labeled)
    high = [row for row in labeled if row["value"] >= threshold]
    low = [row for row in labeled if row["value"] < threshold]
    if not high or not low:
        return {**base, "threshold": _round(threshold), "rating": "not_enough_split"}

    high_avg = mean(float(row["return"]) for row in high)
    low_avg = mean(float(row["return"]) for row in low)
    raw_spread = high_avg - low_avg
    adjusted_spread = -raw_spread if spec.direction == "lower_is_better" else raw_spread
    high_win_rate = _win_rate(high, win_return_pct)
    low_win_rate = _win_rate(low, win_return_pct)
    win_rate_spread = high_win_rate - low_win_rate
    if spec.direction == "lower_is_better":
        win_rate_spread = -win_rate_spread
    value_score = adjusted_spread + win_rate_spread * 2.0
    rating = _rating(adjusted_spread, value_score)
    return {
        **base,
        "rating": rating,
        "value_score": _round(value_score),
        "threshold": _round(threshold),
        "high_avg_return_pct": _round(high_avg),
        "low_avg_return_pct": _round(low_avg),
        "adjusted_spread_pct": _round(adjusted_spread),
        "high_win_rate": _round(high_win_rate),
        "low_win_rate": _round(low_win_rate),
        "threshold_results": _threshold_results(labeled, spec.direction, thresholds, win_return_pct),
    }


def _threshold_results(
    labeled: list[Mapping[str, Any]],
    direction: str,
    thresholds: list[float],
    win_return_pct: float,
) -> dict[float, dict[str, Any]]:
    results = {}
    for threshold in thresholds:
        if direction == "lower_is_better":
            selected = [row for row in labeled if float(row["value"]) <= threshold]
            rejected = [row for row in labeled if float(row["value"]) > threshold]
            rule = "value <= threshold"
        else:
            selected = [row for row in labeled if float(row["value"]) >= threshold]
            rejected = [row for row in labeled if float(row["value"]) < threshold]
            rule = "value >= threshold"
        selected_returns = [float(row["return"]) for row in selected]
        rejected_returns = [float(row["return"]) for row in rejected]
        selected_avg = mean(selected_returns) if selected_returns else None
        rejected_avg = mean(rejected_returns) if rejected_returns else None
        results[threshold] = {
            "threshold": threshold,
            "selection_rule": rule,
            "selected_count": len(selected_returns),
            "rejected_count": len(rejected_returns),
            "selected_avg_return_pct": _round(selected_avg),
            "rejected_avg_return_pct": _round(rejected_avg),
            "spread_vs_rejected_pct": _round(selected_avg - rejected_avg) if selected_avg is not None and rejected_avg is not None else None,
            "selected_win_rate": _round(sum(1 for value in selected_returns if value > win_return_pct) / len(selected_returns)) if selected_returns else None,
        }
    return results


def _category_report(category: str, factors: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(item) for item in factors.values() if item.get("category") == category]
    ranked = sorted(rows, key=lambda item: (item.get("value_score") is not None, item.get("value_score") or -999.0), reverse=True)
    return {
        "category": category,
        "factor_count": len(rows),
        "valuable_factor_count": sum(1 for item in rows if item.get("rating") == "valuable"),
        "watchlist_factor_count": sum(1 for item in rows if item.get("rating") == "watchlist"),
        "pending_validation_factor_count": sum(1 for item in rows if item.get("rating") == "insufficient_labeled_samples"),
        "top_factors": ranked[:5],
    }


def _rating(adjusted_spread: float, value_score: float) -> str:
    if adjusted_spread >= 0.5 and value_score >= 0.75:
        return "valuable"
    if adjusted_spread >= 0.15 and value_score >= 0.25:
        return "watchlist"
    if adjusted_spread <= -0.15:
        return "negative"
    return "weak"


def _win_rate(rows: list[Mapping[str, Any]], win_return_pct: float) -> float:
    if not rows:
        return 0.0
    return sum(1 for row in rows if float(row["return"]) > win_return_pct) / len(rows)


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None
