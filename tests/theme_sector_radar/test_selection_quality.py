"""
Selection Quality 测试

覆盖：
- core_watch 分类正确
- v2_opportunity 分类正确
- divergence_review 分类正确
- blocked 分类正确
- hard_blocker 生效
- soft_warning 不阻断
- 去重优先级正确
- selection_score 限制在 0-100
- pool_quality ok/warn/fail 正确
- action_state 恒定为 watch_only
- 不包含 forbidden words
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from theme_sector_radar.reporting.selection_quality import (
    classify_stock_candidate,
    build_eligible_watchlist,
)


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

class TestClassifyStockCandidate:
    """测试候选股分类。"""

    def test_core_watch_classification(self):
        """core_watch 应正确分类。"""
        candidate = {
            "code": "600001",
            "name": "测试股",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert result["selection_bucket"] == "core_watch"
        assert result["quality_level"] == "ok"
        assert result["action_state"] == "watch_only"

    def test_v2_opportunity_classification(self):
        """v2_opportunity 应正确分类。"""
        candidate = {
            "code": "600001",
            "name": "测试股",
            "final_score": 30.0,
            "v2_score": 80.0,
            "signal_type": "low_final_high_v2",
            "data_quality": "ok",
        }

        result = classify_stock_candidate(candidate, "v2_potential")

        assert result["selection_bucket"] == "v2_opportunity"
        assert result["quality_level"] == "ok"
        assert result["action_state"] == "watch_only"

    def test_divergence_review_classification(self):
        """divergence_review 应正确分类。"""
        candidate = {
            "code": "600001",
            "name": "测试股",
            "final_score": 80.0,
            "v2_score": 30.0,
            "signal_type": "high_final_low_v2",
            "data_quality": "ok",
        }

        result = classify_stock_candidate(candidate, "divergence_review")

        assert result["selection_bucket"] == "divergence_review"
        assert result["quality_level"] == "ok"
        assert result["action_state"] == "watch_only"

    def test_blocked_classification(self):
        """blocked 应正确分类。"""
        candidate = {
            "code": "600001",
            "name": "测试股",
            "final_score": 50.0,
            "v2_score": 50.0,
            "data_quality": "ok",
        }

        result = classify_stock_candidate(candidate, "trend_top")

        # final_score < 55 应该是 blocked
        assert result["selection_bucket"] == "blocked"
        assert result["action_state"] == "watch_only"

    def test_hard_blocker_missing_code(self):
        """missing_code 应触发 hard_blocker。"""
        candidate = {
            "code": "",
            "name": "测试股",
            "final_score": 75.0,
            "data_quality": "ok",
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert "missing_code" in result["hard_blockers"]
        assert result["selection_bucket"] == "blocked"

    def test_hard_blocker_missing_name(self):
        """missing_name 应触发 hard_blocker。"""
        candidate = {
            "code": "600001",
            "name": "",
            "final_score": 75.0,
            "data_quality": "ok",
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert "missing_name" in result["hard_blockers"]
        assert result["selection_bucket"] == "blocked"

    def test_hard_blocker_data_missing(self):
        """data_missing 应触发 hard_blocker。"""
        candidate = {
            "code": "600001",
            "name": "测试股",
            "final_score": 75.0,
            "data_quality": "missing",
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert "data_missing" in result["hard_blockers"]
        assert result["selection_bucket"] == "blocked"

    def test_soft_warning_partial_data(self):
        """partial data 应触发 soft_warning。"""
        candidate = {
            "code": "600001",
            "name": "测试股",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "partial",
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert "partial_data" in result["soft_warnings"]
        assert result["quality_level"] == "warn"
        assert result["selection_bucket"] == "core_watch"

    def test_selection_score_limit(self):
        """selection_score 应限制在 0-100。"""
        candidate = {
            "code": "600001",
            "name": "测试股",
            "final_score": 150.0,
            "v2_score": 150.0,
            "data_quality": "ok",
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert 0 <= result["selection_score"] <= 100

    def test_v2_score_fallback_to_factor_composite(self):
        """v2_score 缺失但 factor_composite_shadow_score_v2 存在时应能用于 selection_score。"""
        candidate = {
            "code": "600001",
            "name": "测试股",
            "final_score": 75.0,
            "factor_composite_shadow_score_v2": 80.0,
            "data_quality": "ok",
        }

        result = classify_stock_candidate(candidate, "trend_top")

        # 应该能正常分类，不因 v2_score 缺失而报错
        assert result["selection_bucket"] == "core_watch"
        assert result["selection_score"] > 0

    def test_final_score_none_not_zero(self):
        """final_score 缺失时应保持 None，不输出 0。"""
        candidate = {
            "code": "600001",
            "name": "测试股",
            "v2_score": 80.0,
            "data_quality": "ok",
        }

        result = classify_stock_candidate(candidate, "trend_top")

        # final_score 缺失时，scores_missing 不应触发（因为 v2_score 存在）
        assert "scores_missing" not in result["hard_blockers"]

    def test_scores_missing_only_when_both_missing(self):
        """scores_missing 只在 final 和 v2 都缺失时触发。"""
        candidate = {
            "code": "600001",
            "name": "测试股",
            "data_quality": "ok",
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert "scores_missing" in result["hard_blockers"]

    def test_final_score_zero_is_valid(self):
        """final_score=0 是有效数值，不等同缺失。"""
        candidate = {
            "code": "600001",
            "name": "测试股",
            "final_score": 0.0,
            "v2_score": 80.0,
            "data_quality": "ok",
        }

        result = classify_stock_candidate(candidate, "trend_top")

        # final_score=0 不应触发 scores_missing
        assert "scores_missing" not in result["hard_blockers"]
        # 但 final_score=0 < 55，所以应该是 blocked
        assert result["selection_bucket"] == "blocked"


class TestBuildEligibleWatchlist:
    """测试 eligible_watchlist 构建。"""

    def test_build_eligible_watchlist(self):
        """应正确构建 eligible_watchlist。"""
        stock_pools = {
            "trend_top": [
                {"code": "600001", "name": "A", "final_score": 75.0, "v2_score": 60.0, "data_quality": "ok"},
                {"code": "600002", "name": "B", "final_score": 70.0, "v2_score": 55.0, "data_quality": "ok"},
            ],
            "burst_top": [
                {"code": "600003", "name": "C", "final_score": 65.0, "v2_score": 50.0, "data_quality": "ok"},
            ],
            "v2_potential": [
                {"code": "600004", "name": "D", "final_score": 30.0, "v2_score": 80.0, "signal_type": "low_final_high_v2", "data_quality": "ok"},
            ],
            "divergence_review": [
                {"code": "600005", "name": "E", "final_score": 80.0, "v2_score": 30.0, "signal_type": "high_final_low_v2", "data_quality": "ok"},
            ],
        }

        result = build_eligible_watchlist(stock_pools)

        assert "eligible_watchlist" in result
        assert "core_watch" in result
        assert "v2_opportunity" in result
        assert "divergence_review" in result
        assert "blocked" in result
        assert "selection_quality" in result
        assert result["selection_quality"]["eligible_count"] > 0

    def test_dedup_priority(self):
        """去重应保留优先级最高的。"""
        stock_pools = {
            "trend_top": [
                {"code": "600001", "name": "A", "final_score": 75.0, "v2_score": 60.0, "data_quality": "ok"},
            ],
            "v2_potential": [
                {"code": "600002", "name": "B", "final_score": 30.0, "v2_score": 80.0, "signal_type": "low_final_high_v2", "data_quality": "ok"},
            ],
        }

        result = build_eligible_watchlist(stock_pools)

        # v2_opportunity 应包含 600002
        v2_codes = [s["code"] for s in result["v2_opportunity"]]
        assert "600002" in v2_codes

        # core_watch 应包含 600001
        core_codes = [s["code"] for s in result["core_watch"]]
        assert "600001" in core_codes

    def test_pool_quality_ok(self):
        """eligible_count > 0 且 blocked_count < eligible_count 时 pool_quality=ok。"""
        stock_pools = {
            "trend_top": [
                {"code": "600001", "name": "A", "final_score": 75.0, "v2_score": 60.0, "data_quality": "ok"},
                {"code": "600002", "name": "B", "final_score": 70.0, "v2_score": 55.0, "data_quality": "ok"},
            ],
            "burst_top": [],
            "v2_potential": [],
            "divergence_review": [],
        }

        result = build_eligible_watchlist(stock_pools)

        assert result["selection_quality"]["pool_quality"] == "ok"

    def test_pool_quality_fail_no_eligible(self):
        """eligible_count=0 时 pool_quality=fail。"""
        stock_pools = {
            "trend_top": [],
            "burst_top": [],
            "v2_potential": [],
            "divergence_review": [],
        }

        result = build_eligible_watchlist(stock_pools)

        assert result["selection_quality"]["pool_quality"] == "fail"

    def test_pool_quality_warn(self):
        """blocked_count > eligible_count 时 pool_quality=warn。"""
        stock_pools = {
            "trend_top": [
                {"code": "600001", "name": "A", "final_score": 75.0, "v2_score": 60.0, "data_quality": "ok"},
            ],
            "burst_top": [
                {"code": "600002", "name": "", "final_score": 70.0, "data_quality": "ok"},  # blocked: missing_name
                {"code": "600003", "name": "", "final_score": 70.0, "data_quality": "ok"},  # blocked: missing_name
            ],
            "v2_potential": [],
            "divergence_review": [],
        }

        result = build_eligible_watchlist(stock_pools)

        # blocked_count(2) > eligible_count(1)
        assert result["selection_quality"]["pool_quality"] == "warn"

    def test_action_state_watch_only(self):
        """action_state 应恒定为 watch_only。"""
        stock_pools = {
            "trend_top": [
                {"code": "600001", "name": "A", "final_score": 75.0, "v2_score": 60.0, "data_quality": "ok"},
            ],
            "burst_top": [],
            "v2_potential": [],
            "divergence_review": [],
        }

        result = build_eligible_watchlist(stock_pools)

        for bucket in ["eligible_watchlist", "core_watch", "v2_opportunity", "divergence_review", "blocked"]:
            for item in result[bucket]:
                assert item["action_state"] == "watch_only"

    def test_no_forbidden_trade_words(self):
        """不包含 forbidden trade words。"""
        stock_pools = {
            "trend_top": [
                {"code": "600001", "name": "A", "final_score": 75.0, "v2_score": 60.0, "data_quality": "ok"},
            ],
            "burst_top": [],
            "v2_potential": [],
            "divergence_review": [],
        }

        result = build_eligible_watchlist(stock_pools)

        result_str = json.dumps(result, ensure_ascii=False)

        for word in FORBIDDEN_WORDS:
            assert word not in result_str, f"Found forbidden word: {word}"


class TestNewFactorSelectionQuality:
    """测试新因子对 selection_quality 的影响。"""

    def test_liquidity_weak_soft_warning(self):
        """liquidity_score < 40 应产生 soft_warning。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "liquidity_score": 35.0,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert "liquidity_weak" in result["soft_warnings"]
        # 不应是 hard_blocker
        assert "liquidity_weak" not in result["hard_blockers"]

    def test_chasing_risk_high_soft_warning(self):
        """chasing_risk_score >= 80 应产生 soft_warning。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "chasing_risk_score": 85.0,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert "chasing_risk_high" in result["soft_warnings"]
        # 不应是 hard_blocker
        assert "chasing_risk_high" not in result["hard_blockers"]

    def test_drawdown_deep_soft_warning(self):
        """drawdown_depth_20 > 35 应产生 soft_warning。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "drawdown_depth_20": 40.0,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert "drawdown_deep" in result["soft_warnings"]
        # 不应是 hard_blocker
        assert "drawdown_deep" not in result["hard_blockers"]

    def test_near_breakout_policy_does_not_require_reason_codes(self):
        """near breakout bars policy should not rely on external reason_codes."""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 60.0,
            "data_quality": "ok",
            "factor_snapshot": {"breakout_distance_20": 2.0},
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert result["bars_factor_policy"]["breakout_distance_20"] == {
            "policy": "trigger_candidate",
            "applied": False,
            "reason": "near breakout structure",
        }
        assert "breakout_structure_candidate" in result["quality_confirmations"]
        assert result["action_state"] == "watch_only"

    def test_none_factor_snapshot_does_not_raise(self):
        """factor_snapshot=None should keep bars policy missing instead of raising."""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 60.0,
            "data_quality": "ok",
            "factor_snapshot": None,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert result["bars_factor_policy"]["breakout_distance_20"]["policy"] == "missing"
        assert result["action_state"] == "watch_only"

    def test_selection_score_formula_unchanged(self):
        """selection_score 公式不应改变。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
        }

        result = classify_stock_candidate(candidate, "trend_top")

        # selection_score = final_score * 0.7 + v2_score * 0.3 = 75 * 0.7 + 60 * 0.3 = 52.5 + 18 = 70.5
        assert result["selection_score"] == pytest.approx(70.5, rel=0.01)

    def test_action_state_watch_only(self):
        """action_state 应恒定为 watch_only。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "liquidity_score": 35.0,
            "chasing_risk_score": 85.0,
            "drawdown_depth_20": 40.0,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert result["action_state"] == "watch_only"

    def test_sector_support_confirmed_quality(self):
        """sector_support_score >= 65 应生成 quality_confirmations。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "sector_support_score": 70.0,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert "sector_support_confirmed" in result["quality_confirmations"]

    def test_sector_support_weak_warning(self):
        """sector_support_score < 50 应生成 soft_warning。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "sector_support_score": 40.0,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert "sector_support_weak" in result["soft_warnings"]

    def test_selection_score_adjusted_high_sector_support(self):
        """sector_support_score >= 75 应增加 selection_score_adjusted（trend_follow）。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "selection_bucket": "core_watch",
            "sector_support_score": 80.0,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        # selection_score = 75 * 0.7 + 60 * 0.3 = 52.5 + 18 = 70.5
        assert result["selection_score"] == pytest.approx(70.5, rel=0.01)
        # selection_score_adjusted = 70.5 + 5 = 75.5 (trend_follow + sector_support >= 75)
        assert result["selection_score_adjusted"] == pytest.approx(75.5, rel=0.01)

    def test_selection_score_adjusted_low_sector_support(self):
        """sector_support_score < 50 应减少 selection_score_adjusted（trend_follow）。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "selection_bucket": "core_watch",
            "sector_support_score": 40.0,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        # selection_score = 75 * 0.7 + 60 * 0.3 = 52.5 + 18 = 70.5
        assert result["selection_score"] == pytest.approx(70.5, rel=0.01)
        # selection_score_adjusted = 70.5 - 3 = 67.5 (trend_follow + 40 <= sector_support < 50)
        assert result["selection_score_adjusted"] == pytest.approx(67.5, rel=0.01)

    def test_sector_support_weak_not_hard_block(self):
        """sector_support_weak 不应作为 hard_blocker。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "sector_support_score": 40.0,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert "sector_support_weak" not in result["hard_blockers"]
        assert "sector_support_weak" in result["soft_warnings"]

    def test_trend_follow_enable_adjustment(self):
        """trend_follow + sector_support_score >= 75 应启用调整。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "selection_bucket": "core_watch",
            "sector_support_score": 80.0,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert result["sector_support_adjustment_policy"] == "enable_adjustment"
        assert result["sector_support_adjustment_applied"] is True
        assert result["sector_support_adjustment_delta"] == 5.0
        # selection_score = 75 * 0.7 + 60 * 0.3 = 52.5 + 18 = 70.5
        # selection_score_adjusted = 70.5 + 5 = 75.5
        assert result["selection_score_adjusted"] == pytest.approx(75.5, rel=0.01)

    def test_trend_follow_disable_low_score(self):
        """trend_follow + sector_support_score < 40 应扣分。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "selection_bucket": "core_watch",
            "sector_support_score": 35.0,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert result["sector_support_adjustment_policy"] == "enable_adjustment"
        assert result["sector_support_adjustment_applied"] is True
        assert result["sector_support_adjustment_delta"] == -5.0

    def test_short_burst_disable_adjustment(self):
        """short_burst 应禁用调整。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "source_pool": "burst_top",
            "sector_support_score": 80.0,
        }

        result = classify_stock_candidate(candidate, "burst_top")

        assert result["sector_support_adjustment_policy"] == "disable_adjustment"
        assert result["sector_support_adjustment_applied"] is False
        assert result["sector_support_adjustment_delta"] == 0.0
        # selection_score 不应改变
        assert result["selection_score_adjusted"] == result["selection_score"]

    def test_blocked_disable_adjustment(self):
        """blocked 应禁用调整。"""
        candidate = {
            "code": "600001",
            "name": "",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "selection_bucket": "blocked",
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert result["sector_support_adjustment_policy"] == "disable_adjustment"
        assert result["sector_support_adjustment_applied"] is False

    def test_v2_recovery_display_only(self):
        """v2_recovery 应为 display_only。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 30.0,
            "v2_score": 80.0,
            "data_quality": "ok",
            "signal_type": "low_final_high_v2",
            "sector_support_score": 70.0,
        }

        result = classify_stock_candidate(candidate, "v2_potential")

        assert result["sector_support_adjustment_policy"] == "display_only"
        assert result["sector_support_adjustment_applied"] is False
        assert result["sector_support_adjustment_delta"] == 0.0

    def test_selection_score_unchanged(self):
        """selection_score 原值不应改变。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "selection_bucket": "core_watch",
            "sector_support_score": 80.0,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        # selection_score = 75 * 0.7 + 60 * 0.3 = 52.5 + 18 = 70.5
        assert result["selection_score"] == pytest.approx(70.5, rel=0.01)
        # selection_score_adjusted = 70.5 + 5 = 75.5
        assert result["selection_score_adjusted"] == pytest.approx(75.5, rel=0.01)

    def test_action_state_watch_only(self):
        """action_state 应恒定为 watch_only。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "selection_bucket": "core_watch",
            "sector_support_score": 80.0,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert result["action_state"] == "watch_only"
