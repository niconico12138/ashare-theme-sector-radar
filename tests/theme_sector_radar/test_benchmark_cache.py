"""
市场基准 Cache 测试

测试 benchmark_cache.py 模块的各项功能。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.data.benchmark_cache import BenchmarkCache
from theme_sector_radar.data.benchmark_provider import BenchmarkData, BenchmarkRecord


class TestBenchmarkCache:
    """测试市场基准 Cache"""

    def test_has_cache(self):
        """测试检查缓存是否存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = BenchmarkCache(tmpdir)

            # 创建缓存文件
            cache_dir = os.path.join(tmpdir, "hs300")
            os.makedirs(cache_dir)
            cache_file = os.path.join(cache_dir, "20260616_to_20260630.json")
            with open(cache_file, "w") as f:
                json.dump({"benchmark_id": "hs300"}, f)

            # 测试
            assert cache.has_cache("hs300", "2026-06-16", "2026-06-30") is True
            assert cache.has_cache("hs300", "2026-07-01", "2026-07-10") is False

    def test_set_and_get_cache(self):
        """测试设置和获取缓存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = BenchmarkCache(tmpdir)

            # 创建基准数据
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
                ],
            )

            # 保存缓存
            cache.set_cache(benchmark_data)

            # 获取缓存
            loaded = cache.get_cache("hs300", "2026-06-16", "2026-06-30")
            assert loaded is not None
            assert loaded.benchmark_id == "hs300"
            assert loaded.status == "ok"
            assert len(loaded.records) == 2
            assert loaded.records[0].date == "2026-06-16"
            assert loaded.records[1].pct_change == 2.0

    def test_get_cache_nonexistent(self):
        """测试获取不存在的缓存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = BenchmarkCache(tmpdir)
            loaded = cache.get_cache("hs300", "2026-06-16", "2026-06-30")
            assert loaded is None

    def test_delete_cache(self):
        """测试删除缓存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = BenchmarkCache(tmpdir)

            # 创建缓存
            benchmark_data = BenchmarkData(
                benchmark_id="hs300",
                benchmark_name="沪深300",
                source="test",
                start_date="2026-06-16",
                end_date="2026-06-30",
                fetched_at="2026-06-30T10:00:00",
                status="ok",
            )
            cache.set_cache(benchmark_data)
            assert cache.has_cache("hs300", "2026-06-16", "2026-06-30") is True

            # 删除缓存
            cache.delete_cache("hs300", "2026-06-16", "2026-06-30")
            assert cache.has_cache("hs300", "2026-06-16", "2026-06-30") is False

    def test_list_cached_benchmarks(self):
        """测试列出已缓存的基准"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = BenchmarkCache(tmpdir)

            # 创建多个缓存
            for benchmark_id in ["hs300", "zz500"]:
                benchmark_data = BenchmarkData(
                    benchmark_id=benchmark_id,
                    benchmark_name="test",
                    source="test",
                    start_date="2026-06-16",
                    end_date="2026-06-30",
                    fetched_at="2026-06-30T10:00:00",
                    status="ok",
                )
                cache.set_cache(benchmark_data)

            # 列出缓存
            cached = cache.list_cached_benchmarks()
            assert len(cached) == 2
            benchmark_ids = [c["benchmark_id"] for c in cached]
            assert "hs300" in benchmark_ids
            assert "zz500" in benchmark_ids
