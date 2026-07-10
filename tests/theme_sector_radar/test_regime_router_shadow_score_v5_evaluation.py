"""Tests for regime router shadow score V5 evaluation."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from evaluate_regime_router_shadow_score_v5 import (
    compute_score_comparison,
    compute_window_comparisons,
    compute_regime_comparisons,
    generate_markdown,
    check_improvement,
    _comparison_table,
    REGIMES,
    WINDOWS,
    run_sample_evaluation,
)


def _make_records(n=30, regime="broad_up", base_return=1.0):
    """Generate synthetic records for testing."""
    records = []
    for i in range(n):
        records.append({
            "date": f"2026-06-{(i % 28) + 1:02d}",
            "code": f"{600000 + i:06d}",
            "name": f"Stock{i}",
            "market_regime": regime,
            "data_available": True,
            "next_return_pct": base_return + (i - n / 2) * 0.2,
            "decision_score": 50 + i * 1.5,
            "shadow_decision_score_v4": 55 + i * 1.2,
            "defensive_shadow_score": 48 + i * 1.0,
            "regime_router_shadow_score_v5": 52 + i * 1.1,
            "regime_router_selected_profile": "blended",
            "stock_short_score": 45 + i * 1.0,
            "stock_short_score_v2": 48 + i * 1.1,
        })
    return records


# ======================================================================

def test_run_sample_evaluation_writes_shadow_v5_outputs(tmp_path):
    output = run_sample_evaluation(tmp_path)

    assert output["sample_mode"] is True
    assert output["production_change_allowed"] is False
    assert output["promotion_gate"] == "review_ready_shadow_only"
    assert output["coverage"]["forward_samples"] >= 20
    assert (tmp_path / "regime_router_shadow_score_v5_evaluation.json").exists()
    assert (tmp_path / "regime_router_shadow_score_v5_evaluation.md").exists()
# Test: Empty Data
# ======================================================================

class TestEmptyData:
    def test_empty_comparison(self):
        result = compute_score_comparison([], "empty")
        assert "error" in result

    def test_insufficient_samples(self):
        records = _make_records(5)
        result = compute_score_comparison(records, "small")
        assert result["sample_count"] == 5


# ======================================================================
# Test: Score Comparison
# ======================================================================

class TestScoreComparison:
    def test_comparison_structure(self):
        records = _make_records(30)
        result = compute_score_comparison(records, "test")
        assert "production" in result
        assert "shadow_v4" in result
        assert "defensive" in result
        assert "regime_router_v5" in result

    def test_comparison_has_metrics(self):
        records = _make_records(30)
        result = compute_score_comparison(records, "test")
        for key in ["production", "shadow_v4", "defensive", "regime_router_v5"]:
            data = result[key]
            assert "top_bottom_gap" in data
            assert "hit_rate_diff" in data
            assert "spearman_corr" in data
            assert "consistency" in data


# ======================================================================
# Test: Window Comparisons
# ======================================================================

class TestWindowComparisons:
    def test_window_structure(self):
        records = _make_records(150)
        result = compute_window_comparisons(records)
        assert "20d" in result
        assert "40d" in result

    def test_insufficient_window(self):
        records = _make_records(10)
        result = compute_window_comparisons(records)
        assert "error" in result.get("20d", {})


# ======================================================================
# Test: Regime Comparisons
# ======================================================================

class TestRegimeComparisons:
    def test_regime_structure(self):
        records = _make_records(30, "broad_up") + _make_records(30, "broad_down") + _make_records(30, "mixed")
        result = compute_regime_comparisons(records)
        assert "broad_up" in result
        assert "broad_down" in result
        assert "mixed" in result


# ======================================================================
# Test: Improvement Check
# ======================================================================

class TestImprovementCheck:
    def test_improved_when_better_gap(self):
        overall = {
            "production": {"top_bottom_gap": 0.5, "consistency": 50.0},
            "regime_router_v5": {"top_bottom_gap": 0.8, "consistency": 50.0},
        }
        assert check_improvement(overall, "production", "regime_router_v5") is True

    def test_not_improved_when_worse(self):
        overall = {
            "production": {"top_bottom_gap": 0.8, "consistency": 55.0},
            "regime_router_v5": {"top_bottom_gap": 0.5, "consistency": 50.0},
        }
        assert check_improvement(overall, "production", "regime_router_v5") is False


# ======================================================================
# Test: Markdown Generation
# ======================================================================

class TestMarkdown:
    def test_markdown_structure(self):
        coverage = {"valid_dates": 120, "forward_samples": 2000}
        overall = {
            "sample_count": 2000,
            "production": {"top_bottom_gap": 0.5, "hit_rate_diff": 5.0, "spearman_corr": 0.03, "consistency": 55.0},
            "shadow_v4": {"top_bottom_gap": 0.6, "hit_rate_diff": 6.0, "spearman_corr": 0.04, "consistency": 56.0},
            "defensive": {"top_bottom_gap": 0.4, "hit_rate_diff": 4.0, "spearman_corr": 0.02, "consistency": 54.0},
            "regime_router_v5": {"top_bottom_gap": 0.7, "hit_rate_diff": 7.0, "spearman_corr": 0.05, "consistency": 57.0},
        }
        windows = {"20d": overall, "40d": overall}
        regimes = {"broad_up": overall, "broad_down": overall, "mixed": overall}
        v5_dist = {"min": 20, "max": 80, "mean": 50, "spread": 60, "unique_count": 50}
        bucket_mono = {"bucket_stats": {}, "monotonicity": "inconclusive"}

        md = generate_markdown(coverage, overall, windows, regimes, v5_dist, bucket_mono, "test_range")
        assert "Regime Router Shadow Score V5 Evaluation" in md
        assert "production_change_allowed" in md
        assert "false" in md


# ======================================================================
# Test: Production Change Not Allowed
# ======================================================================

class TestProductionChange:
    def test_always_false_in_markdown(self):
        coverage = {"valid_dates": 10, "forward_samples": 100}
        overall = {"sample_count": 100, "production": {}, "shadow_v4": {}, "defensive": {}, "regime_router_v5": {}}
        md = generate_markdown(coverage, overall, {}, {}, {}, {}, "test")
        assert "`false`" in md
        assert "production_change_allowed" in md



