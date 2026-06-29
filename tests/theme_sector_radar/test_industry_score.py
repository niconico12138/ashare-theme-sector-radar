"""
行业评分测试

测试行业板块评分逻辑。
"""

import pytest

from theme_sector_radar.models import ConstituentSnapshot, SectorSnapshot, SectorType
from theme_sector_radar.scoring.industry_score import (
    calculate_capital_flow_score,
    calculate_industry_score,
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
        score = calculate_trend_strength_score(sector)
        assert score >= 20.0

    def test_trend_strength_low(self):
        """测试低趋势强度"""
        sector = self._create_sector(price_change_pct=-2.0, turnover=1_000_000_000)
        score = calculate_trend_strength_score(sector)
        assert score <= 10.0

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
        score = calculate_industry_score(sector)
        assert 0 <= score <= 100

    def test_industry_score_high_quality(self):
        """测试高质量板块评分"""
        sector = self._create_sector(
            price_change_pct=5.0,
            turnover=20_000_000_000,
            main_net_inflow=3_000_000_000,
            data_quality_score=95.0,
        )
        score = calculate_industry_score(sector)
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
