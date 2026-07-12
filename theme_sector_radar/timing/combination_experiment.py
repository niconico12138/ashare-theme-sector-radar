"""Paper-only timing factor combination experiments."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class FactorCondition:
    factor_id: str
    operator: str
    threshold: float

    def matches(self, row: Mapping[str, Any]) -> bool:
        value = _float(row.get(self.factor_id))
        if value is None:
            return False
        if self.operator == ">=":
            return value >= self.threshold
        if self.operator == "<=":
            return value <= self.threshold
        raise ValueError(f"Unsupported operator: {self.operator}")


@dataclass(frozen=True)
class StrategyVersion:
    version_id: str
    description: str
    conditions: tuple[FactorCondition, ...]


def build_default_strategy_versions() -> list[StrategyVersion]:
    """Build the first paper-only strategy iteration set from confirmed factors."""
    return [
        StrategyVersion(
            "v1_time_core",
            "Time-structure core.",
            (
                FactorCondition("open_to_midday_resilience_score", ">=", 53.0),
                FactorCondition("midday_hold_score", ">=", 56.0),
            ),
        ),
        StrategyVersion(
            "v2_time_vwap",
            "Time core plus VWAP support.",
            (
                FactorCondition("open_to_midday_resilience_score", ">=", 53.0),
                FactorCondition("midday_hold_score", ">=", 56.0),
                FactorCondition("vwap_above_ratio_score", ">=", 48.0),
                FactorCondition("midday_vwap_support_score", ">=", 45.0),
            ),
        ),
        StrategyVersion(
            "v3_time_vwap_position",
            "Time and VWAP confirmation plus high-area close.",
            (
                FactorCondition("open_to_midday_resilience_score", ">=", 53.0),
                FactorCondition("midday_hold_score", ">=", 56.0),
                FactorCondition("vwap_above_ratio_score", ">=", 48.0),
                FactorCondition("late_high_near_close_score", ">=", 80.0),
                FactorCondition("high_area_acceptance_score", ">=", 73.0),
            ),
        ),
        StrategyVersion(
            "v4_risk_filtered",
            "Quality setup with reversal-risk filters.",
            (
                FactorCondition("open_to_midday_resilience_score", ">=", 53.0),
                FactorCondition("midday_hold_score", ">=", 56.0),
                FactorCondition("vwap_above_ratio_score", ">=", 48.0),
                FactorCondition("late_high_near_close_score", ">=", 80.0),
                FactorCondition("high_to_close_drawdown_score", "<=", 20.0),
                FactorCondition("late_breakdown_risk", "<=", 4.0),
                FactorCondition("lower_low_sequence_risk", "<=", 35.0),
                FactorCondition("volume_without_price_progress_risk", "<=", 10.5),
            ),
        ),
        StrategyVersion(
            "v5_relative_addon",
            "Risk-filtered setup plus relative strength.",
            (
                FactorCondition("open_to_midday_resilience_score", ">=", 53.0),
                FactorCondition("midday_hold_score", ">=", 56.0),
                FactorCondition("vwap_above_ratio_score", ">=", 48.0),
                FactorCondition("late_high_near_close_score", ">=", 80.0),
                FactorCondition("high_to_close_drawdown_score", "<=", 20.0),
                FactorCondition("lower_low_sequence_risk", "<=", 35.0),
                FactorCondition("stock_vs_market_intraday_alpha_score", ">=", 59.0),
                FactorCondition("relative_resilience_score", ">=", 67.0),
            ),
        ),
        StrategyVersion(
            "v6_strict_high_conviction",
            "Strict high-conviction timing setup.",
            (
                FactorCondition("open_to_midday_resilience_score", ">=", 57.0),
                FactorCondition("midday_hold_score", ">=", 60.0),
                FactorCondition("vwap_above_ratio_score", ">=", 52.0),
                FactorCondition("midday_vwap_support_score", ">=", 53.0),
                FactorCondition("late_high_near_close_score", ">=", 83.0),
                FactorCondition("high_to_close_drawdown_score", "<=", 17.0),
                FactorCondition("volume_without_price_progress_risk", "<=", 10.0),
            ),
        ),
        StrategyVersion(
            "v7_time_core_strict",
            "Stricter time-structure core.",
            (
                FactorCondition("open_to_midday_resilience_score", ">=", 57.0),
                FactorCondition("midday_hold_score", ">=", 60.0),
            ),
        ),
        StrategyVersion(
            "v8_time_position_soft",
            "Time core plus soft position confirmation.",
            (
                FactorCondition("open_to_midday_resilience_score", ">=", 53.0),
                FactorCondition("midday_hold_score", ">=", 56.0),
                FactorCondition("late_high_near_close_score", ">=", 80.0),
            ),
        ),
        StrategyVersion(
            "v9_time_vwap_soft",
            "Time core plus soft VWAP confirmation.",
            (
                FactorCondition("open_to_midday_resilience_score", ">=", 53.0),
                FactorCondition("midday_hold_score", ">=", 56.0),
                FactorCondition("vwap_above_ratio_score", ">=", 48.0),
            ),
        ),
        StrategyVersion(
            "v10_time_risk_soft",
            "Time core with soft reversal-risk filter.",
            (
                FactorCondition("open_to_midday_resilience_score", ">=", 53.0),
                FactorCondition("midday_hold_score", ">=", 56.0),
                FactorCondition("high_to_close_drawdown_score", "<=", 25.0),
                FactorCondition("lower_low_sequence_risk", "<=", 45.0),
            ),
        ),
        StrategyVersion(
            "v11_time_relative_soft",
            "Time core plus broad relative strength.",
            (
                FactorCondition("open_to_midday_resilience_score", ">=", 53.0),
                FactorCondition("midday_hold_score", ">=", 56.0),
                FactorCondition("stock_vs_market_intraday_alpha_score", ">=", 59.0),
            ),
        ),
        StrategyVersion(
            "v12_time_vwap_position_strict",
            "Stricter time, VWAP, and position confirmation.",
            (
                FactorCondition("open_to_midday_resilience_score", ">=", 57.0),
                FactorCondition("midday_hold_score", ">=", 60.0),
                FactorCondition("vwap_above_ratio_score", ">=", 52.0),
                FactorCondition("late_high_near_close_score", ">=", 83.0),
            ),
        ),
        StrategyVersion(
            "v13_open_midday_only",
            "Open-to-midday resilience only.",
            (
                FactorCondition("open_to_midday_resilience_score", ">=", 57.0),
            ),
        ),
        StrategyVersion(
            "v14_midday_hold_only",
            "Midday hold only.",
            (
                FactorCondition("midday_hold_score", ">=", 60.0),
            ),
        ),
        StrategyVersion(
            "v15_tuned_time_vwap_close",
            "Tuned time, VWAP, and near-high close confirmation.",
            (
                FactorCondition("open_to_midday_resilience_score", ">=", 65.0),
                FactorCondition("midday_hold_score", ">=", 56.0),
                FactorCondition("vwap_above_ratio_score", ">=", 60.0),
                FactorCondition("late_high_near_close_score", ">=", 88.0),
            ),
        ),
        StrategyVersion(
            "v16_tuned_broader_vwap_close",
            "Broader tuned VWAP and near-high close confirmation.",
            (
                FactorCondition("open_to_midday_resilience_score", ">=", 65.0),
                FactorCondition("midday_hold_score", ">=", 56.0),
                FactorCondition("vwap_above_ratio_score", ">=", 52.0),
                FactorCondition("late_high_near_close_score", ">=", 88.0),
            ),
        ),
        StrategyVersion(
            "v17_tuned_time_only_strict",
            "Strict time-only tuned setup.",
            (
                FactorCondition("open_to_midday_resilience_score", ">=", 70.0),
                FactorCondition("midday_hold_score", ">=", 65.0),
            ),
        ),
    ]


def evaluate_strategy_versions(
    samples: Sequence[Mapping[str, Any]],
    versions: Sequence[StrategyVersion],
    *,
    return_field: str = "forward_return_pct",
    min_selected: int = 20,
    win_return_pct: float = 0.0,
) -> dict[str, Any]:
    rows = [dict(row) for row in samples]
    reports = [
        _evaluate_version(rows, version, return_field, min_selected, win_return_pct)
        for version in versions
    ]
    reports.sort(key=lambda item: (item["is_valid"], item["research_score"]), reverse=True)
    return {
        "schema_version": "timing_combination_experiment.v1",
        "summary": {
            "sample_count": len(rows),
            "labeled_sample_count": sum(1 for row in rows if _float(row.get(return_field)) is not None),
            "version_count": len(reports),
            "valid_version_count": sum(1 for item in reports if item["is_valid"]),
            "min_selected": min_selected,
            "return_field": return_field,
        },
        "best_version": reports[0] if reports else None,
        "versions": reports,
        "shadow_only": True,
        "paper_trading_only": True,
        "does_not_modify_official_scores": True,
        "no_execution_signals": True,
    }


def _evaluate_version(
    rows: list[Mapping[str, Any]],
    version: StrategyVersion,
    return_field: str,
    min_selected: int,
    win_return_pct: float,
) -> dict[str, Any]:
    labeled = [row for row in rows if _float(row.get(return_field)) is not None]
    selected = [row for row in labeled if all(condition.matches(row) for condition in version.conditions)]
    rejected = [row for row in labeled if row not in selected]
    selected_returns = [float(row[return_field]) for row in selected]
    rejected_returns = [float(row[return_field]) for row in rejected]
    selected_avg = mean(selected_returns) if selected_returns else None
    rejected_avg = mean(rejected_returns) if rejected_returns else None
    spread = selected_avg - rejected_avg if selected_avg is not None and rejected_avg is not None else None
    selected_win = _win_rate(selected_returns, win_return_pct)
    rejected_win = _win_rate(rejected_returns, win_return_pct)
    win_spread = selected_win - rejected_win if selected_win is not None and rejected_win is not None else None
    is_valid = len(selected_returns) >= min_selected
    research_score = _research_score(selected_avg, spread, win_spread, len(selected_returns), min_selected)
    return {
        "version_id": version.version_id,
        "description": version.description,
        "conditions": [
            {"factor_id": item.factor_id, "operator": item.operator, "threshold": item.threshold}
            for item in version.conditions
        ],
        "selected_count": len(selected_returns),
        "rejected_count": len(rejected_returns),
        "selected_avg_return_pct": _round(selected_avg),
        "rejected_avg_return_pct": _round(rejected_avg),
        "spread_vs_rejected_pct": _round(spread),
        "selected_win_rate": _round(selected_win),
        "rejected_win_rate": _round(rejected_win),
        "win_rate_spread": _round(win_spread),
        "selected_min_return_pct": _round(min(selected_returns)) if selected_returns else None,
        "selected_max_return_pct": _round(max(selected_returns)) if selected_returns else None,
        "is_valid": is_valid,
        "research_score": _round(research_score),
        "paper_trading_only": True,
        "no_execution_signals": True,
    }


def _research_score(
    selected_avg: float | None,
    spread: float | None,
    win_spread: float | None,
    selected_count: int,
    min_selected: int,
) -> float:
    if selected_avg is None or spread is None:
        return -999.0
    sample_factor = min(1.0, selected_count / max(1, min_selected))
    penalty = 0.0 if selected_count >= min_selected else (min_selected - selected_count) * 0.05
    return (selected_avg * 0.65 + spread * 0.30 + (win_spread or 0.0) * 0.8) * sample_factor - penalty


def _win_rate(values: list[float], threshold: float) -> float | None:
    if not values:
        return None
    return sum(1 for value in values if value > threshold) / len(values)


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None
