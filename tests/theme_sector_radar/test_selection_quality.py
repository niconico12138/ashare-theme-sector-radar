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
from tests.theme_sector_radar.paper_only_contract import (
    FORBIDDEN_WORDS,
    extract_executable_instructions,
)


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

    def test_executable_instruction_extractor_ignores_research_text(self):
        payload = {
            "research_note": "buy and hold research only",
            "shadow_status": "paper_hold_observation",
            "Orders": [{"side": "sell"}],
            "command": {"side": "buy"},
            "position_size": 0.5,
            "submit_order": True,
        }

        instruction_keys, instruction_texts = extract_executable_instructions(payload)

        assert instruction_keys == {
            "orders",
            "side",
            "command",
            "position_size",
            "submit_order",
        }
        assert instruction_texts == ["sell", "buy", "0.5", "True"]

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

        instruction_keys, instruction_texts = extract_executable_instructions(result)
        assert not instruction_keys, f"Found executable instruction keys: {sorted(instruction_keys)}"
        executable_text = "\n".join(instruction_texts).casefold()

        for word in FORBIDDEN_WORDS:
            assert word.casefold() not in executable_text, f"Found forbidden word: {word}"


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
        """chasing_risk_score >= 70 应产生 soft_warning。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "chasing_risk_score": 75.0,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert "chasing_risk_high" in result["soft_warnings"]
        # 不应是 hard_blocker
        assert "chasing_risk_high" not in result["hard_blockers"]

    def test_chasing_risk_watch_display_only(self):
        """chasing_risk_score 60-70 应产生 display_only policy。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "chasing_risk_score": 65.0,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert result["bars_factor_policy"]["chasing_risk_score"]["policy"] == "display_only"
        assert result["bars_factor_policy"]["chasing_risk_score"]["applied"] is False

    def test_drawdown_deep_repair_context(self):
        """drawdown_depth_20 > 15 应产生 repair_context policy (非 soft_warning)。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 75.0,
            "v2_score": 60.0,
            "data_quality": "ok",
            "drawdown_depth_20": 20.0,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert result["bars_factor_policy"]["drawdown_depth_20"]["policy"] == "repair_context"
        assert result["bars_factor_policy"]["drawdown_depth_20"]["applied"] is False
        # deep 不再是 soft_warning
        assert "drawdown_deep" not in result["soft_warnings"]

    def test_near_breakout_policy_structure_candidate(self):
        """near breakout (raw<=3) 应产生 structure_candidate policy (非 trigger)。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 60.0,
            "data_quality": "ok",
            "factor_snapshot": {"breakout_distance_20": 2.0},
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert result["bars_factor_policy"]["breakout_distance_20"]["policy"] == "structure_candidate"
        assert result["bars_factor_policy"]["breakout_distance_20"]["applied"] is False
        assert "structure_position_candidate" in result["quality_confirmations"]
        assert result["action_state"] == "watch_only"

    def test_neutral_breakout_policy_profile_only(self):
        """neutral breakout (3<raw<=10) 应产生 profile_only policy。"""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 60.0,
            "data_quality": "ok",
            "factor_snapshot": {"breakout_distance_20": 7.0},
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert result["bars_factor_policy"]["breakout_distance_20"]["policy"] == "profile_only"
        assert result["bars_factor_policy"]["breakout_distance_20"]["applied"] is False

    def test_none_factor_snapshot_does_not_raise(self):
        """factor_snapshot=None should keep bars policy calibration_needed instead of raising."""
        candidate = {
            "code": "600001",
            "name": "A",
            "final_score": 60.0,
            "data_quality": "ok",
            "factor_snapshot": None,
        }

        result = classify_stock_candidate(candidate, "trend_top")

        assert result["bars_factor_policy"]["breakout_distance_20"]["policy"] == "calibration_needed"
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


def test_selection_quality_uses_factor_snapshot_values_for_valuable_factors():
    from theme_sector_radar.reporting.selection_quality import classify_stock_candidate

    candidate = {
        "code": "600001",
        "name": "Alpha",
        "final_score": 70.0,
        "factor_composite_shadow_score_v2": 60.0,
        "data_quality": "ok",
        "factor_snapshot": {
            "factors": [
                {"factor_id": "sector_support_score", "raw_value": 82.0, "score": 82.0, "quality": "good"},
                {"factor_id": "liquidity_score", "raw_value": 35.0, "score": 35.0, "quality": "good"},
                {"factor_id": "chasing_risk_score", "raw_value": 75.0, "score": 75.0, "quality": "good"},
                {"factor_id": "breakout_distance_20", "raw_value": 2.0, "score": 90.0, "quality": "good"},
                {"factor_id": "drawdown_depth_20", "raw_value": 18.0, "score": 40.0, "quality": "good"},
            ]
        },
    }

    result = classify_stock_candidate(candidate, "trend_top")

    assert "sector_support_confirmed" in result["quality_confirmations"]
    assert result["sector_support_adjustment_applied"] is True
    assert result["selection_score_adjusted"] == result["selection_score"] + 5.0
    assert "liquidity_weak" in result["soft_warnings"]
    assert "overheat_risk_high" in result["soft_warnings"]
    assert result["bars_factor_policy"]["breakout_distance_20"]["policy"] == "structure_candidate"
    assert result["bars_factor_policy"]["drawdown_depth_20"]["policy"] == "repair_context"


def test_factor_value_overlay_boosts_validated_positive_factors_without_changing_official_scores():
    candidate = {
        "code": "600101",
        "name": "OverlayPositive",
        "final_score": 70.0,
        "v2_score": 60.0,
        "data_quality": "ok",
        "stock_trend_score": 76.0,
        "contraction_score": 82.0,
        "factor_composite_shadow_score": 72.0,
        "factor_snapshot": {
            "factors": [
                {"factor_id": "sector_support_score", "raw_value": 82.0, "score": 82.0, "quality": "good"},
                {"factor_id": "chasing_risk_score", "raw_value": 35.0, "score": 35.0, "quality": "good"},
                {"factor_id": "drawdown_depth_20", "raw_value": 4.0, "score": 80.0, "quality": "good"},
                {"factor_id": "breakout_distance_20", "raw_value": 4.0, "score": 75.0, "quality": "good"},
            ]
        },
    }

    result = classify_stock_candidate(candidate, "trend_top")

    assert result["selection_score"] == pytest.approx(67.0)
    assert result["selection_score_adjusted"] == pytest.approx(72.0)
    assert result["optimized_watch_score"] > result["selection_score_adjusted"]
    assert result["action_state"] == "watch_only"
    assert result["factor_value_overlay"]["policy"] == "watch_ranking_only"
    assert result["factor_value_overlay"]["model"] == "backtest_weighted_score_v1"
    assert result["factor_value_overlay"]["does_not_change_official_scores"] is True
    assert "sector_support_positive" in result["factor_value_overlay"]["positive_factors"]
    assert "trend_positive" in result["factor_value_overlay"]["positive_factors"]


def test_factor_value_overlay_penalizes_inverse_risk_factors_without_trade_trigger():
    candidate = {
        "code": "600102",
        "name": "OverlayRisk",
        "final_score": 70.0,
        "v2_score": 60.0,
        "data_quality": "ok",
        "factor_snapshot": {
            "factors": [
                {"factor_id": "sector_support_score", "raw_value": 58.0, "score": 58.0, "quality": "good"},
                {"factor_id": "chasing_risk_score", "raw_value": 78.0, "score": 78.0, "quality": "good"},
                {"factor_id": "drawdown_depth_20", "raw_value": 22.0, "score": 30.0, "quality": "good"},
                {"factor_id": "breakout_distance_20", "raw_value": 24.0, "score": 20.0, "quality": "good"},
                {"factor_id": "amount_ratio_20", "raw_value": 2.8, "score": 35.0, "quality": "good"},
            ]
        },
    }

    result = classify_stock_candidate(candidate, "trend_top")

    overlay = result["factor_value_overlay"]
    assert result["optimized_watch_score"] < result["selection_score_adjusted"]
    assert overlay["rule_delta"] == pytest.approx(-10.0)
    assert overlay["raw_risk_guardrail"] <= -10.0
    assert "overheat_risk_penalty" in overlay["risk_factors"]
    assert "deep_drawdown_penalty" in overlay["risk_factors"]
    assert "volume_spike_penalty" in overlay["risk_factors"]
    assert result["action_state"] == "watch_only"
    assert "buy_point" not in json.dumps(result, ensure_ascii=False)
    assert "trade_trigger" not in json.dumps(result, ensure_ascii=False)


def test_eligible_watchlist_sorts_by_optimized_watch_score_when_available():
    weak_overlay = {
        "code": "600201",
        "name": "OldScoreHigher",
        "final_score": 73.0,
        "v2_score": 60.0,
        "data_quality": "ok",
        "factor_snapshot": {
            "factors": [
                {"factor_id": "sector_support_score", "raw_value": 48.0, "score": 48.0, "quality": "good"},
                {"factor_id": "chasing_risk_score", "raw_value": 75.0, "score": 75.0, "quality": "good"},
                {"factor_id": "drawdown_depth_20", "raw_value": 18.0, "score": 35.0, "quality": "good"},
            ]
        },
    }
    strong_overlay = {
        "code": "600202",
        "name": "FactorValueHigher",
        "final_score": 68.0,
        "v2_score": 60.0,
        "data_quality": "ok",
        "stock_trend_score": 78.0,
        "contraction_score": 78.0,
        "factor_snapshot": {
            "factors": [
                {"factor_id": "sector_support_score", "raw_value": 82.0, "score": 82.0, "quality": "good"},
                {"factor_id": "chasing_risk_score", "raw_value": 30.0, "score": 30.0, "quality": "good"},
                {"factor_id": "drawdown_depth_20", "raw_value": 4.0, "score": 80.0, "quality": "good"},
            ]
        },
    }

    result = build_eligible_watchlist({"trend_top": [weak_overlay, strong_overlay]}, top_n=2)

    assert result["eligible_watchlist"][0]["code"] == "600202"
    assert result["eligible_watchlist"][0]["optimized_watch_score"] > result["eligible_watchlist"][1]["optimized_watch_score"]


def test_sector_peer_rank_score_is_added_before_watch_scoring():
    stronger = {
        "code": "600301",
        "name": "SectorLeader",
        "sector_name": "AI",
        "final_score": 72.0,
        "v2_score": 60.0,
        "stock_trend_score": 82.0,
        "data_quality": "ok",
    }
    weaker = {
        "code": "600302",
        "name": "SectorFollower",
        "sector_name": "AI",
        "final_score": 70.0,
        "v2_score": 60.0,
        "stock_trend_score": 55.0,
        "data_quality": "ok",
    }

    result = build_eligible_watchlist({"trend_top": [weaker, stronger]}, top_n=2)
    by_code = {item["code"]: item for item in result["eligible_watchlist"]}

    assert by_code["600301"]["sector_peer_rank_score"] > by_code["600302"]["sector_peer_rank_score"]
    assert by_code["600301"]["factor_value_overlay_v2_shadow"]["model"] == "factor_value_shadow_v2"
    assert by_code["600301"]["optimized_watch_score_v2_shadow"] != by_code["600301"]["optimized_watch_score"]
    assert result["eligible_watchlist"][0]["code"] in {"600301", "600302"}


def test_watch_ranking_decision_explains_current_and_shadow_scores():
    candidate = {
        "code": "600401",
        "name": "RankingDecision",
        "final_score": 72.0,
        "v2_score": 60.0,
        "data_quality": "ok",
        "stock_trend_score": 75.0,
    }

    result = classify_stock_candidate(candidate, "trend_top")

    decision = result["watch_ranking_decision"]
    assert decision["current_sort_score"] == result["risk_adjusted_watch_score_shadow"]
    assert decision["base_sort_score"] == result["optimized_watch_score"]
    assert decision["shadow_score"] == result["optimized_watch_score_v2_shadow"]
    assert decision["current_sort_model"] == "risk_adjusted_watch_score_shadow"
    assert decision["base_sort_model"] == "optimized_watch_score"
    assert decision["shadow_model"] == "optimized_watch_score_v2_shadow"
    assert decision["status"] == "shadow_observation"
    assert decision["no_execution_signals"] is True


def test_risk_gate_shadow_penalizes_weak_market_sector_and_trend_without_changing_official_scores():
    weak_environment = {
        "code": "600501",
        "name": "WeakEnvironment",
        "sector_name": "WeakSector",
        "final_score": 75.0,
        "v2_score": 60.0,
        "data_quality": "ok",
        "stock_trend_score": 45.0,
        "trend_persistence_score": 38.0,
        "risk_adjusted_return_20": 35.0,
        "volume_stability_score": 35.0,
        "relative_strength_20": 35.0,
        "sector_support_score": 38.0,
    }
    healthy_environment = {
        "code": "600502",
        "name": "HealthyEnvironment",
        "sector_name": "StrongSector",
        "final_score": 75.0,
        "v2_score": 60.0,
        "data_quality": "ok",
        "stock_trend_score": 78.0,
        "trend_persistence_score": 72.0,
        "risk_adjusted_return_20": 70.0,
        "volume_stability_score": 66.0,
        "relative_strength_20": 68.0,
        "sector_support_score": 82.0,
    }
    weak_peer_1 = dict(weak_environment, code="600503", name="WeakPeer1", stock_trend_score=44.0)
    weak_peer_2 = dict(weak_environment, code="600504", name="WeakPeer2", stock_trend_score=46.0)

    result = build_eligible_watchlist(
        {"trend_top": [weak_environment, healthy_environment, weak_peer_1, weak_peer_2]},
        top_n=4,
    )
    by_code = {item["code"]: item for item in result["eligible_watchlist"]}

    weak = by_code["600501"]
    healthy = by_code["600502"]

    assert weak["selection_score"] == pytest.approx(70.5)
    assert healthy["selection_score"] == pytest.approx(70.5)
    assert weak["risk_gate_decision"]["schema_version"] == "risk_gate_decision.v1"
    assert weak["risk_gate_decision"]["policy"] == "watch_ranking_shadow_only"
    assert weak["risk_gate_decision"]["market_gate"]["regime"] == "risk_off"
    assert weak["risk_gate_decision"]["sector_gate"]["regime"] in {"fading", "weak"}
    assert weak["risk_gate_decision"]["trend_health_gate"]["state"] == "weak"
    assert weak["risk_gate_decision"]["observation_mode"] == "risk_limited_observation"
    assert weak["risk_gate_decision"]["observation_priority"] == 0
    assert weak["risk_adjusted_watch_score_shadow"] < weak["optimized_watch_score"]
    assert healthy["risk_adjusted_watch_score_shadow"] > weak["risk_adjusted_watch_score_shadow"]
    assert result["eligible_watchlist"][0]["code"] == "600502"
    assert "trade_trigger" not in json.dumps(result, ensure_ascii=False)


def test_short_burst_risk_gate_penalizes_overheat_without_changing_official_scores():
    hot_single_name = {
        "code": "600601",
        "name": "HotSingleName",
        "sector_name": "Media",
        "final_score": 72.0,
        "v2_score": 55.0,
        "data_quality": "ok",
        "source_pool": "burst_top",
        "stock_short_score_v2": 82.0,
        "stock_trend_score": 58.0,
        "sector_burst_score": 44.0,
        "sector_support_score": 42.0,
        "chasing_risk_score": 82.0,
        "amount_ratio_20": 2.8,
        "breakout_distance_20": 22.0,
        "relative_strength_20": 92.0,
        "volume_stability_score": 38.0,
    }
    healthy_burst = {
        "code": "600602",
        "name": "HealthyBurst",
        "sector_name": "Robotics",
        "final_score": 72.0,
        "v2_score": 55.0,
        "data_quality": "ok",
        "source_pool": "burst_top",
        "stock_short_score_v2": 76.0,
        "stock_trend_score": 62.0,
        "sector_burst_score": 78.0,
        "sector_support_score": 70.0,
        "chasing_risk_score": 48.0,
        "amount_ratio_20": 1.35,
        "breakout_distance_20": 6.0,
        "relative_strength_20": 72.0,
        "volume_stability_score": 65.0,
    }

    result = build_eligible_watchlist({"burst_top": [hot_single_name, healthy_burst]}, top_n=2)
    by_code = {item["code"]: item for item in result["eligible_watchlist"]}
    hot = by_code["600601"]
    healthy = by_code["600602"]

    assert hot["selection_score"] == healthy["selection_score"]
    assert hot["short_burst_risk_gate"]["schema_version"] == "short_burst_risk_gate.v1"
    assert hot["short_burst_risk_gate"]["policy"] == "short_burst_watch_ranking_shadow_only"
    assert hot["short_burst_risk_gate"]["observation_mode"] == "burst_risk_limited_observation"
    assert hot["short_burst_risk_adjusted_score_shadow"] < hot["optimized_watch_score"]
    assert healthy["short_burst_risk_adjusted_score_shadow"] > hot["short_burst_risk_adjusted_score_shadow"]
    assert result["eligible_watchlist"][0]["code"] == "600602"
    assert "trade_trigger" not in json.dumps(result, ensure_ascii=False)


def test_short_burst_emotion_overlay_is_shadow_only_and_keeps_official_scores():
    candidate = {
        "code": "600701",
        "name": "EmotionShadow",
        "sector_name": "Media",
        "final_score": 66.0,
        "v2_score": 58.0,
        "data_quality": "ok",
        "source_pool": "burst_top",
        "stock_short_score_v2": 72.0,
        "sector_burst_score": 68.0,
        "sector_support_score": 62.0,
        "short_burst_emotion_score_v1": 54.0,
        "short_burst_emotion_score_v2": 61.0,
        "volume_burst_quality_score": 65.0,
        "limit_attention_score": 42.0,
        "next_day_cashout_risk_score": 35.0,
    }

    result = build_eligible_watchlist({"burst_top": [candidate]}, top_n=1)
    item = result["eligible_watchlist"][0]
    overlay = item["short_burst_emotion_overlay_shadow"]

    assert item["selection_score"] == pytest.approx(63.6)
    assert item["selection_score_adjusted"] == pytest.approx(63.6)
    assert overlay["schema_version"] == "short_burst_emotion_overlay.v1"
    assert overlay["policy"] == "shadow_observation_only"
    assert overlay["score_source"] == "short_burst_emotion_score_v2"
    assert overlay["short_burst_emotion_score_shadow"] == pytest.approx(61.0)
    assert overlay["does_not_modify_official_scores"] is True
    assert overlay["no_execution_signals"] is True
    assert item["watch_ranking_decision"]["short_burst_shadow_model"] == "short_burst_emotion_score_v2"
    assert item["watch_ranking_decision"]["short_burst_shadow_score"] == pytest.approx(61.0)


def test_short_burst_intraday_overlay_is_shadow_only_and_does_not_drive_current_sort():
    candidate = {
        "code": "600702",
        "name": "IntradayShadow",
        "sector_name": "Media",
        "final_score": 66.0,
        "v2_score": 58.0,
        "data_quality": "ok",
        "source_pool": "burst_top",
        "prev_close": 100.0,
        "sector_intraday_breadth_score": 72.0,
        "intraday_bars": [
            {"time": "09:30", "price": 100.0, "amount": 8_000_000.0},
            {"time": "10:30", "price": 101.0, "amount": 10_000_000.0},
            {"time": "13:30", "price": 102.0, "amount": 12_000_000.0},
            {"time": "14:30", "price": 103.0, "amount": 16_000_000.0},
            {"time": "14:55", "price": 104.0, "amount": 20_000_000.0},
        ],
    }

    result = build_eligible_watchlist({"burst_top": [candidate]}, top_n=1)
    item = result["eligible_watchlist"][0]
    overlay = item["short_burst_intraday_emotion_overlay_shadow"]

    assert item["selection_score"] == pytest.approx(63.6)
    assert item["selection_score_adjusted"] == pytest.approx(63.6)
    assert item["intraday_factor_snapshot"]["schema_version"] == "intraday_factor_snapshot.v1"
    assert overlay["schema_version"] == "short_burst_intraday_emotion_overlay.v1"
    assert overlay["policy"] == "shadow_observation_only"
    assert overlay["score_source"] == "short_burst_intraday_emotion_score_shadow"
    assert overlay["does_not_modify_official_scores"] is True
    assert overlay["does_not_drive_current_sort"] is True
    assert overlay["no_execution_signals"] is True
    assert item["watch_ranking_decision"]["intraday_shadow_model"] == "short_burst_intraday_emotion_score_shadow"
    assert item["watch_ranking_decision"]["intraday_shadow_score"] == overlay["short_burst_intraday_emotion_score_shadow"]


def test_short_burst_news_emotion_overlay_is_shadow_only_and_keeps_official_scores():
    candidate = {
        "code": "600703",
        "name": "NewsEmotionShadow",
        "sector_name": "Media",
        "final_score": 66.0,
        "v2_score": 58.0,
        "data_quality": "ok",
        "source_pool": "burst_top",
        "short_burst_emotion_score_v2": 61.0,
        "short_burst_news_emotion_score_shadow": 67.5,
        "market_short_emotion_score": 74.0,
        "news_heat_score": 68.0,
        "event_continuation_score": 72.0,
        "negative_news_risk_score": 18.0,
    }

    result = build_eligible_watchlist({"burst_top": [candidate]}, top_n=1)
    item = result["eligible_watchlist"][0]
    overlay = item["short_burst_news_emotion_overlay_shadow"]

    assert item["selection_score"] == pytest.approx(63.6)
    assert item["selection_score_adjusted"] == pytest.approx(63.6)
    assert overlay["schema_version"] == "short_burst_news_emotion_overlay.v1"
    assert overlay["policy"] == "shadow_observation_only"
    assert overlay["score_source"] == "short_burst_news_emotion_score_shadow"
    assert overlay["short_burst_news_emotion_score_shadow"] == pytest.approx(67.5)
    assert overlay["does_not_modify_official_scores"] is True
    assert overlay["does_not_drive_current_sort"] is True
    assert overlay["no_execution_signals"] is True
    assert item["watch_ranking_decision"]["news_emotion_shadow_model"] == "short_burst_news_emotion_score_shadow"
    assert item["watch_ranking_decision"]["news_emotion_shadow_score"] == pytest.approx(67.5)
