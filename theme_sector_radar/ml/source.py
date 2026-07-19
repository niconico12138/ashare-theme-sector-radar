"""Strict adapters for isolated ML feature and label source documents."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from theme_sector_radar.data.trading_calendar import (
    validate_trading_calendar_identity,
)
from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)

from .feature_builder import build_feature_row
from .label_builder import build_forward_label_rows
from .schema import MODE


FEATURE_SOURCE_SCHEMA_VERSION = "ml-stock-feature-source-v1"
LABEL_SOURCE_SCHEMA_VERSION = "ml-stock-label-source-v1"


def build_feature_rows_from_source(
    source: Mapping[str, Any], *, as_of_date: str | None = None
) -> list[dict[str, Any]]:
    if source.get("schema_version") != FEATURE_SOURCE_SCHEMA_VERSION:
        raise ValueError("ML feature source schema mismatch")
    if source.get("mode") != MODE:
        raise ValueError("ML feature source must be paper/shadow only")
    validate_no_executable_instructions(source, context="ML feature source")
    snapshots = source.get("snapshots")
    if not isinstance(snapshots, list):
        raise ValueError("ML feature source snapshots are missing")
    rows: list[dict[str, Any]] = []
    seen_dates: set[str] = set()
    for snapshot in snapshots:
        if not isinstance(snapshot, Mapping):
            raise ValueError("ML feature snapshot must be an object")
        day = str(snapshot.get("as_of_date") or "")
        if as_of_date is not None and day != as_of_date:
            continue
        if day in seen_dates:
            raise ValueError(f"duplicate ML feature snapshot date: {day}")
        seen_dates.add(day)
        candidates = snapshot.get("candidates")
        bars_by_code = snapshot.get("bars_by_code")
        if not isinstance(candidates, list) or not isinstance(bars_by_code, Mapping):
            raise ValueError(f"ML feature snapshot inputs are incomplete: {day}")
        seen_codes: set[str] = set()
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                raise ValueError("ML feature candidate must be an object")
            code = str(candidate.get("code") or candidate.get("stock_code") or "").zfill(6)
            if code in seen_codes:
                raise ValueError(f"duplicate ML feature candidate: {day} {code}")
            seen_codes.add(code)
            bars = bars_by_code.get(code)
            if not isinstance(bars, Sequence) or isinstance(bars, (str, bytes)):
                raise ValueError(f"ML feature bars are missing: {day} {code}")
            rows.append(build_feature_row(candidate, bars, as_of_date=day))
    if as_of_date is not None and not rows:
        raise ValueError(f"ML feature source has no snapshot for {as_of_date}")
    return rows


def build_label_rows_from_source(
    source: Mapping[str, Any],
    *,
    trading_calendar: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if source.get("schema_version") != LABEL_SOURCE_SCHEMA_VERSION:
        raise ValueError("ML label source schema mismatch")
    if source.get("mode") != MODE:
        raise ValueError("ML label source must be paper/shadow only")
    validate_no_executable_instructions(source, context="ML label source")
    stock_rows = source.get("stock_price_rows")
    sector_rows = source.get("sector_price_rows")
    recorded_calendar = source.get("trading_calendar")
    if trading_calendar is not None:
        try:
            validate_trading_calendar_identity(
                recorded_calendar,
                trading_calendar,
                context="ML label source",
            )
        except ValueError as exc:
            raise ValueError(f"calendar identity mismatch: {exc}") from exc
        trading_dates = trading_calendar.get("dates")
    else:
        trading_dates = source.get("trading_dates")
        if not isinstance(trading_dates, list) and isinstance(
            recorded_calendar, Mapping
        ):
            trading_dates = recorded_calendar.get("dates")
    if (
        not isinstance(stock_rows, list)
        or not isinstance(sector_rows, list)
        or not isinstance(trading_dates, list)
    ):
        raise ValueError("ML label price sources are missing")
    return build_forward_label_rows(
        stock_rows,
        sector_rows,
        trading_dates=trading_dates,
    )
