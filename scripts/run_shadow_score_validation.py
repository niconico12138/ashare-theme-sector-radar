#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run rolling validation for current vs shadow watch-ranking scores."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.backtest.factor_value import DEFAULT_HORIZONS, run_shadow_score_validation  # noqa: E402
from scripts.run_factor_backtest import parse_horizons  # noqa: E402

DEFAULT_CANDIDATE_ROOT = PROJECT_ROOT / "reports" / "agent_bridge"
DEFAULT_RETURNS_ROOT = PROJECT_ROOT / "reports" / "forward_returns"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "reports" / "shadow_score_validation"


def parse_windows(value: str) -> tuple[int, ...]:
    windows: list[int] = []
    for part in re.split(r"[\s,]+", value.strip()):
        if part:
            windows.append(int(part))
    return tuple(windows)


def generate_markdown_report(result: dict) -> str:
    lines = [
        "# Shadow Score Validation",
        "",
        f"- End date: {result.get('end_date')}",
        f"- Baseline: `{result.get('baseline_factor_id')}`",
        f"- Shadow: `{result.get('shadow_factor_id')}`",
        f"- Recommendation: `{result.get('recommendation')}`",
        "",
        "## Rolling Windows",
        "",
        "| Window | Dates | Baseline IC | Shadow IC | Delta | Passed | N |",
        "|---:|---|---:|---:|---:|---|---:|",
    ]
    for item in result.get("window_results", []):
        lines.append(
            "| {window} | {start} to {end} | {base} | {shadow} | {delta} | {passed} | {n} |".format(
                window=item.get("lookback_days"),
                start=item.get("start_date"),
                end=item.get("end_date"),
                base="-" if item.get("baseline_rank_ic") is None else f"{item.get('baseline_rank_ic'):.4f}",
                shadow="-" if item.get("shadow_rank_ic") is None else f"{item.get('shadow_rank_ic'):.4f}",
                delta="-" if item.get("ic_delta") is None else f"{item.get('ic_delta'):.4f}",
                passed="yes" if item.get("passed") else "no",
                n=item.get("sample_count") or 0,
            )
        )
    lines.extend([
        "",
        "## Guardrails",
        "",
        "This validation is watch-ranking research only. It does not modify final_score, v2_score, selection_score, or emit trade triggers.",
    ])
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rolling validation for shadow watch score")
    parser.add_argument("--end-date", required=True, help="End date, YYYY-MM-DD")
    parser.add_argument("--windows", default="30,60,90,120", help="Comma-separated natural-day windows")
    parser.add_argument("--candidate-root", default=str(DEFAULT_CANDIDATE_ROOT))
    parser.add_argument("--returns-root", default=str(DEFAULT_RETURNS_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--horizons", default=",".join(DEFAULT_HORIZONS))
    parser.add_argument("--baseline-factor", default="optimized_watch_score")
    parser.add_argument("--shadow-factor", default="optimized_watch_score_v2_shadow")
    parser.add_argument("--min-samples", type=int, default=30)
    parser.add_argument("--min-ic-improvement", type=float, default=0.02)
    parser.add_argument("--min-pass-windows", type=int, default=3)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_shadow_score_validation(
        end_date=args.end_date,
        candidate_root=Path(args.candidate_root),
        returns_root=Path(args.returns_root),
        windows=parse_windows(args.windows),
        horizons=parse_horizons(args.horizons),
        baseline_factor_id=args.baseline_factor,
        shadow_factor_id=args.shadow_factor,
        min_samples=args.min_samples,
        min_ic_improvement=args.min_ic_improvement,
        min_pass_windows=args.min_pass_windows,
    )
    output_dir = Path(args.output_dir) / args.end_date
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "shadow_score_validation.json"
    md_path = output_dir / "shadow_score_validation.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(generate_markdown_report(result), encoding="utf-8")

    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    print(f"Recommendation: {result.get('recommendation')}")
    summary = result.get("summary", {})
    print(f"Passed windows: {summary.get('pass_window_count', 0)}/{summary.get('window_count', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
