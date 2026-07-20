"""Strict adapters for isolated ML feature and label source documents."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from theme_sector_radar.data.trading_calendar import (
    validate_trading_calendar_identity,
)
from theme_sector_radar.reporting.paper_only_contract import (
    validate_no_executable_instructions,
)
from theme_sector_radar.reporting.strict_json import load_strict_json_with_sha256

from .contract import canonical_sha256
from .feature_builder import build_feature_row
from .label_builder import build_forward_label_rows
from .schema import MODE


FEATURE_SOURCE_SCHEMA_VERSION = "ml-stock-feature-source-v1"
LABEL_SOURCE_SCHEMA_VERSION = "ml-stock-label-source-v1"


def _validate_source_contract(
    source: Mapping[str, Any],
    *,
    kind: str,
    allow_fixture: bool,
    source_identity: Mapping[str, Any] | None,
) -> Mapping[str, Any] | None:
    fixture_only = source.get("fixture_only")
    strict_pit = source.get("strict_pit_eligible")
    if fixture_only is True:
        if not allow_fixture or strict_pit is not False:
            raise ValueError(f"ML {kind} source fixture opt-in is required")
        return None
    if fixture_only is not False or strict_pit is not True:
        raise ValueError(f"ML {kind} source PIT safety envelope is missing")
    identity = source_identity
    if not isinstance(identity, Mapping):
        raise ValueError(f"ML {kind} source physical identity is required")
    path = Path(str(identity.get("path") or ""))
    expected_sha = str(identity.get("sha256") or "").lower()
    if not path.is_absolute() or not path.is_file() or len(expected_sha) != 64:
        raise ValueError(f"ML {kind} source physical identity is invalid")
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        raise ValueError(f"ML {kind} source physical identity changed")
    manifest = source.get("source_manifest")
    if not isinstance(manifest, Mapping):
        raise ValueError(f"ML {kind} source PIT manifest is missing")
    archive_root = Path(str(manifest.get("archive_root") or ""))
    evidence_sha = str(manifest.get("pit_evidence_sha256") or "").lower()
    if not archive_root.is_absolute() or len(evidence_sha) != 64:
        raise ValueError(f"ML {kind} source PIT manifest is invalid")
    from .accumulation import verify_accumulation_archive

    evidence = verify_accumulation_archive(archive_root)
    if evidence.get("evidence_sha256") != evidence_sha:
        raise ValueError(f"ML {kind} source PIT evidence SHA mismatch")
    if evidence.get("strict_pit_eligible") is not True:
        raise ValueError(f"ML {kind} source PIT evidence is not strict")
    return evidence


def _require_verified_feature_snapshots(
    source_snapshots: Any,
    *,
    evidence: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    if not isinstance(source_snapshots, list):
        raise ValueError("ML feature source snapshots are missing")
    archive_root = Path(str(evidence.get("archive_root") or "")).resolve()
    evidence_snapshots = evidence.get("snapshots")
    if not isinstance(evidence_snapshots, list):
        raise ValueError("ML feature source verified archive snapshots are missing")
    expected: list[dict[str, Any]] = []
    for raw_entry in evidence_snapshots:
        if not isinstance(raw_entry, Mapping):
            raise ValueError("ML feature source archive snapshot entry is invalid")
        day = str(raw_entry.get("as_of_date") or "")
        expected_path = (archive_root / "snapshots" / f"{day}.json").resolve()
        recorded_path = Path(str(raw_entry.get("path") or "")).resolve()
        if recorded_path != expected_path:
            raise ValueError("ML feature source verified archive path mismatch")
        snapshot, snapshot_sha = load_strict_json_with_sha256(expected_path)
        if snapshot_sha != raw_entry.get("sha256"):
            raise ValueError("ML feature source verified archive SHA mismatch")
        if raw_entry.get("strict_pit_eligible") is not True:
            raise ValueError("ML feature source archive snapshot is not strict")
        if (
            not isinstance(snapshot, Mapping)
            or snapshot.get("as_of_date") != day
            or not isinstance(snapshot.get("feature_candidates"), list)
            or not isinstance(snapshot.get("bars_by_code"), Mapping)
        ):
            raise ValueError("ML feature source verified archive content is invalid")
        expected.append(
            {
                "as_of_date": day,
                "candidates": snapshot["feature_candidates"],
                "bars_by_code": snapshot["bars_by_code"],
            }
        )
    if source_snapshots != expected:
        raise ValueError("ML feature source does not match the verified archive")
    return source_snapshots


def _require_verified_label_rows(
    source: Mapping[str, Any], *, evidence: Mapping[str, Any]
) -> None:
    archive_root = Path(str(evidence.get("archive_root") or "")).resolve()
    evidence_labels = evidence.get("labels")
    if not isinstance(evidence_labels, list):
        raise ValueError("ML label source verified archive labels are missing")
    stock_by_identity: dict[tuple[str, str], Mapping[str, Any]] = {}
    sector_by_identity: dict[tuple[str, str], Mapping[str, Any]] = {}
    expected_calendar: Mapping[str, Any] | None = None
    for raw_entry in evidence_labels:
        if not isinstance(raw_entry, Mapping):
            raise ValueError("ML label source archive label entry is invalid")
        day = str(raw_entry.get("signal_date") or "")
        expected_path = (archive_root / "labels" / f"{day}.json").resolve()
        recorded_path = Path(str(raw_entry.get("path") or "")).resolve()
        if recorded_path != expected_path:
            raise ValueError("ML label source verified archive path mismatch")
        snapshot, snapshot_sha = load_strict_json_with_sha256(expected_path)
        if snapshot_sha != raw_entry.get("sha256"):
            raise ValueError("ML label source verified archive SHA mismatch")
        if not isinstance(snapshot, Mapping):
            raise ValueError("ML label source verified archive content is invalid")
        stock_rows = snapshot.get("stock_price_rows")
        sector_rows = snapshot.get("sector_price_rows")
        calendar = (snapshot.get("source_manifest") or {}).get("trading_calendar")
        if (
            not isinstance(stock_rows, list)
            or not isinstance(sector_rows, list)
            or not isinstance(calendar, Mapping)
        ):
            raise ValueError("ML label source verified archive rows are missing")
        if expected_calendar is None:
            expected_calendar = calendar
        elif canonical_sha256(dict(calendar)) != canonical_sha256(dict(expected_calendar)):
            raise ValueError("ML label source verified archive calendar mismatch")
        for row in stock_rows:
            if not isinstance(row, Mapping):
                raise ValueError("ML label source archived stock row is invalid")
            identity = (str(row.get("stock_code") or ""), str(row.get("date") or ""))
            stock_by_identity[identity] = row
        for row in sector_rows:
            if not isinstance(row, Mapping):
                raise ValueError("ML label source archived sector row is invalid")
            identity = (str(row.get("sector_name") or ""), str(row.get("date") or ""))
            sector_by_identity[identity] = row
    source_stock = source.get("stock_price_rows")
    source_sector = source.get("sector_price_rows")
    if not isinstance(source_stock, list) or not isinstance(source_sector, list):
        raise ValueError("ML label source price rows are missing")
    expected_stock = sorted(stock_by_identity.values(), key=lambda row: (
        str(row.get("stock_code") or ""), str(row.get("date") or "")
    ))
    expected_sector = sorted(sector_by_identity.values(), key=lambda row: (
        str(row.get("sector_name") or ""), str(row.get("date") or "")
    ))
    actual_stock = sorted(source_stock, key=lambda row: (
        str(row.get("stock_code") or ""), str(row.get("date") or "")
    ))
    actual_sector = sorted(source_sector, key=lambda row: (
        str(row.get("sector_name") or ""), str(row.get("date") or "")
    ))
    if canonical_sha256(actual_stock) != canonical_sha256(expected_stock):
        raise ValueError("ML label source does not match the verified archive stock rows")
    if canonical_sha256(actual_sector) != canonical_sha256(expected_sector):
        raise ValueError("ML label source does not match the verified archive sector rows")
    recorded_calendar = source.get("trading_calendar")
    if not isinstance(recorded_calendar, Mapping) or expected_calendar is None:
        raise ValueError("ML label source verified archive calendar is missing")
    for key in ("schema_version", "market", "dates"):
        if recorded_calendar.get(key) != expected_calendar.get(key):
            raise ValueError("ML label source does not match the verified archive calendar")


def build_feature_rows_from_source(
    source: Mapping[str, Any],
    *,
    as_of_date: str | None = None,
    allow_fixture: bool = False,
    source_identity: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if source.get("schema_version") != FEATURE_SOURCE_SCHEMA_VERSION:
        raise ValueError("ML feature source schema mismatch")
    if source.get("mode") != MODE:
        raise ValueError("ML feature source must be paper/shadow only")
    evidence = _validate_source_contract(
        source,
        kind="feature",
        allow_fixture=allow_fixture,
        source_identity=source_identity,
    )
    validate_no_executable_instructions(source, context="ML feature source")
    snapshots = source.get("snapshots")
    if evidence is not None:
        snapshots = _require_verified_feature_snapshots(
            snapshots,
            evidence=evidence,
        )
    elif not isinstance(snapshots, list):
        raise ValueError("ML feature source snapshots are missing")
    rows: list[dict[str, Any]] = []
    seen_dates: set[str] = set()
    for snapshot in snapshots:
        if not isinstance(snapshot, Mapping):
            raise ValueError("ML feature snapshot must be an object")
        day = str(snapshot.get("as_of_date") or "")
        if as_of_date is not None and day != as_of_date:
            continue
        if day in seen_dates:
            raise ValueError(f"duplicate ML feature snapshot date: {day}")
        seen_dates.add(day)
        candidates = snapshot.get("candidates")
        bars_by_code = snapshot.get("bars_by_code")
        if not isinstance(candidates, list) or not isinstance(bars_by_code, Mapping):
            raise ValueError(f"ML feature snapshot inputs are incomplete: {day}")
        seen_codes: set[str] = set()
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                raise ValueError("ML feature candidate must be an object")
            code = str(candidate.get("code") or candidate.get("stock_code") or "").zfill(6)
            if code in seen_codes:
                raise ValueError(f"duplicate ML feature candidate: {day} {code}")
            seen_codes.add(code)
            bars = bars_by_code.get(code)
            if not isinstance(bars, Sequence) or isinstance(bars, (str, bytes)):
                raise ValueError(f"ML feature bars are missing: {day} {code}")
            rows.append(build_feature_row(candidate, bars, as_of_date=day))
    if as_of_date is not None and not rows:
        raise ValueError(f"ML feature source has no snapshot for {as_of_date}")
    return rows


def build_label_rows_from_source(
    source: Mapping[str, Any],
    *,
    trading_calendar: Mapping[str, Any] | None = None,
    allow_fixture: bool = False,
    source_identity: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if source.get("schema_version") != LABEL_SOURCE_SCHEMA_VERSION:
        raise ValueError("ML label source schema mismatch")
    if source.get("mode") != MODE:
        raise ValueError("ML label source must be paper/shadow only")
    evidence = _validate_source_contract(
        source,
        kind="label",
        allow_fixture=allow_fixture,
        source_identity=source_identity,
    )
    validate_no_executable_instructions(source, context="ML label source")
    if evidence is not None:
        _require_verified_label_rows(source, evidence=evidence)
    stock_rows = source.get("stock_price_rows")
    sector_rows = source.get("sector_price_rows")
    recorded_calendar = source.get("trading_calendar")
    if trading_calendar is not None:
        try:
            validate_trading_calendar_identity(
                recorded_calendar,
                trading_calendar,
                context="ML label source",
            )
        except ValueError as exc:
            raise ValueError(f"calendar identity mismatch: {exc}") from exc
        trading_dates = trading_calendar.get("dates")
    else:
        trading_dates = source.get("trading_dates")
        if not isinstance(trading_dates, list) and isinstance(
            recorded_calendar, Mapping
        ):
            trading_dates = recorded_calendar.get("dates")
    if (
        not isinstance(stock_rows, list)
        or not isinstance(sector_rows, list)
        or not isinstance(trading_dates, list)
    ):
        raise ValueError("ML label price sources are missing")
    return build_forward_label_rows(
        stock_rows,
        sector_rows,
        trading_dates=trading_dates,
    )
