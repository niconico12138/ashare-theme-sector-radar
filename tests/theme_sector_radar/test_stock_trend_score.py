"""Tests for stock_trend_score module."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "theme_sector_radar" / "scoring"))

from stock_trend_score import compute_stock_trend_score


class TestComputeStockTrendScore:
    """Test compute_stock_trend_score function."""

    def test_basic_score_no_bars(self):
        """Score with basic fields, no bars — uses fallback."""
        stock = {
            "change_pct": 2.0,
            "quant_score": 65.0,
            "sector_trend_score": 70.0,
        }
        result = compute_stock_trend_score(stock, bars=None)
        assert "stock_trend_score" in result
        assert "stock_trend_breakdown" in result
        assert "stock_trend_tags" in result
        assert 0 <= result["stock_trend_score"] <= 100
        assert "trend_score_degraded_missing_bars" in result["stock_trend_tags"]

    def test_with_bars_full_data(self):
        """Score with complete bar data (60+ bars for MA60)."""
        # Generate 65 bars of uptrending data
        bars = []
        price = 8.0
        for i in range(65):
            price += 0.05  # slight uptrend
            bars.append({
                "date": f"2026-04-{(i % 28) + 1:02d}",
                "open": price - 0.1,
                "high": price + 0.2,
                "low": price - 0.2,
                "close": price,
                "volume": 1_000_000 + i * 10_000,
                "amount": price * (1_000_000 + i * 10_000),
            })
        stock = {"change_pct": 1.5, "quant_score": 70.0}
        result = compute_stock_trend_score(stock, bars=bars)
        assert 0 <= result["stock_trend_score"] <= 100
        assert "trend_score_degraded_missing_bars" not in result["stock_trend_tags"]

    def test_with_insufficient_bars_fallback(self):
        """With only 3 bars, should use fallback."""
        bars = [
            {"date": "2026-07-09", "close": 10.0, "volume": 1_000_000},
            {"date": "2026-07-08", "close": 9.8, "volume": 900_000},
            {"date": "2026-07-07", "close": 9.5, "volume": 800_000},
        ]
        stock = {"change_pct": 2.0, "quant_score": 60.0, "sector_trend_score": 55.0}
        result = compute_stock_trend_score(stock, bars=bars)
        assert 0 <= result["stock_trend_score"] <= 100
        assert "trend_score_degraded_missing_bars" in result["stock_trend_tags"]

    def test_fallback_uses_quant_score(self):
        """Fallback should incorporate quant_score."""
        stock = {"change_pct": 0, "quant_score": 80.0, "sector_trend_score": 60.0}
        result = compute_stock_trend_score(stock, bars=None)
        # Higher quant_score should contribute to higher trend score
        assert result["stock_trend_score"] > 40

    def test_fallback_missing_quant_score(self):
        """Missing quant_score should be marked in tags."""
        stock = {"change_pct": 2.0}
        result = compute_stock_trend_score(stock, bars=None)
        assert "quant_score_missing_neutral" in result["stock_trend_tags"]

    def test_uptrend_higher_than_downtrend(self):
        """Uptrending bars should score higher than downtrending.

        Model: uptrend stock climbs steadily; downtrend stock peaks then pulls back.
        """
        # Uptrend: steady climb from 8.0 to ~10.0 over 25 days
        uptrend_bars = []
        for i in range(25):
            p = 8.0 + i * 0.08
            uptrend_bars.append({
                "date": f"2026-06-{(i % 28) + 1:02d}",
                "close": round(p, 2), "high": round(p + 0.15, 2), "low": round(p - 0.1, 2),
                "open": round(p - 0.05, 2), "volume": 1_000_000,
            })

        # Downtrend: peaks at 10.0 then declines to ~8.0
        downtrend_bars = []
        for i in range(25):
            if i < 10:
                p = 8.0 + i * 0.2   # rise to 10.0
            else:
                p = 10.0 - (i - 10) * 0.2  # decline to ~8.0
            downtrend_bars.append({
                "date": f"2026-06-{(i % 28) + 1:02d}",
                "close": round(p, 2), "high": round(p + 0.15, 2), "low": round(p - 0.1, 2),
                "open": round(p - 0.05, 2), "volume": 1_000_000,
            })

        stock = {"change_pct": 0}
        up_result = compute_stock_trend_score(stock, bars=uptrend_bars)
        down_result = compute_stock_trend_score(stock, bars=downtrend_bars)
        assert up_result["stock_trend_score"] > down_result["stock_trend_score"]

    def test_score_range_bounds(self):
        """Score should always be 0-100."""
        stock = {"change_pct": -10, "quant_score": 0, "sector_trend_score": 0}
        result = compute_stock_trend_score(stock, bars=None)
        assert 0 <= result["stock_trend_score"] <= 100

    def test_empty_stock_dict(self):
        """Empty stock dict should not crash."""
        result = compute_stock_trend_score({}, bars=None)
        assert 0 <= result["stock_trend_score"] <= 100
