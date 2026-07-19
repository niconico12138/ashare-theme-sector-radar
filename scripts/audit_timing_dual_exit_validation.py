#!/usr/bin/env python3
"""Audit paper-only dual-exit validation results."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.timing.exit_validation import validate_dual_exit_records
from theme_sector_radar.reporting.artifact_archive import write_text_preserving_previous
from theme_sector_radar.reporting.strict_json import load_strict_json


def audit_dual_exit_validation(
    *,
    records_path: Path,
    output_dir: Path,
    as_of: str,
    snapshot_label: str,
    fold_count: int = 3,
    min_labeled_triggers: int = 5,
    tail_loss_pct: float = -5.0,
) -> dict[str, Any]:
    data = load_strict_json(records_path)
    records = data.get("records") if isinstance(data, Mapping) else data
    records = [
        dict(record)
        for record in records or []
        if isinstance(record, Mapping)
        and str(record.get("as_of") or record.get("_sample_date") or "") <= as_of
    ]
    report = validate_dual_exit_records(
        records,
        fold_count=fold_count,
        min_labeled_triggers=min_labeled_triggers,
        tail_loss_pct=tail_loss_pct,
    )
    report.update(
        {
            "as_of": as_of,
            "snapshot_label": snapshot_label,
            "records_path": str(records_path),
            "promotion_status": "paper_research_only",
        }
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"timing_dual_exit_validation_{as_of}_{snapshot_label}.json"
    markdown_path = output_dir / f"timing_dual_exit_validation_{as_of}_{snapshot_label}.md"
    archived_json_path = write_text_preserving_previous(
        json_path,
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),
    )
    archived_markdown_path = write_text_preserving_previous(markdown_path, _markdown(report))
    return {
        "status": "ok",
        "json_path": json_path,
        "markdown_path": markdown_path,
        "archived_previous_paths": [path for path in (archived_json_path, archived_markdown_path) if path is not None],
        "report": report,
    }


def _markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Timing Dual Exit Validation",
        "",
        f"As of: `{report.get('as_of')}`",
        f"Snapshot: `{report.get('snapshot_label')}`",
        "",
        "- Paper-only: `True`",
        "- No execution signals: `True`",
        "- Promotion status: `paper_research_only`",
        "",
        "## Candidate Summary",
        "",
        "| Candidate | Triggers | Labeled | Avg exit % | Avg next % | Saved next % | Missed next % | Avoided next tail |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for candidate_id, candidate in (report.get("candidates") or {}).items():
        summary = candidate.get("summary") or {}
        lines.append(
            f"| `{candidate_id}` | {summary.get('trigger_count')} | {summary.get('labeled_trigger_count')} | "
            f"{summary.get('avg_simulated_exit_return_pct')} | {summary.get('avg_forward_return_pct')} | "
            f"{summary.get('avg_saved_vs_forward_pct')} | {summary.get('avg_missed_upside_pct')} | "
            f"{summary.get('forward_tail_avoided_count')} |"
        )
    lines.extend(["", "## Walk-Forward", ""])
    for candidate_id, candidate in (report.get("candidates") or {}).items():
        lines.append(f"### `{candidate_id}`")
        lines.extend(["", "| Fold | Range | Status | Labeled triggers | Avoided tails |", "|---:|---|---|---:|---:|"])
        for fold in ((candidate.get("walk_forward") or {}).get("folds") or []):
            lines.append(
                f"| {fold.get('fold_index')} | {fold.get('start_date')} to {fold.get('end_date')} | {fold.get('status')} | "
                f"{fold.get('labeled_trigger_count')} | {fold.get('forward_tail_avoided_count')} |"
            )
        lines.extend(["", "### Trigger Factors", "", "| Factor | Triggers | Saved next % | Avoided tails |", "|---|---:|---:|---:|"])
        for factor, item in (candidate.get("by_trigger_factor") or {}).items():
            lines.append(
                f"| `{factor}` | {item.get('trigger_count')} | {item.get('avg_saved_vs_forward_pct')} | "
                f"{item.get('forward_tail_avoided_count')} |"
            )
        concentration = candidate.get("concentration") or {}
        lines.extend(
            [
                "",
                f"Concentration: top date `{concentration.get('top_date_share')}`, "
                f"top board `{concentration.get('top_board_share')}`, "
                f"top code `{concentration.get('top_code_share')}`.",
                "",
            ]
        )
    lines.append("All outputs are paper research only and do not provide executable trading directions.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit paper-only dual exit validation")
    parser.add_argument("--records-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--snapshot-label", required=True)
    parser.add_argument("--fold-count", type=int, default=3)
    parser.add_argument("--min-labeled-triggers", type=int, default=5)
    parser.add_argument("--tail-loss-pct", type=float, default=-5.0)
    args = parser.parse_args(argv)
    result = audit_dual_exit_validation(
        records_path=Path(args.records_path),
        output_dir=Path(args.output_dir),
        as_of=args.as_of,
        snapshot_label=args.snapshot_label,
        fold_count=args.fold_count,
        min_labeled_triggers=args.min_labeled_triggers,
        tail_loss_pct=args.tail_loss_pct,
    )
    print(result["json_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
