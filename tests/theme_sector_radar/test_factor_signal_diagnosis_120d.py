"""Tests for 120-day factor signal diagnosis."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from diagnose_factor_signal_120d import (
    _rank,
    spearman_correlation,
    _safe_float,
    _avg,
    _pct,
    _split_by_quantile,
    compute_factor_bucket_performance,
    compute_rank_correlations,
    compute_regime_breakdown,
    compute_top_bottom_analysis,
    compute_trend_vs_burst,
    compute_agent_comparison,
    classify_factor_signal,
    find_strongest_factors,
    generate_markdown,
    FACTOR_FIELDS,
    CONSISTENCY_THRESHOLD,
)


# ======================================================================
# Helpers
# ======================================================================

def _make_records(n=30, regime="broad_up", base_return=1.0, score_offset=0.0):
    """Generate synthetic records for testing."""
    records = []
    for i in range(n):
        records.append({
            "date": f"2026-06-{(i % 28) + 1:02d}",
            "code": f"{600000 + i:06d}",
            "name": f"Stock{i}",
            "market_regime": regime,
            "data_available": True,
            "next_return_pct": base_return + (i - n / 2) * 0.2,
            "next_low_return_pct": base_return - 1.0 + (i - n / 2) * 0.1,
            "max_intraday_drawdown_pct": 2.0 + i * 0.1,
            "decision_score": 50 + score_offset + i * 1.5,
            "stock_short_score": 45 + score_offset + i * 1.2,
            "stock_trend_score": 40 + score_offset + i * 1.0,
            "sector_leader_score": 55 + i * 0.8,
            "risk_penalty_score": 20 - i * 0.3,
            "agent_score": 50 + i * 0.5 if i % 3 != 0 else None,
            "source_pool": "trend" if i % 2 == 0 else "burst",
            "trade_eligibility": "focus" if i < n // 3 else ("watch" if i < 2 * n // 3 else "backup"),
            "agent_analysis_status": "analyzed" if i % 3 != 0 else "skipped_by_agent_stock_limit",
        })
    return records


# ======================================================================
# Test: Spearman
# ======================================================================

class TestSpearman:
    def test_perfect_positive(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert spearman_correlation(x, y) == 1.0

    def test_perfect_negative(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [5.0, 4.0, 3.0, 2.0, 1.0]
        assert spearman_correlation(x, y) == -1.0

    def test_insufficient_data(self):
        assert spearman_correlation([1.0], [1.0]) is None
        assert spearman_correlation([1.0, 2.0], [1.0, 2.0]) is None

    def test_tied_ranks(self):
        x = [1.0, 1.0, 3.0, 4.0, 5.0]
        y = [1.0, 2.0, 3.0, 4.0, 5.0]
        corr = spearman_correlation(x, y)
        assert corr is not None
        assert corr > 0.8


# ======================================================================
# Test: Empty Data
# ======================================================================

class TestEmptyData:
    def test_empty_records_bucket_perf(self):
        result = compute_factor_bucket_performance([])
        for field in FACTOR_FIELDS:
            assert field in result
            assert result[field]["high_low_gap"] is None

    def test_empty_records_rank_corr(self):
        result = compute_rank_correlations([])
        assert "overall" in result
        for field in FACTOR_FIELDS:
            assert result["overall"][field]["valid_date_count"] == 0

    def test_empty_records_regime(self):
        result = compute_regime_breakdown([])
        assert len(result) == 0

    def test_empty_records_top_bottom(self):
        result = compute_top_bottom_analysis([])
        for field in FACTOR_FIELDS:
            assert "error" in result[field]

    def test_empty_records_trend_burst(self):
        result = compute_trend_vs_burst([])
        assert result["trend"]["count"] == 0
        assert result["burst"]["count"] == 0

    def test_empty_records_agent(self):
        result = compute_agent_comparison([])
        assert result["analyzed"]["count"] == 0
        assert result["skipped"]["count"] == 0

    def test_empty_markdown(self):
        coverage = {"total_dates": 0, "valid_dates": 0, "total_candidates": 0, "forward_samples": 0}
        md = generate_markdown(coverage, {}, {}, {}, {}, {}, {}, {}, {}, "empty")
        assert "Factor Signal Diagnosis" in md
        assert "0" in md


# ======================================================================
# Test: Factor Bucket Performance
# ======================================================================

class TestFactorBuckets:
    def test_bucket_split(self):
        records = _make_records(30)
        result = compute_factor_bucket_performance(records)
        assert "decision_score" in result
        ds = result["decision_score"]
        assert ds["buckets"]["high"]["count"] > 0
        assert ds["buckets"]["low"]["count"] > 0
        assert ds["high_low_gap"] is not None

    def test_bucket_hit_rate(self):
        records = _make_records(30, base_return=2.0)
        result = compute_factor_bucket_performance(records)
        ds = result["decision_score"]
        assert ds["buckets"]["high"]["hit_rate"] is not None
        assert 0 <= ds["buckets"]["high"]["hit_rate"] <= 100

    def test_missing_field_ignored(self):
        records = _make_records(30)
        records[0]["decision_score"] = None
        result = compute_factor_bucket_performance(records)
        assert result["decision_score"]["high_low_gap"] is not None


# ======================================================================
# Test: Regime Split
# ======================================================================

class TestRegimeSplit:
    def test_regime_grouping(self):
        records = _make_records(20, regime="broad_up") + _make_records(20, regime="broad_down")
        result = compute_regime_breakdown(records)
        assert "broad_up" in result
        assert "broad_down" in result
        assert result["broad_up"]["sample_count"] == 20
        assert result["broad_down"]["sample_count"] == 20

    def test_regime_factor_gaps(self):
        records = _make_records(20, regime="broad_up") + _make_records(20, regime="broad_down")
        result = compute_regime_breakdown(records)
        for regime in ["broad_up", "broad_down"]:
            assert "factor_gaps" in result[regime]
            assert "decision_score" in result[regime]["factor_gaps"]

    def test_regime_trend_burst(self):
        records = _make_records(20, regime="broad_up")
        result = compute_regime_breakdown(records)
        tvb = result["broad_up"]["trend_vs_burst"]
        assert tvb["trend_count"] > 0
        assert tvb["burst_count"] > 0


# ======================================================================
# Test: Sign Flip -> regime_dependent
# ======================================================================

class TestSignFlip:
    def test_regime_dependent_classification(self):
        """When up_gap > 0 and down_gap < 0, should be regime_dependent."""
        bucket_perf = {
            "decision_score": {"high_low_gap": 0.5, "hit_rate_diff": 5.0, "drawdown_diff": -0.5},
        }
        rank_corr = {
            "decision_score": {"consistency": 50.0, "avg_correlation": 0.02},
        }
        regime_data = {
            "broad_up": {"factor_gaps": {"decision_score": {"gap": 1.0}}},
            "broad_down": {"factor_gaps": {"decision_score": {"gap": -0.8}}},
        }
        top_bottom = {"decision_score": {"gap": 0.5}}

        result = classify_factor_signal("decision_score", bucket_perf, rank_corr, regime_data, top_bottom)
        assert result["signal"] == "regime_dependent"
        assert result["regime_dependent"] is True

    def test_no_sign_flip_not_regime_dependent(self):
        """When both gaps are positive, should NOT be regime_dependent."""
        bucket_perf = {
            "decision_score": {"high_low_gap": 0.5, "hit_rate_diff": 5.0, "drawdown_diff": -0.5},
        }
        rank_corr = {
            "decision_score": {"consistency": 50.0, "avg_correlation": 0.02},
        }
        regime_data = {
            "broad_up": {"factor_gaps": {"decision_score": {"gap": 1.0}}},
            "broad_down": {"factor_gaps": {"decision_score": {"gap": 0.3}}},
        }
        top_bottom = {"decision_score": {"gap": 0.5}}

        result = classify_factor_signal("decision_score", bucket_perf, rank_corr, regime_data, top_bottom)
        assert result["signal"] != "regime_dependent"


# ======================================================================
# Test: Consistency Threshold
# ======================================================================

class TestConsistencyThreshold:
    def test_positive_signal_above_threshold(self):
        bucket_perf = {
            "decision_score": {"high_low_gap": 0.5, "hit_rate_diff": 5.0, "drawdown_diff": -0.5},
        }
        rank_corr = {
            "decision_score": {"consistency": 60.0, "avg_correlation": 0.05},
        }
        regime_data = {
            "broad_up": {"factor_gaps": {"decision_score": {"gap": 0.5}}},
            "broad_down": {"factor_gaps": {"decision_score": {"gap": 0.3}}},
        }
        top_bottom = {"decision_score": {"gap": 0.5}}

        result = classify_factor_signal("decision_score", bucket_perf, rank_corr, regime_data, top_bottom)
        assert result["signal"] == "positive_signal"

    def test_inconclusive_below_threshold(self):
        bucket_perf = {
            "decision_score": {"high_low_gap": 0.5, "hit_rate_diff": 5.0, "drawdown_diff": -0.5},
        }
        rank_corr = {
            "decision_score": {"consistency": 50.0, "avg_correlation": 0.02},
        }
        regime_data = {
            "broad_up": {"factor_gaps": {"decision_score": {"gap": 0.5}}},
            "broad_down": {"factor_gaps": {"decision_score": {"gap": 0.3}}},
        }
        top_bottom = {"decision_score": {"gap": 0.5}}

        result = classify_factor_signal("decision_score", bucket_perf, rank_corr, regime_data, top_bottom)
        assert result["signal"] == "inconclusive"

    def test_negative_signal(self):
        bucket_perf = {
            "risk_penalty_score": {"high_low_gap": -0.8, "hit_rate_diff": -5.0, "drawdown_diff": 0.5},
        }
        rank_corr = {
            "risk_penalty_score": {"consistency": 60.0, "avg_correlation": -0.05},
        }
        regime_data = {
            "broad_up": {"factor_gaps": {"risk_penalty_score": {"gap": -0.5}}},
            "broad_down": {"factor_gaps": {"risk_penalty_score": {"gap": -0.3}}},
        }
        top_bottom = {"risk_penalty_score": {"gap": -0.8}}

        result = classify_factor_signal("risk_penalty_score", bucket_perf, rank_corr, regime_data, top_bottom)
        assert result["signal"] == "negative_signal"


# ======================================================================
# Test: Defensive Not Alpha
# ======================================================================

class TestDefensiveNotAlpha:
    def test_defensive_classification(self):
        """When gap <= 0 but drawdown_diff < 0, should be defensive_not_alpha.
        Both regime gaps must be same sign to avoid regime_dependent taking priority."""
        bucket_perf = {
            "decision_score": {"high_low_gap": -0.3, "hit_rate_diff": -2.0, "drawdown_diff": -1.5},
        }
        rank_corr = {
            "decision_score": {"consistency": 50.0, "avg_correlation": -0.01},
        }
        regime_data = {
            "broad_up": {"factor_gaps": {"decision_score": {"gap": -0.1}}},
            "broad_down": {"factor_gaps": {"decision_score": {"gap": -0.2}}},
        }
        top_bottom = {"decision_score": {"gap": -0.3}}

        result = classify_factor_signal("decision_score", bucket_perf, rank_corr, regime_data, top_bottom)
        assert result["signal"] == "defensive_not_alpha"


# ======================================================================
# Test: Strongest Factors
# ======================================================================

class TestStrongestFactors:
    def test_find_strongest(self):
        factor_signals = {
            "decision_score": {"avg_gap": 0.5, "consistency": 60.0},
            "stock_short_score": {"avg_gap": -0.8, "consistency": 55.0},
            "stock_trend_score": {"avg_gap": 0.2, "consistency": 52.0},
            "sector_leader_score": {"avg_gap": None, "consistency": None},
            "risk_penalty_score": {"avg_gap": -0.3, "consistency": 48.0},
            "agent_score": {"avg_gap": 0.1, "consistency": 50.0},
        }
        result = find_strongest_factors(factor_signals)
        assert result["strongest_positive"]["factor"] == "decision_score"
        assert result["strongest_negative"]["factor"] == "stock_short_score"

    def test_no_positive(self):
        factor_signals = {
            "decision_score": {"avg_gap": -0.5, "consistency": 60.0},
            "stock_short_score": {"avg_gap": -0.8, "consistency": 55.0},
            "stock_trend_score": {"avg_gap": None, "consistency": None},
            "sector_leader_score": {"avg_gap": None, "consistency": None},
            "risk_penalty_score": {"avg_gap": None, "consistency": None},
            "agent_score": {"avg_gap": None, "consistency": None},
        }
        result = find_strongest_factors(factor_signals)
        assert result["strongest_positive"] is None
        assert result["strongest_negative"]["factor"] == "stock_short_score"


# ======================================================================
# Test: Markdown Generation
# ======================================================================

class TestMarkdownGeneration:
    def test_full_markdown(self):
        coverage = {"total_dates": 184, "valid_dates": 120, "total_candidates": 2100, "forward_samples": 2053}
        bucket_perf = {
            "decision_score": {
                "buckets": {
                    "high": {"count": 100, "avg_return": 1.5, "hit_rate": 55.0, "avg_drawdown": 3.0},
                    "mid": {"count": 100, "avg_return": 1.0, "hit_rate": 50.0, "avg_drawdown": 3.5},
                    "low": {"count": 100, "avg_return": 0.5, "hit_rate": 45.0, "avg_drawdown": 4.0},
                },
                "high_low_gap": 1.0,
                "hit_rate_diff": 10.0,
                "drawdown_diff": -1.0,
            },
        }
        rank_corrs = {
            "decision_score": {"avg_correlation": 0.03, "positive_date_count": 65, "negative_date_count": 55, "consistency": 54.2},
        }
        regime_data = {
            "broad_up": {
                "sample_count": 800,
                "factor_gaps": {"decision_score": {"gap": 1.5}},
                "trend_vs_burst": {"trend_avg_return": 2.0, "trend_count": 400, "burst_avg_return": 1.5, "burst_count": 400, "gap": 0.5},
                "agent_comparison": {"analyzed_avg_return": 2.0, "analyzed_count": 600, "skipped_avg_return": 1.5, "skipped_count": 200, "gap": 0.5},
            },
        }
        top_bottom = {
            "decision_score": {"top20_avg_return": 2.0, "bottom20_avg_return": 0.5, "gap": 1.5, "top20_hit_rate": 60.0, "bottom20_hit_rate": 40.0, "hit_rate_diff": 20.0, "top20_avg_drawdown": 2.5, "bottom20_avg_drawdown": 4.0, "drawdown_diff": -1.5},
        }
        trend_burst = {
            "trend": {"count": 1000, "avg_return": 1.5, "hit_rate": 55.0, "avg_drawdown": 3.0},
            "burst": {"count": 1000, "avg_return": 1.0, "hit_rate": 50.0, "avg_drawdown": 3.5},
            "both": {"count": 53, "avg_return": 1.2, "hit_rate": 52.0, "avg_drawdown": 3.2},
            "trend_burst_gap": 0.5,
        }
        agent_comp = {
            "analyzed": {"count": 1500, "avg_return": 1.5, "hit_rate": 55.0, "avg_drawdown": 3.0},
            "skipped": {"count": 553, "avg_return": 1.0, "hit_rate": 50.0, "avg_drawdown": 3.5},
            "gap": 0.5,
        }
        factor_signals = {
            "decision_score": {"signal": "inconclusive", "explanation": "test", "avg_gap": 1.0, "consistency": 54.2},
        }
        strongest = {"strongest_positive": {"factor": "decision_score", "gap": 1.0, "consistency": 54.2}, "strongest_negative": None}

        md = generate_markdown(
            coverage, bucket_perf, rank_corrs, regime_data,
            top_bottom, trend_burst, agent_comp,
            factor_signals, strongest, "2026-01-05_to_2026-07-08",
        )

        assert "Factor Signal Diagnosis" in md
        assert "120" in md
        assert "2100" in md
        assert "production_change_allowed" in md
        assert "false" in md
        assert "decision_score" in md

    def test_markdown_with_all_signals(self):
        """Test markdown includes all signal types."""
        factor_signals = {}
        for field in FACTOR_FIELDS:
            factor_signals[field] = {
                "signal": "inconclusive",
                "explanation": "test explanation",
                "avg_gap": 0.0,
                "consistency": 50.0,
            }
        coverage = {"total_dates": 10, "valid_dates": 10, "total_candidates": 100, "forward_samples": 100}
        md = generate_markdown(coverage, {}, {}, {}, {}, {}, {}, factor_signals, {}, "test")
        for field in FACTOR_FIELDS:
            assert field in md


# ======================================================================
# Test: Top/Bottom Analysis
# ======================================================================

class TestTopBottom:
    def test_basic_top_bottom(self):
        records = _make_records(30)
        result = compute_top_bottom_analysis(records)
        assert "decision_score" in result
        ds = result["decision_score"]
        assert ds["top20_count"] > 0
        assert ds["bottom20_count"] > 0
        assert ds["gap"] is not None

    def test_insufficient_samples(self):
        records = _make_records(5)
        result = compute_top_bottom_analysis(records)
        assert "error" in result["decision_score"]


# ======================================================================
# Test: Trend vs Burst
# ======================================================================

class TestTrendVsBurst:
    def test_basic_comparison(self):
        records = _make_records(30)
        result = compute_trend_vs_burst(records)
        assert result["trend"]["count"] > 0
        assert result["burst"]["count"] > 0
        assert result["trend_burst_gap"] is not None


# ======================================================================
# Test: Agent Comparison
# ======================================================================

class TestAgentComparison:
    def test_basic_comparison(self):
        records = _make_records(30)
        result = compute_agent_comparison(records)
        assert result["analyzed"]["count"] > 0
        assert result["skipped"]["count"] > 0
        assert result["gap"] is not None


# ======================================================================
# Test: Production Change Not Allowed
# ======================================================================

class TestProductionChange:
    def test_always_false(self):
        """production_change_allowed must always be false."""
        # This is enforced by the script design - the value is hardcoded as False
        # We verify it's in the output
        factor_signals = {}
        for field in FACTOR_FIELDS:
            factor_signals[field] = {"signal": "inconclusive", "explanation": "", "avg_gap": 0.0, "consistency": 50.0}
        coverage = {"total_dates": 10, "valid_dates": 10, "total_candidates": 100, "forward_samples": 100}
        md = generate_markdown(coverage, {}, {}, {}, {}, {}, {}, factor_signals, {}, "test")
        assert "production_change_allowed" in md
        assert "`false`" in md
