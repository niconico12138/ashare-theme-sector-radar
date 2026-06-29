"""
CLI 轮动参数测试

测试 CLI 的轮动相关参数。
"""

import pytest

from theme_sector_radar.pipeline import run_pipeline


class TestCliRotationArgs:
    """测试 CLI 轮动参数"""

    def test_cli_accepts_compare_to(self):
        """测试 CLI 接受 --compare-to 参数"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            fixture_profile="rotation-day2",
            compare_to="2026-06-27",
        )

        assert report is not None
        assert report.comparison.get("compare_to_date") == "2026-06-27"

    def test_cli_accepts_lookback_days(self):
        """测试 CLI 接受 --lookback-days 参数"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            fixture_profile="rotation-day2",
            lookback_days=5,
        )

        assert report is not None
        # 应该能找到历史快照
        assert report.comparison.get("comparison_status") == "ok"

    def test_compare_to_missing_does_not_crash(self):
        """测试 compare-to 缺失时 CLI 不崩溃"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            fixture_profile="rotation-day2",
            compare_to="2020-01-01",  # 不存在的日期
        )

        assert report is not None
        # 应该有轮动数据，但所有板块标记为新条目
        assert report.rotation_summary is not None

    def test_lookback_no_history_does_not_crash(self):
        """测试 lookback 找不到历史时 CLI 不崩溃"""
        report = run_pipeline(
            as_of_date="2020-01-10",
            top_n=5,
            offline_fixture=True,
            fixture_profile="rotation-day2",
            lookback_days=5,
        )

        assert report is not None
        # 应该有轮动数据，但所有板块标记为新条目
        assert report.rotation_summary is not None

    def test_comparison_status_correct(self):
        """测试 comparison_status 正确"""
        # 有历史数据
        report_with_history = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            fixture_profile="rotation-day2",
            compare_to="2026-06-27",
        )
        assert report_with_history.comparison.get("comparison_status") == "ok"

        # 无历史数据
        report_without_history = run_pipeline(
            as_of_date="2020-01-10",
            top_n=5,
            offline_fixture=True,
            fixture_profile="rotation-day2",
            compare_to="2020-01-01",
        )
        assert report_without_history.comparison.get("comparison_status") == "no_previous_data"
