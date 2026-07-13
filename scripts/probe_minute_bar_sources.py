#!/usr/bin/env python3
"""Probe historical 1m/5m minute bars for paper-only intraday research."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class EastmoneyMinuteBarsClient:
    """Small Eastmoney minute-bar client compatible with backfill_intraday_factors."""

    def __init__(self, timeout: int = 20, retries: int = 2):
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        self.session.trust_env = False

    def get_stock_bars(
        self,
        code: str,
        start: str,
        end: str,
        frequency: str = "5m",
        fq: str | None = None,
    ) -> list[dict[str, Any]]:
        period = _frequency_to_period(frequency)
        secid = _secid(code)
        if period == "1":
            rows = self._fetch_1m(secid)
        else:
            rows = self._fetch_kline(secid, period, fq)
        start_key = _normalize_datetime(start)
        end_key = _normalize_datetime(end)
        return [row for row in rows if start_key <= row["date"] <= end_key]

    def _fetch_1m(self, secid: str) -> list[dict[str, Any]]:
        url = "https://push2his.eastmoney.com/api/qt/stock/trends2/get"
        params = {
            "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "ndays": "5",
            "iscr": "0",
            "secid": secid,
        }
        data = self._get_json(url, params)
        raw_rows = ((data.get("data") or {}).get("trends") or [])
        return [_parse_1m_row(item) for item in raw_rows]

    def _fetch_kline(self, secid: str, period: str, fq: str | None) -> list[dict[str, Any]]:
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        adjust_map = {None: "0", "": "0", "qfq": "1", "hfq": "2"}
        params = {
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "klt": period,
            "fqt": adjust_map.get(fq, "0"),
            "secid": secid,
            "beg": "0",
            "end": "20500000",
        }
        data = self._get_json(url, params)
        raw_rows = ((data.get("data") or {}).get("klines") or [])
        return [_parse_kline_row(item) for item in raw_rows]

    def _get_json(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(max(1, self.retries + 1)):
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(0.3 * (attempt + 1))
        raise last_error if last_error else RuntimeError("Eastmoney request failed")


def probe_minute_bars(
    *,
    codes: list[str],
    dates: list[str],
    frequencies: list[str],
    output_dir: Path,
    timeout: int = 20,
) -> dict[str, Any]:
    client = EastmoneyMinuteBarsClient(timeout=timeout)
    rows = []
    for code in codes:
        for date in dates:
            day = date.replace("-", "")
            for frequency in frequencies:
                started = time.time()
                try:
                    bars = client.get_stock_bars(code, f"{day}093000", f"{day}150000", frequency=frequency, fq=None)
                    status = "ok" if bars else "empty"
                    error = None
                except Exception as exc:
                    bars = []
                    status = "error"
                    error = f"{type(exc).__name__}: {str(exc)[:180]}"
                rows.append(
                    {
                        "code": code,
                        "date": date,
                        "frequency": frequency,
                        "status": status,
                        "bar_count": len(bars),
                        "first_time": bars[0]["date"] if bars else None,
                        "last_time": bars[-1]["date"] if bars else None,
                        "latency_s": round(time.time() - started, 3),
                        "error": error,
                    }
                )
    report = {
        "schema_version": "minute_bar_source_probe.v1",
        "generated_at": datetime.now().isoformat(),
        "source": "eastmoney_direct",
        "paper_trading_only": True,
        "no_execution_signals": True,
        "summary": _summary(rows),
        "results": rows,
        "notes": [
            "Eastmoney 1m endpoint is limited to the most recent five trading days.",
            "Eastmoney 5m endpoint currently exposes a rolling intraday history window.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "minute_bar_source_probe.json"
    md_path = output_dir / "minute_bar_source_probe.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_markdown(report), encoding="utf-8")
    return {"status": "ok", "json_path": json_path, "markdown_path": md_path, "report": report}


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_frequency: dict[str, dict[str, int]] = {}
    for row in rows:
        item = by_frequency.setdefault(row["frequency"], {"ok": 0, "empty": 0, "error": 0, "bars": 0})
        item[row["status"]] += 1
        item["bars"] += int(row["bar_count"])
    return {
        "probe_count": len(rows),
        "ok_count": sum(1 for row in rows if row["status"] == "ok"),
        "empty_count": sum(1 for row in rows if row["status"] == "empty"),
        "error_count": sum(1 for row in rows if row["status"] == "error"),
        "by_frequency": by_frequency,
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Minute Bar Source Probe",
        "",
        f"Generated: `{report.get('generated_at')}`",
        "",
        "- Source: `eastmoney_direct`",
        "- Paper-only: `True`",
        "- No execution signals: `True`",
        "",
        "## Summary",
        "",
        f"- Probe count: `{report['summary']['probe_count']}`",
        f"- OK: `{report['summary']['ok_count']}`",
        f"- Empty: `{report['summary']['empty_count']}`",
        f"- Error: `{report['summary']['error_count']}`",
        "",
        "## Results",
        "",
        "| Code | Date | Frequency | Status | Bars | First | Last | Error |",
        "|---|---|---|---|---:|---|---|---|",
    ]
    for row in report.get("results") or []:
        lines.append(
            f"| `{row['code']}` | `{row['date']}` | `{row['frequency']}` | `{row['status']}` | "
            f"{row['bar_count']} | {row.get('first_time') or ''} | {row.get('last_time') or ''} | "
            f"{row.get('error') or ''} |"
        )
    lines.extend(["", "## Notes", ""])
    for note in report.get("notes") or []:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def _secid(code: str) -> str:
    text = str(code).strip()
    market = "1" if text.startswith("6") else "0"
    return f"{market}.{text}"


def _frequency_to_period(frequency: str) -> str:
    mapping = {"1m": "1", "5m": "5", "15m": "15", "30m": "30", "60m": "60"}
    if frequency not in mapping:
        raise ValueError(f"Unsupported frequency: {frequency}")
    return mapping[frequency]


def _normalize_datetime(value: Any) -> str:
    text = str(value).strip().replace("-", "").replace(":", "").replace(" ", "")
    if text.endswith(".0"):
        text = text[:-2]
    if len(text) == 12 and text.isdigit():
        return f"{text}00"
    return text


def _parse_1m_row(raw: str) -> dict[str, Any]:
    parts = raw.split(",")
    return {
        "date": _normalize_datetime(parts[0]),
        "time": _normalize_datetime(parts[0]),
        "open": _float(parts[1]),
        "close": _float(parts[2]),
        "high": _float(parts[3]),
        "low": _float(parts[4]),
        "volume": _float(parts[5]),
        "amount": _float(parts[6]),
        "avg_price": _float(parts[7]) if len(parts) > 7 else None,
    }


def _parse_kline_row(raw: str) -> dict[str, Any]:
    parts = raw.split(",")
    return {
        "date": _normalize_datetime(parts[0]),
        "time": _normalize_datetime(parts[0]),
        "open": _float(parts[1]),
        "close": _float(parts[2]),
        "high": _float(parts[3]),
        "low": _float(parts[4]),
        "volume": _float(parts[5]),
        "amount": _float(parts[6]),
    }


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe Eastmoney historical minute bars")
    parser.add_argument("--codes", nargs="+", required=True)
    parser.add_argument("--dates", nargs="+", required=True)
    parser.add_argument("--frequencies", nargs="+", default=["5m", "1m"], choices=["1m", "5m", "15m", "30m", "60m"])
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args(argv)
    result = probe_minute_bars(
        codes=args.codes,
        dates=args.dates,
        frequencies=args.frequencies,
        output_dir=Path(args.output_dir),
        timeout=args.timeout,
    )
    print(result["json_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
