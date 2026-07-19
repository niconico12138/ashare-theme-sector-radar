"""
行业评分测试

测试行业板块评分逻辑。
"""

import pytest

from theme_sector_radar.models import ConstituentSnapshot, SectorSnapshot, SectorType
from theme_sector_radar.scoring.industry_score import (
    calculate_capital_flow_score,
    calculate_continuity_score,
    calculate_industry_score,
    calculate_industry_score_breakdown,
    calculate_trend_strength_score,
)


class TestIndustryScore:
    """测试行业评分"""

    def _create_sector(self, **kwargs) -> SectorSnapshot:
        """创建测试板块"""
        defaults = {
            "sector_id": "BK0428",
            "name": "半导体",
            "type": SectorType.INDUSTRY,
            "price_change_pct": 3.0,
            "turnover": 10_000_000_000,
            "main_net_inflow": 1_000_000_000,
            "data_quality_score": 80.0,
        }
        defaults.update(kwargs)
        return SectorSnapshot(**defaults)

    def test_trend_strength_high(self):
        """测试高趋势强度"""
        sector = self._create_sector(price_change_pct=5.0, turnover=15_000_000_000)
        score = calculate_trend_strength_score(
            sector,
            {
                "recent_returns": [0.5] * 20,
                "relative_strength_percentiles": {5: 1.0, 10: 1.0, 20: 1.0},
            },
        )
        assert score >= 20.0

    def test_trend_strength_low(self):
        """测试低趋势强度"""
        sector = self._create_sector(price_change_pct=-2.0, turnover=1_000_000_000)
        score = calculate_trend_strength_score(sector)
        assert score <= 10.0

    def test_trend_strength_uses_multi_day_relative_performance(self):
        sector = self._create_sector(price_change_pct=1.0, turnover=5_000_000_000)

        strong = calculate_trend_strength_score(
            sector,
            {
                "recent_returns": [0.5] * 20,
                "relative_strength_percentiles": {5: 0.9, 10: 0.8, 20: 0.75},
            },
        )
        weak = calculate_trend_strength_score(
            sector,
            {
                "recent_returns": [-0.5] * 20,
                "relative_strength_percentiles": {5: 0.1, 10: 0.2, 20: 0.25},
            },
        )

        assert strong > weak

    def test_continuity_rewards_a_stable_multi_day_path(self):
        sector = self._create_sector(price_change_pct=1.0, turnover=5_000_000_000)
        stable_returns = [0.5] * 20
        choppy_returns = [4.0, -3.5] * 10

        stable = calculate_continuity_score(
            sector,
            {
                "recent_returns": stable_returns,
                "daily_rank_percentiles": [0.9] * 10,
            },
        )
        choppy = calculate_continuity_score(
            sector,
            {
                "recent_returns": choppy_returns,
                "daily_rank_percentiles": [0.5] * 10,
            },
        )

        assert stable > choppy

    def test_breakdown_marks_missing_history_instead_of_awarding_proxy_points(self):
        sector = self._create_sector(price_change_pct=8.0, turnover=20_000_000_000)

        breakdown = calculate_industry_score_breakdown(sector)

        assert breakdown["trend_strength"] == 0.0
        assert breakdown["persistence"] == 0.0
        assert breakdown["trend_history_status"] == "insufficient_history"

    def test_breakdown_uses_only_mature_components_for_partial_history(self):
        sector = self._create_sector()
        breakdown = calculate_industry_score_breakdown(
            sector,
            trend_features={
                "recent_returns": [0.5] * 10,
                "relative_strength_percentiles": {5: 1.0, 10: 1.0},
                "daily_rank_percentiles": [1.0] * 10,
            },
        )

        assert breakdown["trend_history_status"] == "partial_history"
        assert breakdown["trend_history_coverage_ratio"] == 0.5
        assert breakdown["trend_strength"] == 14.0
        assert 0.0 < breakdown["persistence"] < 15.0

    def test_capital_flow_positive(self):
        """测试正向资金流"""
        sector = self._create_sector(main_net_inflow=2_000_000_000)
        score = calculate_capital_flow_score(sector)
        assert score >= 20.0

    def test_capital_flow_negative(self):
        """测试负向资金流"""
        sector = self._create_sector(main_net_inflow=-500_000_000)
        score = calculate_capital_flow_score(sector)
        assert score <= 10.0

    def test_industry_score_range(self):
        """测试行业评分范围"""
        sector = self._create_sector()
        score = calculate_industry_score(
            sector,
            trend_features={
                "recent_returns": [0.5] * 20,
                "relative_strength_percentiles": {5: 1.0, 10: 1.0, 20: 1.0},
                "daily_rank_percentiles": [1.0] * 10,
            },
        )
        assert 0 <= score <= 100

    def test_industry_score_high_quality(self):
        """测试高质量板块评分"""
        sector = self._create_sector(
            price_change_pct=5.0,
            turnover=20_000_000_000,
            main_net_inflow=3_000_000_000,
            data_quality_score=95.0,
        )
        score = calculate_industry_score(
            sector,
            trend_features={
                "recent_returns": [0.5] * 20,
                "relative_strength_percentiles": {5: 1.0, 10: 1.0, 20: 1.0},
                "daily_rank_percentiles": [1.0] * 10,
            },
        )
        assert score >= 70.0

    def test_industry_score_low_quality(self):
        """测试低质量板块评分"""
        sector = self._create_sector(
            price_change_pct=-3.0,
            turnover=500_000_000,
            main_net_inflow=-200_000_000,
            data_quality_score=30.0,
        )
        score = calculate_industry_score(sector)
        assert score <= 40.0

    def test_unavailable_price_payload_does_not_change_price_components(self):
        positive_payload = self._create_sector(
            price_change_pct=18.0,
            price_change_available=False,
            turnover=1_000_000_000,
            main_net_inflow=0.0,
        )
        negative_payload = self._create_sector(
            price_change_pct=-18.0,
            price_change_available=False,
            turnover=1_000_000_000,
            main_net_inflow=0.0,
        )

        positive = calculate_industry_score_breakdown(positive_payload, 80.0)
        negative = calculate_industry_score_breakdown(negative_payload, 80.0)

        for field in ("trend_strength", "persistence", "market_fit", "positive_score"):
            assert positive[field] == negative[field]
        assert positive["price_change_available"] is False
        assert negative["price_change_available"] is False
