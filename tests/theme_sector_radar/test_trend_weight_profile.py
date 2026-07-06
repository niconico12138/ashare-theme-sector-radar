"""
趋势权重 Profile 测试

测试权重 profile 管理和 trend_confirmation 权重。
"""

import pytest

from theme_sector_radar.scoring.sector_composite_score import (
    DEFAULT_WEIGHTS,
    TREND_CONFIRMATION_WEIGHTS,
    get_weight_profile,
    validate_weights,
    get_available_profiles,
    calculate_sector_composite_score,
)


class TestWeightProfiles:
    """测试权重 Profile"""

    def test_baseline_weights_total(self):
        """测试 baseline 权重总分为 100"""
        assert validate_weights(DEFAULT_WEIGHTS)

    def test_trend_confirmation_weights_total(self):
        """测试 trend_confirmation 权重总分为 100"""
        assert validate_weights(TREND_CONFIRMATION_WEIGHTS)

    def test_get_weight_profile_baseline(self):
        """测试获取 baseline profile"""
        weights = get_weight_profile("baseline")
        assert weights == DEFAULT_WEIGHTS

    def test_get_weight_profile_trend_confirmation(self):
        """测试获取 trend_confirmation profile"""
        weights = get_weight_profile("trend_confirmation")
        assert weights == TREND_CONFIRMATION_WEIGHTS

    def test_get_weight_profile_invalid(self):
        """测试获取无效 profile"""
        with pytest.raises(ValueError) as exc_info:
            get_weight_profile("invalid")
        assert "Unknown weight profile" in str(exc_info.value)

    def test_get_available_profiles(self):
        """测试获取可用 profile 列表"""
        profiles = get_available_profiles()
        assert "baseline" in profiles
        assert "trend_confirmation" in profiles

    def test_baseline_vs_trend_confirmation_weights(self):
        """测试 baseline 和 trend_confirmation 权重差异"""
        # baseline: radar=25, momentum=20, relative=15, persistence=15
        # trend_confirmation: radar=15, momentum=25, relative=20, persistence=20
        assert DEFAULT_WEIGHTS["radar_score_component"] == 25.0
        assert DEFAULT_WEIGHTS["momentum_component"] == 20.0
        assert DEFAULT_WEIGHTS["relative_strength_component"] == 15.0
        assert DEFAULT_WEIGHTS["persistence_component"] == 15.0

        assert TREND_CONFIRMATION_WEIGHTS["radar_score_component"] == 15.0
        assert TREND_CONFIRMATION_WEIGHTS["momentum_component"] == 25.0
        assert TREND_CONFIRMATION_WEIGHTS["relative_strength_component"] == 20.0
        assert TREND_CONFIRMATION_WEIGHTS["persistence_component"] == 20.0

    def test_risk_penalty_max_not_in_sum(self):
        """测试 risk_penalty_max 不参与正向组件求和"""
        # baseline
        positive_sum = sum(
            v for k, v in DEFAULT_WEIGHTS.items()
            if k != "risk_penalty_max"
        )
        assert positive_sum == 100.0

        # trend_confirmation
        positive_sum = sum(
            v for k, v in TREND_CONFIRMATION_WEIGHTS.items()
            if k != "risk_penalty_max"
        )
        assert positive_sum == 100.0


class TestTrendWeightProfileInScoring:
    """测试 trend_weight_profile 在评分中的应用"""

    def test_baseline_profile_in_composite_score(self):
        """测试 baseline profile 在综合评分中的应用"""
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
        # baseline: radar=25, momentum=20, relative=15
        assert result["score_breakdown"]["radar_score_component"] <= 25.0
        assert result["score_breakdown"]["momentum_component"] <= 20.0
        assert result["score_breakdown"]["relative_strength_component"] <= 15.0

    def test_trend_confirmation_profile_in_composite_score(self):
        """测试 trend_confirmation profile 在综合评分中的应用"""
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
        # trend_confirmation: radar=15, momentum=25, relative=20
        assert result["score_breakdown"]["radar_score_component"] <= 15.0
        assert result["score_breakdown"]["momentum_component"] <= 25.0
        assert result["score_breakdown"]["relative_strength_component"] <= 20.0

    def test_different_profiles_produce_different_scores(self):
        """测试不同 profile 产生不同的分数"""
        kwargs = {
            "radar_score": 70.0,
            "recent_returns": [2.0, 1.5, 1.0],
            "sector_return": 4.5,
            "benchmark_return": 2.0,
            "positive_days_count": 2,
            "total_days": 3,
            "max_drawdown": -0.02,
            "volatility": 1.5,
            "data_quality_score": 80.0,
            "history_days": 5,
        }

        result_baseline = calculate_sector_composite_score(
            **kwargs, trend_weight_profile="baseline"
        )
        result_trend = calculate_sector_composite_score(
            **kwargs, trend_weight_profile="trend_confirmation"
        )

        # 两个 profile 应该产生不同的分数
        assert result_baseline["sector_selection_score"] != result_trend["sector_selection_score"]

    def test_short_term_burst_score_not_affected(self):
        """测试 short_term_burst_score 不受 trend_weight_profile 影响"""
        from theme_sector_radar.scoring.short_term_burst_score import calculate_short_term_burst_score

        kwargs = {
            "radar_score": 70.0,
            "one_day_change": 5.0,
            "recent_returns": [3.0, 2.0, 4.0],
            "data_quality_score": 80.0,
            "price_change_available": True,
            "history_days": 5,
        }

        result = calculate_short_term_burst_score(**kwargs)
        # short_term_burst_score 应该只返回一个值
        assert "short_term_burst_score" in result
        assert "burst_level" in result
        # 不应该有 trend_weight_profile
        assert "trend_weight_profile" not in result


class TestTrendWeightProfileInReport:
    """测试 trend_weight_profile 在报告中的体现"""

    def test_json_report_includes_trend_weight_profile(self):
        """测试 JSON 报告包含 trend_weight_profile"""
        from theme_sector_radar.reports.sector_score_report import generate_sector_score_report

        report_data = {
            "as_of_date": "2026-06-29",
            "metadata": {
                "trend_weight_profile": "trend_confirmation",
            },
            "scores": [],
        }

        # 生成报告应该不崩溃
        report = generate_sector_score_report(report_data)
        assert "趋势权重方案" in report
        assert "trend_confirmation" in report

    def test_markdown_report_includes_weight_scheme(self):
        """测试 Markdown 报告包含趋势权重方案说明"""
        from theme_sector_radar.reports.sector_score_report import generate_sector_score_report

        # baseline
        report_data_baseline = {
            "as_of_date": "2026-06-29",
            "metadata": {"trend_weight_profile": "baseline"},
            "scores": [],
        }
        report_baseline = generate_sector_score_report(report_data_baseline)
        assert "baseline (默认)" in report_baseline

        # trend_confirmation
        report_data_trend = {
            "as_of_date": "2026-06-29",
            "metadata": {"trend_weight_profile": "trend_confirmation"},
            "scores": [],
        }
        report_trend = generate_sector_score_report(report_data_trend)
        assert "trend_confirmation (趋势确认型)" in report_trend
        assert "更重视动量、相对强度和持续性" in report_trend
