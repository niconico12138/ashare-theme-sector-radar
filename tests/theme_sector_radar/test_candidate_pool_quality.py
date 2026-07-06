#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for candidate pool quality analysis and concept coverage analysis."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import analyze_candidate_pool_quality as acpq
import analyze_concept_coverage_for_reports as accr


# ============================================================
# Candidate Pool Quality Tests
# ============================================================


class TestCandidatePoolQuality:
    """Tests for candidate pool quality analysis."""

    def test_analyze_returns_valid_structure(self, tmp_path):
        """Test that analysis returns valid structure."""
        # Create mock top30_candidates.json
        date = "2026-07-06"
        output_dir = tmp_path / "reports" / "agent_bridge" / date
        output_dir.mkdir(parents=True)

        mock_data = {
            "candidates": [
                {"code": "600001", "name": "测试A", "boards": ["板块1"], "source_pool": "trend"},
                {"code": "600002", "name": "测试B", "boards": ["板块1"], "source_pool": "burst"},
                {"code": "600003", "name": "测试C", "boards": ["板块2"], "source_pool": "both"},
            ],
            "selection_funnel": {
                "trend_pool": {"eligible": 34, "selected_final": 15},
                "burst_pool": {"eligible": 39, "selected_final": 15},
                "merge": {"before_dedup": 30, "after_dedup": 20, "final_count": 20},
                "top_loss_reasons": [{"reason": "non_main_board", "count": 22}],
            },
        }
        (output_dir / "top30_candidates.json").write_text(
            json.dumps(mock_data, ensure_ascii=False), encoding="utf-8"
        )

        # Monkey-patch OUTPUT_DIR
        orig_dir = acpq.OUTPUT_DIR
        acpq.OUTPUT_DIR = tmp_path / "reports" / "agent_bridge"
        try:
            result = acpq.analyze_candidate_pool_quality(date)
        finally:
            acpq.OUTPUT_DIR = orig_dir

        assert "basic_stats" in result
        assert "board_concentration" in result
        assert "quality_risk_tags" in result
        assert result["basic_stats"]["final_candidate_count"] == 3

    def test_board_concentration_calculation(self, tmp_path):
        """Test board concentration calculation."""
        date = "2026-07-06"
        output_dir = tmp_path / "reports" / "agent_bridge" / date
        output_dir.mkdir(parents=True)

        # Create mock data with concentration
        mock_data = {
            "candidates": [
                {"code": f"60000{i}", "name": f"测试{i}", "boards": ["集中板块"], "source_pool": "trend"}
                for i in range(5)
            ] + [
                {"code": "600010", "name": "测试10", "boards": ["其他板块"], "source_pool": "burst"}
            ],
            "selection_funnel": {
                "trend_pool": {"eligible": 5, "selected_final": 5},
                "burst_pool": {"eligible": 1, "selected_final": 1},
                "merge": {"before_dedup": 6, "after_dedup": 6, "final_count": 6},
                "top_loss_reasons": [],
            },
        }
        (output_dir / "top30_candidates.json").write_text(
            json.dumps(mock_data, ensure_ascii=False), encoding="utf-8"
        )

        orig_dir = acpq.OUTPUT_DIR
        acpq.OUTPUT_DIR = tmp_path / "reports" / "agent_bridge"
        try:
            result = acpq.analyze_candidate_pool_quality(date)
        finally:
            acpq.OUTPUT_DIR = orig_dir

        concentration = result["board_concentration"]
        assert concentration["top1_board_ratio"] == pytest.approx(5 / 6, abs=0.01)
        assert "concentrated_boards" in result["quality_risk_tags"]

    def test_insufficient_candidates_tag(self, tmp_path):
        """Test insufficient_candidates tag when count < 25."""
        date = "2026-07-06"
        output_dir = tmp_path / "reports" / "agent_bridge" / date
        output_dir.mkdir(parents=True)

        mock_data = {
            "candidates": [
                {"code": f"60000{i}", "name": f"测试{i}", "boards": ["板块"], "source_pool": "trend"}
                for i in range(10)
            ],
            "selection_funnel": {
                "trend_pool": {"eligible": 10, "selected_final": 10},
                "burst_pool": {"eligible": 0, "selected_final": 0},
                "merge": {"before_dedup": 10, "after_dedup": 10, "final_count": 10},
                "top_loss_reasons": [],
            },
        }
        (output_dir / "top30_candidates.json").write_text(
            json.dumps(mock_data, ensure_ascii=False), encoding="utf-8"
        )

        orig_dir = acpq.OUTPUT_DIR
        acpq.OUTPUT_DIR = tmp_path / "reports" / "agent_bridge"
        try:
            result = acpq.analyze_candidate_pool_quality(date)
        finally:
            acpq.OUTPUT_DIR = orig_dir

        assert "insufficient_candidates" in result["quality_risk_tags"]

    def test_markdown_report_generation(self, tmp_path):
        """Test markdown report generation."""
        result = {
            "analysis_date": "2026-07-06T00:00:00",
            "as_of_date": "2026-07-06",
            "basic_stats": {
                "final_candidate_count": 20,
                "trend_count": 5,
                "burst_count": 5,
                "both_count": 10,
                "unique_board_count": 8,
                "unique_stock_count": 20,
            },
            "board_concentration": {
                "top_boards": [{"board": "氟化工概念", "count": 7, "ratio": 0.35}],
                "top1_board_ratio": 0.35,
                "top3_board_ratio": 0.65,
            },
            "duplicate_analysis": {
                "stocks_with_multiple_boards": 5,
                "duplicate_ratio": 0.25,
            },
            "selection_funnel_summary": {
                "trend_eligible": 34,
                "trend_selected": 15,
                "burst_eligible": 39,
                "burst_selected": 15,
                "merge_before_dedup": 30,
                "merge_after_dedup": 20,
                "final_count": 20,
            },
            "top_loss_reasons": [{"reason": "non_main_board", "count": 22}],
            "quality_risk_tags": ["insufficient_candidates"],
        }

        md = acpq.generate_markdown_report(result)
        assert "Candidate Pool Quality Report" in md
        assert "Final Candidate Count" in md
        assert "Top1 Board Ratio" in md


# ============================================================
# Concept Coverage Analysis Tests
# ============================================================


class TestConceptCoverageAnalysis:
    """Tests for concept coverage analysis."""

    def test_coverage_status_missing(self, tmp_path):
        """Test coverage status for missing concept."""
        # Create mock concept_members_history.csv
        csv_dir = tmp_path / "market_data_service" / "data"
        csv_dir.mkdir(parents=True)
        csv_content = "as_of,concept,code,name,source,confidence,note,created_at\n"
        (csv_dir / "concept_members_history.csv").write_text(csv_content, encoding="utf-8")

        # Create mock concept_unified_rank.csv
        rank_dir = tmp_path / "reports" / "full_concept" / "unified_rank" / "2026-07-06"
        rank_dir.mkdir(parents=True)
        rank_content = "rank,sector_name,concept_final_rank_score,trend_continuation_score,short_term_burst_score\n"
        rank_content += "1,缺失概念,70.0,60.0,50.0\n"
        (rank_dir / "concept_unified_rank.csv").write_text(rank_content, encoding="utf-8")

        orig_dir = accr.CONCEPT_RANK_DIR
        accr.CONCEPT_RANK_DIR = tmp_path / "reports" / "full_concept" / "unified_rank"
        try:
            result = accr.analyze_concept_coverage(["2026-07-06"], 10, str(tmp_path))
        finally:
            accr.CONCEPT_RANK_DIR = orig_dir

        assert result["coverage_summary"]["missing"] == 1
        assert result["concept_coverage"][0]["coverage_status"] == "missing"

    def test_coverage_status_covered_thin(self, tmp_path):
        """Test coverage status for thin coverage concept."""
        # Create mock concept_members_history.csv with 5 stocks
        csv_dir = tmp_path / "market_data_service" / "data"
        csv_dir.mkdir(parents=True)
        csv_lines = ["as_of,concept,code,name,source,confidence,note,created_at"]
        for i in range(5):
            csv_lines.append(f"2026-07-06,薄覆盖概念,60000{i},股票{i},manual_snapshot,0.8,test,2026-07-06T00:00:00Z")
        (csv_dir / "concept_members_history.csv").write_text("\n".join(csv_lines), encoding="utf-8")

        # Create mock concept_unified_rank.csv
        rank_dir = tmp_path / "reports" / "full_concept" / "unified_rank" / "2026-07-06"
        rank_dir.mkdir(parents=True)
        rank_content = "rank,sector_name,concept_final_rank_score,trend_continuation_score,short_term_burst_score\n"
        rank_content += "1,薄覆盖概念,70.0,60.0,50.0\n"
        (rank_dir / "concept_unified_rank.csv").write_text(rank_content, encoding="utf-8")

        orig_dir = accr.CONCEPT_RANK_DIR
        accr.CONCEPT_RANK_DIR = tmp_path / "reports" / "full_concept" / "unified_rank"
        try:
            result = accr.analyze_concept_coverage(["2026-07-06"], 10, str(tmp_path))
        finally:
            accr.CONCEPT_RANK_DIR = orig_dir

        assert result["coverage_summary"]["covered_thin"] == 1
        assert result["concept_coverage"][0]["coverage_status"] == "covered_thin"

    def test_priority_score_calculation(self, tmp_path):
        """Test priority score calculation."""
        # Create mock concept_members_history.csv
        csv_dir = tmp_path / "market_data_service" / "data"
        csv_dir.mkdir(parents=True)
        csv_content = "as_of,concept,code,name,source,confidence,note,created_at\n"
        (csv_dir / "concept_members_history.csv").write_text(csv_content, encoding="utf-8")

        # Create mock concept_unified_rank.csv with high rank
        rank_dir = tmp_path / "reports" / "full_concept" / "unified_rank" / "2026-07-06"
        rank_dir.mkdir(parents=True)
        rank_content = "rank,sector_name,concept_final_rank_score,trend_continuation_score,short_term_burst_score\n"
        rank_content += "1,高优先概念,80.0,70.0,60.0\n"
        (rank_dir / "concept_unified_rank.csv").write_text(rank_content, encoding="utf-8")

        orig_dir = accr.CONCEPT_RANK_DIR
        accr.CONCEPT_RANK_DIR = tmp_path / "reports" / "full_concept" / "unified_rank"
        try:
            result = accr.analyze_concept_coverage(["2026-07-06"], 10, str(tmp_path))
        finally:
            accr.CONCEPT_RANK_DIR = orig_dir

        coverage = result["concept_coverage"][0]
        # priority_score = appearances * 2 + max(0, 21 - best_rank) + composite_score / 10 + coverage_penalty
        # = 1 * 2 + max(0, 21 - 1) + 80.0 / 10 + 20 = 2 + 20 + 8 + 20 = 50
        assert coverage["priority_score"] == pytest.approx(50.0, abs=0.1)

    def test_markdown_report_generation(self, tmp_path):
        """Test markdown report generation."""
        result = {
            "analysis_date": "2026-07-06T00:00:00",
            "dates_analyzed": ["2026-07-06"],
            "top_n": 10,
            "total_concepts": 5,
            "coverage_summary": {
                "covered_good": 3,
                "covered_thin": 1,
                "missing": 1,
            },
            "concept_coverage": [
                {"concept_name": "概念1", "appearances": 3, "best_rank": 1, "latest_rank": 2,
                 "latest_composite_score": 70.0, "latest_trend_score": 60.0, "latest_burst_score": 50.0,
                 "has_local_concept_members": False, "local_stock_count": 0, "latest_snapshot_as_of": None,
                 "source_distribution": [], "coverage_status": "missing", "priority_score": 50.0,
                 "dates_affected": ["2026-07-06"]},
            ],
            "priority_list": [
                {"priority": 1, "concept_name": "概念1", "reason": "missing",
                 "suggested_min_stock_count": 10, "dates_affected": ["2026-07-06"],
                 "current_status": "missing", "local_stock_count": 0, "priority_score": 50.0},
            ],
        }

        md = accr.generate_markdown_report(result)
        assert "Concept Coverage Analysis Report" in md
        assert "Priority List" in md
        assert "概念1" in md
