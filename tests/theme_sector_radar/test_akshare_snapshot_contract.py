"""
AkShare 快照契约测试

测试 AkShare 数据快照的契约要求。
"""

import pytest

from theme_sector_radar.data.akshare_provider import AkShareProvider
from theme_sector_radar.models import SectorType


class TestAkShareSnapshotContract:
    """测试 AkShare 快照契约"""

    @pytest.mark.network
    def test_industry_snapshot_has_required_fields(self):
        """测试行业板块快照包含必要字段"""
        provider = AkShareProvider()
        sectors = provider.get_industry_sectors("2026-06-28", top_n=5)

        for sector in sectors:
            # 验证必要字段存在
            assert hasattr(sector, "sector_id")
            assert hasattr(sector, "name")
            assert hasattr(sector, "type")
            assert hasattr(sector, "price_change_pct")
            assert hasattr(sector, "data_sources")
            assert hasattr(sector, "updated_at")
            assert hasattr(sector, "data_quality_score")

            # 验证字段值
            assert isinstance(sector.sector_id, str)
            assert isinstance(sector.name, str)
            assert sector.type == SectorType.INDUSTRY
            assert isinstance(sector.price_change_pct, float)
            assert isinstance(sector.data_sources, list)
            assert isinstance(sector.updated_at, str)
            assert isinstance(sector.data_quality_score, float)

    @pytest.mark.network
    def test_concept_snapshot_has_required_fields(self):
        """测试概念板块快照包含必要字段"""
        provider = AkShareProvider()
        sectors = provider.get_concept_sectors("2026-06-28", top_n=5)

        for sector in sectors:
            # 验证必要字段存在
            assert hasattr(sector, "sector_id")
            assert hasattr(sector, "name")
            assert hasattr(sector, "type")
            assert hasattr(sector, "price_change_pct")
            assert hasattr(sector, "data_sources")
            assert hasattr(sector, "updated_at")
            assert hasattr(sector, "data_quality_score")

            # 验证字段值
            assert isinstance(sector.sector_id, str)
            assert isinstance(sector.name, str)
            assert sector.type == SectorType.CONCEPT
            assert isinstance(sector.price_change_pct, float)
            assert isinstance(sector.data_sources, list)
            assert isinstance(sector.updated_at, str)
            assert isinstance(sector.data_quality_score, float)

    @pytest.mark.network
    def test_data_sources_contains_akshare(self):
        """测试 data_sources 包含 akshare 标识"""
        provider = AkShareProvider()

        industry_sectors = provider.get_industry_sectors("2026-06-28", top_n=3)
        concept_sectors = provider.get_concept_sectors("2026-06-28", top_n=3)

        for sector in industry_sectors:
            assert any("akshare" in ds for ds in sector.data_sources), \
                f"行业板块 {sector.name} 的 data_sources 应包含 akshare"

        for sector in concept_sectors:
            assert any("akshare" in ds for ds in sector.data_sources), \
                f"概念板块 {sector.name} 的 data_sources 应包含 akshare"

    @pytest.mark.network
    def test_updated_at_is_not_empty(self):
        """测试 updated_at 不为空"""
        provider = AkShareProvider()

        industry_sectors = provider.get_industry_sectors("2026-06-28", top_n=3)
        concept_sectors = provider.get_concept_sectors("2026-06-28", top_n=3)

        for sector in industry_sectors:
            assert sector.updated_at, f"行业板块 {sector.name} 的 updated_at 不应为空"

        for sector in concept_sectors:
            assert sector.updated_at, f"概念板块 {sector.name} 的 updated_at 不应为空"

    @pytest.mark.network
    def test_data_quality_score_in_valid_range(self):
        """测试 data_quality_score 在有效范围内"""
        provider = AkShareProvider()

        industry_sectors = provider.get_industry_sectors("2026-06-28", top_n=3)
        concept_sectors = provider.get_concept_sectors("2026-06-28", top_n=3)

        for sector in industry_sectors:
            assert 0 <= sector.data_quality_score <= 100, \
                f"行业板块 {sector.name} 的 data_quality_score 应在 0-100 之间"

        for sector in concept_sectors:
            assert 0 <= sector.data_quality_score <= 100, \
                f"概念板块 {sector.name} 的 data_quality_score 应在 0-100 之间"

    def test_fixture_provider_also_has_correct_types(self):
        """测试 FixtureProvider 也有正确的类型"""
        from theme_sector_radar.data.fixture_provider import FixtureProvider

        provider = FixtureProvider()
        industry_sectors = provider.get_industry_sectors("2026-06-28", top_n=5)
        concept_sectors = provider.get_concept_sectors("2026-06-28", top_n=5)

        for sector in industry_sectors:
            assert sector.type == SectorType.INDUSTRY

        for sector in concept_sectors:
            assert sector.type == SectorType.CONCEPT
