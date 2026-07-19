#!/usr/bin/env python3
"""Build a paper-only stop-loss event dataset from local minute ZIP archives."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.data.local_minute_archive import scan_stock_daily_paths_batch
from theme_sector_radar.reporting.artifact_archive import write_text_preserving_previous
from theme_sector_radar.reporting.strict_json import load_strict_json
from theme_sector_radar.timing.stop_loss_research import build_metric_negative_sample


def run_local_stop_loss_sample(
    *,
    stock_archives: list[Path],
    codes: list[str],
    output_dir: Path,
    as_of: str,
) -> dict[str, Any]:
    normalized_as_of = date.fromisoformat(as_of).isoformat()
    if normalized_as_of != as_of:
        raise ValueError("as_of must be a zero-padded ISO date")
    rows = []
    year_counts = {}
    for archive_path in stock_archives:
        batch = scan_stock_daily_paths_batch(archive_path, codes)
        year_rows = [
            row
            for code_rows in batch.values()
            for row in code_rows
            if _row_date(row) <= normalized_as_of
        ]
        rows.extend(year_rows)
        year_counts[archive_path.stem[:4]] = len(year_rows)
    report = build_metric_negative_sample(rows)
    report.update({"as_of": as_of, "stock_archives": [str(path) for path in stock_archives], "year_record_counts": year_counts})
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"local_stop_loss_negative_sample_{as_of}.json"
    markdown_path = output_dir / f"local_stop_loss_negative_sample_{as_of}.md"
    archived_json_path = write_text_preserving_previous(
        json_path,
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),
    )
    archived_markdown_path = write_text_preserving_previous(markdown_path, _markdown(report))
    return {
        "status": "ok",
        "json_path": json_path,
        "markdown_path": markdown_path,
        "archived_previous_paths": [path for path in (archived_json_path, archived_markdown_path) if path],
        "report": report,
    }


def _row_date(row: dict[str, Any]) -> str:
    value = str(row.get("date") or "")
    normalized = date.fromisoformat(value).isoformat()
    if normalized != value:
        raise ValueError(f"local stop-loss row date is not canonical ISO: {value}")
    return normalized


def _markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    return (
        "# Local Stop-Loss Negative Sample\n\n"
        f"As of: `{report.get('as_of')}`\n\n"
        "- Paper-only: `True`\n"
        "- No execution signals: `True`\n\n"
        f"- Records: `{summary['record_count']}`\n"
        f"- Negative events: `{summary['negative_event_count']}`\n"
        f"- Matched controls: `{summary['matched_control_count']}`\n"
        f"- Year records: `{report.get('year_record_counts')}`\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build local paper-only stop-loss samples")
    parser.add_argument("--stock-archive", action="append", required=True)
    parser.add_argument("--codes-json", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args(argv)
    codes_data = load_strict_json(args.codes_json)
    codes = codes_data.get("codes") if isinstance(codes_data, dict) else codes_data
    result = run_local_stop_loss_sample(
        stock_archives=[Path(path) for path in args.stock_archive],
        codes=[str(code) for code in codes or []],
        output_dir=Path(args.output_dir),
        as_of=args.as_of,
    )
    print(result["json_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
