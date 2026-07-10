"""Tests for shadow decision score v3."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.scoring.shadow_decision_score_v3 import compute_shadow_decision_score_v3
from theme_sector_radar.scoring.decision_score import compute_decision_score


# ======================================================================
# Test: Score Range
# ======================================================================

class TestScoreRange:
    def test_score_in_range(self):
        """Score must be 0-100."""
        stock = {
            "trend_score": 60, "burst_score": 55,
            "stock_short_score": 70, "stock_short_score_v2": 65,
            "stock_trend_score": 60, "sector_leader_score": 75,
            "agent_score": 50, "quant_score": 55,
            "hard_risk_penalty": 10, "trade_risk_penalty": 5,
            "volatility_elasticity_score": 60, "drawdown_risk_score": 8,
        }
        result = compute_shadow_decision_score_v3(stock)
        assert 0 <= result["shadow_decision_score_v3"] <= 100

    def test_score_with_zero_risk(self):
        """Score with zero risk should be higher."""
        stock = {
            "trend_score": 60, "burst_score": 55,
            "stock_short_score": 70, "stock_short_score_v2": 65,
            "stock_trend_score": 60, "sector_leader_score": 75,
            "agent_score": 50, "quant_score": 55,
            "hard_risk_penalty": 0, "trade_risk_penalty": 0,
            "volatility_elasticity_score": 50, "drawdown_risk_score": 0,
        }
        result = compute_shadow_decision_score_v3(stock)
        assert result["shadow_decision_score_v3"] > 50

    def test_score_with_high_risk(self):
        """Score with high risk should be lower."""
        stock = {
            "trend_score": 60, "burst_score": 55,
            "stock_short_score": 70, "stock_short_score_v2": 65,
            "stock_trend_score": 60, "sector_leader_score": 75,
            "agent_score": 50, "quant_score": 55,
            "hard_risk_penalty": 40, "trade_risk_penalty": 30,
            "volatility_elasticity_score": 50, "drawdown_risk_score": 20,
        }
        result = compute_shadow_decision_score_v3(stock)
        assert result["shadow_decision_score_v3"] < 50


# ======================================================================
# Test: V2 Short Score Integration
# ======================================================================

class TestV2ShortScore:
    def test_uses_v2_when_available(self):
        """Should use stock_short_score_v2 when available."""
        stock = {
            "stock_short_score": 50, "stock_short_score_v2": 75,
            "trend_score": 60, "burst_score": 55,
            "stock_trend_score": 60, "sector_leader_score": 75,
            "agent_score": 50, "quant_score": 55,
            "hard_risk_penalty": 5, "trade_risk_penalty": 3,
            "volatility_elasticity_score": 55, "drawdown_risk_score": 5,
        }
        result = compute_shadow_decision_score_v3(stock)
        breakdown = result["shadow_decision_breakdown_v3"]
        assert breakdown["stock_short_score_source"] == "v2"
        assert breakdown["stock_short_score"] == 75.0

    def test_fallback_to_v1(self):
        """Should fallback to v1 when v2 is 0."""
        stock = {
            "stock_short_score": 50,
            "trend_score": 60, "burst_score": 55,
            "stock_trend_score": 60, "sector_leader_score": 75,
            "agent_score": 50, "quant_score": 55,
            "hard_risk_penalty": 5, "trade_risk_penalty": 3,
            "volatility_elasticity_score": 55, "drawdown_risk_score": 5,
        }
        result = compute_shadow_decision_score_v3(stock)
        breakdown = result["shadow_decision_breakdown_v3"]
        assert breakdown["stock_short_score_source"] == "v1_fallback"
        assert "v3_short_score_v1_fallback" in result["shadow_decision_v3_tags"]


# ======================================================================
# Test: Elasticity as Opportunity
# ======================================================================

class TestElasticity:
    def test_elasticity_not_penalty(self):
        """High elasticity should add bonus, not penalty."""
        stock_low = {
            "trend_score": 60, "burst_score": 55,
            "stock_short_score": 70, "stock_short_score_v2": 65,
            "stock_trend_score": 60, "sector_leader_score": 75,
            "agent_score": 50, "quant_score": 55,
            "hard_risk_penalty": 5, "trade_risk_penalty": 3,
            "volatility_elasticity_score": 30, "drawdown_risk_score": 5,
        }
        stock_high = dict(stock_low)
        stock_high["volatility_elasticity_score"] = 80

        result_low = compute_shadow_decision_score_v3(stock_low)
        result_high = compute_shadow_decision_score_v3(stock_high)

        # High elasticity should give higher score
        assert result_high["shadow_decision_score_v3"] > result_low["shadow_decision_score_v3"]
        assert result_high["shadow_decision_breakdown_v3"]["elasticity_bonus"] > 0


# ======================================================================
# Test: Hard/Trade Risk Deduction
# ======================================================================

class TestRiskDeduction:
    def test_hard_risk_deducts(self):
        """Higher hard_risk should reduce score."""
        stock_low = {
            "trend_score": 60, "burst_score": 55,
            "stock_short_score": 70, "stock_short_score_v2": 65,
            "stock_trend_score": 60, "sector_leader_score": 75,
            "agent_score": 50, "quant_score": 55,
            "hard_risk_penalty": 5, "trade_risk_penalty": 3,
            "volatility_elasticity_score": 55, "drawdown_risk_score": 5,
        }
        stock_high = dict(stock_low)
        stock_high["hard_risk_penalty"] = 40

        result_low = compute_shadow_decision_score_v3(stock_low)
        result_high = compute_shadow_decision_score_v3(stock_high)

        assert result_low["shadow_decision_score_v3"] > result_high["shadow_decision_score_v3"]

    def test_trade_risk_deducts(self):
        """Higher trade_risk should reduce score."""
        stock_low = {
            "trend_score": 60, "burst_score": 55,
            "stock_short_score": 70, "stock_short_score_v2": 65,
            "stock_trend_score": 60, "sector_leader_score": 75,
            "agent_score": 50, "quant_score": 55,
            "hard_risk_penalty": 5, "trade_risk_penalty": 3,
            "volatility_elasticity_score": 55, "drawdown_risk_score": 5,
        }
        stock_high = dict(stock_low)
        stock_high["trade_risk_penalty"] = 30

        result_low = compute_shadow_decision_score_v3(stock_low)
        result_high = compute_shadow_decision_score_v3(stock_high)

        assert result_low["shadow_decision_score_v3"] > result_high["shadow_decision_score_v3"]


# ======================================================================
# Test: Production Decision Score Unchanged
# ======================================================================

class TestProductionUnchanged:
    def test_production_decision_score_unchanged(self):
        """Production decision_score should not be affected by v3."""
        stock = {
            "trend_score": 60, "burst_score": 55,
            "stock_short_score": 70, "stock_trend_score": 65,
            "sector_leader_score": 80, "agent_score": 50,
            "risk_penalty_score": 10,
        }
        prod_result = compute_decision_score(stock)
        v3_result = compute_shadow_decision_score_v3(stock)

        # Production and v3 should be different
        assert prod_result["decision_score"] != v3_result["shadow_decision_score_v3"]


# ======================================================================
# Test: Diagnostic Tags
# ======================================================================

class TestTags:
    def test_high_risk_tags(self):
        """High risk should produce diagnostic tags."""
        stock = {
            "trend_score": 60, "burst_score": 55,
            "stock_short_score": 70, "stock_short_score_v2": 65,
            "stock_trend_score": 60, "sector_leader_score": 75,
            "agent_score": 50, "quant_score": 55,
            "hard_risk_penalty": 30, "trade_risk_penalty": 20,
            "volatility_elasticity_score": 75, "drawdown_risk_score": 25,
        }
        result = compute_shadow_decision_score_v3(stock)
        tags = result["shadow_decision_v3_tags"]
        assert "v3_high_hard_risk" in tags
        assert "v3_high_trade_risk" in tags
        assert "v3_high_elasticity" in tags
        assert "v3_high_drawdown_risk" in tags

    def test_elasticity_tag(self):
        """Should always have elasticity tag."""
        stock = {
            "trend_score": 60, "burst_score": 55,
            "stock_short_score": 70, "stock_short_score_v2": 65,
            "stock_trend_score": 60, "sector_leader_score": 75,
            "agent_score": 50, "quant_score": 55,
            "hard_risk_penalty": 5, "trade_risk_penalty": 3,
            "volatility_elasticity_score": 55, "drawdown_risk_score": 5,
        }
        result = compute_shadow_decision_score_v3(stock)
        assert "v3_elasticity_as_opportunity" in result["shadow_decision_v3_tags"]


# ======================================================================
# Test: Breakdown Structure
# ======================================================================

class TestBreakdown:
    def test_breakdown_keys(self):
        """Breakdown should have all component keys."""
        stock = {
            "trend_score": 60, "burst_score": 55,
            "stock_short_score": 70, "stock_short_score_v2": 65,
            "stock_trend_score": 60, "sector_leader_score": 75,
            "agent_score": 50, "quant_score": 55,
            "hard_risk_penalty": 5, "trade_risk_penalty": 3,
            "volatility_elasticity_score": 55, "drawdown_risk_score": 5,
        }
        result = compute_shadow_decision_score_v3(stock)
        breakdown = result["shadow_decision_breakdown_v3"]
        expected_keys = [
            "sector_trend_score", "sector_burst_score", "stock_short_score",
            "stock_trend_score", "sector_leader_score", "quant_score",
            "agent_score", "hard_risk_penalty", "trade_risk_penalty",
            "volatility_elasticity_score", "drawdown_risk_score",
            "alpha_component", "elasticity_bonus", "risk_component", "total",
        ]
        for key in expected_keys:
            assert key in breakdown, f"Missing key: {key}"
