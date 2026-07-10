"""Tests for factor direction calibration."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from calibrate_factor_direction import (
    compute_factor_stats,
    classify_direction,
    interpret_risk_penalty,
    build_recommendations,
    _split_by_percentile,
    _get_current_usage,
    _resolve_aggregate_path,
)


# ======================================================================
# Test: Bucket Splitting
# ======================================================================

class TestBucketSplitting:
    def test_high_low_split(self):
        items = [
            {"code": "A", "factor": 90, "next_return_pct": 5.0, "data_available": True},
            {"code": "B", "factor": 80, "next_return_pct": 3.0, "data_available": True},
            {"code": "C", "factor": 70, "next_return_pct": 1.0, "data_available": True},
            {"code": "D", "factor": 30, "next_return_pct": -1.0, "data_available": True},
            {"code": "E", "factor": 20, "next_return_pct": -3.0, "data_available": True},
            {"code": "F", "factor": 10, "next_return_pct": -5.0, "data_available": True},
        ]
        high, low = _split_by_percentile(items, "factor", 0.3)
        # max(1, int(6*0.3)) = 1
        assert len(high) >= 1
        assert len(low) >= 1
        assert high[0]["code"] == "A"  # highest factor
        assert low[-1]["code"] == "F"  # lowest factor

    def test_insufficient_items(self):
        items = [{"code": "A", "factor": 90}]
        high, low = _split_by_percentile(items, "factor", 0.3)
        assert len(high) == 0
        assert len(low) == 0


# ======================================================================
# Test: Direction Classification
# ======================================================================

class TestDirectionClassification:
    def test_positive_alpha(self):
        all_stats = {"sample_count": 200, "date_count": 10,
                     "high_minus_low_gap": 1.5, "consistency_positive": 70}
        direction, conf = classify_direction(all_stats, {}, {})
        assert direction == "positive_alpha"
        assert conf == "medium"

    def test_negative_alpha(self):
        all_stats = {"sample_count": 200, "date_count": 10,
                     "high_minus_low_gap": -1.5, "consistency_negative": 70}
        direction, conf = classify_direction(all_stats, {}, {})
        assert direction == "negative_alpha"

    def test_defensive_only(self):
        all_stats = {"sample_count": 200, "date_count": 10, "high_minus_low_gap": 0.3}
        up_stats = {"high_minus_low_gap": -0.2}
        down_stats = {"high_minus_low_gap": 1.0}
        direction, _ = classify_direction(all_stats, up_stats, down_stats)
        assert direction == "defensive_only"

    def test_offensive_only(self):
        all_stats = {"sample_count": 200, "date_count": 10, "high_minus_low_gap": 0.3}
        up_stats = {"high_minus_low_gap": 1.0}
        down_stats = {"high_minus_low_gap": -0.2}
        direction, _ = classify_direction(all_stats, up_stats, down_stats)
        assert direction == "offensive_only"

    def test_regime_dependent(self):
        all_stats = {"sample_count": 200, "date_count": 10, "high_minus_low_gap": 0.1}
        up_stats = {"high_minus_low_gap": 1.5}
        down_stats = {"high_minus_low_gap": -1.5}
        direction, _ = classify_direction(all_stats, up_stats, down_stats)
        assert direction == "regime_dependent"

    def test_insufficient_samples(self):
        all_stats = {"sample_count": 30, "date_count": 3}
        direction, _ = classify_direction(all_stats, {}, {})
        assert direction == "insufficient_samples"

    def test_no_signal(self):
        all_stats = {"sample_count": 200, "date_count": 10,
                     "high_minus_low_gap": 0.3, "consistency_positive": 45}
        direction, _ = classify_direction(all_stats, {}, {})
        assert direction == "no_signal"


# ======================================================================
# Test: Risk Penalty Interpretation
# ======================================================================

class TestRiskPenalty:
    def test_positive_corr_invalid(self):
        all_stats = {"high_minus_low_gap": 1.5, "consistency_positive": 70,
                     "spearman_corr_pooled": 0.15}
        result = interpret_risk_penalty(all_stats, {}, {})
        assert result["is_risk_proxy_valid"] is False
        assert "volatility_or_elasticity" in result["interpretation"]

    def test_negative_corr_valid(self):
        all_stats = {"high_minus_low_gap": -1.0, "spearman_corr_pooled": -0.1}
        result = interpret_risk_penalty(all_stats, {}, {})
        assert result["is_risk_proxy_valid"] is True

    def test_no_signal(self):
        all_stats = {"high_minus_low_gap": 0.0, "spearman_corr_pooled": 0.0}
        result = interpret_risk_penalty(all_stats, {}, {})
        assert result["interpretation"] == "insufficient_signal"


# ======================================================================
# Test: Recommendations
# ======================================================================

class TestRecommendations:
    def test_all_not_allowed(self):
        factor_results = {
            "decision_score": {"direction": "negative_alpha"},
            "risk_penalty_score": {"direction": "positive_alpha"},
            "stock_short_score": {"direction": "no_signal"},
        }
        recs = build_recommendations(factor_results)
        assert all(not r["production_change_allowed"] for r in recs)

    def test_risk_penalty特殊处理(self):
        factor_results = {"risk_penalty_score": {"direction": "positive_alpha"}}
        recs = build_recommendations(factor_results)
        risk_rec = [r for r in recs if r["factor"] == "risk_penalty_score"][0]
        assert "split" in risk_rec["recommended_action"]
        assert risk_rec["production_change_allowed"] is False


# ======================================================================
# Test: Current Usage
# ======================================================================

class TestCurrentUsage:
    def test_known_factors(self):
        assert "subtract" in _get_current_usage("risk_penalty_score")
        assert "composite" in _get_current_usage("decision_score")
        assert "component" in _get_current_usage("stock_short_score")


# ======================================================================
# Test: Aggregate Path Resolution
# ======================================================================

class TestAggregatePathResolution:
    def test_explicit_aggregate_path_wins(self, tmp_path):
        explicit = tmp_path / "custom" / "selection_validation_aggregate.json"
        explicit.parent.mkdir(parents=True)
        explicit.write_text("{}", encoding="utf-8")

        older = tmp_path / "aggregate" / "old" / "selection_validation_aggregate.json"
        older.parent.mkdir(parents=True)
        older.write_text("{}", encoding="utf-8")

        assert _resolve_aggregate_path(tmp_path, str(explicit)) == explicit

    def test_newest_aggregate_selected_when_no_explicit_path(self, tmp_path):
        old = tmp_path / "aggregate" / "old" / "selection_validation_aggregate.json"
        new = tmp_path / "aggregate" / "new" / "selection_validation_aggregate.json"
        old.parent.mkdir(parents=True)
        new.parent.mkdir(parents=True)
        old.write_text("{}", encoding="utf-8")
        new.write_text("{}", encoding="utf-8")

        import os
        os.utime(old, (1, 1))
        os.utime(new, (2, 2))

        assert _resolve_aggregate_path(tmp_path) == new


# ======================================================================
# Test: Integration
# ======================================================================

class TestIntegration:
    def test_output_exists(self):
        path = Path("reports/selection_validation/calibration/2026-06-01_to_2026-07-07/factor_direction_calibration.json")
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "factor_results" in data
        assert "risk_penalty_interpretation" in data
        assert "calibration_recommendations" in data

    def test_all_factors_present(self):
        path = Path("reports/selection_validation/calibration/2026-06-01_to_2026-07-07/factor_direction_calibration.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        expected = ["decision_score", "stock_short_score", "risk_penalty_score",
                    "stock_trend_score", "sector_leader_score", "agent_score"]
        for f in expected:
            assert f in data["factor_results"]

    def test_no_production_changes(self):
        path = Path("reports/selection_validation/calibration/2026-06-01_to_2026-07-07/factor_direction_calibration.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert all(not r["production_change_allowed"] for r in data["calibration_recommendations"])

    def test_markdown_exists(self):
        path = Path("reports/selection_validation/calibration/2026-06-01_to_2026-07-07/factor_direction_calibration.md")
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Factor Direction Calibration" in content
        assert "Do Not Change Production Weights Yet" in content
        assert "Risk Penalty Interpretation" in content
