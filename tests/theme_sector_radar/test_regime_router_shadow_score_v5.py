"""Tests for regime router shadow score V5."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.scoring.regime_router_shadow_score_v5 import compute_regime_router_shadow_score_v5
from theme_sector_radar.scoring.decision_score import compute_decision_score


def _make_stock():
    """Create a test stock with all required fields."""
    return {
        "trend_score": 60, "burst_score": 55,
        "stock_short_score": 70, "stock_short_score_v2": 65,
        "stock_trend_score": 60, "sector_leader_score": 75,
        "agent_score": 50, "quant_score": 55,
        "final_score": 57,
        "risk_penalty_score": 40,
        "hard_risk_penalty": 10, "trade_risk_penalty": 5,
        "volatility_elasticity_score": 60, "drawdown_risk_score": 8,
        "high": 11.0, "low": 9.0, "close": 10.5,
        "change_pct": 3.0, "amount": 100_000_000, "volume": 5_000_000,
    }


# ======================================================================
# Test: Score Range
# ======================================================================

class TestScoreRange:
    def test_score_in_range_all_regimes(self):
        """Score must be 0-100 for all regimes."""
        stock = _make_stock()
        for regime in ["broad_up", "broad_down", "mixed", None]:
            result = compute_regime_router_shadow_score_v5(stock, regime=regime)
            score = result["regime_router_shadow_score_v5"]
            assert 0 <= score <= 100, f"Score {score} out of range for regime {regime}"


# ======================================================================
# Test: Regime Router Selection
# ======================================================================

class TestRegimeRouter:
    def test_broad_up_selects_bull(self):
        """broad_up should select bull profile."""
        stock = _make_stock()
        result = compute_regime_router_shadow_score_v5(stock, regime="broad_up")
        assert result["regime_router_selected_profile"] == "bull"

    def test_broad_down_selects_defensive(self):
        """broad_down should select defensive profile."""
        stock = _make_stock()
        result = compute_regime_router_shadow_score_v5(stock, regime="broad_down")
        assert result["regime_router_selected_profile"] == "defensive"

    def test_mixed_selects_blended(self):
        """mixed should select blended profile."""
        stock = _make_stock()
        result = compute_regime_router_shadow_score_v5(stock, regime="mixed")
        assert result["regime_router_selected_profile"] == "blended"

    def test_unknown_selects_blended(self):
        """Unknown regime should select blended profile."""
        stock = _make_stock()
        result = compute_regime_router_shadow_score_v5(stock, regime=None)
        assert result["regime_router_selected_profile"] == "blended"


# ======================================================================
# Test: Sub-Scores
# ======================================================================

class TestSubScores:
    def test_bull_score_present(self):
        """Bull score should be present."""
        stock = _make_stock()
        result = compute_regime_router_shadow_score_v5(stock, regime="broad_up")
        assert "bull_regime_shadow_score" in result
        assert result["bull_regime_shadow_score"] > 0

    def test_defensive_score_present(self):
        """Defensive score should be present."""
        stock = _make_stock()
        result = compute_regime_router_shadow_score_v5(stock, regime="broad_down")
        assert "defensive_shadow_score" in result
        assert result["defensive_shadow_score"] > 0


# ======================================================================
# Test: Production Decision Score Unchanged
# ======================================================================

class TestProductionUnchanged:
    def test_production_not_affected(self):
        """Production decision_score should not be affected."""
        stock = _make_stock()
        prod_result = compute_decision_score(stock)
        v5_result = compute_regime_router_shadow_score_v5(stock, regime="mixed")
        assert prod_result["decision_score"] != v5_result["regime_router_shadow_score_v5"]


# ======================================================================
# Test: V4 Not Replaced
# ======================================================================

class TestV4NotReplaced:
    def test_v4_score_present(self):
        """V4 (bull) score should still be present."""
        stock = _make_stock()
        result = compute_regime_router_shadow_score_v5(stock, regime="broad_up")
        assert "bull_regime_shadow_score" in result
        assert result["bull_regime_shadow_score"] > 0


# ======================================================================
# Test: Diagnostic Tags
# ======================================================================

class TestTags:
    def test_regime_tag_bull(self):
        """Should include bull regime tag."""
        stock = _make_stock()
        result = compute_regime_router_shadow_score_v5(stock, regime="broad_up")
        assert "v5_regime_bull" in result["regime_router_shadow_tags_v5"]

    def test_regime_tag_defensive(self):
        """Should include defensive regime tag."""
        stock = _make_stock()
        result = compute_regime_router_shadow_score_v5(stock, regime="broad_down")
        assert "v5_regime_defensive" in result["regime_router_shadow_tags_v5"]

    def test_regime_tag_blended(self):
        """Should include blended regime tag."""
        stock = _make_stock()
        result = compute_regime_router_shadow_score_v5(stock, regime="mixed")
        assert "v5_regime_blended" in result["regime_router_shadow_tags_v5"]


# ======================================================================
# Test: Breakdown Structure
# ======================================================================

class TestBreakdown:
    def test_breakdown_keys(self):
        """Breakdown should have all component keys."""
        stock = _make_stock()
        result = compute_regime_router_shadow_score_v5(stock, regime="mixed")
        breakdown = result["regime_router_shadow_breakdown_v5"]
        expected_keys = ["regime", "selected_profile", "bull_score", "defensive_score", "v5_score"]
        for key in expected_keys:
            assert key in breakdown, f"Missing key: {key}"
