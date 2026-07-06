"""
风险评分测试

测试风险扣分、风险等级和风险标志。
所有风险扣分使用正数表示。
"""

import pytest

from theme_sector_radar.models import RiskLevel, SectorSnapshot, SectorType
from theme_sector_radar.scoring.risk_score import (
    calculate_risk_penalty,
    detect_divergence,
    detect_overheat,
)


class TestRiskScore:
    """测试风险评分"""

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

    def test_no_overheat(self):
        """测试无过热"""
        sector = self._create_sector(price_change_pct=3.0, turnover=10_000_000_000)
        is_overheat, penalty, reason = detect_overheat(sector)
        assert is_overheat is False
        assert penalty == 0.0

    def test_overheat_high_gain(self):
        """测试高涨幅过热"""
        sector = self._create_sector(price_change_pct=18.0, turnover=10_000_000_000)
        is_overheat, penalty, reason = detect_overheat(sector)
        assert is_overheat is True
        assert penalty > 0  # 正数

    def test_overheat_high_volume(self):
        """测试高成交额过热"""
        sector = self._create_sector(price_change_pct=5.0, turnover=25_000_000_000)
        is_overheat, penalty, reason = detect_overheat(sector)
        assert is_overheat is True
        assert penalty > 0  # 正数

    def test_no_divergence(self):
        """测试无分歧"""
        sector = self._create_sector(
            price_change_pct=3.0,
            main_net_inflow=1_000_000_000,
            constituents=[
                {"code": "001", "name": "A", "change_pct": 3.0, "is_core": True},
                {"code": "002", "name": "B", "change_pct": 2.5, "is_core": False},
                {"code": "003", "name": "C", "change_pct": 3.5, "is_core": False},
            ],
        )
        is_divergent, penalty, reason = detect_divergence(sector)
        assert is_divergent is False

    def test_divergence_price_flow(self):
        """测试价格资金背离"""
        sector = self._create_sector(
            price_change_pct=3.0,
            main_net_inflow=-500_000_000,
        )
        is_divergent, penalty, reason = detect_divergence(sector)
        assert is_divergent is True
        assert penalty > 0  # 正数

    def test_risk_level_low(self):
        """测试低风险等级"""
        sector = self._create_sector(
            price_change_pct=2.0,
            turnover=5_000_000_000,
            main_net_inflow=500_000_000,
        )
        penalty, level, flags, reasons = calculate_risk_penalty(sector)
        assert level == RiskLevel.LOW
        assert penalty >= 0  # 正数

    def test_risk_level_high(self):
        """测试高风险等级"""
        sector = self._create_sector(
            price_change_pct=20.0,
            turnover=30_000_000_000,
            main_net_inflow=-2_000_000_000,
        )
        penalty, level, flags, reasons = calculate_risk_penalty(sector)
        assert level == RiskLevel.HIGH
        assert penalty >= 15  # 正数

    def test_risk_penalty_range(self):
        """测试风险扣分范围"""
        sector = self._create_sector()
        penalty, _, _, _ = calculate_risk_penalty(sector)
        assert 0 <= penalty <= 30  # 正数范围

    def test_ths_industry_index_source_not_data_quality_low(self):
        sector = self._create_sector(
            data_sources=["akshare/ths_industry"],
            data_quality_score=80.0,
            price_change_available=True,
            updated_at="2026-07-01T15:30:00",
            constituents=[],
        )

        penalty, level, flags, reasons = calculate_risk_penalty(sector)

        assert "data_quality_low" not in flags

    def test_ths_concept_without_price_change_remains_data_quality_low(self):
        sector = self._create_sector(
            type=SectorType.CONCEPT,
            data_sources=["akshare/ths_concept"],
            data_quality_score=50.0,
            price_change_available=False,
            updated_at="2026-07-01T15:30:00",
            constituents=[],
        )

        penalty, level, flags, reasons = calculate_risk_penalty(sector)

        assert "data_quality_low" in flags

