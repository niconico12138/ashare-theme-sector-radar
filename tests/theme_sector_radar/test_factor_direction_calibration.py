"""Tests for factor direction calibration."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from calibrate_factor_direction import (
    CALIBRATION_FACTORS,
    compute_factor_stats,
    classify_direction,
    interpret_risk_penalty,
    build_recommendations,
    propose_next_experiment,
    generate_markdown,
    _split_by_percentile,
    _get_current_usage,
    _resolve_aggregate_path,
)
from tests.theme_sector_radar.report_fixture_factory import write_json


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

@pytest.fixture
def calibration_output_paths(tmp_path):
    date_regimes = [
        ("2026-07-01", "broad_up"),
        ("2026-07-02", "broad_down"),
        ("2026-07-03", "mixed"),
    ]
    records = []
    for date, regime in date_regimes:
        for rank in range(10):
            record = {
                "date": date,
                "code": f"{date[-2:]}-{rank}",
                "market_regime": regime,
                "data_available": True,
                "next_return_pct": float(rank - 4.5),
            }
            record.update({factor: float(rank) for factor in CALIBRATION_FACTORS})
            record["risk_penalty_score"] = float(9 - rank)
            records.append(record)

    factor_results = {}
    for factor in CALIBRATION_FACTORS:
        all_stats = compute_factor_stats(records, factor)
        up_stats = compute_factor_stats(records, factor, regime="broad_up")
        down_stats = compute_factor_stats(records, factor, regime="broad_down")
        mixed_stats = compute_factor_stats(records, factor, regime="mixed")
        direction, confidence = classify_direction(all_stats, up_stats, down_stats)
        factor_results[factor] = {
            "all": all_stats,
            "broad_up": up_stats,
            "broad_down": down_stats,
            "mixed": mixed_stats,
            "direction": direction,
            "confidence": confidence,
        }

    risk_interp = interpret_risk_penalty(
        factor_results["risk_penalty_score"]["all"],
        factor_results["risk_penalty_score"]["broad_up"],
        factor_results["risk_penalty_score"]["broad_down"],
    )
    recommendations = build_recommendations(factor_results)
    next_experiment = propose_next_experiment(factor_results, risk_interp)
    coverage = {
        "valid_date_count": len(date_regimes),
        "total_records": len(records),
        "records_with_data": len(records),
    }
    output = {
        "as_of": "synthetic-test-window",
        "coverage": coverage,
        "factor_results": factor_results,
        "risk_penalty_interpretation": risk_interp,
        "calibration_recommendations": recommendations,
        "next_experiment_proposal": next_experiment,
    }

    output_dir = tmp_path / "calibration"
    json_path = write_json(output_dir / "factor_direction_calibration.json", output)
    markdown_path = output_dir / "factor_direction_calibration.md"
    markdown_path.write_text(
        generate_markdown(
            factor_results,
            risk_interp,
            recommendations,
            next_experiment,
            coverage,
        ),
        encoding="utf-8",
    )
    return {"json": json_path, "markdown": markdown_path}

class TestIntegration:
    def test_output_exists(self, calibration_output_paths):
        path = calibration_output_paths["json"]
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "factor_results" in data
        assert "risk_penalty_interpretation" in data
        assert "calibration_recommendations" in data

    def test_all_factors_present(self, calibration_output_paths):
        path = calibration_output_paths["json"]
        data = json.loads(path.read_text(encoding="utf-8"))
        expected = ["decision_score", "stock_short_score", "risk_penalty_score",
                    "stock_trend_score", "sector_leader_score", "agent_score"]
        for f in expected:
            assert f in data["factor_results"]
        expected_result_keys = {
            "all",
            "broad_up",
            "broad_down",
            "mixed",
            "direction",
            "confidence",
        }
        assert all(
            set(result) == expected_result_keys
            for result in data["factor_results"].values()
        )
        decision_result = data["factor_results"]["decision_score"]
        assert decision_result["all"]["sample_count"] == 30

    def test_no_production_changes(self, calibration_output_paths):
        path = calibration_output_paths["json"]
        data = json.loads(path.read_text(encoding="utf-8"))
        assert all(not r["production_change_allowed"] for r in data["calibration_recommendations"])

    def test_markdown_exists(self, calibration_output_paths):
        path = calibration_output_paths["markdown"]
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        data = json.loads(
            calibration_output_paths["json"].read_text(encoding="utf-8")
        )
        assert "Factor Direction Calibration" in content
        assert "Do Not Change Production Weights Yet" in content
        assert "Risk Penalty Interpretation" in content
        assert data["factor_results"]["decision_score"]["direction"] in content
        assert "Records with forward data: 30" in content
        decision_line = next(
            line for line in content.splitlines()
            if line.startswith("| decision_score ")
        )
        factor, sample_count, date_count, *_ = decision_line.strip("|").split()
        assert (factor, sample_count, date_count) == ("decision_score", "30", "3")
