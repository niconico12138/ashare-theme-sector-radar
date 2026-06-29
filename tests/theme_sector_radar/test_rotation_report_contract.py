"""
轮动报告契约测试

测试 JSON 和 Markdown 报告的轮动字段。
"""

import json
import tempfile
import os

import pytest

from theme_sector_radar.pipeline import run_pipeline


class TestRotationReportContract:
    """测试轮动报告契约"""

    def test_json_has_rotation_summary(self):
        """测试 JSON 包含 rotation_summary"""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                compare_to="2026-06-27",
            )

            json_path = os.path.join(tmpdir, "theme_sector_radar.json")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert "rotation_summary" in data
            assert "industry" in data["rotation_summary"]
            assert "concept" in data["rotation_summary"]

    def test_json_has_comparison(self):
        """测试 JSON 包含 comparison"""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                compare_to="2026-06-27",
            )

            json_path = os.path.join(tmpdir, "theme_sector_radar.json")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert "comparison" in data
            assert "compare_to_date" in data["comparison"]
            assert data["comparison"]["compare_to_date"] == "2026-06-27"

    def test_markdown_has_rotation_section(self):
        """测试 Markdown 包含板块轮动变化章节"""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                compare_to="2026-06-27",
            )

            md_path = os.path.join(tmpdir, "theme_sector_radar.md")
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            assert "板块轮动变化" in content

    def test_markdown_has_new_entries_section(self):
        """测试 Markdown 包含新晋 Top N 章节"""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                compare_to="2026-06-27",
            )

            md_path = os.path.join(tmpdir, "theme_sector_radar.md")
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 应该包含新晋板块章节
            assert "新晋" in content or "新进" in content

    def test_markdown_has_rising_fast_section(self):
        """测试 Markdown 包含快速升温章节"""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                compare_to="2026-06-27",
            )

            md_path = os.path.join(tmpdir, "theme_sector_radar.md")
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 应该包含快速升温章节
            assert "快速升温" in content or "升温" in content

    def test_markdown_has_persistent_strength_section(self):
        """测试 Markdown 包含连续强势章节"""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                compare_to="2026-06-27",
            )

            md_path = os.path.join(tmpdir, "theme_sector_radar.md")
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 应该包含连续强势章节
            assert "连续强势" in content or "持续" in content

    def test_markdown_has_dropped_out_section(self):
        """测试 Markdown 包含掉出 Top N 章节"""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                compare_to="2026-06-27",
            )

            md_path = os.path.join(tmpdir, "theme_sector_radar.md")
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 应该包含掉出章节
            assert "掉出" in content or "退出" in content

    def test_markdown_no_stock_recommendation(self):
        """测试 Markdown 不包含个股推荐"""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                compare_to="2026-06-27",
            )

            md_path = os.path.join(tmpdir, "theme_sector_radar.md")
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 不得出现 buy/sell/hold
            assert "buy" not in content.lower()
            assert "sell" not in content.lower()
            assert "hold" not in content.lower()

    def test_rotation_summary_separates_industry_concept(self):
        """测试 rotation_summary 分开 industry 和 concept"""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                compare_to="2026-06-27",
            )

            json_path = os.path.join(tmpdir, "theme_sector_radar.json")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            rotation = data.get("rotation_summary", {})
            assert "industry" in rotation
            assert "concept" in rotation

            # industry 和 concept 应该是独立的字典
            assert isinstance(rotation["industry"], dict)
            assert isinstance(rotation["concept"], dict)
