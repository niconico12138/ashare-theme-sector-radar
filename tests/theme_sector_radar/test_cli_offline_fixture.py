"""
CLI 离线 Fixture 测试

测试 CLI 离线运行。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.cli import main
from theme_sector_radar.pipeline import run_pipeline


class TestCliOfflineFixture:
    """测试 CLI 离线 Fixture"""

    def test_pipeline_offline_fixture(self):
        """测试 Pipeline 离线运行"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
            )

            # 验证报告生成
            assert report.report_type == "theme_sector_radar"
            assert report.as_of_date == "2026-06-28"
            assert len(report.industry_top) > 0
            assert len(report.concept_top) > 0

            # 验证文件生成
            json_path = os.path.join(tmpdir, "theme_sector_radar.json")
            md_path = os.path.join(tmpdir, "theme_sector_radar.md")
            snapshot_path = os.path.join(tmpdir, "raw_snapshot.json")

            assert os.path.exists(json_path)
            assert os.path.exists(md_path)
            assert os.path.exists(snapshot_path)

            # 验证 JSON 内容
            with open(json_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
            assert json_data["report_type"] == "theme_sector_radar"
            assert "disclaimer" in json_data
            assert "不作为个股操作依据" in json_data["disclaimer"]

            # 验证 Markdown 内容
            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            assert "不作为个股操作依据或自动交易指令" in md_content

    def test_pipeline_market_temperature(self):
        """测试市场温度计算"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
            )

            # 验证市场温度
            assert report.market_temperature.label in [
                "hot", "warm", "neutral", "cool", "cold"
            ]
            assert 0 <= report.market_temperature.score <= 100

    def test_pipeline_focus_levels(self):
        """测试关注等级"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
            )

            # 验证关注等级合法
            valid_levels = {"focus", "watch", "core_only", "caution", "avoid"}
            for score in report.industry_top + report.concept_top:
                assert score.focus_level.value in valid_levels

    def test_pipeline_risk_assessment(self):
        """测试风险评估"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
            )

            # 验证风险等级合法
            valid_risk_levels = {"low", "medium", "high"}
            for score in report.industry_top + report.concept_top:
                assert score.risk_level.value in valid_risk_levels

    def test_pipeline_data_quality(self):
        """测试数据质量"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=5,
                output_dir=tmpdir,
                offline_fixture=True,
            )

            # 验证数据质量分
            assert 0 <= report.data_quality_score <= 100
