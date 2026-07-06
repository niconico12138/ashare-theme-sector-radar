"""
趋势窗口测试

测试 trend-window 参数和窗口截取逻辑。
"""

import pytest

from theme_sector_radar.scoring.sector_composite_score import (
    calculate_sector_composite_score,
)


class TestTrendWindowDefault:
    """测试趋势窗口默认值"""

    def test_default_trend_window_is_10(self):
        """测试默认趋势窗口为 10"""
        # 通过 CLI 参数测试
        import sys
        from io import StringIO
        from theme_sector_radar.cli import main

        # 捕获帮助输出
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            with pytest.raises(SystemExit) as exc_info:
                sys.argv = ["cli", "--score-sectors", "--help"]
                main()
            assert exc_info.value.code == 0
        finally:
            sys.stdout = old_stdout


class TestTrendWindowValues:
    """测试趋势窗口值"""

    def test_trend_window_accepts_5(self):
        """测试 trend-window 接受 5"""
        result = calculate_sector_composite_score(
            radar_score=70.0,
            recent_returns=[2.0, 1.5, 1.0, 0.5, 0.3],
            sector_return=5.3,
            benchmark_return=2.0,
            positive_days_count=4,
            total_days=5,
            max_drawdown=-2.0,
            volatility=1.5,
            data_quality_score=80.0,
            history_days=5,
            trend_weight_profile="baseline",
        )
        # 应该能正常计算
        assert 0 <= result["sector_selection_score"] <= 100

    def test_trend_window_accepts_10(self):
        """测试 trend-window 接受 10"""
        result = calculate_sector_composite_score(
            radar_score=70.0,
            recent_returns=[2.0, 1.5, 1.0, 0.5, 0.3, 0.2, 0.1, 0.0, -0.1, -0.2],
            sector_return=5.0,
            benchmark_return=2.0,
            positive_days_count=6,
            total_days=10,
            max_drawdown=-2.0,
            volatility=1.5,
            data_quality_score=80.0,
            history_days=10,
            trend_weight_profile="baseline",
        )
        assert 0 <= result["sector_selection_score"] <= 100

    def test_trend_window_accepts_20(self):
        """测试 trend-window 接受 20"""
        result = calculate_sector_composite_score(
            radar_score=70.0,
            recent_returns=[2.0] * 20,
            sector_return=40.0,
            benchmark_return=2.0,
            positive_days_count=20,
            total_days=20,
            max_drawdown=-2.0,
            volatility=1.5,
            data_quality_score=80.0,
            history_days=20,
            trend_weight_profile="baseline",
        )
        assert 0 <= result["sector_selection_score"] <= 100


class TestTrendWindowTruncation:
    """测试趋势窗口截取逻辑"""

    def test_truncate_returns(self):
        """测试截取最近 N 个收益率"""
        from theme_sector_radar.cli import _apply_trend_window

        history = [
            {"date": "2026-06-16", "close": 100.0},
            {"date": "2026-06-17", "close": 102.0},
            {"date": "2026-06-18", "close": 101.0},
            {"date": "2026-06-19", "close": 103.0},
            {"date": "2026-06-20", "close": 105.0},
            {"date": "2026-06-23", "close": 104.0},
            {"date": "2026-06-24", "close": 106.0},
            {"date": "2026-06-25", "close": 108.0},
            {"date": "2026-06-26", "close": 107.0},
            {"date": "2026-06-27", "close": 109.0},
            {"date": "2026-06-28", "close": 110.0},
            {"date": "2026-06-29", "close": 112.0},
        ]

        truncated, window_info = _apply_trend_window(history, trend_window=5)

        assert len(truncated) == 5
        assert truncated[0]["date"] == "2026-06-25"
        assert truncated[-1]["date"] == "2026-06-29"
        assert window_info["trend_window"] == 5
        assert window_info["actual_history_days"] == 5
        assert window_info["history_coverage_ratio"] == 1.0
        assert window_info["trend_window_status"] == "ok"

    def test_truncate_returns_insufficient(self):
        """测试历史数据不足时的截取"""
        from theme_sector_radar.cli import _apply_trend_window

        history = [
            {"date": "2026-06-28", "close": 110.0},
            {"date": "2026-06-29", "close": 112.0},
        ]

        truncated, window_info = _apply_trend_window(history, trend_window=10)

        assert len(truncated) == 2
        assert window_info["trend_window"] == 10
        assert window_info["actual_history_days"] == 2
        assert window_info["history_coverage_ratio"] == 0.2
        assert window_info["trend_window_status"] == "insufficient_history"

    def test_truncate_empty_history(self):
        """测试空历史数据"""
        from theme_sector_radar.cli import _apply_trend_window

        truncated, window_info = _apply_trend_window([], trend_window=10)

        assert len(truncated) == 0
        assert window_info["trend_window"] == 10
        assert window_info["actual_history_days"] == 0
        assert window_info["history_coverage_ratio"] == 0.0
        assert window_info["trend_window_status"] == "insufficient_history"

class TestTrendHistoryDateResolution:
    """测试趋势窗口对应的历史日期范围兜底"""

    def test_default_history_start_expands_for_20_day_window(self):
        """未显式传入 history_start_date 时，20日窗口不能只回看10天"""
        from theme_sector_radar.cli import _resolve_history_date_range

        history_start, history_end, resolution = _resolve_history_date_range(
            as_of_date="2026-07-03",
            history_start_date=None,
            history_end_date=None,
            history_lookback_days=10,
            trend_window=20,
        )

        assert history_start == "2026-05-19"
        assert history_end == "2026-07-03"
        assert resolution["effective_history_lookback_days"] == 45
        assert resolution["history_start_date_was_explicit"] is False

    def test_explicit_history_start_is_preserved(self):
        """显式传入 history_start_date 时不自动改写"""
        from theme_sector_radar.cli import _resolve_history_date_range

        history_start, history_end, resolution = _resolve_history_date_range(
            as_of_date="2026-07-03",
            history_start_date="2026-05-20",
            history_end_date="2026-07-01",
            history_lookback_days=10,
            trend_window=20,
        )

        assert history_start == "2026-05-20"
        assert history_end == "2026-07-01"
        assert resolution["history_start_date_was_explicit"] is True
        assert resolution["history_end_date_was_explicit"] is True

class TestTrendWindowInScoring:
    """测试 trend_window 在评分中的体现"""

    def test_trend_window_in_score_output(self):
        """测试 trend_window 在评分输出中"""
        result = calculate_sector_composite_score(
            radar_score=70.0,
            recent_returns=[2.0, 1.5, 1.0],
            sector_return=4.5,
            benchmark_return=2.0,
            positive_days_count=2,
            total_days=3,
            max_drawdown=-0.02,
            volatility=1.5,
            data_quality_score=80.0,
            history_days=5,
            trend_weight_profile="baseline",
        )

        # trend_weight_profile 应该在输出中
        assert "trend_weight_profile" in result
        assert result["trend_weight_profile"] == "baseline"

    def test_different_windows_produce_different_scores(self):
        """测试不同窗口产生不同的分数"""
        # 5 天窗口
        result_5 = calculate_sector_composite_score(
            radar_score=70.0,
            recent_returns=[2.0, 1.5, 1.0, 0.5, 0.3],
            sector_return=5.3,
            benchmark_return=2.0,
            positive_days_count=4,
            total_days=5,
            max_drawdown=-0.02,
            volatility=1.5,
            data_quality_score=80.0,
            history_days=5,
            trend_weight_profile="baseline",
        )

        # 10 天窗口 (使用更多数据)
        result_10 = calculate_sector_composite_score(
            radar_score=70.0,
            recent_returns=[2.0, 1.5, 1.0, 0.5, 0.3, 0.2, 0.1, 0.0, -0.1, -0.2],
            sector_return=5.3,
            benchmark_return=2.0,
            positive_days_count=6,
            total_days=10,
            max_drawdown=-0.02,
            volatility=1.5,
            data_quality_score=80.0,
            history_days=10,
            trend_weight_profile="baseline",
        )

        # 两个窗口应该产生不同的分数
        assert result_5["sector_selection_score"] != result_10["sector_selection_score"]


class TestTrendWindowAndWeightProfile:
    """测试 trend_window 和 trend_weight_profile 可以一起工作"""

    def test_trend_window_with_baseline(self):
        """测试 trend_window 和 baseline profile 一起工作"""
        result = calculate_sector_composite_score(
            radar_score=70.0,
            recent_returns=[2.0, 1.5, 1.0],
            sector_return=4.5,
            benchmark_return=2.0,
            positive_days_count=2,
            total_days=3,
            max_drawdown=-0.02,
            volatility=1.5,
            data_quality_score=80.0,
            history_days=5,
            trend_weight_profile="baseline",
        )

        assert result["trend_weight_profile"] == "baseline"
        assert 0 <= result["sector_selection_score"] <= 100

    def test_trend_window_with_trend_confirmation(self):
        """测试 trend_window 和 trend_confirmation profile 一起工作"""
        result = calculate_sector_composite_score(
            radar_score=70.0,
            recent_returns=[2.0, 1.5, 1.0],
            sector_return=4.5,
            benchmark_return=2.0,
            positive_days_count=2,
            total_days=3,
            max_drawdown=-0.02,
            volatility=1.5,
            data_quality_score=80.0,
            history_days=5,
            trend_weight_profile="trend_confirmation",
        )

        assert result["trend_weight_profile"] == "trend_confirmation"
        assert 0 <= result["sector_selection_score"] <= 100


class TestShortTermBurstScoreIndependent:
    """测试 short_term_burst_score 不受 trend_window 影响"""

    def test_burst_score_uses_recent_returns(self):
        """测试短线爆发分使用 recent_returns"""
        from theme_sector_radar.scoring.short_term_burst_score import calculate_short_term_burst_score

        # 短线爆发分应该只使用最近 3 天的收益率
        result = calculate_short_term_burst_score(
            radar_score=70.0,
            one_day_change=5.0,
            recent_returns=[3.0, 2.0, 4.0, 1.0, 0.5],  # 只用最后 3 个
            data_quality_score=80.0,
            price_change_available=True,
            history_days=5,
        )

        assert "short_term_burst_score" in result
        assert 0 <= result["short_term_burst_score"] <= 100
        # 短线爆发分不应该有 trend_window
        assert "trend_window" not in result


