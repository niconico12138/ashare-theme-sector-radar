"""Validate causal paper-record paths before research audits consume them."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from theme_sector_radar.data.local_minute_archive import (
    aggregate_complete_1m_session_to_5m,
    bar_timestamp,
    validate_bar_security_identity,
    validate_complete_a_share_session,
)
from theme_sector_radar.data.trading_calendar import next_trading_date
from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import load_strict_json_with_sha256


def entry_bars_sha256(bars: Sequence[Mapping[str, Any]]) -> str:
    payload = json.dumps(list(bars), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def entry_path_manifest(
    records: Sequence[Mapping[str, Any]],
    *,
    timeframe: str,
    context: str,
) -> dict[tuple[str, str, str], str]:
    hash_field = {
        "1m": "entry_bars_sha256",
        "5m": "source_1m_bars_sha256",
    }.get(timeframe)
    if hash_field is None:
        raise ValueError(f"unsupported paper-record timeframe: {timeframe}")
    manifest: dict[tuple[str, str, str], str] = {}
    for raw in records:
        if not isinstance(raw, Mapping):
            raise ValueError(f"{context} record must be a JSON object")
        if raw.get("causal_entry_valid") is not True:
            continue
        key = (
            str(raw.get("signal_date") or raw.get("as_of") or ""),
            str(raw.get("entry_date") or ""),
            str(raw.get("code") or "").strip(),
        )
        if not all(key):
            raise ValueError(f"{context} entry path identity is incomplete")
        path_sha256 = str(raw.get(hash_field) or "").lower()
        if len(path_sha256) != 64 or any(char not in "0123456789abcdef" for char in path_sha256):
            raise ValueError(f"{context} entry path SHA is missing or invalid")
        existing = manifest.get(key)
        if existing is not None and existing != path_sha256:
            raise ValueError(
                f"{context} entry path mismatch for {'|'.join(key)}"
            )
        manifest[key] = path_sha256
    return manifest


def merge_entry_path_manifests(
    manifests: Sequence[Mapping[tuple[str, str, str], str]],
    *,
    context: str,
) -> dict[tuple[str, str, str], str]:
    merged: dict[tuple[str, str, str], str] = {}
    for manifest in manifests:
        for key, path_sha256 in manifest.items():
            existing = merged.get(key)
            if existing is not None and existing != path_sha256:
                raise ValueError(
                    f"{context} entry path mismatch for {'|'.join(key)}"
                )
            merged[key] = path_sha256
    return merged


def validate_paper_record_cohort(
    records: Sequence[Mapping[str, Any]],
    *,
    samples: Sequence[Mapping[str, Any]],
    version_ids: Sequence[str],
    snapshot_label: str,
    calendar_dates: Sequence[str],
    start: str | None,
    end: str | None,
    concentration_threshold: int,
    factor_exit_peak_giveback_pct: float,
    timeframe: str,
    context: str,
) -> dict[str, Any]:
    from theme_sector_radar.timing.paper_trading import build_timing_paper_trading_records

    bar_source = {
        "1m": "complete_1m_session",
        "5m": "aggregated_from_complete_1m_session",
    }.get(timeframe)
    if bar_source is None:
        raise ValueError(f"unsupported paper-record timeframe: {timeframe}")
    calendar_set = {str(value) for value in calendar_dates}
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for sample in samples:
        if not isinstance(sample, Mapping) or sample.get("_sample_mode") or sample.get("sample_mode"):
            continue
        signal_date = str(sample.get("_sample_date") or sample.get("as_of") or "")
        if (
            not signal_date
            or signal_date not in calendar_set
            or (start is not None and signal_date < start)
            or (end is not None and signal_date > end)
        ):
            continue
        grouped.setdefault(signal_date, []).append(sample)
    expected: dict[tuple[str, str, str], dict[str, Any]] = {}
    for signal_date, rows in sorted(grouped.items()):
        candidates_by_code = {
            str(row.get("code") or "").strip(): row
            for row in rows
            if str(row.get("code") or "").strip()
        }
        probe = build_timing_paper_trading_records(
            rows,
            as_of=signal_date,
            snapshot_label=snapshot_label,
            version_ids=version_ids,
            concentration_threshold=concentration_threshold,
            factor_exit_peak_giveback_pct=factor_exit_peak_giveback_pct,
            bar_interval=timeframe,
            bar_source=bar_source,
        )
        for row in probe["records"]:
            key = _paper_record_key(row)
            if key in expected:
                raise ValueError(f"{context} candidate source produces a duplicate cohort identity")
            candidate = candidates_by_code.get(key[1]) or {}
            selection_return = _finite_number(candidate.get("forward_return_pct"))
            expected[key] = {
                "source_fields": _cohort_source_fields(row),
                "selection_forward_return_pct": (
                    round(selection_return, 4) if selection_return is not None else None
                ),
            }
    actual: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    for row in records:
        if not isinstance(row, Mapping):
            raise ValueError(f"{context} record must be a JSON object")
        key = _paper_record_key(row)
        if key in actual:
            raise ValueError(f"{context} contains a duplicate cohort identity")
        actual[key] = row
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    if missing:
        raise ValueError(f"{context} cohort has missing candidate selections: {len(missing)}")
    if extra:
        raise ValueError(f"{context} cohort has extra candidate selections: {len(extra)}")
    for key in sorted(expected):
        row = actual[key]
        if _cohort_source_fields(row) != expected[key]["source_fields"]:
            raise ValueError(f"{context} cohort source fields differ from candidate source")
        if (
            row.get("causal_entry_valid") is True
            and row.get("selection_forward_return_pct")
            != expected[key]["selection_forward_return_pct"]
        ):
            raise ValueError(f"{context} valid record selection label differs from candidate source")
    manifest = [
        {
            "signal_date": key[0],
            "code": key[1],
            "version_id": key[2],
            "source_fields": expected[key]["source_fields"],
            "selection_forward_return_pct": expected[key]["selection_forward_return_pct"],
        }
        for key in sorted(expected)
    ]
    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return {
        "status": "validated",
        "expected_record_count": len(expected),
        "actual_record_count": len(actual),
        "record_key_manifest_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    }


def validate_causal_paper_records(
    records: Sequence[Mapping[str, Any]],
    *,
    timeframe: str,
    as_of: str,
    calendar_dates: Sequence[str],
    factor_exit_peak_giveback_pct: float,
    context: str,
) -> dict[str, int]:
    interval_minutes = {"1m": 1, "5m": 5}.get(timeframe)
    expected_count = {"1m": 241, "5m": 48}.get(timeframe)
    expected_source = {
        "1m": "complete_1m_session",
        "5m": "aggregated_from_complete_1m_session",
    }.get(timeframe)
    if interval_minutes is None or expected_count is None or expected_source is None:
        raise ValueError(f"unsupported paper-record timeframe: {timeframe}")
    expected_peak_giveback_pct = _finite_number(factor_exit_peak_giveback_pct)
    if expected_peak_giveback_pct is None or expected_peak_giveback_pct <= 0:
        raise ValueError(f"{context} factor-exit parameter identity is missing")
    calendar = sorted({str(value) for value in calendar_dates if str(value) <= as_of})
    calendar_set = set(calendar)
    seen: set[tuple[str, str, str]] = set()
    valid_count = 0
    invalid_count = 0
    for raw in records:
        if not isinstance(raw, Mapping):
            raise ValueError(f"{context} record must be a JSON object")
        row = dict(raw)
        _validate_paper_record_no_executable(row, context=context)
        signal_date = str(row.get("signal_date") or row.get("as_of") or "")
        entry_date = str(row.get("entry_date") or "")
        code = str(row.get("code") or "").strip()
        name = str(row.get("name") or "").strip()
        version_id = str(row.get("timing_version_id") or "").strip()
        if not signal_date or signal_date not in calendar_set or signal_date > as_of:
            raise ValueError(f"{context} signal date is not in the validated trading calendar")
        if not code or not name or not version_id:
            raise ValueError(f"{context} security or strategy identity is missing")
        key = (signal_date, code, version_id)
        if key in seen:
            raise ValueError(f"{context} contains a duplicate strategy entry identity: {'|'.join(key)}")
        seen.add(key)
        if row.get("paper_trading_only") is not True or row.get("no_execution_signals") is not True:
            raise ValueError(f"{context} record must be paper-only")
        assumptions = row.get("execution_assumptions") or {}
        if (
            assumptions.get("signal_available") != "after_signal_session_close"
            or assumptions.get("entry_model") != "next_trading_session_first_bar_open"
            or assumptions.get("bar_interval") != timeframe
            or assumptions.get("bar_source") != expected_source
        ):
            raise ValueError(f"{context} execution identity mismatch")
        expected_entry_date = next_trading_date(calendar, signal_date, as_of=as_of)
        if entry_date != str(expected_entry_date or ""):
            raise ValueError(f"{context} entry date is not the next trading date")
        raw_bars = row.get("entry_bars", [])
        if not isinstance(raw_bars, list) or any(
            not isinstance(bar, Mapping) for bar in raw_bars
        ):
            raise ValueError(f"{context} entry bars must contain only objects")
        bars = [dict(bar) for bar in raw_bars]
        if row.get("causal_entry_valid") is True:
            _validate_complete_record(
                row,
                bars=bars,
                entry_date=entry_date,
                code=code,
                name=name,
                interval_minutes=interval_minutes,
                expected_count=expected_count,
                context=context,
            )
            valid_count += 1
        else:
            _validate_unlabeled_record(row, bars=bars, context=context)
            invalid_count += 1
        _validate_derived_path_fields(
            row,
            bars=bars,
            timeframe=timeframe,
            expected_peak_giveback_pct=expected_peak_giveback_pct,
            context=context,
        )
    entry_path_manifest(records, timeframe=timeframe, context=context)
    return {
        "record_count": len(records),
        "valid_record_count": valid_count,
        "invalid_record_count": invalid_count,
    }


def validate_paper_records_report(
    report: Mapping[str, Any],
    *,
    context: str,
    require_durable_entry_bars_source: bool = False,
) -> None:
    """Reject executable fields anywhere in a records artifact."""
    _validate_required_paper_guards(report, context=context)
    entry_bars_source = validate_entry_bars_source_artifact(
        report.get("entry_bars_source_identity"),
        context=context,
        require_durable=require_durable_entry_bars_source,
    )
    guarded = dict(report)
    records = guarded.pop("records", None)
    validate_no_executable_instructions(guarded, context=context)
    if not isinstance(records, list):
        raise ValueError(f"{context} must contain a records list")
    for row in records:
        if not isinstance(row, Mapping):
            raise ValueError(f"{context} record must be a JSON object")
        _validate_required_paper_guards(row, context=f"{context} record")
        _validate_paper_record_no_executable(row, context=context)
    _validate_records_against_entry_bars_manifest(
        records,
        entry_bars_source=entry_bars_source,
        context=context,
    )


def validate_entry_bars_source_artifact(
    identity: Any,
    *,
    context: str,
    require_durable: bool = False,
) -> dict[str, Any]:
    if not isinstance(identity, Mapping):
        raise ValueError(f"{context} entry-bars source identity is required")
    normalized = dict(identity)
    if normalized.get("status") != "validated":
        raise ValueError(f"{context} entry-bars source identity must be validated")
    source_kind = normalized.get("source_kind")
    sha256 = str(normalized.get("sha256") or "").lower()
    if len(sha256) != 64 or any(char not in "0123456789abcdef" for char in sha256):
        raise ValueError(f"{context} entry-bars source SHA is invalid")
    if source_kind == "in_memory_test_fixture":
        if require_durable:
            raise ValueError(
                f"{context} requires a durable strict JSON manifest"
            )
        return normalized
    if source_kind != "strict_json_manifest":
        raise ValueError(f"{context} entry-bars source kind is unsupported")
    path = Path(str(normalized.get("path") or ""))
    payload, actual_sha256 = load_strict_json_with_sha256(path)
    if actual_sha256.lower() != sha256:
        raise ValueError(f"{context} entry-bars manifest SHA mismatch")
    if not isinstance(payload, Mapping):
        raise ValueError(f"{context} entry-bars manifest must be a JSON object")
    if payload.get("schema_version") != "timing_entry_bars_source_manifest.v1":
        raise ValueError(f"{context} entry-bars manifest schema mismatch")
    _validate_required_paper_guards(payload, context=f"{context} entry-bars manifest")
    validate_no_executable_instructions(
        payload,
        context=f"{context} entry-bars manifest",
    )
    sessions = payload.get("sessions")
    if not isinstance(sessions, list):
        raise ValueError(f"{context} entry-bars manifest sessions must be a list")
    if normalized.get("schema_version") != payload.get("schema_version"):
        raise ValueError(f"{context} entry-bars manifest declared schema mismatch")
    if normalized.get("as_of") != payload.get("as_of"):
        raise ValueError(f"{context} entry-bars manifest as-of mismatch")
    if normalized.get("session_count") != len(sessions):
        raise ValueError(f"{context} entry-bars manifest session count mismatch")
    session_index: dict[tuple[str, str], dict[str, Any]] = {}
    complete_session_count = 0
    for raw_session in sessions:
        if not isinstance(raw_session, Mapping):
            raise ValueError(f"{context} entry-bars manifest session must be an object")
        code = str(raw_session.get("code") or "").strip()
        entry_date = str(raw_session.get("entry_date") or "")
        if not code or len(entry_date) != 10:
            raise ValueError(f"{context} entry-bars manifest session identity is incomplete")
        try:
            canonical_entry_date = date.fromisoformat(entry_date).isoformat()
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{context} entry-bars manifest session date is invalid"
            ) from exc
        if canonical_entry_date != entry_date:
            raise ValueError(f"{context} entry-bars manifest session date is invalid")
        key = (code, entry_date)
        if key in session_index:
            raise ValueError(
                f"{context} duplicate entry-bars manifest session: {code}|{entry_date}"
            )
        bars = raw_session.get("bars")
        if not isinstance(bars, list) or any(
            not isinstance(row, Mapping) for row in bars
        ):
            raise ValueError(f"{context} entry-bars manifest session bars are invalid")
        if bars:
            first_timestamp = bar_timestamp(bars[0])
            if not first_timestamp or first_timestamp[:8] != entry_date.replace("-", ""):
                raise ValueError(
                    f"{context} entry-bars manifest session date does not match bars"
                )
            validate_bar_security_identity(
                bars,
                code=code,
                name=str(bars[0].get("name") or ""),
                context=f"{context} entry-bars manifest session",
            )
        complete_session = validate_complete_a_share_session(
            bars,
            interval_minutes=1,
        )
        if complete_session:
            complete_session_count += 1
        session_index[key] = {
            "bars": bars,
            "bars_sha256": entry_bars_sha256(bars),
            "complete_session": complete_session,
        }
    if normalized.get("complete_session_count") not in (None, complete_session_count):
        raise ValueError(f"{context} entry-bars manifest complete-session count mismatch")
    invalid_session_count = len(sessions) - complete_session_count
    if normalized.get("invalid_session_count") not in (None, invalid_session_count):
        raise ValueError(f"{context} entry-bars manifest invalid-session count mismatch")
    normalized["_manifest_sessions"] = session_index
    normalized["_complete_session_count"] = complete_session_count
    normalized["_invalid_session_count"] = invalid_session_count
    return normalized


def _validate_records_against_entry_bars_manifest(
    records: Sequence[Mapping[str, Any]],
    *,
    entry_bars_source: Mapping[str, Any],
    context: str,
) -> None:
    sessions = entry_bars_source.get("_manifest_sessions")
    if not isinstance(sessions, Mapping):
        return
    for row in records:
        if not isinstance(row, Mapping) or row.get("causal_entry_valid") is not True:
            continue
        code = str(row.get("code") or "").strip()
        entry_date = str(row.get("entry_date") or "")
        session = sessions.get((code, entry_date))
        if not isinstance(session, Mapping):
            raise ValueError(
                f"{context} entry-bars manifest session is missing for {code}|{entry_date}"
            )
        if session.get("complete_session") is not True:
            raise ValueError(
                f"{context} entry-bars manifest session is incomplete for {code}|{entry_date}"
            )
        uses_source_1m = "source_1m_bars" in row
        bars_field = "source_1m_bars" if uses_source_1m else "entry_bars"
        hash_field = (
            "source_1m_bars_sha256" if uses_source_1m else "entry_bars_sha256"
        )
        record_bars = row.get(bars_field)
        if not isinstance(record_bars, list) or any(
            not isinstance(bar, Mapping) for bar in record_bars
        ):
            raise ValueError(f"{context} record {bars_field} is invalid")
        record_sha256 = entry_bars_sha256(record_bars)
        expected_sha256 = str(session.get("bars_sha256") or "")
        if (
            record_sha256 != expected_sha256
            or str(row.get(hash_field) or "").lower() != expected_sha256
        ):
            raise ValueError(
                f"{context} entry-bars manifest path mismatch for {code}|{entry_date}"
            )


def _validate_required_paper_guards(
    payload: Mapping[str, Any],
    *,
    context: str,
) -> None:
    for field in (
        "paper_trading_only",
        "no_execution_signals",
        "does_not_modify_official_scores",
    ):
        if payload.get(field) is not True:
            raise ValueError(f"{context} paper-only guard {field} must be true")


def _validate_paper_record_no_executable(
    row: Mapping[str, Any],
    *,
    context: str,
) -> None:
    guarded = dict(row)
    factor_exit_triggers = guarded.get("factor_exit_triggers")
    if isinstance(factor_exit_triggers, Mapping):
        guarded_triggers = dict(factor_exit_triggers)
        if "entry_price" in guarded_triggers:
            entry_price = guarded_triggers.pop("entry_price")
            legacy_unlabeled_zero = (
                isinstance(entry_price, (int, float))
                and not isinstance(entry_price, bool)
                and float(entry_price) == 0.0
                and row.get("causal_entry_valid") is False
                and not (row.get("entry_bars") or [])
            )
            if not legacy_unlabeled_zero:
                if isinstance(entry_price, bool) or not isinstance(
                    entry_price,
                    (int, float),
                ):
                    raise ValueError(
                        f"{context} observational entry_price must be finite and positive"
                    )
                value = _finite_number(entry_price)
                if value is None or value <= 0:
                    raise ValueError(
                        f"{context} observational entry_price must be finite and positive"
                    )
        guarded["factor_exit_triggers"] = guarded_triggers
    validate_no_executable_instructions(guarded, context=context)


def _paper_record_key(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("signal_date") or row.get("as_of") or ""),
        str(row.get("code") or "").strip(),
        str(row.get("timing_version_id") or "").strip(),
    )


def _cohort_source_fields(row: Mapping[str, Any]) -> dict[str, Any]:
    path_fields = {
        "entry_date",
        "causal_entry_valid",
        "causal_entry_invalid_reasons",
        "entry_bars",
        "entry_bars_sha256",
        "source_1m_bars",
        "source_1m_bars_sha256",
        "forward_return_pct",
        "selection_forward_return_pct",
        "path_stats",
        "exit_research",
        "factor_exit_triggers",
        "paper_exit_candidates",
        "exit_data_quality",
    }
    return {key: value for key, value in row.items() if key not in path_fields}


def _validate_complete_record(
    row: Mapping[str, Any],
    *,
    bars: list[Mapping[str, Any]],
    entry_date: str,
    code: str,
    name: str,
    interval_minutes: int,
    expected_count: int,
    context: str,
) -> None:
    if len(bars) != expected_count or not validate_complete_a_share_session(bars, interval_minutes=interval_minutes):
        raise ValueError(f"{context} causal entry path is not a complete session")
    if any(_bar_date(bar) != entry_date for bar in bars):
        raise ValueError(f"{context} causal entry bar date mismatch")
    if any(str(bar.get("code") or "").strip() != code for bar in bars):
        raise ValueError(f"{context} causal entry security code mismatch")
    if name and any(str(bar.get("name") or "").strip() != name for bar in bars):
        raise ValueError(f"{context} causal entry security name mismatch")
    actual_hash = str(row.get("entry_bars_sha256") or "")
    if actual_hash != entry_bars_sha256(bars):
        raise ValueError(f"{context} causal entry bars SHA mismatch")
    if interval_minutes == 5:
        _validate_bound_source_1m_session(
            row,
            bars=bars,
            entry_date=entry_date,
            code=code,
            name=name,
            context=context,
        )
    elif "source_1m_bars" in row or "source_1m_bars_sha256" in row:
        raise ValueError(f"{context} 1m record retained unexpected source 1m identity")
    first_open = _finite_number(bars[0].get("open"))
    final_close = _finite_number(bars[-1].get("close"))
    if first_open is None or first_open <= 0 or final_close is None:
        raise ValueError(f"{context} causal entry price identity is invalid")
    expected_return = round((final_close - first_open) / first_open * 100.0, 4)
    path_stats = row.get("path_stats") or {}
    quality = row.get("exit_data_quality") or {}
    if (
        _finite_number(path_stats.get("entry_reference_price")) != first_open
        or _finite_number(path_stats.get("close_return_pct")) != expected_return
        or int(path_stats.get("bar_count") or 0) != expected_count
        or _finite_number(row.get("forward_return_pct")) != expected_return
        or int(quality.get("bar_count") or 0) != expected_count
        or quality.get("complete_a_share_session") is not True
        or list(row.get("causal_entry_invalid_reasons") or [])
    ):
        raise ValueError(f"{context} causal entry path statistics mismatch")


def _validate_unlabeled_record(
    row: Mapping[str, Any],
    *,
    bars: list[Mapping[str, Any]],
    context: str,
) -> None:
    path_stats = row.get("path_stats") or {}
    quality = row.get("exit_data_quality") or {}
    if (
        bars
        or row.get("entry_bars_sha256") is not None
        or row.get("forward_return_pct") is not None
        or "source_1m_bars" in row
        or "source_1m_bars_sha256" in row
        or "selection_forward_return_pct" in row
        or int(path_stats.get("bar_count") or 0) != 0
        or path_stats.get("entry_reference_price") is not None
        or path_stats.get("close_return_pct") is not None
        or int(quality.get("bar_count") or 0) != 0
        or quality.get("complete_a_share_session") is not False
        or not list(row.get("causal_entry_invalid_reasons") or [])
    ):
        if "selection_forward_return_pct" in row:
            raise ValueError(f"{context} unlabeled record retained a selection label")
        raise ValueError(f"{context} unlabeled record retained causal path data")


def _validate_bound_source_1m_session(
    row: Mapping[str, Any],
    *,
    bars: list[Mapping[str, Any]],
    entry_date: str,
    code: str,
    name: str,
    context: str,
) -> None:
    raw_source = row.get("source_1m_bars")
    if not isinstance(raw_source, list) or not raw_source or not all(isinstance(item, Mapping) for item in raw_source):
        raise ValueError(f"{context} source 1m session is missing")
    source_bars = [dict(item) for item in raw_source]
    if len(source_bars) != 241 or not validate_complete_a_share_session(source_bars, interval_minutes=1):
        raise ValueError(f"{context} source 1m session is incomplete")
    if any(_bar_date(bar) != entry_date for bar in source_bars):
        raise ValueError(f"{context} source 1m date mismatch")
    if any(str(bar.get("code") or "").strip() != code for bar in source_bars):
        raise ValueError(f"{context} source 1m security code mismatch")
    if any(str(bar.get("name") or "").strip() != name for bar in source_bars):
        raise ValueError(f"{context} source 1m security name mismatch")
    if str(row.get("source_1m_bars_sha256") or "") != entry_bars_sha256(source_bars):
        raise ValueError(f"{context} source 1m bars SHA mismatch")
    if aggregate_complete_1m_session_to_5m(source_bars) != bars:
        raise ValueError(f"{context} source 1m aggregation mismatch")


def _validate_derived_path_fields(
    row: Mapping[str, Any],
    *,
    bars: list[Mapping[str, Any]],
    timeframe: str,
    expected_peak_giveback_pct: float,
    context: str,
) -> None:
    assumptions = row.get("execution_assumptions") or {}
    peak_giveback_pct = _finite_number(assumptions.get("factor_exit_peak_giveback_pct"))
    if peak_giveback_pct is None or not math.isclose(
        peak_giveback_pct,
        expected_peak_giveback_pct,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError(f"{context} factor-exit parameter identity is missing")
    from theme_sector_radar.timing.paper_trading import derive_paper_record_path_fields

    expected = derive_paper_record_path_fields(
        bars,
        factor_exit_peak_giveback_pct=expected_peak_giveback_pct,
        bar_interval=timeframe,
    )
    mismatched = [field for field, value in expected.items() if row.get(field) != value]
    if mismatched:
        raise ValueError(
            f"{context} derived path fields mismatch: {', '.join(mismatched)}"
        )


def _bar_date(row: Mapping[str, Any]) -> str:
    digits = "".join(character for character in str(bar_timestamp(row) or "") if character.isdigit())
    if len(digits) < 8:
        return ""
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"


def _finite_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None
