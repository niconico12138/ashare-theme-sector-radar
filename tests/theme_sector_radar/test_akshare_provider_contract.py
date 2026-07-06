"""
AkShare Provider 契约测试

测试 AkShareProvider 的接口契约。
注意：这些测试需要网络，使用 @pytest.mark.network 标记。
"""

import pytest

from theme_sector_radar.data.akshare_provider import AkShareProvider, CallResult, ProviderStatusInfo
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
        assert isinstance(result, CallResult)
        assert result.status in ["degraded", "failed"]
        assert isinstance(result.data, list)


class TestAkShareProviderTHSFallback:
    """测试 AkShareProvider THS Fallback 功能"""

    def test_provider_status_info_initialization(self):
        """测试 ProviderStatusInfo 初始化"""
        status_info = ProviderStatusInfo()
        assert status_info.effective_provider == "akshare"
        assert status_info.industry_source == ""
        assert status_info.concept_source == ""
        assert status_info.fallback_used is False
        assert status_info.fallback_provider == ""
        assert status_info.fallback_reason == ""
        assert status_info.industry_count == 0
        assert status_info.concept_count == 0
        assert status_info.em_industry_error == ""
        assert status_info.em_concept_error == ""

    def test_akshare_provider_status_tracking(self):
        """测试 AkShareProvider 状态追踪"""
        provider = AkShareProvider()
        status = provider.get_provider_status()
        assert isinstance(status, ProviderStatusInfo)
        assert status.effective_provider == "akshare"

    @pytest.mark.network
    def test_ths_fallback_on_em_failure(self):
        """测试 EM 失败时自动使用 THS fallback"""
        provider = AkShareProvider()
        sectors = provider.get_industry_sectors("2026-06-29", top_n=5)

        # 验证返回类型
        assert isinstance(sectors, list)

        # 获取 provider 状态
        status = provider.get_provider_status()

        # 如果 EM 失败，应该 fallback 到 THS
        if status.fallback_used:
            assert status.fallback_provider == "ths"
            assert "akshare/ths_industry" in status.industry_source
            assert status.industry_count > 0
            assert len(status.em_industry_error) > 0
        else:
            # EM 成功
            assert status.industry_source == "akshare/eastmoney_industry"
            assert status.industry_count > 0

    @pytest.mark.network
    def test_concept_ths_fallback_on_em_failure(self):
        """测试概念板块 EM 失败时自动使用 THS fallback"""
        provider = AkShareProvider()
        sectors = provider.get_concept_sectors("2026-06-29", top_n=5)

        # 验证返回类型
        assert isinstance(sectors, list)

        # 获取 provider 状态
        status = provider.get_provider_status()

        # 如果 EM 失败，应该 fallback 到 THS
        if status.fallback_used:
            assert status.fallback_provider == "ths"
            assert "akshare/ths_concept" in status.concept_source
            assert status.concept_count > 0
            assert len(status.em_concept_error) > 0
        else:
            # EM 成功
            assert status.concept_source == "akshare/eastmoney_concept"
            assert status.concept_count > 0

    @pytest.mark.network
    def test_both_sectors_fallback(self):
        """测试行业和概念板块 fallback 场景（支持部分 fallback）"""
        provider = AkShareProvider()
        industries = provider.get_industry_sectors("2026-06-29", top_n=5)
        concepts = provider.get_concept_sectors("2026-06-29", top_n=5)

        status = provider.get_provider_status()

        # 验证状态
        assert isinstance(industries, list)
        assert isinstance(concepts, list)

        # 根据实际 source 判断 effective_provider
        ind_is_ths = "ths" in status.industry_source if status.industry_source else False
        con_is_ths = "ths" in status.concept_source if status.concept_source else False
        ind_is_em = "eastmoney" in status.industry_source if status.industry_source else False
        con_is_em = "eastmoney" in status.concept_source if status.concept_source else False

        if status.industry_source and status.concept_source:
            if ind_is_ths and con_is_ths:
                assert status.effective_provider == "ths"
            elif ind_is_em and con_is_em:
                assert status.effective_provider == "akshare"
            else:
                # 一个 THS 一个 EM → mixed
                assert status.effective_provider == "mixed"

    def test_prefer_ths_mode(self):
        """测试 prefer_ths 模式"""
        provider = AkShareProvider(prefer_ths=True)
        assert provider.prefer_ths is True

    @pytest.mark.network
    def test_get_provider_status_returns_info(self):
        """测试 get_provider_status 返回 ProviderStatusInfo"""
        provider = AkShareProvider()
        # 先调用一些方法以触发状态更新
        provider.get_industry_sectors("2026-06-29", top_n=3)
        provider.get_concept_sectors("2026-06-29", top_n=3)

        status = provider.get_provider_status()
        assert isinstance(status, ProviderStatusInfo)
        assert status.industry_count > 0 or status.concept_count > 0


class TestCallResult:
    """测试 CallResult 数据类"""

    def test_call_result_initialization(self):
        """测试 CallResult 初始化"""
        result = CallResult(status="ok")
        assert result.status == "ok"
        assert result.data is None
        assert result.warnings == []
        assert result.elapsed_ms == 0.0
        assert result.error_type == ""
        assert result.error_message == ""

    def test_call_result_with_data(self):
        """测试 CallResult 带数据"""
        data = {"key": "value"}
        result = CallResult(status="ok", data=data)
        assert result.status == "ok"
        assert result.data == data

    def test_call_result_with_error(self):
        """测试 CallResult 带错误信息"""
        result = CallResult(
            status="failed",
            error_type="ConnectionError",
            error_message="Remote end closed connection"
        )
        assert result.status == "failed"
        assert result.error_type == "ConnectionError"
        assert "Remote end closed" in result.error_message


class TestEffectiveProviderStateSemantics:
    """测试 effective_provider 状态判定语义（不依赖网络，直接模拟 _status_info）"""

    def test_both_ths_sources(self):
        """两个 source 都是 THS → effective_provider='ths'"""
        provider = AkShareProvider()
        provider._status_info.industry_source = "akshare/ths_industry"
        provider._status_info.concept_source = "akshare/ths_concept"
        provider._status_info.fallback_used = True

        status = provider.get_provider_status()
        assert status.effective_provider == "ths"

    def test_both_em_sources(self):
        """两个 source 都是 EM → effective_provider='akshare'"""
        provider = AkShareProvider()
        provider._status_info.industry_source = "akshare/eastmoney_industry"
        provider._status_info.concept_source = "akshare/eastmoney_concept"
        provider._status_info.fallback_used = False

        status = provider.get_provider_status()
        assert status.effective_provider == "akshare"

    def test_mixed_ths_industry_em_concept(self):
        """industry=THS + concept=EM → effective_provider='mixed'"""
        provider = AkShareProvider()
        provider._status_info.industry_source = "akshare/ths_industry"
        provider._status_info.concept_source = "akshare/eastmoney_concept"
        provider._status_info.fallback_used = True

        status = provider.get_provider_status()
        assert status.effective_provider == "mixed"

    def test_mixed_em_industry_ths_concept(self):
        """industry=EM + concept=THS → effective_provider='mixed'"""
        provider = AkShareProvider()
        provider._status_info.industry_source = "akshare/eastmoney_industry"
        provider._status_info.concept_source = "akshare/ths_concept"
        provider._status_info.fallback_used = True

        status = provider.get_provider_status()
        assert status.effective_provider == "mixed"

    def test_industry_ths_only(self):
        """只有 industry 且为 THS → effective_provider='ths'"""
        provider = AkShareProvider()
        provider._status_info.industry_source = "akshare/ths_industry"
        provider._status_info.concept_source = ""
        provider._status_info.fallback_used = True

        status = provider.get_provider_status()
        assert status.effective_provider == "ths"

    def test_concept_ths_only(self):
        """只有 concept 且为 THS → effective_provider='ths'"""
        provider = AkShareProvider()
        provider._status_info.industry_source = ""
        provider._status_info.concept_source = "akshare/ths_concept"
        provider._status_info.fallback_used = True

        status = provider.get_provider_status()
        assert status.effective_provider == "ths"

    def test_industry_em_only(self):
        """只有 industry 且为 EM → effective_provider='akshare'"""
        provider = AkShareProvider()
        provider._status_info.industry_source = "akshare/eastmoney_industry"
        provider._status_info.concept_source = ""
        provider._status_info.fallback_used = False

        status = provider.get_provider_status()
        assert status.effective_provider == "akshare"

    def test_concept_em_only(self):
        """只有 concept 且为 EM → effective_provider='akshare'"""
        provider = AkShareProvider()
        provider._status_info.industry_source = ""
        provider._status_info.concept_source = "akshare/eastmoney_concept"
        provider._status_info.fallback_used = False

        status = provider.get_provider_status()
        assert status.effective_provider == "akshare"

    def test_prefer_ths_both_em_sources(self):
        """prefer_ths=True 但两个都是 EM → effective_provider='akshare'（source 实际是 EM）"""
        provider = AkShareProvider(prefer_ths=True)
        provider._status_info.industry_source = "akshare/eastmoney_industry"
        provider._status_info.concept_source = "akshare/eastmoney_concept"
        provider._status_info.fallback_used = False

        status = provider.get_provider_status()
        assert status.effective_provider == "akshare"

    def test_no_sources_no_fallback(self):
        """无 source、无 fallback → effective_provider='akshare'"""
        provider = AkShareProvider()
        status = provider.get_provider_status()
        assert status.effective_provider == "akshare"
