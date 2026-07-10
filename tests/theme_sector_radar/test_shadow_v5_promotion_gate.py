"""Tests for shadow V5 promotion gate."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from audit_shadow_v5_promotion_gate import (
    evaluate_promotion_gate,
    generate_markdown,
    REGIMES,
    ROLLING_WINDOWS,
)


# ======================================================================
# Test: Promotion Gate Review Ready
# ======================================================================

class TestPromotionGate:
    def test_review_ready_when_all_pass(self):
        """When all checks pass, status should be review_ready."""
        overall_stats = {"v5_gap": 2.0, "production_gap": -0.1}
        rolling_results = {"60d_rolling": {"positive_window_share": 70}}
        outlier_analysis = {
            "max_single_date_contribution_share": 20,
            "max_single_stock_contribution_share": 10,
            "max_single_sector_contribution_share": 30,
        }
        regime_stability = {"positive_regime_count": 2}
        bucket_monotonicity = {"monotonicity": "positive"}

        result = evaluate_promotion_gate(
            overall_stats, rolling_results, outlier_analysis,
            regime_stability, bucket_monotonicity,
        )
        assert result["status"] == "review_ready"

    def test_blocked_when_many_failures(self):
        """When many checks fail, status should be blocked."""
        overall_stats = {"v5_gap": -1.0}
        rolling_results = {"60d_rolling": {"positive_window_share": 30}}
        outlier_analysis = {
            "max_single_date_contribution_share": 50,
            "max_single_stock_contribution_share": 30,
            "max_single_sector_contribution_share": 50,
        }
        regime_stability = {"positive_regime_count": 0}
        bucket_monotonicity = {"monotonicity": "negative"}

        result = evaluate_promotion_gate(
            overall_stats, rolling_results, outlier_analysis,
            regime_stability, bucket_monotonicity,
        )
        assert result["status"] == "blocked"

    def test_watch_when_few_failures(self):
        """When 1-2 checks fail, status should be watch."""
        overall_stats = {"v5_gap": 2.0}
        rolling_results = {"60d_rolling": {"positive_window_share": 70}}
        outlier_analysis = {
            "max_single_date_contribution_share": 20,
            "max_single_stock_contribution_share": 10,
            "max_single_sector_contribution_share": 30,
        }
        regime_stability = {"positive_regime_count": 1}  # Fails: need >= 2
        bucket_monotonicity = {"monotonicity": "positive"}

        result = evaluate_promotion_gate(
            overall_stats, rolling_results, outlier_analysis,
            regime_stability, bucket_monotonicity,
        )
        assert result["status"] == "watch"

    def test_production_change_always_false(self):
        """production_change_allowed must always be false."""
        result = evaluate_promotion_gate({}, {}, {}, {}, {})
        assert result["production_change_allowed"] is False


# ======================================================================
# Test: Check Details
# ======================================================================

class TestCheckDetails:
    def test_passed_checks_count(self):
        """Should count passed checks correctly."""
        overall_stats = {"v5_gap": 2.0}
        rolling_results = {"60d_rolling": {"positive_window_share": 70}}
        outlier_analysis = {
            "max_single_date_contribution_share": 20,
            "max_single_stock_contribution_share": 10,
            "max_single_sector_contribution_share": 30,
        }
        regime_stability = {"positive_regime_count": 2}
        bucket_monotonicity = {"monotonicity": "positive"}

        result = evaluate_promotion_gate(
            overall_stats, rolling_results, outlier_analysis,
            regime_stability, bucket_monotonicity,
        )
        assert len(result["passed_checks"]) == 7
        assert len(result["failed_checks"]) == 0

    def test_failed_checks_count(self):
        """Should count failed checks correctly."""
        overall_stats = {"v5_gap": -1.0}
        rolling_results = {"60d_rolling": {"positive_window_share": 30}}
        outlier_analysis = {
            "max_single_date_contribution_share": 50,
            "max_single_stock_contribution_share": 30,
            "max_single_sector_contribution_share": 50,
        }
        regime_stability = {"positive_regime_count": 0}
        bucket_monotonicity = {"monotonicity": "negative"}

        result = evaluate_promotion_gate(
            overall_stats, rolling_results, outlier_analysis,
            regime_stability, bucket_monotonicity,
        )
        assert len(result["failed_checks"]) == 7


# ======================================================================
# Test: Markdown Generation
# ======================================================================

class TestMarkdown:
    def test_markdown_structure(self):
        coverage = {"valid_dates": 120, "forward_samples": 2000}
        overall_stats = {"v5_gap": 2.0, "production_gap": -0.1}
        rolling_results = {"20d_rolling": {"available": False}}
        outlier_analysis = {
            "max_single_date_contribution_share": 20,
            "max_single_stock_contribution_share": 10,
            "max_single_sector_contribution_share": 30,
        }
        regime_stability = {"regimes": {}, "positive_regime_count": 2}
        bucket_monotonicity = {"bucket_stats": {}, "monotonicity": "positive"}
        promotion_gate = {"status": "review_ready", "production_change_allowed": False,
                          "passed_checks": [], "failed_checks": [], "reasons": []}

        md = generate_markdown(
            coverage, overall_stats, rolling_results,
            outlier_analysis, regime_stability, bucket_monotonicity,
            promotion_gate, "test_range",
        )
        assert "Shadow V5 Promotion Gate Audit" in md
        assert "production_change_allowed" in md
        assert "false" in md


# ======================================================================
# Test: Production Change Not Allowed
# ======================================================================

class TestProductionChange:
    def test_always_false_in_markdown(self):
        coverage = {"valid_dates": 10, "forward_samples": 100}
        overall_stats = {}
        rolling_results = {}
        outlier_analysis = {}
        regime_stability = {"regimes": {}, "positive_regime_count": 0}
        bucket_monotonicity = {"bucket_stats": {}, "monotonicity": "inconclusive"}
        promotion_gate = {"status": "blocked", "production_change_allowed": False,
                          "passed_checks": [], "failed_checks": [], "reasons": []}

        md = generate_markdown(
            coverage, overall_stats, rolling_results,
            outlier_analysis, regime_stability, bucket_monotonicity,
            promotion_gate, "test",
        )
        assert "`false`" in md
        assert "production_change_allowed" in md

    def test_gate_always_false(self):
        """Promotion gate must always have production_change_allowed = False."""
        result = evaluate_promotion_gate({}, {}, {}, {}, {})
        assert result["production_change_allowed"] is False
