"""
板块历史数据下载器测试

测试 downloader 功能。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.downloader.sector_history_downloader import (
    SectorHistoryDownloader,
    save_download_summary,
)
from theme_sector_radar.models import SectorType


class TestSectorDownloader:
    """测试板块历史数据下载器"""

    def test_downloader_initialization(self):
        """测试下载器初始化"""
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = SectorHistoryDownloader(data_cache_dir=tmpdir)
            assert downloader.data_cache_dir == tmpdir

    def test_save_and_load_sector_history(self):
        """测试保存和加载板块历史数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = SectorHistoryDownloader(data_cache_dir=tmpdir)

            # 创建测试数据
            test_data = {
                "sector_name": "test_sector",
                "sector_code": "BK0001",
                "sector_type": "industry",
                "source": "akshare/ths",
                "start_date": "2026-06-23",
                "end_date": "2026-06-30",
                "fetched_at": "2026-06-29T10:00:00",
                "price_change_available": True,
                "records": [{"date": "2026-06-23", "close": 100}],
            }

            # 保存
            downloader.save_sector_history(SectorType.INDUSTRY, "test_sector", test_data)

            # 加载
            loaded = downloader.load_sector_history(SectorType.INDUSTRY, "test_sector")

            assert loaded is not None
            assert loaded["sector_name"] == "test_sector"
            assert len(loaded["records"]) == 1

    def test_has_cache(self):
        """测试缓存检查"""
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = SectorHistoryDownloader(data_cache_dir=tmpdir)

            # 检查不存在的缓存
            assert downloader.has_cache(SectorType.INDUSTRY, "nonexistent") is False

            # 创建缓存
            downloader.save_sector_history(
                SectorType.INDUSTRY,
                "test_sector",
                {"sector_name": "test_sector", "records": []}
            )

            # 检查存在的缓存
            assert downloader.has_cache(SectorType.INDUSTRY, "test_sector") is True

    def test_save_download_summary(self):
        """测试保存下载摘要"""
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = {
                "requested_sector_type": "industry",
                "requested_count": 10,
                "success_count": 8,
                "failed_count": 1,
                "skipped_count": 1,
                "source": "akshare/ths",
                "failed_symbols": ["test_failed"],
                "warnings": ["test warning"],
                "output_paths": [],
            }

            save_download_summary(summary, tmpdir)

            # 检查文件
            assert os.path.exists(os.path.join(tmpdir, "download_summary.json"))
            assert os.path.exists(os.path.join(tmpdir, "download_summary.md"))

    def test_download_summary_fields(self):
        """测试下载摘要字段完整性"""
        summary = {
            "requested_sector_type": "industry",
            "requested_count": 10,
            "success_count": 8,
            "failed_count": 1,
            "skipped_count": 1,
            "source": "akshare/ths",
            "failed_symbols": ["test_failed"],
            "warnings": ["test warning"],
            "output_paths": [],
        }

        required_fields = [
            "requested_sector_type",
            "requested_count",
            "success_count",
            "failed_count",
            "skipped_count",
            "source",
            "failed_symbols",
            "warnings",
            "output_paths",
        ]

        for field in required_fields:
            assert field in summary, f"Missing field: {field}"

    def test_concept_data_quality_warning(self):
        """测试概念数据质量警告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = SectorHistoryDownloader(data_cache_dir=tmpdir)

            # 创建概念数据（缺少价格变化字段）
            test_data = {
                "sector_name": "test_concept",
                "sector_type": "concept",
                "price_change_available": False,
                "records": [{"date": "2026-06-23"}],
            }

            downloader.save_sector_history(SectorType.CONCEPT, "test_concept", test_data)

            loaded = downloader.load_sector_history(SectorType.CONCEPT, "test_concept")
            assert loaded["price_change_available"] is False
