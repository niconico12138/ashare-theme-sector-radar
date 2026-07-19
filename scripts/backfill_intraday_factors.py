#!/usr/bin/env python3
"""Backfill shadow-only intraday factors for historical candidates."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.backfill_stock_analysis_fields import backfill_stock_analysis_fields  # noqa: E402
from theme_sector_radar.data.market_data_http_client import MarketDataHttpClient  # noqa: E402
from theme_sector_radar.factors.calculators import calculate_intraday_factors  # noqa: E402
from theme_sector_radar.reporting.artifact_archive import write_text_preserving_previous  # noqa: E402
from theme_sector_radar.reporting.strict_json import load_strict_json  # noqa: E402


DEFAULT_CANDIDATE_ROOT = PROJECT_ROOT / "reports" / "agent_bridge"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "reports" / "agent_bridge_intraday_backfilled"
DEFAULT_REPORT_ROOT = PROJECT_ROOT / "reports" / "intraday_factor_backfill"


def _candidate_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("candidates"), list):
        return data["candidates"]
    if isinstance(data, list):
        return data
    return []


def _read_json(path: Path) -> Any:
    return load_strict_json(path)


def _write_json(path: Path, data: Any) -> Path | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    return write_text_preserving_previous(
        path,
        json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False),
    )


def _load_candidate_file(candidate_root: Path, date: str) -> tuple[Path | None, Any | None]:
    date_dir = candidate_root / date
    for name in (
        "top30_candidates.intraday_backfilled.json",
        "top30_candidates.analysis_backfilled.json",
        "top30_candidates.factor_backfilled.json",
        "top30_candidates.json",
    ):
        path = date_dir / name
        if path.exists():
            return path, _read_json(path)
    return None, None


def _date_range(start: str, end: str) -> list[str]:
    current = datetime.strptime(start, "%Y-%m-%d")
    stop = datetime.strptime(end, "%Y-%m-%d")
    dates = []
    while current <= stop:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates


def _normalize_datetime(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace("-", "").replace(":", "").replace(" ", "")
    if text.endswith(".0"):
        text = text[:-2]
    return text


def _safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def normalize_intraday_bars(raw_bars: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    bars = []
    for item in raw_bars or []:
        if not isinstance(item, dict):
            continue
        date = _normalize_datetime(item.get("date") or item.get("time") or item.get("datetime"))
        close = _safe_float(item.get("close") if item.get("close") is not None else item.get("price"))
        if not date or close is None:
            continue
        amount = _safe_float(item.get("amount"))
        volume = _safe_float(item.get("volume"))
        bars.append(
            {
                "date": date,
                "time": date,
                "price": close,
                "close": close,
                "open": _safe_float(item.get("open")) or close,
                "high": _safe_float(item.get("high")) or close,
                "low": _safe_float(item.get("low")) or close,
                "amount": amount if amount is not None else 0.0,
                "volume": volume if volume is not None else 0.0,
            }
        )
    return sorted(bars, key=lambda bar: bar["date"])


def _should_fetch(candidate: dict[str, Any], opportunity_type: str) -> bool:
    if opportunity_type == "all":
        return True
    return candidate.get("opportunity_type") == opportunity_type or (
        opportunity_type == "short_burst" and candidate.get("source_pool") == "burst_top"
    )


def backfill_intraday_candidates(
    data: Any,
    date: str,
    *,
    client: Any,
    frequency: str = "5m",
    opportunity_type: str = "short_burst",
    store_bars: bool = False,
) -> dict[str, Any]:
    result_data = deepcopy(data)
    candidates = _candidate_rows(result_data)
    day = date.replace("-", "")
    start = f"{day}093000"
    end = f"{day}150000"
    requested = 0
    matched = 0
    missing = 0
    errors: list[dict[str, str]] = []

    for candidate in candidates:
        candidate.pop("intraday_bars", None)
        if not _should_fetch(candidate, opportunity_type):
            continue
        code = str(candidate.get("code", "")).strip()
        if not code:
            continue
        requested += 1
        try:
            raw_bars = client.get_stock_bars(code, start, end, frequency=frequency, fq=None)
            bars = normalize_intraday_bars(raw_bars)
        except Exception as exc:
            bars = []
            errors.append({"code": code, "error": str(exc)[:160]})
        if bars:
            matched += 1
            candidate["intraday_bars"] = bars
        else:
            missing += 1

    enriched = backfill_stock_analysis_fields(result_data)
    for candidate in _candidate_rows(enriched):
        candidate.update(calculate_intraday_factors(candidate))
        if not store_bars:
            candidate.pop("intraday_bars", None)

    return {
        "data": enriched,
        "summary": {
            "date": date,
            "frequency": frequency,
            "opportunity_type": opportunity_type,
            "requested_count": requested,
            "matched_count": matched,
            "missing_count": missing,
            "error_count": len(errors),
            "errors": errors[:20],
        },
    }


def backfill_date(
    date: str,
    *,
    candidate_root: Path = DEFAULT_CANDIDATE_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    client: Any | None = None,
    frequency: str = "5m",
    opportunity_type: str = "short_burst",
    store_bars: bool = False,
    write: bool = True,
) -> dict[str, Any]:
    if candidate_root.resolve() == output_root.resolve():
        raise ValueError("candidate and output roots must differ to prevent in-place source mutation")
    path, data = _load_candidate_file(candidate_root, date)
    if data is None:
        return {"date": date, "status": "missing_candidate_file", "candidate_count": 0}
    client = client or MarketDataHttpClient(timeout=30, retries=1)
    result = backfill_intraday_candidates(
        data,
        date,
        client=client,
        frequency=frequency,
        opportunity_type=opportunity_type,
        store_bars=store_bars,
    )
    candidates = _candidate_rows(result["data"])
    output_path = output_root / date / "top30_candidates.intraday_backfilled.json"
    if path is not None and path.resolve() == output_path.resolve():
        raise ValueError(f"candidate source and output file must differ: {path}")
    archived_previous_path = None
    if write:
        archived_previous_path = _write_json(output_path, result["data"])
    return {
        "date": date,
        "status": "processed",
        "source_path": str(path),
        "output_path": str(output_path),
        "archived_previous_path": str(archived_previous_path) if archived_previous_path else None,
        "candidate_count": len(candidates),
        **result["summary"],
    }


def generate_report(start: str, end: str, daily_results: list[dict[str, Any]]) -> dict[str, Any]:
    processed = [item for item in daily_results if item.get("status") == "processed"]
    return {
        "schema_version": "intraday_factor_backfill.v1",
        "start": start,
        "end": end,
        "processed_days": len(processed),
        "requested_count": sum(item.get("requested_count", 0) for item in processed),
        "matched_count": sum(item.get("matched_count", 0) for item in processed),
        "missing_count": sum(item.get("missing_count", 0) for item in processed),
        "error_count": sum(item.get("error_count", 0) for item in processed),
        "daily_results": daily_results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill shadow-only intraday factors")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--candidate-root", default=str(DEFAULT_CANDIDATE_ROOT))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--report-root", default=str(DEFAULT_REPORT_ROOT))
    parser.add_argument("--frequency", default="5m", choices=["1m", "5m", "15m", "30m", "60m"])
    parser.add_argument("--opportunity-type", default="short_burst", choices=["short_burst", "all"])
    parser.add_argument("--store-bars", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    client = MarketDataHttpClient(timeout=30, retries=1)
    daily_results = []
    print("  Backfilling intraday shadow factors...")
    print(f"  Period: {args.start} ~ {args.end}")
    print(f"  Frequency: {args.frequency}")
    for date in _date_range(args.start, args.end):
        item = backfill_date(
            date,
            candidate_root=Path(args.candidate_root),
            output_root=Path(args.output_root),
            client=client,
            frequency=args.frequency,
            opportunity_type=args.opportunity_type,
            store_bars=args.store_bars,
            write=not args.dry_run,
        )
        daily_results.append(item)
        if item.get("status") == "processed":
            print(
                f"  {date}: requested={item.get('requested_count', 0)} "
                f"matched={item.get('matched_count', 0)} missing={item.get('missing_count', 0)}"
            )
        else:
            print(f"  {date}: {item.get('status')}")

    report = generate_report(args.start, args.end, daily_results)
    report_root = Path(args.report_root)
    report_root.mkdir(parents=True, exist_ok=True)
    json_path = report_root / f"intraday_factor_backfill_{args.start}_{args.end}_{args.frequency}.json"
    _write_json(json_path, report)
    print("  Backfill complete")
    print(f"  Matched: {report['matched_count']}/{report['requested_count']}")
    print(f"  Report: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
