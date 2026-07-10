"""Tests for defensive shadow score."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.scoring.defensive_shadow_score import compute_defensive_shadow_score


def _make_stock():
    """Create a test stock with all required fields."""
    return {
        "risk_penalty_score": 40,
        "hard_risk_penalty": 10,
        "trade_risk_penalty": 5,
        "drawdown_risk_score": 8,
        "volatility_elasticity_score": 60,
        "sector_leader_score": 70,
        "stock_short_score_v2": 55,
        "stock_short_score": 50,
        "quant_score": 55,
        "final_score": 57,
        "high": 11.0,
        "low": 9.0,
        "close": 10.5,
        "change_pct": 3.0,
        "amount": 100_000_000,
        "volume": 5_000_000,
    }


# ======================================================================
# Test: Score Range 0-100
# ======================================================================

class TestScoreRange:
    def test_score_in_range(self):
        """Score must be 0-100."""
        stock = _make_stock()
        result = compute_defensive_shadow_score(stock)
        assert 0 <= result["defensive_shadow_score"] <= 100

    def test_score_with_high_risk(self):
        """High risk should still be in range."""
        stock = _make_stock()
        stock["hard_risk_penalty"] = 50
        stock["trade_risk_penalty"] = 40
        stock["drawdown_risk_score"] = 50
        result = compute_defensive_shadow_score(stock)
        assert 0 <= result["defensive_shadow_score"] <= 100


# ======================================================================
# Test: Risk Penalty Score Positive Contribution
# ======================================================================

class TestRiskPenaltyPositive:
    def test_higher_risk_penalty_higher_score(self):
        """Higher risk_penalty_score should give higher defensive score (all_weather_alpha)."""
        stock_low = _make_stock()
        stock_low["risk_penalty_score"] = 10
        stock_high = _make_stock()
        stock_high["risk_penalty_score"] = 50

        result_low = compute_defensive_shadow_score(stock_low)
        result_high = compute_defensive_shadow_score(stock_high)

        assert result_high["defensive_shadow_score"] > result_low["defensive_shadow_score"]


# ======================================================================
# Test: Risk Deductions
# ======================================================================

class TestRiskDeductions:
    def test_hard_risk_deducts(self):
        """Higher hard_risk should reduce score."""
        stock_low = _make_stock()
        stock_low["hard_risk_penalty"] = 5
        stock_high = _make_stock()
        stock_high["hard_risk_penalty"] = 40

        result_low = compute_defensive_shadow_score(stock_low)
        result_high = compute_defensive_shadow_score(stock_high)

        assert result_low["defensive_shadow_score"] > result_high["defensive_shadow_score"]

    def test_trade_risk_deducts(self):
        """Higher trade_risk should reduce score."""
        stock_low = _make_stock()
        stock_low["trade_risk_penalty"] = 3
        stock_high = _make_stock()
        stock_high["trade_risk_penalty"] = 30

        result_low = compute_defensive_shadow_score(stock_low)
        result_high = compute_defensive_shadow_score(stock_high)

        assert result_low["defensive_shadow_score"] > result_high["defensive_shadow_score"]

    def test_drawdown_risk_deducts(self):
        """Higher drawdown_risk should reduce score."""
        stock_low = _make_stock()
        stock_low["drawdown_risk_score"] = 5
        stock_high = _make_stock()
        stock_high["drawdown_risk_score"] = 40

        result_low = compute_defensive_shadow_score(stock_low)
        result_high = compute_defensive_shadow_score(stock_high)

        assert result_low["defensive_shadow_score"] > result_high["defensive_shadow_score"]


# ======================================================================
# Test: Elasticity Penalty
# ======================================================================

class TestElasticityPenalty:
    def test_high_elasticity_penalized(self):
        """High elasticity should be penalized in defensive score."""
        stock_low = _make_stock()
        stock_low["volatility_elasticity_score"] = 40
        stock_high = _make_stock()
        stock_high["volatility_elasticity_score"] = 80

        result_low = compute_defensive_shadow_score(stock_low)
        result_high = compute_defensive_shadow_score(stock_high)

        # High elasticity should be penalized, so low elasticity score is better
        assert result_low["defensive_shadow_score"] > result_high["defensive_shadow_score"]


# ======================================================================
# Test: Close Position Score
# ======================================================================

class TestClosePosition:
    def test_close_at_high_improves_score(self):
        """Close at high should improve defensive score."""
        stock = _make_stock()
        stock["high"] = 11.0
        stock["low"] = 9.0
        stock["close"] = 11.0  # Close at high
        result = compute_defensive_shadow_score(stock)
        assert result["defensive_shadow_breakdown"]["close_position_score"] > 15

    def test_close_at_low_reduces_score(self):
        """Close at low should reduce defensive score."""
        stock = _make_stock()
        stock["high"] = 11.0
        stock["low"] = 9.0
        stock["close"] = 9.0  # Close at low
        result = compute_defensive_shadow_score(stock)
        assert result["defensive_shadow_breakdown"]["close_position_score"] < 5


# ======================================================================
# Test: Diagnostic Tags
# ======================================================================

class TestTags:
    def test_high_risk_tags(self):
        """High risk should produce diagnostic tags."""
        stock = _make_stock()
        stock["hard_risk_penalty"] = 30
        stock["trade_risk_penalty"] = 20
        stock["drawdown_risk_score"] = 25
        stock["volatility_elasticity_score"] = 80
        stock["sector_leader_score"] = 20
        result = compute_defensive_shadow_score(stock)
        tags = result["defensive_shadow_tags"]
        assert "defensive_high_hard_risk" in tags
        assert "defensive_high_trade_risk" in tags
        assert "defensive_high_drawdown_risk" in tags
        assert "defensive_high_elasticity_penalty" in tags
        assert "defensive_weak_leader" in tags


# ======================================================================
# Test: Breakdown Structure
# ======================================================================

class TestBreakdown:
    def test_breakdown_keys(self):
        """Breakdown should have all component keys."""
        stock = _make_stock()
        result = compute_defensive_shadow_score(stock)
        breakdown = result["defensive_shadow_breakdown"]
        expected_keys = [
            "risk_penalty_bonus", "hard_risk_deduction", "trade_risk_deduction",
            "drawdown_deduction", "close_position_score", "short_score_component",
            "elasticity_penalty", "leader_penalty", "data_quality_penalty", "total",
        ]
        for key in expected_keys:
            assert key in breakdown, f"Missing key: {key}"


# ======================================================================
# Test: Missing Data
# ======================================================================

class TestMissingData:
    def test_empty_stock_no_crash(self):
        """Empty stock dict should not crash."""
        result = compute_defensive_shadow_score({})
        assert 0 <= result["defensive_shadow_score"] <= 100

    def test_missing_ohlc_no_crash(self):
        """Missing OHLC should not crash."""
        stock = {"risk_penalty_score": 40, "quant_score": 55}
        result = compute_defensive_shadow_score(stock)
        assert 0 <= result["defensive_shadow_score"] <= 100
