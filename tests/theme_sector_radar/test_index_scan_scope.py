"""
Index 扫描范围测试

测试 index_report 只扫描标准日报目录。
"""

import pytest

from theme_sector_radar.reports.index_report import is_standard_daily_dir, scan_daily_reports


class TestIndexScanScope:
    """测试 Index 扫描范围"""

    def test_is_standard_daily_dir(self):
        """测试标准日报目录识别"""
        assert is_standard_daily_dir("2026-06-28") is True
        assert is_standard_daily_dir("2026-01-01") is True

    def test_is_not_standard_daily_dir(self):
        """测试非标准日报目录识别"""
        assert is_standard_daily_dir("2026-06-28-phase4") is False
        assert is_standard_daily_dir("2026-06-28-rotation-day1") is False
        assert is_standard_daily_dir("2026-06-28-akshare") is False
        assert is_standard_daily_dir("2026-06-28-fixture") is False
        assert is_standard_daily_dir("experiments") is False

    def test_scan_daily_reports_only_standard(self):
        """测试 scan_daily_reports 只扫描标准目录"""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建标准日报目录
            standard_dir = os.path.join(tmpdir, "2026-06-28")
            os.makedirs(standard_dir)
            with open(os.path.join(standard_dir, "theme_sector_radar.json"), "w") as f:
                f.write("{}")

            # 创建实验目录
            experiment_dir = os.path.join(tmpdir, "2026-06-28-phase4")
            os.makedirs(experiment_dir)
            with open(os.path.join(experiment_dir, "theme_sector_radar.json"), "w") as f:
                f.write("{}")

            # 扫描（默认不包含实验目录）
            dates = scan_daily_reports(tmpdir, include_experiments=False)
            assert "2026-06-28" in dates
            assert "2026-06-28-phase4" not in dates

    def test_scan_daily_reports_include_experiments(self):
        """测试 scan_daily_reports 包含实验目录"""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建标准日报目录
            standard_dir = os.path.join(tmpdir, "2026-06-28")
            os.makedirs(standard_dir)
            with open(os.path.join(standard_dir, "theme_sector_radar.json"), "w") as f:
                f.write("{}")

            # 创建实验目录
            experiment_dir = os.path.join(tmpdir, "2026-06-28-phase4")
            os.makedirs(experiment_dir)
            with open(os.path.join(experiment_dir, "theme_sector_radar.json"), "w") as f:
                f.write("{}")

            # 扫描（包含实验目录）
            dates = scan_daily_reports(tmpdir, include_experiments=True)
            assert "2026-06-28" in dates
            assert "2026-06-28-phase4" in dates
