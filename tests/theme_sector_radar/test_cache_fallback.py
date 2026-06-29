"""
缓存 Fallback 测试

测试缓存回退策略。
"""

import tempfile

import pytest

from theme_sector_radar.data.cache import DataCache


class TestCacheFallback:
    """测试缓存 Fallback"""

    def test_find_fallback_cache_returns_none_when_no_cache(self):
        """测试没有缓存时返回 None"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DataCache(cache_dir=tmpdir)
            result = cache.find_fallback_cache(
                "raw_snapshot", "2026-06-28", max_days=7
            )
            assert result is None

    def test_find_fallback_cache_finds_recent_cache(self):
        """测试找到最近缓存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DataCache(cache_dir=tmpdir)

            # 创建一个 3 天前的缓存
            cache.set(
                "raw_snapshot",
                {
                    "industry_sectors": [{"id": i} for i in range(25)],
                    "concept_sectors": [{"id": i} for i in range(20)],
                },
                as_of_date="2026-06-25",
                metadata={"provider": "akshare", "created_at": "2026-06-25T10:00:00"}
            )

            # 尝试查找 2026-06-28 的 fallback
            result = cache.find_fallback_cache(
                "raw_snapshot", "2026-06-28", max_days=7, min_data_count=20
            )

            assert result is not None
            assert result["metadata"]["is_fallback"] is True
            assert result["metadata"]["source_as_of_date"] == "2026-06-25"

    def test_find_fallback_cache_skips_insufficient_data(self):
        """测试跳过数据不足的缓存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DataCache(cache_dir=tmpdir)

            # 创建一个数据不足的缓存
            cache.set(
                "raw_snapshot",
                {
                    "industry_sectors": [{"id": i} for i in range(5)],  # 只有 5 个
                    "concept_sectors": [{"id": i} for i in range(5)],
                },
                as_of_date="2026-06-25",
                metadata={"provider": "akshare"}
            )

            # 尝试查找，要求至少 20 个
            result = cache.find_fallback_cache(
                "raw_snapshot", "2026-06-28", max_days=7, min_data_count=20
            )

            assert result is None

    def test_find_fallback_cache_respects_max_days(self):
        """测试遵守最大回退天数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DataCache(cache_dir=tmpdir)

            # 创建一个 10 天前的缓存
            cache.set(
                "raw_snapshot",
                {
                    "industry_sectors": [{"id": i} for i in range(25)],
                    "concept_sectors": [{"id": i} for i in range(20)],
                },
                as_of_date="2026-06-18",
                metadata={"provider": "akshare"}
            )

            # 尝试查找，最多回退 7 天
            result = cache.find_fallback_cache(
                "raw_snapshot", "2026-06-28", max_days=7, min_data_count=20
            )

            # 10 天前的缓存应该找不到
            assert result is None

    def test_list_dates(self):
        """测试列出缓存日期"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DataCache(cache_dir=tmpdir)

            # 创建几个日期的缓存
            cache.set("test", {"data": 1}, as_of_date="2026-06-25")
            cache.set("test", {"data": 2}, as_of_date="2026-06-26")
            cache.set("test", {"data": 3}, as_of_date="2026-06-27")

            dates = cache.list_dates()
            assert len(dates) == 3
            assert "2026-06-27" in dates
            assert "2026-06-26" in dates
            assert "2026-06-25" in dates

    def test_cache_metadata_preserved(self):
        """测试缓存元数据保留"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DataCache(cache_dir=tmpdir)

            metadata = {
                "provider": "akshare",
                "created_at": "2026-06-28T10:00:00",
                "as_of_date": "2026-06-28",
                "data_sources": ["akshare/eastmoney"],
            }

            cache.set("test", {"data": 1}, as_of_date="2026-06-28", metadata=metadata)

            result = cache.get("test", as_of_date="2026-06-28")
            assert result["metadata"]["provider"] == "akshare"
            assert result["metadata"]["as_of_date"] == "2026-06-28"
