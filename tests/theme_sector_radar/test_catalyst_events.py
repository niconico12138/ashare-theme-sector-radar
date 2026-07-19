"""
催化事件测试

测试 CatalystEvent 模型、缓存、映射和下载器。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.data.catalyst_events.models import CatalystEvent, EVENT_TYPE_NEWS
from theme_sector_radar.data.catalyst_events.cache import CatalystEventCache
from theme_sector_radar.data.catalyst_events.mapper import SymbolSectorMapper
from theme_sector_radar.data.catalyst_events.downloader import CatalystEventDownloader


class TestCatalystEventModel:
    """测试 CatalystEvent 模型"""

    def test_creation(self):
        """测试创建"""
        event = CatalystEvent(
            event_id="test_001",
            event_date="2026-06-29",
            source="test",
            title="Test Event",
        )
        assert event.event_id == "test_001"
        assert event.event_date == "2026-06-29"

    def test_serialization(self):
        """测试序列化/反序列化"""
        event = CatalystEvent(
            event_id="test_001",
            event_date="2026-06-29",
            source="test",
            title="Test Event",
            related_symbols=["600519"],
            related_industries=["白酒"],
        )

        data = event.to_dict()
        restored = CatalystEvent.from_dict(data)

        assert restored.event_id == event.event_id
        assert restored.related_symbols == event.related_symbols
        assert restored.related_industries == event.related_industries

    def test_hash_stability(self):
        """测试哈希稳定性"""
        payload = {"key": "value", "number": 123}
        hash1 = CatalystEvent.compute_hash(payload)
        hash2 = CatalystEvent.compute_hash(payload)
        assert hash1 == hash2

    def test_hash_different_for_different_payload(self):
        """测试不同数据产生不同哈希"""
        hash1 = CatalystEvent.compute_hash({"key": "value1"})
        hash2 = CatalystEvent.compute_hash({"key": "value2"})
        assert hash1 != hash2


class TestCatalystEventCache:
    """测试 CatalystEventCache"""

    def test_save_and_load(self):
        """测试保存和加载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CatalystEventCache(cache_root=tmpdir)

            events = [
                CatalystEvent(event_id="test_001", event_date="2026-06-29", source="test"),
                CatalystEvent(event_id="test_002", event_date="2026-06-29", source="test"),
            ]
            source_status = [{"source_id": "test", "status": "ok"}]

            cache_dir = cache.save_events("2026-06-29", events, source_status)
            assert os.path.exists(cache_dir)

            loaded = cache.load_events("2026-06-29")
            assert loaded is not None
            assert len(loaded) == 2

    def test_deduplicate(self):
        """测试去重"""
        cache = CatalystEventCache()

        events = [
            CatalystEvent(event_id="test_001", event_date="2026-06-29", source="test",
                         raw_payload_hash="hash1"),
            CatalystEvent(event_id="test_002", event_date="2026-06-29", source="test",
                         raw_payload_hash="hash1"),  # 重复
            CatalystEvent(event_id="test_003", event_date="2026-06-29", source="test",
                         raw_payload_hash="hash2"),
        ]

        unique = cache.deduplicate_events(events)
        assert len(unique) == 2

    def test_source_status(self):
        """测试 source_status 读写"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CatalystEventCache(cache_root=tmpdir)

            events = [CatalystEvent(event_id="test_001", event_date="2026-06-29", source="test")]
            source_status = [{"source_id": "test", "status": "ok"}]

            cache.save_events("2026-06-29", events, source_status)

            loaded_status = cache.load_source_status("2026-06-29")
            assert loaded_status is not None
            assert loaded_status["sources"][0]["status"] == "ok"


class TestSymbolSectorMapper:
    """测试 SymbolSectorMapper"""

    def test_map_symbol_to_sectors(self):
        """测试 symbol -> sector 映射"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 sector_history
            history_dir = os.path.join(tmpdir, "industry")
            os.makedirs(history_dir)
            with open(os.path.join(history_dir, "白酒.json"), "w") as f:
                json.dump({"records": []}, f)

            mapper = SymbolSectorMapper(history_root=tmpdir)
            result = mapper.map_symbol_to_sectors("600519", "贵州茅台白酒")

            assert "白酒" in result["industries"]

    def test_unmapped_not_fail(self):
        """测试 unmapped 不失败"""
        mapper = SymbolSectorMapper()
        result = mapper.map_symbol_to_sectors("999999", "未知公司")

        assert result["industries"] == []
        assert result["concepts"] == []


class TestCatalystEventDownloader:
    """测试 CatalystEventDownloader"""

    def test_offline_fixture(self):
        """测试 offline_fixture 下载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 sector_history
            history_dir = os.path.join(tmpdir, "industry")
            os.makedirs(history_dir)
            with open(os.path.join(history_dir, "白酒.json"), "w") as f:
                json.dump({"records": []}, f)

            downloader = CatalystEventDownloader(
                cache_root=os.path.join(tmpdir, "cache"),
                history_root=tmpdir,
            )

            fixture_data = [
                {
                    "event_id": "fixture_001",
                    "event_date": "2026-06-29",
                    "source": "fixture",
                    "title": "Test",
                    "event_type": "stock_news",
                    "related_symbols": ["600519"],
                    "related_symbol_names": ["贵州茅台"],
                    "related_industries": ["白酒"],
                    "related_concepts": [],
                    "confidence": 0.8,
                    "freshness": "same_day",
                    "raw_payload_hash": "hash1",
                    "raw_payload": {},
                },
            ]

            result = downloader.download(
                as_of_date="2026-06-29",
                symbols=["600519"],
                offline_fixture=True,
                fixture_data=fixture_data,
            )

            assert result["total_events"] == 1
            assert result["mode"] == "fixture"

    def test_network_false_no_network(self):
        """测试 network=False 不访问网络"""
        with tempfile.TemporaryDirectory() as tmpdir:
            downloader = CatalystEventDownloader(
                cache_root=os.path.join(tmpdir, "cache"),
                history_root=tmpdir,
            )

            result = downloader.download(
                as_of_date="2026-06-29",
                symbols=["600519"],
                network=False,
            )

            assert result["total_events"] == 0
            assert result["source_status"][0]["status"] == "skipped"


class TestCLI:
    """测试 CLI"""

    def test_download_fixture(self):
        """测试 CLI fixture 下载"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "output")

            import sys
            sys.argv = [
                "cli",
                "--download-catalyst-events",
                "--as-of", "2026-06-29",
                "--offline-fixture",
                "--symbols", "600519,300750",
                "--output", output_dir,
                "--cache-root", os.path.join(tmpdir, "cache"),
                "--history-root", os.path.join(tmpdir, "history"),
                "--refresh",
            ]

            from theme_sector_radar.cli import main
            main()

            assert os.path.exists(os.path.join(output_dir, "catalyst_historical_collection_summary.json"))
            assert os.path.exists(os.path.join(output_dir, "catalyst_historical_collection_summary.md"))
            assert os.path.exists(
                os.path.join(tmpdir, "cache", "catalyst_events", "2026-06-29", "events.json")
            )
