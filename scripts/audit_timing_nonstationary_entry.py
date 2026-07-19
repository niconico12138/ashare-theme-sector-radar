#!/usr/bin/env python3
"""Audit v26/v31/v32 under recent-dominant nonstationary windows."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping

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
from theme_sector_radar.timing.candidate_source_identity import (
    revalidate_records_candidate_source_identity,
    validate_records_candidate_source_identity,
)
from theme_sector_radar.timing.combination_experiment import (
    FactorCondition,
    StrategyVersion,
    build_default_strategy_versions,
    evaluate_strategy_versions,
)
from theme_sector_radar.timing.nonstationary_validation import (
    CANDIDATE_DATE_COVERAGE_FIELDS,
    attach_candidate_date_coverage,
    build_nonstationary_windows,
    concentration_summary,
    current_regime_summary,
    group_by_regime,
    labeled_trading_dates,
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

VERSION_IDS = (
    "v26_relative_watch_late_surge_cap",
    "v31_expanded_balanced_tail_guard",
    "v32_expanded_defensive_breakdown_guard",
)

def audit_nonstationary_entry_samples(
    samples: list[dict[str, Any]],
    *,
    causal_entry_records: list[dict[str, Any]] | None = None,
    as_of: str | None = None,
    timeframe: str | None = None,
    calendar_dates: list[str] | None = None,
    source_document_dates: list[str] | None = None,
    complete_candidate_dates: list[str] | None = None,
    min_selected: int = 5,
    holdout_days: int = 20,
    round_trip_cost_pct: float = 0.0,
) -> dict[str, Any]:
    if not math.isfinite(round_trip_cost_pct) or round_trip_cost_pct < 0:
        raise ValueError("round_trip_cost_pct must be a finite non-negative number")
    versions = [version for version in build_default_strategy_versions() if version.version_id in VERSION_IDS]
    report_windows = build_nonstationary_windows(
        samples,
        as_of=as_of,
        calendar_dates=calendar_dates,
        holdout_days=holdout_days,
    )
    attach_candidate_date_coverage(
        report_windows,
        source_document_dates=source_document_dates,
        complete_candidate_dates=complete_candidate_dates,
    )
    causal_index, causal_coverage = _causal_entry_index(
        causal_entry_records or [],
        as_of=as_of,
        timeframe=timeframe,
    )
    version_reports = {}
    for version in versions:
        version_samples = (
            _apply_causal_entry_returns(
                samples,
                version.version_id,
                causal_index,
                round_trip_cost_pct=round_trip_cost_pct,
            )
            if causal_entry_records is not None
            else samples
        )
        windows = build_nonstationary_windows(
            version_samples,
            as_of=as_of,
            calendar_dates=calendar_dates,
            holdout_days=holdout_days,
        )
        attach_candidate_date_coverage(
            windows,
            source_document_dates=source_document_dates,
            complete_candidate_dates=complete_candidate_dates,
        )
        window_rows = {
            key: item["records"]
            for key, item in windows.items()
            if isinstance(item, dict) and "records" in item
        }
        by_window = {}
        for key, rows in window_rows.items():
            result = _version_result(rows, version, min_selected=min_selected)
            result["window_status"] = windows[key]["status"]
            result["window_date_count"] = windows[key]["date_count"]
            for field in CANDIDATE_DATE_COVERAGE_FIELDS:
                result[field] = windows[key].get(field)
            by_window[key] = result
        perturbation = _perturbation_report(window_rows.get("recent_60", []), version, min_selected=min_selected)
        ablation = _ablation_report(window_rows.get("recent_60", []), version, min_selected=min_selected)
        selected = _selected(window_rows.get("recent_120", []), version)
        version_reports[version.version_id] = {
            "description": version.description,
            "condition_count": len(version.conditions),
            "by_window": by_window,
            "perturbation": perturbation,
            "ablation": ablation,
            "regime": {
                label: _version_result(rows, version, min_selected=max(1, min_selected // 2))
                for label, rows in group_by_regime(window_rows.get("recent_120", [])).items()
            },
            "concentration": concentration_summary(selected),
            "walk_forward": _walk_forward(window_rows.get("recent_120", []), version, min_selected=min_selected),
            "factor_correlation": _factor_correlation(window_rows.get("recent_120", []), version),
            "factor_decay": _factor_decay(window_rows, version, min_selected=max(1, min_selected // 2)),
            "overfit_risk": _overfit_risk(by_window, perturbation, ablation),
        }
    return {
        "schema_version": "timing_nonstationary_entry_audit.v1",
        "holdout_evidence": dict(report_windows.get("holdout_evidence") or {}),
        "windows": {
            key: {field: value for field, value in item.items() if field != "records"}
            for key, item in report_windows.items()
            if isinstance(item, dict) and "records" in item
        },
        "versions": version_reports,
        "label_source": {
            "mode": "causal_next_session_open_to_close" if causal_entry_records is not None else "selection_forward_return",
            "version_specific": causal_entry_records is not None,
        },
        "causal_entry_coverage": causal_coverage if causal_entry_records is not None else None,
        "current_regime": current_regime_summary(
            samples,
            calendar_dates=calendar_dates or (report_windows.get("all_history") or {}).get("dates") or [],
        ),
        "parameters": {
            "round_trip_cost_pct": round(round_trip_cost_pct, 4),
            "returns_net_of_round_trip_cost": causal_entry_records is not None,
        },
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }


def audit_nonstationary_entry(
    *,
    candidate_root: Path,
    candidate_source_root: Path,
    selection_validation_root: Path,
    entry_records_path: Path,
    trading_calendar_path: Path,
    output_dir: Path,
    as_of: str,
    timeframe: str | None = None,
    min_selected: int = 5,
    round_trip_cost_pct: float = 0.1,
) -> dict[str, Any]:
    calendar = load_trading_calendar(trading_calendar_path, as_of=as_of)
    entry_records_report, entry_records_sha256 = _load_causal_entry_records_report(
        entry_records_path,
        as_of=as_of,
        timeframe=timeframe,
        candidate_root=candidate_root,
        candidate_source_root=candidate_source_root,
    )
    validate_trading_calendar_identity(
        entry_records_report.get("trading_calendar"),
        calendar,
        context="entry records",
    )
    source_parameters = entry_records_report.get("parameters") or {}
    candidate_document_snapshots: dict[Path, Mapping[str, Any]] = {}
    revalidated_candidate_source = revalidate_records_candidate_source_identity(
        source_parameters.get("candidate_source_identity"),
        candidate_root=candidate_root,
        source_root=candidate_source_root,
        timeframe=str(timeframe or ""),
        start=source_parameters.get("start"),
        end=min(str(source_parameters.get("end") or as_of), as_of),
        context="entry records",
        document_snapshots=candidate_document_snapshots,
    )
    selection_document_snapshots: dict[str, Mapping[str, Any]] = {}
    revalidated_selection_source = revalidate_records_selection_source_identity(
        source_parameters.get("selection_source_identity"),
        selection_validation_root=selection_validation_root,
        start=source_parameters.get("start"),
        end=min(str(source_parameters.get("end") or as_of), as_of),
        context="entry records",
        document_snapshots=selection_document_snapshots,
    )
    causal_record_identity = validate_causal_paper_records(
        entry_records_report["records"],
        timeframe=str(timeframe or ""),
        as_of=as_of,
        calendar_dates=calendar["dates"],
        factor_exit_peak_giveback_pct=source_parameters.get("factor_exit_peak_giveback_pct"),
        context="entry records",
    )
    samples = [
        row
        for row in _load_samples(
            candidate_root,
            None,
            as_of,
            selection_validation_root,
            candidate_document_snapshots,
            selection_document_snapshots,
        )
        if not row.get("_sample_mode")
    ]
    record_cohort_identity = validate_paper_record_cohort(
        entry_records_report["records"],
        samples=samples,
        version_ids=VERSION_IDS,
        snapshot_label=str(entry_records_report.get("snapshot_label") or ""),
        calendar_dates=calendar["dates"],
        start=source_parameters.get("start"),
        end=min(str(source_parameters.get("end") or as_of), as_of),
        concentration_threshold=int(source_parameters.get("concentration_threshold")),
        factor_exit_peak_giveback_pct=float(source_parameters.get("factor_exit_peak_giveback_pct")),
        timeframe=str(timeframe or ""),
        context="entry records",
    )
    sample_dates = sorted(
        {
            str(row.get("_sample_date") or row.get("as_of") or "")
            for row in samples
            if not row.get("_sample_mode") and str(row.get("_sample_date") or row.get("as_of") or "")
        }
    )
    if not sample_dates:
        raise ValueError("entry audit candidate source has no dated samples")
    calendar_dates = [value for value in calendar["dates"] if sample_dates[0] <= value <= as_of]
    report = audit_nonstationary_entry_samples(
        samples,
        causal_entry_records=entry_records_report["records"],
        as_of=as_of,
        timeframe=timeframe,
        calendar_dates=calendar_dates,
        source_document_dates=list(revalidated_candidate_source.get("document_dates") or []),
        complete_candidate_dates=list(revalidated_candidate_source.get("complete_candidate_dates") or []),
        min_selected=min_selected,
        round_trip_cost_pct=round_trip_cost_pct,
    )
    report["label_source"].update(
        {
            "entry_records_path": str(entry_records_path),
            "entry_records_sha256": entry_records_sha256,
            "source_as_of": entry_records_report.get("as_of"),
            "source_bar_interval": entry_records_report.get("bar_interval"),
            "source_version_ids": list((entry_records_report.get("parameters") or {}).get("version_ids") or []),
            "candidate_source_identity": dict(
                (entry_records_report.get("parameters") or {}).get("candidate_source_identity") or {}
            ),
            "revalidated_candidate_source_identity": revalidated_candidate_source,
            "revalidated_selection_source_identity": revalidated_selection_source,
            "causal_record_identity": causal_record_identity,
            "record_cohort_identity": record_cohort_identity,
        }
    )
    report.update(
        {
            "as_of": as_of,
            "timeframe": timeframe,
            "candidate_root": str(candidate_root),
            "calendar_source": calendar,
        }
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"nonstationary_entry_audit_{as_of}.json"
    markdown_path = output_dir / f"nonstationary_entry_audit_{as_of}.md"
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


def _load_causal_entry_records_report(
    path: Path,
    *,
    as_of: str,
    timeframe: str | None,
    candidate_root: Path,
    candidate_source_root: Path,
) -> tuple[dict[str, Any], str]:
    report, report_sha256 = load_strict_json_with_sha256(path)
    if not isinstance(report, dict):
        raise ValueError("entry records report must be a JSON object")
    validate_paper_records_report(
        report,
        context="entry records report",
        require_durable_entry_bars_source=True,
    )
    if report.get("paper_trading_only") is not True or report.get("no_execution_signals") is not True:
        raise ValueError("entry records report must be paper-only with no execution signals")
    if str(report.get("as_of") or "") != as_of:
        raise ValueError(f"entry records as_of mismatch: expected {as_of}, got {report.get('as_of')}")
    if timeframe and str(report.get("bar_interval") or "") != timeframe:
        raise ValueError(
            f"entry records timeframe mismatch: expected {timeframe}, got {report.get('bar_interval')}"
        )
    expected_bar_source = {
        "1m": "complete_1m_session",
        "5m": "aggregated_from_complete_1m_session",
    }.get(str(timeframe or ""))
    if expected_bar_source and report.get("bar_source") != expected_bar_source:
        raise ValueError(
            f"entry records bar source mismatch: expected {expected_bar_source}, got {report.get('bar_source')}"
        )
    parameters = report.get("parameters") or {}
    source_versions = list(parameters.get("version_ids") or [])
    if len(source_versions) != len(VERSION_IDS) or set(source_versions) != set(VERSION_IDS):
        raise ValueError(
            "entry records must contain the exact strategy versions: " + ", ".join(VERSION_IDS)
        )
    validate_records_candidate_source_identity(
        parameters.get("candidate_source_identity") if isinstance(parameters, Mapping) else None,
        candidate_root=candidate_root,
        source_root=candidate_source_root,
        timeframe=str(timeframe or ""),
        context="entry records",
    )
    records = report.get("records")
    if not isinstance(records, list):
        raise ValueError("entry records report must contain a records list")
    return report, report_sha256


def _causal_entry_index(
    records: list[dict[str, Any]],
    *,
    as_of: str | None,
    timeframe: str | None,
) -> tuple[dict[tuple[str, str, str], float], dict[str, Any]]:
    index: dict[tuple[str, str, str], float] = {}
    invalid_count = 0
    for record in records:
        signal_date = str(record.get("signal_date") or record.get("as_of") or "")
        entry_date = str(record.get("entry_date") or "")
        code = str(record.get("code") or "")
        version_id = str(record.get("timing_version_id") or "")
        value = _finite_float(record.get("forward_return_pct"))
        if as_of and entry_date and entry_date > as_of:
            raise ValueError(f"causal entry {entry_date} is after audit as_of {as_of}")
        if record.get("causal_entry_valid"):
            assumptions = record.get("execution_assumptions") or {}
            if assumptions.get("signal_available") != "after_signal_session_close":
                raise ValueError("causal entry signal availability identity is invalid")
            if assumptions.get("entry_model") != "next_trading_session_first_bar_open":
                raise ValueError("causal entry model identity is invalid")
            if timeframe and assumptions.get("bar_interval") != timeframe:
                raise ValueError("causal entry record timeframe identity is invalid")
            expected_bar_source = {
                "1m": "complete_1m_session",
                "5m": "aggregated_from_complete_1m_session",
            }.get(str(timeframe or ""))
            if expected_bar_source and assumptions.get("bar_source") != expected_bar_source:
                raise ValueError("causal entry record bar source identity is invalid")
            path_hash = str(record.get("entry_bars_sha256") or "")
            if len(path_hash) != 64:
                raise ValueError("causal entry path hash is missing")
        if not record.get("causal_entry_valid") or not signal_date or not entry_date or entry_date <= signal_date or not code or not version_id or value is None:
            invalid_count += 1
            continue
        key = (signal_date, code, version_id)
        if key in index and index[key] != value:
            raise ValueError(f"conflicting causal entry returns for {signal_date}|{code}|{version_id}")
        index[key] = value
    return index, {
        "source_record_count": len(records),
        "valid_record_count": len(index),
        "invalid_record_count": invalid_count,
    }


def _apply_causal_entry_returns(
    samples: list[dict[str, Any]],
    version_id: str,
    causal_index: Mapping[tuple[str, str, str], float],
    *,
    round_trip_cost_pct: float,
) -> list[dict[str, Any]]:
    rows = []
    for sample in samples:
        row = dict(sample)
        signal_date = str(row.get("_sample_date") or row.get("as_of") or row.get("date") or "")
        code = str(row.get("code") or "")
        gross_return = causal_index.get((signal_date, code, version_id))
        row["selection_forward_return_pct"] = row.get("forward_return_pct")
        row["gross_forward_return_pct"] = gross_return
        row["causal_entry_label_available"] = gross_return is not None
        row["forward_return_pct"] = (
            round(gross_return - round_trip_cost_pct, 4)
            if gross_return is not None
            else None
        )
        rows.append(row)
    return rows


def _finite_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _version_result(rows: list[dict[str, Any]], version: StrategyVersion, *, min_selected: int) -> dict[str, Any]:
    report = evaluate_strategy_versions(rows, [version], min_selected=min_selected)
    result = report["versions"][0] if report["versions"] else {}
    causal_mode = any("causal_entry_label_available" in row for row in rows)
    if causal_mode:
        eligible = [row for row in rows if all(condition.matches(row) for condition in version.conditions)]
        valid_count = sum(1 for row in eligible if row.get("causal_entry_label_available") is True)
        result.update(
            {
                "causal_entry_expected_count": len(eligible),
                "causal_entry_valid_count": valid_count,
                "causal_entry_fill_rate": round(valid_count / len(eligible), 4) if eligible else None,
            }
        )
    return result


def _selected(rows: list[dict[str, Any]], version: StrategyVersion) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("forward_return_pct") is not None and all(condition.matches(row) for condition in version.conditions)]


def _perturbed(version: StrategyVersion, direction: str, label: str) -> StrategyVersion:
    conditions = []
    for condition in version.conditions:
        loose = direction == "loose"
        multiplier = 0.9 if (loose and condition.operator == ">=") or (not loose and condition.operator == "<=") else 1.1
        threshold = condition.threshold * multiplier
        conditions.append(FactorCondition(condition.factor_id, condition.operator, threshold))
    return StrategyVersion(f"{version.version_id}_{label}", label, tuple(conditions))


def _perturbation_report(rows: list[dict[str, Any]], version: StrategyVersion, *, min_selected: int) -> dict[str, Any]:
    variants = [_perturbed(version, "loose", "loose_10pct"), _perturbed(version, "strict", "strict_10pct")]
    results = evaluate_strategy_versions(rows, variants, min_selected=max(1, min_selected // 2))["versions"]
    valid_results = [item for item in results if item.get("is_valid") is True]
    avgs = [item.get("selected_avg_return_pct") for item in valid_results if item.get("selected_avg_return_pct") is not None]
    return {
        "variant_count": len(variants),
        "valid_variant_count": len(valid_results),
        "all_variants_valid": len(valid_results) == len(variants),
        "positive_variant_rate": round(sum(value > 0 for value in avgs) / len(avgs), 4) if avgs else None,
        "variants": results,
    }


def _ablation_report(rows: list[dict[str, Any]], version: StrategyVersion, *, min_selected: int) -> dict[str, Any]:
    variants = [
        StrategyVersion(
            f"{version.version_id}_without_{condition.factor_id}",
            f"Remove {condition.factor_id}",
            tuple(item for item in version.conditions if item is not condition),
        )
        for condition in version.conditions
    ]
    results = evaluate_strategy_versions(rows, variants, min_selected=max(1, min_selected // 2))["versions"]
    return {"variant_count": len(variants), "variants": results}


def _factor_decay(windows: Mapping[str, list[dict[str, Any]]], version: StrategyVersion, *, min_selected: int) -> dict[str, Any]:
    result = {}
    for condition in version.conditions:
        single = StrategyVersion(f"single_{condition.factor_id}", condition.factor_id, (condition,))
        result[condition.factor_id] = {
            key: _version_result(rows, single, min_selected=min_selected)
            for key, rows in windows.items()
            if key in {"recent_60", "recent_120", "holdout"}
        }
    return result


def _walk_forward(rows: list[dict[str, Any]], version: StrategyVersion, *, min_selected: int, fold_count: int = 5) -> dict[str, Any]:
    dates = sorted({str(row.get("_sample_date") or row.get("as_of") or "") for row in rows})
    count = min(fold_count, len(dates)) if dates else 0
    folds = []
    if count:
        base, extra = divmod(len(dates), count)
        start = 0
        for index in range(count):
            size = base + (1 if index < extra else 0)
            fold_dates = dates[start : start + size]
            fold_rows = [row for row in rows if str(row.get("_sample_date") or row.get("as_of") or "") in fold_dates]
            result = _version_result(fold_rows, version, min_selected=max(1, min_selected // 2))
            result.update(
                {
                    "fold_index": index + 1,
                    "start_date": fold_dates[0] if fold_dates else None,
                    "end_date": fold_dates[-1] if fold_dates else None,
                }
            )
            folds.append(result)
            start += size
    return {"fold_count": len(folds), "folds": folds}


def _factor_correlation(rows: list[dict[str, Any]], version: StrategyVersion, *, threshold: float = 0.85) -> dict[str, Any]:
    factor_ids = list(dict.fromkeys(condition.factor_id for condition in version.conditions))
    expected_pair_count = len(factor_ids) * (len(factor_ids) - 1) // 2
    pairs = []
    for left_index, left in enumerate(factor_ids):
        for right in factor_ids[left_index + 1 :]:
            values = [
                (float(row[left]), float(row[right]))
                for row in rows
                if _is_number(row.get(left)) and _is_number(row.get(right))
            ]
            correlation = _pearson(values)
            if correlation is not None:
                pairs.append({"left": left, "right": right, "correlation": round(correlation, 4), "sample_count": len(values)})
    return {
        "factor_count": len(factor_ids),
        "pair_count": len(pairs),
        "expected_pair_count": expected_pair_count,
        "pair_coverage_rate": round(len(pairs) / expected_pair_count, 4) if expected_pair_count else None,
        "high_correlation_threshold": threshold,
        "high_correlation_pairs": [item for item in pairs if abs(item["correlation"]) >= threshold],
        "pairs": pairs,
    }


def _pearson(values: list[tuple[float, float]]) -> float | None:
    if len(values) < 5:
        return None
    left_mean = sum(left for left, _ in values) / len(values)
    right_mean = sum(right for _, right in values) / len(values)
    numerator = sum((left - left_mean) * (right - right_mean) for left, right in values)
    left_variance = sum((left - left_mean) ** 2 for left, _ in values)
    right_variance = sum((right - right_mean) ** 2 for _, right in values)
    denominator = (left_variance * right_variance) ** 0.5
    return numerator / denominator if denominator else None


def _is_number(value: Any) -> bool:
    try:
        number = float(value)
        return value is not None and value != "" and math.isfinite(number)
    except (TypeError, ValueError):
        return False


def _overfit_risk(by_window: Mapping[str, Mapping[str, Any]], perturbation: Mapping[str, Any], ablation: Mapping[str, Any]) -> dict[str, Any]:
    recent = (by_window.get("recent_60") or {}).get("selected_avg_return_pct")
    medium = (by_window.get("recent_120") or {}).get("selected_avg_return_pct")
    holdout_report = by_window.get("holdout") or {}
    holdout = holdout_report.get("selected_avg_return_pct")
    perturb_rate = perturbation.get("positive_variant_rate")
    risk_points = []
    if recent is None or medium is None:
        risk_points.append("insufficient_recent_samples")
    if (by_window.get("recent_120") or {}).get("window_status") != "ok":
        risk_points.append("recent_120_insufficient")
    if not holdout_report.get("is_valid"):
        risk_points.append("holdout_insufficient")
    elif holdout is None:
        risk_points.append("insufficient_holdout_samples")
    elif holdout <= 0:
        risk_points.append("holdout_nonpositive")
    if not perturbation.get("all_variants_valid"):
        risk_points.append("threshold_variants_insufficient")
    if perturb_rate is None or perturb_rate < 0.5:
        risk_points.append("threshold_fragile")
    ablation_avgs = [item.get("selected_avg_return_pct") for item in ablation.get("variants") or [] if item.get("selected_avg_return_pct") is not None]
    if recent is not None and ablation_avgs and max(ablation_avgs) > recent:
        risk_points.append("complexity_not_justified")
    level = "high" if any(point in risk_points for point in ("holdout_nonpositive", "insufficient_holdout_samples", "holdout_insufficient")) else "medium" if risk_points else "low"
    return {"risk_level": level, "risk_points": risk_points}


def _markdown(report: Mapping[str, Any]) -> str:
    tail = observed_evaluation_tail_summary(report, allow_short_window=True)
    lines = ["# Nonstationary Entry Audit", "", "- Paper-only: True"]
    lines.extend(observed_evaluation_tail_markdown_lines(tail))
    lines.extend(["", "| Version | 60d avg | 120d avg | observed_evaluation_tail avg | Perturb positive | Risk |", "|---|---:|---:|---:|---:|---|"])
    for version_id, item in (report.get("versions") or {}).items():
        windows = item.get("by_window") or {}
        lines.append(
            f"| {version_id} | {(windows.get('recent_60') or {}).get('selected_avg_return_pct')} | "
            f"{(windows.get('recent_120') or {}).get('selected_avg_return_pct')} | "
            f"{(windows.get('holdout') or {}).get('selected_avg_return_pct')} | "
            f"{(item.get('perturbation') or {}).get('positive_variant_rate')} | "
            f"{(item.get('overfit_risk') or {}).get('risk_level')} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit nonstationary entry strategies")
    parser.add_argument("--candidate-root", required=True)
    parser.add_argument("--candidate-source-root", required=True)
    parser.add_argument("--selection-validation-root", required=True)
    parser.add_argument("--entry-records-path", required=True)
    parser.add_argument("--trading-calendar-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--timeframe", required=True, choices=["1m", "5m"])
    parser.add_argument("--min-selected", type=int, default=5)
    parser.add_argument("--round-trip-cost-pct", type=float, default=0.1)
    args = parser.parse_args(argv)
    result = audit_nonstationary_entry(
        candidate_root=Path(args.candidate_root),
        candidate_source_root=Path(args.candidate_source_root),
        selection_validation_root=Path(args.selection_validation_root),
        entry_records_path=Path(args.entry_records_path),
        trading_calendar_path=Path(args.trading_calendar_path),
        output_dir=Path(args.output_dir),
        as_of=args.as_of,
        timeframe=args.timeframe,
        min_selected=args.min_selected,
        round_trip_cost_pct=args.round_trip_cost_pct,
    )
    print(result["json_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
