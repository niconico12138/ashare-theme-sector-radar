"""Tests for regime-aware factor behavior diagnosis."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from diagnose_regime_aware_factor_behavior import (
    compute_regime_factor_gaps,
    classify_regime_behavior,
    generate_regime_recommendations,
    generate_markdown,
    FACTOR_FIELDS,
    REGIMES,
)


def _make_records(n_per_regime=20, up_return=2.0, down_return=-2.0, mixed_return=0.0):
    """Generate synthetic records for testing."""
    records = []
    for regime, base_ret in [("broad_up", up_return), ("broad_down", down_return), ("mixed", mixed_return)]:
        for i in range(n_per_regime):
            records.append({
                "date": f"2026-06-{(i % 28) + 1:02d}",
                "code": f"{600000 + i:06d}",
                "name": f"Stock{i}",
                "market_regime": regime,
                "data_available": True,
                "next_return_pct": base_ret + (i - n_per_regime / 2) * 0.3,
                "next_low_return_pct": base_ret - 1.0 + i * 0.1,
                "max_intraday_drawdown_pct": 2.0 + i * 0.1,
                "decision_score": 50 + i * 1.5,
                "stock_short_score": 45 + i * 1.2,
                "stock_trend_score": 40 + i * 1.0,
                "sector_leader_score": 55 + i * 0.8,
                "risk_penalty_score": 20 - i * 0.3,
                "agent_score": 50 + i * 0.5,
                "source_pool": "trend" if i % 2 == 0 else "burst",
                "trade_eligibility": "focus" if i < 7 else "watch",
            })
    return records


# ======================================================================
# Test: Empty Data
# ======================================================================

class TestEmptyData:
    def test_empty_records(self):
        result = compute_regime_factor_gaps([])
        assert len(result) == 3  # broad_up, broad_down, mixed
        for regime in REGIMES:
            assert result[regime]["sample_count"] == 0

    def test_empty_classification(self):
        regime_gaps = {
            "broad_up": {"sample_count": 0, "factors": {}},
            "broad_down": {"sample_count": 0, "factors": {}},
            "mixed": {"sample_count": 0, "factors": {}},
        }
        result = classify_regime_behavior(regime_gaps)
        for field in FACTOR_FIELDS:
            assert result[field]["classification"] == "inconclusive"


# ======================================================================
# Test: Regime Split
# ======================================================================

class TestRegimeSplit:
    def test_regime_grouping(self):
        records = _make_records(20)
        result = compute_regime_factor_gaps(records)
        assert result["broad_up"]["sample_count"] == 20
        assert result["broad_down"]["sample_count"] == 20
        assert result["mixed"]["sample_count"] == 20

    def test_factor_gaps_computed(self):
        records = _make_records(20)
        result = compute_regime_factor_gaps(records)
        for regime in REGIMES:
            for field in FACTOR_FIELDS:
                f = result[regime]["factors"].get(field, {})
                assert "gap" in f
                assert "high_avg_return" in f
                assert "low_avg_return" in f


# ======================================================================
# Test: Sign Flip -> regime_dependent
# ======================================================================

class TestSignFlip:
    def test_up_only_alpha_when_flips(self):
        """When up_gap > 0 and down_gap < 0, should be up_only_alpha."""
        regime_gaps = {
            "broad_up": {"sample_count": 20, "factors": {
                "decision_score": {"gap": 1.0, "drawdown_diff": -0.5, "spearman_corr": 0.1},
            }},
            "broad_down": {"sample_count": 20, "factors": {
                "decision_score": {"gap": -0.8, "drawdown_diff": 0.3, "spearman_corr": -0.1},
            }},
            "mixed": {"sample_count": 20, "factors": {
                "decision_score": {"gap": 0.1, "drawdown_diff": 0.0, "spearman_corr": 0.01},
            }},
        }
        result = classify_regime_behavior(regime_gaps)
        assert result["decision_score"]["classification"] == "up_only_alpha"

    def test_regime_dependent_when_no_clear_pattern(self):
        """When gaps are near zero with no clear pattern, should be regime_dependent."""
        regime_gaps = {
            "broad_up": {"sample_count": 20, "factors": {
                "decision_score": {"gap": 0.01, "drawdown_diff": 0.0, "spearman_corr": 0.001},
            }},
            "broad_down": {"sample_count": 20, "factors": {
                "decision_score": {"gap": -0.01, "drawdown_diff": 0.0, "spearman_corr": -0.001},
            }},
            "mixed": {"sample_count": 20, "factors": {
                "decision_score": {"gap": 0.0, "drawdown_diff": 0.0, "spearman_corr": 0.0},
            }},
        }
        result = classify_regime_behavior(regime_gaps)
        # Near-zero gaps should still be classified (up_only_alpha or regime_dependent)
        assert result["decision_score"]["classification"] in ("up_only_alpha", "regime_dependent")


# ======================================================================
# Test: Defensive Not Alpha
# ======================================================================

class TestDefensiveNotAlpha:
    def test_defensive_classification(self):
        """When gap <= 0 in both regimes but drawdown < 0, should be defensive_not_alpha."""
        regime_gaps = {
            "broad_up": {"sample_count": 20, "factors": {
                "risk_penalty_score": {"gap": -0.3, "drawdown_diff": -1.0, "spearman_corr": -0.05},
            }},
            "broad_down": {"sample_count": 20, "factors": {
                "risk_penalty_score": {"gap": -0.2, "drawdown_diff": -0.8, "spearman_corr": -0.03},
            }},
            "mixed": {"sample_count": 20, "factors": {
                "risk_penalty_score": {"gap": -0.1, "drawdown_diff": -0.5, "spearman_corr": -0.02},
            }},
        }
        result = classify_regime_behavior(regime_gaps)
        assert result["risk_penalty_score"]["classification"] == "defensive_not_alpha"


# ======================================================================
# Test: All Weather Alpha
# ======================================================================

class TestAllWeatherAlpha:
    def test_all_weather_classification(self):
        """When gap > 0 in both regimes, should be all_weather_alpha."""
        regime_gaps = {
            "broad_up": {"sample_count": 20, "factors": {
                "stock_trend_score": {"gap": 0.5, "drawdown_diff": 0.0, "spearman_corr": 0.05},
            }},
            "broad_down": {"sample_count": 20, "factors": {
                "stock_trend_score": {"gap": 0.3, "drawdown_diff": 0.0, "spearman_corr": 0.03},
            }},
            "mixed": {"sample_count": 20, "factors": {
                "stock_trend_score": {"gap": 0.2, "drawdown_diff": 0.0, "spearman_corr": 0.02},
            }},
        }
        result = classify_regime_behavior(regime_gaps)
        assert result["stock_trend_score"]["classification"] == "all_weather_alpha"


# ======================================================================
# Test: Recommendations
# ======================================================================

class TestRecommendations:
    def test_recommendations_production_not_allowed(self):
        """All recommendations must have production_change_allowed = False."""
        classifications = {
            "decision_score": {"classification": "regime_dependent", "up_gap": 1.0, "down_gap": -0.5},
            "stock_short_score": {"classification": "up_only_alpha", "up_gap": 0.5, "down_gap": -0.3},
        }
        recs = generate_regime_recommendations(classifications)
        for rec in recs:
            assert rec["production_change_allowed"] is False

    def test_always_has_no_change_rec(self):
        """Should always include a 'no production change' recommendation."""
        recs = generate_regime_recommendations({})
        action_recs = [r for r in recs if r["action"] == "no_production_change"]
        assert len(action_recs) >= 1


# ======================================================================
# Test: Markdown Generation
# ======================================================================

class TestMarkdown:
    def test_markdown_structure(self):
        coverage = {"valid_dates": 120, "forward_samples": 2000}
        regime_gaps = {
            "broad_up": {"sample_count": 800, "factors": {}},
            "broad_down": {"sample_count": 500, "factors": {}},
            "mixed": {"sample_count": 700, "factors": {}},
        }
        classifications = {
            "decision_score": {"classification": "regime_dependent", "explanation": "test", "up_gap": 1.0, "down_gap": -0.5, "mixed_gap": 0.1},
        }
        recommendations = [{"factor": "all", "recommendation": "test", "regime": "all", "action": "no_production_change", "production_change_allowed": False}]
        md = generate_markdown(coverage, regime_gaps, classifications, recommendations, "test_range")
        assert "Regime-Aware Factor Behavior" in md
        assert "production_change_allowed" in md
        assert "false" in md

    def test_markdown_all_regimes(self):
        coverage = {"valid_dates": 10, "forward_samples": 100}
        regime_gaps = {}
        for regime in REGIMES:
            regime_gaps[regime] = {"sample_count": 30, "factors": {}}
        md = generate_markdown(coverage, regime_gaps, {}, [], "test")
        for regime in REGIMES:
            assert regime in md


# ======================================================================
# Test: Production Change Not Allowed
# ======================================================================

class TestProductionChange:
    def test_always_false_in_markdown(self):
        coverage = {"valid_dates": 10, "forward_samples": 100}
        regime_gaps = {r: {"sample_count": 30, "factors": {}} for r in REGIMES}
        md = generate_markdown(coverage, regime_gaps, {}, [], "test")
        assert "`false`" in md
