"""Tests for risk decomposition module."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "theme_sector_radar" / "scoring"))

from risk_decomposition import decompose_trade_risk


class TestHardRiskPenalty:
    def test_st_stock_gets_high_hard_risk(self):
        stock = {"name": "*ST测试", "code": "000001"}
        result = decompose_trade_risk(stock)
        assert result["hard_risk_penalty"] >= 50.0
        assert any("hard_st" in t for t in result["risk_decomposition_tags"])

    def test_delisted_stock_gets_high_hard_risk(self):
        stock = {"name": "退市整理", "code": "000001"}
        result = decompose_trade_risk(stock)
        assert result["hard_risk_penalty"] >= 50.0
        assert any("hard_delisted" in t for t in result["risk_decomposition_tags"])

    def test_non_main_board_gets_hard_risk(self):
        stock = {"name": "测试", "code": "300001"}
        result = decompose_trade_risk(stock)
        assert result["hard_risk_penalty"] >= 30.0
        assert any("hard_non_main_board" in t for t in result["risk_decomposition_tags"])

    def test_low_liquidity_gets_hard_risk(self):
        stock = {"name": "测试", "code": "600001", "amount": 3_000_000}
        result = decompose_trade_risk(stock)
        assert result["hard_risk_penalty"] >= 15.0
        assert any("hard_low_liquidity" in t for t in result["risk_decomposition_tags"])

    def test_clean_stock_low_hard_risk(self):
        stock = {"name": "优质股", "code": "600001", "amount": 100_000_000,
                 "change_pct": 2.0, "quant_score": 70, "final_score": 70}
        result = decompose_trade_risk(stock)
        assert result["hard_risk_penalty"] < 5.0


class TestVolatilityElasticity:
    def test_high_change_pct_increases_elasticity(self):
        stock = {"name": "测试", "code": "600001", "change_pct": 8.0}
        result = decompose_trade_risk(stock)
        assert result["volatility_elasticity_score"] > 50.0

    def test_burst_pool_increases_elasticity(self):
        stock = {"name": "测试", "code": "600001", "source_pool": "burst"}
        result = decompose_trade_risk(stock)
        assert result["volatility_elasticity_score"] > 50.0

    def test_high_volume_ratio_increases_elasticity(self):
        stock = {"name": "测试", "code": "600001", "volume_ratio": 5.0}
        result = decompose_trade_risk(stock)
        assert result["volatility_elasticity_score"] > 50.0

    def test_elasticity_range_0_100(self):
        stock = {"name": "测试", "code": "600001", "change_pct": 15.0,
                 "volume_ratio": 10.0, "turnover_rate": 10.0,
                 "stock_short_score": 95, "source_pool": "burst"}
        result = decompose_trade_risk(stock)
        assert 0 <= result["volatility_elasticity_score"] <= 100


class TestDrawdownRisk:
    def test_near_limit_up_increases_drawdown(self):
        stock = {"name": "测试", "code": "600001", "change_pct": 9.8}
        result = decompose_trade_risk(stock)
        assert result["drawdown_risk_score"] >= 15.0
        assert any("drawdown_near_limit_up" in t for t in result["risk_decomposition_tags"])

    def test_volume_stagnation_increases_drawdown(self):
        stock = {"name": "测试", "code": "600001", "change_pct": 0.3, "volume_ratio": 3.0}
        result = decompose_trade_risk(stock)
        assert result["drawdown_risk_score"] >= 12.0

    def test_drawdown_range_0_50(self):
        stock = {"name": "测试", "code": "600001", "change_pct": 15.0,
                 "volume_ratio": 10.0, "stock_short_score": 95}
        result = decompose_trade_risk(stock)
        assert 0 <= result["drawdown_risk_score"] <= 50


class TestMissingFields:
    def test_empty_stock_does_not_crash(self):
        result = decompose_trade_risk({})
        assert "hard_risk_penalty" in result
        assert "volatility_elasticity_score" in result
        assert "drawdown_risk_score" in result
        assert isinstance(result["risk_decomposition_tags"], list)
        assert isinstance(result["risk_decomposition_breakdown"], dict)

    def test_none_values_handled(self):
        stock = {"name": None, "code": None, "change_pct": None, "amount": None}
        result = decompose_trade_risk(stock)
        assert 0 <= result["hard_risk_penalty"] <= 50
