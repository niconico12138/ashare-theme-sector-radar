"""
历史快照加载器测试

测试 snapshot_loader 的功能。
"""

import pytest

from tests.theme_sector_radar.report_fixture_factory import write_theme_snapshot
from theme_sector_radar.history.snapshot_loader import load_previous_snapshot


class TestSnapshotLoader:
    """测试历史快照加载器"""

    def test_compare_to_finds_existing_report(self, tmp_path):
        """测试 --compare-to 能找到已存在的报告"""
        report_dir = tmp_path / "reports" / "theme_sector_radar"
        cache_dir = tmp_path / "data_cache"
        write_theme_snapshot(report_dir, "2026-06-27", "rotation-day1")

        snapshot = load_previous_snapshot(
            current_date="2026-06-28",
            compare_to="2026-06-27",
            lookback_days=5,
            report_dirs=[str(report_dir)],
            cache_dirs=[str(cache_dir)],
        )

        # 应该能找到 rotation-day1 的报告
        assert snapshot is not None
        assert snapshot.get("as_of_date") == "2026-06-27"

    def test_compare_to_returns_report_with_data(self, tmp_path):
        """测试 --compare-to 返回有数据的报告"""
        report_dir = tmp_path / "reports" / "theme_sector_radar"
        cache_dir = tmp_path / "data_cache"
        write_theme_snapshot(report_dir, "2026-06-27", "rotation-day1")

        snapshot = load_previous_snapshot(
            current_date="2026-06-28",
            compare_to="2026-06-27",
            lookback_days=5,
            report_dirs=[str(report_dir)],
            cache_dirs=[str(cache_dir)],
        )

        assert snapshot is not None
        # 应该有 industry_top 或 concept_top 数据
        assert snapshot.get("industry_top") or snapshot.get("concept_top")

    def test_compare_to_missing_returns_none(self, tmp_path):
        """测试 --compare-to 找不到报告时返回 None"""
        report_dir = tmp_path / "reports" / "theme_sector_radar"
        cache_dir = tmp_path / "data_cache"
        write_theme_snapshot(report_dir, "2026-06-27", "rotation-day1")

        with pytest.warns(
            UserWarning,
            match=r"未找到指定日期 2020-01-01 的历史快照",
        ):
            snapshot = load_previous_snapshot(
                current_date="2026-06-28",
                compare_to="2020-01-01",  # 不存在的日期
                lookback_days=5,
                report_dirs=[str(report_dir)],
                cache_dirs=[str(cache_dir)],
            )

        assert snapshot is None

    def test_lookback_finds_recent_report(self, tmp_path):
        """测试 --lookback-days 能找到最近可用报告"""
        report_dir = tmp_path / "reports" / "theme_sector_radar"
        cache_dir = tmp_path / "data_cache"
        write_theme_snapshot(report_dir, "2026-06-27", "rotation-day1")

        snapshot = load_previous_snapshot(
            current_date="2026-06-28",
            compare_to=None,
            lookback_days=5,
            report_dirs=[str(report_dir)],
            cache_dirs=[str(cache_dir)],
        )

        # 应该能找到历史报告
        assert snapshot is not None

    def test_lookback_does_not_read_current_date(self, tmp_path):
        """测试 lookback 不会误读当天报告"""
        report_dir = tmp_path / "reports" / "theme_sector_radar"
        cache_dir = tmp_path / "data_cache"
        write_theme_snapshot(report_dir, "2020-01-10", "rotation-day2")

        snapshot = load_previous_snapshot(
            current_date="2020-01-10",
            compare_to=None,
            lookback_days=5,
            report_dirs=[str(report_dir)],
            cache_dirs=[str(cache_dir)],
        )

        # 应该找不到报告
        assert snapshot is None

    def test_lookback_finds_rotation_day1(self, tmp_path):
        """测试 lookback 能找到 rotation-day1 报告"""
        report_dir = tmp_path / "reports" / "theme_sector_radar"
        cache_dir = tmp_path / "data_cache"
        write_theme_snapshot(report_dir, "2026-06-27", "rotation-day1")

        snapshot = load_previous_snapshot(
            current_date="2026-06-28",
            compare_to=None,
            lookback_days=5,
            report_dirs=[str(report_dir)],
            cache_dirs=[str(cache_dir)],
        )

        assert snapshot is not None
        # 应该找到 2026-06-27 的报告
        assert snapshot.get("as_of_date") == "2026-06-27"

    def test_no_history_returns_none(self, tmp_path):
        """测试没有历史快照时返回 None"""
        report_dir = tmp_path / "reports" / "theme_sector_radar"
        cache_dir = tmp_path / "data_cache"

        with pytest.warns(
            UserWarning,
            match=r"未找到指定日期 2020-01-01 的历史快照",
        ):
            snapshot = load_previous_snapshot(
                current_date="2020-01-10",
                compare_to="2020-01-01",
                lookback_days=5,
                report_dirs=[str(report_dir)],
                cache_dirs=[str(cache_dir)],
            )

        assert snapshot is None
