"""Read local minute archives directly from ZIP files for paper-only research."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import zipfile
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping


def detect_bar_interval_minutes(bars: list[Mapping[str, Any]]) -> int | None:
    times = sorted(value for row in bars if (value := _bar_datetime(row)) is not None)
    intervals = []
    for previous, current in zip(times, times[1:]):
        if previous.date() != current.date():
            continue
        minutes = int((current - previous).total_seconds() // 60)
        if 0 < minutes <= 15:
            intervals.append(minutes)
    if not intervals:
        return None
    counts = Counter(intervals)
    return min(counts, key=lambda value: (-counts[value], value))


def validate_complete_a_share_session(
    bars: list[Mapping[str, Any]],
    *,
    interval_minutes: int,
) -> bool:
    rows = [dict(row) for row in bars]
    times = [_bar_datetime(row) for row in rows]
    if not times or any(value is None for value in times):
        return False
    trading_date = times[0].date()
    if any(value.date() != trading_date for value in times if value is not None):
        return False
    if _session_convention(times, trading_date, interval_minutes) is None:
        return False
    for row in rows:
        open_price, high, low, close = (_number(row.get(field)) for field in ("open", "high", "low", "close"))
        volume = _number(row.get("volume"))
        amount = _number(row.get("amount"))
        if any(value is None or value <= 0 for value in (open_price, high, low, close)):
            return False
        if volume is None or volume < 0 or amount is None or amount < 0:
            return False
        if low > min(open_price, close) or high < max(open_price, close) or low > high:
            return False
    return True


def validate_bar_security_identity(
    bars: list[Mapping[str, Any]],
    *,
    code: str,
    name: str,
    context: str,
) -> None:
    expected_code = _security_code(code)
    expected_name = str(name or "").strip()
    for row in bars:
        row_code = str(row.get("code") or "").strip()
        if row_code and _security_code(row_code) != expected_code:
            raise ValueError(f"{context} bar security identity mismatch")
        row_name = str(row.get("name") or "").strip()
        if row_name and expected_name and row_name != expected_name:
            raise ValueError(f"{context} bar security identity mismatch")


def security_bound_bars_sha256(
    bars: list[Mapping[str, Any]],
    *,
    code: str,
    name: str,
) -> str:
    """Bind source bar bytes to their parent candidate security identity."""
    normalized_code = _security_code(code)
    normalized_name = str(name or "").strip()
    if not normalized_code or not normalized_name:
        raise ValueError("source bar parent security identity is required")
    payload = json.dumps(
        {
            "code": normalized_code,
            "name": normalized_name,
            "bars": [dict(row) for row in bars],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def aggregate_complete_1m_session_to_5m(
    bars: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows = [dict(row) for row in bars]
    if not validate_complete_a_share_session(rows, interval_minutes=1):
        raise ValueError("a complete 1m A-share session is required for 5m aggregation")
    times = [_bar_datetime(row) for row in rows]
    trading_date = times[0].date()
    if _session_convention(times, trading_date, 1) == "stockdb_start_time":
        morning_rows = [
            row
            for row, timestamp in zip(rows, times)
            if timestamp is not None and timestamp.hour * 60 + timestamp.minute <= 689
        ]
        afternoon_rows = [
            row
            for row, timestamp in zip(rows, times)
            if timestamp is not None and timestamp.hour * 60 + timestamp.minute >= 780
        ]
        if len(morning_rows) != 120 or len(afternoon_rows) != 121:
            raise ValueError("StockDB 1m session has an unexpected lunch-boundary shape")
        groups: list[tuple[list[dict[str, Any]], datetime]] = []
        # StockDB moves the canonical 11:30 bar to 13:00; align each side
        # independently so the lunch gap can never share a 5m group.
        for segment in (morning_rows, afternoon_rows):
            cursor = 0
            groups.append((segment[:6], _bar_datetime(segment[5]) or datetime.min))
            cursor = 6
            while cursor < len(segment):
                group = segment[cursor : cursor + 5]
                groups.append((group, _bar_datetime(group[-1]) or datetime.min))
                cursor += 5
        aggregated = [
            _aggregate_bar_group(
                group,
                timestamp=_stockdb_elapsed_to_datetime(trading_date, group_end),
            )
            for group, last_timestamp in groups
            for elapsed in [_stockdb_trading_elapsed(last_timestamp)]
            if elapsed is not None
            for group_end in [_elapsed_group_end(elapsed, interval=5)]
        ]
        if len(aggregated) != 48 or not validate_complete_a_share_session(
            aggregated,
            interval_minutes=5,
        ):
            raise ValueError("StockDB 1m session could not be aggregated into a complete 5m session")
        return aggregated
    groups = [rows[:6]]
    cursor = 6
    while cursor < 121:
        groups.append(rows[cursor : cursor + 5])
        cursor += 5
    while cursor < len(rows):
        groups.append(rows[cursor : cursor + 5])
        cursor += 5
    aggregated = [_aggregate_bar_group(group) for group in groups]
    if len(aggregated) != 48 or not validate_complete_a_share_session(aggregated, interval_minutes=5):
        raise ValueError("1m session could not be aggregated into a complete 5m session")
    return aggregated


def _security_code(value: Any) -> str:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    return digits[-6:].zfill(6) if digits else ""


def _expected_session_datetimes(trading_date: date, interval_minutes: int) -> list[datetime]:
    if interval_minutes == 1:
        morning = [datetime.combine(trading_date, datetime.min.time()).replace(hour=9, minute=30)]
        current = morning[0] + timedelta(minutes=1)
        morning_end = morning[0].replace(hour=11, minute=30)
        while current <= morning_end:
            morning.append(current)
            current += timedelta(minutes=1)
        afternoon = []
        current = morning[0].replace(hour=13, minute=1)
        afternoon_end = morning[0].replace(hour=15, minute=0)
        while current <= afternoon_end:
            afternoon.append(current)
            current += timedelta(minutes=1)
        return morning + afternoon
    if interval_minutes == 5:
        result = []
        current = datetime.combine(trading_date, datetime.min.time()).replace(hour=9, minute=35)
        morning_end = current.replace(hour=11, minute=30)
        while current <= morning_end:
            result.append(current)
            current += timedelta(minutes=5)
        current = result[0].replace(hour=13, minute=5)
        afternoon_end = result[0].replace(hour=15, minute=0)
        while current <= afternoon_end:
            result.append(current)
            current += timedelta(minutes=5)
        return result
    return []


def _aggregate_bar_group(
    group: list[dict[str, Any]],
    *,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    first = group[0]
    last = group[-1]
    result = {
        "date": int((timestamp or _bar_datetime(last) or datetime.min).strftime("%Y%m%d%H%M%S")),
        "code": first.get("code"),
        "name": first.get("name"),
        "open": _number(first.get("open")),
        "high": max(_number(row.get("high")) for row in group),
        "low": min(_number(row.get("low")) for row in group),
        "close": _number(last.get("close")),
        "volume": sum(_number(row.get("volume")) or 0.0 for row in group),
        "amount": sum(_number(row.get("amount")) or 0.0 for row in group),
        "turnover": None,
        "is_st": first.get("is_st"),
    }
    open_price = result["open"]
    close_price = result["close"]
    result["pct_chg"] = round((close_price - open_price) / open_price * 100.0, 4) if open_price else None
    return result


def build_stop_trigger_path_labels(
    bars: list[dict[str, Any]],
    *,
    entry_price: float | None = None,
    trigger_drawdown_pct: float = -3.0,
    horizons: tuple[int, ...] = (5, 15, 30),
    bar_interval_minutes: int | None = None,
) -> dict[str, Any]:
    """Label the path strictly after the first fixed-drawdown trigger bar."""
    rows = sorted((dict(bar) for bar in bars), key=lambda bar: _bar_datetime(bar) or datetime.min)
    reference = entry_price or _first_price(rows)
    base = {
        "schema_version": "timing_stop_trigger_path.v1",
        "triggered": False,
        "decision_model": "trigger_bar_close_confirmed_next_bar_open_fill",
        "decision_time": "trigger_bar_close",
        "fill_model": "next_contiguous_bar_open_when_available",
        "entry_reference_price": reference,
        "trigger_drawdown_pct": trigger_drawdown_pct,
        "bar_interval_minutes": bar_interval_minutes,
        "trigger_index": None,
        "trigger_time": None,
        "trigger_price": None,
        "trigger_return_pct": None,
        "next_bar_fill_available": False,
        "next_bar_fill_return_pct": None,
        "trigger_snapshot": {},
        "horizons": {},
        "paper_research_only": True,
    }
    if reference is None or reference <= 0:
        return base
    trigger_index = next(
        (
            index
            for index, bar in enumerate(rows)
            if (price := _number(bar.get("close"))) is not None
            and _return_pct(price, reference) <= trigger_drawdown_pct
        ),
        None,
    )
    if trigger_index is None:
        return base
    trigger_bar = rows[trigger_index]
    trigger_price = _number(trigger_bar.get("close"))
    post_trigger = _contiguous_after_trigger(rows, trigger_index, bar_interval_minutes)
    fill_price = None
    if post_trigger:
        fill_price = _number(post_trigger[0].get("open"))
    base.update(
        {
            "triggered": True,
            "trigger_index": trigger_index,
            "trigger_time": bar_timestamp(trigger_bar),
            "trigger_price": trigger_price,
            "trigger_return_pct": _round(_return_pct(trigger_price, reference)) if trigger_price is not None else None,
            "next_bar_fill_available": fill_price is not None,
            "next_bar_fill_return_pct": _round(_return_pct(fill_price, reference)) if fill_price is not None else None,
            "trigger_snapshot": _trigger_snapshot(rows[: trigger_index + 1], reference),
        }
    )
    for horizon in sorted({int(value) for value in horizons if int(value) > 0}):
        segment = post_trigger[:horizon]
        lows = [_number(bar.get("low")) for bar in segment]
        highs = [_number(bar.get("high")) for bar in segment]
        closes = [_number(bar.get("close")) for bar in segment]
        prices_complete = bool(
            len(segment) >= horizon
            and all(value is not None for value in lows)
            and all(value is not None for value in highs)
            and all(value is not None for value in closes)
        )
        end_price = closes[-1] if prices_complete else None
        complete = prices_complete
        base["horizons"][str(horizon)] = {
            "requested_bars": horizon,
            "observed_bars": len(segment),
            "complete": complete,
            "end_return_from_entry_pct": _round(_return_pct(end_price, reference)) if complete else None,
            "end_return_from_trigger_fill_pct": _round(_return_pct(end_price, fill_price))
            if complete and fill_price is not None
            else None,
            "post_trigger_mae_pct": _round(_return_pct(min(lows), reference)) if complete else None,
            "post_trigger_mfe_pct": _round(_return_pct(max(highs), reference)) if complete else None,
            "recovered_entry": any(value >= reference for value in highs) if complete else None,
        }
    return base


def _contiguous_after_trigger(
    rows: list[dict[str, Any]],
    trigger_index: int,
    bar_interval_minutes: int | None,
) -> list[dict[str, Any]]:
    if bar_interval_minutes not in {1, 5}:
        return []
    contiguous = []
    previous = rows[trigger_index]
    for row in rows[trigger_index + 1 :]:
        if not is_expected_next_bar(previous, row, bar_interval_minutes):
            break
        contiguous.append(row)
        previous = row
    return contiguous


def is_expected_next_bar(previous: Mapping[str, Any], current: Mapping[str, Any], interval: int) -> bool:
    previous_time = _bar_datetime(previous)
    current_time = _bar_datetime(current)
    if previous_time is None or current_time is None or previous_time.date() != current_time.date():
        return False
    normal_next = previous_time + timedelta(minutes=interval)
    if current_time == normal_next:
        return True
    if previous_time.hour == 11 and previous_time.minute == 29:
        stockdb_lunch_next = previous_time.replace(hour=13, minute=0, second=0)
        if current_time == stockdb_lunch_next:
            return True
    if previous_time.hour == 11 and previous_time.minute == 30:
        expected = previous_time.replace(hour=13, minute=0, second=0) + timedelta(minutes=interval)
    else:
        expected = normal_next
    return current_time == expected


def bar_timestamp(row: Mapping[str, Any]) -> str:
    value = _bar_datetime(row)
    return value.strftime("%Y%m%d%H%M%S") if value is not None else ""


def _bar_datetime(row: Mapping[str, Any]) -> datetime | None:
    raw = "".join(character for character in str(row.get("time") or row.get("date") or "") if character.isdigit())
    if len(raw) < 14:
        return None
    try:
        return datetime.strptime(raw[:14], "%Y%m%d%H%M%S")
    except ValueError:
        return None


def _session_convention(
    times: list[datetime | None],
    trading_date: date,
    interval_minutes: int,
) -> str | None:
    if any(value is None for value in times):
        return None
    normalized = [value for value in times if value is not None]
    if normalized == _expected_session_datetimes(trading_date, interval_minutes):
        return "canonical"
    if interval_minutes == 1 and normalized == _stockdb_start_time_session_datetimes(trading_date):
        return "stockdb_start_time"
    return None


def _stockdb_start_time_session_datetimes(trading_date: date) -> list[datetime]:
    morning = [
        datetime.combine(trading_date, datetime.min.time()).replace(hour=9, minute=30)
        + timedelta(minutes=offset)
        for offset in range(120)
    ]
    afternoon = [
        datetime.combine(trading_date, datetime.min.time()).replace(hour=13, minute=0)
        + timedelta(minutes=offset)
        for offset in range(121)
    ]
    return morning + afternoon


def _stockdb_trading_elapsed(timestamp: datetime | None) -> int | None:
    if timestamp is None:
        return None
    minute_of_day = timestamp.hour * 60 + timestamp.minute
    if 570 <= minute_of_day <= 689:
        return minute_of_day - 570
    if 780 <= minute_of_day <= 900:
        return 120 + (minute_of_day - 780)
    return None


def _elapsed_group_end(elapsed: int, *, interval: int) -> int:
    if elapsed <= 0:
        return interval
    return ((elapsed - 1) // interval + 1) * interval


def _stockdb_elapsed_to_datetime(trading_date: date, elapsed: int) -> datetime:
    if elapsed <= 120:
        return datetime.combine(trading_date, datetime.min.time()).replace(hour=9, minute=30) + timedelta(
            minutes=elapsed
        )
    return datetime.combine(trading_date, datetime.min.time()).replace(hour=13, minute=0) + timedelta(
        minutes=elapsed - 120
    )


def _first_price(rows: list[dict[str, Any]]) -> float | None:
    for bar in rows:
        value = _number(bar.get("close")) or _number(bar.get("open"))
        if value is not None and value > 0:
            return value
    return None


def _trigger_snapshot(rows: list[dict[str, Any]], entry_price: float) -> dict[str, Any]:
    current = next((_number(bar.get("close")) for bar in reversed(rows) if _number(bar.get("close")) is not None), None)
    weighted = [
        (_number(bar.get("close")), _number(bar.get("volume")))
        for bar in rows
        if _number(bar.get("close")) is not None and (_number(bar.get("volume")) or 0.0) > 0
    ]
    total_volume = sum(volume for _, volume in weighted if volume is not None)
    vwap = sum(price * volume for price, volume in weighted if price is not None and volume is not None) / total_volume if total_volume else None
    amounts = [_number(bar.get("amount")) for bar in rows]
    amounts = [value for value in amounts if value is not None]
    recent_size = min(15, max(1, len(amounts) // 2))
    recent = amounts[-recent_size:]
    prior = amounts[-2 * recent_size : -recent_size]
    recent_average = sum(recent) / len(recent) if recent else None
    prior_average = sum(prior) / len(prior) if prior else None
    amount_ratio = recent_average / prior_average if recent_average is not None and prior_average else None
    close_vs_vwap = _return_pct(current, vwap) if current is not None and vwap else None
    money_flow_deterioration = (
        None
        if close_vs_vwap is None or amount_ratio is None
        else close_vs_vwap <= -1.0 and amount_ratio >= 1.2
    )
    return {
        "close_return_from_entry_pct": _round(_return_pct(current, entry_price)) if current is not None else None,
        "close_vs_cumulative_vwap_pct": _round(close_vs_vwap),
        "recent_amount_ratio": _round(amount_ratio),
        "money_flow_deterioration": money_flow_deterioration,
    }


def _return_pct(price: float | None, reference: float | None) -> float:
    if price is None or reference is None or reference <= 0:
        return 0.0
    return (price - reference) / reference * 100.0


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def annotate_board_trigger_features(
    rows_by_code: dict[str, list[dict[str, Any]]],
    board_bars_by_date: Mapping[str, Mapping[str, list[dict[str, Any]]]],
    stock_to_board_codes: Mapping[str, list[str]],
    *,
    board_weakness_pct: float = -1.0,
) -> dict[str, list[dict[str, Any]]]:
    """Attach static-mapping board evidence visible at each stock trigger."""
    for raw_code, rows in rows_by_code.items():
        code = str(raw_code).zfill(6)
        board_codes = [str(value) for value in stock_to_board_codes.get(code, [])]
        for row in rows:
            path = row.get("fixed_stop_path") or {}
            features = row.setdefault("trigger_factor_features", {})
            if not path.get("triggered"):
                continue
            date = str(row.get("date") or "")
            trigger_time = str(path.get("trigger_time") or "")
            date_boards = board_bars_by_date.get(date) or {}
            returns = [
                value
                for board_code in board_codes
                if (value := _board_return_at_time(date_boards.get(board_code) or [], trigger_time)) is not None
            ]
            board_return = sum(returns) / len(returns) if returns else None
            features.update(
                {
                    "board_synchronous_weakness": board_return <= board_weakness_pct if board_return is not None else None,
                    "board_return_at_trigger_pct": _round(board_return),
                    "matched_board_count": len(returns),
                    "board_mapping_kind": "current_static_research_pool",
                }
            )
    return rows_by_code


def _board_return_at_time(bars: list[dict[str, Any]], trigger_time: str) -> float | None:
    rows = sorted((dict(bar) for bar in bars), key=lambda bar: str(bar.get("time") or ""))
    if not rows:
        return None
    entry = _number(rows[0].get("open")) or _number(rows[0].get("close"))
    visible = [bar for bar in rows if str(bar.get("time") or "") <= trigger_time]
    current = next(
        (_number(bar.get("close")) for bar in reversed(visible) if _number(bar.get("close")) is not None),
        None,
    )
    if entry is None or current is None:
        return None
    return _return_pct(current, entry)


def available_board_dates(root: Path, start: str, end: str) -> list[str]:
    start_key = _date_key(start)
    end_key = _date_key(end)
    dates = []
    for path in root.rglob("*_1min.zip"):
        key = _date_key(path.name)
        if len(key) == 8 and start_key <= key <= end_key:
            dates.append(f"{key[:4]}-{key[4:6]}-{key[6:]}")
    return sorted(set(dates))


def read_stock_day_bars(archive_path: Path, code: str, day: str) -> list[dict[str, Any]]:
    normalized_code = str(code).zfill(6)
    with zipfile.ZipFile(archive_path) as archive:
        name = next(
            (
                item
                for item in archive.namelist()
                if Path(item).stem.lower().endswith(normalized_code + "_" + Path(archive_path).stem[:4])
            ),
            None,
        )
        if not name:
            return []
        rows = _csv_rows(archive.read(name))
    day_key = _date_key(day)
    return [_bar(row) for row in rows if _date_key(row.get("时间")) == day_key]


def read_board_day_bars(archive_path: Path, board_code: str) -> list[dict[str, Any]]:
    with zipfile.ZipFile(archive_path) as archive:
        name = f"{board_code}.csv"
        if name not in archive.namelist():
            return []
        return [_bar(row) for row in _csv_rows(archive.read(name))]


def read_board_day_bars_batch(archive_path: Path, board_codes: list[str]) -> dict[str, list[dict[str, Any]]]:
    result = {str(code): [] for code in board_codes}
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
        for code in result:
            name = f"{code}.csv"
            if name in names:
                result[code] = [_bar(row) for row in _csv_rows(archive.read(name))]
    return result


def read_board_name_code_map(archive_path: Path) -> dict[str, str]:
    result = {}
    with zipfile.ZipFile(archive_path) as archive:
        for archive_name in archive.namelist():
            rows = _csv_rows(archive.read(archive_name))
            if not rows:
                continue
            first = rows[0]
            board_name = str(first.get("名称") or "").strip()
            board_code = str(first.get("代码") or Path(archive_name).stem).strip()
            if board_name and board_code:
                result[board_name] = board_code
    return result


def scan_stock_daily_paths(archive_path: Path, code: str) -> list[dict[str, Any]]:
    normalized_code = str(code).zfill(6)
    with zipfile.ZipFile(archive_path) as archive:
        name = next(
            (
                item
                for item in archive.namelist()
                if Path(item).stem.lower().endswith(normalized_code + "_" + Path(archive_path).stem[:4])
            ),
            None,
        )
        if not name:
            return []
        rows = _csv_rows(archive.read(name))
    return _scan_stock_rows(rows, normalized_code)


def scan_stock_daily_paths_batch(
    archive_path: Any,
    codes: list[str],
    *,
    archive_name: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    normalized_codes = [str(code).zfill(6) for code in codes]
    source_name = archive_name or str(getattr(archive_path, "name", archive_path))
    year = Path(source_name).stem[:4]
    result = {code: [] for code in normalized_codes}
    market_aggregate: dict[str, list[float]] = {}
    with zipfile.ZipFile(archive_path) as archive:
        entries = {
            Path(name).stem.lower().split("_")[0][-6:]: name
            for name in archive.namelist()
            if Path(name).stem.lower().endswith("_" + year)
        }
        for code in normalized_codes:
            name = entries.get(code)
            if name:
                result[code] = _scan_stock_rows(
                    _csv_rows(archive.read(name)),
                    code,
                    market_aggregate=market_aggregate,
                )
    _annotate_market_trigger_features(result, market_aggregate)
    return result


def _scan_stock_rows(
    rows: list[dict[str, str]],
    normalized_code: str,
    *,
    market_aggregate: dict[str, list[float]] | None = None,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(_date_key(row.get("时间")), []).append(_bar(row))
    result = []
    for day, bars in sorted(grouped.items()):
        entry = next((bar.get("close") for bar in bars if bar.get("close") is not None), None)
        close = next((bar.get("close") for bar in reversed(bars) if bar.get("close") is not None), None)
        lows = [bar.get("low") for bar in bars if bar.get("low") is not None]
        highs = [bar.get("high") for bar in bars if bar.get("high") is not None]
        if not entry or close is None or not lows or not highs:
            continue
        if market_aggregate is not None:
            _accumulate_market_returns(bars, entry, market_aggregate)
        day_low = min(lows)
        day_high = max(highs)
        weighted = [
            (bar.get("close"), bar.get("volume"))
            for bar in bars
            if bar.get("close") is not None and bar.get("volume") is not None and bar.get("volume") > 0
        ]
        total_volume = sum(volume for _, volume in weighted)
        vwap = sum(price * volume for price, volume in weighted) / total_volume if total_volume > 0 else None
        segment_size = max(1, len(bars) // 3)
        early_amounts = [bar.get("amount") for bar in bars[:segment_size] if bar.get("amount") is not None]
        late_amounts = [bar.get("amount") for bar in bars[-segment_size:] if bar.get("amount") is not None]
        early_average = sum(early_amounts) / len(early_amounts) if early_amounts else None
        late_average = sum(late_amounts) / len(late_amounts) if late_amounts else None
        fixed_stop_path = build_stop_trigger_path_labels(bars, entry_price=entry, bar_interval_minutes=1)
        trigger_snapshot = fixed_stop_path.get("trigger_snapshot") or {}
        result.append(
            {
                "date": f"{day[:4]}-{day[4:6]}-{day[6:]}",
                "code": normalized_code,
                "mae_pct": round((day_low - entry) / entry * 100.0, 4),
                "mfe_pct": round((day_high - entry) / entry * 100.0, 4),
                "close_return_pct": round((close - entry) / entry * 100.0, 4),
                "close_position_pct": round((close - day_low) / (day_high - day_low) * 100.0, 4)
                if day_high > day_low
                else 50.0,
                "close_vs_vwap_pct": round((close - vwap) / vwap * 100.0, 4) if vwap else None,
                "late_amount_ratio": round(late_average / early_average, 4)
                if early_average and late_average is not None
                else None,
                "fixed_stop_path": fixed_stop_path,
                "trigger_factor_features": {
                    "relative_weakness": None,
                    "relative_vs_market_proxy_pct": None,
                    "market_proxy_return_at_trigger_pct": None,
                    "money_flow_deterioration": trigger_snapshot.get("money_flow_deterioration")
                    if fixed_stop_path.get("triggered")
                    else None,
                    "board_synchronous_weakness": None,
                    "board_return_at_trigger_pct": None,
                    "matched_board_count": 0,
                },
                "close_price": close,
            }
        )
    for index, row in enumerate(result[:-1]):
        next_close = result[index + 1]["close_price"]
        row["next_day_return_pct"] = round((next_close - row["close_price"]) / row["close_price"] * 100.0, 4)
    if result:
        result[-1]["next_day_return_pct"] = None
    for row in result:
        row.pop("close_price")
    return result


def _accumulate_market_returns(
    bars: list[dict[str, Any]],
    entry_price: float,
    aggregate: dict[str, list[float]],
) -> None:
    for bar in bars:
        time = str(bar.get("time") or "")
        close = _number(bar.get("close"))
        if not time or close is None:
            continue
        total_count = aggregate.setdefault(time, [0.0, 0.0])
        total_count[0] += _return_pct(close, entry_price)
        total_count[1] += 1.0


def _annotate_market_trigger_features(
    rows_by_code: dict[str, list[dict[str, Any]]],
    aggregate: Mapping[str, list[float]],
    *,
    relative_weakness_pct: float = -1.0,
) -> None:
    for rows in rows_by_code.values():
        for row in rows:
            path = row.get("fixed_stop_path") or {}
            if not path.get("triggered"):
                continue
            trigger_time = str(path.get("trigger_time") or "")
            stock_return = _number((path.get("trigger_snapshot") or {}).get("close_return_from_entry_pct"))
            total, count = aggregate.get(trigger_time) or [0.0, 0.0]
            benchmark = (total - stock_return) / (count - 1.0) if stock_return is not None and count > 1 else None
            relative = stock_return - benchmark if stock_return is not None and benchmark is not None else None
            features = row.setdefault("trigger_factor_features", {})
            features.update(
                {
                    "relative_weakness": relative <= relative_weakness_pct if relative is not None else None,
                    "relative_vs_market_proxy_pct": _round(relative),
                    "market_proxy_return_at_trigger_pct": _round(benchmark),
                    "market_proxy_kind": "equal_weight_research_universe_ex_self",
                }
            )


def _csv_rows(raw: bytes) -> list[dict[str, str]]:
    text = raw.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def _bar(row: dict[str, str]) -> dict[str, Any]:
    return {
        "time": _time_key(row.get("时间")),
        "open": _number(row.get("开盘价")),
        "close": _number(row.get("收盘价")),
        "high": _number(row.get("最高价")),
        "low": _number(row.get("最低价")),
        "volume": _number(row.get("成交量")),
        "amount": _number(row.get("成交额")),
    }


def _date_key(value: str | None) -> str:
    return re.sub(r"[^0-9]", "", str(value or ""))[:8]


def _time_key(value: str | None) -> str:
    digits = re.sub(r"[^0-9]", "", str(value or ""))
    return digits + "00" if len(digits) == 12 else digits


def _number(value: str | None) -> float | None:
    try:
        number = float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None
    return number if number is not None and math.isfinite(number) else None
