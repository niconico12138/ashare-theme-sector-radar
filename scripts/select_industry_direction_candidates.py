#!/usr/bin/env python
"""Select paper-only industry candidates from a direction shadow report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.reporting.strict_json import (  # noqa: E402
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)
from theme_sector_radar.scoring.industry_direction_candidates import (  # noqa: E402
    select_industry_direction_candidates,
)


def _extract_latest_daily_report(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise ValueError("direction report must be an object")
    if isinstance(document.get("sectors"), list):
        return document
    daily_results = document.get("daily_results")
    if isinstance(daily_results, list) and daily_results:
        latest = daily_results[-1]
        if isinstance(latest, dict) and isinstance(latest.get("sectors"), list):
            return latest
    raise ValueError("direction report does not contain daily sector rows")


def build_candidate_report(
    source_document: Any,
    *,
    source_path: Path,
    source_sha256: str,
    candidate_top_n: int = 7,
    core_top_n: int = 5,
    observation_top_n: int = 10,
    minimum_direction_score: float = 50.0,
    minimum_time_series_score: float = 40.0,
) -> dict[str, Any]:
    daily = _extract_latest_daily_report(source_document)
    selection = select_industry_direction_candidates(
        daily["sectors"],
        candidate_top_n=candidate_top_n,
        core_top_n=core_top_n,
        observation_top_n=observation_top_n,
        minimum_direction_score=minimum_direction_score,
        minimum_time_series_score=minimum_time_series_score,
    )
    return {
        **selection,
        "as_of_date": daily.get("as_of_date"),
        "source": {
            "path": str(source_path.resolve()),
            "sha256": source_sha256,
            "schema_version": source_document.get("schema_version"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate-top-n", type=int, default=7)
    parser.add_argument("--core-top-n", type=int, default=5)
    parser.add_argument("--observation-top-n", type=int, default=10)
    parser.add_argument("--minimum-direction-score", type=float, default=50.0)
    parser.add_argument("--minimum-time-series-score", type=float, default=40.0)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(f"output already exists: {args.output}")
    source, source_sha256 = load_strict_json_with_sha256(args.input)
    report = build_candidate_report(
        source,
        source_path=args.input,
        source_sha256=source_sha256,
        candidate_top_n=args.candidate_top_n,
        core_top_n=args.core_top_n,
        observation_top_n=args.observation_top_n,
        minimum_direction_score=args.minimum_direction_score,
        minimum_time_series_score=args.minimum_time_series_score,
    )
    write_strict_json_atomic(args.output, report)
    print(
        f"selected {report['selection_counts']} for {report.get('as_of_date')} "
        f"into {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
