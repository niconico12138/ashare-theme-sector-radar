#!/usr/bin/env python3
"""Audit current stop-loss trigger paths under nonstationary windows."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_timing_strategy_overfit import _load_samples
from theme_sector_radar.data.trading_calendar import (
    load_trading_calendar,
    validate_trading_calendar_identity,
)
from theme_sector_radar.reporting.artifact_archive import (
    validate_file_sha256_identity,
    write_text_preserving_previous,
)
from theme_sector_radar.reporting.paper_only_contract import validate_no_executable_instructions
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    loads_strict_json,
)
from theme_sector_radar.data.local_minute_archive import (
    bar_timestamp,
    build_stop_trigger_path_labels,
    detect_bar_interval_minutes,
)
from theme_sector_radar.timing.nonstationary_validation import (
    attach_candidate_date_coverage,
    build_nonstationary_windows,
    current_regime_summary,
    observed_evaluation_tail_markdown_lines,
    observed_evaluation_tail_summary,
)
from theme_sector_radar.timing.candidate_source_identity import revalidate_records_candidate_source_identity
from theme_sector_radar.timing.paper_record_identity import (
    validate_causal_paper_records,
    validate_paper_records_report,
    validate_paper_record_cohort,
)
from theme_sector_radar.timing.selection_source_identity import (
    revalidate_records_selection_source_identity,
)
from theme_sector_radar.timing.stop_loss_research import STOP_FACTOR_IDS, validate_stop_trigger_factor_paths


STOP_ENTRY_VERSION_IDS = (
    "v31_expanded_balanced_tail_guard",
    "v32_expanded_defensive_breakdown_guard",
)
ENTRY_RECORD_VERSION_IDS = (
    "v26_relative_watch_late_surge_cap",
    *STOP_ENTRY_VERSION_IDS,
)
STOP_LONG_HISTORY_SCHEMA_VERSION = "timing_stop_trigger_factor_validation.v1"
STOP_LONG_HISTORY_HORIZONS = (5, 15, 30)
STOP_LONG_HISTORY_FOLD_COUNT = 5
STOP_LONG_HISTORY_MIN_SIGNALS = 30
LEGACY_STOP_TRIGGER_EVENTS_SHA256 = (
    "e92a2fd232cddb2df0abb14b0e8e374ad7a2423f2e1840df6a02d46506ab979a"
)


def build_current_stop_trigger_records(
    samples: Sequence[Mapping[str, Any]],
    *,
    selected_entries: Sequence[Mapping[str, Any]] | None = None,
    as_of: str | None = None,
    timeframe: str,
) -> list[dict[str, Any]]:
    if selected_entries is None:
        raise ValueError("strategy selected entry records are required for stop-path audit")
    interval_minutes = {"1m": 1, "5m": 5}.get(timeframe)
    if interval_minutes is None:
        raise ValueError(f"unsupported stop timeframe: {timeframe}")
    aggregates: dict[str, list[float]] = {}
    selected_map = _selected_entry_map(selected_entries, as_of=as_of)
    source_rows = []
    for (signal_date, code), selected in selected_map.items():
        bars = list(selected.get("entry_bars") or [])
        declared_interval = str(selected.get("bar_interval") or "")
        detected_interval = detect_bar_interval_minutes(bars)
        if declared_interval != timeframe or detected_interval != interval_minutes:
            raise ValueError(
                f"selected entry timeframe mismatch for {signal_date} {code}: "
                f"audit={timeframe}, declared={declared_interval or 'missing'}, detected={detected_interval}m"
            )
        entry = _number(selected.get("entry_reference_price"))
        entry_date = str(selected.get("entry_date") or "")
        if entry is None or not bars:
            continue
        for bar in bars:
            close = _number(bar.get("close")) or _number(bar.get("price"))
            time = bar_timestamp(bar)
            if close is None or not time:
                continue
            key = f"{entry_date}:{time}"
            total_count = aggregates.setdefault(key, [0.0, 0.0])
            total_count[0] += _return_pct(close, entry)
            total_count[1] += 1.0
        source_rows.append((signal_date, entry_date, code, bars, entry, selected))

    prepared = []
    for signal_date, entry_date, code, bars, entry, selected in source_rows:
        path = build_stop_trigger_path_labels(
            bars,
            entry_price=entry,
            bar_interval_minutes=interval_minutes,
        )
        if not path.get("triggered"):
            continue
        snapshot = path.get("trigger_snapshot") or {}
        prepared.append(
            {
                "as_of": signal_date,
                "date": signal_date,
                "entry_date": entry_date,
                "code": code,
                "timing_version_ids": sorted(selected.get("timing_version_ids") or []),
                "strategy_linked_entry": True,
                "entry_reference_is_actual_fill": False,
                "entry_reference_is_causal_simulated_fill": True,
                "entry_reference_kind": "next_session_first_bar_open",
                "boards": selected.get("boards") or [],
                "market_regime_score": selected.get("market_regime_score"),
                "next_day_return_pct": selected.get("selection_forward_return_pct"),
                "fixed_stop_path": path,
                "trigger_factor_features": {
                    "relative_weakness": None,
                    "relative_vs_market_proxy_pct": None,
                    "market_proxy_return_at_trigger_pct": None,
                    "money_flow_deterioration": snapshot.get("money_flow_deterioration"),
                    "board_synchronous_weakness": None,
                    "board_return_at_trigger_pct": None,
                    "matched_board_count": 0,
                },
                "paper_research_only": True,
            }
        )
    for event in prepared:
        path = event["fixed_stop_path"]
        snapshot = path.get("trigger_snapshot") or {}
        stock_return = _number(snapshot.get("close_return_from_entry_pct"))
        key = f"{event['entry_date']}:{path.get('trigger_time') or ''}"
        total, count = aggregates.get(key) or [0.0, 0.0]
        benchmark = (total - stock_return) / (count - 1.0) if stock_return is not None and count > 1 else None
        relative = stock_return - benchmark if stock_return is not None and benchmark is not None else None
        event["trigger_factor_features"].update(
            {
                "relative_weakness": relative <= -1.0 if relative is not None else None,
                "relative_vs_market_proxy_pct": _round(relative),
                "market_proxy_return_at_trigger_pct": _round(benchmark),
                "market_proxy_kind": "equal_weight_candidate_pool_ex_self",
            }
        )
    return prepared


def audit_nonstationary_stop_samples(
    samples: Sequence[Mapping[str, Any]],
    *,
    selected_entries: Sequence[Mapping[str, Any]] | None = None,
    as_of: str | None = None,
    calendar_dates: Sequence[str] | None = None,
    source_document_dates: Sequence[str] | None = None,
    complete_candidate_dates: Sequence[str] | None = None,
    holdout_days: int = 20,
    horizons: tuple[int, ...] = (5, 15, 30),
    fold_count: int = 3,
    min_signals: int = 5,
    long_history_report: Mapping[str, Any] | None = None,
    timeframe: str | None = None,
) -> dict[str, Any]:
    if selected_entries is None:
        raise ValueError("strategy selected entry records are required for stop-path audit")
    events = build_current_stop_trigger_records(
        samples,
        selected_entries=selected_entries,
        as_of=as_of,
        timeframe=timeframe or "",
    )
    selected_count = len(_selected_entry_map(selected_entries, as_of=as_of))
    windows = build_nonstationary_windows(
        events,
        as_of=as_of,
        calendar_dates=calendar_dates,
        holdout_days=holdout_days,
    )
    attach_candidate_date_coverage(
        windows,
        source_document_dates=source_document_dates,
        complete_candidate_dates=complete_candidate_dates,
    )
    validations = {
        window_id: validate_stop_trigger_factor_paths(
            window["records"],
            horizons=horizons,
            fold_count=fold_count,
            min_signals=min_signals,
        )
        for window_id, window in windows.items()
        if isinstance(window, Mapping) and "records" in window
    }
    baseline = {
        "by_window": {
            window_id: _with_window_metadata(validation.get("baseline") or {}, windows[window_id])
            for window_id, validation in validations.items()
        }
    }
    factors = {
        factor_id: {
            "by_window": {
                window_id: _with_factor_data_status(
                    factor_id,
                    _with_window_metadata(
                        (validation.get("factors") or {}).get(factor_id) or {},
                        windows[window_id],
                    ),
                )
                for window_id, validation in validations.items()
            }
        }
        for factor_id in STOP_FACTOR_IDS
    }
    return {
        "schema_version": "timing_nonstationary_stop_exit_audit.v1",
        "holdout_evidence": dict(windows.get("holdout_evidence") or {}),
        "parameters": {
            "holdout_days": holdout_days,
            "horizons": list(horizons),
            "fold_count": fold_count,
            "min_signals": min_signals,
            "primary_label": "post_trigger_path",
            "next_day_tail_is_auxiliary": True,
            "allowed_entry_version_ids": list(STOP_ENTRY_VERSION_IDS),
        },
        "summary": {
            "source_sample_count": len(samples),
            "triggered_record_count": len(events),
            "trigger_date_count": len({event["date"] for event in events}),
            "strategy_linked_entry_count": selected_count,
            "strategy_linked_entry_paths": True,
            "entry_reference_is_actual_fill": False,
            "entry_reference_is_causal_simulated_fill": True,
        },
        "windows": {
            window_id: {key: value for key, value in window.items() if key != "records"}
            for window_id, window in windows.items()
            if isinstance(window, Mapping) and "records" in window
        },
        "baseline": baseline,
        "factors": factors,
        "long_history_veto_evidence": _compact_long_history(long_history_report, timeframe=timeframe),
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }


def audit_nonstationary_stop_exit(
    *,
    candidate_root: Path,
    candidate_source_root: Path,
    selection_validation_root: Path | None,
    output_dir: Path,
    as_of: str,
    timeframe: str,
    entry_records_path: Path,
    trading_calendar_path: Path,
    long_history_report_path: Path | None = None,
    holdout_days: int = 20,
    horizons: tuple[int, ...] = (5, 15, 30),
    fold_count: int = 3,
    min_signals: int = 5,
) -> dict[str, Any]:
    calendar = load_trading_calendar(trading_calendar_path, as_of=as_of)
    candidate_document_snapshots: dict[Path, Mapping[str, Any]] = {}
    selected_entries, source_identity, entry_records_sha256 = _load_entry_records_report(
        entry_records_path,
        as_of=as_of,
        timeframe=timeframe,
        candidate_root=candidate_root,
        candidate_source_root=candidate_source_root,
        candidate_document_snapshots=candidate_document_snapshots,
    )
    validate_trading_calendar_identity(
        source_identity.get("trading_calendar"),
        calendar,
        context="stop entry records",
    )
    source_selection_value = source_identity.get("selection_validation_root")
    source_selection_root = Path(str(source_selection_value)) if source_selection_value else None
    if _resolved_path(source_selection_root) != _resolved_path(selection_validation_root):
        raise ValueError("stop entry records selection root does not match caller selection root")
    source_parameters = source_identity["parameters"]
    selection_document_snapshots: dict[str, Mapping[str, Any]] = {}
    selection_source_identity = revalidate_records_selection_source_identity(
        source_parameters.get("selection_source_identity"),
        selection_validation_root=selection_validation_root,
        start=source_parameters.get("start"),
        end=min(str(source_parameters.get("end") or as_of), as_of),
        context="stop entry records",
        document_snapshots=selection_document_snapshots,
    )
    causal_record_identity = validate_causal_paper_records(
        selected_entries,
        timeframe=timeframe,
        as_of=as_of,
        calendar_dates=calendar["dates"],
        factor_exit_peak_giveback_pct=source_identity["factor_exit_peak_giveback_pct"],
        context="stop entry records",
    )
    samples = _load_samples(
        candidate_root,
        None,
        as_of,
        selection_validation_root,
        candidate_document_snapshots,
        selection_document_snapshots,
    )
    record_cohort_identity = validate_paper_record_cohort(
        selected_entries,
        samples=samples,
        version_ids=source_parameters["version_ids"],
        snapshot_label=str(source_identity.get("snapshot_label") or ""),
        calendar_dates=calendar["dates"],
        start=source_parameters.get("start"),
        end=min(str(source_parameters.get("end") or as_of), as_of),
        concentration_threshold=int(source_parameters.get("concentration_threshold")),
        factor_exit_peak_giveback_pct=float(source_parameters.get("factor_exit_peak_giveback_pct")),
        timeframe=timeframe,
        context="stop entry records",
    )
    source_dates = sorted(
        {
            str(row.get("_sample_date") or row.get("as_of") or "")
            for row in samples
            if not row.get("_sample_mode") and str(row.get("_sample_date") or row.get("as_of") or "")
        }
    )
    if not source_dates:
        raise ValueError("stop audit candidate source has no dated research coverage")
    calendar_dates = [value for value in calendar["dates"] if source_dates[0] <= value <= as_of]
    long_history_report = None
    long_history_report_sha256 = None
    if long_history_report_path:
        long_history_report, long_history_report_sha256 = load_strict_json_with_sha256(
            long_history_report_path
        )
    if long_history_report is not None:
        validate_long_history_identity(long_history_report, timeframe=timeframe)
    report = audit_nonstationary_stop_samples(
        samples,
        selected_entries=selected_entries,
        as_of=as_of,
        calendar_dates=calendar_dates,
        source_document_dates=list((source_identity.get("candidate_source_identity") or {}).get("document_dates") or []),
        complete_candidate_dates=list((source_identity.get("candidate_source_identity") or {}).get("complete_candidate_dates") or []),
        holdout_days=holdout_days,
        horizons=horizons,
        fold_count=fold_count,
        min_signals=min_signals,
        long_history_report=long_history_report,
        timeframe=timeframe,
    )
    report["current_regime"] = current_regime_summary(samples, calendar_dates=calendar_dates)
    report.update(
        {
            "as_of": as_of,
            "timeframe": timeframe,
            "candidate_root": str(candidate_root),
            "entry_records_path": str(entry_records_path),
            "entry_records_sha256": entry_records_sha256,
            "source_as_of": source_identity["as_of"],
            "source_bar_interval": source_identity["bar_interval"],
            "source_bar_source": source_identity["bar_source"],
            "source_paper_trading_only": source_identity["paper_trading_only"],
            "candidate_source_identity": source_identity["candidate_source_identity"],
            "selection_source_identity": selection_source_identity,
            "causal_record_identity": causal_record_identity,
            "record_cohort_identity": record_cohort_identity,
            "calendar_source": calendar,
            "long_history_report_path": str(long_history_report_path) if long_history_report_path else None,
            "long_history_report_sha256": long_history_report_sha256,
        }
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"nonstationary_stop_exit_audit_{as_of}.json"
    markdown_path = output_dir / f"nonstationary_stop_exit_audit_{as_of}.md"
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


def _with_window_metadata(item: Mapping[str, Any], window: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(item)
    result.update({"window_status": window.get("status"), "window_date_count": window.get("date_count")})
    return result


def _with_factor_data_status(factor_id: str, item: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(item)
    eligible_count = int(result.get("eligible_count") or 0)
    if factor_id == "board_synchronous_weakness" and eligible_count == 0:
        result.update(
            {
                "data_status": "data_unavailable",
                "data_reason": "causal_board_minute_series_not_supplied",
            }
        )
    else:
        result.update(
            {
                "data_status": "available" if eligible_count else "insufficient_sample",
                "data_reason": None if eligible_count else "no_eligible_factor_observations",
            }
        )
    return result


def _selected_entry_map(
    selected_entries: Sequence[Mapping[str, Any]] | None,
    *,
    as_of: str | None,
) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in selected_entries or []:
        row = dict(raw)
        version_id = str(row.get("timing_version_id") or "")
        if version_id not in STOP_ENTRY_VERSION_IDS:
            continue
        date = str(row.get("as_of") or row.get("_sample_date") or row.get("date") or "")
        entry_date = str(row.get("entry_date") or "")
        code = str(row.get("code") or "")
        if (
            not date
            or not entry_date
            or not code
            or row.get("causal_entry_valid") is not True
            or entry_date <= date
            or (as_of and (date > as_of or entry_date > as_of))
        ):
            continue
        entry_bars = [dict(bar) for bar in row.get("entry_bars") or [] if isinstance(bar, Mapping)]
        entry_reference = _number((row.get("path_stats") or {}).get("entry_reference_price"))
        signature = json.dumps(
            {"entry_date": entry_date, "entry_reference_price": entry_reference, "entry_bars": entry_bars},
            ensure_ascii=False,
            sort_keys=True,
        )
        item = result.get((date, code))
        if item is None:
            factor_snapshot = row.get("factor_snapshot") or {}
            item = {
                "entry_date": entry_date,
                "entry_reference_price": entry_reference,
                "entry_bars": entry_bars,
                "boards": list(row.get("boards") or []),
                "selection_forward_return_pct": row.get("selection_forward_return_pct"),
                "market_regime_score": factor_snapshot.get("market_regime_score"),
                "bar_interval": (row.get("execution_assumptions") or {}).get("bar_interval"),
                "timing_version_ids": set(),
                "_path_signature": signature,
            }
            result[(date, code)] = item
        elif item.get("_path_signature") != signature:
            raise ValueError(f"duplicate selected entry path conflict for {date} {code}")
        item["timing_version_ids"].add(version_id)
    return result


def _load_entry_records_report(
    path: Path,
    *,
    as_of: str,
    timeframe: str,
    candidate_root: Path,
    candidate_source_root: Path,
    candidate_document_snapshots: dict[Path, Mapping[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    data, records_sha256 = load_strict_json_with_sha256(path)
    if not isinstance(data, Mapping):
        raise ValueError("stop entry records report must be a JSON object")
    validate_paper_records_report(
        data,
        context="stop entry records report",
        require_durable_entry_bars_source=True,
    )
    if data.get("paper_trading_only") is not True or data.get("no_execution_signals") is not True:
        raise ValueError("stop entry records report must be paper-only with no execution signals")
    source_as_of = str(data.get("as_of") or "")
    if source_as_of != as_of:
        raise ValueError(f"stop entry records as_of mismatch: expected {as_of}, got {source_as_of or 'missing'}")
    source_interval = str(data.get("bar_interval") or "")
    if source_interval != timeframe:
        raise ValueError(
            f"stop entry records timeframe mismatch: expected {timeframe}, got {source_interval or 'missing'}"
        )
    expected_bar_source = {
        "1m": "complete_1m_session",
        "5m": "aggregated_from_complete_1m_session",
    }.get(timeframe)
    if not expected_bar_source:
        raise ValueError(f"unsupported stop timeframe: {timeframe}")
    source_bar_source = str(data.get("bar_source") or "")
    if source_bar_source != expected_bar_source:
        raise ValueError(
            f"stop entry records bar source mismatch: expected {expected_bar_source}, "
            f"got {source_bar_source or 'missing'}"
        )
    parameters = data.get("parameters") or {}
    source_versions = list(parameters.get("version_ids") or []) if isinstance(parameters, Mapping) else []
    if len(source_versions) != len(ENTRY_RECORD_VERSION_IDS) or set(source_versions) != set(ENTRY_RECORD_VERSION_IDS):
        raise ValueError(
            "stop entry records must contain the exact upstream strategy versions: "
            + ", ".join(ENTRY_RECORD_VERSION_IDS)
        )
    source_selection = parameters.get("selection_validation_root") if isinstance(parameters, Mapping) else None
    candidate_source_identity = revalidate_records_candidate_source_identity(
        parameters.get("candidate_source_identity") if isinstance(parameters, Mapping) else None,
        candidate_root=candidate_root,
        source_root=candidate_source_root,
        timeframe=timeframe,
        start=parameters.get("start") if isinstance(parameters, Mapping) else None,
        end=min(str(parameters.get("end") or as_of), as_of) if isinstance(parameters, Mapping) else as_of,
        context="stop entry records",
        document_snapshots=candidate_document_snapshots,
    )
    rows = data.get("records")
    if not isinstance(rows, list):
        raise ValueError("stop entry records report must contain a records list")
    identity = {
        "as_of": source_as_of,
        "snapshot_label": str(data.get("snapshot_label") or ""),
        "bar_interval": source_interval,
        "bar_source": source_bar_source,
        "paper_trading_only": True,
        "no_execution_signals": True,
        "candidate_source_identity": candidate_source_identity,
        "factor_exit_peak_giveback_pct": parameters.get("factor_exit_peak_giveback_pct"),
        "selection_validation_root": source_selection,
        "trading_calendar": data.get("trading_calendar"),
        "parameters": dict(parameters),
    }
    return [dict(row) for row in rows if isinstance(row, Mapping)], identity, records_sha256


def validate_long_history_identity(report: Mapping[str, Any], *, timeframe: str) -> dict[str, Any]:
    validate_no_executable_instructions(report, context="long-history report")
    if report.get("schema_version") != STOP_LONG_HISTORY_SCHEMA_VERSION:
        raise ValueError("long-history schema identity mismatch")
    if (
        report.get("paper_trading_only") is not True
        or report.get("no_execution_signals") is not True
        or report.get("does_not_modify_official_scores") is not True
    ):
        raise ValueError("long-history report must have strict paper-only identity")
    interval = str(report.get("bar_interval") or "")
    if interval != timeframe:
        raise ValueError(f"long-history bar interval {interval or 'missing'} does not match stop timeframe {timeframe}")
    trigger_events_identity = validate_file_sha256_identity(
        report.get("trigger_events_path"),
        report.get("trigger_events_sha256"),
        context="trigger events",
    )
    strategy_linked_claimed = report.get("strategy_linked_entry_paths") is True
    parameters = report.get("parameters") or {}
    versions = list(parameters.get("version_ids") or []) if isinstance(parameters, Mapping) else []
    strategy_envelope_valid = (
        strategy_linked_claimed
        and report.get("entry_model") == "next_trading_session_first_bar_open"
        and len(versions) == len(STOP_ENTRY_VERSION_IDS)
        and set(versions) == set(STOP_ENTRY_VERSION_IDS)
    )
    reason = None
    if strategy_linked_claimed:
        reason = (
            "strategy_linked_external_anchors_unavailable"
            if strategy_envelope_valid
            else "strategy_linked_envelope_identity_unverifiable"
        )
    return {
        "status": "auxiliary_only",
        "eligible_as_long_history_veto": False,
        "reason": reason,
        "sample_scope": report.get("sample_scope"),
        "bar_interval": interval,
        "trigger_events_path": trigger_events_identity["path"],
        "trigger_events_sha256": trigger_events_identity["sha256"],
    }


def _compact_long_history(report: Mapping[str, Any] | None, *, timeframe: str | None) -> dict[str, Any]:
    if report is None:
        return {"status": "not_evaluated", "source": None}
    identity = validate_long_history_identity(report, timeframe=timeframe or str(report.get("bar_interval") or ""))
    if "trigger_events" in report:
        raise ValueError("embedded trigger_events are forbidden; verified JSONL is the only stop-audit source")
    event_path = Path(identity["trigger_events_path"])
    event_bytes = event_path.read_bytes()
    event_sha256 = hashlib.sha256(event_bytes).hexdigest()
    if event_sha256 != identity["trigger_events_sha256"]:
        raise ValueError(
            "trigger events SHA mismatch while binding bytes for stop-audit recomputation"
        )
    legacy_event_guards = event_sha256 == LEGACY_STOP_TRIGGER_EVENTS_SHA256
    events = []
    for line_number, line in enumerate(
        event_bytes.decode("utf-8-sig").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        row = loads_strict_json(line, context=f"{event_path}:{line_number}")
        if not isinstance(row, Mapping):
            raise ValueError(f"long-history trigger event must be a JSON object: {event_path}:{line_number}")
        _validate_long_history_event_paper_only(
            row,
            context=f"long-history trigger event {event_path}:{line_number}",
        )
        if row.get("paper_research_only") is not True:
            raise ValueError(
                f"long-history event paper_research_only must be true: {event_path}:{line_number}"
            )
        for field in ("no_execution_signals", "does_not_modify_official_scores"):
            if row.get(field) is True:
                continue
            if legacy_event_guards and field not in row:
                continue
            if row.get(field) is not True:
                raise ValueError(
                    f"long-history event {field} must be true: {event_path}:{line_number}"
                )
        events.append(dict(row))
    recomputed = validate_stop_trigger_factor_paths(
        events,
        horizons=STOP_LONG_HISTORY_HORIZONS,
        fold_count=STOP_LONG_HISTORY_FOLD_COUNT,
        min_signals=STOP_LONG_HISTORY_MIN_SIGNALS,
    )
    return {
        **identity,
        "summary": recomputed.get("summary"),
        "parameters": recomputed.get("parameters"),
        "baseline": recomputed.get("baseline"),
        "factors": recomputed.get("factors"),
        "board_mapping": report.get("board_mapping"),
    }


def _validate_long_history_event_paper_only(
    row: Mapping[str, Any],
    *,
    context: str,
) -> None:
    guarded = dict(row)
    fixed_stop_path = guarded.get("fixed_stop_path")
    if isinstance(fixed_stop_path, Mapping):
        guarded_path = dict(fixed_stop_path)
        if "trigger_price" in guarded_path:
            trigger_price = guarded_path.pop("trigger_price")
            numeric_trigger = _number(trigger_price)
            if (
                isinstance(trigger_price, bool)
                or numeric_trigger is None
                or numeric_trigger <= 0
            ):
                raise ValueError(
                    f"{context} fixed_stop_path.trigger_price must be a finite positive observation"
                )
        guarded["fixed_stop_path"] = guarded_path
    validate_no_executable_instructions(guarded, context=context)


def _markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    tail = observed_evaluation_tail_summary(report, allow_short_window=True)
    lines = [
        "# Nonstationary Stop Exit Audit",
        "",
        f"- As of: `{report.get('as_of')}`",
        f"- Timeframe: `{report.get('timeframe')}`",
        f"- Source samples: `{summary.get('source_sample_count')}`",
        f"- Fixed -3% triggers: `{summary.get('triggered_record_count')}`",
        f"- Trigger dates: `{summary.get('trigger_date_count')}`",
        "- Paper-only: `True`",
    ]
    lines.extend(observed_evaluation_tail_markdown_lines(tail))
    lines.extend(
        [
            "",
            "| Factor | Window | Status | Dates | Eligible | Signal rate | 5-bar tail | 15-bar tail | 30-bar tail |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for factor_id, factor in (report.get("factors") or {}).items():
        for window_id in ("recent_60", "recent_120", "holdout", "all_history"):
            item = (factor.get("by_window") or {}).get(window_id) or {}
            by_horizon = item.get("by_horizon") or {}
            display_window_id = "observed_evaluation_tail" if window_id == "holdout" else window_id
            lines.append(
                f"| `{factor_id}` | `{display_window_id}` | {item.get('window_status')} | {item.get('window_date_count')} | "
                f"{item.get('eligible_count')} | {item.get('signal_rate_within_eligible')} | "
                f"{(by_horizon.get('5') or {}).get('continuation_tail_rate')} | "
                f"{(by_horizon.get('15') or {}).get('continuation_tail_rate')} | "
                f"{(by_horizon.get('30') or {}).get('continuation_tail_rate')} |"
            )
    lines.extend(["", "No output is an executable stop-loss instruction."])
    return "\n".join(lines) + "\n"


def _first_price(bars: list[dict[str, Any]]) -> float | None:
    for bar in bars:
        value = _number(bar.get("close")) or _number(bar.get("price")) or _number(bar.get("open"))
        if value is not None and value > 0:
            return value
    return None


def _return_pct(price: float, reference: float) -> float:
    return (price - reference) / reference * 100.0


def _number(value: Any) -> float | None:
    try:
        number = float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None
    return number if number is not None and math.isfinite(number) else None


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def _resolved_path(path: Path | None) -> str | None:
    return str(path.resolve()) if path is not None else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit current paper-only stop paths")
    parser.add_argument("--candidate-root", required=True)
    parser.add_argument("--candidate-source-root", required=True)
    parser.add_argument("--selection-validation-root", default=str(PROJECT_ROOT / "reports" / "selection_validation"))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--entry-records-path", required=True)
    parser.add_argument("--trading-calendar-path", required=True)
    parser.add_argument("--long-history-report")
    parser.add_argument("--holdout-days", type=int, default=20)
    parser.add_argument("--horizon", action="append", type=int)
    parser.add_argument("--fold-count", type=int, default=3)
    parser.add_argument("--min-signals", type=int, default=5)
    args = parser.parse_args(argv)
    result = audit_nonstationary_stop_exit(
        candidate_root=Path(args.candidate_root),
        candidate_source_root=Path(args.candidate_source_root),
        selection_validation_root=Path(args.selection_validation_root) if args.selection_validation_root else None,
        output_dir=Path(args.output_dir),
        as_of=args.as_of,
        timeframe=args.timeframe,
        entry_records_path=Path(args.entry_records_path),
        trading_calendar_path=Path(args.trading_calendar_path),
        long_history_report_path=Path(args.long_history_report) if args.long_history_report else None,
        holdout_days=args.holdout_days,
        horizons=tuple(args.horizon or (5, 15, 30)),
        fold_count=args.fold_count,
        min_signals=args.min_signals,
    )
    print(result["json_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
