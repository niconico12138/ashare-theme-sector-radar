"""
概念评分测试

测试概念板块评分逻辑。
"""

import pytest

from theme_sector_radar.models import (
    ConceptPhase,
    ConstituentSnapshot,
    SectorSnapshot,
    SectorType,
)
from theme_sector_radar.scoring.concept_score import (
    calculate_concept_phase,
    calculate_concept_score,
    calculate_heat_burst_score,
)


class TestConceptScore:
    """测试概念评分"""

    def _create_sector(self, **kwargs) -> SectorSnapshot:
        """创建测试板块"""
        defaults = {
            "sector_id": "BK1036",
            "name": "ChatGPT概念",
            "type": SectorType.CONCEPT,
            "price_change_pct": 5.0,
            "turnover": 20_000_000_000,
            "main_net_inflow": 3_000_000_000,
            "data_quality_score": 85.0,
        }
        defaults.update(kwargs)
        return SectorSnapshot(**defaults)

    def test_heat_burst_high(self):
        """测试高热度爆发"""
        sector = self._create_sector(price_change_pct=8.0, turnover=25_000_000_000)
        score = calculate_heat_burst_score(sector)
        assert score >= 20.0

    def test_heat_burst_low(self):
        """测试低热度爆发"""
        sector = self._create_sector(price_change_pct=0.5, turnover=2_000_000_000)
        score = calculate_heat_burst_score(sector)
        assert score <= 10.0

    def test_concept_phase_acceleration(self):
        """测试加速阶段"""
        sector = self._create_sector(price_change_pct=6.0, turnover=15_000_000_000)
        phase = calculate_concept_phase(sector)
        assert phase == ConceptPhase.ACCELERATION

    def test_concept_phase_retreat(self):
        """测试退潮阶段"""
        sector = self._create_sector(price_change_pct=-3.0, turnover=5_000_000_000)
        phase = calculate_concept_phase(sector)
        assert phase == ConceptPhase.RETREAT

    def test_concept_score_range(self):
        """测试概念评分范围"""
        sector = self._create_sector()
        score = calculate_concept_score(sector)
        assert 0 <= score <= 100

    def test_concept_score_high(self):
        """测试高概念评分"""
        sector = self._create_sector(
            price_change_pct=8.0,
            turnover=30_000_000_000,
            main_net_inflow=5_000_000_000,
        )
        score = calculate_concept_score(sector, ConceptPhase.ACCELERATION)
        assert score >= 70.0

    def test_concept_score_low(self):
        """测试低概念评分"""
        sector = self._create_sector(
            price_change_pct=-2.0,
            turnover=3_000_000_000,
            main_net_inflow=-500_000_000,
        )
        score = calculate_concept_score(sector, ConceptPhase.RETREAT)
        assert score <= 40.0
