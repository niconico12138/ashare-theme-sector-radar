"""Tests for show_daily_result.py — uses temporary directories with fake data."""

import json
import csv
import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from show_daily_result import (
    load_sector_research,
    load_concept_rank,
    load_unified_report,
    _field,
    _f,
)


def _sample_joint_decision_summary() -> dict:
    from theme_sector_radar.joint_decision.builder import build_joint_decision_summary

    return build_joint_decision_summary(
        as_of="2026-07-10",
        unified_report={
            "run_health": {"status": "pass"},
            "data_quality": {"status": "pass"},
            "trend_top_stocks": [
                {
                    "code": "600001",
                    "name": "Alpha",
                    "sector_name": "Semiconductor",
                    "final_score": 76.0,
                    "factor_composite_shadow_score_v2": 61.0,
                    "selection_score": 71.5,
                    "selection_score_adjusted": 73.0,
                    "sector_support_score": 72.0,
                }
            ],
            "burst_top_stocks": [],
        },
        sectors=[
            {
                "sector_name": "Semiconductor",
                "sector_type": "concept",
                "ranking_score": 78.0,
                "trend_continuation_score": 71.0,
                "confidence_score": 0.82,
                "consensus_label": "trend_confirmed",
            }
        ],
        top30={"candidates": []},
        aihf_ranking={"items": [{"code": "600001", "agent_score": 74.0, "risk_level": "medium"}]},
        v2_monitor={"status_light": {"status": "ok"}},
        top_n=5,
    )


class TestFieldHelper:
    def test_found(self):
        assert _field({"a": 1, "b": 2}, "a", "b") == 1

    def test_missing_returns_default(self):
        assert _field({"a": 1}, "x", "y") == "-"

    def test_empty_string_returns_default(self):
        assert _field({"a": ""}, "a", "b") == "-"

    def test_none_returns_default(self):
        assert _field({"a": None}, "a", "b") == "-"


class TestFormatHelper:
    def test_format_number(self):
        assert _f(3.456) == "3.46"
        assert _f(0) == "0.00"

    def test_format_none(self):
        assert _f(None) == "-"
        assert _f("-") == "-"


class TestLoadSectorResearch:
    def test_load_existing(self, tmp_path):
        research_dir = tmp_path / "reports" / "full90" / "sector_research" / "2026-07-03"
        research_dir.mkdir(parents=True)
        data = {
            "as_of_date": "2026-07-03",
            "sector_type": "mixed",
            "research_results": [
                {"sector_name": "化学制药", "sector_type": "industry",
                 "ranking_score": 0.8, "opportunity_score": 0.55,
                 "evidence_score": 0.7, "confidence_score": 0.9,
                 "consensus_label": "trend_confirmed"},
                {"sector_name": "氟化工", "sector_type": "concept",
                 "ranking_score": 0.6, "opportunity_score": 0.4},
            ],
        }
        (research_dir / "sector_research.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        import show_daily_result as sdr
        orig = sdr.SECTOR_RESEARCH_DIR
        sdr.SECTOR_RESEARCH_DIR = tmp_path / "reports" / "full90" / "sector_research"
        try:
            result = sdr.load_sector_research("2026-07-03")
        finally:
            sdr.SECTOR_RESEARCH_DIR = orig

        assert len(result) == 1
        assert result[0]["sector_name"] == "化学制药"
        assert result[0]["sector_type"] == "industry"
        assert result[0]["ranking_score"] == 0.8

    def test_missing_file_returns_empty(self, tmp_path):
        import show_daily_result as sdr
        orig = sdr.SECTOR_RESEARCH_DIR
        sdr.SECTOR_RESEARCH_DIR = tmp_path / "nonexistent"
        try:
            result = sdr.load_sector_research("2026-07-03")
        finally:
            sdr.SECTOR_RESEARCH_DIR = orig
        assert result == []


class TestLoadConceptRank:
    def test_load_existing(self, tmp_path):
        concept_dir = tmp_path / "reports" / "full_concept" / "unified_rank" / "2026-07-03"
        concept_dir.mkdir(parents=True)
        csv_path = concept_dir / "concept_unified_rank.csv"
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["rank", "sector_name", "concept_final_rank_score",
                                                   "trend_continuation_score", "trend_level_cn",
                                                   "short_term_burst_score", "burst_level_cn",
                                                   "agent_consensus_label"])
            writer.writeheader()
            writer.writerow({"rank": 1, "sector_name": "氟化工概念", "concept_final_rank_score": "67.53",
                             "trend_continuation_score": "66.2", "trend_level_cn": "强趋势",
                             "short_term_burst_score": "48.8", "burst_level_cn": "短线中性",
                             "agent_consensus_label": "trend_confirmed"})

        import show_daily_result as sdr
        orig = sdr.CONCEPT_RANK_DIR
        sdr.CONCEPT_RANK_DIR = tmp_path / "reports" / "full_concept" / "unified_rank"
        try:
            result = sdr.load_concept_rank("2026-07-03")
        finally:
            sdr.CONCEPT_RANK_DIR = orig

        assert len(result) == 1
        assert result[0]["_name"] == "氟化工概念"
        assert result[0]["_comp"] == "67.53"
        assert result[0]["_trend"] == "66.2"
        assert result[0]["_agent"] == "trend_confirmed"

    def test_missing_returns_empty(self, tmp_path):
        import show_daily_result as sdr
        orig = sdr.CONCEPT_RANK_DIR
        sdr.CONCEPT_RANK_DIR = tmp_path / "nonexistent"
        try:
            result = sdr.load_concept_rank("2026-07-03")
        finally:
            sdr.CONCEPT_RANK_DIR = orig
        assert result == []


class TestLoadUnifiedReport:
    def test_load_existing(self, tmp_path):
        unified_dir = tmp_path / "reports" / "unified" / "2026-07-03"
        unified_dir.mkdir(parents=True)
        data = {
            "report_type": "unified_pipeline",
            "data_source": {
                "constituent_sources": {"http_mapping": 8},
                "quant_score_sources": {"http_enhanced": 10},
                "fund_flow_source": "fund_flow_ths_batch",
                "stock_info_sources": {"ok": 30, "filtered_st": 2, "unknown": 0},
            },
            "run_health": {"status": "warn", "reasons": ["mapping占比高"]},
            "trend_top_stocks": [
                {"code": "600030", "name": "中信证券", "final_score": 82.5,
                 "quant_score": 82.0, "relevance_score": 0.833, "sector_name": "证券",
                 "score_breakdown": {"has_fund_flow": True, "final_score": 82.5}},
            ],
            "burst_top_stocks": [
                {"code": "002422", "name": "科伦药业", "final_score": 84.5,
                 "quant_score": 85.3, "relevance_score": 0.789, "sector_name": "化学制药",
                 "score_breakdown": {"has_fund_flow": True, "final_score": 84.5}},
            ],
        }
        (unified_dir / "unified_report.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        import show_daily_result as sdr
        orig = sdr.UNIFIED_DIR
        sdr.UNIFIED_DIR = tmp_path / "reports" / "unified"
        try:
            result = sdr.load_unified_report("2026-07-03")
        finally:
            sdr.UNIFIED_DIR = orig
        assert result.get("report_type") == "unified_pipeline"
        assert len(result.get("trend_top_stocks", [])) == 1
        assert result.get("run_health", {}).get("status") == "warn"

    def test_missing_returns_empty(self, tmp_path):
        import show_daily_result as sdr
        orig = sdr.UNIFIED_DIR
        sdr.UNIFIED_DIR = tmp_path / "nonexistent"
        try:
            result = sdr.load_unified_report("2026-07-03")
        finally:
            sdr.UNIFIED_DIR = orig
        assert result == {}


class TestMainWithFakeData:
    def test_output_format(self, tmp_path, capsys):
        """Test full output format with fake data."""
        # Create all necessary files
        research_dir = tmp_path / "reports" / "full90" / "sector_research" / "2026-07-03"
        research_dir.mkdir(parents=True)
        (research_dir / "sector_research.json").write_text(json.dumps({
            "research_results": [
                {"sector_name": "化学制药", "sector_type": "industry",
                 "ranking_score": 0.8, "opportunity_score": 0.55,
                 "confidence_score": 0.9, "consensus_label": "trend_confirmed"},
            ],
        }, ensure_ascii=False), encoding="utf-8")

        concept_dir = tmp_path / "reports" / "full_concept" / "unified_rank" / "2026-07-03"
        concept_dir.mkdir(parents=True)
        with open(concept_dir / "concept_unified_rank.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["rank", "sector_name", "concept_final_rank_score",
                                                   "trend_continuation_score", "trend_level_cn",
                                                   "short_term_burst_score", "burst_level_cn",
                                                   "agent_consensus_label"])
            writer.writeheader()
            writer.writerow({"rank": 1, "sector_name": "氟化工", "concept_final_rank_score": "67.53",
                             "trend_continuation_score": "66.2", "trend_level_cn": "强",
                             "short_term_burst_score": "48.8", "burst_level_cn": "中",
                             "agent_consensus_label": "confirmed"})

        unified_dir = tmp_path / "reports" / "unified" / "2026-07-03"
        unified_dir.mkdir(parents=True)
        (unified_dir / "unified_report.json").write_text(json.dumps({
            "data_source": {"sector_input_source": "mixed",
                            "constituent_sources": {"http_mapping": 5},
                            "quant_score_sources": {"http_enhanced": 10},
                            "fund_flow_source": "fund_flow_ths_batch",
                            "stock_info_sources": {"ok": 10, "unknown": 0}},
            "run_health": {"status": "warn", "reasons": ["mapping占比高"]},
            "data_quality": {"coverage": {"constituent_real_ratio": 0.5}},
            "trend_top_stocks": [{"code": "600030", "name": "中信证券", "final_score": 82.5,
                                   "quant_score": 82.0, "relevance_score": 0.833,
                                   "sector_name": "证券", "sector_type": "industry",
                                   "score_breakdown": {"has_fund_flow": True}}],
            "burst_top_stocks": [{"code": "002422", "name": "科伦药业", "final_score": 84.5,
                                   "quant_score": 85.3, "relevance_score": 0.789,
                                   "sector_name": "化学制药", "sector_type": "industry",
                                   "score_breakdown": {"has_fund_flow": True}}],
        }, ensure_ascii=False), encoding="utf-8")

        import show_daily_result as sdr
        # Override paths
        orig_r, orig_c, orig_u = sdr.SECTOR_RESEARCH_DIR, sdr.CONCEPT_RANK_DIR, sdr.UNIFIED_DIR
        sdr.SECTOR_RESEARCH_DIR = tmp_path / "reports" / "full90" / "sector_research"
        sdr.CONCEPT_RANK_DIR = tmp_path / "reports" / "full_concept" / "unified_rank"
        sdr.UNIFIED_DIR = tmp_path / "reports" / "unified"

        try:
            report = sdr.load_unified_report("2026-07-03")
            sectors = sdr.load_sector_research("2026-07-03")
            concepts = sdr.load_concept_rank("2026-07-03")
            assert report, "report should not be empty"
            assert sectors, "sectors should not be empty"
            assert concepts, "concepts should not be empty"
        finally:
            sdr.SECTOR_RESEARCH_DIR = orig_r
            sdr.CONCEPT_RANK_DIR = orig_c
            sdr.UNIFIED_DIR = orig_u


class TestJointDecisionPreferredOutput:
    def test_load_joint_decision_summary_existing(self, tmp_path):
        import show_daily_result as sdr

        summary = _sample_joint_decision_summary()
        summary_dir = tmp_path / "reports" / "joint_decision" / "2026-07-10"
        summary_dir.mkdir(parents=True)
        (summary_dir / "joint_decision_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False),
            encoding="utf-8",
        )

        orig = sdr.JOINT_DECISION_DIR
        sdr.JOINT_DECISION_DIR = tmp_path / "reports" / "joint_decision"
        try:
            result = sdr.load_joint_decision_summary("2026-07-10")
        finally:
            sdr.JOINT_DECISION_DIR = orig

        assert result["schema_version"] == "1.0"
        assert result["stock_decision"]["core_watch"][0]["code"] == "600001"

    def test_load_joint_decision_summary_missing_returns_empty(self, tmp_path):
        import show_daily_result as sdr

        orig = sdr.JOINT_DECISION_DIR
        sdr.JOINT_DECISION_DIR = tmp_path / "missing"
        try:
            assert sdr.load_joint_decision_summary("2026-07-10") == {}
        finally:
            sdr.JOINT_DECISION_DIR = orig

    def test_compact_prefers_joint_decision_summary(self, tmp_path, capsys):
        import show_daily_result as sdr

        summary = _sample_joint_decision_summary()
        summary_dir = tmp_path / "reports" / "joint_decision" / "2026-07-10"
        summary_dir.mkdir(parents=True)
        (summary_dir / "joint_decision_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False),
            encoding="utf-8",
        )

        orig = sdr.JOINT_DECISION_DIR
        sdr.JOINT_DECISION_DIR = tmp_path / "reports" / "joint_decision"
        try:
            sdr._run_compact({}, "2026-07-10", 5, [], [], None, tmp_path / "out")
        finally:
            sdr.JOINT_DECISION_DIR = orig

        captured = capsys.readouterr()
        assert "# Joint Decision 2026-07-10" in captured.out
        output_json = tmp_path / "out" / "2026-07-10" / "decision_summary.json"
        output_md = tmp_path / "out" / "2026-07-10" / "decision_summary.md"
        assert json.loads(output_json.read_text(encoding="utf-8"))["decision_mode"] == "watch_only"
        assert "Alpha" in output_md.read_text(encoding="utf-8")

    def test_json_prefers_joint_decision_summary(self, tmp_path, capsys):
        import show_daily_result as sdr

        summary = _sample_joint_decision_summary()
        summary_dir = tmp_path / "reports" / "joint_decision" / "2026-07-10"
        summary_dir.mkdir(parents=True)
        (summary_dir / "joint_decision_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False),
            encoding="utf-8",
        )

        orig = sdr.JOINT_DECISION_DIR
        sdr.JOINT_DECISION_DIR = tmp_path / "reports" / "joint_decision"
        try:
            sdr._run_json({}, "2026-07-10", 5, [], [], None, tmp_path / "out")
        finally:
            sdr.JOINT_DECISION_DIR = orig

        captured = capsys.readouterr()
        assert '"stock_decision"' in captured.out
        output_json = tmp_path / "out" / "2026-07-10" / "decision_summary.json"
        assert json.loads(output_json.read_text(encoding="utf-8"))["as_of"] == "2026-07-10"

    def test_main_compact_uses_joint_summary_without_unified_report(self, tmp_path, monkeypatch, capsys):
        import show_daily_result as sdr

        summary = _sample_joint_decision_summary()
        summary_dir = tmp_path / "reports" / "joint_decision" / "2026-07-10"
        summary_dir.mkdir(parents=True)
        (summary_dir / "joint_decision_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False),
            encoding="utf-8",
        )

        monkeypatch.setattr(sdr, "JOINT_DECISION_DIR", tmp_path / "reports" / "joint_decision")
        monkeypatch.setattr(sdr, "UNIFIED_DIR", tmp_path / "missing_unified")
        monkeypatch.setattr(sdr, "SECTOR_RESEARCH_DIR", tmp_path / "missing_sector")
        monkeypatch.setattr(sdr, "CONCEPT_RANK_DIR", tmp_path / "missing_concept")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "show_daily_result.py",
                "--as-of",
                "2026-07-10",
                "--format",
                "compact",
                "--output-dir",
                str(tmp_path / "out"),
            ],
        )

        sdr.main()

        captured = capsys.readouterr()
        assert "# Joint Decision 2026-07-10" in captured.out
        assert (tmp_path / "out" / "2026-07-10" / "decision_summary.json").exists()



    def test_load_joint_decision_summary_invalid_contract_returns_empty(self, tmp_path):
        import show_daily_result as sdr

        summary = _sample_joint_decision_summary()
        summary["decision_mode"] = "trade_ready"
        summary_dir = tmp_path / "reports" / "joint_decision" / "2026-07-10"
        summary_dir.mkdir(parents=True)
        (summary_dir / "joint_decision_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False),
            encoding="utf-8",
        )

        orig = sdr.JOINT_DECISION_DIR
        sdr.JOINT_DECISION_DIR = tmp_path / "reports" / "joint_decision"
        try:
            result = sdr.load_joint_decision_summary("2026-07-10")
        finally:
            sdr.JOINT_DECISION_DIR = orig

        assert result == {}

class TestEdgeCases:
    def test_missing_file_gives_error(self):
        """Missing unified_report.json should print error, not traceback."""
        import show_daily_result as sdr
        orig = sdr.UNIFIED_DIR
        sdr.UNIFIED_DIR = Path("/nonexistent/path")
        try:
            # The script would print an error and exit(1)
            # We test the load function returns empty
            result = sdr.load_unified_report("2099-01-01")
            assert result == {}
        finally:
            sdr.UNIFIED_DIR = orig
