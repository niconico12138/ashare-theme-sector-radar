#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build forward-return observations for scoring calibration.

The script reads a dated candidate pool, fetches daily bars from
market_data_service, and writes ``forward_returns.json`` for
``evaluate_scoring_calibration.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
DEFAULT_AGENT_BRIDGE_DIR = PROJECT_ROOT / "reports" / "agent_bridge"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "forward_returns"
DEFAULT_HORIZONS = (1, 3, 5)
SDK_PROJECTED_FIELDS = ("date", "code", "close", "open")
from theme_sector_radar.data.stockdb_sdk_client import StockDBSdkClient
from theme_sector_radar.data.trading_calendar import load_trading_calendar
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)


def _parse_date(value: str) -> datetime:
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text[:10] if fmt == "%Y-%m-%d" else text[:8], fmt)
        except ValueError:
            continue
    raise ValueError(f"unsupported date: {value}")


def _date_key(value: str) -> str:
    return _parse_date(value).strftime("%Y-%m-%d")


def _service_date(value: datetime) -> str:
    return value.strftime("%Y%m%d")


def _coerce_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        converted = float(value)
    except (TypeError, ValueError):
        return None
    return converted if math.isfinite(converted) else None


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normalized_trading_dates(
    trading_dates: Sequence[str], *, signal_date: str
) -> list[str]:
    dates = [_date_key(value) for value in trading_dates]
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise ValueError("trading dates must be sorted and unique")
    if signal_date not in dates:
        raise ValueError("signal date is absent from the trading calendar")
    return dates


def _extract_candidate_codes(data: object) -> list[str]:
    if isinstance(data, list):
        candidates = data
    elif (
        isinstance(data, dict)
        and data.get("candidate_chain") == "direction_linkage_v2"
    ):
        formal = data.get("formal_candidate_selection")
        if (
            isinstance(formal, dict)
            and formal.get("status") == "active_for_paper_research"
            and isinstance(formal.get("selected"), list)
        ):
            candidates = formal["selected"]
        else:
            candidates = []
    elif isinstance(data, dict) and any(
        key in data
        for key in (
            "trend_candidates_all",
            "burst_candidates_all",
            "direction_shadow_candidates_all",
        )
    ):
        candidates = (
            list(data.get("trend_candidates_all", []))
            + list(data.get("burst_candidates_all", []))
            + list(data.get("direction_shadow_candidates_all", []))
        )
    else:
        candidates = data.get("candidates", []) if isinstance(data, dict) else []
    seen: set[str] = set()
    codes: list[str] = []
    for item in candidates if isinstance(candidates, list) else []:
        code = str(item.get("code", "")).strip()
        if code and code not in seen:
            seen.add(code)
            codes.append(code)
    return codes


def load_candidate_codes_with_sha256(candidate_path: Path) -> tuple[list[str], str]:
    data, sha256 = load_strict_json_with_sha256(candidate_path)
    return _extract_candidate_codes(data), sha256


def load_candidate_codes(candidate_path: Path) -> list[str]:
    codes, _sha256 = load_candidate_codes_with_sha256(candidate_path)
    return codes


class StockDBSdkBarsClient(StockDBSdkClient):
    """Forward-return adapter that preserves the legacy projected fields."""

    selection = {
        "source": "stockdb-sdk",
        "reason": "explicit_stockdb_sdk",
    }

    def get_stock_bars(
        self,
        code: str,
        start: str,
        end: str,
        frequency: str = "1d",
        fq: str | None = "qfq",
    ) -> list[dict]:
        return super().get_stock_bars(
            code,
            start,
            end,
            frequency=frequency,
            fq=fq,
            fields=SDK_PROJECTED_FIELDS,
        )


def compute_forward_returns_from_bars(
    bars: list[dict],
    as_of: str,
    horizons: Iterable[int] = DEFAULT_HORIZONS,
    *,
    trading_dates: Sequence[str],
) -> dict[str, float | None]:
    returns, _metadata = compute_forward_return_observations_from_bars(
        bars, as_of, horizons, trading_dates=trading_dates
    )
    return returns


def _normalize_source_bars(bars: list[dict]) -> list[dict]:
    ordered = []
    seen_dates: set[str] = set()
    for bar in bars:
        if not isinstance(bar, Mapping) or not bar.get("date"):
            continue
        day = _date_key(bar.get("date", ""))
        if day in seen_dates:
            raise ValueError(f"duplicate source bar date: {day}")
        seen_dates.add(day)
        close = _coerce_float(bar.get("close"))
        ordered.append(
            {"date": day, "close": close if close is not None and close > 0 else None}
        )
    ordered.sort(key=lambda item: item["date"])
    return ordered


def compute_forward_return_observations_from_bars(
    bars: list[dict],
    as_of: str,
    horizons: Iterable[int] = DEFAULT_HORIZONS,
    *,
    trading_dates: Sequence[str],
    stock_code: str | None = None,
) -> tuple[dict[str, float | None], dict]:
    """Return values on exchange-calendar targets without suspension roll."""

    horizons = tuple(int(horizon) for horizon in horizons)
    as_of_key = _date_key(as_of)
    calendar_dates = _normalized_trading_dates(
        trading_dates, signal_date=as_of_key
    )
    ordered = _normalize_source_bars(bars)
    bars_by_date = {row["date"]: row["close"] for row in ordered}
    source_latest = ordered[-1]["date"] if ordered else None
    signal_close = bars_by_date.get(as_of_key)
    signal_index = calendar_dates.index(as_of_key)
    bar_snapshot_sha256 = _canonical_sha256(
        {
            "stock_code": str(stock_code or ""),
            "frequency": "1d",
            "adjustment": "qfq",
            "bars": ordered,
        }
    )
    result = {f"{horizon}d": None for horizon in horizons}
    metadata = {
        "signal_date": as_of_key,
        "frequency": "1d",
        "adjustment": "qfq",
        "stock_code": str(stock_code or ""),
        "signal_close": signal_close,
        "source_latest_bar_date": source_latest,
        "bar_snapshot_sha256": bar_snapshot_sha256,
        "horizons": {
            f"{horizon}d": {
                "horizon_trading_days": horizon,
                "target_trading_date": None,
                "target_close": None,
                "mature": False,
                "return_available": False,
            }
            for horizon in horizons
        },
    }
    for horizon in horizons:
        target_idx = signal_index + int(horizon)
        if target_idx >= len(calendar_dates):
            continue
        target_date = calendar_dates[target_idx]
        target_close = bars_by_date.get(target_date)
        horizon_metadata = metadata["horizons"][f"{horizon}d"]
        horizon_metadata["target_trading_date"] = target_date
        horizon_metadata["target_close"] = target_close
        horizon_metadata["mature"] = bool(
            source_latest is not None and source_latest >= target_date
        )
        if not horizon_metadata["mature"]:
            continue
        if signal_close is None:
            continue
        if target_close is None:
            continue
        result[f"{horizon}d"] = round(
            (target_close - signal_close) / signal_close * 100, 4
        )
        horizon_metadata["return_available"] = True
    return result, metadata


def _make_http_client():
    from theme_sector_radar.data.market_data_http_client import MarketDataHttpClient

    return MarketDataHttpClient()


def make_bars_client(source: str = "http", expected_min_date: str | None = None):
    if source == "stockdb-sdk":
        return StockDBSdkBarsClient()
    if source == "auto":
        from theme_sector_radar.data.bars_data_router import AutoBarsClient

        return AutoBarsClient(expected_min_date=expected_min_date)
    if source == "http":
        return _make_http_client()
    raise ValueError(f"unsupported source: {source}")


def build_forward_returns(
    codes: list[str],
    as_of: str,
    client=None,
    horizons: Iterable[int] = DEFAULT_HORIZONS,
    lookahead_days: int = 14,
    trading_calendar: Mapping[str, Any] | None = None,
) -> dict:
    if not isinstance(trading_calendar, Mapping):
        raise ValueError("a versioned trading_calendar is required")
    calendar_dates = trading_calendar.get("dates")
    if not isinstance(calendar_dates, list):
        raise ValueError("trading_calendar dates are required")
    client = client or make_bars_client("http")
    signal_date = _parse_date(as_of)
    start = _service_date(signal_date)
    end = _service_date(signal_date + timedelta(days=lookahead_days))
    horizons = tuple(int(horizon) for horizon in horizons)

    forward_returns: dict[str, dict[str, float | None]] = {}
    label_metadata: dict[str, dict] = {}
    errors: dict[str, str] = {}
    bar_counts: dict[str, int] = {}
    source_bar_manifest: dict[str, dict[str, Any]] = {}

    for code in codes:
        try:
            bars = client.get_stock_bars(code, start, end, frequency="1d", fq="qfq")
            bar_counts[code] = len(bars or [])
            forward_returns[code], label_metadata[code] = (
                compute_forward_return_observations_from_bars(
                    bars or [],
                    as_of,
                    horizons,
                    trading_dates=calendar_dates,
                    stock_code=code,
                )
            )
            source_bar_manifest[code] = {
                "stock_code": code,
                "normalized_bars": _normalize_source_bars(bars or []),
                "bar_snapshot_sha256": label_metadata[code]["bar_snapshot_sha256"],
                "bar_count": len(bars or []),
                "query": {
                    "start": start,
                    "end": end,
                    "frequency": "1d",
                    "adjustment": "qfq",
                    "projected_fields": list(SDK_PROJECTED_FIELDS),
                },
            }
        except Exception as exc:
            errors[code] = str(exc)
            forward_returns[code], label_metadata[code] = (
                compute_forward_return_observations_from_bars(
                    [],
                    as_of,
                    horizons,
                    trading_dates=calendar_dates,
                    stock_code=code,
                )
            )
            bar_counts[code] = 0
            source_bar_manifest[code] = {
                "stock_code": code,
                "normalized_bars": [],
                "bar_snapshot_sha256": label_metadata[code]["bar_snapshot_sha256"],
                "bar_count": 0,
                "query": {
                    "start": start,
                    "end": end,
                    "frequency": "1d",
                    "adjustment": "qfq",
                    "projected_fields": list(SDK_PROJECTED_FIELDS),
                },
            }

    with_any = sum(
        1
        for item in forward_returns.values()
        if any(value is not None for value in item.values())
    )
    bars_data_source = getattr(client, "selection", None)

    return {
        "schema_version": "1.0",
        "as_of": as_of,
        "generated_at": datetime.now().isoformat(),
        "bars_data_source": bars_data_source or {"source": "custom_client"},
        "label_contract": {
            "schema_version": "forward-return-label-contract-v2",
            "frequency": "1d",
            "adjustment": "qfq",
            "target_date_basis": "versioned_exchange_calendar",
        },
        "trading_calendar": dict(trading_calendar),
        "horizons": [f"{horizon}d" for horizon in horizons],
        "coverage": {
            "stock_count": len(codes),
            "stocks_with_any_forward_return": with_any,
            "missing_or_empty_count": max(len(codes) - with_any, 0),
            "coverage_ratio": round(with_any / len(codes), 4) if codes else 0,
        },
        "bar_counts": bar_counts,
        "source_bar_manifest": source_bar_manifest,
        "label_metadata": label_metadata,
        "errors": errors,
        "forward_returns": forward_returns,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build forward_returns.json from market_data_service bars")
    parser.add_argument("--as-of", required=True, help="Signal date, YYYY-MM-DD")
    parser.add_argument("--candidate-path", default=None, help="Path to top30_candidates.json")
    parser.add_argument("--output-dir", default=None, help="Base output directory")
    parser.add_argument("--horizons", default="1,3,5", help="Comma-separated future trading-day horizons")
    parser.add_argument("--lookahead-days", type=int, default=14, help="Natural-day buffer used when fetching bars")
    parser.add_argument("--source", choices=["http", "stockdb-sdk", "auto"], default="http", help="Bar data source")
    parser.add_argument("--trading-calendar-path", required=True, type=Path)
    parser.add_argument("--expected-calendar-sha256", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, client=None) -> int:
    args = parse_args(argv)
    candidate_path = Path(args.candidate_path) if args.candidate_path else DEFAULT_AGENT_BRIDGE_DIR / args.as_of / "top30_candidates.json"
    output_base = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR
    horizons = tuple(int(part.strip()) for part in args.horizons.split(",") if part.strip())

    if not candidate_path.exists():
        print(f"ERROR: candidate file not found: {candidate_path}", file=sys.stderr)
        return 2

    codes, candidate_sha256 = load_candidate_codes_with_sha256(candidate_path)
    trading_calendar = load_trading_calendar(
        args.trading_calendar_path,
        as_of=args.as_of,
        include_future=True,
    )
    if trading_calendar["sha256"] != args.expected_calendar_sha256.lower():
        raise ValueError("trading calendar SHA mismatch")
    bars_client = client or make_bars_client(args.source, expected_min_date=args.as_of)
    result = build_forward_returns(
        codes,
        args.as_of,
        client=bars_client,
        horizons=horizons,
        lookahead_days=args.lookahead_days,
        trading_calendar=trading_calendar,
    )
    result["candidate_input"] = {
        "path": str(candidate_path.resolve()),
        "sha256": candidate_sha256,
        "sha256_basis": "raw_utf8_file_bytes",
    }

    output_dir = output_base / args.as_of
    output_path = output_dir / "forward_returns.json"
    write_strict_json_atomic(output_path, result)

    coverage = result["coverage"]
    print(f"JSON: {output_path}")
    print(
        "Coverage: "
        f"{coverage['stocks_with_any_forward_return']}/{coverage['stock_count']} "
        f"({coverage['coverage_ratio']:.1%})"
    )
    bars_source = result.get("bars_data_source", {})
    if isinstance(bars_source, dict) and bars_source.get("source"):
        reason = bars_source.get("reason")
        suffix = f" ({reason})" if reason else ""
        print(f"Bars source: {bars_source['source']}{suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
