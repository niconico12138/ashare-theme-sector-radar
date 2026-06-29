"""
报告可读性测试

测试 Markdown 报告的可读性改进。
"""

import os
import tempfile

import pytest

from theme_sector_radar.pipeline import run_pipeline


class TestReportReadability:
    """测试报告可读性"""

    def test_markdown_has_score_breakdown_section(self):
        """测试 Markdown 包含评分 breakdown 章节"""
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
                content = f.read()

            # 应该包含评分相关信息
            assert "分数" in content or "score" in content.lower()

    def test_markdown_has_clear_structure(self):
        """测试 Markdown 有清晰的结构"""
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
                content = f.read()

            # 应该有清晰的章节结构
            assert "## " in content  # 有二级标题

    def test_markdown_tables_are_formatted(self):
        """测试 Markdown 表格格式正确"""
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
                content = f.read()

            # 应该有表格分隔符
            assert "|------|" in content or "| --- |" in content

    def test_json_has_complete_breakdown(self):
        """测试 JSON 包含完整的 breakdown"""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="full",
            )

            import json
            json_path = os.path.join(tmpdir, "theme_sector_radar.json")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 检查行业板块包含 score_breakdown
            if data.get("industry_top"):
                first = data["industry_top"][0]
                assert "score_breakdown" in first
