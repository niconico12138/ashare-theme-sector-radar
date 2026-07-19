import hashlib
import json
from pathlib import Path

import pytest

from scripts.build_a_share_trading_calendar import build_a_share_trading_calendar
from theme_sector_radar.data import trading_calendar as trading_calendar_module
from theme_sector_radar.data.trading_calendar import (
    build_trading_calendar_report,
    load_trading_calendar,
    next_trading_date,
    validate_trading_calendar_identity,
)


def test_trading_calendar_artifact_validation_rejects_bad_declared_count(tmp_path):
    report = build_trading_calendar_report(
        ["2026-07-01", "2026-07-02"],
        source="unit-exchange-calendar",
        requested_start="2026-07-01",
        requested_end="2026-07-02",
    )
    report["date_count"] = 99

    with pytest.raises(ValueError, match="date_count"):
        trading_calendar_module.validate_trading_calendar_artifact(
            report,
            path=tmp_path / "calendar.json",
            sha256="a" * 64,
            as_of="2026-07-02",
        )


def test_trading_calendar_is_independent_of_candidate_labels(tmp_path):
    report = build_trading_calendar_report(
        ["2026-07-03", "2026-07-01", "2026-07-02", "2026-07-02"],
        source="unit-exchange-calendar",
        requested_start="2026-07-01",
        requested_end="2026-07-03",
    )
    path = tmp_path / "calendar.json"
    path.write_text(json.dumps(report), encoding="utf-8")

    loaded = load_trading_calendar(path, as_of="2026-07-03")

    assert loaded["dates"] == ["2026-07-01", "2026-07-02", "2026-07-03"]
    assert loaded["source"] == "unit-exchange-calendar"
    assert loaded["sha256"]
    assert next_trading_date(loaded["dates"], "2026-07-01", as_of="2026-07-03") == "2026-07-02"


def test_trading_calendar_rejects_weekends_and_incomplete_as_of_coverage(tmp_path):
    with pytest.raises(ValueError, match="weekend"):
        build_trading_calendar_report(
            ["2026-07-04"],
            source="unit",
            requested_start="2026-07-04",
            requested_end="2026-07-04",
        )

    path = tmp_path / "calendar.json"
    path.write_text(
        json.dumps(
            build_trading_calendar_report(
                ["2026-07-01", "2026-07-02"],
                source="unit",
                requested_start="2026-07-01",
                requested_end="2026-07-02",
            )
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="coverage"):
        load_trading_calendar(path, as_of="2026-07-03")


def test_trading_calendar_rejects_declared_date_count_mismatch(tmp_path):
    report = build_trading_calendar_report(
        ["2026-07-01", "2026-07-02"],
        source="unit",
        requested_start="2026-07-01",
        requested_end="2026-07-03",
    )
    report["date_count"] = 99
    path = tmp_path / "calendar.json"
    path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ValueError, match="date_count"):
        load_trading_calendar(path, as_of="2026-07-03")


def test_trading_calendar_rejects_duplicate_dates_hidden_by_unique_count(tmp_path):
    report = build_trading_calendar_report(
        ["2026-07-01", "2026-07-02"],
        source="unit",
        requested_start="2026-07-01",
        requested_end="2026-07-03",
    )
    report["dates"] = ["2026-07-01", "2026-07-01", "2026-07-02"]
    path = tmp_path / "calendar.json"
    path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        load_trading_calendar(path, as_of="2026-07-03")


def test_trading_calendar_rejects_noncanonical_iso_date_literal(tmp_path):
    report = build_trading_calendar_report(
        ["2026-07-01", "2026-07-02"],
        source="unit",
        requested_start="2026-07-01",
        requested_end="2026-07-03",
    )
    report["dates"][0] = "20260701"
    path = tmp_path / "calendar.json"
    path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ValueError, match="canonical ISO date"):
        load_trading_calendar(path, as_of="2026-07-03")


def test_trading_calendar_builder_rejects_noncanonical_requested_range():
    with pytest.raises(ValueError, match="canonical ISO date"):
        build_trading_calendar_report(
            ["2026-07-01", "2026-07-02"],
            source="unit",
            requested_start="20260701",
            requested_end="20260702",
        )


def test_top_level_calendar_builder_rejects_suffixed_trade_date(tmp_path):
    output_path = tmp_path / "calendar.json"

    with pytest.raises(ValueError, match="canonical ISO date"):
        build_a_share_trading_calendar(
            output_path=output_path,
            start="2026-07-01",
            end="2026-07-03",
            trade_dates=["2026-07-01evil"],
        )

    assert not output_path.exists()


def test_trading_calendar_rejects_dates_outside_declared_range(tmp_path):
    report = {
        "schema_version": "a_share_trading_calendar.v1",
        "market": "CN_A",
        "source": "unit",
        "requested_start": "2026-07-02",
        "requested_end": "2026-07-03",
        "dates": ["2026-07-01", "2026-07-02", "2026-07-03"],
        "date_count": 3,
    }
    path = tmp_path / "calendar.json"
    path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(ValueError, match="requested range"):
        load_trading_calendar(path, as_of="2026-07-03")


def test_trading_calendar_sha_binds_the_bytes_used_for_dates(tmp_path, monkeypatch):
    report = build_trading_calendar_report(
        ["2026-07-01", "2026-07-02"],
        source="unit",
        requested_start="2026-07-01",
        requested_end="2026-07-03",
    )
    path = tmp_path / "calendar.json"
    first_bytes = json.dumps(report).encode("utf-8")
    path.write_bytes(first_bytes)
    original_read_bytes = Path.read_bytes

    def read_then_replace(self):
        payload = original_read_bytes(self)
        self.write_text("{}", encoding="utf-8")
        return payload

    monkeypatch.setattr(Path, "read_bytes", read_then_replace)

    loaded = load_trading_calendar(path, as_of="2026-07-02")

    assert loaded["dates"] == ["2026-07-01", "2026-07-02"]
    assert loaded["sha256"] == hashlib.sha256(first_bytes).hexdigest()


def test_records_calendar_identity_must_match_caller_calendar(tmp_path):
    report = build_trading_calendar_report(
        ["2026-07-01", "2026-07-02"],
        source="unit",
        requested_start="2026-07-01",
        requested_end="2026-07-03",
    )
    path = tmp_path / "calendar.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    current = load_trading_calendar(path, as_of="2026-07-02")
    recorded = dict(current)
    recorded["sha256"] = "a" * 64

    with pytest.raises(ValueError, match="calendar sha256 mismatch"):
        validate_trading_calendar_identity(recorded, current, context="entry records")
