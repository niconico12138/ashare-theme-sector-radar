"""Minute-bar trigger checks for paper-only intraday timing research."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class IntradayBuyTriggerConfig:
    min_return_from_open_pct: float = 0.0
    min_bar_amount: float = 0.0
    require_above_vwap: bool = False
    max_chase_from_open_pct: float | None = None


@dataclass(frozen=True)
class IntradayExitTriggerConfig:
    entry_price: float
    stop_loss_pct: float = -5.0
    take_profit_pct: float = 8.0


def evaluate_intraday_buy_trigger(
    bars: list[Mapping[str, Any]],
    config: IntradayBuyTriggerConfig | None = None,
) -> dict[str, Any]:
    config = config or IntradayBuyTriggerConfig()
    rows = _normalize_bars(bars)
    if not rows:
        return _buy_report(False, blocked_reason="missing_intraday_bars")

    open_price = _price(rows[0])
    if open_price is None or open_price <= 0:
        return _buy_report(False, blocked_reason="invalid_open_price")

    for row in rows:
        price = _price(row)
        if price is None or price <= 0:
            continue
        return_from_open = (price - open_price) / open_price * 100.0
        if config.max_chase_from_open_pct is not None and return_from_open > config.max_chase_from_open_pct:
            return _buy_report(False, blocked_reason="chasing_limit_exceeded")
        if return_from_open < config.min_return_from_open_pct:
            continue
        if (_float(row.get("amount")) or 0.0) < config.min_bar_amount:
            continue
        vwap = _float(row.get("vwap"))
        if config.require_above_vwap and vwap is not None and price < vwap:
            continue
        if config.require_above_vwap and vwap is None:
            continue
        return _buy_report(
            True,
            trigger_time=str(row.get("time") or row.get("date") or ""),
            trigger_price=_round(price),
            trigger_reason="buy_conditions_met",
            return_from_open_pct=_round(return_from_open),
        )

    return _buy_report(False, blocked_reason="buy_conditions_not_met")


def evaluate_intraday_exit_sequence(
    bars: list[Mapping[str, Any]],
    config: IntradayExitTriggerConfig,
) -> dict[str, Any]:
    rows = _normalize_bars(bars)
    entry_price = float(config.entry_price)
    if not rows:
        return _exit_report(False, blocked_reason="missing_intraday_bars")
    if entry_price <= 0:
        return _exit_report(False, blocked_reason="invalid_entry_price")

    stop_price = entry_price * (1 + config.stop_loss_pct / 100.0)
    take_profit_price = entry_price * (1 + config.take_profit_pct / 100.0)
    for row in rows:
        high = _float(row.get("high")) or _price(row)
        low = _float(row.get("low")) or _price(row)
        time = str(row.get("time") or row.get("date") or "")
        hit_stop = low is not None and low <= stop_price
        hit_take_profit = high is not None and high >= take_profit_price
        if hit_stop:
            return _exit_report(
                True,
                exit_reason="stop_loss",
                exit_time=time,
                exit_price=_round(stop_price),
                same_bar_stop_and_take_profit=bool(hit_take_profit),
            )
        if hit_take_profit:
            return _exit_report(
                True,
                exit_reason="take_profit",
                exit_time=time,
                exit_price=_round(take_profit_price),
                same_bar_stop_and_take_profit=False,
            )
    return _exit_report(False, blocked_reason="exit_conditions_not_met")


def _normalize_bars(bars: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized = [dict(row) for row in bars or [] if isinstance(row, Mapping)]
    return sorted(normalized, key=lambda row: str(row.get("time") or row.get("date") or ""))


def _price(row: Mapping[str, Any]) -> float | None:
    for key in ("price", "close", "latest_price"):
        value = _float(row.get(key))
        if value is not None:
            return value
    return None


def _buy_report(
    triggered: bool,
    trigger_time: str | None = None,
    trigger_price: float | None = None,
    trigger_reason: str | None = None,
    blocked_reason: str | None = None,
    return_from_open_pct: float | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "intraday_buy_trigger.v1",
        "triggered": triggered,
        "trigger_time": trigger_time,
        "trigger_price": trigger_price,
        "trigger_reason": trigger_reason,
        "blocked_reason": blocked_reason,
        "return_from_open_pct": return_from_open_pct,
        "shadow_only": True,
        "paper_trading_only": True,
        "does_not_modify_official_scores": True,
        "no_execution_signals": True,
    }


def _exit_report(
    triggered: bool,
    exit_reason: str | None = None,
    exit_time: str | None = None,
    exit_price: float | None = None,
    blocked_reason: str | None = None,
    same_bar_stop_and_take_profit: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": "intraday_exit_sequence.v1",
        "triggered": triggered,
        "exit_reason": exit_reason,
        "exit_time": exit_time,
        "exit_price": exit_price,
        "blocked_reason": blocked_reason,
        "same_bar_stop_and_take_profit": same_bar_stop_and_take_profit,
        "shadow_only": True,
        "paper_trading_only": True,
        "does_not_modify_official_scores": True,
        "no_execution_signals": True,
    }


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None
