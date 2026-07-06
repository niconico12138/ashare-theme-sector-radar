"""
Degraded 报告契约测试

测试 degraded 状态下的报告契约。
"""

import json

import pytest

from theme_sector_radar.pipeline import run_pipeline


class TestDegradedReportContract:
    """测试 Degraded 报告契约"""

    def test_report_has_status_field(self):
        """测试报告包含 status 字段"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            provider_name="fixture",
        )

        assert hasattr(report, "status")
        assert report.status in ["ok", "degraded", "failed"]

    def test_report_has_provider_status(self):
        """测试报告包含 provider_status 字段"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            provider_name="fixture",
        )

        assert hasattr(report, "provider_status")
        assert hasattr(report.provider_status, "industry_sectors")
        assert hasattr(report.provider_status, "concept_sectors")

    def test_report_has_cache_fallback(self):
        """测试报告包含 cache_fallback 字段"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            provider_name="fixture",
        )

        assert hasattr(report, "cache_fallback")
        assert isinstance(report.cache_fallback, dict)

    def test_report_has_fund_flow_coverage(self):
        """测试报告包含 fund_flow_coverage 字段"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            provider_name="fixture",
        )

        assert hasattr(report, "fund_flow_coverage")
        assert isinstance(report.fund_flow_coverage, dict)

    def test_report_has_constituent_coverage(self):
        """测试报告包含 constituent_coverage 字段"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            provider_name="fixture",
        )

        assert hasattr(report, "constituent_coverage")
        assert isinstance(report.constituent_coverage, dict)

    def test_json_report_has_required_fields(self):
        """测试 JSON 报告包含必要字段"""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                provider_name="fixture",
            )

            json_path = os.path.join(tmpdir, "theme_sector_radar.json")
            with open(json_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            # 检查必要字段
            required_fields = [
                "report_type",
                "version",
                "as_of_date",
                "status",
                "provider_status",
                "data_completeness",
                "cache_fallback",
                "fund_flow_coverage",
                "constituent_coverage",
                "disclaimer",
            ]

            for field in required_fields:
                assert field in json_data, f"Missing field: {field}"

    def test_json_report_no_stock_recommendation(self):
        """测试 JSON 报告不含个股操作结论"""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                provider_name="fixture",
            )

            json_path = os.path.join(tmpdir, "theme_sector_radar.json")
            with open(json_path, "r", encoding="utf-8") as f:
                json_str = f.read()

            # 不得出现 buy/sell/hold
            assert "buy" not in json_str.lower()
            assert "sell" not in json_str.lower()
            assert "hold" not in json_str.lower()
            assert "买入" not in json_str
            assert "卖出" not in json_str
            assert "持有建议" not in json_str

    def test_markdown_report_has_data_completeness_section(self):
        """测试 Markdown 报告包含数据完整性章节"""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                provider_name="fixture",
            )

            md_path = os.path.join(tmpdir, "theme_sector_radar.md")
            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()

            assert "数据完整性" in md_content
            assert "行业板块数量" in md_content
            assert "概念板块数量" in md_content

    def test_markdown_report_has_disclaimer(self):
        """测试 Markdown 报告包含声明"""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
                provider_name="fixture",
            )

            md_path = os.path.join(tmpdir, "theme_sector_radar.md")
            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()

            assert "不作为个股操作依据或自动交易指令" in md_content
