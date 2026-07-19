#!/usr/bin/env python3
"""Audit same-day board concentration risk for paper-only timing versions."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_timing_strategy_overfit import _load_samples  # noqa: E402
from scripts.run_timing_combination_experiment import _float  # noqa: E402
from theme_sector_radar.reporting.artifact_archive import write_text_preserving_previous  # noqa: E402
from theme_sector_radar.timing.combination_experiment import (  # noqa: E402
    StrategyVersion,
    build_default_strategy_versions,
)


def run_concentration_risk_audit(
    *,
    candidate_root: Path,
    output_dir: Path,
    as_of: str,
    snapshot_label: str,
    version_ids: Sequence[str],
    start: str | None = None,
    end: str | None = None,
    selection_validation_root: Path | None = PROJECT_ROOT / "reports" / "selection_validation",
    concentration_threshold: int = 2,
    tail_loss_pct: float = -5.0,
) -> dict[str, Any]:
    samples = _load_samples(candidate_root, start, end, selection_validation_root)
    versions = _select_versions(version_ids)
    report = {
        "schema_version": "timing_concentration_risk_audit.v1",
        "as_of": as_of,
        "snapshot_label": snapshot_label,
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
        "parameters": {
            "candidate_root": str(candidate_root),
            "selection_validation_root": str(selection_validation_root) if selection_validation_root else None,
            "start": start,
            "end": end,
            "version_ids": list(version_ids),
            "concentration_threshold": concentration_threshold,
            "tail_loss_pct": tail_loss_pct,
        },
        "sample_summary": _sample_summary(samples),
        "versions": {},
    }
    for version in versions:
        report["versions"][version.version_id] = _audit_version(
            samples,
            version,
            concentration_threshold=concentration_threshold,
            tail_loss_pct=tail_loss_pct,
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"timing_concentration_risk_{as_of}_{snapshot_label}.json"
    markdown_path = output_dir / f"timing_concentration_risk_{as_of}_{snapshot_label}.md"
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


def _select_versions(version_ids: Sequence[str]) -> list[StrategyVersion]:
    versions_by_id = {version.version_id: version for version in build_default_strategy_versions()}
    missing = [version_id for version_id in version_ids if version_id not in versions_by_id]
    if missing:
        raise ValueError(f"Unknown strategy version ids: {', '.join(missing)}")
    return [versions_by_id[version_id] for version_id in version_ids]


def _audit_version(
    samples: Sequence[Mapping[str, Any]],
    version: StrategyVersion,
    *,
    concentration_threshold: int,
    tail_loss_pct: float,
) -> dict[str, Any]:
    labeled = [row for row in samples if _float(row.get("forward_return_pct")) is not None]
    selected = [row for row in labeled if all(condition.matches(row) for condition in version.conditions)]
    groups = _date_board_groups(selected, tail_loss_pct=tail_loss_pct)
    concentrated = [item for item in groups if item["selected_count"] >= concentration_threshold]
    tail_loss_count = sum(1 for row in selected if (_float(row.get("forward_return_pct")) or 0.0) <= tail_loss_pct)
    concentrated_entries = {
        (item["date"], str(code.get("code") or ""))
        for item in concentrated
        for code in item.get("codes") or []
    }
    concentrated_tail_entries = {
        (item["date"], str(code.get("code") or ""))
        for item in concentrated
        for code in item.get("codes") or []
        if (_float(code.get("forward_return_pct")) or 0.0) <= tail_loss_pct
    }
    concentrated_tail_loss_count = len(concentrated_tail_entries)
    top_concentrated = sorted(
        concentrated,
        key=lambda item: (-item["tail_loss_count"], -item["selected_count"], item["group_key"]),
    )[:20]
    return {
        "version_id": version.version_id,
        "description": version.description,
        "selected_count": len(selected),
        "tail_loss_count": tail_loss_count,
        "tail_loss_rate": round(tail_loss_count / len(selected), 4) if selected else None,
        "group_count": len(groups),
        "concentrated_group_count": len(concentrated),
        "concentrated_selected_count": len(concentrated_entries),
        "concentrated_tail_loss_count": concentrated_tail_loss_count,
        "concentrated_tail_loss_share": round(concentrated_tail_loss_count / tail_loss_count, 4) if tail_loss_count else 0.0,
        "top_concentrated_groups": top_concentrated,
        "paper_trading_only": True,
        "no_execution_signals": True,
    }


def _date_board_groups(rows: Sequence[Mapping[str, Any]], *, tail_loss_pct: float) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        date = str(row.get("_sample_date") or "unknown_date")
        boards = _boards(row)
        if not boards:
            boards = ["unknown_board"]
        for board in boards:
            grouped[f"{date}|{board}"].append(row)
    result = []
    for key, items in grouped.items():
        returns = [_float(row.get("forward_return_pct")) for row in items]
        clean_returns = [value for value in returns if value is not None]
        tail_rows = [row for row in items if (_float(row.get("forward_return_pct")) or 0.0) <= tail_loss_pct]
        result.append(
            {
                "group_key": key,
                "date": key.split("|", 1)[0],
                "board": key.split("|", 1)[1],
                "selected_count": len(items),
                "tail_loss_count": len(tail_rows),
                "tail_loss_rate": round(len(tail_rows) / len(items), 4) if items else None,
                "avg_return_pct": round(sum(clean_returns) / len(clean_returns), 4) if clean_returns else None,
                "min_return_pct": round(min(clean_returns), 4) if clean_returns else None,
                "codes": [
                    {
                        "code": row.get("code"),
                        "name": row.get("name"),
                        "forward_return_pct": _round(_float(row.get("forward_return_pct"))),
                    }
                    for row in sorted(items, key=lambda item: (_float(item.get("forward_return_pct")) or 0.0))
                ],
            }
        )
    return sorted(result, key=lambda item: (-item["selected_count"], -item["tail_loss_count"], item["group_key"]))


def _boards(row: Mapping[str, Any]) -> list[str]:
    raw = row.get("boards") or row.get("source_boards")
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item)]
    if isinstance(raw, str) and raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    return []


def _sample_summary(samples: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    dates = sorted({str(row.get("_sample_date")) for row in samples if row.get("_sample_date")})
    return {
        "sample_count": len(samples),
        "labeled_sample_count": sum(1 for row in samples if _float(row.get("forward_return_pct")) is not None),
        "date_count": len(dates),
        "start": dates[0] if dates else None,
        "end": dates[-1] if dates else None,
    }


def _markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Timing Concentration Risk Audit",
        "",
        f"As of: `{report.get('as_of')}`",
        f"Snapshot: `{report.get('snapshot_label')}`",
        "",
        "- Paper-only: `True`",
        "- No execution signals: `True`",
        "- Does not modify official scores: `True`",
        "",
        "## Version Summary",
        "",
        "| Version | Selected | Tail | Tail rate | Concentrated groups | Concentrated selected | Concentrated tail | Tail share |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for version_id, item in (report.get("versions") or {}).items():
        lines.append(
            f"| `{version_id}` | {item.get('selected_count')} | {item.get('tail_loss_count')} | "
            f"{item.get('tail_loss_rate')} | {item.get('concentrated_group_count')} | "
            f"{item.get('concentrated_selected_count')} | {item.get('concentrated_tail_loss_count')} | "
            f"{item.get('concentrated_tail_loss_share')} |"
        )
    for version_id, item in (report.get("versions") or {}).items():
        lines.extend(["", f"## Top Concentrated Groups: `{version_id}`", ""])
        lines.extend(["| Group | Selected | Tail | Tail rate | Avg % | Min % | Codes |", "|---|---:|---:|---:|---:|---:|---|"])
        for group in item.get("top_concentrated_groups") or []:
            codes = ", ".join(
                f"{row.get('code')}({row.get('forward_return_pct')})" for row in group.get("codes") or []
            )
            lines.append(
                f"| `{group.get('group_key')}` | {group.get('selected_count')} | {group.get('tail_loss_count')} | "
                f"{group.get('tail_loss_rate')} | {group.get('avg_return_pct')} | {group.get('min_return_pct')} | {codes} |"
            )
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- This report is for paper-only concentration risk research.",
            "- It does not connect to brokers or emit executable buy/sell signals.",
            "- It does not modify official scores.",
        ]
    )
    return "\n".join(lines) + "\n"


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit paper-only timing concentration risk")
    parser.add_argument("--candidate-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--snapshot-label", required=True)
    parser.add_argument("--version-id", action="append", required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--selection-validation-root", default=str(PROJECT_ROOT / "reports" / "selection_validation"))
    parser.add_argument("--concentration-threshold", type=int, default=2)
    parser.add_argument("--tail-loss-pct", type=float, default=-5.0)
    args = parser.parse_args(argv)
    result = run_concentration_risk_audit(
        candidate_root=Path(args.candidate_root),
        output_dir=Path(args.output_dir),
        as_of=args.as_of,
        snapshot_label=args.snapshot_label,
        version_ids=args.version_id,
        start=args.start,
        end=args.end,
        selection_validation_root=Path(args.selection_validation_root) if args.selection_validation_root else None,
        concentration_threshold=args.concentration_threshold,
        tail_loss_pct=args.tail_loss_pct,
    )
    print(result["json_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
