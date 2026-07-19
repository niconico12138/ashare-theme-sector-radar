#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run paper-only intraday factor research from candidate JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if sys.stdout.encoding and sys.stdout.encoding.lower() in ("gbk", "cp936", "cp1252"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.timing.factor_research import (  # noqa: E402
    INTRADAY_FACTOR_RESEARCH_SPECS,
    evaluate_intraday_factor_research,
)


CANDIDATE_FILE_NAMES = (
    "top30_candidates.intraday_backfilled.json",
    "top30_candidates.analysis_backfilled.json",
    "top30_candidates.factor_backfilled.json",
    "top30_candidates.json",
)

OBSERVED_INTRADAY_FACTOR_IDS = {
    spec.factor_id
    for spec in INTRADAY_FACTOR_RESEARCH_SPECS
    if spec.factor_id not in {"sector_peer_rank_score", "market_regime_score", "sector_leader_score"}
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _candidate_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("candidates"), list):
        return [dict(item) for item in data["candidates"] if isinstance(item, dict)]
    if isinstance(data, list):
        return [dict(item) for item in data if isinstance(item, dict)]
    return []


def _load_forward_returns(path: Path | None) -> dict[str, float]:
    if path is None:
        return {}
    data = _load_json(path)
    rows = data.get("returns") if isinstance(data, dict) else data
    result: dict[str, float] = {}
    if not isinstance(rows, list):
        return result
    for item in rows:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip()
        value = _float(
            item.get("forward_return_pct")
            if item.get("forward_return_pct") is not None
            else item.get("return_pct")
        )
        if code and value is not None:
            result[code] = value
    return result


def _load_selection_validation_returns(root: Path | None, date: str) -> dict[str, float]:
    if root is None or not date:
        return {}
    path = root / date / "next_day_selection_validation.json"
    if not path.exists():
        return {}
    data = _load_json(path)
    rows = data.get("per_stock") if isinstance(data, dict) else None
    result: dict[str, float] = {}
    if not isinstance(rows, list):
        return result
    for item in rows:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip()
        value = _float(
            item.get("next_return_pct")
            if item.get("next_return_pct") is not None
            else item.get("forward_return_pct")
        )
        if code and value is not None:
            result[code] = value
    return result


def _discover_candidate_files(candidate_root: Path | None, start: str | None, end: str | None) -> list[Path]:
    if candidate_root is None or not candidate_root.exists():
        return []
    files: list[Path] = []
    for date_dir in sorted(path for path in candidate_root.iterdir() if path.is_dir()):
        date = date_dir.name
        if start and date < start:
            continue
        if end and date > end:
            continue
        for name in CANDIDATE_FILE_NAMES:
            path = date_dir / name
            if path.exists():
                files.append(path)
                break
    return files


def _has_intraday_factor(row: dict[str, Any]) -> bool:
    return any(row.get(factor_id) is not None for factor_id in OBSERVED_INTRADAY_FACTOR_IDS)


def run_timing_factor_research(
    *,
    candidate_files: list[Path],
    candidate_root: Path | None = None,
    start: str | None = None,
    end: str | None = None,
    output_dir: Path | str,
    as_of: str,
    snapshot_label: str,
    forward_returns_json: Path | None = None,
    selection_validation_root: Path | None = PROJECT_ROOT / "reports" / "selection_validation",
    return_field: str = "forward_return_pct",
    min_labeled_samples: int = 20,
    thresholds: list[float] | None = None,
) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    discovered_files = _discover_candidate_files(candidate_root, start, end)
    all_candidate_files = list(candidate_files) + [path for path in discovered_files if path not in candidate_files]
    forward_returns = _load_forward_returns(forward_returns_json)
    dates_without_selection_validation: list[str] = []
    for path in all_candidate_files:
        date = Path(path).parent.name
        dated_returns = _load_selection_validation_returns(selection_validation_root, date)
        if selection_validation_root is not None and not dated_returns:
            dates_without_selection_validation.append(date)
        for row in _candidate_rows(_load_json(Path(path))):
            code = str(row.get("code") or "").strip()
            if return_field not in row:
                if code in dated_returns:
                    row[return_field] = dated_returns[code]
                elif code in forward_returns:
                    row[return_field] = forward_returns[code]
            samples.append(row)

    report = evaluate_intraday_factor_research(
        samples,
        return_field=return_field,
        min_labeled_samples=min_labeled_samples,
        thresholds=thresholds,
    )
    report["as_of"] = as_of
    report["snapshot_label"] = snapshot_label
    report["source_files"] = {
        "candidate_files": [str(path) for path in all_candidate_files],
        "forward_returns_json": str(forward_returns_json) if forward_returns_json else None,
        "selection_validation_root": str(selection_validation_root) if selection_validation_root else None,
    }
    report["data_coverage"] = {
        "candidate_file_count": len(all_candidate_files),
        "sample_count": len(samples),
        "labeled_sample_count": sum(1 for row in samples if _float(row.get(return_field)) is not None),
        "intraday_observed_sample_count": sum(1 for row in samples if _has_intraday_factor(row)),
        "dates_without_selection_validation": sorted(set(dates_without_selection_validation)),
        "start": start,
        "end": end,
    }

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / f"timing_factor_research_{as_of}_{snapshot_label}.json"
    markdown_path = root / f"timing_factor_research_{as_of}_{snapshot_label}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(report, markdown_path)
    return {"status": "ok", "json_path": json_path, "markdown_path": markdown_path, "report": report}


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report.get("summary") or {}
    lines = [
        "# Timing Factor Research",
        "",
        f"As of: {report.get('as_of')}",
        f"Snapshot: `{report.get('snapshot_label')}`",
        "",
        "## Summary",
        "",
        f"- Paper-only: `{report.get('paper_trading_only')}`",
        f"- No execution signals: `{report.get('no_execution_signals')}`",
        f"- Samples: `{summary.get('sample_count')}`",
        f"- Labeled samples: `{summary.get('labeled_sample_count')}`",
        f"- Categories: `{summary.get('category_count')}`",
        f"- Valuable factors: `{summary.get('valuable_factor_count')}`",
        f"- Watchlist factors: `{summary.get('watchlist_factor_count')}`",
        f"- Pending validation factors: `{summary.get('pending_validation_factor_count')}`",
        "",
        "## Data Coverage",
        "",
        f"- Candidate files: `{(report.get('data_coverage') or {}).get('candidate_file_count')}`",
        f"- Intraday observed samples: `{(report.get('data_coverage') or {}).get('intraday_observed_sample_count')}`",
        f"- Dates without selection validation: `{len((report.get('data_coverage') or {}).get('dates_without_selection_validation') or [])}`",
        "",
        "## Category Results",
        "",
        "| Category | Valuable | Watchlist | Pending | Top factor | Rating | Value score | Best threshold |",
        "|---|---:|---:|---:|---|---|---:|---:|",
    ]
    for category, item in (report.get("categories") or {}).items():
        top = (item.get("top_factors") or [{}])[0]
        best = _best_threshold(top)
        lines.append(
            f"| `{category}` | {item.get('valuable_factor_count')} | {item.get('watchlist_factor_count')} | "
            f"{item.get('pending_validation_factor_count')} | `{top.get('factor_id') or ''}` | "
            f"{top.get('rating') or ''} | {top.get('value_score') or ''} | {best.get('threshold') or ''} |"
        )
    lines.extend(
        [
            "",
            "## Valuable / Watchlist Factors",
            "",
            "| Factor | Category | Direction | Rating | Spread % | Value score | Best threshold | Threshold spread % |",
            "|---|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for item in report.get("valuable_factors", []):
        best = _best_threshold(item)
        lines.append(
            f"| `{item.get('factor_id')}` | `{item.get('category')}` | `{item.get('direction')}` | "
            f"{item.get('rating')} | {item.get('adjusted_spread_pct') or ''} | {item.get('value_score') or ''} | "
            f"{best.get('threshold') or ''} | {best.get('spread_vs_rejected_pct') or ''} |"
        )
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- Paper-only research artifact.",
            "- Does not connect to brokers.",
            "- Does not emit executable buy/sell signals.",
            "- Does not modify official scores.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run paper-only timing factor research")
    parser.add_argument("--candidate-json", action="append", default=[])
    parser.add_argument("--candidate-root")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--forward-returns-json")
    parser.add_argument("--selection-validation-root", default=str(PROJECT_ROOT / "reports" / "selection_validation"))
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "reports" / "timing_factor_research"))
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--snapshot-label", required=True)
    parser.add_argument("--return-field", default="forward_return_pct")
    parser.add_argument("--min-labeled-samples", type=int, default=20)
    parser.add_argument("--thresholds", nargs="*", type=float, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_timing_factor_research(
        candidate_files=[Path(path) for path in args.candidate_json],
        candidate_root=Path(args.candidate_root) if args.candidate_root else None,
        start=args.start,
        end=args.end,
        forward_returns_json=Path(args.forward_returns_json) if args.forward_returns_json else None,
        selection_validation_root=Path(args.selection_validation_root) if args.selection_validation_root else None,
        output_dir=Path(args.output_dir),
        as_of=args.as_of,
        snapshot_label=args.snapshot_label,
        return_field=args.return_field,
        min_labeled_samples=args.min_labeled_samples,
        thresholds=args.thresholds,
    )
    summary = result["report"]["summary"]
    print(f"Timing factor research written: {result['json_path']}")
    print(
        f"samples={summary['sample_count']} labeled={summary['labeled_sample_count']} "
        f"valuable={summary['valuable_factor_count']} watchlist={summary['watchlist_factor_count']} "
        f"no_execution_signals={result['report']['no_execution_signals']}"
    )
    return 0


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _best_threshold(factor: dict[str, Any]) -> dict[str, Any]:
    rows = list((factor.get("threshold_results") or {}).values())
    rows = [row for row in rows if row.get("spread_vs_rejected_pct") is not None and row.get("selected_count")]
    if not rows:
        return {}
    return sorted(rows, key=lambda row: (row.get("spread_vs_rejected_pct") or -999.0, row.get("selected_count") or 0))[-1]


if __name__ == "__main__":
    raise SystemExit(main())
