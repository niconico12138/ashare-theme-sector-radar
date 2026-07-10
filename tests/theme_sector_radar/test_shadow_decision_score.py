"""Tests for shadow decision score module."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "theme_sector_radar" / "scoring"))

from shadow_decision_score import compute_shadow_decision_score_v2
from risk_decomposition import decompose_trade_risk


class TestShadowScoreBasic:
    def test_returns_required_keys(self):
        stock = {"code": "600001", "name": "测试"}
        result = compute_shadow_decision_score_v2(stock)
        assert "shadow_decision_score_v2" in result
        assert "shadow_decision_breakdown_v2" in result
        assert "shadow_decision_tags_v2" in result

    def test_score_range_0_100(self):
        stock = {"code": "600001", "name": "测试", "change_pct": 15.0,
                 "volume_ratio": 10.0, "stock_short_score": 95}
        result = compute_shadow_decision_score_v2(stock)
        assert 0 <= result["shadow_decision_score_v2"] <= 100

    def test_does_not_overwrite_decision_score(self):
        """Shadow score should not modify the original stock dict's decision_score."""
        stock = {"code": "600001", "decision_score": 75.0}
        compute_shadow_decision_score_v2(stock)
        assert stock["decision_score"] == 75.0


class TestNormalization:
    def test_01_scale_normalized(self):
        stock = {"trend_score": 0.6, "burst_score": 0.0}
        result = compute_shadow_decision_score_v2(stock)
        breakdown = result["shadow_decision_breakdown_v2"]
        assert breakdown["sector_trend_score"] == 60.0
        assert breakdown["sector_trend_score_normalized_from_0_1"] is True

    def test_100_scale_not_normalized(self):
        stock = {"trend_score": 70.0, "burst_score": 65.0}
        result = compute_shadow_decision_score_v2(stock)
        breakdown = result["shadow_decision_breakdown_v2"]
        assert breakdown["sector_trend_score"] == 70.0
        assert breakdown["sector_trend_score_normalized_from_0_1"] is False


class TestAgentScoreMissing:
    def test_agent_score_missing_neutral(self):
        stock = {"code": "600001"}
        result = compute_shadow_decision_score_v2(stock)
        breakdown = result["shadow_decision_breakdown_v2"]
        assert breakdown["agent_score"] == 50.0
        assert breakdown["agent_score_missing_neutral"] is True
        assert "agent_score_missing_neutral" in result["shadow_decision_tags_v2"]

    def test_agent_score_present(self):
        stock = {"code": "600001", "agent_score": 70.0}
        result = compute_shadow_decision_score_v2(stock)
        breakdown = result["shadow_decision_breakdown_v2"]
        assert breakdown["agent_score"] == 70.0
        assert breakdown["agent_score_missing_neutral"] is False


class TestRiskImpact:
    def test_hard_risk_reduces_shadow_score(self):
        base_stock = {"code": "600001", "stock_short_score": 70, "stock_trend_score": 60,
                      "sector_leader_score": 65, "quant_score": 60, "agent_score": 60}
        base_result = compute_shadow_decision_score_v2(base_stock)

        risky_stock = dict(base_stock)
        risky_stock["hard_risk_penalty"] = 30.0
        risky_result = compute_shadow_decision_score_v2(risky_stock)

        assert risky_result["shadow_decision_score_v2"] < base_result["shadow_decision_score_v2"]

    def test_elasticity_increases_shadow_score(self):
        base_stock = {"code": "600001", "stock_short_score": 70, "stock_trend_score": 60,
                      "sector_leader_score": 65, "quant_score": 60, "agent_score": 60}
        base_result = compute_shadow_decision_score_v2(base_stock)

        elastic_stock = dict(base_stock)
        elastic_stock["volatility_elasticity_score"] = 80.0
        elastic_result = compute_shadow_decision_score_v2(elastic_stock)

        assert elastic_result["shadow_decision_score_v2"] > base_result["shadow_decision_score_v2"]

    def test_drawdown_risk_reduces_shadow_score(self):
        base_stock = {"code": "600001", "stock_short_score": 70, "stock_trend_score": 60,
                      "sector_leader_score": 65, "quant_score": 60, "agent_score": 60}
        base_result = compute_shadow_decision_score_v2(base_stock)

        dd_stock = dict(base_stock)
        dd_stock["drawdown_risk_score"] = 30.0
        dd_result = compute_shadow_decision_score_v2(dd_stock)

        assert dd_result["shadow_decision_score_v2"] < base_result["shadow_decision_score_v2"]


class TestEndToEnd:
    def test_with_risk_decomposition(self):
        """Full pipeline: decompose → shadow score."""
        stock = {"code": "600001", "name": "测试", "change_pct": 3.0,
                 "stock_short_score": 70, "stock_trend_score": 60,
                 "sector_leader_score": 65, "quant_score": 60,
                 "source_pool": "trend", "amount": 50_000_000}
        decomp = decompose_trade_risk(stock)
        stock.update(decomp)
        shadow = compute_shadow_decision_score_v2(stock)
        assert 0 <= shadow["shadow_decision_score_v2"] <= 100
        assert shadow["shadow_decision_breakdown_v2"]["hard_risk_penalty"] >= 0
