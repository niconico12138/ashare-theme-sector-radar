#!/usr/bin/env python3
"""Audit paper-only profit exits under nonstationary time windows."""

from __future__ import annotations

import argparse
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
from theme_sector_radar.reporting.artifact_archive import write_text_preserving_previous
from theme_sector_radar.reporting.strict_json import load_strict_json_with_sha256
from theme_sector_radar.timing.exit_validation import validate_dual_exit_records
from theme_sector_radar.timing.candidate_source_identity import revalidate_records_candidate_source_identity
from theme_sector_radar.timing.nonstationary_validation import (
    attach_candidate_date_coverage,
    build_nonstationary_windows,
    current_regime_summary,
    group_by_regime,
    observed_evaluation_tail_markdown_lines,
    observed_evaluation_tail_summary,
)
from theme_sector_radar.timing.paper_record_identity import (
    validate_causal_paper_records,
    validate_paper_records_report,
    validate_paper_record_cohort,
)
from theme_sector_radar.timing.selection_source_identity import (
    revalidate_records_selection_source_identity,
)


PROFIT_CANDIDATE_IDS = (
    "paper_fixed_exit_baseline",
    "paper_take_profit_protect_candidate",
)
DECLARED_GIVEBACK_CANDIDATES_PCT = (2.0, 3.0)
PROFIT_ENTRY_VERSION_IDS = (
    "v31_expanded_balanced_tail_guard",
    "v32_expanded_defensive_breakdown_guard",
)


def audit_nonstationary_profit_records(
    records: Sequence[Mapping[str, Any]],
    *,
    holdout_days: int = 20,
    recent_windows: tuple[int, ...] = (60, 120),
    as_of: str | None = None,
    calendar_dates: Sequence[str] | None = None,
    source_document_dates: Sequence[str] | None = None,
    complete_candidate_dates: Sequence[str] | None = None,
    fold_count: int = 3,
    min_labeled_triggers: int = 5,
    tail_loss_pct: float = -5.0,
    applied_giveback_pct: float | None = None,
    round_trip_cost_pct: float = 0.1,
    long_history_records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if applied_giveback_pct is not None and applied_giveback_pct not in DECLARED_GIVEBACK_CANDIDATES_PCT:
        raise ValueError(f"applied giveback must be one of the declared giveback candidates: {DECLARED_GIVEBACK_CANDIDATES_PCT}")
    rows = [_with_regime(dict(row)) for row in records if isinstance(row, Mapping)]
    windows = build_nonstationary_windows(
        rows,
        as_of=as_of,
        calendar_dates=calendar_dates,
        holdout_days=holdout_days,
        recent_windows=recent_windows,
    )
    attach_candidate_date_coverage(
        windows,
        source_document_dates=source_document_dates,
        complete_candidate_dates=complete_candidate_dates,
    )
    validations = {
        window_id: validate_dual_exit_records(
            window["records"],
            fold_count=fold_count,
            min_labeled_triggers=min_labeled_triggers,
            tail_loss_pct=tail_loss_pct,
        )
        for window_id, window in windows.items()
        if isinstance(window, Mapping) and "records" in window
    }
    recent_rows = (windows.get("recent_120") or {}).get("records") or []
    regimes = group_by_regime(recent_rows)
    candidates: dict[str, Any] = {}
    for candidate_id in PROFIT_CANDIDATE_IDS:
        by_window = {
            window_id: _window_candidate_summary(
                window=windows[window_id],
                validation=validation,
                candidate_id=candidate_id,
                tail_loss_pct=tail_loss_pct,
            )
            for window_id, validation in validations.items()
        }
        candidates[candidate_id] = {
            "by_window": by_window,
            "paired_vs_fixed_by_window": {
                window_id: _paired_policy_summary(
                    windows[window_id].get("records") or [],
                    candidate_id,
                    round_trip_cost_pct=round_trip_cost_pct,
                    tail_loss_pct=tail_loss_pct,
                )
                for window_id in validations
            },
            "fold_stability": _paired_fold_stability(
                recent_rows,
                candidate_id,
                fold_count=fold_count,
                min_pairs=min_labeled_triggers,
                round_trip_cost_pct=round_trip_cost_pct,
                tail_loss_pct=tail_loss_pct,
            ),
            "by_regime": {
                regime: _paired_policy_summary(
                    regime_rows,
                    candidate_id,
                    round_trip_cost_pct=round_trip_cost_pct,
                    tail_loss_pct=tail_loss_pct,
                )
                for regime, regime_rows in regimes.items()
            },
            "long_history_veto": _long_history_veto(
                long_history_records,
                candidate_id,
                fold_count=fold_count,
                min_labeled_triggers=min_labeled_triggers,
                tail_loss_pct=tail_loss_pct,
                round_trip_cost_pct=round_trip_cost_pct,
            ),
        }
    _attach_baseline_deltas(candidates)
    return {
        "schema_version": "timing_nonstationary_profit_exit_audit.v1",
        "holdout_evidence": dict(windows.get("holdout_evidence") or {}),
        "parameters": {
            "holdout_days": holdout_days,
            "fold_count": fold_count,
            "min_labeled_triggers": min_labeled_triggers,
            "tail_loss_pct": tail_loss_pct,
            "declared_giveback_candidates_pct": list(DECLARED_GIVEBACK_CANDIDATES_PCT),
            "applied_giveback_pct": applied_giveback_pct,
            "continuous_threshold_search": False,
            "round_trip_cost_pct": round_trip_cost_pct,
        },
        "windows": {
            window_id: {key: value for key, value in window.items() if key != "records"}
            for window_id, window in windows.items()
            if isinstance(window, Mapping) and "records" in window
        },
        "candidates": candidates,
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }


def audit_nonstationary_profit_exit(
    *,
    records_path: Path,
    candidate_root: Path,
    candidate_source_root: Path,
    selection_validation_root: Path | None,
    trading_calendar_path: Path,
    output_dir: Path,
    as_of: str,
    snapshot_label: str,
    timeframe: str,
    applied_giveback_pct: float | None = None,
    round_trip_cost_pct: float = 0.1,
    long_history_records_path: Path | None = None,
    long_history_trading_calendar_path: Path | None = None,
    long_history_candidate_root: Path | None = None,
    long_history_candidate_source_root: Path | None = None,
    long_history_selection_validation_root: Path | None = None,
    holdout_days: int = 20,
    fold_count: int = 3,
    min_labeled_triggers: int = 5,
    tail_loss_pct: float = -5.0,
) -> dict[str, Any]:
    records, source_parameters, source_identity, records_sha256 = _load_records(records_path)
    if source_identity.get("paper_trading_only") is not True or source_identity.get("no_execution_signals") is not True:
        raise ValueError("profit source records must be paper-only with no execution signals")
    calendar = load_trading_calendar(trading_calendar_path, as_of=as_of)
    validate_trading_calendar_identity(
        source_identity.get("trading_calendar"),
        calendar,
        context="profit records",
    )
    long_history_records = None
    long_history_source = {
        "status": "not_supplied",
        "path": None,
        "sha256": None,
    }
    if long_history_records_path:
        (
            loaded_long_history_records,
            long_history_parameters,
            long_history_identity,
            _long_history_records_sha256,
        ) = _load_records(long_history_records_path)
        long_history_source = validate_profit_long_history_identity(
            long_history_identity,
            parameters=long_history_parameters,
            timeframe=timeframe,
            expected_version_ids=source_parameters.get("version_ids") or [],
        )
        causal_long_history = validate_profit_long_history_records(
            loaded_long_history_records,
            identity=long_history_identity,
            parameters=long_history_parameters,
            timeframe=timeframe,
            expected_version_ids=PROFIT_ENTRY_VERSION_IDS,
            trading_calendar_path=long_history_trading_calendar_path,
            candidate_root=long_history_candidate_root,
            candidate_source_root=long_history_candidate_source_root,
            selection_validation_root=long_history_selection_validation_root,
        )
        long_history_source.update(causal_long_history)
        if causal_long_history["status"] == "validated_strategy_linked":
            long_history_records = loaded_long_history_records
        long_history_source.update(
            {
                "path": str(long_history_records_path),
                "sha256": _long_history_records_sha256,
            }
        )
    if applied_giveback_pct is None:
        applied_giveback_pct = _float(source_parameters.get("factor_exit_peak_giveback_pct"))
    source_giveback = _float(source_parameters.get("factor_exit_peak_giveback_pct"))
    if source_giveback is not None and source_giveback != applied_giveback_pct:
        raise ValueError(f"applied giveback {applied_giveback_pct} does not match source records {source_giveback}")
    source_as_of = str(source_identity.get("as_of") or "")
    if source_as_of != as_of:
        raise ValueError(f"source records as_of mismatch: expected {as_of}, got {source_as_of or 'missing'}")
    source_snapshot_label = str(source_identity.get("snapshot_label") or "")
    source_bar_interval = str(source_identity.get("bar_interval") or "")
    source_bar_source = str(source_identity.get("bar_source") or "")
    if source_bar_interval != timeframe:
        raise ValueError(
            f"source records timeframe mismatch: expected {timeframe}, "
            f"got {source_bar_interval or 'missing'}"
        )
    expected_bar_source = {
        "1m": "complete_1m_session",
        "5m": "aggregated_from_complete_1m_session",
    }.get(timeframe)
    if source_bar_source != expected_bar_source:
        raise ValueError(
            f"source records bar source mismatch: expected {expected_bar_source}, got {source_bar_source or 'missing'}"
        )
    normalized_snapshot_label = _cohort_snapshot_label(source_snapshot_label, applied_giveback_pct)
    if not source_snapshot_label or normalized_snapshot_label != snapshot_label:
        raise ValueError(
            f"source records snapshot mismatch: expected cohort {snapshot_label}, "
            f"got {source_snapshot_label or 'missing'}"
        )
    source_candidate_root = Path(str(source_parameters.get("candidate_root") or ""))
    if source_candidate_root.resolve() != candidate_root.resolve():
        raise ValueError("profit records candidate root does not match caller candidate root")
    selection_value = source_parameters.get("selection_validation_root")
    source_selection_root = Path(str(selection_value)) if selection_value else None
    if _resolved_path(source_selection_root) != _resolved_path(selection_validation_root):
        raise ValueError("profit records selection root does not match caller selection root")
    source_versions = list(source_parameters.get("version_ids") or [])
    if len(source_versions) != len(PROFIT_ENTRY_VERSION_IDS) or set(source_versions) != set(PROFIT_ENTRY_VERSION_IDS):
        raise ValueError(
            "profit records must contain the exact strategy versions: " + ", ".join(PROFIT_ENTRY_VERSION_IDS)
        )
    candidate_document_snapshots: dict[Path, Mapping[str, Any]] = {}
    candidate_source_identity = revalidate_records_candidate_source_identity(
        source_parameters.get("candidate_source_identity"),
        candidate_root=candidate_root,
        source_root=candidate_source_root,
        timeframe=timeframe,
        start=source_parameters.get("start"),
        end=min(str(source_parameters.get("end") or as_of), as_of),
        context="profit records",
        document_snapshots=candidate_document_snapshots,
    )
    selection_document_snapshots: dict[str, Mapping[str, Any]] = {}
    selection_source_identity = revalidate_records_selection_source_identity(
        source_parameters.get("selection_source_identity"),
        selection_validation_root=selection_validation_root,
        start=source_parameters.get("start"),
        end=min(str(source_parameters.get("end") or as_of), as_of),
        context="profit records",
        document_snapshots=selection_document_snapshots,
    )
    causal_record_identity = validate_causal_paper_records(
        records,
        timeframe=timeframe,
        as_of=as_of,
        calendar_dates=calendar["dates"],
        factor_exit_peak_giveback_pct=applied_giveback_pct,
        context="profit records",
    )
    selection_root = selection_validation_root
    source_dates = []
    calendar_samples = []
    if candidate_root.exists():
        calendar_samples = _load_samples(
            candidate_root,
            None,
            as_of,
            selection_root,
            candidate_document_snapshots,
            selection_document_snapshots,
        )
        source_dates = sorted(
            {
                str(row.get("_sample_date") or row.get("as_of") or "")
                for row in calendar_samples
                if not row.get("_sample_mode") and str(row.get("_sample_date") or row.get("as_of") or "")
            }
        )
    if not source_dates:
        source_dates = sorted(
            {
                str(row.get("signal_date") or row.get("as_of") or "")
                for row in records
                if str(row.get("signal_date") or row.get("as_of") or "")
            }
        )
    if not source_dates:
        raise ValueError("profit audit source has no dated research coverage")
    record_cohort_identity = validate_paper_record_cohort(
        records,
        samples=calendar_samples,
        version_ids=PROFIT_ENTRY_VERSION_IDS,
        snapshot_label=source_snapshot_label,
        calendar_dates=calendar["dates"],
        start=source_parameters.get("start"),
        end=min(str(source_parameters.get("end") or as_of), as_of),
        concentration_threshold=int(source_parameters.get("concentration_threshold")),
        factor_exit_peak_giveback_pct=float(applied_giveback_pct),
        timeframe=timeframe,
        context="profit records",
    )
    calendar_dates = [value for value in calendar["dates"] if source_dates[0] <= value <= as_of]
    report = audit_nonstationary_profit_records(
        records,
        as_of=as_of,
        calendar_dates=calendar_dates,
        source_document_dates=list(candidate_source_identity.get("document_dates") or []),
        complete_candidate_dates=list(candidate_source_identity.get("complete_candidate_dates") or []),
        holdout_days=holdout_days,
        fold_count=fold_count,
        min_labeled_triggers=min_labeled_triggers,
        tail_loss_pct=tail_loss_pct,
        applied_giveback_pct=applied_giveback_pct,
        round_trip_cost_pct=round_trip_cost_pct,
        long_history_records=long_history_records,
    )
    report["current_regime"] = current_regime_summary(
        calendar_samples or records,
        calendar_dates=calendar_dates,
    )
    report.update(
        {
            "as_of": as_of,
            "snapshot_label": snapshot_label,
            "source_snapshot_label": source_snapshot_label,
            "source_as_of": source_as_of,
            "source_bar_interval": source_bar_interval,
            "source_bar_source": source_bar_source,
            "timeframe": timeframe,
            "records_path": str(records_path),
            "records_sha256": records_sha256,
            "calendar_source": calendar,
            "candidate_source": {
                "candidate_root": str(candidate_root),
                "selection_validation_root": str(selection_root) if selection_root else None,
                "start": source_parameters.get("start"),
                "end": source_parameters.get("end"),
                "version_ids": list(source_parameters.get("version_ids") or []),
                "source_snapshot_base": normalized_snapshot_label,
                "bar_interval": source_bar_interval,
                "candidate_source_identity": candidate_source_identity,
                "selection_source_identity": selection_source_identity,
            },
            "long_history_records_path": str(long_history_records_path) if long_history_records_path else None,
            "long_history_source": long_history_source,
            "causal_record_identity": causal_record_identity,
            "record_cohort_identity": record_cohort_identity,
        }
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_giveback_{applied_giveback_pct:g}pct" if applied_giveback_pct is not None else ""
    json_path = output_dir / f"nonstationary_profit_exit_audit_{as_of}_{snapshot_label}{suffix}.json"
    markdown_path = output_dir / f"nonstationary_profit_exit_audit_{as_of}_{snapshot_label}{suffix}.md"
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


def _window_candidate_summary(
    *,
    window: Mapping[str, Any],
    validation: Mapping[str, Any],
    candidate_id: str,
    tail_loss_pct: float,
) -> dict[str, Any]:
    candidate = ((validation.get("candidates") or {}).get(candidate_id) or {})
    summary = dict(candidate.get("summary") or {})
    summary.update(_extra_exit_metrics(window.get("records") or [], candidate_id, tail_loss_pct=tail_loss_pct))
    summary.update(
        {
            "window_status": window.get("status"),
            "window_date_count": window.get("date_count"),
            "concentration": candidate.get("concentration") or {},
        }
    )
    return summary


def _candidate_summary(
    rows: Sequence[Mapping[str, Any]],
    candidate_id: str,
    *,
    fold_count: int,
    min_labeled_triggers: int,
    tail_loss_pct: float,
) -> dict[str, Any]:
    report = validate_dual_exit_records(
        rows,
        fold_count=fold_count,
        min_labeled_triggers=min_labeled_triggers,
        tail_loss_pct=tail_loss_pct,
    )
    candidate = (report.get("candidates") or {}).get(candidate_id) or {}
    summary = dict(candidate.get("summary") or {})
    summary.update(_extra_exit_metrics(rows, candidate_id, tail_loss_pct=tail_loss_pct))
    return summary


def _extra_exit_metrics(
    rows: Sequence[Mapping[str, Any]],
    candidate_id: str,
    *,
    tail_loss_pct: float,
) -> dict[str, Any]:
    triggered = []
    filled = []
    for row in rows:
        candidate = ((row.get("paper_exit_candidates") or {}).get(candidate_id) or {})
        if not isinstance(candidate, Mapping) or not candidate.get("triggered"):
            continue
        triggered.append(candidate)
        exit_return = _float(candidate.get("simulated_exit_return_pct"))
        if candidate.get("fill_available") and exit_return is not None:
            filled.append(exit_return)
    return {
        "next_bar_fill_rate": _round(len(filled) / len(triggered)) if triggered else None,
        "simulated_exit_tail_loss_count": sum(value <= tail_loss_pct for value in filled),
        "simulated_exit_tail_loss_rate": _round(sum(value <= tail_loss_pct for value in filled) / len(filled)) if filled else None,
    }


def _paired_policy_summary(
    rows: Sequence[Mapping[str, Any]],
    candidate_id: str,
    *,
    round_trip_cost_pct: float,
    tail_loss_pct: float,
) -> dict[str, Any]:
    deduplicated, duplicate_count, conflict_count = _deduplicate_entries(rows)
    pairs = []
    for row in deduplicated:
        candidate_return = _policy_return(row, candidate_id, round_trip_cost_pct=round_trip_cost_pct)
        fixed_return = _policy_return(row, "paper_fixed_exit_baseline", round_trip_cost_pct=round_trip_cost_pct)
        if candidate_return is not None and fixed_return is not None:
            pairs.append((candidate_return, fixed_return))
    deltas = [candidate_return - fixed_return for candidate_return, fixed_return in pairs]
    return {
        "source_record_count": len(rows),
        "deduplicated_record_count": len(deduplicated),
        "duplicate_record_count": duplicate_count,
        "duplicate_policy_conflict_count": conflict_count,
        "paired_record_count": len(pairs),
        "avg_candidate_policy_return_pct": _avg([candidate for candidate, _ in pairs]),
        "avg_fixed_policy_return_pct": _avg([fixed for _, fixed in pairs]),
        "avg_paired_delta_pct": _avg(deltas),
        "candidate_tail_loss_count": sum(candidate <= tail_loss_pct for candidate, _ in pairs),
        "fixed_tail_loss_count": sum(fixed <= tail_loss_pct for _, fixed in pairs),
        "paired_tail_avoided_count": sum(candidate > tail_loss_pct and fixed <= tail_loss_pct for candidate, fixed in pairs),
        "paired_tail_worsened_count": sum(candidate <= tail_loss_pct and fixed > tail_loss_pct for candidate, fixed in pairs),
        "round_trip_cost_pct": round_trip_cost_pct,
        "paper_research_only": True,
    }


def _deduplicate_entries(rows: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], int, int]:
    by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    duplicate_count = 0
    conflict_count = 0
    for raw in rows:
        row = dict(raw)
        key = (
            str(row.get("signal_date") or row.get("as_of") or row.get("_sample_date") or ""),
            str(row.get("entry_date") or ""),
            str(row.get("code") or ""),
            str((row.get("execution_assumptions") or {}).get("bar_interval") or ""),
        )
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = row
            continue
        duplicate_count += 1
        if _policy_signature(existing) != _policy_signature(row):
            conflict_count += 1
    return list(by_key.values()), duplicate_count, conflict_count


def _policy_signature(row: Mapping[str, Any]) -> str:
    interval = str((row.get("execution_assumptions") or {}).get("bar_interval") or "")
    return json.dumps(
        {
            "entry_date": row.get("entry_date"),
            "bar_interval": interval,
            "entry_path_sha256": (
                row.get("source_1m_bars_sha256")
                if interval == "5m"
                else row.get("entry_bars_sha256")
            ),
            "forward_return_pct": row.get("forward_return_pct"),
            "path_stats": row.get("path_stats"),
            "paper_exit_candidates": row.get("paper_exit_candidates") or {},
        },
        ensure_ascii=False,
        sort_keys=True,
        allow_nan=False,
    )


def _policy_return(row: Mapping[str, Any], candidate_id: str, *, round_trip_cost_pct: float) -> float | None:
    candidate = ((row.get("paper_exit_candidates") or {}).get(candidate_id) or {})
    if candidate.get("triggered"):
        if not candidate.get("fill_available"):
            return None
        value = _float(candidate.get("simulated_exit_return_pct"))
    else:
        close_return = _float((row.get("path_stats") or {}).get("close_return_pct"))
        if close_return is None:
            close_return = _float((row.get("exit_research") or {}).get("close_return_pct"))
        value = close_return
    return value - round_trip_cost_pct if value is not None else None


def _fold_stability(walk_forward: Mapping[str, Any]) -> dict[str, Any]:
    folds = list(walk_forward.get("folds") or [])
    valid = [fold for fold in folds if fold.get("status") == "ok"]
    saved = [_float(fold.get("avg_saved_vs_forward_pct")) for fold in valid]
    saved = [value for value in saved if value is not None]
    return {
        "fold_count": len(folds),
        "valid_fold_count": len(valid),
        "positive_saved_fold_count": sum(value > 0 for value in saved),
        "positive_saved_fold_rate": _round(sum(value > 0 for value in saved) / len(saved)) if saved else None,
        "folds": folds,
    }


def _paired_fold_stability(
    rows: Sequence[Mapping[str, Any]],
    candidate_id: str,
    *,
    fold_count: int,
    min_pairs: int,
    round_trip_cost_pct: float,
    tail_loss_pct: float,
) -> dict[str, Any]:
    dates = sorted({str(row.get("as_of") or row.get("_sample_date") or "") for row in rows if row.get("as_of") or row.get("_sample_date")})
    count = min(max(0, fold_count), len(dates))
    folds = []
    for index in range(count):
        start = index * len(dates) // count
        end = (index + 1) * len(dates) // count
        fold_dates = dates[start:end]
        fold_rows = [row for row in rows if str(row.get("as_of") or row.get("_sample_date") or "") in fold_dates]
        summary = _paired_policy_summary(
            fold_rows,
            candidate_id,
            round_trip_cost_pct=round_trip_cost_pct,
            tail_loss_pct=tail_loss_pct,
        )
        summary.update(
            {
                "fold_index": index + 1,
                "start_date": fold_dates[0] if fold_dates else None,
                "end_date": fold_dates[-1] if fold_dates else None,
                "status": "ok" if summary.get("paired_record_count", 0) >= min_pairs else "insufficient_sample",
            }
        )
        folds.append(summary)
    valid = [fold for fold in folds if fold.get("status") == "ok"]
    positive = [fold for fold in valid if (_float(fold.get("avg_paired_delta_pct")) or 0.0) > 0]
    return {
        "fold_count": len(folds),
        "valid_fold_count": len(valid),
        "positive_delta_fold_count": len(positive),
        "positive_delta_fold_rate": _round(len(positive) / len(valid)) if valid else None,
        "folds": folds,
    }


def _long_history_veto(
    records: Sequence[Mapping[str, Any]] | None,
    candidate_id: str,
    *,
    fold_count: int,
    min_labeled_triggers: int,
    tail_loss_pct: float,
    round_trip_cost_pct: float,
) -> dict[str, Any]:
    if records is None:
        return {
            "status": "not_evaluated",
            "vetoed": None,
            "reasons": ["long_history_records_not_supplied"],
        }
    rows = [dict(row) for row in records if isinstance(row, Mapping)]
    paired = _paired_policy_summary(
        rows,
        candidate_id,
        round_trip_cost_pct=round_trip_cost_pct,
        tail_loss_pct=tail_loss_pct,
    )
    candidate = _candidate_summary(
        rows,
        candidate_id,
        fold_count=fold_count,
        min_labeled_triggers=min_labeled_triggers,
        tail_loss_pct=tail_loss_pct,
    )
    baseline = _candidate_summary(
        rows,
        "paper_fixed_exit_baseline",
        fold_count=fold_count,
        min_labeled_triggers=min_labeled_triggers,
        tail_loss_pct=tail_loss_pct,
    )
    if (paired.get("paired_record_count") or 0) < min_labeled_triggers:
        return {
            "status": "insufficient_sample",
            "vetoed": None,
            "metrics_complete": False,
            "reasons": ["insufficient_long_history_paired_policies"],
            "paired": paired,
            "candidate": candidate,
            "baseline": baseline,
        }
    paired_delta = _float(paired.get("avg_paired_delta_pct"))
    fill_rates = []
    fill_incomplete = False
    for summary in (candidate, baseline):
        if (summary.get("trigger_count") or 0) > 0:
            rate = _float(summary.get("next_bar_fill_rate"))
            if rate is None:
                fill_incomplete = True
                break
            fill_rates.append(rate)
    if paired_delta is None or fill_incomplete or (fill_rates and min(fill_rates) < 0.95):
        return {
            "status": "insufficient_metrics",
            "vetoed": None,
            "metrics_complete": False,
            "reasons": ["long_history_metrics_or_fill_incomplete"],
            "paired": paired,
            "candidate": candidate,
            "baseline": baseline,
        }
    reasons = []
    if paired_delta < 0:
        reasons.append("paired_net_return_worse_than_fixed_baseline")
    if (paired.get("candidate_tail_loss_count") or 0) > (paired.get("fixed_tail_loss_count") or 0):
        reasons.append("paired_tail_loss_count_worse_than_fixed_baseline")
    return {
        "status": "ok",
        "vetoed": bool(reasons),
        "metrics_complete": True,
        "reasons": reasons,
        "paired": paired,
        "candidate": candidate,
        "baseline": baseline,
    }


def _attach_baseline_deltas(candidates: dict[str, Any]) -> None:
    baseline = candidates.get("paper_fixed_exit_baseline") or {}
    for candidate_id, candidate in candidates.items():
        deltas = {}
        for window_id, summary in (candidate.get("by_window") or {}).items():
            baseline_summary = ((baseline.get("by_window") or {}).get(window_id) or {})
            deltas[window_id] = {
                metric: _difference(summary.get(metric), baseline_summary.get(metric))
                for metric in (
                    "avg_simulated_exit_return_pct",
                    "avg_saved_vs_forward_pct",
                    "avg_missed_upside_pct",
                    "forward_tail_avoided_count",
                    "simulated_exit_tail_loss_rate",
                )
            }
        candidate["vs_fixed_baseline_by_window"] = deltas


def _with_regime(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("market_regime") is None and row.get("market_regime_score") is None:
        score = (row.get("factor_snapshot") or {}).get("market_regime_score")
        if score is not None:
            row["market_regime_score"] = score
    return row


def _load_records(
    path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], str]:
    data, records_sha256 = load_strict_json_with_sha256(path)
    if isinstance(data, Mapping):
        validate_paper_records_report(
            data,
            context=f"profit records report {path}",
            require_durable_entry_bars_source=True,
        )
    rows = data.get("records") if isinstance(data, Mapping) else data
    parameters = dict(data.get("parameters") or {}) if isinstance(data, Mapping) else {}
    identity = (
        {
            "as_of": data.get("as_of"),
            "snapshot_label": data.get("snapshot_label"),
            "bar_interval": data.get("bar_interval"),
            "bar_source": data.get("bar_source"),
            "entry_model": data.get("entry_model"),
            "strategy_linked_entry_paths": data.get("strategy_linked_entry_paths"),
            "trading_calendar": data.get("trading_calendar") or data.get("calendar_source"),
            "paper_trading_only": data.get("paper_trading_only"),
            "no_execution_signals": data.get("no_execution_signals"),
        }
        if isinstance(data, Mapping)
        else {}
    )
    return (
        [dict(row) for row in rows or [] if isinstance(row, Mapping)],
        parameters,
        identity,
        records_sha256,
    )


def validate_profit_long_history_identity(
    identity: Mapping[str, Any],
    *,
    parameters: Mapping[str, Any],
    timeframe: str,
    expected_version_ids: Sequence[str],
) -> dict[str, Any]:
    if identity.get("paper_trading_only") is not True or identity.get("no_execution_signals") is not True:
        raise ValueError("profit long-history records must be paper-only with no execution signals")
    interval = str(identity.get("bar_interval") or "")
    if interval != timeframe:
        raise ValueError(
            f"profit long-history timeframe mismatch: expected {timeframe}, got {interval or 'missing'}"
        )
    expected_bar_source = {
        "1m": "complete_1m_session",
        "5m": "aggregated_from_complete_1m_session",
    }.get(timeframe)
    source = str(identity.get("bar_source") or "")
    if source != expected_bar_source:
        raise ValueError(
            f"profit long-history bar source mismatch: expected {expected_bar_source}, got {source or 'missing'}"
        )
    entry_model = str(identity.get("entry_model") or "")
    if entry_model != "next_trading_session_first_bar_open":
        raise ValueError(
            "profit long-history entry model must be next_trading_session_first_bar_open"
        )
    if identity.get("strategy_linked_entry_paths") is not True:
        raise ValueError("profit long-history records must contain strategy-linked entry paths")
    expected_versions = {str(value) for value in expected_version_ids if str(value)}
    actual_versions = {str(value) for value in parameters.get("version_ids") or [] if str(value)}
    if actual_versions != expected_versions or len(list(parameters.get("version_ids") or [])) != len(expected_versions):
        raise ValueError(
            "profit long-history strategy versions must exactly match current source: "
            + ", ".join(sorted(expected_versions))
        )
    return {
        "status": "validated_strategy_linked",
        "as_of": identity.get("as_of"),
        "snapshot_label": identity.get("snapshot_label"),
        "bar_interval": interval,
        "bar_source": source,
        "entry_model": entry_model,
        "strategy_linked_entry_paths": True,
        "version_ids": sorted(actual_versions),
        "paper_trading_only": True,
        "no_execution_signals": True,
    }


def validate_profit_long_history_records(
    records: Sequence[Mapping[str, Any]],
    *,
    identity: Mapping[str, Any],
    parameters: Mapping[str, Any],
    timeframe: str,
    expected_version_ids: Sequence[str],
    trading_calendar_path: Path | None,
    candidate_root: Path | None,
    candidate_source_root: Path | None,
    selection_validation_root: Path | None,
) -> dict[str, Any]:
    long_as_of = str(identity.get("as_of") or "")
    giveback_pct = _float(parameters.get("factor_exit_peak_giveback_pct"))
    if (
        not records
        or not long_as_of
        or giveback_pct is None
        or trading_calendar_path is None
        or candidate_root is None
        or candidate_source_root is None
        or selection_validation_root is None
    ):
        return {
            "status": "not_evaluated",
            "eligible_as_long_history_veto": False,
            "reason": "causal_records_or_external_anchors_unavailable",
            "causal_record_identity": None,
            "record_cohort_identity": None,
        }
    try:
        calendar = load_trading_calendar(trading_calendar_path, as_of=long_as_of)
        reported_calendar = identity.get("trading_calendar")
        if not isinstance(reported_calendar, Mapping):
            raise ValueError("profit long-history reported calendar identity is missing")
        if (
            _resolved_path(Path(str(reported_calendar.get("path") or "")))
            != _resolved_path(trading_calendar_path)
            or str(reported_calendar.get("sha256") or "") != calendar["sha256"]
        ):
            raise ValueError("profit long-history calendar path or SHA does not match caller-bound calendar")
        source_candidate_root = Path(str(parameters.get("candidate_root") or ""))
        source_candidate_source_root = Path(str(parameters.get("candidate_source_root") or ""))
        selection_value = parameters.get("selection_validation_root")
        source_selection_root = Path(str(selection_value)) if selection_value else None
        if _resolved_path(source_candidate_root) != _resolved_path(candidate_root):
            raise ValueError("profit long-history candidate root does not match caller-bound root")
        if _resolved_path(source_candidate_source_root) != _resolved_path(candidate_source_root):
            raise ValueError("profit long-history candidate source root does not match caller-bound root")
        if _resolved_path(source_selection_root) != _resolved_path(selection_validation_root):
            raise ValueError("profit long-history selection root does not match caller-bound root")
        candidate_document_snapshots: dict[Path, Mapping[str, Any]] = {}
        candidate_source_identity = revalidate_records_candidate_source_identity(
            parameters.get("candidate_source_identity"),
            candidate_root=candidate_root,
            source_root=candidate_source_root,
            timeframe=timeframe,
            start=parameters.get("start"),
            end=min(str(parameters.get("end") or long_as_of), long_as_of),
            context="profit long-history records",
            document_snapshots=candidate_document_snapshots,
        )
        selection_document_snapshots: dict[str, Mapping[str, Any]] = {}
        selection_source_identity = revalidate_records_selection_source_identity(
            parameters.get("selection_source_identity"),
            selection_validation_root=selection_validation_root,
            start=parameters.get("start"),
            end=min(str(parameters.get("end") or long_as_of), long_as_of),
            context="profit long-history records",
            document_snapshots=selection_document_snapshots,
        )
        causal_identity = validate_causal_paper_records(
            records,
            timeframe=timeframe,
            as_of=long_as_of,
            calendar_dates=calendar["dates"],
            factor_exit_peak_giveback_pct=giveback_pct,
            context="profit long-history records",
        )
        if int(causal_identity.get("valid_record_count") or 0) <= 0:
            raise ValueError("profit long-history records contain no valid causal entry paths")
        samples = _load_samples(
            candidate_root,
            None,
            long_as_of,
            selection_validation_root,
            candidate_document_snapshots,
            selection_document_snapshots,
        )
        cohort_identity = validate_paper_record_cohort(
            records,
            samples=samples,
            version_ids=list(expected_version_ids),
            snapshot_label=str(identity.get("snapshot_label") or ""),
            calendar_dates=calendar["dates"],
            start=parameters.get("start"),
            end=min(str(parameters.get("end") or long_as_of), long_as_of),
            concentration_threshold=int(parameters.get("concentration_threshold")),
            factor_exit_peak_giveback_pct=float(giveback_pct),
            timeframe=timeframe,
            context="profit long-history records",
        )
    except ValueError as exc:
        return {
            "status": "not_evaluated",
            "eligible_as_long_history_veto": False,
            "reason": "external_anchor_validation_failed",
            "validation_error": str(exc),
            "causal_record_identity": None,
            "record_cohort_identity": None,
        }
    return {
        "status": "validated_strategy_linked",
        "eligible_as_long_history_veto": True,
        "reason": None,
        "causal_record_identity": causal_identity,
        "record_cohort_identity": cohort_identity,
        "candidate_source_identity": candidate_source_identity,
        "selection_source_identity": selection_source_identity,
        "trading_calendar": calendar,
    }


def _cohort_snapshot_label(source_label: str, giveback_pct: float | None) -> str:
    if not source_label or giveback_pct is None:
        return source_label
    suffix = f"_giveback_{giveback_pct:g}pct"
    return source_label[: -len(suffix)] if source_label.endswith(suffix) else source_label


def _resolved_path(path: Path | None) -> str | None:
    return str(path.resolve()) if path is not None else None


def _markdown(report: Mapping[str, Any]) -> str:
    parameters = report.get("parameters") or {}
    tail = observed_evaluation_tail_summary(report, allow_short_window=True)
    lines = [
        "# Nonstationary Profit Exit Audit",
        "",
        f"- As of: `{report.get('as_of')}`",
        f"- Snapshot: `{report.get('snapshot_label')}`",
        f"- Applied peak giveback: `{parameters.get('applied_giveback_pct')}`",
        f"- Declared candidates only: `{parameters.get('declared_giveback_candidates_pct')}`",
        f"- Round-trip friction: `{parameters.get('round_trip_cost_pct')}` percent",
        "- Paper-only: `True`",
    ]
    lines.extend(observed_evaluation_tail_markdown_lines(tail))
    lines.extend(
        [
            "",
            "## Paired Policy Comparison",
            "",
            "| Candidate | Window | Dates | Deduplicated | Paired | Candidate net % | Fixed net % | Paired delta % | Tail avoided | Tail worsened |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for candidate_id, candidate in (report.get("candidates") or {}).items():
        for window_id in ("recent_60", "recent_120", "holdout", "all_history"):
            summary = (candidate.get("by_window") or {}).get(window_id) or {}
            paired = (candidate.get("paired_vs_fixed_by_window") or {}).get(window_id) or {}
            display_window_id = "observed_evaluation_tail" if window_id == "holdout" else window_id
            lines.append(
                f"| `{candidate_id}` | `{display_window_id}` | {summary.get('window_date_count')} | "
                f"{paired.get('deduplicated_record_count')} | {paired.get('paired_record_count')} | "
                f"{paired.get('avg_candidate_policy_return_pct')} | {paired.get('avg_fixed_policy_return_pct')} | "
                f"{paired.get('avg_paired_delta_pct')} | {paired.get('paired_tail_avoided_count')} | "
                f"{paired.get('paired_tail_worsened_count')} |"
            )
    lines.extend(
        [
            "",
            "Long-history evidence is a veto only; it is not equally weighted with recent samples.",
            "This report does not contain executable trading instructions.",
        ]
    )
    return "\n".join(lines) + "\n"


def _difference(left: Any, right: Any) -> float | None:
    left_value = _float(left)
    right_value = _float(right)
    if left_value is None or right_value is None:
        return None
    return _round(left_value - right_value)


def _avg(values: Sequence[float]) -> float | None:
    return _round(sum(values) / len(values)) if values else None


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit nonstationary paper-only profit exits")
    parser.add_argument("--records-path", required=True)
    parser.add_argument("--candidate-root", required=True)
    parser.add_argument("--candidate-source-root", required=True)
    parser.add_argument("--selection-validation-root", required=True)
    parser.add_argument("--trading-calendar-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--snapshot-label", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--applied-giveback-pct", type=float)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.1)
    parser.add_argument("--long-history-records-path")
    parser.add_argument("--long-history-trading-calendar-path")
    parser.add_argument("--long-history-candidate-root")
    parser.add_argument("--long-history-candidate-source-root")
    parser.add_argument("--long-history-selection-validation-root")
    parser.add_argument("--holdout-days", type=int, default=20)
    parser.add_argument("--fold-count", type=int, default=3)
    parser.add_argument("--min-labeled-triggers", type=int, default=5)
    parser.add_argument("--tail-loss-pct", type=float, default=-5.0)
    args = parser.parse_args(argv)
    result = audit_nonstationary_profit_exit(
        records_path=Path(args.records_path),
        candidate_root=Path(args.candidate_root),
        candidate_source_root=Path(args.candidate_source_root),
        selection_validation_root=Path(args.selection_validation_root),
        trading_calendar_path=Path(args.trading_calendar_path),
        output_dir=Path(args.output_dir),
        as_of=args.as_of,
        snapshot_label=args.snapshot_label,
        timeframe=args.timeframe,
        applied_giveback_pct=args.applied_giveback_pct,
        round_trip_cost_pct=args.round_trip_cost_pct,
        long_history_records_path=Path(args.long_history_records_path) if args.long_history_records_path else None,
        long_history_trading_calendar_path=(
            Path(args.long_history_trading_calendar_path) if args.long_history_trading_calendar_path else None
        ),
        long_history_candidate_root=Path(args.long_history_candidate_root) if args.long_history_candidate_root else None,
        long_history_candidate_source_root=(
            Path(args.long_history_candidate_source_root) if args.long_history_candidate_source_root else None
        ),
        long_history_selection_validation_root=(
            Path(args.long_history_selection_validation_root)
            if args.long_history_selection_validation_root
            else None
        ),
        holdout_days=args.holdout_days,
        fold_count=args.fold_count,
        min_labeled_triggers=args.min_labeled_triggers,
        tail_loss_pct=args.tail_loss_pct,
    )
    print(result["json_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
