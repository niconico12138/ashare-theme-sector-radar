"""Tests for historical data availability audit."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from audit_historical_data_availability import (
    audit_availability,
    generate_markdown,
    _scan_dir_dates,
    _is_trading_day,
    _next_trading_date,
)


class TestDateUtils:
    def test_is_trading_day_weekday(self):
        assert _is_trading_day("2026-06-01") is True  # Monday

    def test_is_trading_day_sunday(self):
        assert _is_trading_day("2026-06-07") is False  # Sunday

    def test_next_trading_date(self):
        # 2026-06-06 is Friday, next should be 2026-06-08 (Monday)
        result = _next_trading_date("2026-06-06")
        assert result == "2026-06-08"

    def test_next_trading_date_skips_sunday(self):
        # 2026-06-07 is Sunday, next should be 2026-06-08
        result = _next_trading_date("2026-06-07")
        assert result == "2026-06-08"


class TestScanDirDates:
    def test_scans_dates(self, tmp_path):
        (tmp_path / "2026-06-01").mkdir()
        (tmp_path / "2026-06-02").mkdir()
        (tmp_path / "not-a-date").mkdir()
        dates = _scan_dir_dates(tmp_path)
        assert "2026-06-01" in dates
        assert "2026-06-02" in dates
        assert "not-a-date" not in dates

    def test_empty_dir(self, tmp_path):
        dates = _scan_dir_dates(tmp_path)
        assert len(dates) == 0

    def test_nonexistent_dir(self, tmp_path):
        dates = _scan_dir_dates(tmp_path / "nonexistent")
        assert len(dates) == 0


class TestAuditAvailability:
    def test_basic_audit(self):
        report = audit_availability("2026-06-01", "2026-06-05")
        assert "scan_range" in report
        assert "total_calendar_days" in report
        assert "classification" in report
        assert report["total_calendar_days"] == 5

    def test_classification_structure(self):
        report = audit_availability("2026-06-01", "2026-06-05")
        cls = report["classification"]
        assert "direct_verify" in cls
        assert "backfillable" in cls
        assert "needs_unified" in cls
        assert "needs_sector_inputs" in cls
        assert "missing_sector_scores" in cls
        assert "non_trading" in cls

    def test_known_dates_have_data(self):
        report = audit_availability("2026-06-01", "2026-06-05")
        # 2026-06-01 to 2026-06-05 should have sector_scores
        assert report["data_source_counts"]["sector_scores"] >= 5

    def test_non_trading_days_identified(self):
        report = audit_availability("2026-06-05", "2026-06-08")
        # 2026-06-07 is Sunday
        non_trading = report["classification"]["non_trading"]["dates"]
        assert "2026-06-07" in non_trading


class TestMarkdown:
    def test_contains_key_sections(self):
        report = audit_availability("2026-06-01", "2026-06-05")
        md = generate_markdown(report)
        assert "Summary" in md
        assert "Data Source Counts" in md
        assert "Date Classification" in md
        assert "Projection" in md


class TestOutputExists:
    def test_output_files_exist(self):
        path = Path("reports/selection_validation/data_availability/historical_data_availability.json")
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "classification" in data
        assert "projected_validatable" in data
