"""
轮动 fixture profiles 测试

测试 rotation-day1 和 rotation-day2 fixture。
"""

import json
import os
import tempfile

import pytest

from theme_sector_radar.pipeline import run_pipeline


class TestRotationFixtureProfiles:
    """测试轮动 fixture profiles"""

    def test_rotation_day1_generates_report(self):
        """测试 rotation-day1 能生成报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_root = os.path.join(tmpdir, "reports", "theme_sector_radar")
            output_dir = os.path.join(report_root, "2026-06-27")

            report = run_pipeline(
                as_of_date="2026-06-27",
                top_n=10,
                output_dir=output_dir,
                offline_fixture=True,
                fixture_profile="rotation-day1",
                report_root=report_root,
            )

            assert report is not None
            assert report.as_of_date == "2026-06-27"
            assert len(report.industry_top) > 0
            assert len(report.concept_top) > 0

    def test_rotation_day2_generates_report(self):
        """测试 rotation-day2 能生成报告"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_root = os.path.join(tmpdir, "reports", "theme_sector_radar")
            output_dir = os.path.join(report_root, "2026-06-28")

            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=10,
                output_dir=output_dir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                report_root=report_root,
            )

            assert report is not None
            assert report.as_of_date == "2026-06-28"
            assert len(report.industry_top) > 0
            assert len(report.concept_top) > 0

    def test_day2_has_rotation_data(self):
        """测试 day2 有轮动数据"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_root = os.path.join(tmpdir, "reports", "theme_sector_radar")
            day1_dir = os.path.join(report_root, "2026-06-27")
            day2_dir = os.path.join(report_root, "2026-06-28")

            # 先生成 day1
            run_pipeline(
                as_of_date="2026-06-27",
                top_n=10,
                output_dir=day1_dir,
                offline_fixture=True,
                fixture_profile="rotation-day1",
                report_root=report_root,
            )

            # 再生成 day2
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=10,
                output_dir=day2_dir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                compare_to="2026-06-27",
                report_root=report_root,
            )

            # 应该有轮动数据
            assert report.rotation_summary is not None
            assert "industry" in report.rotation_summary
            assert "concept" in report.rotation_summary

    def test_day2_has_new_entries(self):
        """测试 day2 有新晋板块"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_root = os.path.join(tmpdir, "reports", "theme_sector_radar")
            day1_dir = os.path.join(report_root, "2026-06-27")
            day2_dir = os.path.join(report_root, "2026-06-28")

            # 先生成 day1
            run_pipeline(
                as_of_date="2026-06-27",
                top_n=10,
                output_dir=day1_dir,
                offline_fixture=True,
                fixture_profile="rotation-day1",
                report_root=report_root,
            )

            # 再生成 day2
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=10,
                output_dir=day2_dir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                compare_to="2026-06-27",
                report_root=report_root,
            )

            # 应该有新晋板块
            industry_new = report.rotation_summary.get("industry", {}).get("new_entries", [])
            concept_new = report.rotation_summary.get("concept", {}).get("new_entries", [])

            assert len(industry_new) > 0 or len(concept_new) > 0

    def test_day2_has_dropped_out(self):
        """测试 day2 有掉出板块"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_root = os.path.join(tmpdir, "reports", "theme_sector_radar")
            day1_dir = os.path.join(report_root, "2026-06-27")
            day2_dir = os.path.join(report_root, "2026-06-28")

            # 先生成 day1
            run_pipeline(
                as_of_date="2026-06-27",
                top_n=10,
                output_dir=day1_dir,
                offline_fixture=True,
                fixture_profile="rotation-day1",
                report_root=report_root,
            )

            # 再生成 day2
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=10,
                output_dir=day2_dir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                compare_to="2026-06-27",
                report_root=report_root,
            )

            # 应该有掉出板块
            industry_dropped = report.rotation_summary.get("industry", {}).get("dropped_out", [])
            concept_dropped = report.rotation_summary.get("concept", {}).get("dropped_out", [])

            assert len(industry_dropped) > 0 or len(concept_dropped) > 0

    def test_day2_has_rising_fast(self):
        """测试 day2 有快速升温板块"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_root = os.path.join(tmpdir, "reports", "theme_sector_radar")
            day1_dir = os.path.join(report_root, "2026-06-27")
            day2_dir = os.path.join(report_root, "2026-06-28")

            # 先生成 day1
            run_pipeline(
                as_of_date="2026-06-27",
                top_n=10,
                output_dir=day1_dir,
                offline_fixture=True,
                fixture_profile="rotation-day1",
                report_root=report_root,
            )

            # 再生成 day2
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=10,
                output_dir=day2_dir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                compare_to="2026-06-27",
                report_root=report_root,
            )

            # 应该有快速升温板块
            industry_rising = report.rotation_summary.get("industry", {}).get("rising_fast", [])
            concept_rising = report.rotation_summary.get("concept", {}).get("rising_fast", [])

            assert len(industry_rising) > 0 or len(concept_rising) > 0

    def test_day2_has_persistent_strength(self):
        """测试 day2 有连续强势板块"""
        with tempfile.TemporaryDirectory() as tmpdir:
            report_root = os.path.join(tmpdir, "reports", "theme_sector_radar")
            day1_dir = os.path.join(report_root, "2026-06-27")
            day2_dir = os.path.join(report_root, "2026-06-28")

            # 先生成 day1
            run_pipeline(
                as_of_date="2026-06-27",
                top_n=10,
                output_dir=day1_dir,
                offline_fixture=True,
                fixture_profile="rotation-day1",
                report_root=report_root,
            )

            # 再生成 day2
            report = run_pipeline(
                as_of_date="2026-06-28",
                top_n=10,
                output_dir=day2_dir,
                offline_fixture=True,
                fixture_profile="rotation-day2",
                compare_to="2026-06-27",
                report_root=report_root,
            )

            # 应该有连续强势板块
            industry_persistent = report.rotation_summary.get("industry", {}).get("persistent_strength", [])
            concept_persistent = report.rotation_summary.get("concept", {}).get("persistent_strength", [])

            assert len(industry_persistent) > 0 or len(concept_persistent) > 0
