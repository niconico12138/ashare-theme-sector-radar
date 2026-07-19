#!/usr/bin/env python3
"""Generate paper-only timing observation records from historical candidates."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audit_timing_strategy_overfit import _load_samples  # noqa: E402
from theme_sector_radar.data.local_minute_archive import (  # noqa: E402
    aggregate_complete_1m_session_to_5m,
    validate_complete_a_share_session,
)
from theme_sector_radar.data.trading_calendar import load_trading_calendar, next_trading_date  # noqa: E402
from theme_sector_radar.reporting.artifact_archive import write_text_preserving_previous  # noqa: E402
from theme_sector_radar.reporting.paper_only_contract import validate_no_executable_instructions  # noqa: E402
from theme_sector_radar.reporting.strict_json import load_strict_json_with_sha256  # noqa: E402
from theme_sector_radar.timing.candidate_source_identity import validate_candidate_root_identity  # noqa: E402
from theme_sector_radar.timing.paper_trading import (  # noqa: E402
    DEFAULT_PAPER_TIMING_VERSION_IDS,
    build_timing_paper_trading_records,
)
from theme_sector_radar.timing.paper_record_identity import (  # noqa: E402
    validate_paper_record_cohort,
    validate_paper_records_report,
)
from theme_sector_radar.timing.selection_source_identity import (  # noqa: E402
    validate_selection_source_identity,
)


def run_timing_paper_trading_records(
    *,
    candidate_root: Path,
    candidate_source_root: Path,
    output_dir: Path,
    as_of: str,
    snapshot_label: str,
    start: str | None = None,
    end: str | None = None,
    selection_validation_root: Path | None = PROJECT_ROOT / "reports" / "selection_validation",
    version_ids: list[str] | None = None,
    concentration_threshold: int = 2,
    factor_exit_peak_giveback_pct: float = 2.0,
    bar_interval: str,
    trading_calendar_path: Path | None = None,
    trading_calendar_dates: Sequence[str] | None = None,
    client: Any | None = None,
    entry_bars_source_identity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    calendar = _resolve_calendar(
        path=trading_calendar_path,
        dates=trading_calendar_dates,
        as_of=as_of,
    )
    calendar_dates = calendar["dates"]
    calendar_set = set(calendar_dates)
    bar_source = "complete_1m_session" if bar_interval == "1m" else "aggregated_from_complete_1m_session"
    effective_end = min(value for value in (end, as_of) if value)
    effective_version_ids = list(version_ids or DEFAULT_PAPER_TIMING_VERSION_IDS)
    candidate_document_snapshots: dict[Path, Mapping[str, Any]] = {}
    source_identity = validate_candidate_root_identity(
        candidate_root,
        source_root=candidate_source_root,
        timeframe=bar_interval,
        start=start,
        end=effective_end,
        document_snapshots=candidate_document_snapshots,
    )
    if (
        source_identity.get("status") != "validated"
        or source_identity.get("bar_interval") != bar_interval
        or source_identity.get("bar_source") != bar_source
        or len(str(source_identity.get("manifest_sha256") or "")) != 64
    ):
        raise ValueError("candidate source identity does not match the requested paper-record timeframe")
    if selection_validation_root is None:
        raise ValueError("selection validation root is required for content-bound paper records")
    selection_document_snapshots: dict[str, Mapping[str, Any]] = {}
    selection_source_identity = validate_selection_source_identity(
        selection_validation_root,
        start=start,
        end=effective_end,
        document_snapshots=selection_document_snapshots,
    )
    samples = _load_samples(
        candidate_root,
        start,
        effective_end,
        selection_validation_root,
        candidate_document_snapshots,
        selection_document_snapshots,
    )
    samples = [
        row
        for row in samples
        if not row.get("_sample_mode")
        and str(row.get("_sample_date") or "") in calendar_set
    ]
    entry_bars_source = _validate_entry_bars_source_identity(
        entry_bars_source_identity
    )
    if client is None:
        raise ValueError(
            "caller-bound entry-bar source client is required; implicit HTTP is disabled"
        )
    records = []
    fetch_errors = {}
    for date, rows in _group_by_date(samples).items():
        entry_date = next_trading_date(calendar_dates, date, as_of=as_of)
        probe = build_timing_paper_trading_records(
            rows,
            as_of=date,
            snapshot_label=snapshot_label,
            version_ids=effective_version_ids,
            concentration_threshold=concentration_threshold,
            factor_exit_peak_giveback_pct=factor_exit_peak_giveback_pct,
            bar_interval=bar_interval,
            bar_source=bar_source,
        )
        names_by_code: dict[str, str] = {}
        for record in probe["records"]:
            code = str(record.get("code") or "")
            name = str(record.get("name") or "")
            if code and code in names_by_code and names_by_code[code] != name:
                raise ValueError(f"conflicting candidate security names for {code}")
            if code:
                names_by_code[code] = name
        bars_by_code = {}
        source_1m_bars_by_code = {}
        entry_date_by_code = {}
        for code in sorted({str(record.get("code") or "") for record in probe["records"] if record.get("code")}):
            if entry_date:
                entry_date_by_code[code] = entry_date
            else:
                continue
            try:
                source_1m_bars = _fetch_entry_session_bars(
                    client,
                    code=code,
                    expected_name=names_by_code.get(code, ""),
                    entry_date=entry_date,
                )
            except ValueError:
                raise
            except Exception as exc:
                fetch_errors[f"{date}|{code}"] = f"{type(exc).__name__}: {exc}"
                continue
            if source_1m_bars:
                source_1m_bars_by_code[code] = source_1m_bars
                bars_by_code[code] = (
                    source_1m_bars
                    if bar_interval == "1m"
                    else aggregate_complete_1m_session_to_5m(source_1m_bars)
                )
        dated_report = build_timing_paper_trading_records(
            rows,
            minute_bars_by_code=bars_by_code,
            source_1m_bars_by_code=source_1m_bars_by_code,
            entry_date_by_code=entry_date_by_code,
            as_of=date,
            snapshot_label=snapshot_label,
            version_ids=effective_version_ids,
            concentration_threshold=concentration_threshold,
            factor_exit_peak_giveback_pct=factor_exit_peak_giveback_pct,
            bar_interval=bar_interval,
            bar_source=bar_source,
        )
        records.extend(dated_report["records"])
    record_cohort_identity = validate_paper_record_cohort(
        records,
        samples=samples,
        version_ids=effective_version_ids,
        snapshot_label=snapshot_label,
        calendar_dates=calendar_dates,
        start=start,
        end=effective_end,
        concentration_threshold=concentration_threshold,
        factor_exit_peak_giveback_pct=factor_exit_peak_giveback_pct,
        timeframe=bar_interval,
        context="paper records",
    )
    report = {
        "schema_version": "timing_paper_trading_records_batch.v1",
        "as_of": as_of,
        "snapshot_label": snapshot_label,
        "bar_interval": bar_interval,
        "bar_source": bar_source,
        "candidate_source_identity": source_identity,
        "selection_source_identity": selection_source_identity,
        "trading_calendar": calendar,
        "entry_bars_source_identity": entry_bars_source,
        "parameters": {
            "candidate_root": str(candidate_root),
            "selection_validation_root": str(selection_validation_root) if selection_validation_root else None,
            "start": start,
            "end": effective_end,
            "requested_end": end,
            "version_ids": effective_version_ids,
            "concentration_threshold": concentration_threshold,
            "factor_exit_peak_giveback_pct": factor_exit_peak_giveback_pct,
            "bar_interval": bar_interval,
            "bar_source": bar_source,
            "candidate_source_identity": source_identity,
            "selection_source_identity": selection_source_identity,
            "trading_calendar_path": str(trading_calendar_path) if trading_calendar_path else None,
            "entry_bars_source_identity": entry_bars_source,
        },
        "summary": {
            "sample_count": len(samples),
            "record_count": len(records),
            "labeled_record_count": sum(1 for record in records if record.get("forward_return_pct") is not None),
            "unlabeled_record_count": sum(1 for record in records if record.get("forward_return_pct") is None),
            "causal_entry_valid_count": sum(1 for record in records if record.get("causal_entry_valid")),
            "minute_fetch_error_count": len(fetch_errors),
            "version_counts": dict(Counter(record["timing_version_id"] for record in records)),
            "risk_tag_counts": dict(Counter(tag for record in records for tag in record.get("paper_risk_tags") or [])),
        },
        "record_cohort_identity": record_cohort_identity,
        "records": records,
        "minute_fetch_errors": fetch_errors,
        "paper_trading_only": True,
        "no_execution_signals": True,
        "does_not_modify_official_scores": True,
    }
    validate_paper_records_report(
        report,
        context="paper records report",
        require_durable_entry_bars_source=True,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"timing_paper_trading_records_{as_of}_{snapshot_label}.json"
    markdown_path = output_dir / f"timing_paper_trading_records_{as_of}_{snapshot_label}.md"
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


def _validate_entry_bars_source_identity(
    identity: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(identity, Mapping):
        raise ValueError("caller-bound entry-bar source identity is required")
    normalized = dict(identity)
    if normalized.get("status") != "validated":
        raise ValueError("caller-bound entry-bar source identity must be validated")
    if normalized.get("source_kind") != "strict_json_manifest":
        raise ValueError(
            "caller-bound entry-bar source requires a durable strict JSON manifest"
        )
    sha256 = str(normalized.get("sha256") or "")
    if len(sha256) != 64 or any(
        character not in "0123456789abcdefABCDEF" for character in sha256
    ):
        raise ValueError("caller-bound entry-bar source SHA must be SHA-256")
    if normalized.get("source_kind") == "strict_json_manifest" and not str(
        normalized.get("path") or ""
    ):
        raise ValueError("caller-bound entry-bar source manifest path is required")
    return normalized


class _EntryBarsManifestClient:
    def __init__(self, sessions: Mapping[tuple[str, str], list[dict[str, Any]]]):
        self._sessions = {
            key: [dict(row) for row in rows]
            for key, rows in sessions.items()
        }

    def get_stock_bars(self, code, start, _end, frequency, fq):
        if frequency != "1m" or fq is not None:
            raise ValueError("entry-bars manifest only supports unadjusted 1m sessions")
        digits = "".join(character for character in str(start) if character.isdigit())
        if len(digits) < 8:
            return []
        day = f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
        return [dict(row) for row in self._sessions.get((str(code).zfill(6), day), [])]


def _load_entry_bars_manifest(
    path: Path,
    *,
    expected_sha256: str,
) -> tuple[_EntryBarsManifestClient, dict[str, Any]]:
    payload, actual_sha256 = load_strict_json_with_sha256(path)
    if actual_sha256.lower() != str(expected_sha256 or "").lower():
        raise ValueError("caller-bound entry-bars manifest SHA mismatch")
    if not isinstance(payload, Mapping):
        raise ValueError("entry-bars manifest must be a JSON object")
    if payload.get("schema_version") != "timing_entry_bars_source_manifest.v1":
        raise ValueError("entry-bars manifest schema mismatch")
    for field in (
        "paper_trading_only",
        "no_execution_signals",
        "does_not_modify_official_scores",
    ):
        if payload.get(field) is not True:
            raise ValueError(f"entry-bars manifest {field} must be true")
    validate_no_executable_instructions(payload, context="entry-bars manifest")
    sessions_value = payload.get("sessions")
    if not isinstance(sessions_value, list):
        raise ValueError("entry-bars manifest sessions must be a list")
    sessions: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for index, item in enumerate(sessions_value):
        if not isinstance(item, Mapping):
            raise ValueError(f"entry-bars manifest session {index} must be an object")
        code = _normalize_security_code(item.get("code"))
        day = str(item.get("entry_date") or "")
        bars = item.get("bars")
        if not code or not _is_iso_date(day) or not isinstance(bars, list):
            raise ValueError(f"entry-bars manifest session {index} identity is invalid")
        if (code, day) in sessions:
            raise ValueError(f"duplicate entry-bars manifest session: {code} {day}")
        if any(not isinstance(row, Mapping) for row in bars):
            raise ValueError(f"entry-bars manifest session {index} bars must be objects")
        sessions[(code, day)] = [dict(row) for row in bars]
    identity = _validate_entry_bars_source_identity(
        {
            "status": "validated",
            "source_kind": "strict_json_manifest",
            "path": str(path),
            "sha256": actual_sha256,
            "schema_version": payload.get("schema_version"),
            "as_of": payload.get("as_of"),
            "session_count": len(sessions),
        }
    )
    return _EntryBarsManifestClient(sessions), identity


def _is_iso_date(value: str) -> bool:
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _fetch_entry_session_bars(
    client: Any,
    *,
    code: str,
    expected_name: str,
    entry_date: str,
) -> list[dict[str, Any]]:
    compact_date = entry_date.replace("-", "")
    rows = client.get_stock_bars(
        code,
        f"{compact_date}000000",
        f"{compact_date}235959",
        frequency="1m",
        fq=None,
    )
    normalized = [dict(row) for row in rows or [] if isinstance(row, Mapping)]
    selected = [row for row in normalized if _bar_date(row) == entry_date]
    selected.sort(key=lambda row: str(row.get("time") or row.get("date") or ""))
    if any(_normalize_security_code(row.get("code")) != code for row in selected):
        raise ValueError(f"entry bar security code mismatch for {code} on {entry_date}")
    for row in selected:
        source_name = _normalize_security_name(row.get("name"))
        if source_name and expected_name and source_name != expected_name:
            raise ValueError(f"entry bar security name mismatch for {code} on {entry_date}")
        row["code"] = code
        row["name"] = expected_name or source_name
    if not validate_complete_a_share_session(selected, interval_minutes=1):
        return []
    return selected


def _resolve_calendar(
    *,
    path: Path | None,
    dates: Sequence[str] | None,
    as_of: str,
) -> dict[str, Any]:
    if path is not None:
        return load_trading_calendar(path, as_of=as_of)
    if dates is None:
        raise ValueError("an independent trading calendar is required")
    normalized = sorted({str(value) for value in dates if str(value) <= as_of})
    return {
        "dates": normalized,
        "source": "explicit_in_memory_calendar",
        "path": None,
        "sha256": None,
        "requested_start": normalized[0] if normalized else None,
        "requested_end": as_of,
    }


def _bar_date(row: Mapping[str, Any]) -> str:
    raw = "".join(character for character in str(row.get("time") or row.get("date") or "") if character.isdigit())
    if len(raw) < 8:
        return ""
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


def _normalize_security_code(value: Any) -> str:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    return digits.zfill(6) if digits else ""


def _normalize_security_name(value: Any) -> str:
    name = str(value or "").strip()
    return "" if name.casefold() in {"none", "null", "nan"} else name


def _is_weekday(value: str) -> bool:
    try:
        return date.fromisoformat(value).weekday() < 5
    except ValueError:
        return False


def _group_by_date(samples: list[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in samples:
        date = str(row.get("_sample_date") or "unknown_date")
        grouped.setdefault(date, []).append(row)
    return dict(sorted(grouped.items()))


def _markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# Timing Paper Trading Records",
        "",
        f"As of: `{report.get('as_of')}`",
        f"Snapshot: `{report.get('snapshot_label')}`",
        "",
        "- Paper-only: `True`",
        "- No execution signals: `True`",
        "- Does not modify official scores: `True`",
        "",
        "## Summary",
        "",
        f"- Sample count: `{summary.get('sample_count')}`",
        f"- Record count: `{summary.get('record_count')}`",
        f"- Labeled record count: `{summary.get('labeled_record_count')}`",
        f"- Unlabeled record count: `{summary.get('unlabeled_record_count')}`",
        f"- Version counts: `{summary.get('version_counts')}`",
        f"- Risk tag counts: `{summary.get('risk_tag_counts')}`",
        "",
        "## Records",
        "",
        "| Date | Version | Code | Name | Tags | MFE % | MAE % | Close % |",
        "|---|---|---|---|---|---:|---:|---:|",
    ]
    for record in (report.get("records") or [])[:200]:
        stats = record.get("path_stats") or {}
        tags = ", ".join(record.get("paper_risk_tags") or [])
        lines.append(
            f"| {record.get('as_of')} | `{record.get('timing_version_id')}` | `{record.get('code')}` | "
            f"{record.get('name') or ''} | {tags or '-'} | {stats.get('max_favorable_excursion_pct')} | "
            f"{stats.get('max_adverse_excursion_pct')} | {stats.get('close_return_pct')} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate paper-only timing observation records")
    parser.add_argument("--candidate-root", required=True)
    parser.add_argument("--candidate-source-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--snapshot-label", required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--selection-validation-root", default=str(PROJECT_ROOT / "reports" / "selection_validation"))
    parser.add_argument("--version-id", action="append")
    parser.add_argument("--concentration-threshold", type=int, default=2)
    parser.add_argument("--factor-exit-peak-giveback-pct", type=float, default=2.0)
    parser.add_argument("--bar-interval", required=True, choices=["1m", "5m"])
    parser.add_argument("--trading-calendar-path", required=True)
    parser.add_argument("--entry-bars-manifest", required=True)
    parser.add_argument("--expected-entry-bars-manifest-sha256", required=True)
    args = parser.parse_args(argv)
    client, entry_bars_source_identity = _load_entry_bars_manifest(
        Path(args.entry_bars_manifest),
        expected_sha256=args.expected_entry_bars_manifest_sha256,
    )
    result = run_timing_paper_trading_records(
        candidate_root=Path(args.candidate_root),
        candidate_source_root=Path(args.candidate_source_root),
        output_dir=Path(args.output_dir),
        as_of=args.as_of,
        snapshot_label=args.snapshot_label,
        start=args.start,
        end=args.end,
        selection_validation_root=Path(args.selection_validation_root) if args.selection_validation_root else None,
        version_ids=args.version_id,
        concentration_threshold=args.concentration_threshold,
        factor_exit_peak_giveback_pct=args.factor_exit_peak_giveback_pct,
        bar_interval=args.bar_interval,
        trading_calendar_path=Path(args.trading_calendar_path),
        client=client,
        entry_bars_source_identity=entry_bars_source_identity,
    )
    print(result["json_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
