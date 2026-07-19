#!/usr/bin/env python3
"""Audit paper-only factor exit strategies from timing paper records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.reporting.artifact_archive import write_text_preserving_previous  # noqa: E402
from theme_sector_radar.reporting.strict_json import load_strict_json  # noqa: E402


def audit_factor_exit_report(
    *,
    records_path: Path,
    output_dir: Path,
    as_of: str,
    snapshot_label: str,
    tail_loss_pct: float = -5.0,
) -> dict[str, Any]:
    records = _load_records(records_path)
    report = {
        "schema_version": "timing_factor_exit_audit.v1",
        "as_of": as_of,
        "snapshot_label": snapshot_label,
        "records_path": str(records_path),
        "summary": {
            "record_count": len(records),
            "labeled_record_count": sum(1 for record in records if _float(record.get("forward_return_pct")) is not None),
            "unlabeled_record_count": sum(1 for record in records if _float(record.get("forward_return_pct")) is None),
            "tail_loss_pct": tail_loss_pct,
        },
        "strategies": _strategy_summary(records, tail_loss_pct=tail_loss_pct),
        "by_version": _by_version_summary(records, tail_loss_pct=tail_loss_pct),
        "by_trigger_factor": _by_trigger_factor_summary(records, tail_loss_pct=tail_loss_pct),
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"timing_factor_exit_audit_{as_of}_{snapshot_label}.json"
    markdown_path = output_dir / f"timing_factor_exit_audit_{as_of}_{snapshot_label}.md"
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


def _load_records(path: Path) -> list[dict[str, Any]]:
    data = load_strict_json(path)
    rows = data.get("records") if isinstance(data, dict) else data
    return [dict(row) for row in rows or [] if isinstance(row, dict)]


def _strategy_summary(records: list[Mapping[str, Any]], *, tail_loss_pct: float) -> dict[str, Any]:
    strategy_ids = sorted(
        {
            strategy_id
            for record in records
            for strategy_id in ((record.get("factor_exit_triggers") or {}).get("strategies") or {}).keys()
        }
    )
    return {strategy_id: _summarize_strategy(records, strategy_id, tail_loss_pct=tail_loss_pct) for strategy_id in strategy_ids}


def _by_version_summary(records: list[Mapping[str, Any]], *, tail_loss_pct: float) -> dict[str, Any]:
    versions = sorted({str(record.get("timing_version_id") or "unknown") for record in records})
    return {
        version: _strategy_summary(
            [record for record in records if str(record.get("timing_version_id") or "unknown") == version],
            tail_loss_pct=tail_loss_pct,
        )
        for version in versions
    }


def _by_trigger_factor_summary(records: list[Mapping[str, Any]], *, tail_loss_pct: float) -> dict[str, Any]:
    factor_pairs: dict[str, list[tuple[Mapping[str, Any], Mapping[str, Any]]]] = {}
    combo_pairs: dict[str, list[tuple[Mapping[str, Any], Mapping[str, Any]]]] = {}
    for record in records:
        strategies = (record.get("factor_exit_triggers") or {}).get("strategies") or {}
        for strategy_id, row in strategies.items():
            if not isinstance(row, Mapping) or not row.get("triggered"):
                continue
            factors = sorted({str(item) for item in row.get("trigger_factors") or [] if str(item)})
            for factor in factors:
                factor_pairs.setdefault(f"{strategy_id}:{factor}", []).append((record, row))
            if factors:
                combo_pairs.setdefault(f"{strategy_id}:{'+'.join(factors)}", []).append((record, row))
    return {
        "single_factors": {
            key: _summarize_trigger_pairs(pairs, tail_loss_pct=tail_loss_pct)
            for key, pairs in sorted(factor_pairs.items())
        },
        "factor_combinations": {
            key: _summarize_trigger_pairs(pairs, tail_loss_pct=tail_loss_pct)
            for key, pairs in sorted(combo_pairs.items())
        },
        "paper_trading_only": True,
    }


def _summarize_strategy(records: list[Mapping[str, Any]], strategy_id: str, *, tail_loss_pct: float) -> dict[str, Any]:
    strategy_pairs = [
        (record, ((record.get("factor_exit_triggers") or {}).get("strategies") or {}).get(strategy_id) or {})
        for record in records
    ]
    strategy_rows = [row for _, row in strategy_pairs]
    triggered_pairs = [(record, row) for record, row in strategy_pairs if row.get("triggered")]
    triggered = [row for _, row in triggered_pairs]
    labeled_pairs = [(record, row) for record, row in strategy_pairs if _float(record.get("forward_return_pct")) is not None]
    triggered_labeled_pairs = [
        (record, row)
        for record, row in triggered_pairs
        if _float(record.get("forward_return_pct")) is not None and _float(row.get("trigger_return_pct")) is not None
    ]
    close_returns = [_float(row.get("close_return_pct")) for row in strategy_rows]
    close_returns = [value for value in close_returns if value is not None]
    trigger_returns = [_float(row.get("trigger_return_pct")) for row in triggered]
    trigger_returns = [value for value in trigger_returns if value is not None]
    forward_returns = [_float(record.get("forward_return_pct")) for record, _ in labeled_pairs]
    forward_returns = [value for value in forward_returns if value is not None]
    saved = [_float(row.get("saved_vs_close_pct")) for row in triggered]
    saved = [value for value in saved if value is not None]
    missed = [_float(row.get("missed_upside_pct")) for row in triggered]
    missed = [value for value in missed if value is not None]
    saved_vs_forward = [
        _float(row.get("trigger_return_pct")) - _float(record.get("forward_return_pct"))
        for record, row in triggered_labeled_pairs
        if _float(row.get("trigger_return_pct")) is not None and _float(record.get("forward_return_pct")) is not None
    ]
    missed_vs_forward = [max(0.0, -value) for value in saved_vs_forward]
    triggered_tail = sum(1 for value in trigger_returns if value <= tail_loss_pct)
    close_tail = sum(1 for value in close_returns if value <= tail_loss_pct)
    forward_tail = sum(1 for value in forward_returns if value <= tail_loss_pct)
    trigger_vs_forward_tail = sum(
        1
        for record, row in triggered_labeled_pairs
        if (_float(row.get("trigger_return_pct")) or 0.0) <= tail_loss_pct
        and (_float(record.get("forward_return_pct")) is not None)
    )
    avoided_forward_tail = sum(
        1
        for record, row in triggered_labeled_pairs
        if (_float(record.get("forward_return_pct")) or 0.0) <= tail_loss_pct
        and (_float(row.get("trigger_return_pct")) or 0.0) > tail_loss_pct
    )
    return {
        "record_count": len(records),
        "labeled_record_count": len(labeled_pairs),
        "trigger_count": len(triggered),
        "trigger_labeled_count": len(triggered_labeled_pairs),
        "trigger_rate": _round(len(triggered) / len(records)) if records else None,
        "trigger_labeled_rate": _round(len(triggered_labeled_pairs) / len(labeled_pairs)) if labeled_pairs else None,
        "avg_trigger_return_pct": _avg(trigger_returns),
        "avg_close_return_pct": _avg(close_returns),
        "avg_forward_return_pct": _avg(forward_returns),
        "avg_saved_vs_close_pct": _avg(saved),
        "avg_missed_upside_pct": _avg(missed),
        "avg_saved_vs_forward_pct": _avg(saved_vs_forward),
        "avg_missed_vs_forward_pct": _avg(missed_vs_forward),
        "trigger_tail_loss_count": triggered_tail,
        "close_tail_loss_count": close_tail,
        "forward_tail_loss_count": forward_tail,
        "trigger_vs_forward_tail_loss_count": trigger_vs_forward_tail,
        "tail_loss_reduction_count": close_tail - triggered_tail,
        "forward_tail_avoided_count": avoided_forward_tail,
        "paper_trading_only": True,
    }


def _summarize_trigger_pairs(
    pairs: list[tuple[Mapping[str, Any], Mapping[str, Any]]],
    *,
    tail_loss_pct: float,
) -> dict[str, Any]:
    labeled_pairs = [
        (record, row)
        for record, row in pairs
        if _float(record.get("forward_return_pct")) is not None and _float(row.get("trigger_return_pct")) is not None
    ]
    trigger_returns = [_float(row.get("trigger_return_pct")) for _, row in pairs]
    trigger_returns = [value for value in trigger_returns if value is not None]
    close_returns = [_float(row.get("close_return_pct")) for _, row in pairs]
    close_returns = [value for value in close_returns if value is not None]
    forward_returns = [_float(record.get("forward_return_pct")) for record, _ in labeled_pairs]
    forward_returns = [value for value in forward_returns if value is not None]
    saved_vs_forward = [
        _float(row.get("trigger_return_pct")) - _float(record.get("forward_return_pct"))
        for record, row in labeled_pairs
        if _float(row.get("trigger_return_pct")) is not None and _float(record.get("forward_return_pct")) is not None
    ]
    missed_vs_forward = [max(0.0, -value) for value in saved_vs_forward]
    avoided_forward_tail = sum(
        1
        for record, row in labeled_pairs
        if (_float(record.get("forward_return_pct")) or 0.0) <= tail_loss_pct
        and (_float(row.get("trigger_return_pct")) or 0.0) > tail_loss_pct
    )
    return {
        "trigger_count": len(pairs),
        "labeled_trigger_count": len(labeled_pairs),
        "avg_trigger_return_pct": _avg(trigger_returns),
        "avg_close_return_pct": _avg(close_returns),
        "avg_forward_return_pct": _avg(forward_returns),
        "avg_saved_vs_forward_pct": _avg(saved_vs_forward),
        "avg_missed_vs_forward_pct": _avg(missed_vs_forward),
        "forward_tail_loss_count": sum(1 for value in forward_returns if value <= tail_loss_pct),
        "forward_tail_avoided_count": avoided_forward_tail,
        "paper_trading_only": True,
    }


def _markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Timing Factor Exit Audit",
        "",
        f"As of: `{report.get('as_of')}`",
        f"Snapshot: `{report.get('snapshot_label')}`",
        "",
        "- Paper-only: `True`",
        "- No execution signals: `True`",
        "- Does not modify official scores: `True`",
        "",
        "## Strategy Summary",
        "",
        "| Strategy | Records | Labeled | Triggers | Trigger rate | Avg trigger % | Avg close % | Avg next % | Saved close % | Saved next % | Missed next % | Close tail | Next tail | Avoided next tail |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for strategy_id, item in (report.get("strategies") or {}).items():
        lines.append(
            f"| `{strategy_id}` | {item.get('record_count')} | {item.get('labeled_record_count')} | "
            f"{item.get('trigger_count')} | {item.get('trigger_rate')} | {item.get('avg_trigger_return_pct')} | "
            f"{item.get('avg_close_return_pct')} | {item.get('avg_forward_return_pct')} | "
            f"{item.get('avg_saved_vs_close_pct')} | {item.get('avg_saved_vs_forward_pct')} | "
            f"{item.get('avg_missed_vs_forward_pct')} | {item.get('close_tail_loss_count')} | "
            f"{item.get('forward_tail_loss_count')} | {item.get('forward_tail_avoided_count')} |"
        )
    lines.extend([
        "",
        "## Trigger Factor Summary",
        "",
        "| Factor | Triggers | Labeled | Avg trigger % | Avg next % | Saved next % | Missed next % | Next tail | Avoided next tail |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for factor_id, item in ((report.get("by_trigger_factor") or {}).get("single_factors") or {}).items():
        lines.append(
            f"| `{factor_id}` | {item.get('trigger_count')} | {item.get('labeled_trigger_count')} | "
            f"{item.get('avg_trigger_return_pct')} | {item.get('avg_forward_return_pct')} | "
            f"{item.get('avg_saved_vs_forward_pct')} | {item.get('avg_missed_vs_forward_pct')} | "
            f"{item.get('forward_tail_loss_count')} | {item.get('forward_tail_avoided_count')} |"
        )
    lines.extend(["", "## Guardrails", "", "- Exit triggers are research fields only, not executable sell instructions."])
    return "\n".join(lines) + "\n"


def _avg(values: list[float]) -> float | None:
    return _round(sum(values) / len(values)) if values else None


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit paper-only factor exit strategies")
    parser.add_argument("--records-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--snapshot-label", required=True)
    parser.add_argument("--tail-loss-pct", type=float, default=-5.0)
    args = parser.parse_args(argv)
    result = audit_factor_exit_report(
        records_path=Path(args.records_path),
        output_dir=Path(args.output_dir),
        as_of=args.as_of,
        snapshot_label=args.snapshot_label,
        tail_loss_pct=args.tail_loss_pct,
    )
    print(result["json_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
