#!/usr/bin/env python3
"""Compare paper-only price-momentum research on 5m and 1m candidate data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_timing_factor_research import run_timing_factor_research
from theme_sector_radar.timing.factor_research import compare_frequency_factor_reports


def run_price_momentum_frequency_validation(
    *,
    candidate_root_5m: Path,
    candidate_root_1m: Path,
    output_dir: Path,
    as_of: str,
    snapshot_label: str,
    start: str | None = None,
    end: str | None = None,
    selection_validation_root: Path | None = PROJECT_ROOT / "reports" / "selection_validation",
    min_labeled_samples: int = 20,
    thresholds: list[float] | None = None,
) -> dict[str, Any]:
    common = {
        "candidate_files": [],
        "start": start,
        "end": end,
        "as_of": as_of,
        "selection_validation_root": selection_validation_root,
        "min_labeled_samples": min_labeled_samples,
        "thresholds": thresholds,
    }
    report_5m = run_timing_factor_research(
        candidate_root=candidate_root_5m,
        output_dir=output_dir / "five_minute",
        snapshot_label=f"{snapshot_label}_5m",
        **common,
    )["report"]
    report_1m = run_timing_factor_research(
        candidate_root=candidate_root_1m,
        output_dir=output_dir / "one_minute",
        snapshot_label=f"{snapshot_label}_1m",
        **common,
    )["report"]
    report = {
        "schema_version": "price_momentum_frequency_validation.v1",
        "as_of": as_of,
        "snapshot_label": snapshot_label,
        "paper_trading_only": True,
        "shadow_only": True,
        "does_not_modify_official_scores": True,
        "no_execution_signals": True,
        "report_5m_summary": report_5m["summary"],
        "report_1m_summary": report_1m["summary"],
        "coverage_5m": report_5m.get("data_coverage", {}),
        "coverage_1m": report_1m.get("data_coverage", {}),
        "comparison": compare_frequency_factor_reports(report_5m, report_1m),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"price_momentum_frequency_validation_{as_of}_{snapshot_label}.json"
    markdown_path = output_dir / f"price_momentum_frequency_validation_{as_of}_{snapshot_label}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(_markdown(report), encoding="utf-8")
    return {"status": "ok", "json_path": json_path, "markdown_path": markdown_path, "report": report}


def _markdown(report: dict[str, Any]) -> str:
    comparison = report["comparison"]
    lines = [
        "# Price Momentum Frequency Validation",
        "",
        f"As of: {report['as_of']}",
        f"Snapshot: `{report['snapshot_label']}`",
        "",
        "- Paper-only: `True`",
        "- No execution signals: `True`",
        "",
        "## 1m Eligible Factors",
        "",
        "| Factor | 5m rating | 1m rating | Status |",
        "|---|---|---|---|",
    ]
    for factor_id in comparison["eligible_factor_ids"]:
        item = comparison["factors"][factor_id]
        lines.append(
            f"| `{factor_id}` | `{item['rating_5m']}` | `{item['rating_1m']}` | `{item['confirmation_status']}` |"
        )
    if not comparison["eligible_factor_ids"]:
        lines.append("| None | - | - | No 5m price-momentum factor was promoted. |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run paper-only 5m then 1m price-momentum validation")
    parser.add_argument("--candidate-root-5m", required=True)
    parser.add_argument("--candidate-root-1m", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--snapshot-label", required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--selection-validation-root", default=str(PROJECT_ROOT / "reports" / "selection_validation"))
    parser.add_argument("--min-labeled-samples", type=int, default=20)
    parser.add_argument("--thresholds", nargs="*", type=float)
    args = parser.parse_args(argv)
    result = run_price_momentum_frequency_validation(
        candidate_root_5m=Path(args.candidate_root_5m),
        candidate_root_1m=Path(args.candidate_root_1m),
        output_dir=Path(args.output_dir),
        as_of=args.as_of,
        snapshot_label=args.snapshot_label,
        start=args.start,
        end=args.end,
        selection_validation_root=Path(args.selection_validation_root) if args.selection_validation_root else None,
        min_labeled_samples=args.min_labeled_samples,
        thresholds=args.thresholds,
    )
    print(result["json_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
