"""Tests for stock_short_score module."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "theme_sector_radar" / "scoring"))

from stock_short_score import compute_stock_short_score


class TestComputeStockShortScore:
    """Test compute_stock_short_score function."""

    def test_basic_score_no_bars(self):
        """Score with basic fields, no bars data."""
        stock = {
            "change_pct": 3.5,
            "amount": 50_000_000,
            "volume": 1_000_000,
            "turnover_rate": 2.0,
            "volume_ratio": 1.5,
            "sector_burst_score": 65.0,
        }
        result = compute_stock_short_score(stock, bars=None)
        assert "stock_short_score" in result
        assert "stock_short_breakdown" in result
        assert "stock_short_tags" in result
        assert 0 <= result["stock_short_score"] <= 100
        assert isinstance(result["stock_short_breakdown"], dict)
        assert isinstance(result["stock_short_tags"], list)

    def test_missing_bars_has_degraded_tag(self):
        """When bars are missing, degraded tag should be present."""
        stock = {"change_pct": 2.0, "amount": 10_000_000}
        result = compute_stock_short_score(stock, bars=None)
        assert "short_score_degraded_missing_bars" in result["stock_short_tags"]

    def test_with_bars_full_data(self):
        """Score with complete bar data."""
        bars = [
            {"date": "2026-07-09", "open": 10.0, "high": 11.0, "low": 9.8, "close": 10.8, "volume": 2_000_000, "amount": 21_600_000},
            {"date": "2026-07-08", "open": 9.5, "high": 10.2, "low": 9.3, "close": 10.0, "volume": 1_500_000, "amount": 15_000_000},
            {"date": "2026-07-07", "open": 9.2, "high": 9.8, "low": 9.0, "close": 9.5, "volume": 1_200_000, "amount": 11_400_000},
            {"date": "2026-07-04", "open": 9.0, "high": 9.5, "low": 8.8, "close": 9.2, "volume": 1_000_000, "amount": 9_200_000},
            {"date": "2026-07-03", "open": 8.8, "high": 9.1, "low": 8.5, "close": 9.0, "volume": 900_000, "amount": 8_100_000},
            {"date": "2026-07-02", "open": 8.5, "high": 8.9, "low": 8.3, "close": 8.8, "volume": 800_000, "amount": 7_040_000},
        ]
        stock = {
            "change_pct": 8.0,
            "amount": 21_600_000,
            "volume": 2_000_000,
            "turnover_rate": 3.0,
            "volume_ratio": 1.5,
            "sector_burst_score": 70.0,
        }
        result = compute_stock_short_score(stock, bars=bars)
        assert 0 <= result["stock_short_score"] <= 100
        # With bars, no degraded tag
        assert "short_score_degraded_missing_bars" not in result["stock_short_tags"]

    def test_high_rejection_stock(self):
        """Stock with upper shadow (冲高回落) gets penalized."""
        bars = [
            {"date": "2026-07-09", "open": 10.0, "high": 12.0, "low": 9.8, "close": 10.2, "volume": 2_000_000, "amount": 21_600_000},
            {"date": "2026-07-08", "open": 9.5, "high": 10.2, "low": 9.3, "close": 10.0, "volume": 1_500_000, "amount": 15_000_000},
            {"date": "2026-07-07", "open": 9.2, "high": 9.8, "low": 9.0, "close": 9.5, "volume": 1_200_000, "amount": 11_400_000},
            {"date": "2026-07-04", "open": 9.0, "high": 9.5, "low": 8.8, "close": 9.2, "volume": 1_000_000, "amount": 9_200_000},
            {"date": "2026-07-03", "open": 8.8, "high": 9.1, "low": 8.5, "close": 9.0, "volume": 900_000, "amount": 8_100_000},
        ]
        stock = {"change_pct": 2.0, "amount": 21_600_000, "volume": 2_000_000, "turnover_rate": 3.0}
        result = compute_stock_short_score(stock, bars=bars)
        assert "high_rejection" in result["stock_short_tags"]

    def test_score_range(self):
        """Score should always be 0-100."""
        # Extreme case: everything positive
        stock = {"change_pct": 10, "amount": 100_000_000, "volume_ratio": 5, "sector_burst_score": 90}
        result = compute_stock_short_score(stock, bars=None)
        assert 0 <= result["stock_short_score"] <= 100

        # Extreme case: everything negative
        stock = {"change_pct": -10, "amount": 1_000, "volume_ratio": 0.1, "sector_burst_score": 10}
        result = compute_stock_short_score(stock, bars=None)
        assert 0 <= result["stock_short_score"] <= 100

    def test_empty_stock_dict(self):
        """Empty stock dict should not crash."""
        result = compute_stock_short_score({}, bars=None)
        assert 0 <= result["stock_short_score"] <= 100
        assert isinstance(result["stock_short_tags"], list)

    def test_with_sector_context(self):
        """Sector context should affect relative strength."""
        stock = {"change_pct": 5.0, "amount": 50_000_000, "sector_burst_score": 80.0}
        result = compute_stock_short_score(stock, bars=None, sector_context={"burst_score": 80})
        assert 0 <= result["stock_short_score"] <= 100
