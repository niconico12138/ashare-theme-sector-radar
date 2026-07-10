#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史数据源探针

检查 stockdb-sdk / market_data_service 的可用性、延迟、样本数据覆盖。

用法:
  python scripts/probe_historical_data_sources.py \
    --start-date 2026-01-01 --end-date 2026-07-09 \
    --sample-codes 000001 600519 000700 603355 \
    --output-dir reports/data_source_health
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _check_port(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def _probe_stockdb(sample_codes: list[str], start_date: str, end_date: str) -> dict:
    result = {
        "reachable": False,
        "latest_daily_date": None,
        "sample_bars": {},
        "errors": [],
    }
    try:
        from theme_sector_radar.data.stockdb_sdk_client import StockDBSdkClient
        t0 = time.time()
        client = StockDBSdkClient()
        probe = client.probe_freshness(codes=sample_codes)
        latency = round(time.time() - t0, 3)
        result["reachable"] = probe.get("ok", False)
        result["latest_daily_date"] = probe.get("latest_daily_date")
        result["latency_s"] = latency
        result["probe_detail"] = probe

        start_compact = start_date.replace("-", "")
        end_compact = end_date.replace("-", "")
        for code in sample_codes:
            try:
                bars = client.get_stock_bars(code, start=start_compact, end=end_compact,
                                             fields=("date", "close"), limit=5, desc=True)
                result["sample_bars"][code] = {"count": len(bars), "latest": bars[0]["date"] if bars else None}
            except Exception as e:
                result["sample_bars"][code] = {"count": 0, "error": str(e)}
    except Exception as e:
        result["errors"].append(f"StockDB SDK init failed: {e}")
    return result


def _probe_http_market_data() -> dict:
    result = {"reachable": False, "errors": []}
    try:
        import requests
        t0 = time.time()
        resp = requests.get("http://127.0.0.1:8000/health", timeout=5)
        latency = round(time.time() - t0, 3)
        result["reachable"] = resp.status_code == 200
        result["latency_s"] = latency
        if resp.status_code == 200:
            result["health"] = resp.json()
    except Exception as e:
        result["errors"].append(str(e))
    return result


def _scan_stockdb_trading_days(sample_code: str, start_date: str, end_date: str) -> list[str]:
    """Get actual trading days from stockdb for a liquid stock."""
    try:
        from theme_sector_radar.data.stockdb_sdk_client import StockDBSdkClient
        client = StockDBSdkClient()
        bars = client.get_stock_bars(sample_code, start=start_date.replace("-", ""),
                                     end=end_date.replace("-", ""), fields=("date",))
        return sorted(set(b["date"] for b in bars), reverse=False)
    except Exception:
        return []


def generate_markdown(report: dict) -> str:
    lines = []
    lines.append("# Historical Data Source Probe Report")
    lines.append("")
    lines.append(f"**Generated**: {report.get('generated_at', '')}")
    lines.append(f"**Range**: {report.get('start_date')} to {report.get('end_date')}")
    lines.append("")

    sdk = report.get("stockdb_sdk", {})
    lines.append("## StockDB SDK")
    lines.append("")
    lines.append(f"- Reachable: {'YES' if sdk.get('reachable') else 'NO'}")
    lines.append(f"- Latest daily date: {sdk.get('latest_daily_date', 'N/A')}")
    lines.append(f"- Latency: {sdk.get('latency_s', 'N/A')}s")
    lines.append("")
    if sdk.get("sample_bars"):
        lines.append("### Sample Bars")
        lines.append("")
        for code, info in sdk["sample_bars"].items():
            lines.append(f"- {code}: count={info.get('count', 0)}, latest={info.get('latest', 'N/A')}")
        lines.append("")

    http = report.get("market_data_service", {})
    lines.append("## Market Data HTTP Service")
    lines.append("")
    lines.append(f"- Reachable: {'YES' if http.get('reachable') else 'NO'}")
    if http.get("errors"):
        lines.append(f"- Errors: {http['errors'][0][:100]}")
    lines.append("")

    td = report.get("trading_days", {})
    lines.append("## Trading Days")
    lines.append("")
    lines.append(f"- Trading days found: {td.get('count', 0)}")
    lines.append(f"- Sample code: {td.get('sample_code', 'N/A')}")
    if td.get("first") and td.get("last"):
        lines.append(f"- Range: {td['first']} to {td['last']}")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Probe historical data sources")
    parser.add_argument("--start-date", default="2026-01-01")
    parser.add_argument("--end-date", default="2026-07-09")
    parser.add_argument("--sample-codes", nargs="+", default=["000001", "600519", "000700", "603355"])
    parser.add_argument("--output-dir", default="reports/data_source_health")
    args = parser.parse_args()

    print(f"Probing data sources {args.start_date} to {args.end_date}...")

    report = {
        "generated_at": datetime.now().isoformat(),
        "start_date": args.start_date,
        "end_date": args.end_date,
        "stockdb_sdk": _probe_stockdb(args.sample_codes, args.start_date, args.end_date),
        "market_data_service": _probe_http_market_data(),
    }

    # Trading days scan
    sample_code = args.sample_codes[0]
    trading_days = _scan_stockdb_trading_days(sample_code, args.start_date, args.end_date)
    report["trading_days"] = {
        "sample_code": sample_code,
        "count": len(trading_days),
        "first": trading_days[0] if trading_days else None,
        "last": trading_days[-1] if trading_days else None,
        "dates": trading_days,
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "historical_data_sources.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path = out_dir / "historical_data_sources.md"
    md_path.write_text(generate_markdown(report), encoding="utf-8")

    print(f"\nResults:")
    print(f"  stockdb-sdk: {'OK' if report['stockdb_sdk']['reachable'] else 'FAIL'}, latest={report['stockdb_sdk'].get('latest_daily_date')}")
    print(f"  market_data_service: {'OK' if report['market_data_service']['reachable'] else 'FAIL'}")
    print(f"  trading days: {report['trading_days']['count']}")
    print(f"  JSON: {json_path}")
    print(f"  MD: {md_path}")


if __name__ == "__main__":
    main()
