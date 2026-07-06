"""
板块评分 Benchmark 测试

测试 benchmark 与 sector scoring 的集成。
"""

import pytest

from theme_sector_radar.scoring.sector_composite_score import (
    calculate_sector_composite_score,
    calculate_relative_strength_component,
)
from theme_sector_radar.data.benchmark_provider import BenchmarkData, BenchmarkRecord


class TestBenchmarkIntegration:
    """测试 Benchmark 集成"""

    def test_benchmark_mode_market_benchmark(self):
        """测试 benchmark 数据可用时使用 market_benchmark"""
        benchmark_return = 2.0

        score, mode, benchmark_id, benchmark_name = calculate_relative_strength_component(
            sector_return=5.0,
            benchmark_return=benchmark_return,
            benchmark_id="hs300",
            benchmark_name="沪深300",
        )

        assert mode == "market_benchmark"
        assert benchmark_id == "hs300"
        assert benchmark_name == "沪深300"
        assert score > 0  # 超额收益为正

    def test_benchmark_mode_sector_median_fallback(self):
        """测试无基准时使用 sector_median fallback"""
        score, mode, benchmark_id, benchmark_name = calculate_relative_strength_component(
            sector_return=5.0,
            benchmark_return=0.0,  # 无基准收益率
            all_sector_returns=[1.0, 2.0, 3.0, 4.0, 5.0],
        )

        assert mode == "sector_median"
        assert benchmark_id is None
        assert benchmark_name is None

    def test_relative_return_calculation(self):
        """测试相对收益率计算"""
        # 板块收益率 5%，基准收益率 2%，超额收益 3%
        score, mode, _, _ = calculate_relative_strength_component(
            sector_return=5.0,
            benchmark_return=2.0,
            benchmark_id="hs300",
            benchmark_name="沪深300",
        )

        # 超额收益 3% 应该得到较高分数
        assert score >= 10.0  # 15 * 0.7 = 10.5

    def test_composite_score_with_benchmark(self):
        """测试使用基准的综合评分"""
        result = calculate_sector_composite_score(
            radar_score=70.0,
            recent_returns=[2.0, 1.5, 1.0, 0.5, 0.3],
            sector_return=5.3,
            benchmark_return=2.0,
            all_sector_returns=[1.0, 2.0, 3.0, 4.0, 5.0],
            positive_days_count=4,
            total_days=5,
            max_drawdown=-0.02,
            volatility=1.5,
            data_quality_score=80.0,
            history_days=5,
            price_change_available=True,
            benchmark_id="hs300",
            benchmark_name="沪深300",
        )

        assert result["benchmark_mode"] == "market_benchmark"
        assert result["benchmark_id"] == "hs300"
        assert result["benchmark_name"] == "沪深300"
        assert 0 <= result["sector_selection_score"] <= 100

    def test_composite_score_without_benchmark(self):
        """测试不使用基准的综合评分"""
        result = calculate_sector_composite_score(
            radar_score=70.0,
            recent_returns=[2.0, 1.5, 1.0, 0.5, 0.3],
            sector_return=5.3,
            benchmark_return=0.0,
            all_sector_returns=[1.0, 2.0, 3.0, 4.0, 5.0],
            positive_days_count=4,
            total_days=5,
            max_drawdown=-0.02,
            volatility=1.5,
            data_quality_score=80.0,
            history_days=5,
            price_change_available=True,
        )

        assert result["benchmark_mode"] == "sector_median"
        assert result["benchmark_id"] is None
        assert result["benchmark_name"] is None


class TestBenchmarkDataProvider:
    """测试 BenchmarkProvider"""

    @pytest.mark.network
    def test_fetch_hs300_data(self):
        """测试获取沪深300数据（需要网络）"""
        from theme_sector_radar.data.benchmark_provider import BenchmarkProvider

        provider = BenchmarkProvider()
        data = provider.fetch_benchmark_data("hs300", "2026-06-16", "2026-06-30")

        # 如果网络可用，应该能获取数据
        if data.status == "ok":
            assert len(data.records) > 0
            assert data.benchmark_id == "hs300"
            assert data.benchmark_name == "沪深300"

    def test_fetch_invalid_benchmark(self):
        """测试获取不存在的基准"""
        from theme_sector_radar.data.benchmark_provider import BenchmarkProvider

        provider = BenchmarkProvider()
        data = provider.fetch_benchmark_data("invalid", "2026-06-16", "2026-06-30")

        assert data.status == "failed"
        assert len(data.warnings) > 0
