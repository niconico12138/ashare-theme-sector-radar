"""
轮动 fixture profiles 测试

测试 rotation-day1 和 rotation-day2 fixture。
"""

import pytest

from theme_sector_radar.pipeline import run_pipeline


class TestRotationFixtureProfiles:
    """测试轮动 fixture profiles"""

    def test_rotation_day1_generates_report(self):
        """测试 rotation-day1 能生成报告"""
        report = run_pipeline(
            as_of_date="2026-06-27",
            top_n=10,
            offline_fixture=True,
            fixture_profile="rotation-day1",
        )

        assert report is not None
        assert report.as_of_date == "2026-06-27"
        assert len(report.industry_top) > 0
        assert len(report.concept_top) > 0

    def test_rotation_day2_generates_report(self):
        """测试 rotation-day2 能生成报告"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=10,
            offline_fixture=True,
            fixture_profile="rotation-day2",
        )

        assert report is not None
        assert report.as_of_date == "2026-06-28"
        assert len(report.industry_top) > 0
        assert len(report.concept_top) > 0

    def test_day2_has_rotation_data(self):
        """测试 day2 有轮动数据"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=10,
            offline_fixture=True,
            fixture_profile="rotation-day2",
            compare_to="2026-06-27",
        )

        # 应该有轮动数据
        assert report.rotation_summary is not None
        assert "industry" in report.rotation_summary
        assert "concept" in report.rotation_summary

    def test_day2_has_new_entries(self):
        """测试 day2 有新晋板块"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=10,
            offline_fixture=True,
            fixture_profile="rotation-day2",
            compare_to="2026-06-27",
        )

        # 应该有新晋板块
        industry_new = report.rotation_summary.get("industry", {}).get("new_entries", [])
        concept_new = report.rotation_summary.get("concept", {}).get("new_entries", [])

        assert len(industry_new) > 0 or len(concept_new) > 0

    def test_day2_has_dropped_out(self):
        """测试 day2 有掉出板块"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=10,
            offline_fixture=True,
            fixture_profile="rotation-day2",
            compare_to="2026-06-27",
        )

        # 应该有掉出板块
        industry_dropped = report.rotation_summary.get("industry", {}).get("dropped_out", [])
        concept_dropped = report.rotation_summary.get("concept", {}).get("dropped_out", [])

        assert len(industry_dropped) > 0 or len(concept_dropped) > 0

    def test_day2_has_rising_fast(self):
        """测试 day2 有快速升温板块"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=10,
            offline_fixture=True,
            fixture_profile="rotation-day2",
            compare_to="2026-06-27",
        )

        # 应该有快速升温板块
        industry_rising = report.rotation_summary.get("industry", {}).get("rising_fast", [])
        concept_rising = report.rotation_summary.get("concept", {}).get("rising_fast", [])

        assert len(industry_rising) > 0 or len(concept_rising) > 0

    def test_day2_has_persistent_strength(self):
        """测试 day2 有连续强势板块"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=10,
            offline_fixture=True,
            fixture_profile="rotation-day2",
            compare_to="2026-06-27",
        )

        # 应该有连续强势板块
        industry_persistent = report.rotation_summary.get("industry", {}).get("persistent_strength", [])
        concept_persistent = report.rotation_summary.get("concept", {}).get("persistent_strength", [])

        assert len(industry_persistent) > 0 or len(concept_persistent) > 0
