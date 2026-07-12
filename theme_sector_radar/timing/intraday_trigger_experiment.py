"""Paper-only intraday trigger experiments over historical minute bars."""

from __future__ import annotations

from dataclasses import replace
from statistics import mean
from typing import Any, Mapping

from theme_sector_radar.timing.intraday_trigger import (
    IntradayBuyTriggerConfig,
    IntradayExitTriggerConfig,
    evaluate_intraday_buy_trigger,
    evaluate_intraday_exit_sequence,
)


def run_intraday_trigger_experiment(
    candidates: list[Mapping[str, Any]],
    minute_bars_by_code: Mapping[str, list[Mapping[str, Any]]],
    buy_config: IntradayBuyTriggerConfig,
    exit_config_template: IntradayExitTriggerConfig,
    bar_frequency: str = "1m",
) -> dict[str, Any]:
    results = []
    for candidate in candidates:
        code = str(candidate.get("code") or "")
        bars = list(minute_bars_by_code.get(code) or [])
        buy_trigger = evaluate_intraday_buy_trigger(bars, buy_config)
        if not buy_trigger["triggered"]:
            results.append(
                {
                    "code": code,
                    "name": candidate.get("name") or "",
                    "status": "not_triggered",
                    "buy_timing_score": candidate.get("buy_timing_score"),
                    "buy_trigger": buy_trigger,
                    "exit_sequence": None,
                    "return_pct": None,
                    "paper_trading_only": True,
                    "no_execution_signals": True,
                }
            )
            continue

        trigger_time = str(buy_trigger.get("trigger_time") or "")
        trigger_price = float(buy_trigger.get("trigger_price") or 0.0)
        exit_bars = _bars_from_trigger(bars, trigger_time)
        exit_sequence = evaluate_intraday_exit_sequence(
            exit_bars,
            replace(exit_config_template, entry_price=trigger_price),
        )
        return_pct = _return_pct(trigger_price, exit_sequence)
        results.append(
            {
                "code": code,
                "name": candidate.get("name") or "",
                "status": "closed" if exit_sequence["triggered"] else "open_at_end",
                "buy_timing_score": candidate.get("buy_timing_score"),
                "buy_trigger": buy_trigger,
                "exit_sequence": exit_sequence,
                "return_pct": return_pct,
                "paper_trading_only": True,
                "no_execution_signals": True,
            }
        )

    summary = _summary(results, len(candidates))
    return {
        "schema_version": "intraday_trigger_experiment.v1",
        "bar_frequency": bar_frequency,
        "summary": summary,
        "results": results,
        "shadow_only": True,
        "paper_trading_only": True,
        "does_not_modify_official_scores": True,
        "no_execution_signals": True,
    }


def _bars_from_trigger(bars: list[Mapping[str, Any]], trigger_time: str) -> list[Mapping[str, Any]]:
    return [bar for bar in bars if str(bar.get("time") or bar.get("date") or "") >= trigger_time]


def _return_pct(entry_price: float, exit_sequence: Mapping[str, Any]) -> float | None:
    if not exit_sequence.get("triggered"):
        return None
    exit_price = _float(exit_sequence.get("exit_price"))
    if entry_price <= 0 or exit_price is None:
        return None
    return _round((exit_price - entry_price) / entry_price * 100.0)


def _summary(results: list[Mapping[str, Any]], candidate_count: int) -> dict[str, Any]:
    triggered = [item for item in results if item.get("buy_trigger", {}).get("triggered")]
    closed = [item for item in results if item.get("status") == "closed"]
    returns = [float(item["return_pct"]) for item in closed if item.get("return_pct") is not None]
    return {
        "candidate_count": candidate_count,
        "triggered_count": len(triggered),
        "closed_count": len(closed),
        "take_profit_count": sum(1 for item in closed if item.get("exit_sequence", {}).get("exit_reason") == "take_profit"),
        "stop_loss_count": sum(1 for item in closed if item.get("exit_sequence", {}).get("exit_reason") == "stop_loss"),
        "avg_return_pct": _round(mean(returns)) if returns else None,
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
