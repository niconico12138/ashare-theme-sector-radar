"""Tests for next-day selection validation."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from evaluate_next_day_selection import (
    _compute_group_stats,
    _split_by_quantile,
    _interpret_signal,
    run_validation,
    generate_markdown,
)


class TestGroupStats:
    """Test _compute_group_stats function."""

    def test_empty_returns(self):
        result = _compute_group_stats([], [], [])
        assert result["sample_count"] == 0
        assert result["avg_next_return_pct"] is None

    def test_single_return(self):
        result = _compute_group_stats([2.5], [3.0], [1.0])
        assert result["sample_count"] == 1
        assert result["avg_next_return_pct"] == 2.5
        assert result["hit_rate_positive"] == 100.0

    def test_mixed_returns(self):
        result = _compute_group_stats([3.0, -1.0, 2.0], [4.0, 0.5, 3.0], [1.0, -2.0, 0.5])
        assert result["sample_count"] == 3
        assert abs(result["avg_next_return_pct"] - 1.3333) < 0.01
        assert result["hit_rate_positive"] == pytest.approx(66.67, abs=0.1)
        assert result["best_next_return_pct"] == 3.0
        assert result["worst_next_return_pct"] == -1.0


class TestSplitByQuantile:
    """Test _split_by_quantile function."""

    def test_three_groups(self):
        candidates = [
            {"code": f"600{i:03d}", "score": i * 10}
            for i in range(1, 10)
        ]
        groups = _split_by_quantile(candidates, "score", 3)
        assert "high" in groups
        assert "mid" in groups
        assert "low" in groups
        total = sum(len(g) for g in groups.values())
        assert total == 9

    def test_high_group_has_highest_scores(self):
        candidates = [
            {"code": "A", "score": 90},
            {"code": "B", "score": 50},
            {"code": "C", "score": 10},
        ]
        groups = _split_by_quantile(candidates, "score", 3)
        high_codes = [c["code"] for c in groups["high"]]
        assert "A" in high_codes


class TestInterpretSignal:
    """Test _interpret_signal function."""

    def test_positive_signal(self):
        top = {"sample_count": 10, "avg_next_return_pct": 5.0}
        bot = {"sample_count": 10, "avg_next_return_pct": 1.0}
        result = _interpret_signal(top, bot)
        assert result["signal"] == "positive"
        assert result["gap_pct"] == 4.0

    def test_negative_signal(self):
        top = {"sample_count": 10, "avg_next_return_pct": 1.0}
        bot = {"sample_count": 10, "avg_next_return_pct": 5.0}
        result = _interpret_signal(top, bot)
        assert result["signal"] == "negative"

    def test_inconclusive_signal(self):
        top = {"sample_count": 10, "avg_next_return_pct": 3.0}
        bot = {"sample_count": 10, "avg_next_return_pct": 2.5}
        result = _interpret_signal(top, bot)
        assert result["signal"] == "inconclusive"

    def test_insufficient_samples(self):
        top = {"sample_count": 2, "avg_next_return_pct": 5.0}
        bot = {"sample_count": 10, "avg_next_return_pct": 1.0}
        result = _interpret_signal(top, bot, min_samples=5)
        assert result["signal"] == "insufficient_samples"

    def test_none_groups(self):
        result = _interpret_signal(None, None)
        assert result["signal"] == "insufficient_samples"


class TestRunValidation:
    """Test run_validation with synthetic data."""

    def _make_candidate(self, code, decision_score, trade_eligibility, source_pool, agent_status="pending_agent_analysis"):
        return {
            "code": code, "name": f"Stock{code}",
            "decision_score": decision_score,
            "stock_short_score": decision_score * 0.9,
            "stock_trend_score": decision_score * 0.8,
            "trade_eligibility": trade_eligibility,
            "source_pool": source_pool,
            "agent_analysis_status": agent_status,
        }

    def test_basic_validation_runs(self):
        candidates = [
            self._make_candidate("600001", 80, "focus", "trend"),
            self._make_candidate("600002", 60, "watch", "burst"),
            self._make_candidate("600003", 40, "backup", "trend"),
        ]
        bar_data = {
            "600001": {"data_available": True, "next_return_pct": 2.0, "next_high_return_pct": 3.0, "next_low_return_pct": 1.0},
            "600002": {"data_available": True, "next_return_pct": -1.0, "next_high_return_pct": 0.5, "next_low_return_pct": -2.0},
            "600003": {"data_available": True, "next_return_pct": 0.5, "next_high_return_pct": 1.5, "next_low_return_pct": -0.5},
        }
        report = run_validation(candidates, bar_data, [], "2026-07-07")
        assert report["coverage"]["data_available"] == 3
        assert "ranking_groups" in report
        assert "score_buckets" in report
        assert "categorical_groups" in report
        assert "interpretation" in report

    def test_missing_data_handled(self):
        candidates = [self._make_candidate("600001", 80, "focus", "trend")]
        bar_data = {"600001": {"data_available": False}}
        report = run_validation(candidates, bar_data, [], "2026-07-07")
        assert report["coverage"]["data_missing"] == 1
        assert report["coverage"]["data_available"] == 0

    def test_top5_group_correct(self):
        candidates = [
            self._make_candidate(f"600{i:03d}", 100 - i * 5, "focus", "trend")
            for i in range(1, 11)
        ]
        bar_data = {
            f"600{i:03d}": {"data_available": True, "next_return_pct": float(i),
                             "next_high_return_pct": float(i + 1), "next_low_return_pct": float(i - 1)}
            for i in range(1, 11)
        }
        report = run_validation(candidates, bar_data, [], "2026-07-07")
        top5 = report["ranking_groups"]["top5_by_decision_score"]
        assert top5["sample_count"] == 5

    def test_trade_eligibility_groups(self):
        candidates = [
            self._make_candidate("600001", 80, "focus", "trend"),
            self._make_candidate("600002", 60, "watch", "burst"),
            self._make_candidate("600003", 40, "backup", "trend"),
            self._make_candidate("600004", 20, "avoid", "burst"),
        ]
        bar_data = {
            f"60000{i}": {"data_available": True, "next_return_pct": float(i),
                           "next_high_return_pct": float(i + 1), "next_low_return_pct": float(i - 1)}
            for i in range(1, 5)
        }
        report = run_validation(candidates, bar_data, [], "2026-07-07")
        cat = report["categorical_groups"]
        assert cat["trade_eligibility_focus"]["sample_count"] == 1
        assert cat["trade_eligibility_watch"]["sample_count"] == 1
        assert cat["trade_eligibility_backup"]["sample_count"] == 1
        assert cat["trade_eligibility_avoid"]["sample_count"] == 1

    def test_analyzed_vs_skipped(self):
        candidates = [
            self._make_candidate("600001", 80, "focus", "trend", "pending_agent_analysis"),
            self._make_candidate("600002", 60, "watch", "burst", "skipped_by_agent_stock_limit"),
        ]
        bar_data = {
            "600001": {"data_available": True, "next_return_pct": 1.0, "next_high_return_pct": 2.0, "next_low_return_pct": 0.0},
            "600002": {"data_available": True, "next_return_pct": -0.5, "next_high_return_pct": 0.5, "next_low_return_pct": -1.0},
        }
        report = run_validation(candidates, bar_data, [], "2026-07-07")
        cat = report["categorical_groups"]
        assert cat["analyzed"]["sample_count"] == 1
        assert cat["skipped_by_agent_stock_limit"]["sample_count"] == 1

    def test_agent_score_missing_bucket(self):
        candidates = [
            self._make_candidate("600001", 80, "focus", "trend"),
        ]
        bar_data = {"600001": {"data_available": True, "next_return_pct": 1.0, "next_high_return_pct": 2.0, "next_low_return_pct": 0.0}}
        # No ranking → agent_score is None
        report = run_validation(candidates, bar_data, [], "2026-07-07")
        assert report["score_buckets"]["agent_score_missing"]["sample_count"] == 1

    def test_interpretation_has_all_keys(self):
        candidates = [self._make_candidate("600001", 80, "focus", "trend")]
        bar_data = {"600001": {"data_available": True, "next_return_pct": 1.0, "next_high_return_pct": 2.0, "next_low_return_pct": 0.0}}
        report = run_validation(candidates, bar_data, [], "2026-07-07")
        interp = report["interpretation"]
        assert "decision_score_signal" in interp
        assert "stock_short_score_signal" in interp
        assert "trade_eligibility_signal" in interp
        assert "agent_incremental_signal" in interp
        assert "analyzed_vs_skipped_signal" in interp
        assert "trend_vs_burst_signal" in interp
        assert "caution" in interp

    def test_insufficient_samples_when_few_data(self):
        candidates = [
            self._make_candidate("600001", 80, "focus", "trend"),
            self._make_candidate("600002", 60, "watch", "burst"),
        ]
        bar_data = {
            "600001": {"data_available": True, "next_return_pct": 1.0, "next_high_return_pct": 2.0, "next_low_return_pct": 0.0},
            "600002": {"data_available": True, "next_return_pct": -0.5, "next_high_return_pct": 0.5, "next_low_return_pct": -1.0},
        }
        report = run_validation(candidates, bar_data, [], "2026-07-07")
        # With only 2 samples, groups should be small → insufficient_samples
        interp = report["interpretation"]
        # At least some signals should be insufficient_samples due to small n
        signals = [interp[k]["signal"] for k in interp if k != "caution"]
        assert "insufficient_samples" in signals


class TestMarkdown:
    """Test markdown report generation."""

    def test_markdown_contains_key_sections(self):
        report = {
            "as_of": "2026-07-07",
            "generated_at": "2026-07-09T12:00:00",
            "coverage": {"total_candidates": 30, "data_available": 29, "data_missing": 1, "missing_codes": ["601369"]},
            "ranking_groups": {
                "top5_by_decision_score": {"sample_count": 5, "avg_next_return_pct": -6.47, "hit_rate_positive": 0.0},
                "bottom10_by_decision_score": {"sample_count": 10, "avg_next_return_pct": -3.75, "hit_rate_positive": 0.0},
            },
            "score_buckets": {},
            "categorical_groups": {
                "trade_eligibility_focus": {"sample_count": 7, "avg_next_return_pct": -3.97, "hit_rate_positive": 0.0},
                "analyzed": {"sample_count": 10, "avg_next_return_pct": -5.39, "hit_rate_positive": 0.0},
                "skipped_by_agent_stock_limit": {"sample_count": 19, "avg_next_return_pct": -2.90, "hit_rate_positive": 5.3},
                "source_pool_trend": {"sample_count": 15, "avg_next_return_pct": -3.57, "hit_rate_positive": 0.0},
                "source_pool_burst": {"sample_count": 14, "avg_next_return_pct": -3.96, "hit_rate_positive": 7.1},
            },
            "interpretation": {
                "decision_score_signal": {"signal": "negative", "gap_pct": -2.72},
                "stock_short_score_signal": {"signal": "negative", "gap_pct": -2.33},
                "trade_eligibility_signal": {"signal": "inconclusive", "gap_pct": -0.43},
                "agent_incremental_signal": {"signal": "insufficient_samples", "reason": "top_n=9, bot_n=0 < 5"},
                "analyzed_vs_skipped_signal": {"signal": "negative", "gap_pct": -2.48},
                "trend_vs_burst_signal": {"signal": "inconclusive", "gap_pct": -0.39},
                "caution": "single-day validation only; not enough for weight changes",
            },
        }
        md = generate_markdown(report)
        assert "Next-Day Selection Validation" in md
        assert "Data Coverage" in md
        assert "Score Bucket Validation" in md
        assert "Trade Eligibility Validation" in md
        assert "Agent Incremental Validation" in md
        assert "Trend vs Burst Validation" in md
        assert "Interpretation" in md
        assert "Cautions" in md
        assert "single-day validation only" in md
        assert "601369" in md
