"""Prospective daily evidence accumulation for the ML stock-ranker shadow."""

from __future__ import annotations

from datetime import date, datetime
import hashlib
import math
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)

from .contract import canonical_sha256, require_finite
from .feature_builder import build_feature_row
from .label_builder import build_forward_label_rows
from .schema import DISCLAIMER, MODE


DAILY_SNAPSHOT_SCHEMA_VERSION = "ml-stock-daily-snapshot-v1"
DAILY_ARCHIVE_INDEX_SCHEMA_VERSION = "ml-stock-daily-archive-index-v1"
LABEL_SNAPSHOT_SCHEMA_VERSION = "ml-stock-mature-label-snapshot-v1"
LABEL_ARCHIVE_INDEX_SCHEMA_VERSION = "ml-stock-label-archive-index-v1"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")

_FEATURE_CANDIDATE_FIELDS = (
    "code",
    "stock_code",
    "name",
    "sector_name",
    "sector_type",
    "pe",
    "pb",
    "total_mv",
    "market_cap",
    "pe_sector_relative",
    "pb_sector_relative",
    "market_cap_sector_percentile",
    "sector_trend_score",
    "sector_burst_score",
    "sector_direction_score",
    "direction_score_shadow",
    "data_quality_score",
    "factor_coverage",
    "linkage_v2",
    "linkage_v2_shadow",
    "linkage_v2_breakdown",
)


def _finite_number(value: Any, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{context} must be finite")
    return result


def _selection(report: Mapping[str, Any]) -> tuple[str, list[Mapping[str, Any]]]:
    formal = report.get("formal_candidate_selection")
    if (
        isinstance(formal, Mapping)
        and formal.get("status") == "active_for_paper_research"
        and isinstance(formal.get("selected"), list)
    ):
        selected = list(formal["selected"])
        if formal.get("selected_count") != len(selected):
            raise ValueError("formal candidate selected_count mismatch")
        return "formal_candidate_selection", selected

    active = report.get("direction_linkage_v2_selection_shadow")
    if (
        isinstance(active, Mapping)
        and active.get("schema_version")
        == "direction_linkage_v2_selection_shadow.v1"
        and active.get("mode") == MODE
        and isinstance(active.get("selected"), list)
    ):
        selected = list(active["selected"])
        if active.get("selected_count") != len(selected):
            raise ValueError("active direction/linkage V2 selected_count mismatch")
        return "direction_linkage_v2_selection_shadow", selected
    raise ValueError("active direction/linkage V2 selection is required")


def extract_candidate_snapshot(report: Mapping[str, Any]) -> dict[str, Any]:
    """Extract the active Paper/Shadow candidate universe without score writeback."""

    as_of_date = str(report.get("as_of_date") or "")
    if len(as_of_date) != 10:
        raise ValueError("candidate report as_of_date is required")
    selection_field, selected = _selection(report)
    if not selected:
        raise ValueError("active direction/linkage V2 selection is empty")

    feature_candidates: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for raw in selected:
        if not isinstance(raw, Mapping):
            raise ValueError("selected candidate must be an object")
        code = str(raw.get("code") or raw.get("stock_code") or "").zfill(6)
        if len(code) != 6 or not code.isdigit():
            raise ValueError("selected candidate stock code is invalid")
        if code in seen_codes:
            raise ValueError(f"duplicate selected stock identity: {as_of_date} {code}")
        seen_codes.add(code)
        sector_name = str(raw.get("sector_name") or "")
        if not sector_name:
            raise ValueError(f"selected candidate sector identity is missing: {code}")

        quant = _finite_number(raw.get("quant_score"), context=f"quant baseline {code}")
        linkage = raw.get("linkage_v2_shadow")
        if not isinstance(linkage, Mapping):
            linkage = raw.get("linkage_v2")
        if not isinstance(linkage, Mapping):
            raise ValueError(f"Linkage V2 evidence is missing: {code}")
        linkage_status = str(linkage.get("status") or "")
        if linkage_status not in {"ok", "partial", "unavailable"}:
            raise ValueError(f"Linkage V2 status is invalid: {code}")
        raw_linkage_score = linkage.get("score")
        linkage_score = None
        if raw_linkage_score is not None:
            linkage_score = _finite_number(
                raw_linkage_score, context=f"Linkage V2 baseline {code}"
            )
            if not 0.0 <= linkage_score <= 1.0:
                raise ValueError(f"Linkage V2 baseline is outside [0, 1]: {code}")
        if linkage_status in {"ok", "partial"} and linkage_score is None:
            raise ValueError(f"available Linkage V2 baseline has no score: {code}")
        if linkage_status == "unavailable" and linkage_score is not None:
            raise ValueError(f"unavailable Linkage V2 baseline has a score: {code}")

        candidate = {
            key: raw[key]
            for key in _FEATURE_CANDIDATE_FIELDS
            if key in raw
        }
        candidate["code"] = code
        feature_candidates.append(candidate)
        baseline_rows.append(
            {
                "as_of_date": as_of_date,
                "stock_code": code,
                "sector_name": sector_name,
                "quant_baseline_score_shadow": quant,
                "linkage_v2_baseline_score_shadow": (
                    linkage_score * 100.0 if linkage_score is not None else None
                ),
                "linkage_v2_status": linkage_status,
                "rule_eligible": True,
            }
        )

    feature_candidates.sort(key=lambda row: row["code"])
    baseline_rows.sort(key=lambda row: row["stock_code"])
    return {
        "as_of_date": as_of_date,
        "selection_source_field": selection_field,
        "candidate_count": len(feature_candidates),
        "feature_candidates": feature_candidates,
        "baseline_rows": baseline_rows,
    }


def _source_identity(source: Mapping[str, Any], *, context: str) -> dict[str, Any]:
    path = str(source.get("path") or "")
    sha256 = str(source.get("sha256") or "").lower()
    if not path or not _SHA256.fullmatch(sha256):
        raise ValueError(f"{context} path and lowercase SHA-256 are required")
    result = {"path": path, "sha256": sha256}
    for field in ("generated_at", "as_of_date", "sector_name", "source"):
        if field in source:
            result[field] = source[field]
    return result


def _verify_source_file_if_addressable(
    source: Mapping[str, Any], *, context: str
) -> None:
    """Recheck absolute source paths; relative fixture identifiers remain logical."""

    path = Path(str(source.get("path") or ""))
    if not path.is_absolute():
        return
    if not path.is_file():
        raise ValueError(f"{context} source file is missing")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != str(source.get("sha256") or "").lower():
        raise ValueError(f"{context} source file SHA mismatch")


def _canonical_calendar(calendar: Mapping[str, Any], *, as_of_date: str) -> dict[str, Any]:
    dates = calendar.get("dates")
    if not isinstance(dates, list) or dates != sorted(dates) or len(dates) != len(set(dates)):
        raise ValueError("daily snapshot trading calendar must be sorted and unique")
    for value in dates:
        if date.fromisoformat(str(value)).isoformat() != value:
            raise ValueError("daily snapshot trading calendar contains an invalid date")
    if as_of_date not in dates or not any(value > as_of_date for value in dates):
        raise ValueError("daily snapshot calendar must include signal and future dates")
    identity = {
        "dates": list(dates),
        "source": str(calendar.get("source") or ""),
        "path": str(calendar.get("path") or ""),
        "sha256": str(calendar.get("sha256") or "").lower(),
        "requested_start": str(calendar.get("requested_start") or ""),
        "requested_end": str(calendar.get("requested_end") or ""),
    }
    if (
        not identity["source"]
        or not identity["path"]
        or not _SHA256.fullmatch(identity["sha256"])
    ):
        raise ValueError("daily snapshot calendar identity is incomplete")
    return identity


def _normalize_bars(
    bars_by_code: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    candidates: Sequence[Mapping[str, Any]],
    as_of_date: str,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    normalized: dict[str, list[dict[str, Any]]] = {}
    feature_rows: list[dict[str, Any]] = []
    expected_codes = [str(row["code"]) for row in candidates]
    if set(bars_by_code) != set(expected_codes):
        raise ValueError("daily snapshot bars must exactly match the candidate universe")
    for candidate in candidates:
        code = str(candidate["code"])
        raw_bars = bars_by_code.get(code)
        if not isinstance(raw_bars, Sequence) or isinstance(raw_bars, (str, bytes)):
            raise ValueError(f"daily snapshot bars are missing: {code}")
        rows: list[dict[str, Any]] = []
        seen_dates: set[str] = set()
        for raw in raw_bars:
            if not isinstance(raw, Mapping):
                raise ValueError(f"daily snapshot bar must be an object: {code}")
            bar = dict(raw)
            day = str(bar.get("date") or "")
            try:
                canonical_day = date.fromisoformat(day).isoformat()
            except ValueError as exc:
                raise ValueError(f"daily snapshot bar date is invalid: {code}") from exc
            if canonical_day != day or day > as_of_date:
                raise ValueError(f"daily snapshot bar is outside its as-of boundary: {code}")
            if day in seen_dates:
                raise ValueError(f"daily snapshot bar date is duplicated: {code} {day}")
            seen_dates.add(day)
            rows.append(bar)
        rows.sort(key=lambda row: row["date"])
        if len(rows) < 21 or rows[-1]["date"] != as_of_date:
            raise ValueError(f"daily snapshot requires 21 bars ending on as_of_date: {code}")
        feature_rows.append(build_feature_row(candidate, rows, as_of_date=as_of_date))
        normalized[code] = rows
    feature_rows.sort(key=lambda row: row["stock_code"])
    return normalized, feature_rows


def _bars_source_manifest(
    *,
    bars_by_code: Mapping[str, Sequence[Mapping[str, Any]]],
    bars_source: Mapping[str, Any],
    as_of_date: str,
) -> dict[str, dict[str, Any]]:
    """Bind each normalized bar payload to the provider that actually supplied it."""

    by_code = bars_source.get("by_code")
    if not isinstance(by_code, Mapping):
        by_code = {}
    requested_source = str(bars_source.get("provider") or "")
    result: dict[str, dict[str, Any]] = {}
    for code in sorted(bars_by_code):
        supplied = by_code.get(code)
        supplied = supplied if isinstance(supplied, Mapping) else {}
        actual_source = str(
            supplied.get("actual_source")
            or supplied.get("source")
            or (requested_source if requested_source != "auto" else "")
        )
        if not actual_source or actual_source == "auto":
            raise ValueError(
                f"actual bars source is required for replayable snapshot: {code}"
            )
        result[code] = {
            "stock_code": code,
            "requested_source": str(
                supplied.get("requested_source") or requested_source
            ),
            "actual_source": actual_source,
            "adjustment": "qfq",
            "frequency": "1d",
            "query_end": as_of_date,
            "bars_sha256": canonical_sha256(list(bars_by_code[code])),
        }
    return result


def _feature_replay_signature(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Ignore only the runtime build timestamp when replaying feature rows."""

    output: list[dict[str, Any]] = []
    for row in rows:
        copied = dict(row)
        provenance = copied.get("provenance")
        if isinstance(provenance, Mapping):
            provenance_copy = dict(provenance)
            provenance_copy.pop("built_at", None)
            copied["provenance"] = provenance_copy
        output.append(copied)
    return output


def _pit_classification(
    *,
    as_of_date: str,
    captured_at: datetime,
    candidate_source: Mapping[str, Any],
    constituent_sources: Sequence[Mapping[str, Any]],
) -> tuple[bool, list[str], dict[str, Any]]:
    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ValueError("captured_at must be timezone-aware")
    reasons: list[str] = []
    if captured_at.date().isoformat() != as_of_date:
        reasons.append("capture_after_signal_date")
    if str(candidate_source.get("as_of_date") or "") != as_of_date:
        reasons.append("candidate_source_as_of_date_mismatch")
    generated_text = str(candidate_source.get("generated_at") or "")
    try:
        generated = datetime.fromisoformat(generated_text)
    except ValueError:
        generated = None
    if generated is None:
        timestamp_quality = {
            "status": "invalid",
            "accepted_as_ordering_witness": False,
            "archive_witness": "unavailable",
        }
        reasons.append("candidate_source_timestamp_invalid")
    elif generated.tzinfo is None or generated.utcoffset() is None:
        timestamp_quality = {
            "status": "naive",
            "accepted_as_ordering_witness": False,
            "archive_witness": "timezone_aware_capture_bound_to_source_sha_and_as_of_date",
        }
        if generated.date().isoformat() != as_of_date:
            reasons.append("candidate_source_generated_after_signal_date")
    else:
        timestamp_quality = {
            "status": "timezone_aware",
            "accepted_as_ordering_witness": True,
            "archive_witness": "timezone_aware_capture_bound_to_source_sha_and_as_of_date",
        }
        if generated.date().isoformat() != as_of_date:
            reasons.append("candidate_source_generated_after_signal_date")
        if generated > captured_at:
            reasons.append("candidate_source_generated_after_archive_capture")
    if any(str(source.get("as_of_date") or "") != as_of_date for source in constituent_sources):
        reasons.append("constituent_source_not_versioned_for_signal_date")
    return not reasons, reasons, timestamp_quality


def archive_daily_snapshot(
    *,
    archive_root: Path | str,
    candidate_report: Mapping[str, Any],
    candidate_source: Mapping[str, Any],
    constituent_sources: Sequence[Mapping[str, Any]],
    bars_by_code: Mapping[str, Sequence[Mapping[str, Any]]],
    bars_source: Mapping[str, Any],
    trading_calendar: Mapping[str, Any],
    captured_at: datetime | None = None,
) -> dict[str, Any]:
    """Append one immutable daily feature universe to a content-bound archive."""

    captured_at = captured_at or datetime.now().astimezone()
    extracted = extract_candidate_snapshot(candidate_report)
    as_of_date = extracted["as_of_date"]
    candidate_identity = _source_identity(candidate_source, context="candidate source")
    if "generated_at" not in candidate_identity:
        raise ValueError("candidate source generated_at is required")
    if "as_of_date" not in candidate_identity:
        candidate_identity["as_of_date"] = as_of_date
    constituent_identities = [
        _source_identity(source, context="constituent source")
        for source in constituent_sources
    ]
    selected_sectors = {str(row.get("sector_name") or "") for row in extracted["feature_candidates"]}
    recorded_sectors = {str(row.get("sector_name") or "") for row in constituent_identities}
    if selected_sectors != recorded_sectors:
        raise ValueError("dated constituent sources must exactly cover selected sectors")
    calendar_identity = _canonical_calendar(trading_calendar, as_of_date=as_of_date)
    if sum(value > as_of_date for value in calendar_identity["dates"]) < 5:
        prospective_calendar_block = "calendar_missing_5d_target"
    else:
        prospective_calendar_block = None
    bars_identity = {
        "provider": str(bars_source.get("provider") or ""),
        "adjustment": str(bars_source.get("adjustment") or ""),
        "frequency": str(bars_source.get("frequency") or ""),
        "query_end": str(bars_source.get("query_end") or ""),
    }
    if bars_identity != {
        "provider": bars_identity["provider"],
        "adjustment": "qfq",
        "frequency": "1d",
        "query_end": as_of_date,
    } or not bars_identity["provider"]:
        raise ValueError("daily snapshot bars source must be dated 1d qfq evidence")
    normalized_bars, feature_rows = _normalize_bars(
        bars_by_code,
        candidates=extracted["feature_candidates"],
        as_of_date=as_of_date,
    )
    bars_source_by_code = _bars_source_manifest(
        bars_by_code=normalized_bars,
        bars_source=bars_source,
        as_of_date=as_of_date,
    )
    prospective, blocking_reasons, timestamp_quality = _pit_classification(
        as_of_date=as_of_date,
        captured_at=captured_at,
        candidate_source=candidate_identity,
        constituent_sources=constituent_identities,
    )
    if prospective_calendar_block is not None:
        prospective = False
        blocking_reasons.append(prospective_calendar_block)

    input_identity = {
        "as_of_date": as_of_date,
        "selection_source_field": extracted["selection_source_field"],
        "candidate_source": candidate_identity,
        "constituent_sources": sorted(
            constituent_identities,
            key=lambda row: (str(row.get("sector_name") or ""), row["path"]),
        ),
        "bars_source": bars_identity,
        "bars_source_by_code": bars_source_by_code,
        "trading_calendar": calendar_identity,
        "feature_candidates": extracted["feature_candidates"],
        "bars_by_code": normalized_bars,
        "baseline_rows": extracted["baseline_rows"],
    }
    input_identity_sha256 = canonical_sha256(input_identity)
    root = Path(archive_root)
    snapshot_path = root / "snapshots" / f"{as_of_date}.json"
    index_path = root / "index.json"
    entries: list[dict[str, Any]] = []
    if index_path.exists():
        index, _index_file_sha = load_strict_json_with_sha256(index_path)
        if (
            not isinstance(index, Mapping)
            or index.get("schema_version") != DAILY_ARCHIVE_INDEX_SCHEMA_VERSION
            or index.get("mode") != MODE
            or not isinstance(index.get("entries"), list)
        ):
            raise ValueError("ML daily archive index is invalid")
        entries = list(index["entries"])
    existing = next((row for row in entries if row.get("as_of_date") == as_of_date), None)
    if existing is not None:
        snapshot, snapshot_sha256 = load_strict_json_with_sha256(snapshot_path)
        if snapshot_sha256 != existing.get("snapshot_sha256"):
            raise ValueError("immutable daily snapshot SHA mismatch")
        if snapshot.get("input_identity_sha256") != input_identity_sha256:
            raise ValueError("immutable daily snapshot input changed")
        return {
            "created": False,
            "snapshot_path": str(snapshot_path),
            "snapshot_sha256": snapshot_sha256,
            "snapshot": snapshot,
        }
    if entries and as_of_date <= str(entries[-1].get("as_of_date") or ""):
        raise ValueError("daily snapshots must be appended in increasing date order")

    previous_entry_sha256 = entries[-1]["entry_sha256"] if entries else None
    snapshot = {
        "schema_version": DAILY_SNAPSHOT_SCHEMA_VERSION,
        "mode": MODE,
        "status": "captured",
        "as_of_date": as_of_date,
        "captured_at": captured_at.isoformat(),
        "selection_source_field": extracted["selection_source_field"],
        "candidate_count": extracted["candidate_count"],
        "feature_row_count": len(feature_rows),
        "strict_pit_eligible": prospective,
        "pit_evidence_status": (
            "prospective_pre_label_capture" if prospective else "historical_reconstruction"
        ),
        "pit_blocking_reasons": blocking_reasons,
        "source_timestamp_quality": timestamp_quality,
        "input_identity_sha256": input_identity_sha256,
        "candidate_universe_sha256": canonical_sha256(extracted["baseline_rows"]),
        "constituent_universe_sha256": canonical_sha256(constituent_identities),
        "archive_chain_previous_sha256": previous_entry_sha256,
        "source_manifest": {
            "candidate_source": candidate_identity,
            "constituent_sources": input_identity["constituent_sources"],
            "bars_source": bars_identity,
            "bars_source_by_code": bars_source_by_code,
            "trading_calendar": calendar_identity,
        },
        "feature_candidates": extracted["feature_candidates"],
        "bars_by_code": normalized_bars,
        "bars_source_by_code": bars_source_by_code,
        "feature_rows": feature_rows,
        "baseline_rows": extracted["baseline_rows"],
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    require_finite(snapshot, context="ML daily snapshot")
    validate_no_executable_instructions(snapshot, context="ML daily snapshot")
    write_strict_json_atomic(snapshot_path, snapshot)
    _persisted, snapshot_sha256 = load_strict_json_with_sha256(snapshot_path)
    entry_core = {
        "as_of_date": as_of_date,
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256": snapshot_sha256,
        "previous_entry_sha256": previous_entry_sha256,
    }
    entry = {**entry_core, "entry_sha256": canonical_sha256(entry_core)}
    entries.append(entry)
    index = {
        "schema_version": DAILY_ARCHIVE_INDEX_SCHEMA_VERSION,
        "mode": MODE,
        "status": "active",
        "entry_count": len(entries),
        "chain_head_sha256": entry["entry_sha256"],
        "entries": entries,
        "promotion_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    validate_no_executable_instructions(index, context="ML daily archive index")
    write_strict_json_atomic(index_path, index)
    return {
        "created": True,
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256": snapshot_sha256,
        "snapshot": snapshot,
    }


def _load_daily_snapshot(
    archive_root: Path, *, signal_date: str
) -> tuple[dict[str, Any], str]:
    index_path = archive_root / "index.json"
    index, _index_sha = load_strict_json_with_sha256(index_path)
    if (
        not isinstance(index, Mapping)
        or index.get("schema_version") != DAILY_ARCHIVE_INDEX_SCHEMA_VERSION
        or not isinstance(index.get("entries"), list)
    ):
        raise ValueError("ML daily archive index is invalid")
    entry = next(
        (row for row in index["entries"] if row.get("as_of_date") == signal_date),
        None,
    )
    if not isinstance(entry, Mapping):
        raise ValueError(f"ML daily snapshot is unavailable: {signal_date}")
    snapshot_path = archive_root / "snapshots" / f"{signal_date}.json"
    snapshot, snapshot_sha = load_strict_json_with_sha256(snapshot_path)
    if snapshot_sha != entry.get("snapshot_sha256"):
        raise ValueError("ML daily snapshot SHA mismatch")
    if (
        not isinstance(snapshot, dict)
        or snapshot.get("schema_version") != DAILY_SNAPSHOT_SCHEMA_VERSION
        or snapshot.get("as_of_date") != signal_date
    ):
        raise ValueError("ML daily snapshot contract mismatch")
    return snapshot, snapshot_sha


def _label_price_rows(
    *,
    signal_date: str,
    label_as_of_date: str,
    baseline_rows: Sequence[Mapping[str, Any]],
    stock_bars_by_code: Mapping[str, Sequence[Mapping[str, Any]]],
    sector_bars_by_name: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    expected_codes = {str(row.get("stock_code") or "").zfill(6) for row in baseline_rows}
    if set(stock_bars_by_code) != expected_codes:
        raise ValueError("label stock bars must exactly match the feature candidate universe")
    stock_rows: list[dict[str, Any]] = []
    sector_by_code = {
        str(row.get("stock_code") or "").zfill(6): str(row.get("sector_name") or "")
        for row in baseline_rows
    }
    for code in sorted(expected_codes):
        seen_dates: set[str] = set()
        for raw in stock_bars_by_code[code]:
            day = str(raw.get("date") or "")
            if day in seen_dates:
                raise ValueError(f"duplicate label stock bar: {code} {day}")
            seen_dates.add(day)
            if day < signal_date or day > label_as_of_date:
                continue
            stock_rows.append(
                {
                    "stock_code": code,
                    "sector_name": sector_by_code[code],
                    "date": day,
                    "close": raw.get("close"),
                }
            )
    expected_sectors = set(sector_by_code.values())
    if set(sector_bars_by_name) != expected_sectors:
        raise ValueError("label sector bars must exactly match candidate sector identities")
    sector_rows: list[dict[str, Any]] = []
    for sector_name in sorted(expected_sectors):
        seen_dates: set[str] = set()
        for raw in sector_bars_by_name[sector_name]:
            day = str(raw.get("date") or "")
            if day in seen_dates:
                raise ValueError(f"duplicate label sector bar: {sector_name} {day}")
            seen_dates.add(day)
            if day < signal_date or day > label_as_of_date:
                continue
            sector_rows.append(
                {
                    "sector_name": sector_name,
                    "date": day,
                    "close": raw.get("close"),
                }
            )
    return stock_rows, sector_rows


def archive_mature_label_snapshot(
    *,
    archive_root: Path | str,
    signal_date: str,
    label_as_of_date: str,
    stock_bars_by_code: Mapping[str, Sequence[Mapping[str, Any]]],
    sector_bars_by_name: Mapping[str, Sequence[Mapping[str, Any]]],
    label_source: Mapping[str, Any],
    captured_at: datetime | None = None,
) -> dict[str, Any]:
    """Persist one label set only after the exact five-day target has matured."""

    root = Path(archive_root)
    captured_at = captured_at or datetime.now().astimezone()
    if captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ValueError("captured_at must be timezone-aware")
    snapshot, feature_snapshot_sha = _load_daily_snapshot(
        root, signal_date=signal_date
    )
    calendar = snapshot.get("source_manifest", {}).get("trading_calendar")
    if not isinstance(calendar, Mapping) or not isinstance(calendar.get("dates"), list):
        raise ValueError("feature snapshot trading calendar is unavailable")
    trading_dates = list(calendar["dates"])
    try:
        signal_index = trading_dates.index(signal_date)
    except ValueError as exc:
        raise ValueError("signal date is absent from feature trading calendar") from exc
    target_index = signal_index + 5
    if target_index >= len(trading_dates):
        raise ValueError("feature trading calendar does not contain a 5-day target")
    target_5d = trading_dates[target_index]
    if label_as_of_date < target_5d:
        return {
            "status": "pending_label_maturity",
            "signal_date": signal_date,
            "target_5d": target_5d,
            "promotion_allowed": False,
        }
    if captured_at.date().isoformat() < label_as_of_date:
        raise ValueError("label capture timestamp precedes label data as-of date")
    label_source_identity = {
        "provider": str(label_source.get("provider") or ""),
        "adjustment": str(label_source.get("adjustment") or ""),
        "frequency": str(label_source.get("frequency") or ""),
        "query_end": str(label_source.get("query_end") or ""),
    }
    if label_source_identity != {
        "provider": label_source_identity["provider"],
        "adjustment": "qfq",
        "frequency": "1d",
        "query_end": label_as_of_date,
    } or not label_source_identity["provider"]:
        raise ValueError("label source must be dated 1d qfq evidence")

    baseline_rows = snapshot.get("baseline_rows")
    if not isinstance(baseline_rows, list):
        raise ValueError("feature snapshot baseline identities are unavailable")
    stock_rows, sector_rows = _label_price_rows(
        signal_date=signal_date,
        label_as_of_date=label_as_of_date,
        baseline_rows=baseline_rows,
        stock_bars_by_code=stock_bars_by_code,
        sector_bars_by_name=sector_bars_by_name,
    )
    built = build_forward_label_rows(
        stock_rows,
        sector_rows,
        trading_dates=trading_dates,
    )
    expected_codes = {str(row["stock_code"]) for row in baseline_rows}
    label_rows = [
        row
        for row in built
        if row["as_of_date"] == signal_date and row["stock_code"] in expected_codes
    ]
    label_rows.sort(key=lambda row: row["stock_code"])
    if {row["stock_code"] for row in label_rows} != expected_codes:
        raise ValueError("mature label rows do not cover the feature candidate universe")
    required_keys = {
        f"future_{kind}return_{horizon}d"
        for kind in ("", "sector_", "excess_")
        for horizon in (1, 3, 5)
    }
    for row in label_rows:
        labels = row.get("labels")
        dates = row.get("label_dates")
        if (
            not isinstance(labels, Mapping)
            or not isinstance(dates, Mapping)
            or any(labels.get(key) is None for key in required_keys)
            or row.get("training_label_end_date") != target_5d
        ):
            raise ValueError("1d/3d/5d stock-sector labels are not fully mature")

    input_identity = {
        "signal_date": signal_date,
        "label_as_of_date": label_as_of_date,
        "feature_snapshot_sha256": feature_snapshot_sha,
        "label_source": label_source_identity,
        "trading_calendar": dict(calendar),
        "stock_price_rows": stock_rows,
        "sector_price_rows": sector_rows,
    }
    input_identity_sha256 = canonical_sha256(input_identity)
    label_path = root / "labels" / f"{signal_date}.json"
    if label_path.exists():
        existing, label_sha = load_strict_json_with_sha256(label_path)
        if existing.get("input_identity_sha256") != input_identity_sha256:
            raise ValueError("immutable mature label snapshot input changed")
        return {
            "status": "captured",
            "created": False,
            "label_snapshot_path": str(label_path),
            "label_snapshot_sha256": label_sha,
            "label_snapshot": existing,
        }

    label_snapshot = {
        "schema_version": LABEL_SNAPSHOT_SCHEMA_VERSION,
        "mode": MODE,
        "status": "captured",
        "signal_date": signal_date,
        "label_as_of_date": label_as_of_date,
        "target_5d": target_5d,
        "captured_at": captured_at.isoformat(),
        "feature_snapshot_sha256": feature_snapshot_sha,
        "candidate_universe_sha256": snapshot["candidate_universe_sha256"],
        "input_identity_sha256": input_identity_sha256,
        "strict_pit_eligible": bool(snapshot.get("strict_pit_eligible", False)),
        "pit_evidence_status": (
            "prospective_labels_captured_after_maturity"
            if snapshot.get("strict_pit_eligible")
            else "historical_reconstruction_labels"
        ),
        "source_manifest": {
            "label_source": label_source_identity,
            "trading_calendar": dict(calendar),
            "stock_price_rows_sha256": canonical_sha256(stock_rows),
            "sector_price_rows_sha256": canonical_sha256(sector_rows),
        },
        "stock_price_rows": stock_rows,
        "sector_price_rows": sector_rows,
        "label_row_count": len(label_rows),
        "label_rows": label_rows,
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    require_finite(label_snapshot, context="ML mature label snapshot")
    validate_no_executable_instructions(
        label_snapshot, context="ML mature label snapshot"
    )
    write_strict_json_atomic(label_path, label_snapshot)
    _persisted, label_sha = load_strict_json_with_sha256(label_path)

    labels_index_path = root / "labels_index.json"
    entries: list[dict[str, Any]] = []
    if labels_index_path.exists():
        labels_index, _labels_index_sha = load_strict_json_with_sha256(
            labels_index_path
        )
        if (
            labels_index.get("schema_version") != LABEL_ARCHIVE_INDEX_SCHEMA_VERSION
            or not isinstance(labels_index.get("entries"), list)
        ):
            raise ValueError("ML label archive index is invalid")
        entries = list(labels_index["entries"])
    if entries and signal_date <= str(entries[-1].get("signal_date") or ""):
        raise ValueError("mature label snapshots must be appended in signal-date order")
    previous_entry_sha256 = entries[-1]["entry_sha256"] if entries else None
    entry_core = {
        "signal_date": signal_date,
        "label_snapshot_path": str(label_path),
        "label_snapshot_sha256": label_sha,
        "feature_snapshot_sha256": feature_snapshot_sha,
        "previous_entry_sha256": previous_entry_sha256,
    }
    entry = {**entry_core, "entry_sha256": canonical_sha256(entry_core)}
    entries.append(entry)
    labels_index = {
        "schema_version": LABEL_ARCHIVE_INDEX_SCHEMA_VERSION,
        "mode": MODE,
        "status": "active",
        "entry_count": len(entries),
        "chain_head_sha256": entry["entry_sha256"],
        "entries": entries,
        "promotion_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    write_strict_json_atomic(labels_index_path, labels_index)
    return {
        "status": "captured",
        "created": True,
        "label_snapshot_path": str(label_path),
        "label_snapshot_sha256": label_sha,
        "label_snapshot": label_snapshot,
    }


def _verify_chain_entry(
    entry: Mapping[str, Any],
    *,
    date_field: str,
    expected_previous: str | None,
    context: str,
) -> str:
    entry_sha256 = str(entry.get("entry_sha256") or "")
    core = {key: value for key, value in entry.items() if key != "entry_sha256"}
    if core.get("previous_entry_sha256") != expected_previous:
        raise ValueError(f"{context} previous-entry chain mismatch")
    if canonical_sha256(core) != entry_sha256:
        raise ValueError(f"{context} entry SHA mismatch")
    if not str(entry.get(date_field) or ""):
        raise ValueError(f"{context} date identity is missing")
    return entry_sha256


def _verify_replayable_snapshot(snapshot: Mapping[str, Any]) -> bool | None:
    """Rebuild a snapshot's features and PIT classification from archived inputs.

    Older historical reconstructions predate the replayable-bar contract. They are
    retained for audit history but can never contribute a strict training date.
    """

    source_manifest = snapshot.get("source_manifest")
    feature_candidates = snapshot.get("feature_candidates")
    bars_by_code = snapshot.get("bars_by_code")
    bars_source_by_code = snapshot.get("bars_source_by_code")
    if (
        not isinstance(source_manifest, Mapping)
        or not isinstance(feature_candidates, list)
        or not isinstance(bars_by_code, Mapping)
        or not isinstance(bars_source_by_code, Mapping)
    ):
        if snapshot.get("strict_pit_eligible") is True:
            raise ValueError("strict snapshot lacks replayable bar evidence")
        return None

    as_of_date = str(snapshot.get("as_of_date") or "")
    bars_source = source_manifest.get("bars_source")
    if not isinstance(bars_source, Mapping):
        raise ValueError("replayable snapshot bars source is missing")
    normalized_bars, rebuilt_features = _normalize_bars(
        bars_by_code,
        candidates=feature_candidates,
        as_of_date=as_of_date,
    )
    expected_sources = _bars_source_manifest(
        bars_by_code=normalized_bars,
        bars_source={**dict(bars_source), "by_code": bars_source_by_code},
        as_of_date=as_of_date,
    )
    if expected_sources != bars_source_by_code:
        raise ValueError("replayable snapshot bar source identity mismatch")
    stored_features = snapshot.get("feature_rows")
    if not isinstance(stored_features, list) or _feature_replay_signature(
        stored_features
    ) != _feature_replay_signature(rebuilt_features):
        raise ValueError("replayable snapshot features cannot be reproduced")

    candidate_source = source_manifest.get("candidate_source")
    constituent_sources = source_manifest.get("constituent_sources")
    calendar = source_manifest.get("trading_calendar")
    if (
        not isinstance(candidate_source, Mapping)
        or not isinstance(constituent_sources, list)
        or not isinstance(calendar, Mapping)
    ):
        raise ValueError("replayable snapshot source identity is incomplete")
    normalized_candidate_source = _source_identity(
        candidate_source, context="replayable candidate source"
    )
    if normalized_candidate_source != dict(candidate_source):
        raise ValueError("replayable candidate source identity is not canonical")
    _verify_source_file_if_addressable(
        candidate_source, context="replayable candidate"
    )
    normalized_constituents = [
        _source_identity(row, context="replayable constituent source")
        for row in constituent_sources
    ]
    if sorted(normalized_constituents, key=lambda row: (str(row.get("sector_name") or ""), row["path"])) != sorted(
        [dict(row) for row in constituent_sources],
        key=lambda row: (str(row.get("sector_name") or ""), row["path"]),
    ):
        raise ValueError("replayable constituent source identity is not canonical")
    for row in constituent_sources:
        _verify_source_file_if_addressable(row, context="replayable constituent")
    canonical_calendar = _canonical_calendar(calendar, as_of_date=as_of_date)
    if canonical_calendar != dict(calendar):
        raise ValueError("replayable trading calendar identity is not canonical")
    _verify_source_file_if_addressable(calendar, context="replayable calendar")
    captured_at = datetime.fromisoformat(str(snapshot.get("captured_at") or ""))
    prospective, reasons, timestamp_quality = _pit_classification(
        as_of_date=as_of_date,
        captured_at=captured_at,
        candidate_source=candidate_source,
        constituent_sources=constituent_sources,
    )
    if sum(value > as_of_date for value in canonical_calendar["dates"]) < 5:
        prospective = False
        reasons.append("calendar_missing_5d_target")
    if bool(snapshot.get("strict_pit_eligible")) != prospective:
        raise ValueError("snapshot strict PIT flag does not match replayed evidence")
    if set(snapshot.get("pit_blocking_reasons") or []) != set(reasons):
        raise ValueError("snapshot PIT blocking reasons do not match replayed evidence")
    if snapshot.get("source_timestamp_quality") != timestamp_quality:
        raise ValueError("snapshot source timestamp quality does not match replayed evidence")
    baseline_rows = snapshot.get("baseline_rows")
    input_identity = {
        "as_of_date": as_of_date,
        "selection_source_field": snapshot.get("selection_source_field"),
        "candidate_source": dict(candidate_source),
        "constituent_sources": sorted(
            [dict(row) for row in constituent_sources],
            key=lambda row: (str(row.get("sector_name") or ""), row["path"]),
        ),
        "bars_source": dict(bars_source),
        "bars_source_by_code": dict(bars_source_by_code),
        "trading_calendar": dict(calendar),
        "feature_candidates": feature_candidates,
        "bars_by_code": normalized_bars,
        "baseline_rows": baseline_rows,
    }
    if snapshot.get("input_identity_sha256") != canonical_sha256(input_identity):
        raise ValueError("replayable snapshot input identity cannot be reproduced")
    return prospective


def verify_accumulation_archive(archive_root: Path | str) -> dict[str, Any]:
    """Re-verify every archived input, hash-chain entry, and mature label."""

    root = Path(archive_root).resolve()
    daily_index_path = root / "index.json"
    daily_index, daily_index_sha = load_strict_json_with_sha256(daily_index_path)
    if (
        not isinstance(daily_index, Mapping)
        or daily_index.get("schema_version") != DAILY_ARCHIVE_INDEX_SCHEMA_VERSION
        or daily_index.get("mode") != MODE
        or not isinstance(daily_index.get("entries"), list)
    ):
        raise ValueError("ML daily archive index is invalid")
    daily_entries = list(daily_index["entries"])
    if daily_index.get("entry_count") != len(daily_entries):
        raise ValueError("ML daily archive entry_count mismatch")

    snapshots_by_date: dict[str, dict[str, Any]] = {}
    snapshot_manifest: list[dict[str, Any]] = []
    previous: str | None = None
    prior_date: str | None = None
    for raw_entry in daily_entries:
        if not isinstance(raw_entry, Mapping):
            raise ValueError("ML daily archive entry must be an object")
        day = str(raw_entry.get("as_of_date") or "")
        if prior_date is not None and day <= prior_date:
            raise ValueError("ML daily archive dates are not strictly increasing")
        previous = _verify_chain_entry(
            raw_entry,
            date_field="as_of_date",
            expected_previous=previous,
            context="ML daily archive",
        )
        expected_path = root / "snapshots" / f"{day}.json"
        snapshot, snapshot_sha = load_strict_json_with_sha256(expected_path)
        if snapshot_sha != raw_entry.get("snapshot_sha256"):
            raise ValueError("ML daily snapshot file SHA mismatch")
        if (
            snapshot.get("schema_version") != DAILY_SNAPSHOT_SCHEMA_VERSION
            or snapshot.get("mode") != MODE
            or snapshot.get("as_of_date") != day
            or snapshot.get("archive_chain_previous_sha256")
            != raw_entry.get("previous_entry_sha256")
        ):
            raise ValueError("ML daily snapshot identity mismatch")
        feature_rows = snapshot.get("feature_rows")
        baseline_rows = snapshot.get("baseline_rows")
        if not isinstance(feature_rows, list) or not isinstance(baseline_rows, list):
            raise ValueError("ML daily snapshot feature/baseline rows are missing")
        feature_codes = [str(row.get("stock_code") or "") for row in feature_rows]
        baseline_codes = [str(row.get("stock_code") or "") for row in baseline_rows]
        if (
            len(feature_codes) != len(set(feature_codes))
            or feature_codes != baseline_codes
            or snapshot.get("candidate_count") != len(feature_codes)
            or snapshot.get("feature_row_count") != len(feature_rows)
            or snapshot.get("candidate_universe_sha256")
            != canonical_sha256(baseline_rows)
        ):
            raise ValueError("ML daily snapshot candidate universe mismatch")
        replayed_strict = _verify_replayable_snapshot(snapshot)
        if replayed_strict is None and snapshot.get("strict_pit_eligible") is True:
            raise ValueError("legacy snapshot cannot claim strict PIT")
        snapshots_by_date[day] = snapshot
        snapshot_manifest.append(
            {
                "as_of_date": day,
                "path": str(expected_path),
                "sha256": snapshot_sha,
                "entry_sha256": previous,
                "strict_pit_eligible": bool(replayed_strict),
                "candidate_count": len(feature_rows),
            }
        )
        prior_date = day
    if (previous if daily_entries else None) != daily_index.get("chain_head_sha256"):
        raise ValueError("ML daily archive chain head mismatch")

    label_entries: list[Mapping[str, Any]] = []
    labels_index_path = root / "labels_index.json"
    labels_index_sha = None
    if labels_index_path.exists():
        labels_index, labels_index_sha = load_strict_json_with_sha256(
            labels_index_path
        )
        if (
            not isinstance(labels_index, Mapping)
            or labels_index.get("schema_version") != LABEL_ARCHIVE_INDEX_SCHEMA_VERSION
            or labels_index.get("mode") != MODE
            or not isinstance(labels_index.get("entries"), list)
        ):
            raise ValueError("ML label archive index is invalid")
        label_entries = list(labels_index["entries"])
        if labels_index.get("entry_count") != len(label_entries):
            raise ValueError("ML label archive entry_count mismatch")
    else:
        labels_index = None

    labels_by_date: dict[str, dict[str, Any]] = {}
    label_manifest: list[dict[str, Any]] = []
    previous = None
    prior_date = None
    for raw_entry in label_entries:
        if not isinstance(raw_entry, Mapping):
            raise ValueError("ML label archive entry must be an object")
        day = str(raw_entry.get("signal_date") or "")
        if prior_date is not None and day <= prior_date:
            raise ValueError("ML label archive dates are not strictly increasing")
        previous = _verify_chain_entry(
            raw_entry,
            date_field="signal_date",
            expected_previous=previous,
            context="ML label archive",
        )
        feature_snapshot = snapshots_by_date.get(day)
        if feature_snapshot is None:
            raise ValueError("ML label archive references an unknown feature date")
        expected_path = root / "labels" / f"{day}.json"
        label_snapshot, label_sha = load_strict_json_with_sha256(expected_path)
        if label_sha != raw_entry.get("label_snapshot_sha256"):
            raise ValueError("ML mature label snapshot file SHA mismatch")
        feature_manifest = next(row for row in snapshot_manifest if row["as_of_date"] == day)
        if (
            label_snapshot.get("schema_version") != LABEL_SNAPSHOT_SCHEMA_VERSION
            or label_snapshot.get("mode") != MODE
            or label_snapshot.get("signal_date") != day
            or label_snapshot.get("feature_snapshot_sha256") != feature_manifest["sha256"]
            or raw_entry.get("feature_snapshot_sha256") != feature_manifest["sha256"]
            or label_snapshot.get("candidate_universe_sha256")
            != feature_snapshot.get("candidate_universe_sha256")
        ):
            raise ValueError("ML mature label snapshot identity mismatch")
        stock_rows = label_snapshot.get("stock_price_rows")
        sector_rows = label_snapshot.get("sector_price_rows")
        label_rows = label_snapshot.get("label_rows")
        calendar = label_snapshot.get("source_manifest", {}).get("trading_calendar")
        if (
            not isinstance(stock_rows, list)
            or not isinstance(sector_rows, list)
            or not isinstance(label_rows, list)
            or not isinstance(calendar, Mapping)
            or not isinstance(calendar.get("dates"), list)
        ):
            raise ValueError("ML mature label reconstruction inputs are missing")
        calendar_dates = list(calendar["dates"])
        try:
            signal_index = calendar_dates.index(day)
            target_5d = calendar_dates[signal_index + 5]
            label_as_of = date.fromisoformat(
                str(label_snapshot.get("label_as_of_date") or "")
            )
            captured_at = datetime.fromisoformat(
                str(label_snapshot.get("captured_at") or "")
            )
        except (ValueError, IndexError) as exc:
            raise ValueError("ML mature label PIT dates are invalid") from exc
        if captured_at.tzinfo is None or captured_at.utcoffset() is None:
            raise ValueError("ML mature label captured_at must be timezone-aware")
        if label_snapshot.get("target_5d") != target_5d:
            raise ValueError("ML mature label target_5d does not match the calendar")
        if label_as_of.isoformat() < target_5d:
            raise ValueError("ML mature label was captured before the 5-day target")
        if captured_at.date() < label_as_of:
            raise ValueError("ML mature label capture precedes its data as-of date")
        expected_label_strict = bool(feature_manifest["strict_pit_eligible"])
        if bool(label_snapshot.get("strict_pit_eligible")) != expected_label_strict:
            raise ValueError("ML mature label strict PIT identity mismatch")
        expected_label_status = (
            "prospective_labels_captured_after_maturity"
            if expected_label_strict
            else "historical_reconstruction_labels"
        )
        if label_snapshot.get("pit_evidence_status") != expected_label_status:
            raise ValueError("ML mature label PIT status mismatch")
        label_source = label_snapshot.get("source_manifest", {}).get("label_source")
        if not isinstance(label_source, Mapping):
            raise ValueError("ML mature label source identity is missing")
        if (
            str(label_source.get("adjustment") or "") != "qfq"
            or str(label_source.get("frequency") or "") != "1d"
            or str(label_source.get("query_end") or "")
            != label_snapshot.get("label_as_of_date")
            or not str(label_source.get("provider") or "")
        ):
            raise ValueError("ML mature label source contract mismatch")
        if dict(calendar) != dict(
            feature_snapshot.get("source_manifest", {}).get("trading_calendar") or {}
        ):
            raise ValueError("ML mature label calendar identity mismatch")
        _verify_source_file_if_addressable(label_source, context="mature label")
        rebuilt = build_forward_label_rows(
            stock_rows,
            sector_rows,
            trading_dates=calendar_dates,
        )
        expected_codes = {
            str(row.get("stock_code") or "")
            for row in feature_snapshot["baseline_rows"]
        }
        rebuilt = [
            row
            for row in rebuilt
            if row["as_of_date"] == day and row["stock_code"] in expected_codes
        ]
        rebuilt.sort(key=lambda row: row["stock_code"])
        if rebuilt != label_rows or label_snapshot.get("label_row_count") != len(rebuilt):
            raise ValueError("ML mature labels do not reproduce from archived prices")
        input_identity = {
            "signal_date": day,
            "label_as_of_date": label_snapshot.get("label_as_of_date"),
            "feature_snapshot_sha256": feature_manifest["sha256"],
            "label_source": label_snapshot.get("source_manifest", {}).get("label_source"),
            "trading_calendar": dict(calendar),
            "stock_price_rows": stock_rows,
            "sector_price_rows": sector_rows,
        }
        if label_snapshot.get("input_identity_sha256") != canonical_sha256(input_identity):
            raise ValueError("ML mature label input identity mismatch")
        labels_by_date[day] = label_snapshot
        label_manifest.append(
            {
                "signal_date": day,
                "path": str(expected_path),
                "sha256": label_sha,
                "entry_sha256": previous,
                "strict_pit_eligible": bool(label_snapshot.get("strict_pit_eligible")),
                "label_row_count": len(label_rows),
            }
        )
        prior_date = day
    if labels_index is not None and previous != labels_index.get("chain_head_sha256"):
        raise ValueError("ML label archive chain head mismatch")

    prospective_dates = {
        day
        for row in snapshot_manifest
        for day in [row["as_of_date"]]
        if row["strict_pit_eligible"] is True
    }
    strict_label_dates = {
        day
        for day, snapshot in labels_by_date.items()
        if snapshot.get("strict_pit_eligible") is True
    }
    verified_training_dates = sorted(prospective_dates & strict_label_dates)
    verified_training_rows = sum(
        int(labels_by_date[day]["label_row_count"])
        for day in verified_training_dates
    )
    core = {
        "schema_version": "ml-stock-pit-evidence-v1",
        "mode": MODE,
        "status": "verified",
        "verifier": "theme_sector_radar.ml.accumulation.verify_accumulation_archive",
        "archive_root": str(root),
        "daily_index": {
            "path": str(daily_index_path),
            "sha256": daily_index_sha,
            "chain_head_sha256": daily_index.get("chain_head_sha256"),
        },
        "labels_index": (
            {
                "path": str(labels_index_path),
                "sha256": labels_index_sha,
                "chain_head_sha256": labels_index.get("chain_head_sha256"),
            }
            if labels_index is not None
            else None
        ),
        "snapshots": snapshot_manifest,
        "labels": label_manifest,
        "verified_training_dates": verified_training_dates,
        "counts": {
            "candidate_snapshot_dates": len(snapshots_by_date),
            "prospective_candidate_snapshot_dates": len(prospective_dates),
            "mature_label_dates": len(labels_by_date),
            "strict_mature_label_dates": len(strict_label_dates),
            "verified_training_dates": len(verified_training_dates),
            "candidate_rows": sum(
                int(snapshot.get("candidate_count") or 0)
                for snapshot in snapshots_by_date.values()
            ),
            "verified_training_rows": verified_training_rows,
        },
        "minimum_60_dates_satisfied": len(verified_training_dates) >= 60,
        "strict_pit_eligible": len(verified_training_dates) >= 60,
        "historical_candidate_universe_versioned": bool(snapshots_by_date)
        and all(row["strict_pit_eligible"] for row in snapshot_manifest),
        "eligible_for_oos_claim": False,
        "promotion_allowed": False,
        "disclaimer": DISCLAIMER,
    }
    evidence = {**core, "evidence_sha256": canonical_sha256(core)}
    require_finite(evidence, context="ML PIT evidence")
    validate_no_executable_instructions(evidence, context="ML PIT evidence")
    return evidence


def load_verified_training_inputs(archive_root: Path | str) -> dict[str, Any]:
    """Load only dates that the archive verifier admits to strict training."""

    root = Path(archive_root).resolve()
    evidence = verify_accumulation_archive(root)
    training_dates = list(evidence["verified_training_dates"])
    feature_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []
    candidate_snapshots: list[dict[str, Any]] = []
    for snapshot_entry in evidence["snapshots"]:
        day = str(snapshot_entry["as_of_date"])
        snapshot, _snapshot_sha = load_strict_json_with_sha256(
            root / "snapshots" / f"{day}.json"
        )
        candidate_snapshots.append(
            {
                "as_of_date": day,
                "candidate_count": int(snapshot.get("candidate_count") or 0),
                "stock_count": int(snapshot.get("feature_row_count") or 0),
                "feature_buildable": int(snapshot.get("feature_row_count") or 0)
                == int(snapshot.get("candidate_count") or 0),
            }
        )
        if day not in training_dates:
            continue
        feature_rows.extend(list(snapshot["feature_rows"]))
        baseline_rows.extend(list(snapshot["baseline_rows"]))
        label_snapshot, _label_sha = load_strict_json_with_sha256(
            root / "labels" / f"{day}.json"
        )
        label_rows.extend(list(label_snapshot["label_rows"]))
    return {
        "evidence": evidence,
        "feature_rows": feature_rows,
        "label_rows": label_rows,
        "baseline_rows": baseline_rows,
        "candidate_snapshots": candidate_snapshots,
    }


def build_archive_readiness_report(
    archive_root: Path | str,
    *,
    sector_history_date_count: int = 0,
) -> dict[str, Any]:
    """Build the normal readiness contract directly from the verified archive."""

    from .readiness import build_data_readiness_report

    loaded = load_verified_training_inputs(archive_root)
    evidence = loaded["evidence"]
    label_dates_by_horizon = {"1d": set(), "3d": set(), "5d": set()}
    excess_dates_by_horizon = {"1d": set(), "3d": set(), "5d": set()}
    labeled_counts = {"1d": 0, "3d": 0, "5d": 0}
    candidate_counts = {"1d": 0, "3d": 0, "5d": 0}
    for day in evidence["verified_training_dates"]:
        snapshot, _ = load_strict_json_with_sha256(
            Path(archive_root).resolve() / "snapshots" / f"{day}.json"
        )
        labels, _ = load_strict_json_with_sha256(
            Path(archive_root).resolve() / "labels" / f"{day}.json"
        )
        label_rows = list(labels.get("label_rows") or [])
        candidate_count = len(snapshot.get("feature_rows") or [])
        for horizon in ("1d", "3d", "5d"):
            key = f"future_excess_return_{horizon}"
            candidate_counts[horizon] += candidate_count
            mature = sum(
                isinstance(row.get("labels"), Mapping)
                and row["labels"].get(key) is not None
                for row in label_rows
            )
            labeled_counts[horizon] += mature
            if mature:
                excess_dates_by_horizon[horizon].add(day)
                label_dates_by_horizon[horizon].add(day)
    return build_data_readiness_report(
        candidate_snapshots=loaded["candidate_snapshots"],
        forward_stock_return_dates_by_horizon={
            horizon: sorted(label_dates_by_horizon[horizon])
            for horizon in label_dates_by_horizon
        },
        forward_excess_label_dates_by_horizon={
            horizon: sorted(excess_dates_by_horizon[horizon])
            for horizon in excess_dates_by_horizon
        },
        forward_label_coverage_by_horizon={
            horizon: (
                labeled_counts[horizon] / candidate_counts[horizon]
                if candidate_counts[horizon]
                else 0.0
            )
            for horizon in labeled_counts
        },
        sector_history_date_count=sector_history_date_count,
        historical_candidate_universe_versioned=bool(
            evidence.get("historical_candidate_universe_versioned")
        ),
        source_manifest={
            "archive_root": str(Path(archive_root).resolve()),
            "pit_evidence_sha256": evidence["evidence_sha256"],
        },
        pit_evidence=evidence,
    )


def count_sector_history_dates(root: Path | str) -> int:
    """Count unique canonical dates in strict sector-history artifacts."""

    dates: set[str] = set()
    for path in sorted(Path(root).glob("*.json")):
        payload, _sha256 = load_strict_json_with_sha256(path)
        rows = payload.get("records") if isinstance(payload, Mapping) else None
        if not isinstance(rows, list):
            raise ValueError(f"sector history records are missing: {path}")
        for row in rows:
            if not isinstance(row, Mapping):
                raise ValueError(f"sector history row is invalid: {path}")
            value = row.get("date")
            if value is None:
                value = row.get("\u65e5\u671f")
            text = str(value or "")
            try:
                canonical = date.fromisoformat(text).isoformat()
            except ValueError as exc:
                raise ValueError(f"sector history date is invalid: {path}") from exc
            if canonical != text:
                raise ValueError(f"sector history date is non-canonical: {path}")
            dates.add(text)
    return len(dates)
