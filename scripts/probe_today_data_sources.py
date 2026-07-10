#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe whether today's final daily or realtime snapshot data is available."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.data.stockdb_sdk_client import StockDBSdkClient
from theme_sector_radar.data.today_realtime_client import TodayRealtimeClient


def normalize_date(value: str | None) -> str:
    text = str(value or "").strip().replace("-", "")
    return text[:8] if len(text) >= 8 else datetime.now().strftime("%Y%m%d")


def build_probe_result(
    expected_date: str,
    stockdb_client=None,
    realtime_client=None,
) -> dict:
    expected = normalize_date(expected_date)
    stockdb_client = stockdb_client or StockDBSdkClient()
    realtime_client = realtime_client or TodayRealtimeClient()
    latest = None
    stockdb_error = None
    try:
        latest = stockdb_client.get_latest_daily_date()
    except Exception as exc:
        stockdb_error = str(exc)

    if latest and str(latest) >= expected:
        return {
            "status": "final_daily_available",
            "expected_date": expected,
            "stockdb_latest_daily_date": latest,
            "recommended_source": "stockdb",
            "data_semantics": "daily_final",
            "stockdb_error": stockdb_error,
        }

    try:
        realtime = realtime_client.get_a_share_spot()
        if realtime.get("row_count", 0) > 0:
            return {
                "status": "intraday_snapshot_available",
                "expected_date": expected,
                "stockdb_latest_daily_date": latest,
                "recommended_source": realtime.get("source"),
                "data_semantics": realtime.get("data_semantics", "intraday_snapshot"),
                "realtime_row_count": realtime.get("row_count"),
                "realtime_fallback_used": realtime.get("fallback_used"),
                "stockdb_error": stockdb_error,
            }
    except Exception as exc:
        return {
            "status": "today_data_unavailable",
            "expected_date": expected,
            "stockdb_latest_daily_date": latest,
            "recommended_source": None,
            "data_semantics": None,
            "stockdb_error": stockdb_error,
            "realtime_error": str(exc),
        }

    return {
        "status": "today_data_unavailable",
        "expected_date": expected,
        "stockdb_latest_daily_date": latest,
        "recommended_source": None,
        "data_semantics": None,
        "stockdb_error": stockdb_error,
        "realtime_error": "realtime source returned no rows",
    }


def build_stock_snapshot_result(code: str, realtime_client=None) -> dict:
    realtime_client = realtime_client or TodayRealtimeClient()
    try:
        snapshot = realtime_client.get_stock_snapshot(code)
    except Exception as exc:
        return {
            "status": "stock_intraday_snapshot_unavailable",
            "code": str(code).strip(),
            "error": str(exc),
        }
    if snapshot:
        return {
            "status": "stock_intraday_snapshot_available",
            "code": str(code).strip(),
            "data_semantics": snapshot.get("data_semantics", "intraday_snapshot"),
            "source": snapshot.get("source"),
            "snapshot": snapshot,
        }
    return {
        "status": "stock_intraday_snapshot_unavailable",
        "code": str(code).strip(),
        "error": "code not found in realtime snapshot",
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe today's data sources")
    parser.add_argument("--expected-date", default=datetime.now().strftime("%Y%m%d"), help="YYYYMMDD or YYYY-MM-DD")
    parser.add_argument("--code", default="", help="Optional 6-digit stock code to fetch from realtime snapshot")
    parser.add_argument("--json", action="store_true", help="Print JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = build_stock_snapshot_result(args.code) if args.code else build_probe_result(args.expected_date)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Status: {result['status']}")
        if args.code:
            print(f"Code: {result.get('code')}")
            print(f"Source: {result.get('source')}")
            print(f"Data semantics: {result.get('data_semantics')}")
            print(f"Snapshot: {result.get('snapshot')}")
        else:
            print(f"Expected date: {result['expected_date']}")
            print(f"StockDB latest daily date: {result.get('stockdb_latest_daily_date')}")
            print(f"Recommended source: {result.get('recommended_source')}")
            print(f"Data semantics: {result.get('data_semantics')}")
            if result.get("realtime_row_count") is not None:
                print(f"Realtime rows: {result['realtime_row_count']}")
    return 0 if result["status"] != "today_data_unavailable" else 1


if __name__ == "__main__":
    sys.exit(main())
