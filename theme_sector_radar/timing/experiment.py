"""Experiments for paper-only buy timing threshold selection."""

from __future__ import annotations

from statistics import mean
from typing import Any, Mapping


def evaluate_buy_timing_thresholds(
    candidates: list[Mapping[str, Any]],
    thresholds: list[float],
    winner_return_pct: float = 0.0,
) -> dict[str, Any]:
    valid_rows = [
        {
            "code": str(item.get("code") or ""),
            "buy_timing_score": _float(item.get("buy_timing_score")),
            "forward_return_pct": _float(item.get("forward_return_pct")),
        }
        for item in candidates
    ]
    results = [_evaluate_threshold(valid_rows, threshold, winner_return_pct) for threshold in thresholds]
    return {
        "schema_version": "buy_timing_threshold_experiment.v1",
        "threshold_results": results,
        "best_balanced_threshold": _best_balanced_threshold(results),
        "winner_return_pct": winner_return_pct,
        "shadow_only": True,
        "paper_trading_only": True,
        "does_not_modify_official_scores": True,
        "no_execution_signals": True,
    }


def _evaluate_threshold(rows: list[dict[str, Any]], threshold: float, winner_return_pct: float) -> dict[str, Any]:
    eligible = [
        row for row in rows
        if row["buy_timing_score"] is not None
        and row["buy_timing_score"] >= threshold
        and row["forward_return_pct"] is not None
    ]
    missed_winners = [
        row for row in rows
        if row["forward_return_pct"] is not None
        and row["forward_return_pct"] > winner_return_pct
        and (row["buy_timing_score"] is None or row["buy_timing_score"] < threshold)
    ]
    returns = [float(row["forward_return_pct"]) for row in eligible]
    wins = [value for value in returns if value > winner_return_pct]
    return {
        "threshold": threshold,
        "trade_count": len(eligible),
        "win_count": len(wins),
        "win_rate": _round(len(wins) / len(returns)) if returns else None,
        "avg_forward_return_pct": _round(mean(returns)) if returns else None,
        "min_forward_return_pct": _round(min(returns)) if returns else None,
        "max_forward_return_pct": _round(max(returns)) if returns else None,
        "missed_winner_count": len(missed_winners),
    }


def _best_balanced_threshold(results: list[Mapping[str, Any]]) -> float | None:
    scored = []
    for row in results:
        trade_count = int(row.get("trade_count") or 0)
        avg_return = _float(row.get("avg_forward_return_pct"))
        win_rate = _float(row.get("win_rate"))
        missed = int(row.get("missed_winner_count") or 0)
        if trade_count <= 0 or avg_return is None or win_rate is None:
            continue
        balance_score = avg_return + win_rate * 2.0 + min(trade_count, 5) * 0.15 - missed * 0.75
        scored.append((balance_score, row.get("threshold")))
    if not scored:
        return None
    scored.sort(key=lambda item: (item[0], item[1]))
    return scored[-1][1]


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None
