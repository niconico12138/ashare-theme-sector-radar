#!/usr/bin/env python3
"""Build a reproducible A-share exchange calendar artifact."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.data.trading_calendar import build_trading_calendar_report  # noqa: E402
from theme_sector_radar.reporting.artifact_archive import write_text_preserving_previous  # noqa: E402


def _trade_date_literal(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def build_a_share_trading_calendar(
    *,
    output_path: Path,
    start: str,
    end: str,
    trade_dates: Iterable[Any] | None = None,
) -> dict[str, Any]:
    if trade_dates is None:
        import akshare as ak

        frame = ak.tool_trade_date_hist_sina()
        trade_dates = frame["trade_date"].tolist()
    report = build_trading_calendar_report(
        [_trade_date_literal(value) for value in trade_dates],
        source="akshare.tool_trade_date_hist_sina",
        requested_start=start,
        requested_end=end,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    archived = write_text_preserving_previous(
        output_path,
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),
    )
    return {
        "status": "ok",
        "output_path": output_path,
        "archived_previous_path": archived,
        "report": report,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an A-share trading calendar artifact")
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args(argv)
    result = build_a_share_trading_calendar(
        output_path=Path(args.output_path),
        start=args.start,
        end=args.end,
    )
    print(result["output_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
