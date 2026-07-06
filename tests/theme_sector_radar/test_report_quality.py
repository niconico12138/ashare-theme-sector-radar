"""
报告质量测试

测试 Markdown 报告质量。
"""

import pytest

from theme_sector_radar.pipeline import run_pipeline


class TestReportQuality:
    """测试报告质量"""

    def test_markdown_has_market_temperature_section(self):
        """测试 Markdown 包含市场温度章节"""
        import tempfile
        import os

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

            assert "市场短线温度" in content

    def test_markdown_has_industry_top_section(self):
        """测试 Markdown 包含行业 Top N 章节"""
        import tempfile
        import os

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

            assert "行业板块 Top N" in content

    def test_markdown_has_concept_top_section(self):
        """测试 Markdown 包含概念 Top N 章节"""
        import tempfile
        import os

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

            assert "概念板块 Top N" in content

    def test_markdown_has_overlap_section(self):
        """测试 Markdown 包含共振章节"""
        import tempfile
        import os

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

            assert "行业 + 概念共振" in content

    def test_markdown_has_data_completeness_section(self):
        """测试 Markdown 包含数据完整性章节"""
        import tempfile
        import os

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

            assert "数据完整性" in content

    def test_markdown_has_risk_section(self):
        """测试 Markdown 包含风险提示章节"""
        import tempfile
        import os

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

            assert "风险提示" in content

    def test_markdown_has_disclaimer(self):
        """测试 Markdown 包含声明"""
        import tempfile
        import os

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

            assert "不作为个股操作依据或自动交易指令" in content

    def test_markdown_no_stock_recommendation(self):
        """测试 Markdown 不含个股操作结论"""
        import tempfile
        import os

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

            # 不得出现 buy/sell/hold（不区分大小写）
            # 注意：声明中的 "不构成个股操作结论" 是允许的
            lines = content.split("\n")
            disclaimer_line = ""
            for line in lines:
                if "声明" in line or "不构成" in line:
                    disclaimer_line = line
                    break

            # 检查非声明行中不包含禁止词
            for line in lines:
                if line == disclaimer_line or "不构成" in line:
                    continue
                # 这里只检查明显的推荐语义
                # 不检查声明中的 "不构成个股操作结论"

            # 检查 buy/sell/hold 不出现在表格数据中
            assert "buy" not in content.lower().replace("不构成个股操作结论", "")
            assert "sell" not in content.lower().replace("不构成个股操作结论", "")
            assert "hold" not in content.lower().replace("不构成个股操作结论", "")

    def test_json_has_score_breakdown(self):
        """测试 JSON 包含 score_breakdown"""
        import tempfile
        import os
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="full",
            )

            json_path = os.path.join(tmpdir, "theme_sector_radar.json")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 检查行业板块包含 score_breakdown
            if data.get("industry_top"):
                first_industry = data["industry_top"][0]
                assert "score_breakdown" in first_industry
                breakdown = first_industry["score_breakdown"]
                assert "trend_strength" in breakdown
                assert "fund_flow" in breakdown
                assert "positive_score" in breakdown
                assert "final_score" in breakdown

    def test_json_has_watch_points(self):
        """测试 JSON 包含 watch_points"""
        import tempfile
        import os
        import json

        with tempfile.TemporaryDirectory() as tmpdir:
            run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                fixture_profile="full",
            )

            json_path = os.path.join(tmpdir, "theme_sector_radar.json")
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 检查行业板块包含 watch_points
            if data.get("industry_top"):
                first_industry = data["industry_top"][0]
                assert "watch_points" in first_industry
                assert isinstance(first_industry["watch_points"], list)
