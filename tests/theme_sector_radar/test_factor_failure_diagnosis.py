"""Tests for factor failure diagnosis."""

import json
import math
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from diagnose_factor_failure import (
    _rank,
    spearman_correlation,
    compute_regime_breakdown,
    compute_rank_correlations,
    compute_risk_exposure,
    compute_agent_diagnostic,
    compute_forward_return_quality,
    generate_diagnosis_summary,
    generate_markdown,
    _safe_float,
    _avg,
)
from tests.theme_sector_radar.report_fixture_factory import write_json


# ======================================================================
# Test: Spearman Rank Correlation
# ======================================================================

class TestSpearman:
    def test_identical_ranks(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert spearman_correlation(x, y) == 1.0

    def test_inverse_ranks(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [5.0, 4.0, 3.0, 2.0, 1.0]
        assert spearman_correlation(x, y) == -1.0

    def test_partial_correlation(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [1.0, 3.0, 2.0, 5.0, 4.0]
        corr = spearman_correlation(x, y)
        assert corr is not None
        assert 0.5 < corr < 1.0

    def test_insufficient_data(self):
        assert spearman_correlation([1.0], [1.0]) is None
        assert spearman_correlation([1.0, 2.0], [1.0, 2.0]) is None

    def test_tied_ranks(self):
        x = [1.0, 1.0, 3.0, 4.0, 5.0]
        y = [1.0, 2.0, 3.0, 4.0, 5.0]
        corr = spearman_correlation(x, y)
        assert corr is not None
        assert corr > 0.8

    def test_rank_function(self):
        ranks = _rank([3.0, 1.0, 4.0, 1.0, 5.0])
        # Values: 1.0→rank 1.5, 1.0→rank 1.5, 3.0→rank 3, 4.0→rank 4, 5.0→rank 5
        assert ranks[1] == 1.5  # second 1.0
        assert ranks[3] == 1.5  # first 1.0
        assert ranks[0] == 3.0  # 3.0
        assert ranks[4] == 5.0  # 5.0


# ======================================================================
# Test: Regime Breakdown
# ======================================================================

class TestRegimeBreakdown:
    def test_basic_breakdown(self):
        records = []
        for i in range(5):
            records.append({
                "date": "2026-06-01", "code": f"A{i}", "market_regime": "broad_up",
                "data_available": True, "next_return_pct": 2.0 - i,
                "decision_score": 80 - i * 10, "stock_short_score": 70 - i * 5,
                "stock_trend_score": 60, "sector_leader_score": 90,
                "risk_penalty_score": 5, "trade_eligibility": "focus",
                "source_pool": "trend", "agent_analysis_status": "pending_agent_analysis",
            })
        result = compute_regime_breakdown(records)
        assert "broad_up" in result
        assert result["broad_up"]["sample_count"] == 5

    def test_empty_regime_skipped(self):
        records = [
            {"date": "2026-06-01", "code": "A", "market_regime": "broad_up",
             "data_available": True, "next_return_pct": 2.0},
        ]
        result = compute_regime_breakdown(records)
        # Only 1 sample, should be skipped (min 3)
        assert "broad_up" not in result


# ======================================================================
# Test: Risk Exposure
# ======================================================================

class TestRiskExposure:
    def test_basic_risk_exposure(self):
        records = []
        for i in range(20):
            records.append({
                "date": "2026-06-01", "code": f"S{i}",
                "data_available": True, "next_return_pct": -i * 0.5,
                "decision_score": 100 - i * 5,
                "stock_short_score": 80 - i * 3,
                "stock_trend_score": 70 - i * 2,
                "sector_leader_score": 90 - i * 4,
                "risk_penalty_score": i * 2,
                "next_low_return_pct": -i * 1.0,
                "max_intraday_drawdown_pct": -i * 0.8,
                "trade_eligibility": "focus" if i < 5 else "watch",
                "source_pool": "trend" if i < 10 else "burst",
                "risk_level": "low" if i < 10 else "medium",
            })
        result = compute_risk_exposure(records)
        assert "top5" in result
        assert "bottom10" in result
        assert result["top5"]["avg_return"] is not None
        assert result["bottom10"]["avg_return"] is not None

    def test_higher_drawdown_flag(self):
        records = []
        for i in range(15):
            records.append({
                "date": "2026-06-01", "code": f"S{i}",
                "data_available": True, "next_return_pct": -i * 0.5,
                "decision_score": 100 - i * 5,
                "stock_short_score": 80, "stock_trend_score": 70,
                "sector_leader_score": 90, "risk_penalty_score": 5,
                "next_low_return_pct": -10 if i < 5 else -2,  # top5 has deeper lows
                "max_intraday_drawdown_pct": -8 if i < 5 else -1,
                "trade_eligibility": "focus", "source_pool": "trend",
                "risk_level": "low",
            })
        result = compute_risk_exposure(records)
        assert "high_score_higher_drawdown" in result.get("flags", [])


# ======================================================================
# Test: Agent Diagnostic
# ======================================================================

class TestAgentDiagnostic:
    def test_basic_agent_diag(self):
        records = []
        for i in range(10):
            records.append({
                "date": "2026-06-01", "code": f"A{i}",
                "data_available": True, "next_return_pct": 1.0 if i < 5 else -1.0,
                "agent_analysis_status": "pending_agent_analysis",
                "decision_score": 70 if i < 5 else 40,
            })
        for i in range(10):
            records.append({
                "date": "2026-06-01", "code": f"S{i}",
                "data_available": True, "next_return_pct": 0.5,
                "agent_analysis_status": "skipped_by_agent_stock_limit",
                "decision_score": 30,
            })
        result = compute_agent_diagnostic(records)
        assert result["analyzed_count"] == 10
        assert result["skipped_count"] == 10
        # analyzed scores higher but may have lower returns
        assert result["analyzed_avg_decision_score"] > result["skipped_avg_decision_score"]


# ======================================================================
# Test: Forward Return Quality
# ======================================================================

class TestForwardReturnQuality:
    def test_quality_check(self):
        records = [
            {"data_available": True, "next_return_pct": 5.0},
            {"data_available": True, "next_return_pct": -3.0},
            {"data_available": False, "next_return_pct": None},
            {"data_available": True, "next_return_pct": 25.0},  # extreme
        ]
        result = compute_forward_return_quality(records)
        assert result["sample_count"] == 3
        assert result["missing_count"] == 1
        assert result["extreme_return_count"] == 1
        assert result["min_return"] == -3.0
        assert result["max_return"] == 25.0


# ======================================================================
# Test: Diagnosis Summary
# ======================================================================

class TestDiagnosisSummary:
    def test_summary_structure(self):
        summary = generate_diagnosis_summary(
            regime_breakdown={"broad_up": {"decision_score_gap": 0.5}, "broad_down": {"decision_score_gap": -0.5}},
            rank_corrs={"overall": {"decision_score": {"avg_correlation": -0.1}}},
            risk_exposure={"flags": ["high_score_higher_drawdown"]},
            agent_diag={"flags": ["agent_selection_high_beta_risk"]},
            fwd_quality={"extreme_return_count": 2},
            aggregate={"coverage_summary": {"valid_date_count": 24}},
        )
        assert "primary_findings" in summary
        assert "likely_causes" in summary
        assert "recommended_next_steps" in summary
        assert "do_not_do" in summary
        assert len(summary["do_not_do"]) >= 3

    def test_do_not_do_always_present(self):
        summary = generate_diagnosis_summary({}, {}, {}, {}, {}, {"coverage_summary": {}})
        assert "do_not_do" in summary
        assert len(summary["do_not_do"]) >= 3


# ======================================================================
# Test: Markdown
# ======================================================================

class TestMarkdown:
    def test_all_sections(self):
        diagnosis = {
            "coverage": {"valid_date_count": 24, "total_records": 423, "records_with_data": 418},
            "summary": {"primary_findings": ["test finding"], "likely_causes": ["test cause"],
                        "recommended_next_steps": ["test step"], "do_not_do": ["test dont"]},
        }
        md = generate_markdown(diagnosis, {}, {}, {}, {}, {}, diagnosis["summary"])
        assert "Executive Summary" in md
        assert "Data Coverage" in md
        assert "Market Regime Breakdown" in md
        assert "Rank Correlation" in md
        assert "High Score Risk Exposure" in md
        assert "Agent Incremental" in md
        assert "Forward Return Quality" in md
        assert "Likely Causes" in md
        assert "Recommended Next Steps" in md
        assert "Do Not Do" in md


# ======================================================================
# Test: Integration
# ======================================================================

@pytest.fixture
def diagnosis_output_paths(tmp_path):
    records = []
    for i in range(20):
        analyzed = i < 10
        date_index = i // 5
        records.append({
            "date": f"2026-07-{date_index + 1:02d}",
            "code": f"S{i}",
            "market_regime": "broad_up" if date_index % 2 == 0 else "broad_down",
            "data_available": True,
            "next_return_pct": float(-3 - i / 10) if analyzed else float(2 + i / 10),
            "next_low_return_pct": float(-12 - i / 10) if analyzed else float(-2 - i / 100),
            "max_intraday_drawdown_pct": float(-8 - i / 10) if analyzed else float(-1 - i / 100),
            "decision_score": float(100 - i) if analyzed else float(60 - (i - 10)),
            "stock_short_score": float(70 - i),
            "stock_trend_score": float(60 - i),
            "sector_leader_score": float(50 - i),
            "risk_penalty_score": float(20 - i),
            "trade_eligibility": "focus" if analyzed else "watch",
            "source_pool": "burst" if analyzed else "trend",
            "agent_analysis_status": "analyzed" if analyzed else "skipped_by_agent_stock_limit",
            "agent_score": float(40 + i),
        })
    regime_breakdown = compute_regime_breakdown(records)
    rank_corrs = compute_rank_correlations(records)
    risk_exposure = compute_risk_exposure(records)
    agent_diag = compute_agent_diagnostic(records)
    fwd_quality = compute_forward_return_quality(records)
    aggregate = {
        "coverage_summary": {"valid_date_count": 4},
        "factor_performance_summary": {},
    }
    summary = generate_diagnosis_summary(
        regime_breakdown,
        rank_corrs,
        risk_exposure,
        agent_diag,
        fwd_quality,
        aggregate,
    )
    coverage = {
        "valid_date_count": 4,
        "total_records": len(records),
        "records_with_data": len(records),
    }
    diagnosis = {
        "as_of": "synthetic-test-window",
        "coverage": coverage,
        "regime_breakdown": regime_breakdown,
        "rank_correlations": rank_corrs,
        "risk_exposure": risk_exposure,
        "agent_diagnostic": agent_diag,
        "forward_return_quality": fwd_quality,
        "summary": summary,
    }

    output_dir = tmp_path / "diagnostics"
    json_path = write_json(output_dir / "factor_failure_diagnosis.json", diagnosis)
    markdown_path = output_dir / "factor_failure_diagnosis.md"
    markdown_path.write_text(
        generate_markdown(
            diagnosis,
            regime_breakdown,
            rank_corrs,
            risk_exposure,
            agent_diag,
            fwd_quality,
            summary,
        ),
        encoding="utf-8",
    )
    return {"json": json_path, "markdown": markdown_path}

class TestIntegration:
    def test_diagnosis_output_exists(self, diagnosis_output_paths):
        path = diagnosis_output_paths["json"]
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "summary" in data
        assert "rank_correlations" in data
        assert "regime_breakdown" in data
        assert "error" not in data["risk_exposure"]
        assert "high_score_higher_drawdown" in data["risk_exposure"]["flags"]
        assert "agent_selection_high_beta_risk" in data["agent_diagnostic"]["flags"]

    def test_markdown_output_exists(self, diagnosis_output_paths):
        path = diagnosis_output_paths["markdown"]
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Factor Failure Diagnosis" in content
        assert "high_score_higher_drawdown" in content
        assert "agent_selection_high_beta_risk" in content
