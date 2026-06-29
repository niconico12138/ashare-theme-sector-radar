"""
标准化测试

测试不同原始字段能归一化为 SectorSnapshot。
"""

import pytest

from theme_sector_radar.agents.data.sector_normalizer_agent import normalize_sector_data
from theme_sector_radar.data.snapshots import normalize_sector_data as normalize_snapshot
from theme_sector_radar.models import SectorType


class TestSectorNormalizer:
    """测试板块标准化"""

    def test_normalize_with_standard_fields(self):
        """测试标准字段标准化"""
        raw_data = {
            "sector_id": "BK0428",
            "name": "半导体",
            "price_change_pct": 3.21,
            "turnover": 12345678900,
            "main_net_inflow": 1234560000,
            "data_sources": ["akshare"],
            "data_quality_score": 88.0,
        }

        result = normalize_snapshot(raw_data, SectorType.INDUSTRY)

        assert result.sector_id == "BK0428"
        assert result.name == "半导体"
        assert result.type == SectorType.INDUSTRY
        assert result.price_change_pct == 3.21

    def test_normalize_with_alias_fields(self):
        """测试别名字段标准化"""
        raw_data = {
            "board_code": "BK0428",
            "board_name": "半导体",
            "change_pct": 3.21,
            "amount": 12345678900,
            "net_inflow": 1234560000,
        }

        result = normalize_snapshot(raw_data, SectorType.INDUSTRY)

        assert result.sector_id == "BK0428"
        assert result.name == "半导体"
        assert result.price_change_pct == 3.21

    def test_normalize_with_constituents(self):
        """测试带成分股标准化"""
        raw_data = {
            "sector_id": "BK0428",
            "name": "半导体",
            "price_change_pct": 3.21,
        }

        constituents = [
            {"code": "688981", "name": "中芯国际", "change_pct": 5.2, "is_core": True},
        ]

        result = normalize_snapshot(raw_data, SectorType.INDUSTRY, constituents)

        assert len(result.constituents) == 1
        assert result.constituents[0].code == "688981"
        assert result.constituents[0].is_core is True

    def test_normalize_agent_output(self):
        """测试 Agent 标准化输出"""
        raw_sectors = [
            {
                "sector_id": "BK0428",
                "name": "半导体",
                "price_change_pct": 3.21,
            },
        ]

        output = normalize_sector_data(raw_sectors, SectorType.INDUSTRY)

        assert output.agent_id == "sector_normalizer"
        assert "sectors" in output.data
        assert len(output.data["sectors"]) == 1

    def test_normalize_empty_list(self):
        """测试空列表标准化"""
        output = normalize_sector_data([], SectorType.INDUSTRY)

        assert output.agent_id == "sector_normalizer"
        assert output.data["sectors"] == []
