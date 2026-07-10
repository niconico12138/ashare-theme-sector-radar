"""Tests for trade_risk module."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "theme_sector_radar" / "scoring"))

from trade_risk import compute_trade_risk


class TestComputeTradeRisk:
    """Test compute_trade_risk function."""

    def test_st_stock_invalid(self):
        """ST stock should be invalid."""
        stock = {"code": "000001", "name": "*ST测试", "change_pct": 5.0, "amount": 50_000_000}
        result = compute_trade_risk(stock)
        assert result["trade_eligibility"] == "invalid"
        assert result["invalid_reason"] == "st_stock"
        assert "st_stock" in result["risk_tags"]

    def test_delisted_stock_invalid(self):
        """Delisted stock should be invalid."""
        stock = {"code": "000001", "name": "退市整理", "change_pct": 5.0, "amount": 50_000_000}
        result = compute_trade_risk(stock)
        assert result["trade_eligibility"] == "invalid"
        assert result["invalid_reason"] == "delisted_stock"

    def test_non_main_board_invalid(self):
        """Non-main-board stock should be invalid."""
        stock = {"code": "300558", "name": "创业板股", "change_pct": 5.0, "amount": 50_000_000}
        result = compute_trade_risk(stock)
        assert result["trade_eligibility"] == "invalid"
        assert result["invalid_reason"] == "non_main_board"

    def test_clean_stock_focus(self):
        """Clean stock with no risk factors should be focus."""
        stock = {
            "code": "600001",
            "name": "优质股",
            "change_pct": 2.0,
            "amount": 100_000_000,
            "turnover_rate": 3.0,
            "volume_ratio": 1.2,
            "sector_role": "leader",
            "stock_short_score": 50,
            "decision_score": 50,
            "quant_score": 70,
            "final_score": 75,
        }
        result = compute_trade_risk(stock)
        assert result["trade_eligibility"] == "focus"

    def test_near_limit_up_penalty(self):
        """Stock near limit up should get penalty."""
        stock = {
            "code": "600001",
            "name": "涨停股",
            "change_pct": 9.8,
            "amount": 100_000_000,
            "turnover_rate": 5.0,
            "volume_ratio": 1.5,
        }
        result = compute_trade_risk(stock)
        assert result["risk_penalty_score"] > 10
        assert "near_limit_up" in result["risk_tags"]

    def test_low_liquidity_penalty(self):
        """Low liquidity stock should get penalty."""
        stock = {
            "code": "600001",
            "name": "低流动股",
            "change_pct": 2.0,
            "amount": 3_000_000,  # < 500万
            "turnover_rate": 3.0,
            "volume_ratio": 1.0,
        }
        result = compute_trade_risk(stock)
        assert "low_liquidity" in result["risk_tags"]
        assert result["risk_penalty_score"] >= 15

    def test_volume_stagnation(self):
        """Volume stagnation (放量滞涨) should get penalty."""
        stock = {
            "code": "600001",
            "name": "滞涨股",
            "change_pct": 0.3,  # near zero
            "amount": 50_000_000,
            "turnover_rate": 3.0,
            "volume_ratio": 3.0,  # high volume but flat
        }
        result = compute_trade_risk(stock)
        assert "volume_stagnation" in result["risk_tags"]

    def test_laggard_role_penalty(self):
        """Laggard sector role should get penalty."""
        stock = {
            "code": "600001",
            "name": "落后股",
            "change_pct": 1.0,
            "amount": 50_000_000,
            "sector_role": "laggard",
            "decision_score": 30,
            "quant_score": 50,
            "final_score": 50,
        }
        result = compute_trade_risk(stock)
        assert "sector_laggard_risk" in result["risk_tags"]
        assert result["risk_penalty_score"] >= 10

    def test_high_penalty_avoid(self):
        """Stock with high cumulative penalty should be avoid."""
        stock = {
            "code": "600001",
            "name": "高风险股",
            "change_pct": 9.9,  # near limit up
            "amount": 3_000_000,  # low liquidity
            "turnover_rate": 0.3,  # low turnover
            "volume_ratio": 5.0,  # high volatility
            "sector_role": "laggard",
            "stock_short_score": 90,  # overheated
        }
        result = compute_trade_risk(stock)
        assert result["trade_eligibility"] == "avoid"
        assert result["risk_penalty_score"] >= 30

    def test_penalty_max_50(self):
        """Risk penalty should not exceed 50."""
        stock = {
            "code": "600001",
            "name": "极端股",
            "change_pct": 9.9,
            "amount": 1_000_000,
            "turnover_rate": 0.1,
            "volume_ratio": 10,
            "sector_role": "laggard",
            "stock_short_score": 95,
        }
        result = compute_trade_risk(stock)
        assert result["risk_penalty_score"] <= 50

    def test_empty_stock_dict(self):
        """Empty stock dict should not crash (empty code = non_main_board → invalid)."""
        result = compute_trade_risk({})
        assert result["trade_eligibility"] == "invalid"
        assert isinstance(result["risk_tags"], list)

    def test_no_buy_sell_advice(self):
        """Output should not contain buy/sell advice — only classification."""
        stock = {"code": "600001", "name": "普通股", "change_pct": 2.0, "amount": 50_000_000}
        result = compute_trade_risk(stock)
        # Should only be one of: focus, watch, backup, avoid, invalid
        assert result["trade_eligibility"] in ("focus", "watch", "backup", "avoid", "invalid")
