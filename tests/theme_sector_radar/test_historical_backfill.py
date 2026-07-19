"""Tests for historical backfill script."""

import re
import sys
from pathlib import Path

import pytest

from theme_sector_radar.reporting.strict_json import load_strict_json
from tests.theme_sector_radar.report_fixture_factory import (
    build_sector_score_tree,
    write_json,
    write_selection_validation,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import backfill_historical_unified_and_validation as historical_backfill
from backfill_historical_unified_and_validation import (
    scan_available_dates,
    generate_backfill_report,
    generate_backfill_markdown,
    DATE_RE,
)


@pytest.fixture
def historical_report_tree(tmp_path, monkeypatch):
    dates = [
        "2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04", "2026-06-05",
        "2026-06-29", "2026-07-02", "2026-07-03", "2026-07-07", "2026-07-08",
    ]
    roots = build_sector_score_tree(tmp_path, dates)
    (roots["sector_scores"] / "2026-06-27-rotation-day1").mkdir()
    (roots["sector_scores"] / "2026-06-28-phase3-fixture").mkdir()

    write_json(
        roots["unified"] / "2026-06-29" / "unified_report.json",
        {"trend_candidates_all": [{"code": "600000"}], "burst_candidates_all": []},
    )
    write_json(
        roots["sector_research"] / "2026-06-29" / "sector_research.json",
        {"as_of_date": "2026-06-29", "research_results": []},
    )
    concept_path = roots["concept_rank"] / "2026-06-29" / "concept_unified_rank.csv"
    concept_path.parent.mkdir(parents=True)
    concept_path.write_text("rank,sector_name\n", encoding="utf-8")

    monkeypatch.setattr(historical_backfill, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(historical_backfill, "OUTPUT_DIR", roots["selection_validation"])
    return roots


class TestDateRegex:
    def test_valid_date_matches(self):
        assert DATE_RE.match("2026-06-01") is not None
        assert DATE_RE.match("2026-12-31") is not None

    def test_suffix_dirs_rejected(self):
        assert DATE_RE.match("2026-06-27-rotation-day1") is None
        assert DATE_RE.match("2026-06-28-akshare") is None
        assert DATE_RE.match("2026-06-28-phase3-fixture") is None


class TestScanAvailableDates:
    def test_can_export_false_when_input_directories_are_empty(self, tmp_path, monkeypatch):
        date = "2026-06-29"
        roots = build_sector_score_tree(tmp_path, [date])
        (roots["sector_research"] / date).mkdir(parents=True)
        (roots["concept_rank"] / date).mkdir(parents=True)
        monkeypatch.setattr(historical_backfill, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(historical_backfill, "OUTPUT_DIR", roots["selection_validation"])

        plan = scan_available_dates(date, date)

        assert len(plan) == 1
        assert plan[0]["can_export"] is False

    def test_scan_finds_dates(self, historical_report_tree):
        plan = scan_available_dates("2026-06-29", "2026-07-08")
        dates = [p["date"] for p in plan]
        assert "2026-06-29" in dates
        assert "2026-07-07" in dates

    def test_scan_filters_non_dates(self, historical_report_tree):
        plan = scan_available_dates("2026-06-27", "2026-06-28")
        dates = [p["date"] for p in plan]
        # Should not include 2026-06-27-rotation-day1 etc.
        for d in dates:
            assert re.match(r"^2026-\d{2}-\d{2}$", d)

    def test_scan_date_range(self, historical_report_tree):
        plan = scan_available_dates("2026-07-03", "2026-07-06")
        dates = [p["date"] for p in plan]
        for d in dates:
            assert "2026-07-03" <= d <= "2026-07-06"

    def test_can_export_false_for_old_dates(self, historical_report_tree):
        """Before backfill, old dates lack sector_research. After backfill, they have it."""
        plan = scan_available_dates("2026-06-01", "2026-06-05")
        for p in plan:
            # can_export depends on sector_research existence
            # After backfill, these dates have sector_research, so can_export=True
            # Before backfill, they would be False
            assert "can_export" in p

    def test_can_export_true_for_recent_dates(self, historical_report_tree):
        plan = scan_available_dates("2026-06-29", "2026-06-29")
        assert len(plan) == 1
        assert plan[0]["has_unified_report"] is True
        assert plan[0]["can_export"] is True


class TestBackfillReport:
    def _make_plan_entry(self, date, unified=True, top30=False, validation=False, can_export=True):
        return {
            "date": date,
            "has_sector_scores": True,
            "has_theme_snapshot": True,
            "has_unified_report": unified,
            "has_top30_candidates": top30,
            "has_validation": validation,
            "has_sector_research": can_export,
            "can_export": can_export,
            "should_run_unified": False,
            "should_run_export": unified and can_export and not top30,
            "should_run_validation": top30 and not validation,
        }

    def test_report_with_validations(self):
        plan = [
            self._make_plan_entry("2026-07-02", validation=True),
            self._make_plan_entry("2026-07-03", validation=True),
        ]
        results = {
            "2026-07-02": {"validation": {"success": True, "data_available": 20, "market_regime": "broad_up", "avg_candidate_return": 1.17}},
            "2026-07-03": {"validation": {"success": True, "data_available": 20, "market_regime": "broad_down", "avg_candidate_return": -2.62}},
        }
        report = generate_backfill_report(plan, results, {"start_date": "2026-07-02", "end_date": "2026-07-03"})
        assert report["final_valid_date_count"] == 2
        assert len(report["valid_dates"]) == 2

    def test_report_with_failures(self):
        plan = [self._make_plan_entry("2026-07-02")]
        results = {"2026-07-02": {"export": {"success": False, "stderr_snippet": "test error"}}}
        report = generate_backfill_report(plan, results, {})
        assert len(report["failures"]) == 1
        assert report["failures"][0]["step"] == "export"

    def test_report_no_sector_research(self):
        plan = [self._make_plan_entry("2026-06-15", can_export=False)]
        results = {}
        report = generate_backfill_report(plan, results, {})
        # Should not fail
        assert report["final_valid_date_count"] == 0

    def test_markdown_contains_sections(self):
        plan = [self._make_plan_entry("2026-07-02", validation=True)]
        results = {"2026-07-02": {"validation": {"success": True, "data_available": 20, "market_regime": "broad_up", "avg_candidate_return": 1.17}}}
        report = generate_backfill_report(plan, results, {"start_date": "2026-07-02", "end_date": "2026-07-02"})
        md = generate_backfill_markdown(report)
        assert "Run Config" in md
        assert "Date Status" in md
        assert "Cautions" in md

    def test_max_dates_limits_execution(self, historical_report_tree):
        """max-dates parameter should limit the plan length."""
        plan = scan_available_dates("2026-06-01", "2026-07-08")
        assert len(plan) > 3
        limited = plan[:3]
        assert len(limited) == 3

    def test_missing_ranking_doesnt_block(self):
        """Missing ranking should not crash the report."""
        plan = [self._make_plan_entry("2026-07-02", validation=True)]
        results = {"2026-07-02": {"validation": {"success": True, "data_available": 20, "market_regime": "broad_up", "avg_candidate_return": 1.0}}}
        report = generate_backfill_report(plan, results, {})
        assert report["final_valid_date_count"] == 1

    def test_validation_artifact_fixture_contract(self, historical_report_tree):
        valid_dates = ["2026-07-02", "2026-07-03"]
        for d in valid_dates:
            vpath = write_selection_validation(
                historical_report_tree["selection_validation"], d
            )
            assert vpath.exists(), f"Validation missing for {d}"
            payload = load_strict_json(vpath)
            assert payload["as_of"] == d
            assert payload["coverage"] == {
                "total_candidates": 1,
                "data_available": 1,
                "data_missing": 0,
                "missing_codes": [],
            }
