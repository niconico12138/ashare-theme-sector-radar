"""Future-return label construction, isolated from feature and prediction code."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
import math
from typing import Any, Mapping, Sequence

from .schema import LABEL_DEFINITION, LABEL_SCHEMA_VERSION


HORIZONS = (1, 3, 5)


def _date(value: Any, *, field: str) -> str:
    text = str(value or "")
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date: {text!r}") from exc
    if parsed.isoformat() != text:
        raise ValueError(f"{field} must be a canonical ISO date: {text!r}")
    return text


def _close(value: Any, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context} close must be numeric")
    converted = float(value)
    if not math.isfinite(converted) or converted <= 0:
        raise ValueError(f"{context} close must be finite and positive")
    return converted


def build_forward_label_rows(
    stock_price_rows: Sequence[Mapping[str, Any]],
    sector_price_rows: Sequence[Mapping[str, Any]],
    *,
    horizons: tuple[int, ...] = HORIZONS,
    training_horizon: int = 5,
    trading_dates: Sequence[str],
) -> list[dict[str, Any]]:
    """Build labels on one explicit exchange calendar without bar roll-forward."""

    normalized_horizons = tuple(sorted(set(int(value) for value in horizons)))
    if not normalized_horizons or normalized_horizons[0] <= 0:
        raise ValueError("label horizons must be positive")
    if training_horizon not in normalized_horizons:
        raise ValueError("training_horizon must be included in horizons")
    calendar_dates = [_date(value, field="trading calendar date") for value in trading_dates]
    if (
        not calendar_dates
        or calendar_dates != sorted(calendar_dates)
        or len(calendar_dates) != len(set(calendar_dates))
    ):
        raise ValueError("trading calendar dates must be sorted and unique")
    calendar_index = {day: index for index, day in enumerate(calendar_dates)}

    sector_prices: dict[tuple[str, str], float] = {}
    for row in sector_price_rows:
        sector_name = str(row.get("sector_name") or "")
        day = _date(row.get("date"), field="sector date")
        key = (sector_name, day)
        if not sector_name:
            raise ValueError("sector_name is required for sector labels")
        if key in sector_prices:
            raise ValueError(f"duplicate sector price row: {sector_name} {day}")
        sector_prices[key] = _close(row.get("close"), context=f"sector {sector_name} {day}")

    grouped: dict[tuple[str, str], list[tuple[str, float]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for row in stock_price_rows:
        code = str(row.get("stock_code") or row.get("code") or "").zfill(6)
        sector_name = str(row.get("sector_name") or "")
        day = _date(row.get("date"), field="stock date")
        if len(code) != 6 or not code.isdigit() or not sector_name:
            raise ValueError("stock_code and sector_name are required for labels")
        identity = (day, code)
        if identity in seen:
            raise ValueError(f"duplicate stock price row: {day} {code}")
        seen.add(identity)
        grouped[(code, sector_name)].append(
            (day, _close(row.get("close"), context=f"stock {code} {day}"))
        )

    output: list[dict[str, Any]] = []
    max_horizon = max(normalized_horizons)
    for (code, sector_name), prices in sorted(grouped.items()):
        prices.sort(key=lambda item: item[0])
        stock_by_date = dict(prices)
        for as_of, current_stock in prices:
            as_of_index = calendar_index.get(as_of)
            if as_of_index is None:
                continue
            current_sector = sector_prices.get((sector_name, as_of))
            if current_sector is None:
                continue
            labels: dict[str, float | None] = {}
            label_dates: dict[str, str | None] = {}
            has_target_date = False
            for horizon in normalized_horizons:
                raw_key = f"future_return_{horizon}d"
                sector_key = f"future_sector_return_{horizon}d"
                excess_key = f"future_excess_return_{horizon}d"
                target_index = as_of_index + horizon
                future_day = (
                    calendar_dates[target_index]
                    if target_index < len(calendar_dates)
                    else None
                )
                for key in (raw_key, sector_key, excess_key):
                    labels[key] = None
                    label_dates[key] = future_day
                if future_day is None:
                    continue
                has_target_date = True
                future_stock = stock_by_date.get(future_day)
                future_sector = sector_prices.get((sector_name, future_day))
                if future_stock is None or future_sector is None:
                    continue
                stock_return = future_stock / current_stock - 1.0
                sector_return = future_sector / current_sector - 1.0
                labels[raw_key] = stock_return
                labels[sector_key] = sector_return
                labels[excess_key] = stock_return - sector_return
            if not has_target_date:
                continue
            training_key = f"future_excess_return_{training_horizon}d"
            training_label = labels[training_key]
            output.append(
                {
                    "schema_version": LABEL_SCHEMA_VERSION,
                    "as_of_date": as_of,
                    "stock_code": code,
                    "sector_name": sector_name,
                    "labels": labels,
                    "label_dates": label_dates,
                    "training_label": training_label,
                    "training_label_end_date": (
                        label_dates[training_key]
                        if training_label is not None
                        else None
                    ),
                    "label_definition": LABEL_DEFINITION,
                    "max_label_horizon": max_horizon,
                }
            )
    output.sort(key=lambda row: (row["as_of_date"], row["stock_code"]))
    return output
