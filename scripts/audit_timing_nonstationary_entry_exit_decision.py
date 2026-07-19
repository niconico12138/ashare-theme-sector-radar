#!/usr/bin/env python3
"""Combine entry and exit evidence into paper-only hard-gate decisions."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.reporting.artifact_archive import write_text_preserving_previous
from theme_sector_radar.data.trading_calendar import (
    validate_trading_calendar_artifact,
    validate_trading_calendar_identity,
)
from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import load_strict_json, load_strict_json_with_sha256
from theme_sector_radar.timing.candidate_source_identity import validate_candidate_root_identity
from theme_sector_radar.timing.paper_record_identity import (
    entry_path_manifest,
    merge_entry_path_manifests,
    validate_paper_records_report,
)
from theme_sector_radar.timing.selection_source_identity import validate_selection_source_identity
from theme_sector_radar.timing.nonstationary_validation import (
    observed_evaluation_tail_summary,
)


CONCENTRATION_LIMITS = {
    "top_date_share": 0.25,
    "top_code_share": 0.20,
    "top_board_share": 0.40,
}

EXPECTED_RECORD_SOURCE_IDS = frozenset({
    "entry:1m",
    "entry:5m",
    "profit:1m:2pct",
    "profit:1m:3pct",
    "profit:5m:2pct",
    "profit:5m:3pct",
    "stop:1m",
    "stop:5m",
})
ENTRY_BASELINE_ID = "v26_relative_watch_late_surge_cap"
ENTRY_CANDIDATE_IDS = (
    "v31_expanded_balanced_tail_guard",
    "v32_expanded_defensive_breakdown_guard",
)
PROFIT_CANDIDATE_ID = "paper_take_profit_protect_candidate"
PROFIT_REPORT_IDS = {
    "paper_fixed_exit_baseline",
    PROFIT_CANDIDATE_ID,
}
STOP_FACTOR_IDS = (
    "relative_weakness",
    "money_flow_deterioration",
    "board_synchronous_weakness",
)
REQUIRED_HARD_GATES = {
    "recent_60",
    "recent_120",
    "holdout",
    "regime",
    "perturbation",
    "concentration",
    "long_history_veto",
    "next_bar_fill",
    "friction",
}


def evaluate_candidate_hard_gates(
    *,
    candidate_id: str,
    candidate_type: str,
    timeframe: str,
    gates: Mapping[str, Mapping[str, Any]],
    passing_status: str = "challenger",
    research_track_status: str | None = None,
    required_gates: set[str] | None = None,
) -> dict[str, Any]:
    normalized = {name: dict(gate) for name, gate in gates.items()}
    required = set(required_gates or REQUIRED_HARD_GATES)
    for name in sorted(required - set(normalized)):
        normalized[name] = _gate("insufficient", "Required hard gate was not supplied.")
    for name, gate in normalized.items():
        if gate.get("status") not in {"pass", "fail", "insufficient"}:
            normalized[name] = _gate("insufficient", "Hard gate returned an unknown status.", original_status=gate.get("status"))
    failed = [name for name, gate in normalized.items() if gate.get("status") == "fail"]
    insufficient = [name for name, gate in normalized.items() if gate.get("status") == "insufficient"]
    if failed:
        status = "observe"
    elif insufficient:
        status = "insufficient_evidence"
    else:
        status = passing_status
    return {
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "timeframe": timeframe,
        "decision_status": status,
        "research_track_status": research_track_status or status,
        "promotion_eligible": status in {"champion", "challenger"} and not failed and not insufficient,
        "failed_gates": failed,
        "insufficient_gates": insufficient,
        "gates": normalized,
        "paper_trading_only": True,
        "eligible_for_live_execution": False,
    }


def validate_report_identity(
    report: Mapping[str, Any],
    *,
    schema: str,
    as_of: str,
    timeframe: str,
    giveback_pct: float | None = None,
) -> None:
    if report.get("schema_version") != schema:
        raise ValueError(f"report schema mismatch: expected {schema}, got {report.get('schema_version')}")
    if report.get("as_of") != as_of:
        raise ValueError(f"report as_of mismatch: expected {as_of}, got {report.get('as_of')}")
    if report.get("timeframe") != timeframe:
        raise ValueError(f"report timeframe mismatch: expected {timeframe}, got {report.get('timeframe')}")
    if (
        report.get("paper_trading_only") is not True
        or report.get("no_execution_signals") is not True
        or report.get("does_not_modify_official_scores") is not True
    ):
        raise ValueError("report must be paper-only with no execution signals and protected official scores")
    validate_no_executable_instructions(report, context="report")
    if giveback_pct is not None:
        actual = _number((report.get("parameters") or {}).get("applied_giveback_pct"))
        if actual != giveback_pct:
            raise ValueError(f"report giveback mismatch: expected {giveback_pct}, got {actual}")


def validate_profit_report_cohort(reports: Mapping[float, Mapping[str, Any]]) -> None:
    if set(reports) != {2.0, 3.0}:
        raise ValueError("profit cohort requires exactly the declared 2% and 3% giveback reports")
    signatures = []
    for threshold, report in sorted(reports.items()):
        snapshot_label = report.get("snapshot_label")
        calendar_source = report.get("calendar_source")
        candidate_source = report.get("candidate_source")
        windows = report.get("windows") or {}
        if not snapshot_label or not calendar_source or not isinstance(candidate_source, Mapping) or not candidate_source.get("candidate_root"):
            raise ValueError(f"profit cohort identity is incomplete for giveback {threshold:g}%")
        window_signature = {}
        for window_id in ("all_history", "recent_60", "recent_120", "holdout"):
            window = windows.get(window_id) or {}
            dates = window.get("dates")
            if not isinstance(dates, list):
                raise ValueError(f"profit cohort window identity is incomplete for {window_id} at giveback {threshold:g}%")
            window_signature[window_id] = list(dates)
        signatures.append(
            {
                "snapshot_label": snapshot_label,
                "calendar_source": calendar_source,
                "candidate_source": dict(candidate_source),
                "windows": window_signature,
            }
        )
    if any(signature != signatures[0] for signature in signatures[1:]):
        raise ValueError("profit cohort mismatch between declared giveback reports")


def validate_report_strategy_set(report: Mapping[str, Any], *, schema: str) -> None:
    if schema == "timing_nonstationary_entry_audit.v1":
        if set(report.get("versions") or {}) != {ENTRY_BASELINE_ID, *ENTRY_CANDIDATE_IDS}:
            raise ValueError("entry strategy set must be exact")
    elif schema == "timing_nonstationary_profit_exit_audit.v1":
        if set(report.get("candidates") or {}) != PROFIT_REPORT_IDS:
            raise ValueError("profit strategy set must be exact")
    elif schema == "timing_nonstationary_stop_exit_audit.v1":
        if set(report.get("factors") or {}) != set(STOP_FACTOR_IDS):
            raise ValueError("stop factor set must be exact")


def validate_input_topology(
    *,
    entry_reports: Mapping[str, Path],
    profit_reports: Mapping[str, Mapping[float, Path]],
    stop_reports: Mapping[str, Path],
) -> None:
    expected_timeframes = {"1m", "5m"}
    if set(entry_reports) != expected_timeframes:
        raise ValueError("entry report topology must contain exactly 1m and 5m")
    if set(profit_reports) != expected_timeframes or any(
        set(paths_by_threshold) != {2.0, 3.0}
        for paths_by_threshold in profit_reports.values()
    ):
        raise ValueError("profit report topology must contain exactly 1m/5m x 2%/3%")
    if set(stop_reports) != expected_timeframes:
        raise ValueError("stop report topology must contain exactly 1m and 5m")


def validate_expected_report_sha_topology(
    *,
    entry_sha256: Mapping[str, str],
    profit_sha256: Mapping[str, Mapping[float, str]],
    stop_sha256: Mapping[str, str],
) -> None:
    expected_timeframes = {"1m", "5m"}
    if set(entry_sha256) != expected_timeframes:
        raise ValueError("expected entry SHA topology must contain exactly 1m and 5m")
    if set(profit_sha256) != expected_timeframes or any(
        set(values) != {2.0, 3.0} for values in profit_sha256.values()
    ):
        raise ValueError("expected profit SHA topology must contain exactly 1m/5m x 2%/3%")
    if set(stop_sha256) != expected_timeframes:
        raise ValueError("expected stop SHA topology must contain exactly 1m and 5m")
    for context, value in [
        *((f"entry {timeframe}", value) for timeframe, value in entry_sha256.items()),
        *(
            (f"profit {timeframe} {threshold:g}%", value)
            for timeframe, values in profit_sha256.items()
            for threshold, value in values.items()
        ),
        *((f"stop {timeframe}", value) for timeframe, value in stop_sha256.items()),
    ]:
        if not _is_sha256(value):
            raise ValueError(f"expected {context} audit SHA is invalid")


def validate_expected_report_sha256(path: Path, expected_sha256: str, *, context: str) -> str:
    if not _is_sha256(expected_sha256):
        raise ValueError(f"{context} caller-bound audit SHA is invalid")
    actual_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual_sha256 != expected_sha256.lower():
        raise ValueError(f"{context} caller-bound audit SHA mismatch")
    return actual_sha256


def _load_expected_report(
    path: Path,
    expected_sha256: str,
    *,
    context: str,
) -> tuple[dict[str, Any], str]:
    if not _is_sha256(expected_sha256):
        raise ValueError(f"{context} caller-bound audit SHA is invalid")
    report, actual_sha256 = load_strict_json_with_sha256(path)
    if actual_sha256 != expected_sha256.lower():
        raise ValueError(f"{context} caller-bound audit SHA mismatch")
    if not isinstance(report, dict):
        raise ValueError(f"{context} audit report must be a JSON object")
    return report, actual_sha256


def validate_cross_report_source_identity(
    reports: Mapping[str, Mapping[str, Any]],
    *,
    candidate_root: Path,
    candidate_source_root: Path,
    selection_validation_root: Path,
    timeframe: str,
    as_of: str,
    expected_calendar_path: Path,
    expected_calendar_sha256: str,
    source_snapshot_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if set(reports) != {"entry", "profit:2pct", "profit:3pct", "stop"}:
        raise ValueError("cross-report source identity requires entry, 2%/3% profit, and stop reports")
    candidate_validation_kwargs: dict[str, Any] = {
        "source_root": candidate_source_root,
        "timeframe": timeframe,
        "start": None,
        "end": as_of,
    }
    if source_snapshot_identity is not None:
        candidate_validation_kwargs["source_snapshot_identity"] = (
            source_snapshot_identity
        )
    current = validate_candidate_root_identity(
        candidate_root,
        **candidate_validation_kwargs,
    )
    candidate_dates = list(current.get("document_dates") or [])
    selection_anchor = _report_selection_source_identity(reports["entry"])
    selection_start = selection_anchor.get("start")
    selection_end = selection_anchor.get("end")
    if selection_end != as_of:
        raise ValueError("entry selection source end must equal decision as_of")
    if selection_start is not None and candidate_dates and str(selection_start) > min(candidate_dates):
        raise ValueError("entry selection source start is later than current candidate coverage")
    current_selection = validate_selection_source_identity(
        selection_validation_root,
        start=selection_start,
        end=selection_end,
    )
    expected_bar_source = {
        "1m": "complete_1m_session",
        "5m": "aggregated_from_complete_1m_session",
    }.get(timeframe)
    if expected_bar_source is None:
        raise ValueError(f"unsupported decision candidate timeframe: {timeframe}")
    expected_calendar_path = Path(expected_calendar_path)
    if not expected_calendar_path.exists():
        raise ValueError("caller-bound calendar path does not exist")
    expected_calendar_artifact, actual_expected_calendar_sha256 = (
        load_strict_json_with_sha256(expected_calendar_path)
    )
    if actual_expected_calendar_sha256.lower() != str(
        expected_calendar_sha256 or ""
    ).lower():
        raise ValueError("caller-bound calendar SHA mismatch")
    current_expected_calendar = validate_trading_calendar_artifact(
        expected_calendar_artifact,
        path=expected_calendar_path,
        sha256=actual_expected_calendar_sha256,
        as_of=as_of,
    )
    calendar_identity: dict[str, str] | None = None
    for source_id, report in sorted(reports.items()):
        identity, reported_candidate_root = _report_candidate_source_identity(report)
        if not reported_candidate_root or not _same_path(reported_candidate_root, candidate_root):
            raise ValueError(f"{source_id} candidate root does not match caller-bound candidate root")
        if not _same_path(identity.get("candidate_root"), candidate_root):
            raise ValueError(f"{source_id} candidate root identity mismatch")
        if not _same_path(identity.get("source_root"), candidate_source_root):
            raise ValueError(f"{source_id} candidate source root identity mismatch")
        if identity.get("bar_interval") != timeframe or identity.get("bar_source") != expected_bar_source:
            raise ValueError(f"{source_id} candidate cadence identity mismatch")
        for field in (
            "manifest_sha256",
            "document_count",
            "document_dates",
            "complete_candidate_dates",
            "complete_candidate_count",
            "invalid_candidate_count",
        ):
            if identity.get(field) != current.get(field):
                raise ValueError(f"{source_id} candidate {field.replace('_', ' ')} mismatch with current manifest")
        selection_identity = _report_selection_source_identity(report)
        if not _same_path(
            selection_identity.get("selection_validation_root"),
            selection_validation_root,
        ):
            raise ValueError(f"{source_id} selection source root mismatch")
        for field in ("start", "end", "manifest_sha256", "document_count", "document_dates"):
            if selection_identity.get(field) != current_selection.get(field):
                raise ValueError(
                    f"{source_id} selection source {field.replace('_', ' ')} mismatch with current manifest"
                )
        calendar = report.get("calendar_source")
        if not isinstance(calendar, Mapping):
            raise ValueError(f"{source_id} calendar identity is missing")
        calendar_path_value = str(calendar.get("path") or "")
        calendar_sha256 = str(calendar.get("sha256") or "")
        if not calendar_path_value or not calendar_sha256:
            raise ValueError(f"{source_id} calendar path or SHA is missing")
        calendar_path = Path(calendar_path_value)
        if not _same_path(calendar_path, expected_calendar_path):
            raise ValueError(f"{source_id} caller-bound calendar path mismatch")
        if calendar_sha256.lower() != actual_expected_calendar_sha256.lower():
            raise ValueError(f"{source_id} caller-bound calendar SHA mismatch")
        validate_trading_calendar_identity(
            calendar,
            current_expected_calendar,
            context=source_id,
        )
        normalized_calendar = {
            "path": current_expected_calendar["path"],
            "sha256": current_expected_calendar["sha256"],
        }
        if calendar_identity is None:
            calendar_identity = normalized_calendar
        elif (
            not _same_path(calendar_identity["path"], normalized_calendar["path"])
            or calendar_identity["sha256"] != normalized_calendar["sha256"]
        ):
            raise ValueError(f"{source_id} calendar identity differs across reports")
    return {
        "status": "validated",
        "timeframe": timeframe,
        "report_count": len(reports),
        "current_candidate_source_identity": current,
        "current_selection_source_identity": current_selection,
        "calendar_source": calendar_identity,
    }


def validate_cross_timeframe_source_identity(
    validations: Mapping[str, Mapping[str, Any]],
    *,
    source_snapshots: Mapping[str, Mapping[str, Any]],
) -> None:
    """Reject a final decision assembled from different 1m/5m source states."""
    if set(validations) != {"1m", "5m"} or set(source_snapshots) != {"1m", "5m"}:
        raise ValueError("cross-timeframe source identity requires 1m and 5m")
    left = validations["1m"]
    right = validations["5m"]
    left_selection = left.get("current_selection_source_identity")
    right_selection = right.get("current_selection_source_identity")
    if not isinstance(left_selection, Mapping) or not isinstance(
        right_selection, Mapping
    ):
        raise ValueError("selection identity is missing across timeframes")
    if not _same_path(
        str(left_selection.get("selection_validation_root") or ""),
        str(right_selection.get("selection_validation_root") or ""),
    ) or any(
        left_selection.get(field) != right_selection.get(field)
        for field in (
            "start",
            "end",
            "manifest_sha256",
            "document_count",
            "document_dates",
        )
    ):
        raise ValueError("selection identity differs across timeframes")
    left_calendar = left.get("calendar_source")
    right_calendar = right.get("calendar_source")
    if not isinstance(left_calendar, Mapping) or not isinstance(right_calendar, Mapping):
        raise ValueError("calendar identity is missing across timeframes")
    if (
        not _same_path(
            str(left_calendar.get("path") or ""),
            str(right_calendar.get("path") or ""),
        )
        or left_calendar.get("sha256") != right_calendar.get("sha256")
    ):
        raise ValueError("calendar identity differs across timeframes")
    left_source = source_snapshots["1m"]
    right_source = source_snapshots["5m"]
    if not _same_path(
        str(left_source.get("source_root") or ""),
        str(right_source.get("source_root") or ""),
    ) or any(
        left_source.get(field) != right_source.get(field)
        for field in ("manifest_sha256", "document_count", "document_dates")
    ):
        raise ValueError("candidate source snapshot differs across timeframes")


def _report_candidate_source_identity(
    report: Mapping[str, Any],
) -> tuple[Mapping[str, Any], str]:
    schema = report.get("schema_version")
    if schema == "timing_nonstationary_entry_audit.v1":
        label_source = report.get("label_source") or {}
        identity = label_source.get("revalidated_candidate_source_identity") if isinstance(label_source, Mapping) else None
        candidate_root = str(report.get("candidate_root") or "")
    elif schema == "timing_nonstationary_profit_exit_audit.v1":
        candidate_source = report.get("candidate_source") or {}
        identity = candidate_source.get("candidate_source_identity") if isinstance(candidate_source, Mapping) else None
        candidate_root = str(candidate_source.get("candidate_root") or "") if isinstance(candidate_source, Mapping) else ""
    elif schema == "timing_nonstationary_stop_exit_audit.v1":
        identity = report.get("candidate_source_identity")
        candidate_root = str(report.get("candidate_root") or "")
    else:
        raise ValueError(f"unsupported report schema for candidate identity: {schema}")
    if not isinstance(identity, Mapping) or identity.get("status") != "validated":
        raise ValueError("report candidate source identity is missing or unvalidated")
    return identity, candidate_root


def _report_selection_source_identity(report: Mapping[str, Any]) -> Mapping[str, Any]:
    schema = report.get("schema_version")
    if schema == "timing_nonstationary_entry_audit.v1":
        label_source = report.get("label_source") or {}
        identity = (
            label_source.get("revalidated_selection_source_identity")
            if isinstance(label_source, Mapping)
            else None
        )
    elif schema == "timing_nonstationary_profit_exit_audit.v1":
        candidate_source = report.get("candidate_source") or {}
        identity = (
            candidate_source.get("selection_source_identity")
            if isinstance(candidate_source, Mapping)
            else None
        )
    elif schema == "timing_nonstationary_stop_exit_audit.v1":
        identity = report.get("selection_source_identity")
    else:
        raise ValueError(f"unsupported report schema for selection source identity: {schema}")
    if not isinstance(identity, Mapping) or identity.get("status") != "validated":
        raise ValueError("report selection source identity is missing or unvalidated")
    return identity


def _same_path(left: Any, right: Any) -> bool:
    if not str(left or "") or not str(right or ""):
        return False
    return str(Path(str(left)).resolve()).casefold() == str(Path(str(right)).resolve()).casefold()


def _is_sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(character in "0123456789abcdefABCDEF" for character in text)


def build_dynamic_recommendations(decisions: list[Mapping[str, Any]]) -> dict[str, Any]:
    paper_stack = {
        candidate_type: {"champions": [], "challengers": [], "observe": [], "insufficient": [], "rejected": []}
        for candidate_type in ("entry", "profit_exit", "stop_exit")
    }
    blockers: dict[str, list[str]] = {}
    for item in decisions:
        candidate_id = str(item.get("candidate_id") or "")
        candidate_type = str(item.get("candidate_type") or "")
        stack = paper_stack.setdefault(candidate_type, {"champions": [], "challengers": [], "observe": [], "insufficient": [], "rejected": []})
        decision_status = item.get("decision_status")
        if decision_status == "champion":
            stack["champions"].append(candidate_id)
        elif decision_status == "challenger":
            stack["challengers"].append(candidate_id)
        elif decision_status == "rejected":
            stack["rejected"].append(candidate_id)
        elif decision_status == "insufficient_evidence":
            stack["insufficient"].append(candidate_id)
        else:
            stack["observe"].append(candidate_id)
        for gate in list(item.get("failed_gates") or []) + list(item.get("insufficient_gates") or []):
            blockers.setdefault(str(gate), []).append(candidate_id)
    return {"paper_stack": paper_stack, "blockers": dict(sorted(blockers.items()))}


def audit_nonstationary_entry_exit_decision(
    *,
    entry_reports: Mapping[str, Path],
    profit_reports: Mapping[str, Mapping[float, Path]],
    stop_reports: Mapping[str, Path],
    expected_entry_report_sha256: Mapping[str, str],
    expected_profit_report_sha256: Mapping[str, Mapping[float, str]],
    expected_stop_report_sha256: Mapping[str, str],
    candidate_roots: Mapping[str, Path],
    candidate_source_root: Path,
    selection_validation_root: Path,
    expected_calendar_path: Path,
    expected_calendar_sha256: str,
    expected_records_provenance: Mapping[str, Mapping[str, Any]],
    output_dir: Path,
    as_of: str,
) -> dict[str, Any]:
    validate_input_topology(
        entry_reports=entry_reports,
        profit_reports=profit_reports,
        stop_reports=stop_reports,
    )
    validate_expected_report_sha_topology(
        entry_sha256=expected_entry_report_sha256,
        profit_sha256=expected_profit_report_sha256,
        stop_sha256=expected_stop_report_sha256,
    )
    normalized_expected_records = validate_expected_records_provenance(
        expected_records_provenance
    )
    if set(candidate_roots) != {"1m", "5m"}:
        raise ValueError("candidate root topology must contain exactly 1m and 5m")
    decisions = []
    source_reports: dict[str, Any] = {"entry": {}, "profit": {}, "stop": {}}
    evaluation_tail_reports: dict[str, Mapping[str, Any]] = {}
    cohort_reports: dict[str, dict[str, Mapping[str, Any]]] = {"1m": {}, "5m": {}}
    records_entry_path_manifests: list[dict[tuple[str, str, str], str]] = []
    for timeframe, path in entry_reports.items():
        expected_sha256 = expected_entry_report_sha256[timeframe]
        report, report_sha256 = _load_expected_report(
            path,
            expected_sha256,
            context=f"entry {timeframe}",
        )
        validate_report_identity(
            report,
            schema="timing_nonstationary_entry_audit.v1",
            as_of=as_of,
            timeframe=timeframe,
        )
        validate_report_strategy_set(report, schema="timing_nonstationary_entry_audit.v1")
        entry_path_snapshot: dict[tuple[str, str, str], str] = {}
        source_reports["entry"][timeframe] = _report_provenance(
            path,
            report,
            expected_report_sha256=expected_sha256,
            actual_report_sha256=report_sha256,
            entry_path_manifest_out=entry_path_snapshot,
            **_expected_records_kwargs(
                normalized_expected_records,
                f"entry:{timeframe}",
            ),
        )
        records_entry_path_manifests.append(entry_path_snapshot)
        cohort_reports[timeframe]["entry"] = report
        evaluation_tail_reports[f"entry:{timeframe}"] = report
        decisions.extend(_entry_decisions(report, timeframe))
    for timeframe, paths_by_threshold in profit_reports.items():
        reports = {}
        report_sha256s = {}
        for threshold, path in paths_by_threshold.items():
            expected_sha256 = expected_profit_report_sha256[timeframe][threshold]
            reports[threshold], report_sha256s[threshold] = _load_expected_report(
                path,
                expected_sha256,
                context=f"profit {timeframe} {threshold:g}%",
            )
        for threshold, report in reports.items():
            validate_report_identity(
                report,
                schema="timing_nonstationary_profit_exit_audit.v1",
                as_of=as_of,
                timeframe=timeframe,
                giveback_pct=threshold,
            )
            validate_report_strategy_set(report, schema="timing_nonstationary_profit_exit_audit.v1")
        validate_profit_report_cohort(reports)
        source_reports["profit"][timeframe] = {}
        for threshold, path in paths_by_threshold.items():
            entry_path_snapshot = {}
            source_reports["profit"][timeframe][str(threshold)] = _report_provenance(
                path,
                reports[threshold],
                expected_report_sha256=expected_profit_report_sha256[timeframe][threshold],
                actual_report_sha256=report_sha256s[threshold],
                entry_path_manifest_out=entry_path_snapshot,
                **_expected_records_kwargs(
                    normalized_expected_records,
                    f"profit:{timeframe}:{threshold:g}pct",
                ),
            )
            records_entry_path_manifests.append(entry_path_snapshot)
        for threshold, report in reports.items():
            evaluation_tail_reports[f"profit:{timeframe}:{threshold:g}pct"] = report
            cohort_reports[timeframe][f"profit:{threshold:g}pct"] = report
        decisions.extend(_profit_decisions(reports, timeframe))
    merge_entry_path_manifests(
        records_entry_path_manifests,
        context="final upstream records",
    )
    for timeframe, path in stop_reports.items():
        expected_sha256 = expected_stop_report_sha256[timeframe]
        report, report_sha256 = _load_expected_report(
            path,
            expected_sha256,
            context=f"stop {timeframe}",
        )
        validate_report_identity(
            report,
            schema="timing_nonstationary_stop_exit_audit.v1",
            as_of=as_of,
            timeframe=timeframe,
        )
        validate_report_strategy_set(report, schema="timing_nonstationary_stop_exit_audit.v1")
        stop_provenance = _report_provenance(
            path,
            report,
            expected_report_sha256=expected_sha256,
            actual_report_sha256=report_sha256,
            **_expected_records_kwargs(
                normalized_expected_records,
                f"stop:{timeframe}",
            ),
        )
        entry_provenance = source_reports["entry"][timeframe]
        if (
            not _same_path(
                stop_provenance["records_path"],
                entry_provenance["records_path"],
            )
            or str(stop_provenance["records_sha256"]).lower()
            != str(entry_provenance["records_sha256"]).lower()
        ):
            raise ValueError(f"stop {timeframe} must reuse entry records")
        source_reports["stop"][timeframe] = stop_provenance
        cohort_reports[timeframe]["stop"] = report
        evaluation_tail_reports[f"stop:{timeframe}"] = report
        decisions.extend(_stop_decisions(report, timeframe))
    source_identity_validation = {}
    source_snapshots = {}
    for timeframe in ("1m", "5m"):
        source_snapshot = {}
        source_identity_validation[timeframe] = validate_cross_report_source_identity(
            cohort_reports[timeframe],
            candidate_root=candidate_roots[timeframe],
            candidate_source_root=candidate_source_root,
            selection_validation_root=selection_validation_root,
            timeframe=timeframe,
            as_of=as_of,
            expected_calendar_path=expected_calendar_path,
            expected_calendar_sha256=expected_calendar_sha256,
            source_snapshot_identity=source_snapshot,
        )
        source_snapshots[timeframe] = source_snapshot
    validate_cross_timeframe_source_identity(
        source_identity_validation,
        source_snapshots=source_snapshots,
    )
    status_counts = Counter(item["decision_status"] for item in decisions)
    dynamic = build_dynamic_recommendations(decisions)
    report = {
        "schema_version": "timing_nonstationary_entry_exit_decision.v1",
        "as_of": as_of,
        "policy": {
            "recent_dominant": True,
            "recent_windows_days": [60, 120],
            "holdout_days": 20,
            "holdout_mode": "observed_evaluation_tail",
            "holdout_blind": False,
            "holdout_eligible_for_oos_claim": False,
            "prospective_freeze_required": True,
            "long_history_role": "catastrophic_risk_veto_only",
            "concentration_limits": CONCENTRATION_LIMITS,
            "failed_gate_action": "observe",
            "insufficient_gate_action": "insufficient_evidence",
        },
        "summary": {
            "candidate_count": len(decisions),
            "decision_status_counts": dict(status_counts),
            "paper_champions": [item["candidate_id"] for item in decisions if item["decision_status"] == "champion"],
            "hard_gate_challengers": [item["candidate_id"] for item in decisions if item["decision_status"] == "challenger"],
            "live_ready_candidate_count": 0,
        },
        "evaluation_tail": _evaluation_tail_summary(evaluation_tail_reports),
        "recommended_paper_stack": dynamic["paper_stack"],
        "remaining_blockers": dynamic["blockers"],
        "decisions": decisions,
        "source_reports": source_reports,
        "caller_bound_report_sha256": {
            "entry": {key: value.lower() for key, value in expected_entry_report_sha256.items()},
            "profit": {
                timeframe: {str(key): value.lower() for key, value in values.items()}
                for timeframe, values in expected_profit_report_sha256.items()
            },
            "stop": {key: value.lower() for key, value in expected_stop_report_sha256.items()},
        },
        "caller_bound_calendar": {
            "path": str(expected_calendar_path),
            "sha256": str(expected_calendar_sha256).lower(),
        },
        "caller_bound_records_provenance": normalized_expected_records,
        "source_identity_validation": source_identity_validation,
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
        "live_trading_ready": False,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"nonstationary_entry_exit_decision_{as_of}.json"
    markdown_path = output_dir / f"nonstationary_entry_exit_decision_{as_of}.md"
    archived_json_path = write_text_preserving_previous(
        json_path,
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),
    )
    archived_markdown_path = write_text_preserving_previous(markdown_path, _markdown(report))
    return {
        "status": "ok",
        "json_path": json_path,
        "markdown_path": markdown_path,
        "archived_previous_paths": [
            path for path in (archived_json_path, archived_markdown_path) if path is not None
        ],
        "report": report,
    }


def _entry_decisions(report: Mapping[str, Any], timeframe: str) -> list[dict[str, Any]]:
    versions = report.get("versions") or {}
    baseline = versions.get(ENTRY_BASELINE_ID) or {}
    decisions = []
    for version_id in ENTRY_CANDIDATE_IDS:
        candidate = versions.get(version_id) or {}
        risk_points = set((candidate.get("overfit_risk") or {}).get("risk_points") or [])
        gates = {
            "recent_60": _entry_window_gate(candidate, baseline, "recent_60"),
            "recent_120": _entry_window_gate(candidate, baseline, "recent_120"),
            "holdout": _governed_holdout_gate(
                report.get("holdout_evidence") or {},
                _positive_holdout_gate((candidate.get("by_window") or {}).get("holdout") or {}),
            ),
            "regime": _entry_regime_gate(candidate.get("regime") or {}, report.get("current_regime") or {}),
            "perturbation": _entry_perturbation_gate(candidate.get("perturbation") or {}),
            "concentration": _concentration_gate(candidate.get("concentration") or {}),
            "complexity": _gate(
                "fail" if "complexity_not_justified" in risk_points else "pass",
                "Ablation must not improve the candidate." if "complexity_not_justified" in risk_points else "No ablation veto detected.",
                risk_points=sorted(risk_points),
            ),
            "walk_forward": _entry_walk_forward_gate(candidate.get("walk_forward") or {}),
            "redundancy": _entry_redundancy_gate(candidate.get("factor_correlation") or {}),
            "long_history_veto": _gate("insufficient", "No 2024/2025 strategy-linked entry record is available."),
            "next_bar_fill": _entry_fill_gate(report, candidate, timeframe=timeframe),
            "friction": _entry_friction_gate(report),
            "date_coverage": _candidate_date_coverage_gate(report.get("windows") or {}),
        }
        decision = evaluate_candidate_hard_gates(
            candidate_id=f"entry:{timeframe}:{version_id}",
            candidate_type="entry",
            timeframe=timeframe,
            gates=gates,
            passing_status="champion",
            required_gates=REQUIRED_HARD_GATES | {"complexity", "walk_forward", "redundancy", "date_coverage"},
        )
        decision["version_id"] = version_id
        decisions.append(decision)
    return decisions


def _profit_decisions(reports: Mapping[float, Mapping[str, Any]], timeframe: str) -> list[dict[str, Any]]:
    decisions = []
    for threshold, report in sorted(reports.items()):
        candidate = ((report.get("candidates") or {}).get(PROFIT_CANDIDATE_ID) or {})
        alternate_reports = [item for value, item in reports.items() if value != threshold]
        gates = {
            "recent_60": _profit_window_gate(candidate, "recent_60"),
            "recent_120": _profit_window_gate(candidate, "recent_120"),
            "holdout": _governed_holdout_gate(
                report.get("holdout_evidence") or {},
                _profit_window_gate(candidate, "holdout"),
            ),
            "regime": _profit_regime_gate(candidate.get("by_regime") or {}, report.get("current_regime") or {}),
            "walk_forward": _profit_walk_forward_gate(candidate.get("fold_stability") or {}),
            "perturbation": _profit_threshold_robustness_gate(alternate_reports),
            "concentration": _concentration_gate(
                (((candidate.get("by_window") or {}).get("recent_120") or {}).get("concentration") or {})
            ),
            "long_history_veto": _profit_long_history_gate(candidate.get("long_history_veto") or {}),
            "next_bar_fill": _profit_fill_gate(candidate.get("by_window") or {}),
            "friction": _profit_friction_gate(report, candidate),
            "date_coverage": _candidate_date_coverage_gate(report.get("windows") or {}),
        }
        decision = evaluate_candidate_hard_gates(
            candidate_id=f"profit:{timeframe}:exit_v4_giveback_{threshold:g}pct",
            candidate_type="profit_exit",
            timeframe=timeframe,
            gates=gates,
            passing_status="challenger",
            required_gates=REQUIRED_HARD_GATES | {"walk_forward", "date_coverage"},
        )
        decision["giveback_pct"] = threshold
        decisions.append(decision)
    return decisions


def _stop_decisions(report: Mapping[str, Any], timeframe: str) -> list[dict[str, Any]]:
    factors = report.get("factors") or {}
    long_evidence = report.get("long_history_veto_evidence") or {}
    long_factors = (long_evidence.get("factors") or {})
    decisions = []
    for factor_id in STOP_FACTOR_IDS:
        factor = factors.get(factor_id) or {}
        by_window = factor.get("by_window") or {}
        gates = {
            "recent_60": _stop_window_gate(by_window.get("recent_60") or {}),
            "recent_120": _stop_window_gate(by_window.get("recent_120") or {}),
            "holdout": _governed_holdout_gate(
                report.get("holdout_evidence") or {},
                _stop_window_gate(by_window.get("holdout") or {}),
            ),
            "regime": _gate("insufficient", "Current stop-path records do not carry a validated market-regime label."),
            "perturbation": _gate("insufficient", "No +/-10% stop-factor threshold perturbation was selected after holdout isolation."),
            "concentration": _concentration_gate((by_window.get("recent_120") or {}).get("concentration") or {}),
            "long_history_veto": _stop_long_history_gate(long_evidence, long_factors.get(factor_id) or {}, factor_id=factor_id),
            "next_bar_fill": _stop_fill_gate(by_window),
            "friction": _gate("insufficient", "Stop-path audit has no independent fee/slippage sensitivity result."),
            "strategy_linkage": _gate(
                "pass"
                if (report.get("summary") or {}).get("strategy_linked_entry_paths")
                and (report.get("summary") or {}).get("entry_reference_is_causal_simulated_fill")
                else "insufficient",
                "Stop factors must be evaluated on strategy-linked paths with a causal next-session simulated entry fill.",
            ),
            "date_coverage": _candidate_date_coverage_gate(report.get("windows") or {}),
        }
        decision = evaluate_candidate_hard_gates(
            candidate_id=f"stop:{timeframe}:{factor_id}",
            candidate_type="stop_exit",
            timeframe=timeframe,
            gates=gates,
            passing_status="challenger",
            required_gates=REQUIRED_HARD_GATES | {"strategy_linkage", "date_coverage"},
        )
        decision["factor_id"] = factor_id
        decisions.append(decision)
    return decisions


def _entry_window_gate(candidate: Mapping[str, Any], baseline: Mapping[str, Any], window_id: str) -> dict[str, Any]:
    item = (candidate.get("by_window") or {}).get(window_id) or {}
    reference = (baseline.get("by_window") or {}).get(window_id) or {}
    if item.get("window_status") != "ok":
        return _gate("insufficient", f"{window_id} does not contain the required trading days.", date_count=item.get("window_date_count"))
    coverage_gate = _entry_date_coverage_gate(item)
    if coverage_gate["status"] != "pass":
        return coverage_gate
    candidate_avg = _number(item.get("selected_avg_return_pct"))
    baseline_avg = _number(reference.get("selected_avg_return_pct"))
    if not item.get("is_valid") or candidate_avg is None or baseline_avg is None:
        return _gate("insufficient", f"{window_id} lacks a valid selected sample.")
    delta = candidate_avg - baseline_avg
    return _gate("pass" if delta > 0 else "fail", "Candidate must outperform v26 in the declared window.", candidate_avg=candidate_avg, baseline_avg=baseline_avg, delta=_round(delta))


def _positive_holdout_gate(item: Mapping[str, Any]) -> dict[str, Any]:
    if item.get("window_status") != "ok":
        return _gate("insufficient", "Holdout sample is not valid.", selected_count=item.get("selected_count"))
    coverage_gate = _entry_date_coverage_gate(item)
    if coverage_gate["status"] != "pass":
        return coverage_gate
    if not item.get("is_valid"):
        return _gate("insufficient", "Holdout sample is not valid.", selected_count=item.get("selected_count"))
    value = _number(item.get("selected_avg_return_pct"))
    if value is None:
        return _gate("insufficient", "Holdout return is unavailable.")
    return _gate("pass" if value > 0 else "fail", "Holdout direction must remain positive.", avg_return_pct=value)


def _entry_date_coverage_gate(item: Mapping[str, Any]) -> dict[str, Any]:
    window_count = item.get("window_date_count")
    source_count = item.get("source_document_date_count")
    complete_count = item.get("complete_candidate_date_count")
    source_rate = _number(item.get("source_document_date_coverage_rate"))
    complete_rate = _number(item.get("complete_candidate_date_coverage_rate"))
    evidence = {
        "window_date_count": window_count,
        "source_document_date_count": source_count,
        "complete_candidate_date_count": complete_count,
        "source_document_date_coverage_rate": source_rate,
        "complete_candidate_date_coverage_rate": complete_rate,
        "candidate_date_coverage_status": item.get("candidate_date_coverage_status"),
    }
    complete = (
        isinstance(window_count, int)
        and window_count > 0
        and source_count == window_count
        and complete_count == window_count
        and source_rate == 1.0
        and complete_rate == 1.0
        and item.get("candidate_date_coverage_status") == "ok"
    )
    return _gate(
        "pass" if complete else "insufficient",
        "Every trading date in the evaluation window requires a source document and at least one complete-session candidate.",
        **evidence,
    )


def _candidate_date_coverage_gate(windows: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    evidence = {}
    incomplete = []
    for window_id in ("recent_60", "recent_120", "holdout"):
        item = windows.get(window_id) or {}
        date_count = item.get("date_count")
        source_count = item.get("source_document_date_count")
        complete_count = item.get("complete_candidate_date_count")
        source_rate = _number(item.get("source_document_date_coverage_rate"))
        complete_rate = _number(item.get("complete_candidate_date_coverage_rate"))
        complete = (
            isinstance(date_count, int)
            and date_count > 0
            and source_count == date_count
            and complete_count == date_count
            and source_rate == 1.0
            and complete_rate == 1.0
            and item.get("candidate_date_coverage_status") == "ok"
        )
        evidence[window_id] = {
            "date_count": date_count,
            "source_document_date_count": source_count,
            "complete_candidate_date_count": complete_count,
            "source_document_date_coverage_rate": source_rate,
            "complete_candidate_date_coverage_rate": complete_rate,
            "candidate_date_coverage_status": item.get("candidate_date_coverage_status"),
        }
        if not complete:
            incomplete.append(window_id)
    return _gate(
        "pass" if not incomplete else "insufficient",
        "Every required window needs 100% source-document and complete-candidate date coverage.",
        windows=evidence,
        incomplete_windows=incomplete,
    )


def _governed_holdout_gate(
    evidence: Mapping[str, Any],
    observed_metric_gate: Mapping[str, Any],
) -> dict[str, Any]:
    if evidence.get("blind") is not True or evidence.get("eligible_for_oos_claim") is not True:
        return _gate(
            "insufficient",
            "The current evaluation tail was observed during strategy iteration and is not a blind holdout.",
            holdout_evidence=dict(evidence),
            observed_metric_gate=dict(observed_metric_gate),
        )
    return dict(observed_metric_gate)


def _entry_regime_gate(
    regimes: Mapping[str, Mapping[str, Any]],
    current_regime: Mapping[str, Any],
) -> dict[str, Any]:
    regime = str(current_regime.get("regime") or "")
    if current_regime.get("status") != "ok" or regime not in {"strong", "range", "weak"}:
        return _gate("insufficient", "Current market regime is not bound to the latest trading session.", current_regime=dict(current_regime))
    item = regimes.get(regime) or {}
    if (item.get("selected_count") or 0) < 5:
        return _gate("insufficient", "Current market regime has fewer than five selected records.", current_regime=regime, selected_count=item.get("selected_count"))
    value = _number(item.get("selected_avg_return_pct"))
    if value is None:
        return _gate("insufficient", "Current market regime lacks a finite return label.", current_regime=regime)
    return _gate("pass" if value > 0 else "fail", "The latest-session market regime must remain positive.", current_regime=regime, avg_return_pct=value)


def _entry_perturbation_gate(perturbation: Mapping[str, Any]) -> dict[str, Any]:
    variant_count = perturbation.get("variant_count")
    valid_variant_count = perturbation.get("valid_variant_count")
    if variant_count != 2 or valid_variant_count != 2 or perturbation.get("all_variants_valid") is not True:
        return _gate(
            "insufficient",
            "Both fixed +/-10% threshold variants require valid selected samples.",
            variant_count=variant_count,
            valid_variant_count=valid_variant_count,
        )
    rate = _number(perturbation.get("positive_variant_rate"))
    if rate is None:
        return _gate("insufficient", "Perturbation direction is unavailable.")
    return _gate("pass" if rate == 1.0 else "fail", "Both fixed +/-10% threshold variants must stay positive.", positive_variant_rate=rate)


def _entry_walk_forward_gate(walk_forward: Mapping[str, Any]) -> dict[str, Any]:
    folds = list(walk_forward.get("folds") or [])
    if walk_forward.get("fold_count") != 5 or len(folds) != 5:
        return _gate("insufficient", "Exactly five chronological walk-forward folds are required.", fold_count=walk_forward.get("fold_count"))
    invalid = [index + 1 for index, fold in enumerate(folds) if fold.get("is_valid") is not True]
    if invalid:
        return _gate("insufficient", "Every walk-forward fold requires a valid selected sample.", invalid_folds=invalid)
    values = [_number(fold.get("selected_avg_return_pct")) for fold in folds]
    if any(value is None for value in values):
        return _gate("insufficient", "A walk-forward fold is missing its selected return.", fold_returns=values)
    return _gate("pass" if all(value > 0 for value in values) else "fail", "All five walk-forward folds must preserve positive direction.", fold_returns=values)


def _entry_redundancy_gate(correlation: Mapping[str, Any]) -> dict[str, Any]:
    pair_count = correlation.get("pair_count")
    expected_pair_count = correlation.get("expected_pair_count")
    if (
        not isinstance(pair_count, int)
        or not isinstance(expected_pair_count, int)
        or expected_pair_count <= 0
        or pair_count != expected_pair_count
    ):
        return _gate(
            "insufficient",
            "Every declared factor pair requires finite correlation evidence.",
            pair_count=pair_count,
            expected_pair_count=expected_pair_count,
        )
    high_pairs = list(correlation.get("high_correlation_pairs") or [])
    return _gate(
        "fail" if high_pairs else "pass",
        "No factor pair may exceed the predeclared absolute-correlation threshold.",
        pair_count=pair_count,
        expected_pair_count=expected_pair_count,
        threshold=correlation.get("high_correlation_threshold"),
        high_correlation_pairs=high_pairs,
    )


def _entry_fill_gate(
    report: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    timeframe: str,
) -> dict[str, Any]:
    source = report.get("label_source") or {}
    if (
        source.get("mode") != "causal_next_session_open_to_close"
        or source.get("version_specific") is not True
        or source.get("source_bar_interval") != timeframe
    ):
        return _gate("insufficient", "Entry returns must come from version-specific next-session causal bars.", label_source=dict(source))
    fill_rates = {}
    for window_id in ("recent_60", "recent_120", "holdout"):
        item = (candidate.get("by_window") or {}).get(window_id) or {}
        if item.get("window_status") != "ok":
            return _gate("insufficient", f"{window_id} lacks the required trading-day window for entry fill validation.")
        expected = item.get("causal_entry_expected_count")
        valid = item.get("causal_entry_valid_count")
        rate = _number(item.get("causal_entry_fill_rate"))
        if not isinstance(expected, int) or expected < 5 or not isinstance(valid, int) or rate is None:
            return _gate(
                "insufficient",
                f"{window_id} has insufficient causal entry fill evidence.",
                expected_count=expected,
                valid_count=valid,
                fill_rate=rate,
            )
        fill_rates[window_id] = rate
    return _gate(
        "pass" if min(fill_rates.values()) >= 0.95 else "fail",
        "Causal next-session entry fill coverage must be at least 95% in every required window.",
        fill_rates=fill_rates,
    )


def _entry_friction_gate(report: Mapping[str, Any]) -> dict[str, Any]:
    parameters = report.get("parameters") or {}
    cost = _number(parameters.get("round_trip_cost_pct"))
    if cost is None or cost <= 0 or parameters.get("returns_net_of_round_trip_cost") is not True:
        return _gate(
            "insufficient",
            "Entry returns require a positive, explicitly applied round-trip cost.",
            round_trip_cost_pct=cost,
            returns_net_of_round_trip_cost=parameters.get("returns_net_of_round_trip_cost"),
        )
    return _gate("pass", "Entry returns are net of the declared round-trip friction.", round_trip_cost_pct=cost)


def _profit_window_gate(candidate: Mapping[str, Any], window_id: str) -> dict[str, Any]:
    item = (candidate.get("by_window") or {}).get(window_id) or {}
    if item.get("window_status") != "ok":
        return _gate("insufficient", f"{window_id} does not contain the required trading days.", date_count=item.get("window_date_count"))
    paired = (candidate.get("paired_vs_fixed_by_window") or {}).get(window_id) or {}
    if (paired.get("duplicate_policy_conflict_count") or 0) > 0:
        return _gate("fail", "Duplicate entry records disagree on policy outcomes.", paired=paired)
    if (paired.get("paired_record_count") or 0) < 5:
        return _gate("insufficient", f"{window_id} has fewer than five paired policy outcomes.", paired_count=paired.get("paired_record_count"))
    delta = _number(paired.get("avg_paired_delta_pct"))
    if delta is None:
        return _gate("insufficient", "Paired policy delta versus fixed exit is unavailable.")
    tail_ok = (paired.get("paired_tail_worsened_count") or 0) <= (paired.get("paired_tail_avoided_count") or 0)
    return _gate(
        "pass" if delta > 0 and tail_ok else "fail",
        "Dynamic profit policy must improve paired net return without worsening more tails than it avoids.",
        paired_delta_pct=delta,
        paired_tail_avoided_count=paired.get("paired_tail_avoided_count"),
        paired_tail_worsened_count=paired.get("paired_tail_worsened_count"),
    )


def _profit_regime_gate(
    regimes: Mapping[str, Mapping[str, Any]],
    current_regime: Mapping[str, Any],
) -> dict[str, Any]:
    regime = str(current_regime.get("regime") or "")
    if current_regime.get("status") != "ok" or regime not in {"strong", "range", "weak"}:
        return _gate("insufficient", "Current market regime is not bound to the latest trading session.", current_regime=dict(current_regime))
    item = regimes.get(regime) or {}
    if (item.get("duplicate_policy_conflict_count") or 0) > 0:
        return _gate("fail", "Current-regime records contain conflicting duplicate policy outcomes.", current_regime=regime)
    if (item.get("paired_record_count") or 0) < 5:
        return _gate("insufficient", "Current market regime has fewer than five paired policies.", current_regime=regime, paired_count=item.get("paired_record_count"))
    delta = _number(item.get("avg_paired_delta_pct"))
    if delta is None:
        return _gate("insufficient", "Current market regime lacks a finite paired delta.", current_regime=regime)
    tail_ok = (item.get("paired_tail_worsened_count") or 0) <= (item.get("paired_tail_avoided_count") or 0)
    return _gate(
        "pass" if delta > 0 and tail_ok else "fail",
        "The latest-session market regime must improve the same-entry fixed-policy counterfactual without tail worsening.",
        current_regime=regime,
        paired_delta_pct=delta,
        tail_ok=tail_ok,
    )


def _profit_walk_forward_gate(stability: Mapping[str, Any]) -> dict[str, Any]:
    folds = list(stability.get("folds") or [])
    if stability.get("fold_count") != 3 or len(folds) != 3 or stability.get("valid_fold_count") != 3:
        return _gate(
            "insufficient",
            "Three valid chronological paired-policy folds are required.",
            fold_count=stability.get("fold_count"),
            valid_fold_count=stability.get("valid_fold_count"),
        )
    conflicts = [index + 1 for index, fold in enumerate(folds) if (fold.get("duplicate_policy_conflict_count") or 0) > 0]
    if conflicts:
        return _gate("fail", "Walk-forward folds contain conflicting duplicate policies.", conflict_folds=conflicts)
    failed = [
        index + 1
        for index, fold in enumerate(folds)
        if (_number(fold.get("avg_paired_delta_pct")) or 0.0) <= 0
        or (fold.get("paired_tail_worsened_count") or 0) > (fold.get("paired_tail_avoided_count") or 0)
    ]
    return _gate(
        "fail" if failed else "pass",
        "Every paired-policy walk-forward fold must preserve positive net direction without tail worsening.",
        failed_folds=failed,
    )


def _profit_threshold_robustness_gate(alternate_reports: list[Mapping[str, Any]]) -> dict[str, Any]:
    if not alternate_reports:
        return _gate("insufficient", "The alternate declared 2%/3% threshold report is missing.")
    for report in alternate_reports:
        candidate = ((report.get("candidates") or {}).get(PROFIT_CANDIDATE_ID) or {})
        for window_id in ("recent_60", "recent_120", "holdout"):
            gate = _profit_window_gate(candidate, window_id)
            if gate["status"] != "pass":
                return _gate("insufficient" if gate["status"] == "insufficient" else "fail", "The alternate declared giveback threshold is not robust.", alternate_window=window_id, alternate_gate=gate)
    return _gate("pass", "Both declared giveback thresholds preserve direction.")


def _profit_long_history_gate(item: Mapping[str, Any]) -> dict[str, Any]:
    if item.get("status") != "ok" or item.get("vetoed") is None or item.get("metrics_complete") is not True:
        return _gate("insufficient", "Strategy-linked long-history profit paths were not supplied.", source_status=item.get("status"))
    return _gate("fail" if item.get("vetoed") else "pass", "Long-history catastrophic-risk veto.", reasons=item.get("reasons") or [])


def _profit_fill_gate(windows: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    fill_rates = {}
    for window_id in ("recent_60", "recent_120", "holdout"):
        item = windows.get(window_id) or {}
        if item.get("window_status") != "ok":
            return _gate("insufficient", f"{window_id} lacks the required trading-day window for fill validation.")
        trigger_count = item.get("trigger_count") or 0
        if trigger_count < 5:
            return _gate("insufficient", f"{window_id} has fewer than five triggered exits for fill validation.", trigger_count=trigger_count)
        rate = _number(item.get("next_bar_fill_rate"))
        if rate is None:
            return _gate("insufficient", f"{window_id} has no next-bar fill rate.")
        fill_rates[window_id] = rate
    return _gate(
        "pass" if min(fill_rates.values()) >= 0.95 else "fail",
        "Next-bar simulated fill rate must be at least 95% in every required window.",
        fill_rates=fill_rates,
    )


def _profit_friction_gate(report: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    cost = _number((report.get("parameters") or {}).get("round_trip_cost_pct"))
    paired = (candidate.get("paired_vs_fixed_by_window") or {}).get("all_history") or {}
    paired_cost = _number(paired.get("round_trip_cost_pct"))
    if cost is None or cost <= 0 or paired_cost != cost:
        return _gate("insufficient", "A positive, consistently applied fee/slippage cost is required.", report_cost=cost, paired_cost=paired_cost)
    return _gate("pass", "Paired policy outcomes include the declared round-trip friction.", round_trip_cost_pct=cost)


def _stop_window_gate(item: Mapping[str, Any]) -> dict[str, Any]:
    if item.get("data_status") == "data_unavailable":
        return _gate(
            "insufficient",
            "Causal board minute data at the stop trigger is unavailable.",
            data_reason=item.get("data_reason"),
        )
    if item.get("window_status") != "ok":
        return _gate("insufficient", "The stop window does not contain the required trigger dates.", date_count=item.get("window_date_count"))
    if (item.get("eligible_count") or 0) < 5:
        return _gate("insufficient", "Fewer than five eligible stop-factor records are available.", eligible_count=item.get("eligible_count"))
    deltas = item.get("vs_fixed_baseline") or {}
    valid = []
    for horizon in ("5", "15", "30"):
        summary = (item.get("by_horizon") or {}).get(horizon) or {}
        delta = deltas.get(horizon) or {}
        if summary.get("status") != "ok":
            continue
        tail_delta = _number(delta.get("continuation_tail_rate"))
        mae_delta = _number(delta.get("avg_post_trigger_mae_pct"))
        if tail_delta is not None and mae_delta is not None:
            valid.append((horizon, tail_delta, mae_delta))
    if len(valid) < 2:
        return _gate("insufficient", "Fewer than two horizons have valid stop-path comparisons.", valid_horizons=[item[0] for item in valid])
    passing = [horizon for horizon, tail_delta, mae_delta in valid if tail_delta > 0 and mae_delta < 0]
    return _gate("pass" if len(passing) >= 2 else "fail", "At least two horizons must show more tail continuation and worse MAE than the eligible baseline.", valid=valid, passing_horizons=passing)


def _stop_long_history_gate(evidence: Mapping[str, Any], item: Mapping[str, Any], *, factor_id: str) -> dict[str, Any]:
    if evidence.get("status") != "available" or not evidence.get("eligible_as_long_history_veto"):
        return _gate("insufficient", "Long-history data is auxiliary stress evidence, not strategy-linked entry paths.", evidence_status=evidence.get("status"))
    if factor_id == "board_synchronous_weakness" and not ((evidence.get("board_mapping") or {}).get("historical_constituent_membership")):
        return _gate("insufficient", "Board long history lacks historical constituent membership.")
    if not item:
        return _gate("insufficient", "Long-history stop evidence is unavailable.")
    deltas = item.get("vs_fixed_baseline") or {}
    valid = []
    for horizon in ("5", "15", "30"):
        summary = (item.get("by_horizon") or {}).get(horizon) or {}
        if summary.get("status") != "ok":
            continue
        delta = deltas.get(horizon) or {}
        tail_delta = _number(delta.get("continuation_tail_rate"))
        mae_delta = _number(delta.get("avg_post_trigger_mae_pct"))
        if tail_delta is not None and mae_delta is not None:
            valid.append((horizon, tail_delta, mae_delta))
    if len(valid) < 3:
        return _gate("insufficient", "All three long-history horizons are required.", valid=valid)
    passed = all(tail_delta >= 0 and mae_delta <= 0 for _, tail_delta, mae_delta in valid)
    return _gate("pass" if passed else "fail", "Long history must not reverse tail-risk and MAE direction.", deltas=valid)


def _stop_fill_gate(windows: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    fill_rates = {}
    for window_id in ("recent_60", "recent_120", "holdout"):
        item = windows.get(window_id) or {}
        if item.get("window_status") != "ok":
            return _gate("insufficient", f"{window_id} lacks the required trigger-date window for fill validation.")
        valid = [
            _number(summary.get("next_bar_fill_rate"))
            for summary in (item.get("by_horizon") or {}).values()
            if (summary.get("signal_count") or 0) >= 5
        ]
        valid = [value for value in valid if value is not None]
        if not valid:
            return _gate("insufficient", f"{window_id} has fewer than five stop signals with fill evidence.")
        fill_rates[window_id] = min(valid)
    return _gate(
        "pass" if min(fill_rates.values()) >= 0.95 else "fail",
        "Stop next-bar fill rate must be at least 95% in every required window.",
        fill_rates=fill_rates,
    )


def _concentration_gate(concentration: Mapping[str, Any]) -> dict[str, Any]:
    if not concentration or any(_number(concentration.get(field)) is None for field in CONCENTRATION_LIMITS):
        return _gate("insufficient", "Date/code/board concentration evidence is incomplete.", concentration=dict(concentration))
    failures = {
        field: _number(concentration.get(field))
        for field, limit in CONCENTRATION_LIMITS.items()
        if (_number(concentration.get(field)) or 0.0) > limit
    }
    return _gate("fail" if failures else "pass", "Concentration must remain below predeclared limits.", concentration=dict(concentration), limits=CONCENTRATION_LIMITS, failures=failures)


def _minimum_gate(value: Any, minimum: float, reason: str) -> dict[str, Any]:
    number = _number(value)
    if number is None:
        return _gate("insufficient", reason, value=value, minimum=minimum)
    return _gate("pass" if number >= minimum else "fail", reason, value=number, minimum=minimum)


def _gate(status: str, reason: str, **evidence: Any) -> dict[str, Any]:
    return {"status": status, "reason": reason, "evidence": evidence}


def _load(path: Path) -> dict[str, Any]:
    return load_strict_json(path)


def _report_provenance(
    path: Path,
    report: Mapping[str, Any],
    *,
    expected_report_sha256: str | None = None,
    actual_report_sha256: str | None = None,
    entry_path_manifest_out: dict[tuple[str, str, str], str] | None = None,
    expected_records_path: Path | None = None,
    expected_records_sha256: str | None = None,
) -> dict[str, Any]:
    label_source = report.get("label_source") if isinstance(report.get("label_source"), Mapping) else {}
    provenance_aliases = (
        ("records", report.get("records_path"), report.get("records_sha256")),
        (
            "entry_records",
            report.get("entry_records_path"),
            report.get("entry_records_sha256"),
        ),
        (
            "label_source.entry_records",
            label_source.get("entry_records_path"),
            label_source.get("entry_records_sha256"),
        ),
    )
    complete_aliases = []
    for alias, path_value, sha256_value in provenance_aliases:
        has_path = path_value not in (None, "")
        has_sha256 = sha256_value not in (None, "")
        if has_path != has_sha256:
            raise ValueError(f"incomplete upstream records provenance alias {alias} for {path}")
        if has_path:
            complete_aliases.append((alias, str(path_value), str(sha256_value)))
    if not complete_aliases:
        raise ValueError(f"upstream records provenance is required for {path}")
    _alias, records_path_value, records_sha256 = complete_aliases[0]
    if any(
        not _same_path(records_path_value, alias_path)
        or records_sha256.lower() != alias_sha256.lower()
        for _alias, alias_path, alias_sha256 in complete_aliases[1:]
    ):
        raise ValueError(f"conflicting upstream records provenance aliases for {path}")
    records_path = Path(str(records_path_value))
    if expected_records_path is not None and not _same_path(
        records_path,
        expected_records_path,
    ):
        raise ValueError(f"caller-bound records path mismatch for {path}")
    if expected_records_sha256 is not None and records_sha256.lower() != str(
        expected_records_sha256
    ).lower():
        raise ValueError(f"caller-bound records SHA mismatch for {path}")
    if not records_path.exists():
        raise ValueError(f"upstream records path does not exist for {path}: {records_path}")
    records_report, actual_records_sha256 = load_strict_json_with_sha256(records_path)
    if actual_records_sha256 != records_sha256:
        raise ValueError(f"upstream records SHA mismatch for {path}")
    if not isinstance(records_report, Mapping):
        raise ValueError(f"upstream records report is not a JSON object for {path}")
    validate_paper_records_report(
        records_report,
        context=f"upstream records report for {path}",
        require_durable_entry_bars_source=True,
    )
    if entry_path_manifest_out is not None:
        records = records_report.get("records")
        if not isinstance(records, list):
            raise ValueError(f"upstream records list is required for {path}")
        current_manifest = entry_path_manifest(
            records,
            timeframe=str(report.get("timeframe") or ""),
            context=f"upstream records report for {path}",
        )
        entry_path_manifest_out.clear()
        entry_path_manifest_out.update(current_manifest)
    return {
        "path": str(path),
        "sha256": actual_report_sha256 or hashlib.sha256(path.read_bytes()).hexdigest(),
        "expected_sha256": expected_report_sha256.lower() if expected_report_sha256 else None,
        "schema_version": report.get("schema_version"),
        "as_of": report.get("as_of"),
        "timeframe": report.get("timeframe"),
        "snapshot_label": report.get("snapshot_label"),
        "calendar_source": report.get("calendar_source"),
        "candidate_source": report.get("candidate_source") or {"candidate_root": report.get("candidate_root")},
        "records_path": str(records_path),
        "records_sha256": records_sha256,
    }


def validate_expected_records_provenance(
    provenance: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, str]]:
    if not isinstance(provenance, Mapping) or set(provenance) != set(
        EXPECTED_RECORD_SOURCE_IDS
    ):
        raise ValueError("caller-bound records manifest topology mismatch")
    normalized: dict[str, dict[str, str]] = {}
    for source_id in sorted(EXPECTED_RECORD_SOURCE_IDS):
        identity = provenance.get(source_id)
        if not isinstance(identity, Mapping):
            raise ValueError(f"caller-bound records identity is missing: {source_id}")
        path = str(identity.get("path") or "")
        sha256 = str(identity.get("sha256") or "").lower()
        if not path:
            raise ValueError(f"caller-bound records path is missing: {source_id}")
        if not _is_sha256(sha256):
            raise ValueError(f"caller-bound records SHA is invalid: {source_id}")
        normalized[source_id] = {"path": path, "sha256": sha256}
    for timeframe in ("1m", "5m"):
        if normalized[f"stop:{timeframe}"] != normalized[f"entry:{timeframe}"]:
            raise ValueError(
                f"caller-bound stop {timeframe} records must equal entry records"
            )
    return normalized


def _expected_records_kwargs(
    provenance: Mapping[str, Mapping[str, str]],
    source_id: str,
) -> dict[str, Any]:
    identity = provenance[source_id]
    return {
        "expected_records_path": Path(identity["path"]),
        "expected_records_sha256": identity["sha256"],
    }


def _load_expected_records_manifest(
    path: Path,
    *,
    expected_sha256: str,
) -> dict[str, dict[str, str]]:
    payload, actual_sha256 = load_strict_json_with_sha256(path)
    if actual_sha256.lower() != str(expected_sha256 or "").lower():
        raise ValueError("caller-bound records manifest SHA mismatch")
    if not isinstance(payload, Mapping):
        raise ValueError("caller-bound records manifest must be a JSON object")
    if payload.get("schema_version") != "timing_final_records_manifest.v1":
        raise ValueError("caller-bound records manifest schema mismatch")
    for field in (
        "paper_trading_only",
        "no_execution_signals",
        "does_not_modify_official_scores",
    ):
        if payload.get(field) is not True:
            raise ValueError(f"caller-bound records manifest {field} must be true")
    validate_no_executable_instructions(
        payload,
        context="caller-bound records manifest",
    )
    records = payload.get("records")
    if not isinstance(records, Mapping):
        raise ValueError("caller-bound records manifest records are missing")
    return validate_expected_records_provenance(records)


def _evaluation_tail_summary(reports: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    if not reports:
        raise ValueError("at least one source report is required for evaluation-tail governance")
    sources = {
        source_id: observed_evaluation_tail_summary(report, allow_short_window=True)
        for source_id, report in sorted(reports.items())
    }
    return {
        "status": "observed_evaluation_tail",
        "blind": False,
        "eligible_for_oos_claim": False,
        "sources": sources,
    }


def _number(value: Any) -> float | None:
    try:
        number = float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None
    return number if number is not None and math.isfinite(number) else None


def _round(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def _markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    evaluation_tail = report.get("evaluation_tail") or {}
    lines = [
        "# 非平稳市场买入与退出最终决策",
        "",
        f"截至：`{report.get('as_of')}`",
        "",
        "- 范围：仅 paper trading / shadow research",
        "- 实盘准备：`False`",
        f"- 候选数：`{summary.get('candidate_count')}`",
        f"- 硬门槛状态：`{summary.get('decision_status_counts')}`",
        f"- evaluation tail: `{evaluation_tail.get('status')}`",
        f"- blind: `{str(evaluation_tail.get('blind')).lower()}`",
        f"- eligible_for_oos_claim: `{str(evaluation_tail.get('eligible_for_oos_claim')).lower()}`",
    ]
    lines.extend(
        [
            "",
            "## 已观察评估尾部来源覆盖",
            "",
            "| 来源 | 日期 | 源文档覆盖 | 完整候选覆盖 | 状态 |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for source_id, source in (evaluation_tail.get("sources") or {}).items():
        date_count = source.get("date_count")
        lines.append(
            f"| `{source_id}` | {date_count} | {source.get('source_document_date_count')}/{date_count} "
            f"({source.get('source_document_date_coverage_rate')}) | "
            f"{source.get('complete_candidate_date_count')}/{date_count} "
            f"({source.get('complete_candidate_date_coverage_rate')}) | "
            f"{source.get('candidate_date_coverage_status')} |"
        )
    lines.extend(
        [
            "",
            "## 决策表",
            "",
            "| 候选 | 类型 | 周期 | 研究轨道 | 硬门槛状态 | 失败门槛 | 证据不足门槛 |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for item in report.get("decisions") or []:
        lines.append(
            f"| `{item.get('candidate_id')}` | {item.get('candidate_type')} | {item.get('timeframe')} | "
            f"{item.get('research_track_status')} | {item.get('decision_status')} | "
            f"{_display_gate_names(item.get('failed_gates') or [])} | "
            f"{_display_gate_names(item.get('insufficient_gates') or [])} |"
        )
    lines.extend(
        [
            "",
            "## 当前 Paper 组合",
            "",
        ]
    )
    for candidate_type, stack in (report.get("recommended_paper_stack") or {}).items():
        lines.append(
            f"- {candidate_type}: champions={stack.get('champions') or []}, "
            f"challengers={stack.get('challengers') or []}, observe={stack.get('observe') or []}, "
            f"insufficient={stack.get('insufficient') or []}, rejected={stack.get('rejected') or []}"
        )
    champions = summary.get("paper_champions") or []
    hard_challengers = summary.get("hard_gate_challengers") or []
    lines.extend(
        [
            "",
            "## 结论",
            "",
            f"通过全部硬门槛的 Champion：`{champions}`；通过全部门槛的 Challenger：`{hard_challengers}`。",
            "所有结果仍为 paper-only，不能进入实盘执行层。",
        ]
    )
    return "\n".join(lines) + "\n"


def _display_gate_names(gates: list[str]) -> str:
    names = ["observed_evaluation_tail" if gate == "holdout" else str(gate) for gate in gates]
    return ", ".join(names) or "-"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build final paper-only entry/exit decisions")
    parser.add_argument("--entry-1m-report", required=True)
    parser.add_argument("--entry-5m-report", required=True)
    parser.add_argument("--profit-1m-2-report", required=True)
    parser.add_argument("--profit-1m-3-report", required=True)
    parser.add_argument("--profit-5m-2-report", required=True)
    parser.add_argument("--profit-5m-3-report", required=True)
    parser.add_argument("--stop-1m-report", required=True)
    parser.add_argument("--stop-5m-report", required=True)
    parser.add_argument("--candidate-1m-root", required=True)
    parser.add_argument("--candidate-5m-root", required=True)
    parser.add_argument("--candidate-source-root", required=True)
    parser.add_argument("--selection-validation-root", required=True)
    parser.add_argument("--expected-entry-1m-sha256", required=True)
    parser.add_argument("--expected-entry-5m-sha256", required=True)
    parser.add_argument("--expected-profit-1m-2-sha256", required=True)
    parser.add_argument("--expected-profit-1m-3-sha256", required=True)
    parser.add_argument("--expected-profit-5m-2-sha256", required=True)
    parser.add_argument("--expected-profit-5m-3-sha256", required=True)
    parser.add_argument("--expected-stop-1m-sha256", required=True)
    parser.add_argument("--expected-stop-5m-sha256", required=True)
    parser.add_argument("--expected-calendar-path", required=True)
    parser.add_argument("--expected-calendar-sha256", required=True)
    parser.add_argument("--expected-records-manifest", required=True)
    parser.add_argument("--expected-records-manifest-sha256", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args(argv)
    expected_records_provenance = _load_expected_records_manifest(
        Path(args.expected_records_manifest),
        expected_sha256=args.expected_records_manifest_sha256,
    )
    result = audit_nonstationary_entry_exit_decision(
        entry_reports={"1m": Path(args.entry_1m_report), "5m": Path(args.entry_5m_report)},
        profit_reports={
            "1m": {2.0: Path(args.profit_1m_2_report), 3.0: Path(args.profit_1m_3_report)},
            "5m": {2.0: Path(args.profit_5m_2_report), 3.0: Path(args.profit_5m_3_report)},
        },
        stop_reports={"1m": Path(args.stop_1m_report), "5m": Path(args.stop_5m_report)},
        expected_entry_report_sha256={
            "1m": args.expected_entry_1m_sha256,
            "5m": args.expected_entry_5m_sha256,
        },
        expected_profit_report_sha256={
            "1m": {2.0: args.expected_profit_1m_2_sha256, 3.0: args.expected_profit_1m_3_sha256},
            "5m": {2.0: args.expected_profit_5m_2_sha256, 3.0: args.expected_profit_5m_3_sha256},
        },
        expected_stop_report_sha256={
            "1m": args.expected_stop_1m_sha256,
            "5m": args.expected_stop_5m_sha256,
        },
        candidate_roots={"1m": Path(args.candidate_1m_root), "5m": Path(args.candidate_5m_root)},
        candidate_source_root=Path(args.candidate_source_root),
        selection_validation_root=Path(args.selection_validation_root),
        expected_calendar_path=Path(args.expected_calendar_path),
        expected_calendar_sha256=args.expected_calendar_sha256,
        expected_records_provenance=expected_records_provenance,
        output_dir=Path(args.output_dir),
        as_of=args.as_of,
    )
    print(result["json_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
