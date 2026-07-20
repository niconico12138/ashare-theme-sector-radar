from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from theme_sector_radar.ml.prospective_candidate_archive import (
    CAPTURE_REQUEST_SCHEMA_VERSION,
    RAW_FEATURE_NAMES,
    SOURCE_SCHEMA_VERSION,
    SOURCE_TYPES,
    build_prospective_archive_reports,
    capture_prospective_daily_snapshot,
    validate_prospective_report_artifacts,
    verify_prospective_archive,
    write_prospective_archive_reports,
)
from theme_sector_radar.reporting.strict_json import (
    load_strict_json,
    load_strict_json_with_sha256,
    write_strict_json_atomic,
)


AS_OF = "2026-07-16"
AVAILABLE_AT = "2026-07-16T16:30:00+08:00"
CALENDAR_DATES = [
    "2026-07-16",
    "2026-07-17",
    "2026-07-20",
    "2026-07-21",
    "2026-07-22",
    "2026-07-23",
]


@pytest.fixture
def capture_clock(monkeypatch):
    monkeypatch.setattr(
        "theme_sector_radar.ml.prospective_candidate_archive._capture_now",
        lambda: datetime(
            2026, 7, 16, 18, 0, tzinfo=timezone(timedelta(hours=8))
        ),
    )


def _candidate_records():
    return [
        {"stock_code": "000001", "sector_name": "sector-a"},
        {"stock_code": "000002", "sector_name": "sector-a"},
    ]


def _factor_records(*, missing: bool = False):
    records = []
    for code in ("000001", "000002"):
        features = {
            name: float(index + 1) / 100.0
            for index, name in enumerate(RAW_FEATURE_NAMES)
        }
        max_dates = {name: AS_OF for name in RAW_FEATURE_NAMES}
        if missing and code == "000002":
            features["sector_support_score"] = None
            max_dates.pop("sector_support_score")
        records.append(
            {
                "stock_code": code,
                "sector_name": "sector-a",
                "features": features,
                "feature_max_dates": max_dates,
            }
        )
    return records


def _records_by_source(source_type: str, *, missing_feature: bool = False):
    if source_type == "candidate_pool":
        return _candidate_records()
    if source_type == "factor_snapshot":
        return _factor_records(missing=missing_feature)
    if source_type in {"bars_1m_identity", "bars_1d_identity"}:
        frequency = "1m" if source_type == "bars_1m_identity" else "1d"
        return [
            {
                "stock_code": code,
                "as_of_date": AS_OF,
                "available_at": AVAILABLE_AT,
                "frequency": frequency,
                "first_date": AS_OF,
                "last_date": AS_OF,
                "bar_count": 240 if frequency == "1m" else 120,
                "content_sha256": ("a" if code == "000001" else "b") * 64,
            }
            for code in ("000001", "000002")
        ]
    if source_type == "sector_membership":
        return [
            {
                "stock_code": code,
                "sector_name": "sector-a",
                "effective_date": AS_OF,
            }
            for code in ("000001", "000002")
        ]
    if source_type == "direction_inputs":
        return [{"sector_name": "sector-a", "raw_inputs": {"breadth": 0.6}}]
    if source_type == "linkage_v2_inputs":
        return [
            {
                "stock_code": code,
                "sector_name": "sector-a",
                "raw_inputs": {"stock_return_5d": 0.01, "sector_return_5d": 0.005},
            }
            for code in ("000001", "000002")
        ]
    if source_type == "trading_calendar":
        return [{"date": day, "is_trading_day": True} for day in CALENDAR_DATES]
    if source_type == "calculation_contract":
        return [
            {"component": "raw_feature_builder", "version": "prospective-v1"},
            {"component": "direction", "version": "direction-input-v1"},
            {"component": "linkage_v2", "version": "linkage-input-v1"},
        ]
    raise AssertionError(source_type)


def _write_source(
    root: Path,
    source_type: str,
    *,
    records=None,
    as_of_date: str = AS_OF,
    suffix: str = "",
):
    payload = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "source_type": source_type,
        "as_of_date": as_of_date,
        "available_at": AVAILABLE_AT,
        "source_version": f"{source_type}-v1",
        "records": _records_by_source(source_type) if records is None else records,
    }
    path = root / "sources" / f"{source_type}{suffix}.json"
    write_strict_json_atomic(path, payload)
    _loaded, sha256 = load_strict_json_with_sha256(path)
    return {
        "status": "observed",
        "as_of_date": as_of_date,
        "available_at": AVAILABLE_AT,
        "path": str(path.resolve()),
        "sha256": sha256,
        "source_version": f"{source_type}-v1",
    }


def _request(
    root: Path,
    *,
    missing_feature: bool = False,
    unknown_direction: bool = False,
    unknown_linkage: bool = False,
):
    sources = {}
    for source_type in SOURCE_TYPES:
        if source_type in {"stock_event_adjustment", "stock_event_features"}:
            sources[source_type] = {
                "status": "unknown",
                "as_of_date": AS_OF,
                "reason": "stock event adjustment is disabled pending approved manifest",
            }
            continue
        if source_type == "direction_inputs" and unknown_direction:
            sources[source_type] = {
                "status": "unknown",
                "as_of_date": AS_OF,
                "reason": "daily direction input was not available at capture time",
            }
            continue
        if source_type == "linkage_v2_inputs" and unknown_linkage:
            sources[source_type] = {
                "status": "blocked",
                "as_of_date": AS_OF,
                "reason": "dated Linkage V2 input manifest was incomplete",
            }
            continue
        records = (
            _factor_records(missing=True)
            if source_type == "factor_snapshot" and missing_feature
            else None
        )
        sources[source_type] = _write_source(root, source_type, records=records)
    return {
        "schema_version": CAPTURE_REQUEST_SCHEMA_VERSION,
        "as_of_date": AS_OF,
        "sources": sources,
    }


def test_daily_raw_snapshot_is_immutable_and_emits_schema_a_b(tmp_path, capture_clock):
    request = _request(tmp_path, missing_feature=True)
    archive = tmp_path / "archive"

    created = capture_prospective_daily_snapshot(
        archive_root=archive, request=request
    )
    repeated = capture_prospective_daily_snapshot(
        archive_root=archive, request=request
    )

    assert created["created"] is True
    assert repeated["created"] is False
    assert created["manifest_sha256"] == repeated["manifest_sha256"]
    day_root = archive / "daily" / AS_OF
    schema_a = load_strict_json(day_root / "schema_a.json")
    schema_b = load_strict_json(day_root / "schema_b.json")
    missing_a = next(row for row in schema_a["rows"] if row["stock_code"] == "000002")
    missing_b = next(
        row
        for row in schema_b["rows"]
        if row["stock_code"] == "000002"
        and row["feature_name"] == "sector_support_score"
    )
    assert missing_a["features"]["sector_support_score"] is None
    assert missing_a["missing_indicators"]["sector_support_score"] is True
    assert missing_b["value"] is None
    assert missing_b["missing"] is True
    assert schema_b["row_count"] == 2 * len(RAW_FEATURE_NAMES)
    assert created["manifest"]["prospective_pit_eligible"] is True
    assert verify_prospective_archive(archive)["entry_count"] == 1


def test_direction_and_linkage_missing_remain_explicit_and_block_readiness(
    tmp_path, capture_clock
):
    request = _request(
        tmp_path, unknown_direction=True, unknown_linkage=True
    )
    archive = tmp_path / "archive"
    captured = capture_prospective_daily_snapshot(
        archive_root=archive, request=request
    )
    snapshot = load_strict_json(archive / "daily" / AS_OF / "snapshot.json")

    assert captured["manifest"]["data_quality_status"] == "partial"
    assert captured["manifest"]["prospective_pit_eligible"] is False
    assert snapshot["source_manifest"]["direction_inputs"] == {
        "source_type": "direction_inputs",
        "status": "unknown",
        "as_of_date": AS_OF,
        "available_at": None,
        "path": None,
        "sha256": None,
        "source_version": None,
        "reason": "daily direction input was not available at capture time",
    }
    assert "direction_inputs" not in snapshot["source_payloads"]
    reports = build_prospective_archive_reports(
        archive, report_as_of_date="2026-07-17"
    )
    assert reports["readiness_report"]["future_comparison_ready"] is False
    assert reports["data_quality_status"]["direction_missing_dates"] == 1
    assert reports["data_quality_status"]["linkage_v2_missing_dates"] == 1
    assert reports["label_maturity_queue"]["queue"][0]["status"] == "pending_label_maturity"


def test_unreviewed_event_is_rejected_before_event_payload_is_read(
    tmp_path, capture_clock
):
    request = _request(tmp_path)
    adjustment_path = tmp_path / "sources" / "stock_event_adjustment_pending.json"
    write_strict_json_atomic(
        adjustment_path,
        {
            "schema_version": SOURCE_SCHEMA_VERSION,
            "source_type": "stock_event_adjustment",
            "as_of_date": AS_OF,
            "available_at": AVAILABLE_AT,
            "source_version": "stock_event_adjustment-v1",
            "adjustment_manifest": {
                "review_status": "pending",
                "manifest_sha256": "a" * 64,
                "enabled": False,
            },
            "records": [],
        },
    )
    _loaded, adjustment_sha = load_strict_json_with_sha256(adjustment_path)
    request["sources"]["stock_event_adjustment"] = {
        "status": "observed",
        "as_of_date": AS_OF,
        "available_at": AVAILABLE_AT,
        "path": str(adjustment_path.resolve()),
        "sha256": adjustment_sha,
        "source_version": "stock_event_adjustment-v1",
    }
    request["sources"]["stock_event_features"] = {
        "status": "observed",
        "as_of_date": AS_OF,
        "available_at": AVAILABLE_AT,
        "path": str((tmp_path / "does-not-exist.json").resolve()),
        "sha256": "b" * 64,
        "source_version": "stock_event_features-v1",
    }
    with pytest.raises(ValueError, match="unreviewed stock_event_adjustment"):
        capture_prospective_daily_snapshot(
            archive_root=tmp_path / "archive", request=request
        )


def test_approved_disabled_event_features_are_archived_as_raw_schema_rows(
    tmp_path, capture_clock
):
    request = _request(tmp_path)
    adjustment_path = tmp_path / "sources" / "stock_event_adjustment_approved.json"
    write_strict_json_atomic(
        adjustment_path,
        {
            "schema_version": SOURCE_SCHEMA_VERSION,
            "source_type": "stock_event_adjustment",
            "as_of_date": AS_OF,
            "available_at": AVAILABLE_AT,
            "source_version": "stock_event_adjustment-v1",
            "adjustment_manifest": {
                "review_status": "approved",
                "manifest_sha256": "a" * 64,
                "enabled": False,
            },
            "records": [],
        },
    )
    _loaded, adjustment_sha = load_strict_json_with_sha256(adjustment_path)
    request["sources"]["stock_event_adjustment"] = {
        "status": "observed",
        "as_of_date": AS_OF,
        "available_at": AVAILABLE_AT,
        "path": str(adjustment_path.resolve()),
        "sha256": adjustment_sha,
        "source_version": "stock_event_adjustment-v1",
    }
    event_path = tmp_path / "sources" / "stock_event_features_approved.json"
    write_strict_json_atomic(
        event_path,
        {
            "schema_version": SOURCE_SCHEMA_VERSION,
            "source_type": "stock_event_features",
            "as_of_date": AS_OF,
            "available_at": AVAILABLE_AT,
            "source_version": "stock_event_features-v1",
            "records": [
                {
                    "stock_code": code,
                    "sector_name": "sector-a",
                    "features": {"event_count_5d": 1.0, "event_severity_1d": None},
                    "feature_max_dates": {"event_count_5d": AS_OF},
                }
                for code in ("000001", "000002")
            ],
        },
    )
    _loaded, event_sha = load_strict_json_with_sha256(event_path)
    request["sources"]["stock_event_features"] = {
        "status": "observed",
        "as_of_date": AS_OF,
        "available_at": AVAILABLE_AT,
        "path": str(event_path.resolve()),
        "sha256": event_sha,
        "source_version": "stock_event_features-v1",
    }
    captured = capture_prospective_daily_snapshot(
        archive_root=tmp_path / "archive", request=request
    )
    schema_a = load_strict_json(tmp_path / "archive" / "daily" / AS_OF / "schema_a.json")
    schema_b = load_strict_json(tmp_path / "archive" / "daily" / AS_OF / "schema_b.json")
    assert captured["manifest"]["prospective_pit_eligible"] is True
    assert schema_a["event_feature_names"] == ["event_count_5d", "event_severity_1d"]
    assert next(row for row in schema_a["rows"] if row["stock_code"] == "000001")[
        "event_missing_indicators"
    ]["event_severity_1d"] is True
    assert sum(row["feature_family"] == "stock_event" for row in schema_b["rows"]) == 4


def test_same_day_revision_and_source_mutation_are_rejected(tmp_path, capture_clock):
    request = _request(tmp_path)
    archive = tmp_path / "archive"
    capture_prospective_daily_snapshot(archive_root=archive, request=request)

    revised_records = _factor_records()
    revised_records[0]["features"]["ma20_slope_5"] = 9.9
    revised = dict(request)
    revised["sources"] = dict(request["sources"])
    revised["sources"]["factor_snapshot"] = _write_source(
        tmp_path,
        "factor_snapshot",
        records=revised_records,
        suffix="_revision",
    )
    with pytest.raises(ValueError, match="immutable daily snapshot revision rejected"):
        capture_prospective_daily_snapshot(archive_root=archive, request=revised)

    candidate_path = Path(request["sources"]["candidate_pool"]["path"])
    payload = load_strict_json(candidate_path)
    payload["records"][0]["sector_name"] = "revised-sector"
    write_strict_json_atomic(candidate_path, payload)
    with pytest.raises(ValueError, match="source changed after capture"):
        verify_prospective_archive(archive)


def test_future_feature_and_current_membership_as_history_are_rejected(
    tmp_path, capture_clock
):
    future_request = _request(tmp_path / "future")
    future_records = _factor_records()
    future_records[0]["feature_max_dates"]["ma20_slope_5"] = "2026-07-17"
    future_request["sources"]["factor_snapshot"] = _write_source(
        tmp_path / "future",
        "factor_snapshot",
        records=future_records,
        suffix="_future",
    )
    with pytest.raises(ValueError, match="future feature_max_date rejected"):
        capture_prospective_daily_snapshot(
            archive_root=tmp_path / "future_archive", request=future_request
        )

    membership_request = _request(tmp_path / "membership")
    membership_request["sources"]["sector_membership"] = _write_source(
        tmp_path / "membership",
        "sector_membership",
        as_of_date="2026-07-17",
        suffix="_current",
    )
    with pytest.raises(ValueError, match="sector_membership source identity mismatch"):
        capture_prospective_daily_snapshot(
            archive_root=tmp_path / "membership_archive", request=membership_request
        )


@pytest.mark.parametrize(
    "source_type",
    ["factor_snapshot", "bars_1m_identity", "bars_1d_identity"],
)
def test_candidate_coverage_mismatch_is_rejected(tmp_path, capture_clock, source_type):
    request = _request(tmp_path)
    records = _records_by_source(source_type)[:1]
    request["sources"][source_type] = _write_source(
        tmp_path,
        source_type,
        records=records,
        suffix="_incomplete",
    )
    with pytest.raises(ValueError, match="candidate coverage mismatch"):
        capture_prospective_daily_snapshot(
            archive_root=tmp_path / "archive", request=request
        )


@pytest.mark.parametrize("protected_field", ["quant_score", "final_score", "selection_score"])
def test_protected_fields_are_rejected(tmp_path, capture_clock, protected_field):
    request = _request(tmp_path)
    records = _candidate_records()
    records[0][protected_field] = 88.0
    request["sources"]["candidate_pool"] = _write_source(
        tmp_path,
        "candidate_pool",
        records=records,
        suffix=f"_{protected_field}",
    )
    with pytest.raises(ValueError, match="protected or future field rejected"):
        capture_prospective_daily_snapshot(
            archive_root=tmp_path / "archive", request=request
        )


def test_duplicate_candidate_and_backfill_are_rejected(tmp_path, capture_clock, monkeypatch):
    request = _request(tmp_path / "duplicate")
    request["sources"]["candidate_pool"] = _write_source(
        tmp_path / "duplicate",
        "candidate_pool",
        records=[_candidate_records()[0], _candidate_records()[0]],
        suffix="_duplicate",
    )
    with pytest.raises(ValueError, match="duplicate candidate pool stock identity"):
        capture_prospective_daily_snapshot(
            archive_root=tmp_path / "duplicate_archive", request=request
        )

    old_request = _request(tmp_path / "backfill")
    monkeypatch.setattr(
        "theme_sector_radar.ml.prospective_candidate_archive._capture_now",
        lambda: datetime(
            2026, 7, 17, 18, 0, tzinfo=timezone(timedelta(hours=8))
        ),
    )
    with pytest.raises(ValueError, match="backfill is forbidden"):
        capture_prospective_daily_snapshot(
            archive_root=tmp_path / "backfill_archive", request=old_request
        )


def test_empty_archive_reports_wait_for_first_new_trading_day(tmp_path):
    reports = build_prospective_archive_reports(
        tmp_path / "archive", report_as_of_date="2026-07-20"
    )

    assert reports["daily_snapshot_manifest"]["entry_count"] == 0
    assert reports["coverage_report"]["candidate_rows"] == 0
    assert reports["readiness_report"]["status"] == "blocked"
    assert reports["readiness_report"]["future_comparison_ready"] is False
    assert reports["data_quality_status"]["status"] == "awaiting_first_new_trading_day"

    output_root = tmp_path / "reports"
    write_prospective_archive_reports(
        tmp_path / "archive",
        output_root,
        report_as_of_date="2026-07-20",
    )
    validated = validate_prospective_report_artifacts(
        tmp_path / "archive",
        output_root,
        report_as_of_date="2026-07-20",
    )
    assert validated["snapshot_dates"] == 0
    assert validated["future_comparison_ready"] is False
