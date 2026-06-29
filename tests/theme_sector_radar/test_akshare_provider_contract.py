"""
AkShare Provider 契约测试

测试 AkShareProvider 的接口契约。
注意：这些测试需要网络，使用 @pytest.mark.network 标记。
"""

import pytest

from theme_sector_radar.data.akshare_provider import AkShareProvider
from theme_sector_radar.data.providers import DataProvider
from theme_sector_radar.models import SectorType


class TestAkShareProviderContract:
    """测试 AkShareProvider 契约"""

    def test_implements_interface(self):
        """测试实现了 DataProvider 接口"""
        provider = AkShareProvider()
        assert isinstance(provider, DataProvider)

    @pytest.mark.network
    def test_get_industry_sectors(self):
        """测试获取行业板块列表"""
        provider = AkShareProvider()
        sectors = provider.get_industry_sectors("2026-06-28", top_n=5)

        # 验证返回类型
        assert isinstance(sectors, list)

        # 如果有数据，验证结构
        if sectors:
            sector = sectors[0]
            assert hasattr(sector, "sector_id")
            assert hasattr(sector, "name")
            assert hasattr(sector, "type")
            assert sector.type == SectorType.INDUSTRY

    @pytest.mark.network
    def test_get_concept_sectors(self):
        """测试获取概念板块列表"""
        provider = AkShareProvider()
        sectors = provider.get_concept_sectors("2026-06-28", top_n=5)

        # 验证返回类型
        assert isinstance(sectors, list)

        # 如果有数据，验证结构
        if sectors:
            sector = sectors[0]
            assert hasattr(sector, "sector_id")
            assert hasattr(sector, "name")
            assert hasattr(sector, "type")
            assert sector.type == SectorType.CONCEPT

    @pytest.mark.network
    def test_get_market_overview(self):
        """测试获取市场概览"""
        provider = AkShareProvider()
        overview = provider.get_market_overview("2026-06-28")

        # 验证返回类型
        assert isinstance(overview, dict)

        # 验证必要字段
        required_fields = [
            "advance_count",
            "decline_count",
            "limit_up_count",
            "limit_down_count",
            "total_turnover",
            "index_change_pct",
        ]
        for field in required_fields:
            assert field in overview

    @pytest.mark.network
    def test_error_handling(self):
        """测试错误处理"""
        provider = AkShareProvider()

        # 测试不存在的板块
        result = provider.get_sector_constituents(
            "不存在的板块",
            SectorType.INDUSTRY
        )
        # 应该返回 CallResult，status 为 degraded 或 failed，不崩溃
        from theme_sector_radar.data.akshare_provider import CallResult
        assert isinstance(result, CallResult)
        assert result.status in ["degraded", "failed"]
        assert isinstance(result.data, list)
