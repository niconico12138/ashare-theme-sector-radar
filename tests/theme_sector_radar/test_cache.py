"""
缓存测试

测试数据缓存功能。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.data.cache import DataCache


class TestDataCache:
    """测试数据缓存"""

    def test_cache_set_and_get(self):
        """测试缓存写入和读取"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DataCache(cache_dir=tmpdir)

            test_data = {"key": "value", "number": 123}
            cache.set("test_key", test_data, as_of_date="2026-06-28")

            retrieved = cache.get("test_key", as_of_date="2026-06-28")

            assert retrieved is not None
            assert "data" in retrieved
            assert retrieved["data"]["key"] == "value"
            assert retrieved["data"]["number"] == 123

    def test_cache_metadata(self):
        """测试缓存元数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DataCache(cache_dir=tmpdir)

            test_data = {"key": "value"}
            metadata = {
                "provider": "akshare",
                "created_at": "2026-06-28T10:00:00",
                "as_of_date": "2026-06-28",
                "data_sources": ["akshare/eastmoney"],
            }

            cache.set("test_key", test_data, as_of_date="2026-06-28", metadata=metadata)

            retrieved = cache.get("test_key", as_of_date="2026-06-28")

            assert retrieved["metadata"]["provider"] == "akshare"
            assert retrieved["metadata"]["as_of_date"] == "2026-06-28"

    def test_cache_has(self):
        """测试缓存存在检查"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DataCache(cache_dir=tmpdir)

            assert cache.has("test_key", as_of_date="2026-06-28") is False

            cache.set("test_key", {"data": "value"}, as_of_date="2026-06-28")

            assert cache.has("test_key", as_of_date="2026-06-28") is True

    def test_cache_delete(self):
        """测试缓存删除"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DataCache(cache_dir=tmpdir)

            cache.set("test_key", {"data": "value"}, as_of_date="2026-06-28")
            assert cache.has("test_key", as_of_date="2026-06-28") is True

            cache.delete("test_key", as_of_date="2026-06-28")
            assert cache.has("test_key", as_of_date="2026-06-28") is False

    def test_cache_different_dates(self):
        """测试不同日期的缓存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DataCache(cache_dir=tmpdir)

            cache.set("test_key", {"date": "2026-06-28"}, as_of_date="2026-06-28")
            cache.set("test_key", {"date": "2026-06-29"}, as_of_date="2026-06-29")

            retrieved_28 = cache.get("test_key", as_of_date="2026-06-28")
            retrieved_29 = cache.get("test_key", as_of_date="2026-06-29")

            assert retrieved_28["data"]["date"] == "2026-06-28"
            assert retrieved_29["data"]["date"] == "2026-06-29"

    def test_cache_nonexistent(self):
        """测试读取不存在的缓存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DataCache(cache_dir=tmpdir)

            retrieved = cache.get("nonexistent", as_of_date="2026-06-28")
            assert retrieved is None

    def test_cache_info(self):
        """测试缓存信息"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = DataCache(cache_dir=tmpdir)

            cache.set("key1", {"data": "value1"}, as_of_date="2026-06-28")
            cache.set("key2", {"data": "value2"}, as_of_date="2026-06-28")

            info = cache.get_cache_info(as_of_date="2026-06-28")

            assert info["as_of_date"] == "2026-06-28"
            assert len(info["files"]) == 2
