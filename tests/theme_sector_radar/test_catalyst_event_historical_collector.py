"""
历史催化事件采集器测试

测试 historical_collector.py 模块。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.data.catalyst_events.historical_collector import (
    HistoricalCatalystCollector,
    save_historical_collection_summary,
    generate_historical_collection_summary_md,
)


class TestHistoricalCatalystCollector:
    """测试 HistoricalCatalystCollector"""

    def _create_mock_data(self, tmpdir: str):
        """创建模拟数据"""
        # 创建 sector_research
        for date in ["2026-06-01", "2026-06-02", "2026-06-03"]:
            report_dir = os.path.join(tmpdir, "sector_research", date)
            os.makedirs(report_dir)

            data = {
                "as_of_date": date,
                "daily_summary": {
                    "top_watch_names": ["白酒", "电池"],
                },
                "research_results": [
                    {"sector_name": "白酒", "ranking_score": 0.5},
                    {"sector_name": "电池", "ranking_score": 0.4},
                ],
            }
            with open(os.path.join(report_dir, "sector_research.json"), "w") as f:
                json.dump(data, f)

    def test_collect_basic(self):
        """测试基本采集"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            # 加载 fixture 数据
            fixture_path = os.path.join("tests", "fixtures", "catalyst_events", "sample_stock_news.json")
            fixture_data = []
            if os.path.exists(fixture_path):
                with open(fixture_path, "r", encoding="utf-8") as f:
                    fixture_data = json.load(f)

            collector = HistoricalCatalystCollector(
                history_root=os.path.join(tmpdir, "sector_history"),
                catalyst_root=os.path.join(tmpdir, "catalyst_events"),
            )

            result = collector.collect(
                start_date="2026-06-01",
                end_date="2026-06-03",
                report_root=tmpdir,
                offline_fixture=True,
                auto_symbols=True,
                top_sectors=2,
                max_symbols_total=5,
                fixture_data=fixture_data,
            )

            assert len(result["generated_dates"]) == 3
            assert result["total_events"] > 0

    def test_skip_existing(self):
        """测试 skip-existing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            # 预先创建缓存
            cache_dir = os.path.join(tmpdir, "catalyst_events", "2026-06-01")
            os.makedirs(cache_dir)
            with open(os.path.join(cache_dir, "events.json"), "w") as f:
                json.dump({"events": []}, f)

            collector = HistoricalCatalystCollector(
                history_root=os.path.join(tmpdir, "sector_history"),
                catalyst_root=os.path.join(tmpdir, "catalyst_events"),
            )

            result = collector.collect(
                start_date="2026-06-01",
                end_date="2026-06-03",
                report_root=tmpdir,
                offline_fixture=True,
                auto_symbols=True,
                top_sectors=2,
                max_symbols_total=5,
                refresh=False,
            )

            assert "2026-06-01" in result["skipped_dates"]
            assert len(result["generated_dates"]) == 2

    def test_refresh_overwrites(self):
        """测试 refresh 覆盖旧缓存"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            # 预先创建缓存
            cache_dir = os.path.join(tmpdir, "catalyst_events", "2026-06-01")
            os.makedirs(cache_dir)
            with open(os.path.join(cache_dir, "events.json"), "w") as f:
                json.dump({"events": []}, f)

            collector = HistoricalCatalystCollector(
                history_root=os.path.join(tmpdir, "sector_history"),
                catalyst_root=os.path.join(tmpdir, "catalyst_events"),
            )

            result = collector.collect(
                start_date="2026-06-01",
                end_date="2026-06-03",
                report_root=tmpdir,
                offline_fixture=True,
                auto_symbols=True,
                top_sectors=2,
                max_symbols_total=5,
                refresh=True,
            )

            assert "2026-06-01" not in result["skipped_dates"]
            assert len(result["generated_dates"]) == 3

    def test_no_symbols_skipped(self):
        """测试无 symbols 时跳过"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 不创建 sector_research
            collector = HistoricalCatalystCollector(
                history_root=os.path.join(tmpdir, "sector_history"),
                catalyst_root=os.path.join(tmpdir, "catalyst_events"),
            )

            result = collector.collect(
                start_date="2026-06-01",
                end_date="2026-06-01",
                report_root=tmpdir,
                offline_fixture=False,
                auto_symbols=False,
            )

            assert len(result["skipped_dates"]) == 1
            assert result["total_events"] == 0

    def test_summary_fields(self):
        """测试 summary 字段完整"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            collector = HistoricalCatalystCollector(
                history_root=os.path.join(tmpdir, "sector_history"),
                catalyst_root=os.path.join(tmpdir, "catalyst_events"),
            )

            result = collector.collect(
                start_date="2026-06-01",
                end_date="2026-06-03",
                report_root=tmpdir,
                offline_fixture=True,
                auto_symbols=True,
                top_sectors=2,
                max_symbols_total=5,
            )

            assert "start_date" in result
            assert "end_date" in result
            assert "generated_dates" in result
            assert "total_events" in result
            assert "missing_cache_dates" in result

    def test_save_summary(self):
        """测试保存 summary"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            collector = HistoricalCatalystCollector(
                history_root=os.path.join(tmpdir, "sector_history"),
                catalyst_root=os.path.join(tmpdir, "catalyst_events"),
            )

            result = collector.collect(
                start_date="2026-06-01",
                end_date="2026-06-03",
                report_root=tmpdir,
                offline_fixture=True,
                auto_symbols=True,
                top_sectors=2,
                max_symbols_total=5,
            )

            output_dir = os.path.join(tmpdir, "output")
            save_historical_collection_summary(output_dir, result)

            assert os.path.exists(os.path.join(output_dir, "catalyst_historical_collection_summary.json"))
            assert os.path.exists(os.path.join(output_dir, "catalyst_historical_collection_summary.md"))

    def test_no_trade_advice_words(self):
        """测试不包含交易建议词"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_mock_data(tmpdir)

            collector = HistoricalCatalystCollector(
                history_root=os.path.join(tmpdir, "sector_history"),
                catalyst_root=os.path.join(tmpdir, "catalyst_events"),
            )

            result = collector.collect(
                start_date="2026-06-01",
                end_date="2026-06-03",
                report_root=tmpdir,
                offline_fixture=True,
                auto_symbols=True,
                top_sectors=2,
                max_symbols_total=5,
            )

            md = generate_historical_collection_summary_md(result)
            trade_words = ["buy", "sell", "hold", "买入", "卖出", "持有", "推荐"]
            for word in trade_words:
                assert word not in md.lower(), f"报告包含交易建议词: {word}"
