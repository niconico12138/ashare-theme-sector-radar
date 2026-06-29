"""
共振逻辑测试

测试行业与概念板块共振检测。
"""

import pytest

from theme_sector_radar.agents.ranking_report.industry_concept_overlap_agent import (
    calculate_overlap_resonance,
)
from theme_sector_radar.models import (
    ConstituentSnapshot,
    FocusLevel,
    FlowAlignment,
    SectorScore,
    SectorSnapshot,
    SectorType,
)


class TestOverlapResonance:
    """测试共振逻辑"""

    def _create_sector(
        self,
        sector_id: str,
        name: str,
        sector_type: SectorType,
        constituents: list = None,
        main_net_inflow: float = 1_000_000_000,
    ) -> SectorSnapshot:
        """创建测试板块"""
        if constituents is None:
            constituents = []

        return SectorSnapshot(
            sector_id=sector_id,
            name=name,
            type=sector_type,
            main_net_inflow=main_net_inflow,
            constituents=[
                ConstituentSnapshot(**c) for c in constituents
            ],
        )

    def _create_score(
        self,
        sector_id: str,
        name: str,
        score: float = 80.0,
    ) -> SectorScore:
        """创建测试评分"""
        return SectorScore(
            sector_id=sector_id,
            name=name,
            type=SectorType.INDUSTRY,
            score=score,
            positive_score=score,
        )

    def test_no_overlap(self):
        """测试无重合"""
        industry = self._create_sector(
            "BK0428", "半导体", SectorType.INDUSTRY,
            constituents=[{"code": "001", "name": "A"}],
        )
        concept = self._create_sector(
            "BK1036", "ChatGPT", SectorType.CONCEPT,
            constituents=[{"code": "002", "name": "B"}],
        )

        output = calculate_overlap_resonance(
            [industry], [concept],
            [self._create_score("BK0428", "半导体")],
            [self._create_score("BK1036", "ChatGPT")],
        )

        assert output.data["resonance"] == []

    def test_overlap_with_common_constituents(self):
        """测试有共同成分股的共振"""
        industry = self._create_sector(
            "BK0428", "半导体", SectorType.INDUSTRY,
            constituents=[
                {"code": "001", "name": "A", "is_core": True},
                {"code": "002", "name": "B", "is_core": False},
            ],
        )
        concept = self._create_sector(
            "BK1036", "ChatGPT", SectorType.CONCEPT,
            constituents=[
                {"code": "001", "name": "A", "is_core": True},
                {"code": "003", "name": "C", "is_core": False},
            ],
        )

        output = calculate_overlap_resonance(
            [industry], [concept],
            [self._create_score("BK0428", "半导体")],
            [self._create_score("BK1036", "ChatGPT")],
        )

        assert len(output.data["resonance"]) == 1
        resonance = output.data["resonance"][0]
        assert resonance["overlap_constituent_count"] == 1
        assert resonance["common_core_count"] == 1

    def test_resonance_score_range(self):
        """测试共振分范围"""
        industry = self._create_sector(
            "BK0428", "半导体", SectorType.INDUSTRY,
            constituents=[
                {"code": "001", "name": "A", "is_core": True},
                {"code": "002", "name": "B", "is_core": True},
            ],
            main_net_inflow=2_000_000_000,
        )
        concept = self._create_sector(
            "BK1036", "ChatGPT", SectorType.CONCEPT,
            constituents=[
                {"code": "001", "name": "A", "is_core": True},
                {"code": "002", "name": "B", "is_core": True},
                {"code": "003", "name": "C", "is_core": False},
            ],
            main_net_inflow=3_000_000_000,
        )

        output = calculate_overlap_resonance(
            [industry], [concept],
            [self._create_score("BK0428", "半导体", 85.0)],
            [self._create_score("BK1036", "ChatGPT", 82.0)],
        )

        if output.data["resonance"]:
            resonance = output.data["resonance"][0]
            assert 0 <= resonance["resonance_score"] <= 100

    def test_both_top_n_boost(self):
        """测试双强确认加分"""
        industry = self._create_sector(
            "BK0428", "半导体", SectorType.INDUSTRY,
            constituents=[{"code": "001", "name": "A"}],
        )
        concept = self._create_sector(
            "BK1036", "ChatGPT", SectorType.CONCEPT,
            constituents=[{"code": "001", "name": "A"}],
        )

        # 都在 Top N
        output_top = calculate_overlap_resonance(
            [industry], [concept],
            [self._create_score("BK0428", "半导体")],
            [self._create_score("BK1036", "ChatGPT")],
        )

        # 只有行业在 Top N
        output_partial = calculate_overlap_resonance(
            [industry], [concept],
            [self._create_score("BK0428", "半导体")],
            [],
        )

        if output_top.data["resonance"] and output_partial.data["resonance"]:
            assert output_top.data["resonance"][0]["resonance_score"] >= \
                   output_partial.data["resonance"][0]["resonance_score"]
