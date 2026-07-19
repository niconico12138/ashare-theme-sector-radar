"""Content-addressed A-share trading calendars for reproducible research."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from theme_sector_radar.reporting.strict_json import load_strict_json_with_sha256


SCHEMA_VERSION = "a_share_trading_calendar.v1"


def build_trading_calendar_report(
    dates: Iterable[str],
    *,
    source: str,
    requested_start: str,
    requested_end: str,
) -> dict[str, Any]:
    normalized = sorted({_iso_date(value) for value in dates})
    normalized_start = _iso_date(requested_start)
    normalized_end = _iso_date(requested_end)
    if not source:
        raise ValueError("trading calendar source is required")
    if normalized_start > normalized_end:
        raise ValueError("trading calendar requested range is invalid")
    if any(date.fromisoformat(value).weekday() >= 5 for value in normalized):
        raise ValueError("trading calendar contains a weekend date")
    selected = [value for value in normalized if normalized_start <= value <= normalized_end]
    return {
        "schema_version": SCHEMA_VERSION,
        "market": "CN_A",
        "source": source,
        "requested_start": normalized_start,
        "requested_end": normalized_end,
        "dates": selected,
        "date_count": len(selected),
    }


def load_trading_calendar(
    path: Path, *, as_of: str, include_future: bool = False
) -> dict[str, Any]:
    data, calendar_sha256 = load_strict_json_with_sha256(path)
    return validate_trading_calendar_artifact(
        data,
        path=path,
        sha256=calendar_sha256,
        as_of=as_of,
        include_future=include_future,
    )


def validate_trading_calendar_artifact(
    data: Any,
    *,
    path: Path,
    sha256: str,
    as_of: str,
    include_future: bool = False,
) -> dict[str, Any]:
    """Validate one already parsed and hashed calendar byte snapshot."""
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("trading calendar schema mismatch")
    if data.get("market") != "CN_A" or not data.get("source"):
        raise ValueError("trading calendar identity is incomplete")
    raw_dates = data.get("dates")
    if not isinstance(raw_dates, list):
        raise ValueError("trading calendar dates must be a list")
    normalized_dates = [_iso_date(value) for value in raw_dates]
    if len(normalized_dates) != len(set(normalized_dates)):
        raise ValueError("trading calendar contains duplicate dates")
    all_dates = sorted(normalized_dates)
    declared_count = data.get("date_count")
    if (
        not isinstance(declared_count, int)
        or isinstance(declared_count, bool)
        or declared_count != len(all_dates)
    ):
        raise ValueError("trading calendar date_count mismatch")
    requested_start = str(data.get("requested_start") or "")
    requested_end = str(data.get("requested_end") or "")
    if (
        not requested_start
        or not requested_end
        or _iso_date(requested_start) != requested_start
        or _iso_date(requested_end) != requested_end
        or requested_start > requested_end
    ):
        raise ValueError("trading calendar requested range is invalid")
    if any(value < requested_start or value > requested_end for value in all_dates):
        raise ValueError("trading calendar date is outside requested range")
    normalized_as_of = _iso_date(as_of)
    if requested_end < normalized_as_of:
        raise ValueError(f"trading calendar coverage ends before audit as_of {as_of}")
    if any(date.fromisoformat(value).weekday() >= 5 for value in all_dates):
        raise ValueError("trading calendar contains a weekend date")
    if (
        len(sha256) != 64
        or any(character not in "0123456789abcdefABCDEF" for character in sha256)
    ):
        raise ValueError("trading calendar SHA is invalid")
    dates = all_dates if include_future else [
        value for value in all_dates if value <= normalized_as_of
    ]
    return {
        "dates": dates,
        "source": str(data["source"]),
        "path": str(path),
        "sha256": sha256.lower(),
        "requested_start": requested_start,
        "requested_end": requested_end,
    }


def next_trading_date(
    dates: Sequence[str],
    signal_date: str,
    *,
    as_of: str,
) -> str | None:
    return next((value for value in dates if signal_date < value <= as_of), None)


def validate_trading_calendar_identity(
    recorded: Mapping[str, Any] | None,
    current: Mapping[str, Any],
    *,
    context: str,
) -> None:
    if not isinstance(recorded, Mapping):
        raise ValueError(f"{context} trading calendar identity is required")
    for field in ("dates", "source", "sha256", "requested_start", "requested_end"):
        if recorded.get(field) != current.get(field):
            raise ValueError(
                f"{context} calendar {field.replace('_', ' ')} mismatch"
            )
    recorded_path = str(recorded.get("path") or "")
    current_path = str(current.get("path") or "")
    if (
        not recorded_path
        or not current_path
        or str(Path(recorded_path).resolve()).casefold()
        != str(Path(current_path).resolve()).casefold()
    ):
        raise ValueError(f"{context} calendar path mismatch")


def _iso_date(value: Any) -> str:
    raw_value = str(value)
    try:
        normalized = date.fromisoformat(raw_value).isoformat()
    except ValueError as exc:
        raise ValueError("trading calendar date must be a canonical ISO date") from exc
    if raw_value != normalized:
        raise ValueError("trading calendar date must be a canonical ISO date")
    return normalized
