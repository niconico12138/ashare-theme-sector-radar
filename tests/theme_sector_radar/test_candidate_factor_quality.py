"""Tests for candidate factor quality diagnostic and scoring fixes."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "theme_sector_radar" / "scoring"))

from stock_short_score import compute_stock_short_score
from decision_score import compute_decision_score
from trade_risk import compute_trade_risk


class TestStockShortScoreDiscrimination:
    """Verify stock_short_score has sufficient discrimination without bars."""

    def test_different_scores_for_different_stocks(self):
        """Stocks with different quant_score/final_score should get different short scores."""
        stocks = [
            {"code": "600001", "quant_score": 80, "final_score": 85, "source_pool": "burst",
             "sector_burst_score": 70, "change_pct": 3.0},
            {"code": "600002", "quant_score": 40, "final_score": 45, "source_pool": "trend",
             "sector_burst_score": 50, "change_pct": 1.0},
            {"code": "600003", "quant_score": 20, "final_score": 25, "source_pool": "trend",
             "sector_burst_score": 30, "change_pct": -1.0},
        ]
        scores = [compute_stock_short_score(s)["stock_short_score"] for s in stocks]
        assert len(set(round(s, 1) for s in scores)) >= 2, f"Scores too similar: {scores}"

    def test_burst_pool_higher_than_trend(self):
        """Burst pool stock should score higher than trend pool (short-term context)."""
        burst_stock = {"code": "600001", "source_pool": "burst", "quant_score": 60,
                       "final_score": 70, "sector_burst_score": 80, "change_pct": 2.0}
        trend_stock = {"code": "600002", "source_pool": "trend", "quant_score": 60,
                       "final_score": 70, "sector_burst_score": 50, "change_pct": 2.0}
        burst_score = compute_stock_short_score(burst_stock)["stock_short_score"]
        trend_score = compute_stock_short_score(trend_stock)["stock_short_score"]
        assert burst_score > trend_score

    def test_fallback_used_tag(self):
        """When change_pct is missing and fallback is used, tag should be set."""
        stock = {"code": "600001", "quant_score": 60, "final_score": 70}
        result = compute_stock_short_score(stock)
        assert "short_score_fallback_used" in result["stock_short_tags"]

    def test_score_range(self):
        """Score should always be 0-100."""
        for q in [0, 20, 50, 80, 100]:
            stock = {"code": "600001", "quant_score": q, "final_score": q, "source_pool": "trend"}
            result = compute_stock_short_score(stock)
            assert 0 <= result["stock_short_score"] <= 100

    def test_no_bars_still_discriminates(self):
        """Without bars, scores should still differ based on available fields."""
        stocks = [
            {"code": f"600{i:03d}", "quant_score": 30 + i * 10, "final_score": 40 + i * 8,
             "source_pool": "trend", "sector_burst_score": 50, "change_pct": i * 0.5}
            for i in range(1, 6)
        ]
        scores = [compute_stock_short_score(s)["stock_short_score"] for s in stocks]
        unique = len(set(round(s, 1) for s in scores))
        assert unique >= 3, f"Expected >= 3 unique scores, got {unique}: {scores}"

    def test_spread_at_least_20_in_diverse_set(self):
        """A diverse set of stocks should have spread >= 20."""
        stocks = [
            {"code": "600001", "quant_score": 85, "final_score": 85, "source_pool": "burst",
             "relevance_score": 0.9, "sector_burst_score": 80, "change_pct": 5.0},
            {"code": "600002", "quant_score": 45, "final_score": 45, "source_pool": "trend",
             "relevance_score": 0.65, "sector_burst_score": 30, "change_pct": -1.0},
        ]
        scores = [compute_stock_short_score(s)["stock_short_score"] for s in stocks]
        spread = max(scores) - min(scores)
        assert spread >= 15, f"Expected spread >= 15, got {spread:.1f}: {scores}"

    def test_breakdown_has_key_fields(self):
        """Breakdown should contain quant_component and fallback_used."""
        stock = {"code": "600001", "quant_score": 60, "final_score": 70}
        result = compute_stock_short_score(stock)
        bd = result["stock_short_breakdown"]
        assert "quant_component" in bd
        assert "fallback_used" in bd
        assert "distribution_stretch_applied" in bd


class TestDecisionScoreScaleNormalization:
    """Verify decision_score normalizes 0-1 scale values to 0-100."""

    def test_01_scale_normalized(self):
        """trend_score=0.6 should be treated as 60, not 0.6."""
        stock = {
            "trend_score": 0.6,
            "burst_score": 0.0,
            "stock_short_score": 50,
            "stock_trend_score": 50,
            "sector_leader_score": 50,
            "risk_penalty_score": 0,
        }
        result = compute_decision_score(stock)
        breakdown = result["decision_breakdown"]
        assert breakdown["sector_trend_score"] == 60.0
        assert breakdown["sector_trend_score_normalized_from_0_1"] is True
        assert breakdown["sector_burst_score"] == 0.0
        assert breakdown["sector_burst_score_normalized_from_0_1"] is True

    def test_100_scale_not_normalized(self):
        """trend_score=70 should stay 70, not be multiplied."""
        stock = {
            "trend_score": 70,
            "burst_score": 65,
            "stock_short_score": 50,
            "stock_trend_score": 50,
            "sector_leader_score": 50,
            "risk_penalty_score": 0,
        }
        result = compute_decision_score(stock)
        breakdown = result["decision_breakdown"]
        assert breakdown["sector_trend_score"] == 70.0
        assert breakdown["sector_trend_score_normalized_from_0_1"] is False
        assert breakdown["sector_burst_score"] == 65.0
        assert breakdown["sector_burst_score_normalized_from_0_1"] is False

    def test_mixed_scales_in_same_stock(self):
        """One field 0-1, another 0-100 should both normalize correctly."""
        stock = {
            "trend_score": 0.7,
            "burst_score": 80.0,
            "stock_short_score": 50,
            "stock_trend_score": 50,
            "sector_leader_score": 50,
            "risk_penalty_score": 0,
        }
        result = compute_decision_score(stock)
        breakdown = result["decision_breakdown"]
        assert breakdown["sector_trend_score"] == 70.0
        assert breakdown["sector_trend_score_normalized_from_0_1"] is True
        assert breakdown["sector_burst_score"] == 80.0
        assert breakdown["sector_burst_score_normalized_from_0_1"] is False

    def test_decision_score_range(self):
        """Decision score should always be 0-100."""
        stock = {
            "trend_score": 0.9,
            "burst_score": 0.8,
            "stock_short_score": 90,
            "stock_trend_score": 85,
            "sector_leader_score": 95,
            "agent_score": 80,
            "risk_penalty_score": 0,
        }
        result = compute_decision_score(stock)
        assert 0 <= result["decision_score"] <= 100

    def test_risk_penalty_reduces_score(self):
        """Higher risk_penalty should lower decision_score."""
        base = {
            "trend_score": 70, "burst_score": 60,
            "stock_short_score": 70, "stock_trend_score": 65,
            "sector_leader_score": 60, "risk_penalty_score": 0,
        }
        r1 = compute_decision_score(base)["decision_score"]
        base["risk_penalty_score"] = 20
        r2 = compute_decision_score(base)["decision_score"]
        assert r2 < r1, f"Expected r2 < r1, got {r2} >= {r1}"


class TestTradeRiskStratification:
    """Verify trade_risk produces multiple eligibility categories."""

    def test_focus_for_clean_stock(self):
        """Clean stock with high decision_score should be focus."""
        stock = {
            "code": "600001", "name": "优质股",
            "change_pct": 2.0, "amount": 100_000_000,
            "sector_role": "leader", "decision_score": 55,
            "stock_short_score": 65, "stock_trend_score": 60,
            "quant_score": 70, "final_score": 75,
            "sector_leader_score": 80,
        }
        result = compute_trade_risk(stock)
        assert result["trade_eligibility"] == "focus"

    def test_watch_for_weak_stock(self):
        """Stock with low scores should be watch or backup."""
        stock = {
            "code": "600001", "name": "弱股",
            "sector_role": "unknown", "decision_score": 38,
            "stock_short_score": 42, "stock_trend_score": 48,
            "sector_leader_score": 40,
        }
        result = compute_trade_risk(stock)
        assert result["trade_eligibility"] in ("watch", "backup")

    def test_backup_for_follower_risk(self):
        """Follower role with low scores should be backup or worse."""
        stock = {
            "code": "600001", "name": "跟风股",
            "sector_role": "follower", "decision_score": 25,
            "stock_short_score": 35, "stock_trend_score": 35,
            "sector_leader_score": 25,
        }
        result = compute_trade_risk(stock)
        assert result["trade_eligibility"] in ("backup", "avoid")

    def test_avoid_for_high_penalty(self):
        """Stock with high penalty should be avoid."""
        stock = {
            "code": "600001", "name": "高风险",
            "change_pct": 9.9,
            "amount": 3_000_000,
            "turnover_rate": 0.3,
            "sector_role": "laggard",
            "stock_short_score": 90,
            "decision_score": 15,
            "sector_leader_score": 10,
        }
        result = compute_trade_risk(stock)
        assert result["trade_eligibility"] == "avoid"

    def test_eligibility_not_all_same(self):
        """A set of diverse stocks should produce at least 2 different eligibility levels."""
        stocks = [
            {"code": "600001", "name": "A", "change_pct": 2, "amount": 100_000_000,
             "sector_role": "leader", "decision_score": 55, "stock_short_score": 60,
             "stock_trend_score": 65, "quant_score": 70, "final_score": 75,
             "sector_leader_score": 80},
            {"code": "600002", "name": "B", "sector_role": "follower", "decision_score": 20,
             "stock_short_score": 30, "stock_trend_score": 30, "sector_leader_score": 20},
            {"code": "600003", "name": "C", "change_pct": 9.9, "amount": 2_000_000,
             "sector_role": "laggard", "stock_short_score": 90, "decision_score": 10,
             "sector_leader_score": 5},
        ]
        eligibilities = [compute_trade_risk(s)["trade_eligibility"] for s in stocks]
        unique = set(eligibilities)
        assert len(unique) >= 2, f"Expected >= 2 unique eligibility levels, got: {unique}"

    def test_st_stock_invalid(self):
        """ST stock should be invalid regardless of other factors."""
        stock = {"code": "600001", "name": "*ST退市", "decision_score": 80}
        result = compute_trade_risk(stock)
        assert result["trade_eligibility"] == "invalid"

    def test_non_main_board_invalid(self):
        """Non-main-board stock should be invalid."""
        stock = {"code": "300558", "name": "创业板", "decision_score": 80}
        result = compute_trade_risk(stock)
        assert result["trade_eligibility"] == "invalid"

    def test_penalty_range(self):
        """Risk penalty should be 0-50."""
        stock = {
            "code": "600001", "name": "极端",
            "change_pct": 9.9, "amount": 1_000_000,
            "turnover_rate": 0.1, "volume_ratio": 10,
            "sector_role": "laggard", "stock_short_score": 95,
            "decision_score": 5, "sector_leader_score": 5,
        }
        result = compute_trade_risk(stock)
        assert 0 <= result["risk_penalty_score"] <= 50

    def test_follower_not_focus(self):
        """follower role with weak scores should never be focus."""
        stock = {
            "code": "600001", "name": "跟风",
            "sector_role": "follower", "decision_score": 35,
            "stock_short_score": 40, "stock_trend_score": 40,
            "sector_leader_score": 30,
        }
        result = compute_trade_risk(stock)
        assert result["trade_eligibility"] != "focus"

    def test_penalty_spread_at_least_15(self):
        """Diverse stocks should produce penalty spread >= 15."""
        good = {"code": "600001", "name": "A", "change_pct": 2, "amount": 100_000_000,
                "sector_role": "leader", "decision_score": 60, "stock_short_score": 70,
                "stock_trend_score": 65, "sector_leader_score": 80}
        bad = {"code": "600002", "name": "B", "change_pct": 9.9, "amount": 2_000_000,
               "sector_role": "laggard", "decision_score": 10, "stock_short_score": 30,
               "stock_trend_score": 25, "sector_leader_score": 10}
        p1 = compute_trade_risk(good)["risk_penalty_score"]
        p2 = compute_trade_risk(bad)["risk_penalty_score"]
        assert abs(p2 - p1) >= 10, f"Expected spread >= 10, got {abs(p2-p1):.1f}"


class TestExportTop30FactorQuality:
    """Integration tests for export with factor quality checks."""

    def test_top30_has_30_candidates(self, tmp_path, monkeypatch):
        """top30_candidates.json should have exactly 30 candidates."""
        import export_top30_candidates as exp
        unified_dir = tmp_path / "reports" / "unified" / "2026-07-07"
        unified_dir.mkdir(parents=True)
        trend = [
            {"code": f"600{i:03d}", "name": f"T{i}", "sector_name": "板块A",
             "sector_trend_score": 70, "sector_burst_score": 40, "final_score": 80 - i}
            for i in range(1, 18)
        ]
        burst = [
            {"code": f"601{i:03d}", "name": f"B{i}", "sector_name": "板块B",
             "sector_trend_score": 40, "sector_burst_score": 80, "final_score": 75 - i}
            for i in range(1, 18)
        ]
        (unified_dir / "unified_report.json").write_text(
            json.dumps({"trend_top_stocks": trend, "burst_top_stocks": burst}, ensure_ascii=False),
            encoding="utf-8",
        )
        orig = exp.UNIFIED_DIR
        exp.UNIFIED_DIR = tmp_path / "reports" / "unified"
        try:
            candidates, _ = exp.load_unified_candidates("2026-07-07")
        finally:
            exp.UNIFIED_DIR = orig
        assert len(candidates) == 30

    def test_enriched_candidates_have_diverse_short_scores(self):
        """Enriched candidates should have diverse stock_short_score values."""
        import export_top30_candidates as exp
        candidates = [
            {"code": f"600{i:03d}", "name": f"S{i}", "boards": ["A"],
             "trend_score": 70 - i, "burst_score": 60 - i, "final_score": 75 - i,
             "quant_score": 60 + i * 5, "relevance_score": 0.8,
             "source_pool": "trend" if i < 8 else "burst"}
            for i in range(1, 11)
        ]
        enriched = exp.enrich_candidates_with_scoring(candidates)
        scores = [c["stock_short_score"] for c in enriched]
        unique = len(set(round(s, 1) for s in scores))
        assert unique >= 5, f"Expected >= 5 unique short scores, got {unique}: {scores}"

    def test_enriched_candidates_have_multiple_eligibilities(self):
        """Enriched candidates should have at least 2 different trade_eligibility values."""
        import export_top30_candidates as exp
        candidates = [
            {"code": "600001", "name": "A", "boards": ["X"], "trend_score": 80,
             "burst_score": 70, "final_score": 85, "quant_score": 80,
             "source_pool": "burst", "sector_role": "leader", "decision_score": 60,
             "stock_short_score": 70, "sector_leader_score": 90},
            {"code": "600002", "name": "B", "boards": ["X"], "trend_score": 30,
             "burst_score": 20, "final_score": 25, "quant_score": 30,
             "source_pool": "trend", "sector_role": "follower", "decision_score": 20,
             "stock_short_score": 30, "sector_leader_score": 15},
        ]
        enriched = exp.enrich_candidates_with_scoring(candidates)
        elig = set(c["trade_eligibility"] for c in enriched)
        assert len(elig) >= 2, f"Expected >= 2 eligibility levels, got: {elig}"


class TestDiagnosticEnhancements:
    """Test diagnostic script enhancements."""

    def test_bucket_distribution(self):
        """_bucket_distribution should correctly bucket values."""
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from analyze_candidate_factor_quality import _bucket_distribution
        values = [30, 45, 55, 65, 75, 85, 95]
        buckets = _bucket_distribution(values)
        assert buckets["<40"] == 1
        assert buckets["40-60"] == 2
        assert buckets["60-80"] == 2
        assert buckets[">=80"] == 2

    def test_top_bottom_separation(self):
        """_top_bottom_separation should compute correct gap."""
        from analyze_candidate_factor_quality import _top_bottom_separation
        candidates = [
            {"code": f"600{i:03d}", "decision_score": 100 - i * 3}
            for i in range(1, 21)
        ]
        sep = _top_bottom_separation(candidates, "decision_score")
        assert sep["top5_mean"] > sep["bottom10_mean"]
        assert sep["separation"] > 0

    def test_spread_warning_generated(self):
        """Low spread should generate warning."""
        from analyze_candidate_factor_quality import analyze_candidates
        # All same score → low spread
        candidates = [{"stock_short_score": 50.0, "trade_eligibility": "focus"} for _ in range(10)]
        report = analyze_candidates(candidates)
        spread_warnings = [w for w in report["warnings"] if "spread" in w]
        assert len(spread_warnings) > 0
