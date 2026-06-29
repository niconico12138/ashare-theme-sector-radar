"""
Daily 无网络契约测试

测试 daily/replay 报告不包含禁止内容。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.pipeline import run_pipeline


class TestDailyNoNetworkContract:
    """测试 Daily 无网络契约"""

    def test_daily_report_no_stock_recommendation(self):
        """测试 daily 报告不包含个股推荐"""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="full",
            )

            # 检查 JSON
            json_path = os.path.join(tmpdir, "theme_sector_radar.json")
            with open(json_path, "r", encoding="utf-8") as f:
                json_str = f.read()

            assert "buy" not in json_str.lower()
            assert "sell" not in json_str.lower()
            assert "hold" not in json_str.lower()

            # 检查 Markdown
            md_path = os.path.join(tmpdir, "theme_sector_radar.md")
            with open(md_path, "r", encoding="utf-8") as f:
                md_str = f.read()

            assert "buy" not in md_str.lower()
            assert "sell" not in md_str.lower()
            assert "hold" not in md_str.lower()

    def test_daily_report_has_disclaimer(self):
        """测试 daily 报告包含声明"""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="full",
            )

            md_path = os.path.join(tmpdir, "theme_sector_radar.md")
            with open(md_path, "r", encoding="utf-8") as f:
                md_str = f.read()

            assert "不构成个股推荐、买卖建议或自动交易指令" in md_str

    def test_replay_report_no_stock_recommendation(self):
        """测试 replay 报告不包含个股推荐"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 运行两次模拟 replay
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="full",
            )

            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="full",
                use_cache=True,
            )

            # 检查报告
            json_path = os.path.join(tmpdir, "theme_sector_radar.json")
            with open(json_path, "r", encoding="utf-8") as f:
                json_str = f.read()

            assert "buy" not in json_str.lower()
            assert "sell" not in json_str.lower()
            assert "hold" not in json_str.lower()
