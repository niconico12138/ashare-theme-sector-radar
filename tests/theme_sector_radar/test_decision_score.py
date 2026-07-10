"""Tests for decision_score module."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "theme_sector_radar" / "scoring"))

from decision_score import compute_decision_score


class TestComputeDecisionScore:
    """Test compute_decision_score function."""

    def test_basic_decision_score(self):
        """Basic decision score with all fields present."""
        stock = {
            "sector_trend_score": 70.0,
            "sector_burst_score": 65.0,
            "stock_short_score": 75.0,
            "stock_trend_score": 70.0,
            "sector_leader_score": 80.0,
            "agent_score": 60.0,
            "risk_penalty_score": 5.0,
        }
        result = compute_decision_score(stock)
        assert "decision_score" in result
        assert "decision_breakdown" in result
        assert 0 <= result["decision_score"] <= 100

        # Verify weighted sum
        expected = (
            70 * 0.15 + 65 * 0.15 + 75 * 0.25
            + 70 * 0.20 + 80 * 0.15 + 60 * 0.10
            - 5
        )
        assert abs(result["decision_score"] - expected) < 0.1

    def test_agent_score_missing_neutral(self):
        """Missing agent_score should use neutral 50 and mark in breakdown."""
        stock = {
            "sector_trend_score": 70.0,
            "sector_burst_score": 65.0,
            "stock_short_score": 75.0,
            "stock_trend_score": 70.0,
            "sector_leader_score": 80.0,
            "risk_penalty_score": 0,
        }
        result = compute_decision_score(stock)
        breakdown = result["decision_breakdown"]
        assert breakdown["agent_score"] == 50.0
        assert breakdown["agent_score_missing_neutral"] is True

    def test_agent_score_present_not_neutral(self):
        """Present agent_score should not mark as missing."""
        stock = {
            "agent_score": 70.0,
            "risk_penalty_score": 0,
        }
        result = compute_decision_score(stock)
        breakdown = result["decision_breakdown"]
        assert breakdown["agent_score"] == 70.0
        assert breakdown["agent_score_missing_neutral"] is False

    def test_field_name_aliases(self):
        """Should work with both trend_score and sector_trend_score."""
        stock1 = {
            "sector_trend_score": 70.0,
            "sector_burst_score": 65.0,
            "risk_penalty_score": 0,
        }
        stock2 = {
            "trend_score": 70.0,
            "burst_score": 65.0,
            "risk_penalty_score": 0,
        }
        r1 = compute_decision_score(stock1)
        r2 = compute_decision_score(stock2)
        # Should produce same scores when values are the same
        assert abs(r1["decision_score"] - r2["decision_score"]) < 0.1

    def test_risk_penalty_reduces_score(self):
        """Risk penalty should reduce decision score."""
        base_stock = {
            "sector_trend_score": 70.0,
            "sector_burst_score": 65.0,
            "stock_short_score": 75.0,
            "stock_trend_score": 70.0,
            "sector_leader_score": 80.0,
            "agent_score": 60.0,
        }
        no_risk = {**base_stock, "risk_penalty_score": 0}
        with_risk = {**base_stock, "risk_penalty_score": 20}

        r1 = compute_decision_score(no_risk)
        r2 = compute_decision_score(with_risk)
        assert r1["decision_score"] > r2["decision_score"]

    def test_all_defaults(self):
        """Stock with no scoring fields should use defaults."""
        stock = {"risk_penalty_score": 0}
        result = compute_decision_score(stock)
        # All defaults = 50, so weighted sum = 50, minus 0 risk
        assert result["decision_score"] == 50.0

    def test_score_range_bounds(self):
        """Score should always be 0-100."""
        # Very high values
        stock = {
            "sector_trend_score": 100,
            "sector_burst_score": 100,
            "stock_short_score": 100,
            "stock_trend_score": 100,
            "sector_leader_score": 100,
            "agent_score": 100,
            "risk_penalty_score": 0,
        }
        result = compute_decision_score(stock)
        assert result["decision_score"] <= 100

        # Very low values with high risk
        stock = {
            "sector_trend_score": 0,
            "sector_burst_score": 0,
            "stock_short_score": 0,
            "stock_trend_score": 0,
            "sector_leader_score": 0,
            "agent_score": 0,
            "risk_penalty_score": 50,
        }
        result = compute_decision_score(stock)
        assert result["decision_score"] >= 0

    def test_breakdown_contains_all_components(self):
        """Breakdown should contain all component scores."""
        stock = {
            "sector_trend_score": 70.0,
            "sector_burst_score": 65.0,
            "stock_short_score": 75.0,
            "stock_trend_score": 70.0,
            "sector_leader_score": 80.0,
            "agent_score": 60.0,
            "risk_penalty_score": 5.0,
        }
        result = compute_decision_score(stock)
        breakdown = result["decision_breakdown"]
        required_keys = [
            "sector_trend_score", "sector_burst_score", "stock_short_score",
            "stock_trend_score", "sector_leader_score", "agent_score",
            "risk_penalty_score", "weighted_sum", "total",
        ]
        for key in required_keys:
            assert key in breakdown, f"Missing key: {key}"

    def test_empty_stock_dict(self):
        """Empty stock dict should not crash."""
        result = compute_decision_score({})
        assert 0 <= result["decision_score"] <= 100
        assert isinstance(result["decision_breakdown"], dict)
