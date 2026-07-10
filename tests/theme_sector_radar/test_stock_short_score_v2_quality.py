"""Tests for stock short score v2 quality diagnosis."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from diagnose_stock_short_score_v2_quality import (
    compute_distribution,
    compute_factor_performance,
    compute_v1_v2_comparison,
    generate_markdown,
    REGIMES,
)


def _make_records(n=30, regime="broad_up", base_return=1.0):
    """Generate synthetic records for testing."""
    records = []
    for i in range(n):
        records.append({
            "date": f"2026-06-{(i % 28) + 1:02d}",
            "code": f"{600000 + i:06d}",
            "name": f"Stock{i}",
            "market_regime": regime,
            "data_available": True,
            "next_return_pct": base_return + (i - n / 2) * 0.3,
            "stock_short_score_v1": 40 + i * 1.0,
            "stock_short_score_v2": 20 + i * 2.0,
            "stock_short_breakdown_v2": {},
            "stock_short_v2_tags": [],
        })
    return records


# ======================================================================
# Test: Distribution
# ======================================================================

class TestDistribution:
    def test_basic_distribution(self):
        scores = [10, 20, 30, 40, 50, 60, 70, 80, 90]
        result = compute_distribution(scores)
        assert result["sample_count"] == 9
        assert result["min"] == 10
        assert result["max"] == 90
        assert result["spread"] == 80

    def test_empty_distribution(self):
        result = compute_distribution([])
        assert result["sample_count"] == 0

    def test_spread_target_met(self):
        scores = list(range(10, 60))
        result = compute_distribution(scores)
        assert result["spread"] >= 30
        assert "spread_target_met" in result["quality_flags"]

    def test_bucket_distribution(self):
        scores = [5, 15, 25, 35, 45, 55, 65, 75, 85, 95]
        result = compute_distribution(scores)
        buckets = result["bucket_distribution"]
        assert sum(buckets.values()) == 10


# ======================================================================
# Test: Factor Performance
# ======================================================================

class TestFactorPerformance:
    def test_basic_performance(self):
        records = _make_records(30)
        result = compute_factor_performance(records, "stock_short_score_v2", "test")
        assert result["sample_count"] == 30
        assert "gap" in result

    def test_insufficient_samples(self):
        records = _make_records(5)
        result = compute_factor_performance(records, "stock_short_score_v2", "test")
        assert result["sample_count"] == 5


# ======================================================================
# Test: V1 vs V2 Comparison
# ======================================================================

class TestV1V2Comparison:
    def test_comparison_structure(self):
        records = _make_records(30)
        result = compute_v1_v2_comparison(records)
        assert "v1" in result
        assert "v2" in result
        assert "overall" in result["v1"]
        assert "overall" in result["v2"]


# ======================================================================
# Test: Markdown Generation
# ======================================================================

class TestMarkdown:
    def test_markdown_structure(self):
        coverage = {"valid_dates": 120, "forward_samples": 2000}
        v2_dist = {"min": 10, "max": 80, "mean": 45, "spread": 70, "unique_count": 50,
                   "bucket_distribution": {"0-20": 100, "20-40": 400, "40-60": 800, "60-80": 500, "80-100": 200},
                   "quality_flags": ["spread_target_met"], "sample_count": 2000}
        v1_dist = {"min": 20, "max": 60, "mean": 40, "spread": 40, "unique_count": 30,
                   "bucket_distribution": {}, "quality_flags": [], "sample_count": 2000}
        v2_perf = {"sample_count": 2000, "gap": 0.5, "hit_rate_diff": 5.0, "spearman_corr": 0.03}
        comparison = {"v1": {"overall": {"gap": 0.3}}, "v2": {"overall": {"gap": 0.5}}}

        md = generate_markdown(coverage, v2_dist, v1_dist, v2_perf, comparison, "test_range")
        assert "Stock Short Score V2 Quality" in md
        assert "spread_target_met" in md
