"""
AkShare 重试策略测试

测试重试、超时和异常处理。
"""

import pytest

from theme_sector_radar.data.akshare_provider import AkShareProvider, CallResult


class TestAkShareRetry:
    """测试 AkShare 重试策略"""

    def test_call_result_structure(self):
        """测试 CallResult 结构"""
        result = CallResult(status="ok", data=[1, 2, 3], warnings=[], elapsed_ms=100.0)
        assert result.status == "ok"
        assert result.data == [1, 2, 3]
        assert result.warnings == []
        assert result.elapsed_ms == 100.0

    def test_call_result_default_warnings(self):
        """测试 CallResult 默认 warnings"""
        result = CallResult(status="ok")
        assert result.warnings is not None
        assert len(result.warnings) == 0

    def test_provider_initialization(self):
        """测试 Provider 初始化"""
        provider = AkShareProvider(retries=5, retry_delay=2.0)
        assert provider.retries == 5
        assert provider.retry_delay == 2.0

    def test_provider_default_retries(self):
        """测试 Provider 默认重试次数"""
        provider = AkShareProvider()
        assert provider.retries == 3
        assert provider.retry_delay == 1.0

    @pytest.mark.network
    def test_safe_call_returns_result(self):
        """测试 safe_call 返回 CallResult"""
        provider = AkShareProvider()

        # 测试一个简单的函数
        def test_func():
            return [1, 2, 3]

        result = provider._safe_call(test_func)
        assert isinstance(result, CallResult)
        assert result.status == "ok"
        assert result.data == [1, 2, 3]

    @pytest.mark.network
    def test_safe_call_handles_exception(self):
        """测试 safe_call 处理异常"""
        provider = AkShareProvider(retries=1)

        def failing_func():
            raise ValueError("Test error")

        result = provider._safe_call(failing_func)
        assert result.status == "failed"
        assert len(result.warnings) > 0
        assert "ValueError" in result.warnings[0]

    @pytest.mark.network
    def test_safe_call_handles_none_return(self):
        """测试 safe_call 处理 None 返回"""
        provider = AkShareProvider(retries=1)

        def none_func():
            return None

        result = provider._safe_call(none_func)
        # None 不是有效数据，应该重试后失败
        assert result.status == "failed"

    @pytest.mark.network
    def test_safe_call_handles_empty_dataframe(self):
        """测试 safe_call 处理空 DataFrame"""
        import pandas as pd
        provider = AkShareProvider(retries=1)

        def empty_df_func():
            return pd.DataFrame()

        result = provider._safe_call(empty_df_func)
        # 空 DataFrame 不是有效数据，应该重试后失败
        assert result.status == "failed"

    def test_cli_does_not_crash_on_network_error(self):
        """测试 CLI 不会因网络错误崩溃"""
        from theme_sector_radar.pipeline import run_pipeline

        # 使用离线 fixture 确保不会崩溃
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            provider_name="fixture",
        )
        assert report is not None
        assert report.status in ["ok", "degraded"]
