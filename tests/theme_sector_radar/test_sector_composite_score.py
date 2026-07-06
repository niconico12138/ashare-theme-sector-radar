"""
板块综合评分测试

测试 sector_composite_score.py 模块的各项功能。
"""

import pytest

from theme_sector_radar.scoring.sector_composite_score import (
    calculate_data_quality_component,
    calculate_drawdown_component,
    calculate_momentum_component,
    calculate_persistence_component,
    calculate_radar_score_component,
    calculate_risk_penalty,
    calculate_relative_strength_component,
    calculate_sector_composite_score,
    calculate_volatility_component,
    generate_data_warnings,
    generate_risk_reasons,
    generate_strength_reasons,
    generate_watch_points,
    get_selection_level,
)


class TestRadarScoreComponent:
    """测试日报雷达分组件"""

    def test_perfect_score(self):
        """测试满分"""
        score = calculate_radar_score_component(100.0)
        assert score == 25.0

    def test_zero_score(self):
        """测试零分"""
        score = calculate_radar_score_component(0.0)
        assert score == 0.0

    def test_half_score(self):
        """测试半分"""
        score = calculate_radar_score_component(50.0)
        assert score == 12.5

    def test_custom_weight(self):
        """测试自定义权重"""
        score = calculate_radar_score_component(100.0, weight=20.0)
        assert score == 20.0


class TestMomentumComponent:
    """测试动量组件"""

    def test_empty_returns(self):
        """测试空收益率"""
        score = calculate_momentum_component([])
        assert score == 6.0  # 20 * 0.3

    def test_positive_returns(self):
        """测试正收益率"""
        score = calculate_momentum_component([5.0, 3.0, 2.0])
        # 加权动量 = (5*1 + 3*2 + 2*3) / (1+2+3) = 19/6 ≈ 3.17
        # normalized = 0.6, score = 0.6 * 20 = 12.0
        assert score == 12.0

    def test_negative_returns(self):
        """测试负收益率"""
        score = calculate_momentum_component([-5.0, -3.0, -2.0])
        assert score == 0.0

    def test_mixed_returns(self):
        """测试混合收益率"""
        score = calculate_momentum_component([1.0, -1.0, 0.5])
        assert 0.0 <= score <= 20.0


class TestRelativeStrengthComponent:
    """测试相对强度组件"""

    def test_outperform(self):
        """测试跑赢基准"""
        score, mode, benchmark_id, benchmark_name = calculate_relative_strength_component(5.0, 0.0)
        assert score == 15.0
        assert mode == "sector_median"

    def test_underperform(self):
        """测试跑输基准"""
        score, mode, benchmark_id, benchmark_name = calculate_relative_strength_component(-5.0, 0.0)
        assert score == 1.5

    def test_with_sector_returns(self):
        """测试使用行业收益率"""
        all_returns = [1.0, 2.0, 3.0, 4.0, 5.0]
        score, mode, benchmark_id, benchmark_name = calculate_relative_strength_component(3.0, 0.0, all_returns)
        assert mode == "sector_median"


class TestPersistenceComponent:
    """测试持续性组件"""

    def test_all_positive(self):
        """测试全部上涨"""
        score = calculate_persistence_component(5, 5)
        assert score == 15.0

    def test_all_negative(self):
        """测试全部下跌"""
        score = calculate_persistence_component(0, 5)
        assert score == 0.0

    def test_half_positive(self):
        """测试一半上涨"""
        score = calculate_persistence_component(3, 5)
        # persistence_ratio = 0.6, normalized = 0.75, score = 0.75 * 15 = 11.25
        assert score == 11.25


class TestDrawdownComponent:
    """测试回撤组件"""

    def test_no_drawdown(self):
        """测试无回撤"""
        score = calculate_drawdown_component(0.0)
        assert score == 10.0

    def test_small_drawdown(self):
        """测试小回撤"""
        score = calculate_drawdown_component(-0.01)
        assert score == 10.0

    def test_large_drawdown(self):
        """测试大回撤"""
        # max_drawdown 使用百分数点，-20.0 表示 -20%
        score = calculate_drawdown_component(-20.0)
        assert score == 0.0


class TestVolatilityComponent:
    """测试波动率组件"""

    def test_low_volatility(self):
        """测试低波动率"""
        score = calculate_volatility_component(0.5)
        assert score == 5.0

    def test_high_volatility(self):
        """测试高波动率"""
        score = calculate_volatility_component(6.0)
        assert score == 1.0


class TestDataQualityComponent:
    """测试数据质量组件"""

    def test_good_quality(self):
        """测试高质量"""
        score = calculate_data_quality_component(80.0, 5, True)
        assert score == 10.0

    def test_insufficient_history(self):
        """测试历史数据不足"""
        score = calculate_data_quality_component(80.0, 1, True)
        assert score < 10.0

    def test_no_price_change(self):
        """测试无涨跌幅数据"""
        score = calculate_data_quality_component(80.0, 5, False)
        assert score < 10.0


class TestRiskPenalty:
    """测试风险扣分"""

    def test_no_risk(self):
        """测试无风险"""
        penalty = calculate_risk_penalty(0.0, 1.0, 0, 5)
        assert penalty == 0.0

    def test_high_risk(self):
        """测试高风险"""
        # max_drawdown 使用百分数点，-20.0 表示 -20%
        penalty = calculate_risk_penalty(-20.0, 6.0, 4, 5)
        assert penalty == 20.0

    def test_medium_risk(self):
        """测试中等风险"""
        # max_drawdown 使用百分数点，-8.0 表示 -8%
        penalty = calculate_risk_penalty(-8.0, 2.5, 2, 5)
        assert 5.0 <= penalty <= 15.0


class TestSelectionLevel:
    """测试选择等级"""

    def test_strong_watch(self):
        """测试 strong_watch"""
        level = get_selection_level(85.0)
        assert level == "strong_watch"

    def test_watch(self):
        """测试 watch"""
        level = get_selection_level(70.0)
        assert level == "watch"

    def test_neutral(self):
        """测试 neutral"""
        level = get_selection_level(55.0)
        assert level == "neutral"

    def test_cooling(self):
        """测试 cooling"""
        level = get_selection_level(40.0)
        assert level == "cooling"

    def test_avoid(self):
        """测试 avoid"""
        level = get_selection_level(30.0)
        assert level == "avoid"


class TestCompositeScore:
    """测试综合评分"""

    def test_perfect_conditions(self):
        """测试完美条件"""
        result = calculate_sector_composite_score(
            radar_score=100.0,
            recent_returns=[5.0, 4.0, 3.0, 2.0, 1.0],
            sector_return=15.0,
            all_sector_returns=[1.0, 2.0, 3.0, 4.0, 5.0],
            positive_days_count=5,
            total_days=5,
            max_drawdown=0.0,
            volatility=1.0,
            data_quality_score=100.0,
            history_days=5,
            price_change_available=True,
        )
        assert result["sector_selection_score"] >= 80.0
        assert result["selection_level"] == "strong_watch"

    def test_poor_conditions(self):
        """测试较差条件"""
        # max_drawdown 使用百分数点，-20.0 表示 -20%
        result = calculate_sector_composite_score(
            radar_score=20.0,
            recent_returns=[-5.0, -4.0, -3.0, -2.0, -1.0],
            sector_return=-15.0,
            all_sector_returns=[-1.0, -2.0, -3.0, -4.0, -5.0],
            positive_days_count=0,
            total_days=5,
            max_drawdown=-20.0,
            volatility=6.0,
            data_quality_score=20.0,
            history_days=1,
            price_change_available=False,
        )
        assert result["sector_selection_score"] < 35.0
        assert result["selection_level"] == "avoid"

    def test_score_breakdown_sum(self):
        """测试评分拆解加总"""
        # max_drawdown 使用百分数点，-3.0 表示 -3%
        result = calculate_sector_composite_score(
            radar_score=70.0,
            recent_returns=[2.0, 1.0, 0.5],
            sector_return=3.5,
            positive_days_count=2,
            total_days=3,
            max_drawdown=-3.0,
            volatility=1.5,
            data_quality_score=60.0,
            history_days=3,
        )
        breakdown = result["score_breakdown"]

        # 验证正向总分
        positive_sum = (
            breakdown["radar_score_component"]
            + breakdown["momentum_component"]
            + breakdown["relative_strength_component"]
            + breakdown["persistence_component"]
            + breakdown["drawdown_component"]
            + breakdown["volatility_component"]
            + breakdown["data_quality_component"]
        )
        assert abs(breakdown["positive_score"] - positive_sum) < 0.1

        # 验证最终得分
        expected_final = max(positive_sum - breakdown["risk_penalty"], 0.0)
        assert abs(breakdown["final_score"] - expected_final) < 0.1


class TestDiagnosticFunctions:
    """测试诊断函数"""

    def test_strength_reasons(self):
        """测试强度原因"""
        reasons = generate_strength_reasons(
            radar_score=80.0,
            momentum=5.0,
            relative_strength=3.0,
            persistence_ratio=0.8,
            selection_level="strong_watch",
        )
        assert len(reasons) > 0
        assert any("日报雷达分较高" in r for r in reasons)

    def test_risk_reasons(self):
        """测试风险原因"""
        # max_drawdown 使用百分数点，-15.0 表示 -15%
        reasons = generate_risk_reasons(
            max_drawdown=-15.0,
            volatility=4.0,
            negative_ratio=0.6,
        )
        assert len(reasons) > 0

    def test_risk_reasons_drawdown_format_pct_points(self):
        """H1: max_drawdown 为百分数点 (-8.68) 时，格式应为 -8.7%，不是 -868.0%"""
        reasons = generate_risk_reasons(
            max_drawdown=-8.68,
            volatility=1.0,
            negative_ratio=0.2,
        )
        # 应显示 "-8.7%" 而不是 "-868.0%"
        drawdown_reason = [r for r in reasons if "回撤" in r]
        assert len(drawdown_reason) == 1, f"Expected 1 drawdown reason, got {drawdown_reason}"
        assert "-8.7%" in drawdown_reason[0], f"Expected '-8.7%' in reason: {drawdown_reason[0]}"
        assert "-868.0%" not in drawdown_reason[0]

    def test_risk_reasons_drawdown_thresholds(self):
        """H1: 回撤阈值按百分数点解释：>10% 较大，>5% 存在一定回撤"""
        # 9.5% 回撤 -> 触发 "存在一定回撤"
        reasons_moderate = generate_risk_reasons(
            max_drawdown=-9.5,
            volatility=1.0,
            negative_ratio=0.2,
        )
        drawdown_moderate = [r for r in reasons_moderate if "回撤" in r]
        assert len(drawdown_moderate) == 1
        assert "存在一定回撤" in drawdown_moderate[0]

        # 15% 回撤 -> 触发 "最大回撤较大"
        reasons_large = generate_risk_reasons(
            max_drawdown=-15.0,
            volatility=1.0,
            negative_ratio=0.2,
        )
        drawdown_large = [r for r in reasons_large if "回撤" in r]
        assert len(drawdown_large) == 1
        assert "最大回撤较大" in drawdown_large[0]

        # 3% 回撤 -> 不触发回撤原因
        reasons_small = generate_risk_reasons(
            max_drawdown=-3.0,
            volatility=1.0,
            negative_ratio=0.2,
        )
        drawdown_small = [r for r in reasons_small if "回撤" in r]
        assert len(drawdown_small) == 0, f"Expected no drawdown reason for small drawdown: {drawdown_small}"

    def test_risk_reasons_volatility_format(self):
        """确认 volatility 格式保持正确"""
        reasons = generate_risk_reasons(
            max_drawdown=-3.0,
            volatility=3.5,
            negative_ratio=0.2,
        )
        vol_reason = [r for r in reasons if "波动率" in r]
        assert len(vol_reason) == 1
        assert "3.5" in vol_reason[0], f"Expected '3.5' in volatility reason: {vol_reason[0]}"

    def test_watch_points(self):
        """测试观察要点"""
        points = generate_watch_points(
            selection_level="strong_watch",
            benchmark_mode="sector_median",
            persistence_ratio=0.7,
            volatility=2.0,
        )
        assert len(points) > 0

    def test_data_warnings(self):
        """测试数据警告"""
        warnings = generate_data_warnings(
            history_days=1,
            price_change_available=False,
            sector_type="concept",
        )
        assert len(warnings) > 0
        assert any("历史数据不足" in w for w in warnings)
