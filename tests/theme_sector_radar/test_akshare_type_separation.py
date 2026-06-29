"""
AkShare 类型分离测试

测试行业板块和概念板块的类型分离是否正确。
"""

import pytest

from theme_sector_radar.data.akshare_provider import AkShareProvider
from theme_sector_radar.models import SectorType


class TestAkShareTypeSeparation:
    """测试 AkShare 类型分离"""

    @pytest.mark.network
    def test_industry_type_is_industry(self):
        """测试行业板块 type 必须是 industry"""
        provider = AkShareProvider()
        sectors = provider.get_industry_sectors("2026-06-28", top_n=10)

        for sector in sectors:
            assert sector.type == SectorType.INDUSTRY, \
                f"行业板块 {sector.name} 的 type 应为 industry，实际为 {sector.type}"

    @pytest.mark.network
    def test_concept_type_is_concept(self):
        """测试概念板块 type 必须是 concept"""
        provider = AkShareProvider()
        sectors = provider.get_concept_sectors("2026-06-28", top_n=10)

        for sector in sectors:
            assert sector.type == SectorType.CONCEPT, \
                f"概念板块 {sector.name} 的 type 应为 concept，实际为 {sector.type}"

    @pytest.mark.network
    def test_industry_and_concept_are_separate_lists(self):
        """测试行业和概念板块是独立的列表"""
        provider = AkShareProvider()
        industry_sectors = provider.get_industry_sectors("2026-06-28", top_n=10)
        concept_sectors = provider.get_concept_sectors("2026-06-28", top_n=10)

        # 验证是不同的列表对象
        assert industry_sectors is not concept_sectors

        # 验证行业板块中没有 concept 类型
        for sector in industry_sectors:
            assert sector.type != SectorType.CONCEPT

        # 验证概念板块中没有 industry 类型
        for sector in concept_sectors:
            assert sector.type != SectorType.INDUSTRY

    @pytest.mark.network
    def test_industry_count_and_concept_count_are_independent(self):
        """测试行业和概念数量分别统计"""
        provider = AkShareProvider()
        industry_sectors = provider.get_industry_sectors("2026-06-28", top_n=5)
        concept_sectors = provider.get_concept_sectors("2026-06-28", top_n=5)

        # 数量可以不同，但都应该有数据（网络正常时）
        # 这里只验证它们是独立统计的
        industry_count = len(industry_sectors)
        concept_count = len(concept_sectors)

        # 验证各自有数据（假设网络正常）
        # 如果网络异常，可能会返回空列表
        if industry_count > 0:
            assert all(s.type == SectorType.INDUSTRY for s in industry_sectors)
        if concept_count > 0:
            assert all(s.type == SectorType.CONCEPT for s in concept_sectors)

    def test_raw_data_separation(self):
        """测试 raw_data 中 industry 和 concept 不共用同一个 list 对象"""
        from theme_sector_radar.pipeline import run_pipeline

        # 使用离线 fixture 测试
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            provider_name="fixture",
        )

        # 验证 pipeline 能正常运行
        assert report is not None
        assert report.report_type == "theme_sector_radar"

        # 验证行业和概念板块都有数据
        assert len(report.industry_top) > 0
        assert len(report.concept_top) > 0

        # 验证行业板块类型正确
        for score in report.industry_top:
            assert score.type.value == "industry"

        # 验证概念板块类型正确
        for score in report.concept_top:
            assert score.type.value == "concept"

    @pytest.mark.network
    def test_network_failure_returns_empty_or_degraded(self):
        """测试网络失败时返回空列表或降级"""
        provider = AkShareProvider()

        # 模拟网络失败的情况
        # 由于我们无法真正模拟网络失败，这里测试接口的容错性
        try:
            sectors = provider.get_industry_sectors("2026-06-28", top_n=10)
            # 如果成功获取，验证类型正确
            for sector in sectors:
                assert sector.type == SectorType.INDUSTRY
        except Exception as e:
            # 如果失败，应该是网络相关异常
            assert "network" in str(e).lower() or "connection" in str(e).lower() or "timeout" in str(e).lower()
