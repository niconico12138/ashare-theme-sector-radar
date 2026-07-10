"""Tests for stock short score v2."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.scoring.stock_short_score_v2 import (
    compute_stock_short_score_v2,
    _calc_close_position,
    _scale_to_range,
)


# ======================================================================
# Test: Score Range 0-100
# ======================================================================

class TestScoreRange:
    def test_score_in_range(self):
        """Score must be 0-100 for various inputs."""
        stocks = [
            {"change_pct": 5.0, "amount": 100_000_000, "volume_ratio": 2.0},
            {"change_pct": -3.0, "amount": 50_000_000, "volume_ratio": 1.0},
            {"change_pct": 0.0, "amount": 0, "volume_ratio": 0},
            {"change_pct": 10.0, "amount": 200_000_000, "volume_ratio": 5.0},
        ]
        for stock in stocks:
            result = compute_stock_short_score_v2(stock)
            score = result["stock_short_score_v2"]
            assert 0 <= score <= 100, f"Score {score} out of range for {stock}"

    def test_score_with_bars(self):
        """Score with bars data should be in range."""
        stock = {"change_pct": 3.0, "amount": 100_000_000}
        bars = [
            {"date": "2026-07-08", "open": 10.0, "high": 11.0, "low": 9.5, "close": 10.8, "volume": 1000000},
            {"date": "2026-07-07", "open": 9.8, "high": 10.2, "low": 9.5, "close": 10.0, "volume": 800000},
            {"date": "2026-07-06", "open": 9.5, "high": 10.0, "low": 9.2, "close": 9.8, "volume": 600000},
        ]
        result = compute_stock_short_score_v2(stock, bars=bars)
        assert 0 <= result["stock_short_score_v2"] <= 100


# ======================================================================
# Test: Close Position Score
# ======================================================================

class TestClosePosition:
    def test_close_at_high(self):
        """Close at high should give maximum close position."""
        pos = _calc_close_position(11.0, 9.0, 11.0)
        assert pos == 1.0

    def test_close_at_low(self):
        """Close at low should give minimum close position."""
        pos = _calc_close_position(11.0, 9.0, 9.0)
        assert pos == 0.0

    def test_close_at_mid(self):
        """Close at mid should give 0.5."""
        pos = _calc_close_position(11.0, 9.0, 10.0)
        assert pos == 0.5

    def test_zero_range(self):
        """Zero range should give 0.5."""
        pos = _calc_close_position(10.0, 10.0, 10.0)
        assert pos == 0.5

    def test_close_position_score_with_ohlc(self):
        """Test close position score from stock OHLC data."""
        stock = {
            "high": 11.0, "low": 9.0, "close": 10.5, "open": 9.5,
            "change_pct": 5.0, "amount": 100_000_000,
        }
        result = compute_stock_short_score_v2(stock)
        breakdown = result["stock_short_breakdown_v2"]
        assert "close_position_score" in breakdown
        assert breakdown["close_position_score"] > 10  # Close near high


# ======================================================================
# Test: High Rejection Penalty
# ======================================================================

class TestHighRejection:
    def test_severe_rejection(self):
        """Large upper shadow should give severe penalty."""
        stock = {
            "high": 12.0, "low": 9.0, "close": 9.5, "open": 10.0,
            "change_pct": -5.0, "amount": 100_000_000,
        }
        result = compute_stock_short_score_v2(stock)
        tags = result["stock_short_v2_tags"]
        assert "v2_high_rejection_severe" in tags

    def test_no_rejection(self):
        """Close at high should have no rejection penalty."""
        stock = {
            "high": 11.0, "low": 9.0, "close": 11.0, "open": 10.0,
            "change_pct": 10.0, "amount": 100_000_000,
        }
        result = compute_stock_short_score_v2(stock)
        breakdown = result["stock_short_breakdown_v2"]
        assert breakdown["rejection_penalty"] >= -2.0


# ======================================================================
# Test: Missing Data Degradation
# ======================================================================

class TestMissingData:
    def test_no_bars_degradation(self):
        """Without bars, score should still work with fallbacks."""
        stock = {"change_pct": 2.0, "amount": 50_000_000, "volume_ratio": 1.5}
        result = compute_stock_short_score_v2(stock)
        assert 0 <= result["stock_short_score_v2"] <= 100
        assert "v2_three_day_rs_fallback" in result["stock_short_v2_tags"]

    def test_no_ohlc_degradation(self):
        """Without OHLC, close position uses fallback."""
        stock = {"change_pct": 3.0, "amount": 50_000_000}
        result = compute_stock_short_score_v2(stock)
        assert "v2_close_position_fallback" in result["stock_short_v2_tags"]

    def test_empty_stock(self):
        """Empty stock dict should not crash."""
        result = compute_stock_short_score_v2({})
        assert 0 <= result["stock_short_score_v2"] <= 100


# ======================================================================
# Test: Overheat Penalty
# ======================================================================

class TestOverheat:
    def test_near_limit_up(self):
        """Near limit-up should trigger overheat penalty."""
        stock = {"change_pct": 9.8, "amount": 100_000_000, "volume_ratio": 3.0}
        result = compute_stock_short_score_v2(stock)
        assert "v2_overheat_near_limit" in result["stock_short_v2_tags"]
        assert result["stock_short_breakdown_v2"]["overheat_penalty"] < 0

    def test_normal_change_no_overheat(self):
        """Normal change should not trigger overheat."""
        stock = {"change_pct": 2.0, "amount": 100_000_000, "volume_ratio": 1.5}
        result = compute_stock_short_score_v2(stock)
        assert "v2_overheat_near_limit" not in result["stock_short_v2_tags"]
        assert "v2_overheat_high_change" not in result["stock_short_v2_tags"]


# ======================================================================
# Test: Data Quality Penalty
# ======================================================================

class TestdataQuality:
    def test_missing_bars_penalty(self):
        """Missing bars should reduce data quality."""
        stock = {"change_pct": 2.0, "amount": 100_000_000}
        result = compute_stock_short_score_v2(stock)
        assert "v2_missing_bars" in result["stock_short_v2_tags"]
        assert result["stock_short_breakdown_v2"]["data_quality_penalty"] < 0

    def test_with_bars_no_penalty(self):
        """With bars, no missing bars penalty."""
        stock = {"change_pct": 2.0, "amount": 100_000_000}
        bars = [
            {"date": "2026-07-08", "open": 10.0, "high": 11.0, "low": 9.5, "close": 10.8, "volume": 1000000},
            {"date": "2026-07-07", "open": 9.8, "high": 10.2, "low": 9.5, "close": 10.0, "volume": 800000},
        ]
        result = compute_stock_short_score_v2(stock, bars=bars)
        assert "v2_missing_bars" not in result["stock_short_v2_tags"]


# ======================================================================
# Test: Score Spread
# ======================================================================

class TestScoreSpread:
    def test_different_stocks_different_scores(self):
        """Different stock profiles should produce different scores."""
        stocks = [
            {"change_pct": 8.0, "amount": 200_000_000, "volume_ratio": 4.0, "high": 12.0, "low": 9.0, "close": 11.8},
            {"change_pct": -2.0, "amount": 10_000_000, "volume_ratio": 0.5, "high": 10.0, "low": 9.0, "close": 9.2},
            {"change_pct": 0.0, "amount": 50_000_000, "volume_ratio": 1.0, "high": 10.0, "low": 9.8, "close": 9.9},
        ]
        scores = [compute_stock_short_score_v2(s)["stock_short_score_v2"] for s in stocks]
        # Scores should not all be the same
        assert len(set(scores)) > 1, f"All scores are the same: {scores}"


# ======================================================================
# Test: Breakdown Structure
# ======================================================================

class TestBreakdown:
    def test_breakdown_keys(self):
        """Breakdown should have all component keys."""
        stock = {"change_pct": 3.0, "amount": 100_000_000, "volume_ratio": 2.0}
        result = compute_stock_short_score_v2(stock)
        breakdown = result["stock_short_breakdown_v2"]
        expected_keys = [
            "close_position_score", "three_day_rs_score", "five_day_rs_score",
            "volume_expansion_score", "sector_rs_score", "rejection_penalty",
            "overheat_penalty", "data_quality_penalty", "total",
        ]
        for key in expected_keys:
            assert key in breakdown, f"Missing key: {key}"
