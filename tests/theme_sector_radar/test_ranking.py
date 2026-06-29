"""
排名逻辑测试

测试板块排名生成。
"""

import pytest

from theme_sector_radar.agents.ranking_report.sector_ranking_agent import (
    generate_sector_ranking,
)
from theme_sector_radar.models import (
    FocusLevel,
    RiskLevel,
    SectorSnapshot,
    SectorType,
)


class TestSectorRanking:
    """测试板块排名"""

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

    def test_ranking_output_structure(self):
        """测试排名输出结构"""
        sectors = [
            self._create_sector(sector_id="BK0428", name="半导体"),
            self._create_sector(sector_id="BK0437", name="人工智能"),
        ]

        output = generate_sector_ranking(sectors, [], top_n=10)

        assert "industry_top" in output.data
        assert "concept_top" in output.data
        assert len(output.data["industry_top"]) == 2

    def test_ranking_sorted_by_score(self):
        """测试排名按分数排序"""
        sectors = [
            self._create_sector(sector_id="BK0428", name="半导体", price_change_pct=2.0),
            self._create_sector(sector_id="BK0437", name="人工智能", price_change_pct=5.0),
            self._create_sector(sector_id="BK0447", name="新能源", price_change_pct=3.0),
        ]

        output = generate_sector_ranking(sectors, [], top_n=10)

        scores = output.data["industry_top"]
        assert scores[0]["name"] == "人工智能"
        assert scores[1]["name"] == "新能源"
        assert scores[2]["name"] == "半导体"

    def test_ranking_top_n_limit(self):
        """测试 Top N 限制"""
        sectors = [
            self._create_sector(sector_id=f"BK{i}", name=f"板块{i}")
            for i in range(20)
        ]

        output = generate_sector_ranking(sectors, [], top_n=5)

        assert len(output.data["industry_top"]) == 5

    def test_focus_level_assignment(self):
        """测试关注等级分配"""
        # 高分板块
        high_sector = self._create_sector(
            sector_id="BK0428",
            name="半导体",
            price_change_pct=5.0,
            turnover=20_000_000_000,
            main_net_inflow=3_000_000_000,
            data_quality_score=90.0,
        )

        # 低分板块
        low_sector = self._create_sector(
            sector_id="BK0476",
            name="光伏",
            price_change_pct=-3.0,
            turnover=2_000_000_000,
            main_net_inflow=-500_000_000,
            data_quality_score=50.0,
        )

        output = generate_sector_ranking([high_sector, low_sector], [], top_n=10)

        industry_top = output.data["industry_top"]
        # 高分板块应该有更高的关注等级
        high_score_item = next(s for s in industry_top if s["name"] == "半导体")
        low_score_item = next(s for s in industry_top if s["name"] == "光伏")

        # 高分板块的 score 应该更高
        assert high_score_item["score"] > low_score_item["score"]

    def test_risk_flags_in_output(self):
        """测试风险标志在输出中"""
        sector = self._create_sector(
            sector_id="BK0428",
            name="半导体",
            price_change_pct=18.0,  # 过热
            turnover=25_000_000_000,
        )

        output = generate_sector_ranking([sector], [], top_n=10)

        industry_top = output.data["industry_top"]
        assert len(industry_top) == 1
        # 应该有过热风险标志
        assert "overheat" in industry_top[0]["risk_flags"]
