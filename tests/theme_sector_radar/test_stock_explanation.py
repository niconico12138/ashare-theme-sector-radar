"""
Stock Explanation 测试

覆盖：
- v2_opportunity -> v2_recovery
- core_watch -> trend_follow
- core_watch + confirmed -> consensus_confirmed
- burst_top -> short_burst
- divergence_review -> divergence_review
- blocked -> blocked
- reason_codes 正确生成
- invalidation_flags 正确生成
- low_final_high_v2 生成 historical_hint
- explanation_text 不包含 forbidden words
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.reporting.stock_explanation import build_stock_explanation


# ============================================================
# Forbidden Words
# ============================================================

FORBIDDEN_WORDS = [
    "buy", "sell", "hold",
    "买入", "卖出", "持有", "推荐",
    "建仓", "加仓", "减仓",
    "止盈", "止损", "目标价",
]


# ============================================================
# Tests
# ============================================================

class TestStockExplanation:
    """测试入池解释。"""

    def test_v2_opportunity_to_v2_recovery(self):
        """v2_opportunity 应生成 v2_recovery。"""
        candidate = {"selection_bucket": "v2_opportunity"}

        result = build_stock_explanation(candidate)

        assert result["opportunity_type"] == "v2_recovery"

    def test_core_watch_to_trend_follow(self):
        """core_watch 应生成 trend_follow。"""
        candidate = {"selection_bucket": "core_watch"}

        result = build_stock_explanation(candidate)

        assert result["opportunity_type"] == "trend_follow"

    def test_core_watch_confirmed_to_consensus_confirmed(self):
        """core_watch + v2_signal==confirmed 应生成 consensus_confirmed。"""
        candidate = {"selection_bucket": "core_watch"}
        profile = {"v2_signal": "confirmed"}

        result = build_stock_explanation(candidate, profile)

        assert result["opportunity_type"] == "consensus_confirmed"

    def test_burst_top_to_short_burst(self):
        """burst_top 应生成 short_burst。"""
        candidate = {"source_pool": "burst_top"}

        result = build_stock_explanation(candidate)

        assert result["opportunity_type"] == "short_burst"

    def test_divergence_review(self):
        """divergence_review 应生成 divergence_review。"""
        candidate = {"selection_bucket": "divergence_review"}

        result = build_stock_explanation(candidate)

        assert result["opportunity_type"] == "divergence_review"

    def test_blocked(self):
        """blocked 应生成 blocked。"""
        candidate = {"selection_bucket": "blocked"}

        result = build_stock_explanation(candidate)

        assert result["opportunity_type"] == "blocked"

    def test_reason_codes_generation(self):
        """reason_codes 应正确生成。"""
        candidate = {
            "selection_bucket": "core_watch",
            "source_pool": "trend_top",
        }
        profile = {
            "trend_state": "uptrend",
            "momentum_state": "strong",
            "risk_state": "low",
        }

        result = build_stock_explanation(candidate, profile)

        assert "core_watch" in result["reason_codes"]
        assert "trend_uptrend" in result["reason_codes"]
        assert "short_momentum_strong" in result["reason_codes"]
        assert "low_risk_profile" in result["reason_codes"]

    def test_invalidation_flags_generation(self):
        """invalidation_flags 应正确生成。"""
        candidate = {
            "selection_bucket": "core_watch",
            "data_quality": "ok",
        }
        profile = {
            "trend_state": "uptrend",
            "risk_state": "low",
            "sector_support": "strong",
            "volume_state": "confirmed",
        }

        result = build_stock_explanation(candidate, profile)

        assert "trend_score_deteriorates" in result["invalidation_flags"]
        assert "risk_score_rises" in result["invalidation_flags"]
        assert "sector_support_lost" in result["invalidation_flags"]
        assert "volume_confirmation_lost" in result["invalidation_flags"]

    def test_historical_hint_for_v2_recovery(self):
        """v2_recovery 应生成 historical_hint。"""
        candidate = {"selection_bucket": "v2_opportunity"}

        result = build_stock_explanation(candidate)

        assert result["historical_hint"]["matched_pattern"] == "low_final_high_v2"
        assert result["historical_hint"]["best_horizon"] == "10d"
        assert result["historical_hint"]["historical_5d_mean"] == 2.5995
        assert result["historical_hint"]["historical_10d_mean"] == 5.6829

    def test_historical_hint_for_other(self):
        """非 v2_recovery 应生成空 historical_hint。"""
        candidate = {"selection_bucket": "core_watch"}

        result = build_stock_explanation(candidate)

        assert result["historical_hint"]["matched_pattern"] == "none"
        assert result["historical_hint"]["historical_5d_mean"] is None

    def test_no_forbidden_words(self):
        """explanation_text 不应包含 forbidden words。"""
        candidate = {"selection_bucket": "core_watch"}

        result = build_stock_explanation(candidate)

        for word in FORBIDDEN_WORDS:
            assert word not in result["explanation_text"], f"Found forbidden word: {word}"


class TestNewFactorExplanation:
    """测试新因子对 stock_explanation 的影响。"""

    def test_liquidity_strong_reason_code(self):
        """liquidity_score >= 70 应生成 liquidity_strong reason code。"""
        candidate = {
            "selection_bucket": "core_watch",
            "liquidity_score": 75.0,
        }

        result = build_stock_explanation(candidate)

        assert "liquidity_strong" in result["reason_codes"]

    def test_liquidity_weak_reason_code(self):
        """liquidity_score < 40 应生成 liquidity_weak reason code。"""
        candidate = {
            "selection_bucket": "core_watch",
            "liquidity_score": 35.0,
        }

        result = build_stock_explanation(candidate)

        assert "liquidity_weak" in result["reason_codes"]

    def test_overheat_risk_high_reason_code(self):
        """chasing_risk_score >= 75 应生成 overheat_risk_high reason code。"""
        candidate = {
            "selection_bucket": "core_watch",
            "chasing_risk_score": 80.0,
        }

        result = build_stock_explanation(candidate)

        assert "overheat_risk_high" in result["reason_codes"]

    def test_healthy_drawdown_reason_code(self):
        """drawdown_depth_20 5-20 应生成 healthy_drawdown。"""
        candidate = {
            "selection_bucket": "v2_opportunity",
            "drawdown_depth_20": 10.0,
        }

        result = build_stock_explanation(candidate)

        assert "healthy_drawdown" in result["reason_codes"]

    def test_deep_drawdown_risk_reason_code(self):
        """drawdown_depth_20 > 35 应生成 deep_drawdown_risk。"""
        candidate = {
            "selection_bucket": "core_watch",
            "drawdown_depth_20": 40.0,
        }

        result = build_stock_explanation(candidate)

        assert "deep_drawdown_risk" in result["reason_codes"]

    def test_near_breakout_structure_reason_code(self):
        """breakout_distance_20 <= 5 应生成 near_breakout_structure。"""
        candidate = {
            "selection_bucket": "core_watch",
            "breakout_distance_20": 3.0,
        }

        result = build_stock_explanation(candidate)

        assert "near_breakout_structure" in result["reason_codes"]

    def test_overheat_risk_present_invalidation_flag(self):
        """chasing_risk_score >= 75 应生成 overheat_risk_present invalidation flag。"""
        candidate = {
            "selection_bucket": "core_watch",
            "chasing_risk_score": 80.0,
        }

        result = build_stock_explanation(candidate)

        assert "overheat_risk_present" in result["invalidation_flags"]

    def test_liquidity_weak_invalidation_flag(self):
        """liquidity_score < 40 应生成 liquidity_condition_weak invalidation flag。"""
        candidate = {
            "selection_bucket": "core_watch",
            "liquidity_score": 35.0,
        }

        result = build_stock_explanation(candidate)

        assert "liquidity_condition_weak" in result["invalidation_flags"]

    def test_drawdown_too_deep_invalidation_flag(self):
        """drawdown_depth_20 > 35 应生成 drawdown_too_deep invalidation flag。"""
        candidate = {
            "selection_bucket": "core_watch",
            "drawdown_depth_20": 40.0,
        }

        result = build_stock_explanation(candidate)

        assert "drawdown_too_deep" in result["invalidation_flags"]

    def test_sector_support_score_strong_reason_codes(self):
        """sector_support_score >= 65 应生成 sector_supported 和 sector_support_confirmed。"""
        candidate = {
            "selection_bucket": "core_watch",
            "sector_support_score": 70.0,
        }

        result = build_stock_explanation(candidate)

        assert "sector_supported_from_score" in result["reason_codes"]
        assert "sector_support_confirmed" in result["reason_codes"]

    def test_sector_support_score_weak_reason_codes(self):
        """sector_support_score < 50 应生成 sector_support_weak。"""
        candidate = {
            "selection_bucket": "core_watch",
            "sector_support_score": 40.0,
        }

        result = build_stock_explanation(candidate)

        assert "sector_support_weak" in result["reason_codes"]

    def test_sector_support_weak_invalidation_flag(self):
        """sector_support_score < 50 应生成 sector_support_weak_present invalidation flag。"""
        candidate = {
            "selection_bucket": "core_watch",
            "sector_support_score": 40.0,
        }

        result = build_stock_explanation(candidate)

        assert "sector_support_weak_present" in result["invalidation_flags"]
