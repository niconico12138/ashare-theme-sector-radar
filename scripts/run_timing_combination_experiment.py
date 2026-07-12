#!/usr/bin/env python3
"""Run paper-only timing factor combination experiments."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.timing.combination_experiment import (  # noqa: E402
    build_default_strategy_versions,
    evaluate_strategy_versions,
)


CANDIDATE_FILE_NAMES = (
    "top30_candidates.intraday_backfilled.json",
    "top30_candidates.analysis_backfilled.json",
    "top30_candidates.factor_backfilled.json",
    "top30_candidates.json",
)


def run_timing_combination_experiment(
    *,
    candidate_root: Path,
    output_dir: Path,
    as_of: str,
    snapshot_label: str,
    start: str | None = None,
    end: str | None = None,
    selection_validation_root: Path | None = PROJECT_ROOT / "reports" / "selection_validation",
    min_selected: int = 20,
) -> dict[str, Any]:
    candidate_files = _discover_candidate_files(candidate_root, start, end)
    samples = []
    dates_without_selection_validation = []
    for path in candidate_files:
        date = path.parent.name
        dated_returns = _load_selection_validation_returns(selection_validation_root, date)
        if selection_validation_root is not None and not dated_returns:
            dates_without_selection_validation.append(date)
        for row in _candidate_rows(_load_json(path)):
            code = str(row.get("code") or "").strip()
            if row.get("forward_return_pct") is None and code in dated_returns:
                row["forward_return_pct"] = dated_returns[code]
            samples.append(row)

    report = evaluate_strategy_versions(
        samples,
        build_default_strategy_versions(),
        min_selected=min_selected,
    )
    report["as_of"] = as_of
    report["snapshot_label"] = snapshot_label
    report["data_coverage"] = {
        "candidate_file_count": len(candidate_files),
        "sample_count": len(samples),
        "labeled_sample_count": sum(1 for row in samples if _float(row.get("forward_return_pct")) is not None),
        "dates_without_selection_validation": sorted(set(dates_without_selection_validation)),
        "start": start,
        "end": end,
    }
    report["source_files"] = {
        "candidate_root": str(candidate_root),
        "selection_validation_root": str(selection_validation_root) if selection_validation_root else None,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"timing_combination_experiment_{as_of}_{snapshot_label}.json"
    markdown_path = output_dir / f"timing_combination_experiment_{as_of}_{snapshot_label}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(_markdown(report), encoding="utf-8")
    return {"status": "ok", "json_path": json_path, "markdown_path": markdown_path, "report": report}


def _discover_candidate_files(candidate_root: Path, start: str | None, end: str | None) -> list[Path]:
    if not candidate_root.exists():
        return []
    files = []
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


def _candidate_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("candidates"), list):
        return [dict(item) for item in data["candidates"] if isinstance(item, dict)]
    if isinstance(data, list):
        return [dict(item) for item in data if isinstance(item, dict)]
    return []


def _load_selection_validation_returns(root: Path | None, date: str) -> dict[str, float]:
    if root is None:
        return {}
    path = root / date / "next_day_selection_validation.json"
    if not path.exists():
        return {}
    data = _load_json(path)
    rows = data.get("per_stock") if isinstance(data, dict) else None
    result = {}
    if not isinstance(rows, list):
        return result
    for item in rows:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip()
        value = _float(item.get("next_return_pct") if item.get("next_return_pct") is not None else item.get("forward_return_pct"))
        if code and value is not None:
            result[code] = value
    return result


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _markdown(report: dict[str, Any]) -> str:
    best = report.get("best_version") or {}
    lines = [
        "# Timing Combination Experiment",
        "",
        f"As of: {report.get('as_of')}",
        f"Snapshot: `{report.get('snapshot_label')}`",
        "",
        "- Paper-only: `True`",
        "- No execution signals: `True`",
        "",
        "## Best Version",
        "",
        f"- Version: `{best.get('version_id')}`",
        f"- Selected count: `{best.get('selected_count')}`",
        f"- Avg return: `{best.get('selected_avg_return_pct')}`",
        f"- Spread vs rejected: `{best.get('spread_vs_rejected_pct')}`",
        f"- Win rate: `{best.get('selected_win_rate')}`",
        f"- Min return: `{best.get('selected_min_return_pct')}`",
        f"- Tail loss count: `{best.get('selected_tail_loss_count')}`",
        f"- Tail loss rate: `{best.get('selected_tail_loss_rate')}`",
        "",
        "## Ranked Versions",
        "",
        "| Version | Selected | Avg return % | Spread % | Win rate | Min return % | Tail losses | Tail rate | Score | Valid |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in report.get("versions") or []:
        lines.append(
            f"| `{item.get('version_id')}` | {item.get('selected_count')} | "
            f"{item.get('selected_avg_return_pct') or ''} | {item.get('spread_vs_rejected_pct') or ''} | "
            f"{item.get('selected_win_rate') or ''} | {item.get('selected_min_return_pct') or ''} | "
            f"{item.get('selected_tail_loss_count') or 0} | {item.get('selected_tail_loss_rate') or ''} | "
            f"{item.get('research_score') or ''} | `{item.get('is_valid')}` |"
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
    return "\n".join(lines) + "\n"


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run paper-only timing combination experiment")
    parser.add_argument("--candidate-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--snapshot-label", required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--selection-validation-root", default=str(PROJECT_ROOT / "reports" / "selection_validation"))
    parser.add_argument("--min-selected", type=int, default=20)
    args = parser.parse_args(argv)
    result = run_timing_combination_experiment(
        candidate_root=Path(args.candidate_root),
        output_dir=Path(args.output_dir),
        as_of=args.as_of,
        snapshot_label=args.snapshot_label,
        start=args.start,
        end=args.end,
        selection_validation_root=Path(args.selection_validation_root) if args.selection_validation_root else None,
        min_selected=args.min_selected,
    )
    print(result["json_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
