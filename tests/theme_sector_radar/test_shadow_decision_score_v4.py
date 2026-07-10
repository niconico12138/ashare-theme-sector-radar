"""Tests for shadow decision score v4."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.scoring.shadow_decision_score_v4 import (
    compute_shadow_decision_score_v4,
    REGIME_PROFILES,
)
from theme_sector_radar.scoring.decision_score import compute_decision_score
from theme_sector_radar.scoring.shadow_decision_score_v3 import compute_shadow_decision_score_v3


def _make_stock():
    """Create a test stock with all required fields."""
    return {
        "trend_score": 60, "burst_score": 55,
        "stock_short_score": 70, "stock_short_score_v2": 65,
        "stock_trend_score": 60, "sector_leader_score": 75,
        "agent_score": 50, "quant_score": 55,
        "hard_risk_penalty": 10, "trade_risk_penalty": 5,
        "volatility_elasticity_score": 60, "drawdown_risk_score": 8,
    }


# ======================================================================
# Test: Score Range
# ======================================================================

class TestScoreRange:
    def test_score_in_range_all_regimes(self):
        """Score must be 0-100 for all regimes."""
        stock = _make_stock()
        for regime in ["broad_up", "broad_down", "mixed", None]:
            result = compute_shadow_decision_score_v4(stock, regime=regime)
            score = result["shadow_decision_score_v4"]
            assert 0 <= score <= 100, f"Score {score} out of range for regime {regime}"

    def test_score_with_zero_risk(self):
        """Score with zero risk should be higher."""
        stock = _make_stock()
        stock["hard_risk_penalty"] = 0
        stock["trade_risk_penalty"] = 0
        stock["drawdown_risk_score"] = 0
        result = compute_shadow_decision_score_v4(stock, regime="broad_up")
        assert result["shadow_decision_score_v4"] > 50

    def test_score_with_high_risk(self):
        """Score with high risk should be lower."""
        stock = _make_stock()
        stock["hard_risk_penalty"] = 40
        stock["trade_risk_penalty"] = 30
        stock["drawdown_risk_score"] = 20
        result = compute_shadow_decision_score_v4(stock, regime="broad_down")
        assert result["shadow_decision_score_v4"] < 50


# ======================================================================
# Test: Regime Profiles
# ======================================================================

class TestRegimeProfiles:
    def test_broad_up_higher_trend_weight(self):
        """broad_up should have higher trend weight than broad_down."""
        up_profile = REGIME_PROFILES["broad_up"]
        down_profile = REGIME_PROFILES["broad_down"]
        assert up_profile["alpha_weights"]["sector_trend"] > down_profile["alpha_weights"]["sector_trend"]
        assert up_profile["alpha_weights"]["stock_trend"] > down_profile["alpha_weights"]["stock_trend"]

    def test_broad_down_higher_risk_weight(self):
        """broad_down should have higher risk weights than broad_up."""
        up_profile = REGIME_PROFILES["broad_up"]
        down_profile = REGIME_PROFILES["broad_down"]
        assert down_profile["risk_weights"]["hard_risk"] > up_profile["risk_weights"]["hard_risk"]
        assert down_profile["risk_weights"]["trade_risk"] > up_profile["risk_weights"]["trade_risk"]

    def test_broad_up_higher_elasticity(self):
        """broad_up should have higher elasticity weight."""
        up_profile = REGIME_PROFILES["broad_up"]
        down_profile = REGIME_PROFILES["broad_down"]
        assert up_profile["elasticity_weight"] > down_profile["elasticity_weight"]

    def test_all_profiles_complete(self):
        """All profiles should have required keys."""
        for regime, profile in REGIME_PROFILES.items():
            assert "name" in profile
            assert "alpha_weights" in profile
            assert "elasticity_weight" in profile
            assert "risk_weights" in profile


# ======================================================================
# Test: Regime-Aware Behavior
# ======================================================================

class TestRegimeAware:
    def test_broad_up_gives_different_score(self):
        """Different regimes should give different scores."""
        stock = _make_stock()
        result_up = compute_shadow_decision_score_v4(stock, regime="broad_up")
        result_down = compute_shadow_decision_score_v4(stock, regime="broad_down")
        assert result_up["shadow_decision_score_v4"] != result_down["shadow_decision_score_v4"]

    def test_broad_up_with_high_trend(self):
        """High trend stock should score better in broad_up."""
        stock = _make_stock()
        stock["stock_trend_score"] = 90
        stock["volatility_elasticity_score"] = 80
        result_up = compute_shadow_decision_score_v4(stock, regime="broad_up")
        result_down = compute_shadow_decision_score_v4(stock, regime="broad_down")
        # High trend + high elasticity should benefit from broad_up profile
        assert result_up["shadow_decision_score_v4"] > result_down["shadow_decision_score_v4"]

    def test_broad_down_with_high_risk(self):
        """High risk stock should score worse in broad_down."""
        stock = _make_stock()
        stock["hard_risk_penalty"] = 30
        stock["trade_risk_penalty"] = 20
        result_up = compute_shadow_decision_score_v4(stock, regime="broad_up")
        result_down = compute_shadow_decision_score_v4(stock, regime="broad_down")
        # High risk should be penalized more in broad_down
        assert result_down["shadow_decision_score_v4"] < result_up["shadow_decision_score_v4"]

    def test_default_regime(self):
        """Default regime should work without error."""
        stock = _make_stock()
        result = compute_shadow_decision_score_v4(stock, regime=None)
        assert result["shadow_decision_v4_regime_profile"] == "default"


# ======================================================================
# Test: V2 Short Score Integration
# ======================================================================

class TestV2ShortScore:
    def test_uses_v2_when_available(self):
        """Should use stock_short_score_v2 when available."""
        stock = _make_stock()
        result = compute_shadow_decision_score_v4(stock, regime="mixed")
        breakdown = result["shadow_decision_breakdown_v4"]
        assert breakdown["stock_short_score_source"] == "v2"

    def test_fallback_to_v1(self):
        """Should fallback to v1 when v2 is 0."""
        stock = _make_stock()
        stock["stock_short_score_v2"] = 0
        result = compute_shadow_decision_score_v4(stock, regime="mixed")
        breakdown = result["shadow_decision_breakdown_v4"]
        assert breakdown["stock_short_score_source"] == "v1_fallback"


# ======================================================================
# Test: Production Decision Score Unchanged
# ======================================================================

class TestProductionUnchanged:
    def test_production_not_affected(self):
        """Production decision_score should not be affected by v4."""
        stock = _make_stock()
        stock["risk_penalty_score"] = 10
        prod_result = compute_decision_score(stock)
        v4_result = compute_shadow_decision_score_v4(stock, regime="mixed")
        assert prod_result["decision_score"] != v4_result["shadow_decision_score_v4"]


# ======================================================================
# Test: V4 Does Not Replace V3
# ======================================================================

class TestV3NotReplaced:
    def test_v3_still_works(self):
        """V3 should still work independently."""
        stock = _make_stock()
        v3_result = compute_shadow_decision_score_v3(stock)
        v4_result = compute_shadow_decision_score_v4(stock, regime="mixed")
        # Both should produce valid scores
        assert 0 <= v3_result["shadow_decision_score_v3"] <= 100
        assert 0 <= v4_result["shadow_decision_score_v4"] <= 100


# ======================================================================
# Test: Diagnostic Tags
# ======================================================================

class TestTags:
    def test_regime_tag(self):
        """Should include regime tag."""
        stock = _make_stock()
        result = compute_shadow_decision_score_v4(stock, regime="broad_up")
        assert "v4_regime_broad_up" in result["shadow_decision_v4_tags"]

    def test_high_risk_tags(self):
        """High risk should produce diagnostic tags."""
        stock = _make_stock()
        stock["hard_risk_penalty"] = 30
        stock["trade_risk_penalty"] = 20
        stock["drawdown_risk_score"] = 25
        result = compute_shadow_decision_score_v4(stock, regime="mixed")
        tags = result["shadow_decision_v4_tags"]
        assert "v4_high_hard_risk" in tags
        assert "v4_high_trade_risk" in tags
        assert "v4_high_drawdown_risk" in tags


# ======================================================================
# Test: Breakdown Structure
# ======================================================================

class TestBreakdown:
    def test_breakdown_keys(self):
        """Breakdown should have all component keys."""
        stock = _make_stock()
        result = compute_shadow_decision_score_v4(stock, regime="mixed")
        breakdown = result["shadow_decision_breakdown_v4"]
        expected_keys = [
            "regime_profile", "sector_trend_score", "sector_burst_score",
            "stock_short_score", "stock_trend_score", "sector_leader_score",
            "quant_score", "agent_score", "hard_risk_penalty", "trade_risk_penalty",
            "volatility_elasticity_score", "drawdown_risk_score",
            "alpha_component", "elasticity_bonus", "risk_component", "total",
        ]
        for key in expected_keys:
            assert key in breakdown, f"Missing key: {key}"
