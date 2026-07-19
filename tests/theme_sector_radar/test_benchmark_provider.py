"""
市场基准 Provider 测试

测试 benchmark_provider.py 模块的各项功能。
"""

import pytest

from theme_sector_radar.data.benchmark_provider import BenchmarkProvider, BenchmarkData, BenchmarkRecord


class TestBenchmarkProvider:
    """测试市场基准 Provider"""

    def test_get_supported_benchmarks(self):
        """测试获取支持的基准列表"""
        provider = BenchmarkProvider()
        benchmarks = provider.get_supported_benchmarks()
        assert "hs300" in benchmarks
        assert "zz500" in benchmarks
        assert "zz1000" in benchmarks

    def test_get_benchmark_config(self):
        """测试获取基准配置"""
        provider = BenchmarkProvider()

        config = provider.get_benchmark_config("hs300")
        assert config is not None
        assert config["id"] == "hs300"
        assert config["name"] == "沪深300"
        assert config["symbol"] == "sh000300"

    def test_get_benchmark_config_invalid(self):
        """测试获取不存在的基准配置"""
        provider = BenchmarkProvider()
        config = provider.get_benchmark_config("invalid")
        assert config is None

    def test_calculate_benchmark_returns(self):
        """测试计算基准收益率"""
        provider = BenchmarkProvider()

        # 创建模拟基准数据
        benchmark_data = BenchmarkData(
            benchmark_id="hs300",
            benchmark_name="沪深300",
            source="test",
            start_date="2026-06-16",
            end_date="2026-06-30",
            fetched_at="2026-06-30T10:00:00",
            status="ok",
            records=[
                BenchmarkRecord(date="2026-06-16", close=100.0, pct_change=0.0),
                BenchmarkRecord(date="2026-06-17", close=102.0, pct_change=2.0),
                BenchmarkRecord(date="2026-06-18", close=101.0, pct_change=-0.98),
                BenchmarkRecord(date="2026-06-19", close=103.0, pct_change=1.98),
                BenchmarkRecord(date="2026-06-20", close=105.0, pct_change=1.94),
            ],
        )

        returns = provider.calculate_benchmark_returns(benchmark_data)

        assert "1d" in returns
        assert "3d" in returns
        assert "5d" not in returns
        assert returns["1d"] == pytest.approx(105.0 / 103.0 * 100.0 - 100.0, abs=1e-4)
        assert returns["3d"] == pytest.approx(105.0 / 102.0 * 100.0 - 100.0, abs=1e-4)

    def test_benchmark_horizons_require_n_plus_one_closes_and_compound(self):
        provider = BenchmarkProvider()
        closes = [100.0 * (1.01 ** day) for day in range(21)]
        benchmark_data = BenchmarkData(
            benchmark_id="hs300",
            benchmark_name="沪深300",
            source="test",
            start_date="2026-01-01",
            end_date="2026-01-21",
            fetched_at="2026-01-21T00:00:00",
            status="ok",
            records=[
                BenchmarkRecord(
                    date=f"2026-01-{day + 1:02d}",
                    close=close,
                    pct_change=0.0 if day == 0 else 1.0,
                )
                for day, close in enumerate(closes)
            ],
        )

        returns = provider.calculate_benchmark_returns(benchmark_data)

        assert returns["10d"] == pytest.approx((1.01 ** 10 - 1.0) * 100.0, abs=1e-4)
        assert returns["20d"] == pytest.approx((1.01 ** 20 - 1.0) * 100.0, abs=1e-4)


class TestBenchmarkData:
    """测试 BenchmarkData 数据类"""

    def test_benchmark_data_creation(self):
        """测试 BenchmarkData 创建"""
        data = BenchmarkData(
            benchmark_id="hs300",
            benchmark_name="沪深300",
            source="test",
            start_date="2026-06-16",
            end_date="2026-06-30",
            fetched_at="2026-06-30T10:00:00",
            status="ok",
        )
        assert data.benchmark_id == "hs300"
        assert data.status == "ok"
        assert len(data.records) == 0

    def test_benchmark_record_creation(self):
        """测试 BenchmarkRecord 创建"""
        record = BenchmarkRecord(
            date="2026-06-16",
            close=100.0,
            pct_change=1.5,
        )
        assert record.date == "2026-06-16"
        assert record.close == 100.0
        assert record.pct_change == 1.5
