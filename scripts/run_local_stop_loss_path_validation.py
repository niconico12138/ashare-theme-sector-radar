#!/usr/bin/env python3
"""Build and validate paper-only post-trigger stop-loss paths."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_timing_strategy_overfit import _load_samples
from theme_sector_radar.data.local_minute_archive import (
    annotate_board_trigger_features,
    read_board_day_bars_batch,
    read_board_name_code_map,
    scan_stock_daily_paths_batch,
)
from theme_sector_radar.reporting.artifact_archive import write_text_preserving_previous
from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import load_strict_json, loads_strict_json
from theme_sector_radar.timing.stop_loss_research import validate_stop_trigger_factor_paths


LEGACY_STOP_TRIGGER_EVENTS_SHA256 = (
    "e92a2fd232cddb2df0abb14b0e8e374ad7a2423f2e1840df6a02d46506ab979a"
)


def run_local_stop_loss_path_validation(
    *,
    stock_archives: list[Path],
    codes: list[str],
    output_dir: Path,
    as_of: str,
    bar_interval: str = "1m",
    board_archive_root: Path | None = None,
    stock_to_board_codes: Mapping[str, list[str]] | None = None,
    board_mapping_metadata: Mapping[str, Any] | None = None,
    horizons: tuple[int, ...] = (5, 15, 30),
    fold_count: int = 5,
    min_signals: int = 30,
) -> dict[str, Any]:
    archive_intervals = {_archive_bar_interval(path) for path in stock_archives}
    if archive_intervals != {bar_interval}:
        raise ValueError(
            f"stock archive bar interval mismatch: declared {bar_interval}, "
            f"detected {sorted(value or 'missing' for value in archive_intervals)}"
        )
    normalized_codes = sorted({str(code).zfill(6) for code in codes if str(code)})
    board_mapping = {
        str(code).zfill(6): [str(board_code) for board_code in board_codes]
        for code, board_codes in (stock_to_board_codes or {}).items()
    }
    rows = []
    stock_archive_identities = []
    used_board_archive_identities: dict[str, dict[str, str]] = {}
    year_record_counts = {}
    year_trigger_counts = {}
    for archive_path in stock_archives:
        with _open_archive_snapshot(archive_path) as (archive_handle, archive_identity):
            batch = scan_stock_daily_paths_batch(
                archive_handle,
                normalized_codes,
                archive_name=archive_path.name,
            )
            stock_archive_identities.append(archive_identity)
        if board_archive_root and board_mapping:
            for identity in _annotate_board_archives(
                batch,
                board_archive_root,
                board_mapping,
            ):
                used_board_archive_identities[identity["path"]] = identity
        year_rows = [
            row
            for code_rows in batch.values()
            for row in code_rows
            if str(row.get("date") or "") <= as_of
        ]
        year = archive_path.stem[:4]
        year_record_counts[year] = len(year_rows)
        year_trigger_counts[year] = sum(bool((row.get("fixed_stop_path") or {}).get("triggered")) for row in year_rows)
        rows.extend(year_rows)
    deduplicated = {}
    for row in rows:
        deduplicated[(str(row.get("date") or ""), str(row.get("code") or ""))] = row
    duplicate_record_count = len(rows) - len(deduplicated)
    rows = list(deduplicated.values())
    observed_codes = {str(row.get("code") or "").zfill(6) for row in rows if str(row.get("code") or "")}
    report = validate_stop_trigger_factor_paths(
        rows,
        horizons=horizons,
        fold_count=fold_count,
        min_signals=min_signals,
    )
    trigger_events = [_compact_trigger_event(row) for row in rows if (row.get("fixed_stop_path") or {}).get("triggered")]
    summary = dict(report.get("summary") or {})
    summary.update(
        {
            "record_count": len(rows),
            "requested_code_count": len(normalized_codes),
            "observed_code_count": len(observed_codes),
            "code_count": len(observed_codes),
            "board_labeled_trigger_count": sum(
                (event.get("trigger_factor_features") or {}).get("board_synchronous_weakness") is not None
                for event in trigger_events
            ),
            "year_record_counts": year_record_counts,
            "year_trigger_counts": year_trigger_counts,
            "duplicate_record_count": duplicate_record_count,
        }
    )
    report.update(
        {
            "as_of": as_of,
            "bar_interval": bar_interval,
            "sample_scope": "unconditional_stock_day_stress",
            "strategy_linked_entry_paths": False,
            "entry_reference_kind": "first_intraday_bar_proxy",
            "stock_archives": [str(path) for path in stock_archives],
            "board_archive_root": str(board_archive_root) if board_archive_root else None,
            "input_archive_identities": {
                "stock_archives": stock_archive_identities,
                "board_archives": [
                    used_board_archive_identities[path]
                    for path in sorted(used_board_archive_identities)
                ],
            },
            "board_mapping": {
                "mapping_kind": "current_static_research_pool",
                "mapped_stock_count": sum(bool(value) for value in board_mapping.values()),
                "metadata": dict(board_mapping_metadata or {}),
                "historical_constituent_membership": False,
            },
            "summary": summary,
        }
    )
    json_path = output_dir / f"local_stop_loss_path_validation_{as_of}.json"
    markdown_path = output_dir / f"local_stop_loss_path_validation_{as_of}.md"
    events_path = output_dir / f"local_stop_loss_trigger_events_{as_of}.jsonl"
    events_payload = _serialize_events(trigger_events)
    report.update(
        {
            "trigger_events_path": str(events_path),
            "trigger_events_sha256": hashlib.sha256(
                events_payload.encode("utf-8")
            ).hexdigest(),
        }
    )
    _validate_stop_report_paper_only(report, context="stop-loss report")
    json_payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    markdown_payload = _markdown(report)
    output_dir.mkdir(parents=True, exist_ok=True)
    archived_events_path = _write_events(events_path, events_payload)
    archived_json_path = write_text_preserving_previous(
        json_path,
        json_payload,
    )
    archived_markdown_path = write_text_preserving_previous(markdown_path, markdown_payload)
    return {
        "status": "ok",
        "json_path": json_path,
        "markdown_path": markdown_path,
        "events_path": events_path,
        "archived_previous_paths": [
            path for path in (archived_events_path, archived_json_path, archived_markdown_path) if path
        ],
        "report": report,
    }


def _archive_bar_interval(path: Path) -> str | None:
    match = re.search(r"_(\d+)min\.zip$", path.name, flags=re.IGNORECASE)
    return f"{int(match.group(1))}m" if match else None


def reaudit_local_stop_loss_path_validation(
    *,
    existing_report_path: Path,
    output_dir: Path,
    as_of: str,
    horizons: tuple[int, ...] = (5, 15, 30),
    fold_count: int = 5,
    min_signals: int = 30,
) -> dict[str, Any]:
    existing = load_strict_json(existing_report_path)
    if "trigger_events" in existing:
        raise ValueError("embedded trigger_events are forbidden; verified JSONL is the only reaudit source")
    trigger_events_path_value = existing.get("trigger_events_path")
    expected_trigger_events_sha256 = str(
        existing.get("trigger_events_sha256") or ""
    ).lower()
    if not trigger_events_path_value or len(expected_trigger_events_sha256) != 64:
        raise ValueError("trigger events path and SHA are required")
    trigger_events_path = Path(str(trigger_events_path_value))
    if not trigger_events_path.is_file():
        raise ValueError(f"trigger events path does not exist: {trigger_events_path}")
    trigger_event_bytes = trigger_events_path.read_bytes()
    trigger_event_sha256 = hashlib.sha256(trigger_event_bytes).hexdigest()
    if trigger_event_sha256 != expected_trigger_events_sha256:
        raise ValueError(
            "trigger events SHA mismatch: "
            f"expected {expected_trigger_events_sha256}, got {trigger_event_sha256}"
        )
    trigger_events = _read_events_bytes(trigger_events_path, trigger_event_bytes)
    legacy_event_guards = trigger_event_sha256 == LEGACY_STOP_TRIGGER_EVENTS_SHA256
    for line_number, event in enumerate(trigger_events, start=1):
        _validate_reaudit_event_paper_only(
            event,
            context=f"trigger event {trigger_events_path}:{line_number}",
            legacy_event_guards=legacy_event_guards,
        )
    validate_no_executable_instructions(existing, context="existing stop-loss report")
    for field in (
        "paper_trading_only",
        "no_execution_signals",
        "does_not_modify_official_scores",
    ):
        if existing.get(field) is not True:
            raise ValueError(f"existing stop-loss report {field} must be true")
    trigger_events = [row for row in trigger_events if str(row.get("date") or "") <= as_of]
    report = validate_stop_trigger_factor_paths(
        trigger_events,
        horizons=horizons,
        fold_count=fold_count,
        min_signals=min_signals,
    )
    preserved = {
        key: value
        for key, value in existing.items()
        if key not in {"schema_version", "parameters", "summary", "baseline", "factors", "trigger_events", "trigger_events_path", "trigger_events_sha256"}
    }
    report.update(preserved)
    report.update(
        {
            "as_of": as_of,
            "source_existing_report_path": str(existing_report_path),
            "summary": dict(report.get("summary") or {}),
        }
    )
    json_path = output_dir / f"local_stop_loss_path_validation_{as_of}.json"
    markdown_path = output_dir / f"local_stop_loss_path_validation_{as_of}.md"
    events_path = output_dir / f"local_stop_loss_trigger_events_{as_of}.jsonl"
    events_payload = _serialize_events(trigger_events)
    report.update(
        {
            "trigger_events_path": str(events_path),
            "trigger_events_sha256": hashlib.sha256(
                events_payload.encode("utf-8")
            ).hexdigest(),
            "sample_scope": existing.get("sample_scope") or "unconditional_stock_day_stress",
            "strategy_linked_entry_paths": False,
            "bar_interval": existing.get("bar_interval") or "1m",
        }
    )
    _validate_stop_report_paper_only(report, context="reaudited stop-loss report")
    json_payload = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    markdown_payload = _markdown(report)
    output_dir.mkdir(parents=True, exist_ok=True)
    archived_events_path = _write_events(events_path, events_payload)
    archived_json_path = write_text_preserving_previous(
        json_path,
        json_payload,
    )
    archived_markdown_path = write_text_preserving_previous(markdown_path, markdown_payload)
    return {
        "status": "ok",
        "json_path": json_path,
        "markdown_path": markdown_path,
        "events_path": events_path,
        "archived_previous_paths": [
            path for path in (archived_events_path, archived_json_path, archived_markdown_path) if path
        ],
        "report": report,
    }


def build_static_stock_board_map(
    *,
    candidate_roots: list[Path],
    selection_validation_root: Path | None,
    board_archive_root: Path,
) -> tuple[list[str], dict[str, list[str]], dict[str, Any]]:
    stock_to_names: dict[str, set[str]] = {}
    for candidate_root in candidate_roots:
        for row in _load_samples(candidate_root, None, None, selection_validation_root):
            code = str(row.get("code") or "").zfill(6)
            if not code:
                continue
            boards = row.get("boards") or row.get("source_boards") or []
            if not isinstance(boards, list):
                boards = [boards]
            stock_to_names.setdefault(code, set()).update(str(board) for board in boards if str(board))
    first_archive = next(iter(sorted(board_archive_root.rglob("*_1min.zip"))), None)
    name_to_code = read_board_name_code_map(first_archive) if first_archive else {}
    mapping = {
        code: sorted({name_to_code[name] for name in names if name in name_to_code})
        for code, names in stock_to_names.items()
    }
    matched_names = sorted({name for names in stock_to_names.values() for name in names if name in name_to_code})
    metadata = {
        "candidate_roots": [str(path) for path in candidate_roots],
        "board_name_count": len({name for names in stock_to_names.values() for name in names}),
        "matched_board_name_count": len(matched_names),
        "matched_board_names": matched_names,
        "mapped_stock_count": sum(bool(value) for value in mapping.values()),
        "board_reference_archive": str(first_archive) if first_archive else None,
        "board_reference_archive_sha256": _sha256(first_archive) if first_archive else None,
    }
    return sorted(stock_to_names), mapping, metadata


def _annotate_board_archives(
    rows_by_code: dict[str, list[dict[str, Any]]],
    board_archive_root: Path,
    stock_to_board_codes: Mapping[str, list[str]],
) -> list[dict[str, str]]:
    archive_by_date = {
        _date_key(path.stem): path
        for path in board_archive_root.rglob("*_1min.zip")
        if len(_date_key(path.stem)) == 8
    }
    dates = sorted(
        {
            str(row.get("date") or "")
            for rows in rows_by_code.values()
            for row in rows
            if (row.get("fixed_stop_path") or {}).get("triggered")
        }
    )
    used_archives: list[dict[str, str]] = []
    for date in dates:
        archive_path = archive_by_date.get(_date_key(date))
        dated_rows = {
            code: [row for row in rows if str(row.get("date") or "") == date]
            for code, rows in rows_by_code.items()
            if any(str(row.get("date") or "") == date and (row.get("fixed_stop_path") or {}).get("triggered") for row in rows)
        }
        board_codes = sorted(
            {
                board_code
                for code in dated_rows
                for board_code in stock_to_board_codes.get(str(code).zfill(6), [])
            }
        )
        if not archive_path or not board_codes:
            continue
        with _open_archive_snapshot(archive_path) as (archive_handle, archive_identity):
            board_bars = read_board_day_bars_batch(archive_handle, board_codes)
            used_archives.append(archive_identity)
        annotate_board_trigger_features(dated_rows, {date: board_bars}, stock_to_board_codes)
    return used_archives


def _compact_trigger_event(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "date": row.get("date"),
        "code": row.get("code"),
        "next_day_return_pct": row.get("next_day_return_pct"),
        "fixed_stop_path": row.get("fixed_stop_path"),
        "trigger_factor_features": row.get("trigger_factor_features"),
        "paper_research_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }


def _serialize_events(events: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(event, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        + "\n"
        for event in events
    )


def _write_events(path: Path, payload: str) -> Path | None:
    return write_text_preserving_previous(path, payload)


def _validate_stop_report_paper_only(
    report: Mapping[str, Any],
    *,
    context: str,
) -> None:
    validate_no_executable_instructions(report, context=context)
    for field in (
        "paper_trading_only",
        "no_execution_signals",
        "does_not_modify_official_scores",
    ):
        if report.get(field) is not True:
            raise ValueError(f"{context} {field} must be true")


def _read_events_bytes(path: Path, payload: bytes) -> list[dict[str, Any]]:
    return [
        loads_strict_json(line, context=f"{path}:{line_number}")
        for line_number, line in enumerate(
            payload.decode("utf-8-sig").splitlines(), start=1
        )
        if line.strip()
    ]


def _validate_reaudit_event_paper_only(
    event: Any,
    *,
    context: str,
    legacy_event_guards: bool,
) -> None:
    if not isinstance(event, Mapping):
        raise ValueError(f"{context} must be a JSON object")
    guarded = dict(event)
    fixed_stop_path = guarded.get("fixed_stop_path")
    if isinstance(fixed_stop_path, Mapping):
        guarded_path = dict(fixed_stop_path)
        if "trigger_price" in guarded_path:
            trigger_price = guarded_path.pop("trigger_price")
            try:
                numeric_trigger = float(trigger_price)
            except (OverflowError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"{context} fixed_stop_path.trigger_price must be a finite positive observation"
                ) from exc
            if (
                isinstance(trigger_price, bool)
                or not math.isfinite(numeric_trigger)
                or numeric_trigger <= 0
            ):
                raise ValueError(
                    f"{context} fixed_stop_path.trigger_price must be a finite positive observation"
                )
        guarded["fixed_stop_path"] = guarded_path
    validate_no_executable_instructions(guarded, context=context)
    if event.get("paper_research_only") is not True:
        raise ValueError(f"{context} paper_research_only must be true")
    for field in ("no_execution_signals", "does_not_modify_official_scores"):
        if event.get(field) is True:
            continue
        if legacy_event_guards and field not in event:
            continue
        raise ValueError(f"{context} {field} must be true")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@contextmanager
def _open_archive_snapshot(path: Path):
    resolved = path.resolve(strict=True)
    with resolved.open("rb") as handle:
        before = os.fstat(handle.fileno())
        digest = hashlib.sha256()
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
        handle.seek(0)
        identity = {"path": str(path), "sha256": digest.hexdigest()}
        yield handle, identity
        after = os.fstat(handle.fileno())
        before_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        )
        after_identity = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        )
        if before_identity != after_identity:
            raise ValueError(f"archive changed while being analyzed: {path}")


def _archive_identity(path: Path) -> dict[str, str]:
    return {"path": str(path), "sha256": _sha256(path)}


def _load_codes(path: Path) -> list[str]:
    data = load_strict_json(path)
    rows = data.get("codes") if isinstance(data, Mapping) else data
    return [str(code) for code in rows or []]


def _load_stock_board_map(path: Path) -> tuple[dict[str, list[str]], dict[str, Any]]:
    data = load_strict_json(path)
    mapping = data.get("stock_to_board_codes") if isinstance(data, Mapping) else data
    metadata = dict(data.get("metadata") or {}) if isinstance(data, Mapping) else {}
    return {str(code).zfill(6): [str(value) for value in values] for code, values in (mapping or {}).items()}, metadata


def _date_key(value: str) -> str:
    return re.sub(r"[^0-9]", "", str(value or ""))[:8]


def _markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# Local Stop-Loss Trigger Path Validation",
        "",
        f"As of: `{report.get('as_of')}`",
        "",
        "- Paper-only: `True`",
        "- Primary label: post-trigger 5/15/30-bar path",
        "- Next-day tail: auxiliary only",
        "- Board membership: current static research-pool mapping, not historical constituents",
        "",
        f"- Stock-days: `{summary.get('record_count')}`",
        f"- Fixed -3% triggers: `{summary.get('triggered_record_count')}`",
        f"- Board-labeled triggers: `{summary.get('board_labeled_trigger_count')}`",
        "",
        "| Factor | Horizon | Signals | Complete | End % | Post MAE % | Post MFE % | Recovery | Tail continuation | Saved drawdown % | Missed recovery % |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for factor_id, factor in (report.get("factors") or {}).items():
        for horizon, item in (factor.get("by_horizon") or {}).items():
            lines.append(
                f"| `{factor_id}` | {horizon} | {item.get('signal_count')} | {item.get('complete_path_count')} | "
                f"{item.get('avg_end_return_from_entry_pct')} | {item.get('avg_post_trigger_mae_pct')} | "
                f"{item.get('avg_post_trigger_mfe_pct')} | {item.get('recovery_rate')} | "
                f"{item.get('continuation_tail_rate')} | {item.get('avg_drawdown_saved_by_next_bar_exit_pct')} | "
                f"{item.get('avg_missed_recovery_pct')} |"
            )
    lines.extend(["", "No result in this report is an executable stop-loss instruction."])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate local paper-only stop-loss trigger paths")
    parser.add_argument("--stock-archive", action="append")
    parser.add_argument("--existing-report")
    parser.add_argument("--codes-json")
    parser.add_argument("--candidate-root", action="append")
    parser.add_argument("--selection-validation-root", default=str(PROJECT_ROOT / "reports" / "selection_validation"))
    parser.add_argument("--board-archive-root")
    parser.add_argument("--stock-board-map")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--bar-interval", default="1m")
    parser.add_argument("--horizon", action="append", type=int)
    parser.add_argument("--fold-count", type=int, default=5)
    parser.add_argument("--min-signals", type=int, default=30)
    args = parser.parse_args(argv)

    if args.existing_report:
        result = reaudit_local_stop_loss_path_validation(
            existing_report_path=Path(args.existing_report),
            output_dir=Path(args.output_dir),
            as_of=args.as_of,
            horizons=tuple(args.horizon or (5, 15, 30)),
            fold_count=args.fold_count,
            min_signals=args.min_signals,
        )
        print(result["json_path"])
        return 0

    if not args.stock_archive:
        parser.error("provide --stock-archive unless --existing-report is used")

    board_root = Path(args.board_archive_root) if args.board_archive_root else None
    mapping_metadata: dict[str, Any] = {}
    stock_to_board_codes: dict[str, list[str]] = {}
    codes = _load_codes(Path(args.codes_json)) if args.codes_json else []
    if args.stock_board_map:
        stock_to_board_codes, mapping_metadata = _load_stock_board_map(Path(args.stock_board_map))
    elif args.candidate_root and board_root:
        derived_codes, stock_to_board_codes, mapping_metadata = build_static_stock_board_map(
            candidate_roots=[Path(path) for path in args.candidate_root],
            selection_validation_root=Path(args.selection_validation_root) if args.selection_validation_root else None,
            board_archive_root=board_root,
        )
        if not codes:
            codes = derived_codes
    if not codes:
        parser.error("provide --codes-json or --candidate-root with --board-archive-root")
    result = run_local_stop_loss_path_validation(
        stock_archives=[Path(path) for path in args.stock_archive],
        codes=codes,
        output_dir=Path(args.output_dir),
        as_of=args.as_of,
        bar_interval=args.bar_interval,
        board_archive_root=board_root,
        stock_to_board_codes=stock_to_board_codes,
        board_mapping_metadata=mapping_metadata,
        horizons=tuple(args.horizon or (5, 15, 30)),
        fold_count=args.fold_count,
        min_signals=args.min_signals,
    )
    print(result["json_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
