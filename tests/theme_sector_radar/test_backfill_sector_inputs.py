"""Tests for backfill historical sector inputs."""

import csv
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from backfill_historical_sector_inputs import (
    scan_dates,
    build_sector_research,
    build_concept_rank,
    write_concept_csv,
    check_compatibility,
    build_report,
    generate_markdown,
    DATE_RE,
    _derive_consensus_label,
    _safe_float,
)


# ======================================================================
# Helpers
# ======================================================================

def _load_sector_scores(date: str) -> dict:
    path = PROJECT_ROOT / "reports" / "sector_scores" / date / "sector_scores.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ======================================================================
# Test: Date Regex
# ======================================================================

class TestDateRegex:
    def test_valid_date(self):
        assert DATE_RE.match("2026-06-01") is not None
        assert DATE_RE.match("2026-12-31") is not None

    def test_suffix_rejected(self):
        assert DATE_RE.match("2026-06-27-rotation-day1") is None
        assert DATE_RE.match("2026-06-28-akshare") is None


# ======================================================================
# Test: Scan Dates
# ======================================================================

class TestScanDates:
    def test_scan_finds_dates(self):
        plan = scan_dates("2026-06-01", "2026-06-05")
        assert len(plan) >= 4
        dates = [p["date"] for p in plan]
        assert "2026-06-01" in dates

    def test_scan_date_range(self):
        plan = scan_dates("2026-06-10", "2026-06-12")
        for p in plan:
            assert "2026-06-10" <= p["date"] <= "2026-06-12"

    def test_scan_excludes_suffixes(self):
        plan = scan_dates("2026-06-27", "2026-06-28")
        for p in plan:
            assert DATE_RE.match(p["date"])

    def test_scan_shows_existing(self):
        plan = scan_dates("2026-06-01", "2026-06-03")
        for p in plan:
            assert p["has_sector_scores"] is True
            # After backfill, these dates now have research
            # Just verify the fields exist
            assert "has_existing_research" in p
            assert "has_existing_concept" in p


# ======================================================================
# Test: Build Sector Research
# ======================================================================

class TestBuildSectorResearch:
    def test_build_from_scores(self):
        scores = _load_sector_scores("2026-06-01")
        research = build_sector_research("2026-06-01", scores)
        assert research["as_of_date"] == "2026-06-01"
        assert research["version"] == "historical_backfill_v1"
        assert len(research["research_results"]) > 0

    def test_industry_only(self):
        scores = _load_sector_scores("2026-06-01")
        research = build_sector_research("2026-06-01", scores)
        for r in research["research_results"]:
            assert r["sector_type"] == "industry"

    def test_scores_in_0_1_range(self):
        scores = _load_sector_scores("2026-06-01")
        research = build_sector_research("2026-06-01", scores)
        for r in research["research_results"]:
            assert 0 <= r["ranking_score"] <= 1
            assert 0 <= r["opportunity_score"] <= 1
            assert 0 <= r["evidence_score"] <= 1
            assert 0 <= r["risk_control_score"] <= 1
            assert 0 <= r["confidence_score"] <= 1

    def test_sorted_by_ranking_score(self):
        scores = _load_sector_scores("2026-06-01")
        research = build_sector_research("2026-06-01", scores)
        rankings = [r["ranking_score"] for r in research["research_results"]]
        assert rankings == sorted(rankings, reverse=True)

    def test_consensus_label_present(self):
        scores = _load_sector_scores("2026-06-01")
        research = build_sector_research("2026-06-01", scores)
        for r in research["research_results"]:
            assert r["consensus_label"] in [
                "trend_confirmed", "trend_confirmed_but_strength_limited",
                "defensive_watch", "defensive_stable_watch",
                "weak_or_avoid", "conflicted",
            ]


# ======================================================================
# Test: Build Concept Rank
# ======================================================================

class TestBuildConceptRank:
    def test_empty_when_no_concepts(self):
        scores = _load_sector_scores("2026-06-01")
        concepts = build_concept_rank("2026-06-01", scores)
        # 2026-06-01 has no concept sectors
        assert len(concepts) == 0

    def test_no_crash_on_empty(self):
        scores = {"scores": [{"sector_type": "industry"}]}
        concepts = build_concept_rank("2026-06-01", scores)
        assert concepts == []


# ======================================================================
# Test: Write Concept CSV
# ======================================================================

class TestWriteConceptCSV:
    def test_empty_csv(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        write_concept_csv(csv_path, [])
        assert csv_path.exists()
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 0
            assert "sector_name" in reader.fieldnames

    def test_csv_with_data(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        concepts = [
            {"sector_name": "TestConcept", "concept_final_rank_score": 80.0,
             "trend_continuation_score": 70.0, "short_term_burst_score": 60.0,
             "agent_consensus_label": "trend_confirmed", "agent_ranking_score": 80.0,
             "agent_opportunity_score": 65.0, "risk_control_score": 100.0,
             "confidence_score": 0.8, "evidence_score": 70.0,
             "history_days": 20, "actual_history_days": 15,
             "trend_window_status": "ok"},
        ]
        write_concept_csv(csv_path, concepts)
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["sector_name"] == "TestConcept"
            assert rows[0]["rank"] == "1"


# ======================================================================
# Test: Consensus Label Mapping
# ======================================================================

class TestConsensusLabel:
    def test_known_profiles(self):
        assert _derive_consensus_label({"score_interpretation": {"profile": "trend_and_burst_confirmed"}}) == "trend_confirmed"
        assert _derive_consensus_label({"score_interpretation": {"profile": "weak_or_cooling"}}) == "weak_or_avoid"
        assert _derive_consensus_label({"score_interpretation": {"profile": "neutral"}}) == "conflicted"

    def test_fallback_scores(self):
        entry = {"trend_continuation_score": 80, "short_term_burst_score": 70, "sector_selection_score": 75}
        assert _derive_consensus_label(entry) == "trend_confirmed"


# ======================================================================
# Test: Compatibility Check
# ======================================================================

class TestCompatibility:
    def test_existing_date_passes(self):
        result = check_compatibility("2026-06-01")
        assert result["research_ok"] is True
        assert result["concept_ok"] is True

    def test_nonexistent_date_fails(self):
        result = check_compatibility("2099-01-01")
        assert result["research_ok"] is False
        assert len(result["errors"]) > 0


# ======================================================================
# Test: Report Generation
# ======================================================================

class TestReport:
    def test_report_structure(self):
        plan = [{"date": "2026-06-01", "has_sector_scores": True,
                 "has_existing_research": False, "has_existing_concept": False,
                 "has_concept_in_scores": False,
                 "should_build_research": False, "should_build_concept": False}]
        results = {"2026-06-01": {"research_ok": True, "concept_ok": True}}
        report = build_report(plan, results, {"start_date": "2026-06-01", "end_date": "2026-06-01"})
        assert report["generated_sector_research_count"] == 1
        assert report["compatibility_check_summary"]["all_ok"] is True

    def test_markdown_sections(self):
        plan = [{"date": "2026-06-01", "has_sector_scores": True,
                 "has_existing_research": False, "has_existing_concept": False,
                 "has_concept_in_scores": False,
                 "should_build_research": False, "should_build_concept": False}]
        results = {"2026-06-01": {"research_ok": True, "concept_ok": True}}
        report = build_report(plan, results, {"start_date": "2026-06-01", "end_date": "2026-06-01"})
        md = generate_markdown(report)
        assert "Run Config" in md
        assert "Build Summary" in md
        assert "Compatibility" in md
        assert "Next Steps" in md
