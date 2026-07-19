"""Paper-only factor exit trigger research."""

from __future__ import annotations

import math
from typing import Any, Mapping


def evaluate_factor_exit_triggers(
    bars: list[Mapping[str, Any]],
    *,
    entry_price: float,
    fixed_take_profit_pct: float = 5.0,
    fixed_stop_loss_pct: float = -3.0,
    protect_min_profit_pct: float = 3.0,
    protect_peak_giveback_pct: float = 2.0,
    risk_stop_pct: float = -3.0,
) -> dict[str, Any]:
    rows = _enrich_exit_feature_bars(_normalize_bars(bars), entry_price=entry_price)
    close_return = _close_return(rows, entry_price)
    strategies = {
        "exit_v1_fixed": _evaluate_fixed(rows, entry_price, fixed_take_profit_pct, fixed_stop_loss_pct, close_return),
        "exit_v2_factor_protect": _evaluate_factor_protect(
            rows,
            entry_price,
            protect_min_profit_pct,
            protect_peak_giveback_pct,
            close_return,
        ),
        "exit_v3_factor_risk": _evaluate_factor_risk(rows, entry_price, risk_stop_pct, close_return),
        "exit_v4_confirmed_factor_protect": _evaluate_confirmed_factor_protect(
            rows,
            entry_price,
            protect_min_profit_pct,
            protect_peak_giveback_pct,
            close_return,
        ),
        "exit_v5_factor_risk_confirmed": _evaluate_confirmed_factor_risk(
            rows,
            entry_price,
            risk_stop_pct,
            close_return,
        ),
    }
    report = {
        "schema_version": "timing_factor_exit_triggers.v1",
        "close_return_pct": close_return,
        "strategies": strategies,
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }
    if (
        isinstance(entry_price, (int, float))
        and not isinstance(entry_price, bool)
        and math.isfinite(float(entry_price))
        and float(entry_price) > 0
    ):
        report["entry_price"] = _round(entry_price)
    return report


def _evaluate_fixed(
    rows: list[dict[str, Any]],
    entry_price: float,
    take_profit_pct: float,
    stop_loss_pct: float,
    close_return: float | None,
) -> dict[str, Any]:
    for row in rows:
        high = _float(row.get("high")) or _price(row)
        current = _price(row)
        time = _time(row)
        current_return = _return_pct(current, entry_price) if current is not None else None
        if current_return is not None and current_return <= stop_loss_pct:
            return _strategy_report(True, "stop_loss", time, current_return, ["fixed_stop_loss"], close_return)
        if high is not None and _return_pct(high, entry_price) >= take_profit_pct:
            return _strategy_report(True, "take_profit", time, take_profit_pct, ["fixed_take_profit"], close_return)
    return _strategy_report(False, None, None, None, [], close_return)


def _evaluate_factor_protect(
    rows: list[dict[str, Any]],
    entry_price: float,
    min_profit_pct: float,
    peak_giveback_pct: float,
    close_return: float | None,
) -> dict[str, Any]:
    peak_return: float | None = None
    for row in rows:
        price = _price(row)
        if price is None:
            continue
        high = _float(row.get("high")) or price
        high_return = _return_pct(high, entry_price)
        peak_return = high_return if peak_return is None else max(peak_return, high_return)
        current_return = _return_pct(price, entry_price)
        if current_return < min_profit_pct:
            continue
        factors = _protect_factors(
            row,
            current_return=current_return,
            peak_return=peak_return,
            peak_giveback_pct=peak_giveback_pct,
        )
        if factors:
            return _strategy_report(
                True,
                "take_profit_protect",
                _time(row),
                current_return,
                factors,
                close_return,
            )
    return _strategy_report(False, None, None, None, [], close_return)


def _evaluate_factor_risk(
    rows: list[dict[str, Any]],
    entry_price: float,
    stop_pct: float,
    close_return: float | None,
) -> dict[str, Any]:
    previous_low: float | None = None
    for row in rows:
        price = _price(row)
        low = _float(row.get("low")) or price
        if price is None:
            continue
        current_return = _return_pct(price, entry_price)
        factors = _risk_factors(row, low, previous_low)
        previous_low = low if low is not None else previous_low
        if current_return <= stop_pct and factors:
            return _strategy_report(
                True,
                "stop_loss_factor",
                _time(row),
                current_return,
                factors,
                close_return,
            )
    return _strategy_report(False, None, None, None, [], close_return)


def _evaluate_confirmed_factor_protect(
    rows: list[dict[str, Any]],
    entry_price: float,
    min_profit_pct: float,
    peak_giveback_pct: float,
    close_return: float | None,
) -> dict[str, Any]:
    peak_return: float | None = None
    for row in rows:
        price = _price(row)
        if price is None:
            continue
        high = _float(row.get("high")) or price
        high_return = _return_pct(high, entry_price)
        peak_return = high_return if peak_return is None else max(peak_return, high_return)
        current_return = _return_pct(price, entry_price)
        if current_return < min_profit_pct:
            continue
        factors = _protect_factors(
            row,
            current_return=current_return,
            peak_return=peak_return,
            peak_giveback_pct=peak_giveback_pct,
        )
        confirmed = _confirmed_protect_factors(factors)
        if confirmed:
            return _strategy_report(
                True,
                "take_profit_confirmed_protect",
                _time(row),
                current_return,
                confirmed,
                close_return,
                paper_candidate_kind="take_profit_protect",
            )
    return _strategy_report(
        False,
        None,
        None,
        None,
        [],
        close_return,
        paper_candidate_kind="take_profit_protect",
    )


def _evaluate_confirmed_factor_risk(
    rows: list[dict[str, Any]],
    entry_price: float,
    stop_pct: float,
    close_return: float | None,
) -> dict[str, Any]:
    previous_low: float | None = None
    for row in rows:
        price = _price(row)
        low = _float(row.get("low")) or price
        if price is None:
            continue
        current_return = _return_pct(price, entry_price)
        factors = _risk_factors(row, low, previous_low)
        previous_low = low if low is not None else previous_low
        if current_return <= stop_pct and len(factors) >= 2:
            return _strategy_report(
                True,
                "stop_loss_confirmed_risk",
                _time(row),
                current_return,
                factors,
                close_return,
                paper_candidate_kind="stop_loss_risk",
            )
    return _strategy_report(
        False,
        None,
        None,
        None,
        [],
        close_return,
        paper_candidate_kind="stop_loss_risk",
    )


def _protect_factors(
    row: Mapping[str, Any],
    *,
    current_return: float,
    peak_return: float | None,
    peak_giveback_pct: float,
) -> list[str]:
    factors = []
    price = _price(row)
    vwap = _float(row.get("vwap"))
    if price is not None and vwap is not None and price < vwap:
        factors.append("price_below_vwap")
    if (_float(row.get("weak_close_after_volume_risk")) or 0.0) >= 60.0:
        factors.append("weak_close_after_volume_risk")
    if (_float(row.get("high_to_close_drawdown_score")) or 0.0) >= 20.0:
        factors.append("high_to_close_drawdown")
    if (_float(row.get("volume_without_price_progress_risk")) or 0.0) >= 15.0:
        factors.append("volume_without_price_progress")
    if (_float(row.get("failed_breakout_risk")) or 0.0) >= 50.0:
        factors.append("failed_breakout")
    if peak_return is not None and peak_return >= 5.0 and peak_return - current_return >= peak_giveback_pct:
        factors.append("peak_giveback_from_profit")
    return factors


def _confirmed_protect_factors(factors: list[str]) -> list[str]:
    factor_set = set(factors)
    confirmed: list[str] = []
    for primary in ("price_below_vwap", "peak_giveback_from_profit"):
        if primary in factor_set:
            confirmed.append(primary)
    if "failed_breakout" in factor_set and (
        "volume_without_price_progress" in factor_set or "high_to_close_drawdown" in factor_set
    ):
        confirmed.append("failed_breakout_confirmed")
    if "high_to_close_drawdown" in factor_set and "volume_without_price_progress" in factor_set:
        confirmed.append("drawdown_with_volume_stall")
    return confirmed


def _enrich_exit_feature_bars(rows: list[dict[str, Any]], *, entry_price: float) -> list[dict[str, Any]]:
    if not rows:
        return []
    enriched: list[dict[str, Any]] = []
    cumulative_amount = 0.0
    cumulative_volume = 0.0
    prior_amounts: list[float] = []
    peak_return: float | None = None
    prior_high: float | None = None
    for raw in rows:
        row = dict(raw)
        price = _price(row)
        high = _float(row.get("high")) or price
        amount = _float(row.get("amount"))
        volume = _float(row.get("volume"))
        has_turnover_bar = amount is not None and volume is not None and volume > 0
        if has_turnover_bar:
            cumulative_amount += amount
            cumulative_volume += volume
        if row.get("vwap") is None and cumulative_volume > 0:
            row["vwap"] = cumulative_amount / cumulative_volume
        if price is not None and entry_price > 0:
            current_return = _return_pct(price, entry_price)
            high_return = _return_pct(high if high is not None else price, entry_price)
            peak_return = high_return if peak_return is None else max(peak_return, high_return)
            peak_giveback = max(0.0, peak_return - current_return)
            if has_turnover_bar and row.get("high_to_close_drawdown_score") is None:
                row["high_to_close_drawdown_score"] = _clamp(peak_giveback * 10.0)
            if has_turnover_bar and row.get("failed_breakout_risk") is None and prior_high is not None:
                failed_breakout = price < prior_high and peak_giveback >= 1.5
                row["failed_breakout_risk"] = 55.0 if failed_breakout else 0.0
        if row.get("volume_without_price_progress_risk") is None and amount is not None and prior_amounts and price is not None:
            avg_prior_amount = sum(prior_amounts[-5:]) / min(len(prior_amounts), 5)
            amount_ratio = amount / avg_prior_amount if avg_prior_amount > 0 else 1.0
            progress = _return_pct(price, entry_price) if entry_price > 0 else 0.0
            row["volume_without_price_progress_risk"] = _clamp(max(0.0, amount_ratio - 1.2) * 20.0 + max(0.0, 2.0 - progress) * 8.0)
        if amount is not None:
            prior_amounts.append(amount)
        if high is not None:
            prior_high = high if prior_high is None else max(prior_high, high)
        enriched.append(row)
    return enriched


def _risk_factors(row: Mapping[str, Any], low: float | None, previous_low: float | None) -> list[str]:
    factors = []
    price = _price(row)
    vwap = _float(row.get("vwap"))
    if price is not None and vwap is not None and price < vwap:
        factors.append("price_below_vwap")
    if low is not None and previous_low is not None and low < previous_low:
        factors.append("lower_low_sequence")
    if (_float(row.get("late_breakdown_risk")) or 0.0) >= 8.0:
        factors.append("late_breakdown")
    if (_float(row.get("failed_breakout_risk")) or 0.0) >= 50.0:
        factors.append("failed_breakout")
    return factors


def _strategy_report(
    triggered: bool,
    trigger_type: str | None,
    trigger_time: str | None,
    trigger_return_pct: float | None,
    trigger_factors: list[str],
    close_return_pct: float | None,
    *,
    paper_candidate_kind: str | None = None,
) -> dict[str, Any]:
    trigger_return = _round(trigger_return_pct)
    close_return = _round(close_return_pct)
    saved = _round(trigger_return - close_return) if trigger_return is not None and close_return is not None else None
    missed = _round(max(0.0, close_return - trigger_return)) if trigger_return is not None and close_return is not None else 0.0
    result = {
        "triggered": triggered,
        "trigger_type": trigger_type,
        "trigger_time": trigger_time,
        "trigger_return_pct": trigger_return,
        "trigger_factors": trigger_factors,
        "close_return_pct": close_return,
        "saved_vs_close_pct": saved,
        "missed_upside_pct": missed,
        "exit_research_only": True,
        "paper_trading_only": True,
        "no_execution_signals": True,
    }
    if paper_candidate_kind:
        result["paper_candidate_kind"] = paper_candidate_kind
    return result


def _normalize_bars(bars: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return sorted([dict(row) for row in bars or [] if isinstance(row, Mapping)], key=lambda row: _time(row))


def _close_return(rows: list[Mapping[str, Any]], entry_price: float) -> float | None:
    if entry_price <= 0:
        return None
    for row in reversed(rows):
        price = _price(row)
        if price is not None:
            return _round(_return_pct(price, entry_price))
    return None


def _return_pct(price: float, entry_price: float) -> float:
    return (price - entry_price) / entry_price * 100.0


def _time(row: Mapping[str, Any]) -> str:
    return str(row.get("time") or row.get("date") or "")


def _price(row: Mapping[str, Any]) -> float | None:
    for key in ("price", "close", "latest_price"):
        value = _float(row.get(key))
        if value is not None:
            return value
    return None


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None
