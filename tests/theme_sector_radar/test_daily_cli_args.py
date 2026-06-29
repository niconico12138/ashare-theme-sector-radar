"""
Daily CLI 参数测试

测试 daily 相关参数。
"""

import pytest

from theme_sector_radar.pipeline import run_pipeline


class TestDailyCliArgs:
    """测试 Daily CLI 参数"""

    def test_daily_mode_generates_report(self):
        """测试 daily 模式能生成报告"""
        report = run_pipeline(
            as_of_date="2026-06-28",
            top_n=5,
            offline_fixture=True,
            fixture_profile="full",
        )

        assert report is not None
        assert report.as_of_date == "2026-06-28"

    def test_daily_output_directory(self):
        """测试 daily 输出到固定 YYYY-MM-DD 目录"""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            report_root = tmpdir
            as_of_date = "2026-06-28"
            output_dir = os.path.join(report_root, as_of_date)

            run_pipeline(
                as_of_date=as_of_date,
                top_n=5,
                output_dir=output_dir,
                offline_fixture=True,
                fixture_profile="full",
            )

            # 验证目录结构
            assert os.path.exists(output_dir)
            assert os.path.exists(os.path.join(output_dir, "theme_sector_radar.json"))
            assert os.path.exists(os.path.join(output_dir, "theme_sector_radar.md"))
            assert os.path.exists(os.path.join(output_dir, "raw_snapshot.json"))
