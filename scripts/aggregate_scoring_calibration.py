#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aggregate scoring calibration across multiple signal dates.

The script keeps every date/code pair as a separate sample so repeated stocks
on different days do not overwrite each other.
"""

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

DEFAULT_CANDIDATE_ROOT = PROJECT_ROOT / "reports" / "agent_bridge"
DEFAULT_RETURNS_ROOT = PROJECT_ROOT / "reports" / "forward_returns"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "scoring_calibration"

from scripts.evaluate_scoring_calibration import (  # noqa: E402
    BUCKET_ORDER,
    evaluate_score_layers,
    generate_markdown_report as generate_layer_markdown,
    load_candidates,
    load_forward_returns,
)


def _has_any_return(item: dict, horizons: tuple[str, ...]) -> bool:
    return any(item.get(horizon) is not None for horizon in horizons)


def _date_output_name(dates: list[str]) -> str:
    if not dates:
        return "empty"
    if len(dates) == 1:
        return dates[0]
    return f"{dates[0]}_to_{dates[-1]}"


def build_aggregate_samples(
    dates: list[str],
    candidate_root: Path = DEFAULT_CANDIDATE_ROOT,
    returns_root: Path = DEFAULT_RETURNS_ROOT,
    horizons: tuple[str, ...] = ("1d", "3d", "5d"),
) -> tuple[list[dict], dict, dict]:
    samples: list[dict] = []
    aggregate_returns: dict[str, dict] = {}
    date_summary: dict[str, dict] = {}

    for date in dates:
        candidate_path = candidate_root / date / "top30_candidates.json"
        returns_path = returns_root / date / "forward_returns.json"

        if not candidate_path.exists():
            date_summary[date] = {
                "status": "missing_candidate_file",
                "candidate_count": 0,
                "forward_return_count": 0,
                "coverage_ratio": 0,
            }
            continue
        if not returns_path.exists():
            candidates = load_candidates(candidate_path)
            date_summary[date] = {
                "status": "missing_forward_returns_file",
                "candidate_count": len(candidates),
                "forward_return_count": 0,
                "coverage_ratio": 0,
            }
            continue

        candidates = load_candidates(candidate_path)
        forward_returns = load_forward_returns(returns_path)
        date_forward_count = 0

        for candidate in candidates:
            original_code = str(candidate.get("code", "")).strip()
            if not original_code:
                continue
            sample_id = f"{date}:{original_code}"
            sample = dict(candidate)
            sample["code"] = sample_id
            sample["original_code"] = original_code
            sample["signal_date"] = date
            samples.append(sample)

            returns = forward_returns.get(original_code, {})
            if isinstance(returns, dict):
                aggregate_returns[sample_id] = returns
                if _has_any_return(returns, horizons):
                    date_forward_count += 1

        candidate_count = len(candidates)
        date_summary[date] = {
            "status": "ok",
            "candidate_count": candidate_count,
            "forward_return_count": date_forward_count,
            "coverage_ratio": round(date_forward_count / candidate_count, 4) if candidate_count else 0,
        }

    return samples, aggregate_returns, date_summary


def aggregate_scoring_calibration(
    dates: list[str],
    candidate_root: Path = DEFAULT_CANDIDATE_ROOT,
    returns_root: Path = DEFAULT_RETURNS_ROOT,
    horizons: tuple[str, ...] = ("1d", "3d", "5d"),
) -> dict:
    dates = sorted(dates)
    samples, forward_returns, date_summary = build_aggregate_samples(
        dates,
        candidate_root=candidate_root,
        returns_root=returns_root,
        horizons=horizons,
    )
    result = evaluate_score_layers(
        samples,
        forward_returns,
        horizons=horizons,
        as_of=_date_output_name(dates),
    )
    result.update(
        {
            "report_type": "aggregate_scoring_calibration",
            "dates_evaluated": dates,
            "date_summary": date_summary,
            "generated_at": datetime.now().isoformat(),
        }
    )
    return result


def generate_markdown_report(result: dict) -> str:
    lines = [
        "# Aggregate Scoring Calibration Report",
        "",
        f"**Generated At**: {result.get('generated_at', result.get('analysis_date', ''))}",
        f"**Dates**: {', '.join(result.get('dates_evaluated', []))}",
        "",
        "## Date Coverage",
        "",
        "| Date | Status | Candidates | With Returns | Coverage |",
        "|------|--------|------------|--------------|----------|",
    ]
    for date, summary in result.get("date_summary", {}).items():
        lines.append(
            f"| {date} | {summary.get('status', '')} | "
            f"{summary.get('candidate_count', 0)} | "
            f"{summary.get('forward_return_count', 0)} | "
            f"{summary.get('coverage_ratio', 0):.1%} |"
        )
    lines.append("")

    layer_markdown = generate_layer_markdown(result)
    layer_lines = layer_markdown.splitlines()
    if layer_lines and layer_lines[0].startswith("# "):
        layer_lines = layer_lines[1:]
    lines.extend(layer_lines)
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate scoring calibration across dates")
    parser.add_argument("--dates", required=True, help="Comma-separated dates, e.g. 2026-07-01,2026-07-02")
    parser.add_argument("--candidate-root", default=str(DEFAULT_CANDIDATE_ROOT), help="Directory containing DATE/top30_candidates.json")
    parser.add_argument("--returns-root", default=str(DEFAULT_RETURNS_ROOT), help="Directory containing DATE/forward_returns.json")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Base scoring calibration output directory")
    parser.add_argument("--horizons", default="1d,3d,5d", help="Comma-separated horizons")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    dates = [date.strip() for date in args.dates.split(",") if date.strip()]
    if not dates:
        print("ERROR: no dates provided", file=sys.stderr)
        return 2
    horizons = tuple(h.strip() for h in args.horizons.split(",") if h.strip())
    result = aggregate_scoring_calibration(
        dates,
        candidate_root=Path(args.candidate_root),
        returns_root=Path(args.returns_root),
        horizons=horizons,
    )

    output_dir = Path(args.output_dir) / "aggregate" / _date_output_name(sorted(dates))
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "aggregate_scoring_calibration.json"
    md_path = output_dir / "aggregate_scoring_calibration.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(generate_markdown_report(result), encoding="utf-8")

    coverage = result.get("coverage", {})
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    print(
        "Coverage: "
        f"{coverage.get('forward_return_count', 0)}/{coverage.get('candidate_count', 0)} "
        f"({coverage.get('coverage_ratio', 0):.1%})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
