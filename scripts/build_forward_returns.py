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
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

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
        return float(value)
    except (TypeError, ValueError):
        return None


def load_candidate_codes(candidate_path: Path) -> list[str]:
    data = json.loads(candidate_path.read_text(encoding="utf-8-sig"))
    candidates = data if isinstance(data, list) else data.get("candidates", [])
    seen: set[str] = set()
    codes: list[str] = []
    for item in candidates if isinstance(candidates, list) else []:
        code = str(item.get("code", "")).strip()
        if code and code not in seen:
            seen.add(code)
            codes.append(code)
    return codes


class StockDBSdkBarsClient(StockDBSdkClient):
    """Forward-return adapter that preserves the legacy projected fields."""

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
) -> dict[str, float | None]:
    ordered = sorted(
        [
            {"date": _date_key(bar.get("date", "")), "close": _coerce_float(bar.get("close"))}
            for bar in bars
            if bar.get("date") and _coerce_float(bar.get("close")) is not None
        ],
        key=lambda item: item["date"],
    )
    as_of_key = _date_key(as_of)
    signal_idx = next((idx for idx, bar in enumerate(ordered) if bar["date"] == as_of_key), None)
    result = {f"{horizon}d": None for horizon in horizons}
    if signal_idx is None:
        return result

    base_close = ordered[signal_idx]["close"]
    if not base_close or base_close <= 0:
        return result

    for horizon in horizons:
        target_idx = signal_idx + int(horizon)
        if target_idx >= len(ordered):
            result[f"{horizon}d"] = None
            continue
        target_close = ordered[target_idx]["close"]
        if target_close is None:
            result[f"{horizon}d"] = None
        else:
            result[f"{horizon}d"] = round((target_close - base_close) / base_close * 100, 4)
    return result


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
) -> dict:
    client = client or make_bars_client("http")
    signal_date = _parse_date(as_of)
    start = _service_date(signal_date)
    end = _service_date(signal_date + timedelta(days=lookahead_days))
    horizons = tuple(int(horizon) for horizon in horizons)

    forward_returns: dict[str, dict[str, float | None]] = {}
    errors: dict[str, str] = {}
    bar_counts: dict[str, int] = {}

    for code in codes:
        try:
            bars = client.get_stock_bars(code, start, end, frequency="1d", fq="qfq")
            bar_counts[code] = len(bars or [])
            forward_returns[code] = compute_forward_returns_from_bars(bars or [], as_of, horizons)
        except Exception as exc:
            errors[code] = str(exc)
            forward_returns[code] = {f"{horizon}d": None for horizon in horizons}
            bar_counts[code] = 0

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
        "horizons": [f"{horizon}d" for horizon in horizons],
        "coverage": {
            "stock_count": len(codes),
            "stocks_with_any_forward_return": with_any,
            "missing_or_empty_count": max(len(codes) - with_any, 0),
            "coverage_ratio": round(with_any / len(codes), 4) if codes else 0,
        },
        "bar_counts": bar_counts,
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, client=None) -> int:
    args = parse_args(argv)
    candidate_path = Path(args.candidate_path) if args.candidate_path else DEFAULT_AGENT_BRIDGE_DIR / args.as_of / "top30_candidates.json"
    output_base = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR
    horizons = tuple(int(part.strip()) for part in args.horizons.split(",") if part.strip())

    if not candidate_path.exists():
        print(f"ERROR: candidate file not found: {candidate_path}", file=sys.stderr)
        return 2

    codes = load_candidate_codes(candidate_path)
    bars_client = client or make_bars_client(args.source, expected_min_date=args.as_of)
    result = build_forward_returns(
        codes,
        args.as_of,
        client=bars_client,
        horizons=horizons,
        lookahead_days=args.lookahead_days,
    )

    output_dir = output_base / args.as_of
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "forward_returns.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

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
