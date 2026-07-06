"""
双评分测试

测试 trend_continuation_score 和 short_term_burst_score 的计算和交互。
"""

import pytest

from theme_sector_radar.scoring.short_term_burst_score import (
    apply_burst_insufficient_history_cap,
    calculate_short_term_burst_score,
    get_burst_level,
    interpret_dual_scores,
)
from theme_sector_radar.scoring.sector_composite_score import (
    calculate_sector_composite_score,
)


class TestTrendContinuationScore:
    """测试趋势持续评分"""

    def test_trend_score_compatible_with_sector_selection_score(self):
        """测试 trend_continuation_score 兼容原 sector_selection_score"""
        # 使用相同的输入参数
        kwargs = {
            "radar_score": 70.0,
            "recent_returns": [2.0, 1.5, 1.0, 0.5, 0.3],
            "sector_return": 5.3,
            "all_sector_returns": [1.0, 2.0, 3.0, 4.0, 5.0],
            "positive_days_count": 4,
            "total_days": 5,
            "max_drawdown": -0.02,
            "volatility": 1.5,
            "data_quality_score": 80.0,
            "history_days": 5,
            "price_change_available": True,
        }

        # 计算趋势持续评分
        result = calculate_sector_composite_score(**kwargs)
        trend_score = result["sector_selection_score"]

        # 验证结果在合理范围内
        assert 0 <= trend_score <= 100
        assert result["selection_level"] in ["strong_watch", "watch", "neutral", "cooling", "avoid"]


class TestShortTermBurstScore:
    """测试短线爆发评分"""

    def test_burst_score_calculation(self):
        """测试短线爆发评分计算"""
        result = calculate_short_term_burst_score(
            radar_score=80.0,
            one_day_change=5.0,
            recent_returns=[3.0, 2.0, 4.0],
            turnover=10_000_000_000,
            main_net_inflow=500_000_000,
            current_rank=5,
            previous_rank=10,
            data_quality_score=80.0,
            price_change_available=True,
            history_days=5,
        )

        # 验证结果在合理范围内
        assert 0 <= result["short_term_burst_score"] <= 100
        assert result["burst_level"] in ["burst_hot", "burst_watch", "burst_neutral", "burst_fading", "burst_avoid"]
        assert "burst_breakdown" in result
        assert "warnings" in result

    def test_burst_score_with_missing_data(self):
        """测试缺少数据时的短线爆发评分"""
        result = calculate_short_term_burst_score(
            radar_score=50.0,
            one_day_change=None,  # 缺失
            recent_returns=[],  # 缺失
            turnover=None,  # 缺失
            main_net_inflow=None,  # 缺失
            current_rank=None,  # 缺失
            previous_rank=None,  # 缺失
            data_quality_score=50.0,
            price_change_available=True,
            history_days=0,
        )

        # 验证结果在合理范围内
        assert 0 <= result["short_term_burst_score"] <= 100
        assert len(result["warnings"]) > 0  # 应该有警告

    def test_burst_level_thresholds(self):
        """测试短线爆发等级阈值"""
        assert get_burst_level(85.0) == "burst_hot"
        assert get_burst_level(70.0) == "burst_watch"
        assert get_burst_level(55.0) == "burst_neutral"
        assert get_burst_level(40.0) == "burst_fading"
        assert get_burst_level(25.0) == "burst_avoid"


class TestDualScoreInterpretation:
    """测试双评分解读"""

    def test_trend_and_burst_aligned(self):
        """测试趋势和短线都强"""
        result = interpret_dual_scores(
            trend_score=75.0,
            trend_level="watch",
            burst_score=70.0,
            burst_level="burst_watch",
        )

        assert result["profile"] == "trend_and_burst_aligned"
        assert "双重确认" in result["summary"]

    def test_trend_only(self):
        """测试趋势强但短线不热"""
        result = interpret_dual_scores(
            trend_score=70.0,
            trend_level="watch",
            burst_score=45.0,
            burst_level="burst_fading",
        )

        assert result["profile"] == "trend_only"
        assert "趋势强" in result["summary"]

    def test_burst_without_trend_confirmation(self):
        """测试短线强但趋势未确认"""
        result = interpret_dual_scores(
            trend_score=45.0,
            trend_level="cooling",
            burst_score=70.0,
            burst_level="burst_watch",
        )

        assert result["profile"] == "burst_without_trend_confirmation"
        assert "短线强" in result["summary"]
        assert any("持续性" in wp for wp in result["watch_points"])

    def test_weak_or_cooling(self):
        """测试趋势和短线都弱"""
        result = interpret_dual_scores(
            trend_score=35.0,
            trend_level="cooling",
            burst_score=30.0,
            burst_level="burst_avoid",
        )

        assert result["profile"] == "weak_or_cooling"
        assert "弱" in result["summary"]

    def test_neutral(self):
        """测试中等情况"""
        result = interpret_dual_scores(
            trend_score=55.0,
            trend_level="neutral",
            burst_score=55.0,
            burst_level="burst_neutral",
        )

        assert result["profile"] == "neutral"
        assert "中性" in result["summary"]


class TestDualScoreEdgeCases:
    """测试双评分边界情况"""

    def test_burst_high_trend_low_profile(self):
        """测试 burst 高但 trend 低时的 profile"""
        result = interpret_dual_scores(
            trend_score=40.0,
            trend_level="cooling",
            burst_score=75.0,
            burst_level="burst_watch",
        )

        assert result["profile"] == "burst_without_trend_confirmation"
        assert any("确认" in wp or "持续性" in wp for wp in result["watch_points"])

    def test_trend_high_burst_low_profile(self):
        """测试 trend 高但 burst 低时的 profile"""
        result = interpret_dual_scores(
            trend_score=75.0,
            trend_level="watch",
            burst_score=40.0,
            burst_level="burst_fading",
        )

        assert result["profile"] == "trend_only"
        assert any("中长期" in wp or "爆发" in wp for wp in result["watch_points"])

    def test_concept_price_change_unavailable_penalty(self):
        """测试概念涨跌幅不可用时的扣分"""
        result = calculate_short_term_burst_score(
            radar_score=70.0,
            one_day_change=5.0,
            recent_returns=[3.0, 2.0, 4.0],
            turnover=10_000_000_000,
            main_net_inflow=500_000_000,
            data_quality_score=80.0,
            price_change_available=False,  # 涨跌幅不可用
            history_days=5,
        )

        # 验证有警告
        assert any("涨跌幅" in w or "price_change" in w for w in result["warnings"])

    def test_raw_snapshot_fallback_penalty(self):
        """测试 raw_snapshot_fallback 时的扣分"""
        result_with_cache = calculate_short_term_burst_score(
            radar_score=70.0,
            one_day_change=5.0,
            recent_returns=[3.0, 2.0, 4.0],
            data_quality_score=80.0,
            price_change_available=True,
            history_days=5,
            history_source="sector_history_cache",
        )

        result_with_fallback = calculate_short_term_burst_score(
            radar_score=70.0,
            one_day_change=5.0,
            recent_returns=[3.0, 2.0, 4.0],
            data_quality_score=80.0,
            price_change_available=True,
            history_days=5,
            history_source="raw_snapshot_fallback",
        )

        # raw_snapshot_fallback 应该分数更低
        assert result_with_fallback["short_term_burst_score"] < result_with_cache["short_term_burst_score"]


class TestBurstInsufficientHistoryCap:
    """M1: 短线爆发分 insufficient_history 上限测试"""

    def test_history_days_zero_caps_to_34_9(self):
        """history_days=0 时，短线分不超过 34.9"""
        capped, applied, reason = apply_burst_insufficient_history_cap(80.0, 0, 0)
        assert applied is True
        assert capped == 34.9
        assert "34.9" in reason

    def test_history_days_zero_no_cap_if_below(self):
        """history_days=0 但短线分已经低于 34.9，不触发 cap"""
        capped, applied, reason = apply_burst_insufficient_history_cap(20.0, 0, 0)
        assert applied is False
        assert capped == 20.0

    def test_actual_history_days_1_caps_to_49_9(self):
        """actual_history_days=1 (<3) 时，短线分不超过 49.9"""
        capped, applied, reason = apply_burst_insufficient_history_cap(70.0, 5, 1)
        assert applied is True
        assert capped == 49.9
        assert "49.9" in reason

    def test_actual_history_days_2_caps_to_49_9(self):
        """actual_history_days=2 (<3) 时，短线分不超过 49.9"""
        capped, applied, reason = apply_burst_insufficient_history_cap(55.0, 5, 2)
        assert applied is True
        assert capped == 49.9

    def test_actual_history_days_2_no_cap_if_below(self):
        """actual_history_days=2 但短线分已低于 49.9，不触发 cap"""
        capped, applied, reason = apply_burst_insufficient_history_cap(40.0, 5, 2)
        assert applied is False
        assert capped == 40.0

    def test_actual_history_days_3_no_cap(self):
        """actual_history_days >= 3 时，不触发 cap"""
        capped, applied, reason = apply_burst_insufficient_history_cap(80.0, 5, 3)
        assert applied is False
        assert capped == 80.0

    def test_actual_history_days_5_no_cap(self):
        """actual_history_days >= 3 (e.g. 5) 时，不触发 cap"""
        capped, applied, reason = apply_burst_insufficient_history_cap(90.0, 10, 5)
        assert applied is False
        assert capped == 90.0

    def test_actual_history_days_none_falls_back_to_history_days(self):
        """actual_history_days 为 None 时退回到 history_days"""
        # history_days=10, actual_history_days=None => 10, no cap
        capped, applied, reason = apply_burst_insufficient_history_cap(80.0, 10, None)
        assert applied is False

    def test_burst_score_with_history_days_zero_gets_capped(self):
        """端到端: history_days=0 时调用 calculate_short_term_burst_score 后手动 cap"""
        result = calculate_short_term_burst_score(
            radar_score=90.0,
            one_day_change=None,
            recent_returns=[],
            turnover=None,
            main_net_inflow=None,
            data_quality_score=50.0,
            price_change_available=False,
            history_days=0,
        )
        # 应用 cap
        capped, applied, _ = apply_burst_insufficient_history_cap(
            result["short_term_burst_score"], 0, 0
        )
        if applied:
            assert capped <= 34.9, f"Capped score {capped} exceeds 34.9"
            burst_level = get_burst_level(capped)
            assert burst_level == "burst_avoid", f"Expected burst_avoid, got {burst_level}"
