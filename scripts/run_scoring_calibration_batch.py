#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch build forward returns and aggregate scoring calibration.

Use this after several dated candidate pools exist. It fills missing
``reports/forward_returns/DATE/forward_returns.json`` files, then writes one
aggregate calibration report for the selected dates.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_CANDIDATE_ROOT = PROJECT_ROOT / "reports" / "agent_bridge"
DEFAULT_RETURNS_ROOT = PROJECT_ROOT / "reports" / "forward_returns"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "scoring_calibration"
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

from scripts.aggregate_scoring_calibration import (  # noqa: E402
    _date_output_name,
    aggregate_scoring_calibration,
    generate_markdown_report,
)
from scripts.build_forward_returns import (  # noqa: E402
    build_forward_returns,
    load_candidate_codes,
    make_bars_client,
)
from theme_sector_radar.data.trading_calendar import load_trading_calendar  # noqa: E402


def discover_candidate_dates(candidate_root: Path = DEFAULT_CANDIDATE_ROOT) -> list[str]:
    if not candidate_root.exists():
        return []
    dates = []
    for child in candidate_root.iterdir():
        if child.is_dir() and DATE_PATTERN.match(child.name) and (child / "top30_candidates.json").exists():
            dates.append(child.name)
    return sorted(dates)


def _parse_horizons(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip().rstrip("d")) for part in value.split(",") if part.strip())


def _horizon_labels(horizons: tuple[int, ...]) -> tuple[str, ...]:
    return tuple(f"{horizon}d" for horizon in horizons)


def _load_bars_data_source(returns_path: Path) -> dict | None:
    if not returns_path.exists():
        return None
    try:
        data = json.loads(returns_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None
    source = data.get("bars_data_source")
    return source if isinstance(source, dict) else None


def _add_bars_data_source(summary: dict, date: str, source: dict | None) -> None:
    if not source:
        return
    cleaned = {key: value for key, value in source.items() if value is not None}
    if not cleaned:
        return
    summary["dates"][date] = cleaned
    source_name = str(cleaned.get("source") or "unknown")
    reason = str(cleaned.get("reason") or "unknown")
    summary["by_source"][source_name] = summary["by_source"].get(source_name, 0) + 1
    summary["by_reason"][reason] = summary["by_reason"].get(reason, 0) + 1


def _format_count_summary(values: dict) -> str:
    if not values:
        return "none"
    return ", ".join(f"{key}={values[key]}" for key in sorted(values))


def run_scoring_calibration_batch(
    dates: list[str] | None = None,
    candidate_root: Path = DEFAULT_CANDIDATE_ROOT,
    returns_root: Path = DEFAULT_RETURNS_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    horizons: tuple[int, ...] = (1, 3, 5),
    lookahead_days: int = 14,
    force: bool = False,
    source: str = "http",
    client=None,
    trading_calendar: Mapping[str, Any] | None = None,
) -> dict:
    dates = sorted(dates or discover_candidate_dates(candidate_root))
    date_results: dict[str, dict] = {}
    generated = 0
    skipped_existing = 0
    missing_candidate = 0
    bars_data_source_summary = {"by_source": {}, "by_reason": {}, "dates": {}}

    for date in dates:
        candidate_path = candidate_root / date / "top30_candidates.json"
        returns_path = returns_root / date / "forward_returns.json"
        if not candidate_path.exists():
            missing_candidate += 1
            date_results[date] = {"status": "missing_candidate_file"}
            continue

        if returns_path.exists() and not force:
            skipped_existing += 1
            bars_data_source = _load_bars_data_source(returns_path)
            _add_bars_data_source(bars_data_source_summary, date, bars_data_source)
            date_results[date] = {
                "status": "skipped_existing",
                "path": str(returns_path),
                "bars_data_source": bars_data_source,
            }
            continue

        codes = load_candidate_codes(candidate_path)
        bars_client = client or make_bars_client(source, expected_min_date=date)
        result = build_forward_returns(
            codes,
            date,
            client=bars_client,
            horizons=horizons,
            lookahead_days=lookahead_days,
            trading_calendar=trading_calendar,
        )
        returns_path.parent.mkdir(parents=True, exist_ok=True)
        returns_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        generated += 1
        date_results[date] = {
            "status": "generated",
            "path": str(returns_path),
            "coverage": result.get("coverage", {}),
            "bars_data_source": result.get("bars_data_source"),
        }
        _add_bars_data_source(bars_data_source_summary, date, result.get("bars_data_source"))

    aggregate = aggregate_scoring_calibration(
        dates,
        candidate_root=candidate_root,
        returns_root=returns_root,
        horizons=_horizon_labels(horizons),
    )
    aggregate_name = _date_output_name(dates)
    aggregate_dir = output_dir / "aggregate" / aggregate_name
    aggregate_dir.mkdir(parents=True, exist_ok=True)
    aggregate_json = aggregate_dir / "aggregate_scoring_calibration.json"
    aggregate_md = aggregate_dir / "aggregate_scoring_calibration.md"
    aggregate_json.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8")
    aggregate_md.write_text(generate_markdown_report(aggregate), encoding="utf-8")

    summary = {
        "schema_version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "dates": dates,
        "horizons": _horizon_labels(horizons),
        "summary": {
            "date_count": len(dates),
            "generated_forward_returns": generated,
            "skipped_existing_forward_returns": skipped_existing,
            "missing_candidate_files": missing_candidate,
        },
        "date_results": date_results,
        "bars_data_source_summary": bars_data_source_summary,
        "aggregate_paths": {
            "json": str(aggregate_json),
            "markdown": str(aggregate_md),
        },
        "aggregate": aggregate,
    }
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch build forward returns and aggregate scoring calibration")
    parser.add_argument("--dates", default="", help="Comma-separated dates. Omit to scan candidate root.")
    parser.add_argument("--candidate-root", default=str(DEFAULT_CANDIDATE_ROOT), help="Directory containing DATE/top30_candidates.json")
    parser.add_argument("--returns-root", default=str(DEFAULT_RETURNS_ROOT), help="Directory for DATE/forward_returns.json")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Base scoring calibration output directory")
    parser.add_argument("--horizons", default="1,3,5", help="Comma-separated future trading-day horizons")
    parser.add_argument("--lookahead-days", type=int, default=14, help="Natural-day buffer used when fetching bars")
    parser.add_argument("--source", choices=["http", "stockdb-sdk", "auto"], default="http", help="Bar data source")
    parser.add_argument("--force", action="store_true", help="Regenerate existing forward_returns.json files")
    parser.add_argument("--trading-calendar-path", required=True, type=Path)
    parser.add_argument("--expected-calendar-sha256", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, client=None) -> int:
    args = parse_args(argv)
    dates = [date.strip() for date in args.dates.split(",") if date.strip()] if args.dates else None
    effective_dates = dates or discover_candidate_dates(Path(args.candidate_root))
    trading_calendar = (
        load_trading_calendar(
            args.trading_calendar_path,
            as_of=max(effective_dates),
            include_future=True,
        )
        if effective_dates
        else None
    )
    if (
        trading_calendar is not None
        and trading_calendar["sha256"] != args.expected_calendar_sha256.lower()
    ):
        raise ValueError("trading calendar SHA mismatch")
    result = run_scoring_calibration_batch(
        dates,
        candidate_root=Path(args.candidate_root),
        returns_root=Path(args.returns_root),
        output_dir=Path(args.output_dir),
        horizons=_parse_horizons(args.horizons),
        lookahead_days=args.lookahead_days,
        force=args.force,
        source=args.source,
        client=client,
        trading_calendar=trading_calendar,
    )

    output_name = _date_output_name(result["dates"])
    summary_dir = Path(args.output_dir) / "batch" / output_name
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / "batch_scoring_calibration_summary.json"
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    aggregate_coverage = result.get("aggregate", {}).get("coverage", {})
    print(f"Summary: {summary_path}")
    print(f"Aggregate JSON: {result['aggregate_paths']['json']}")
    print(
        "Aggregate coverage: "
        f"{aggregate_coverage.get('forward_return_count', 0)}/"
        f"{aggregate_coverage.get('candidate_count', 0)} "
        f"({aggregate_coverage.get('coverage_ratio', 0):.1%})"
    )
    print(
        "Forward returns: "
        f"generated={result['summary']['generated_forward_returns']}, "
        f"skipped={result['summary']['skipped_existing_forward_returns']}"
    )
    bars_source_summary = result.get("bars_data_source_summary", {})
    print(f"Bars source summary: {_format_count_summary(bars_source_summary.get('by_source', {}))}")
    print(f"Bars source reasons: {_format_count_summary(bars_source_summary.get('by_reason', {}))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
