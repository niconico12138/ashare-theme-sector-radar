"""Load point-in-time sector returns for the production base radar."""

from __future__ import annotations

import math
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ..data.return_validation import trusted_daily_return
from ..models import SectorType
from ..reporting.strict_json import loads_strict_json


def _field(record: Dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in record:
            return record[name]
    return None


def _finite_float(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def _returns_from_records(
    records: List[Dict[str, Any]],
    *,
    as_of_date: str,
    max_returns: int,
) -> Tuple[List[float], List[str], List[List[str]]]:
    try:
        cutoff = date.fromisoformat(as_of_date)
    except ValueError as exc:
        raise ValueError("as_of_date must be an ISO date") from exc
    dated = []
    seen_dates = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("history record must be an object")
        record_date = str(_field(record, "date", "日期", "trade_date") or "")
        try:
            parsed_date = date.fromisoformat(record_date)
        except ValueError as exc:
            raise ValueError(f"history date must be an ISO date: {record_date}") from exc
        if parsed_date.isoformat() != record_date:
            raise ValueError(f"history date must be an ISO date: {record_date}")
        if parsed_date > cutoff:
            continue
        if record_date in seen_dates:
            raise ValueError(f"duplicate history date: {record_date}")
        seen_dates.add(record_date)
        dated.append((record_date, record))
    dated.sort(key=lambda item: item[0])
    if not dated:
        return [], [], []

    closes = [
        _finite_float(_field(record, "close", "收盘价", "收盘"), "close")
        for _, record in dated
    ]
    if any(close <= 0 for close in closes):
        raise ValueError("close must be positive")
    returns = [
        trusted_daily_return(
            (current / previous - 1.0) * 100.0,
            field="derived daily return",
        )
        for previous, current in zip(closes, closes[1:])
    ]
    dates = [record_date for record_date, _ in dated[1:]]
    periods = [
        [previous_date, current_date]
        for (previous_date, _), (current_date, _) in zip(dated, dated[1:])
    ]

    return (
        returns[-max_returns:],
        dates[-max_returns:],
        periods[-max_returns:],
    )


def load_sector_trend_history(
    history_root: str | Path,
    *,
    sector_type: SectorType,
    as_of_date: str,
    max_returns: int = 20,
) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """Load completed returns through ``as_of_date`` without future records."""
    if max_returns <= 0:
        raise ValueError("max_returns must be positive")
    type_dir = "industry" if sector_type == SectorType.INDUSTRY else "concept"
    root = Path(history_root) / type_dir
    if not root.is_dir():
        return {}, [f"行业趋势历史目录不存在: {root}"]

    history: Dict[str, Dict[str, Any]] = {}
    warnings: List[str] = []
    for path in sorted(root.glob("*.json"), key=lambda item: item.name):
        try:
            payload = loads_strict_json(path.read_text(encoding="utf-8"), context=str(path))
            if not isinstance(payload, dict):
                raise ValueError("history payload must be an object")
            records = payload.get("records", [])
            if not isinstance(records, list):
                raise ValueError("history records must be an array")
            recent_returns, recent_dates, recent_periods = _returns_from_records(
                records,
                as_of_date=as_of_date,
                max_returns=max_returns,
            )
            if not recent_returns or recent_dates[-1] != as_of_date:
                continue
            sector_name = str(payload.get("sector_name") or path.stem).strip()
            if not sector_name or sector_name in history:
                raise ValueError("duplicate or empty sector identity")
            history[sector_name] = {
                "recent_returns": recent_returns,
                "recent_dates": recent_dates,
                "recent_periods": recent_periods,
                "history_days": len(recent_returns),
                "history_source": "sector_history_cache",
            }
        except (OSError, UnicodeError, ValueError) as exc:
            warnings.append(f"基础趋势历史不可用 {path.name}: {exc}")
    return history, warnings
